#!/usr/bin/env python3
# coding: utf-8

"""
generate_presets.py
- Validiert Indikatoren (World Bank metadata)
- Holt Indikatorwerte pro Land (World Bank)
- Rechnet Monatswerte aus Jahreswerten (konfigurierbar)
- Versucht Fallback-Quellen (lokale CSV oder custom fetcher)
- Schreibt presets/preset_<COUNTRY>.json
- Optional: Validiert erzeugte Presets gegen scripts/preset_schema.json
"""

import os
import json
import time
import logging
import requests
import glob
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# jsonschema wird nur in der optionalen Validierungsfunktion benötigt
from jsonschema import validate as js_validate, ValidationError

# ---------- Konfiguration ----------
OUTPUT_DIR = "presets"
LOG_FILE = "generate_presets.log"
INDICATORS_CSV = "scripts/indicators.csv"
INDICATORS_JSON = "scripts/indicators.json"
INDICATOR_CACHE = "indicator_cache.json"
WB_BASE = "https://api.worldbank.org/v2"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5
VALIDATION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 Tage
COUNTRIES = ["DE", "CN", "US", "IR", "BR", "IN"]
USE_FALLBACK = True
FALLBACK_CSV = "scripts/fallback_data.csv"
COUNTRY_CODES_FILE = "scripts/country_codes.json"
# -----------------------------------

# Logging konfigurieren
logger = logging.getLogger("generate_presets")
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(fmt)
ch.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(fmt)
fh.setLevel(logging.DEBUG)
logger.addHandler(ch)
logger.addHandler(fh)

# ----------------- Hilfsfunktionen -----------------
def load_indicators() -> List[str]:
    if os.path.exists(INDICATORS_JSON):
        logger.info(f"Lade Indikatoren aus {INDICATORS_JSON}")
        with open(INDICATORS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return list(data) if isinstance(data, list) else data.get("indicators", [])
    if os.path.exists(INDICATORS_CSV):
        logger.info(f"Lade Indikatoren aus {INDICATORS_CSV}")
        inds = []
        with open(INDICATORS_CSV, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    inds.append(s)
        return inds
    logger.info("Keine Indikator-Datei gefunden, verwende eingebaute Liste")
    return ["FI.RES.TOTL", "NE.IMP.GNFS.CD", "DT.DOD.DECT.GN.ZS"]

def load_cache() -> Dict[str, Any]:
    if os.path.exists(INDICATOR_CACHE):
        try:
            with open(INDICATOR_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Cache konnte nicht geladen werden: %s", e)
    return {}

def save_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(INDICATOR_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Cache konnte nicht gespeichert werden: %s", e)

def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------- World Bank GET mit Retries -----------------
def _wb_get(url: str, params: Dict[str, Any]) -> Optional[Any]:
    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                logger.error("Ungültige JSON-Antwort von WB: %s", r.text[:500])
                return None
        except requests.RequestException as e:
            logger.warning("WB RequestException %s (attempt %d)", e, attempt)
            sleep = BACKOFF_FACTOR * (2 ** attempt)
            time.sleep(sleep)
            attempt += 1
    logger.error("Max retries erreicht für URL %s", url)
    return None

# ----------------- Validierung (metadata endpoint) -----------------
def validate_indicator(indicator: str, cache: Dict[str, Any]) -> bool:
    now = time.time()
    cache_key = f"validate:{indicator}"
    cached = cache.get(cache_key)
    if cached:
        age = now - cached.get("checked_at", 0)
        if age < VALIDATION_TTL_SECONDS:
            logger.debug("Verwende Validierungs-Cache für %s (age %ds)", indicator, int(age))
            return cached.get("valid", False)

    url = f"{WB_BASE}/indicator/{indicator}"
    params = {"format": "json"}
    head = _wb_get(url, params)
    valid = False
    if head is None:
        logger.warning("Keine Antwort bei Validierung von %s", indicator)
        valid = False
    else:
        if isinstance(head, list) and head and isinstance(head[0], dict) and "message" in head[0]:
            logger.info("WB metadata returned message for indicator %s: %s", indicator, head[0].get("message"))
            valid = False
        else:
            valid = True

    cache[cache_key] = {"valid": valid, "checked_at": now}
    save_cache(cache)
    return valid

# ----------------- Fetch indicator for country -----------------
def fetch_worldbank_indicator(country: str, indicator: str) -> Dict[str, Any]:
    url = f"{WB_BASE}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "per_page": 100}
    head = _wb_get(url, params)
    if head is None:
        return {"status": "error", "message": "no_response"}
    if isinstance(head, list) and head and isinstance(head[0], dict) and "message" in head[0]:
        return {"status": "error", "message": head[0].get("message"), "raw_head": head}
    if isinstance(head, list) and len(head) > 1:
        paging = head[0]
        data = head[1]
        if not data:
            return {"status": "empty", "paging": paging}
        return {"status": "ok", "paging": paging, "data": data}
    return {"status": "unexpected", "raw": head}

def latest_value_from_data(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for entry in data:
        if entry.get("value") is not None:
            return entry
    return None

# ----------------- Fallback: lokale CSV loader (überarbeitet) -----------------
def load_fallback_csv(path: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Lädt fallback_data.csv und sammelt alle Einträge pro country+indicator.
    Reduziert anschließend auf den Eintrag mit dem neuesten Jahr (wenn Jahr numerisch).
    Erwartetes CSV-Feldset: country,indicator,year,value,source
    Rückgabe: { country: { indicator: { "year": ..., "value": ..., "source": ... } } }
    """
    fallback = {}
    if not os.path.exists(path):
        return {}
    import csv
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            c = (row.get("country") or "").strip()
            ind = (row.get("indicator") or "").strip()
            year = (row.get("year") or "").strip()
            val = row.get("value")
            src = (row.get("source") or "fallback_csv").strip()
            if not (c and ind and val):
                continue
            try:
                v = float(val)
            except Exception:
                continue
            fallback.setdefault(c, {}).setdefault(ind, []).append({"year": year, "value": v, "source": src})

    # reduce to latest-year entry per country+indicator
    reduced = {}
    for c, inds in fallback.items():
        reduced[c] = {}
        for ind, entries in inds.items():
            def year_key(e):
                y = e.get("year")
                try:
                    return int(y)
                except Exception:
                    # fallback: lexicographic order if year not numeric
                    return y or ""
            latest = max(entries, key=year_key)
            reduced[c][ind] = latest
    return reduced

# ----------------- Fallback: placeholder for IMF/COFER or other API -----------------
def fetch_from_imf_cofer(country: str, indicator: str) -> Optional[Dict[str, Any]]:
    # Platzhalter: implementiere echten Abruf hier, falls verfügbar.
    return None

# ----------------- Country codes loader -----------------
def load_country_codes(path: str = COUNTRY_CODES_FILE) -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning("Country codes file %s not found", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Fehler beim Laden von %s: %s", path, e)
        return {}

# ----------------- Monatsregeln (neu) -----------------
def apply_monthly_rules(indicator: str, snapshot: Dict[str, Any]) -> None:
    """
    Ergänzt snapshot um monatliche Ableitungen oder zusätzliche Felder.
    Modifiziert snapshot in-place.
    """
    val = snapshot.get("value")
    if val is None:
        return

    # lineare Monatsableitung für nominale Jahreswerte (USD)
    if indicator == "NE.IMP.GNFS.CD":
        snapshot["monthly_imports_usd"] = val / 12.0
    elif indicator == "FI.RES.TOTL":
        snapshot["monthly_reserves_usd"] = val / 12.0
    elif indicator == "NY.GDP.MKTP.CD":
        snapshot["monthly_gdp_usd"] = val / 12.0
    elif indicator == "NE.EXP.GNFS.CD":
        snapshot["monthly_exports_usd"] = val / 12.0
    elif indicator == "BX.KLT.DINV.CD.WD":
        snapshot["monthly_fdi_net_usd"] = val / 12.0

    # Für Wachstumsraten / Prozentangaben: dokumentiere latest_annual_change
    if indicator in ("FP.CPI.TOTL.ZG", "GC.XPN.TOTL.GD.ZS"):
        snapshot["latest_annual_change"] = val

# ----------------- Preset-Building mit Monatswerten und Fallback -----------------
def build_preset(country_code: str, indicators: List[str], cache: Dict[str, Any], fallback_data: Dict[str, Any], country_codes: Dict[str, Any]) -> Dict[str, Any]:
    cc = country_codes.get(country_code, {})
    preset = {
        "name": f"preset_{country_code}",
        "description": f"Preset für Land {country_code}",
        "version": "1.0",
        "indicator_snapshot": {},
        "metadata": {
            "created_by": "auto-generator",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "country_info": {
                "alpha2": country_code,
                "alpha3": cc.get("alpha3"),
                "numeric": cc.get("numeric"),
                "country_de": cc.get("country_de"),
                "country_en": cc.get("country_en"),
                "timezone": cc.get("timezone"),
                "currency": cc.get("currency")
            }
        }
    }

    for ind in indicators:
        key = ind.replace(".", "_")
        # Validierung
        if not validate_indicator(ind, cache):
            logger.warning("Indikator %s ist ungültig oder nicht verfügbar. Versuche Fallback.", ind)
            snapshot = {"value": None, "year": None, "source": "missing", "indicator": ind, "note": "invalid_indicator"}
            fb = None
            if USE_FALLBACK:
                fb = fallback_data.get(country_code, {}).get(ind) or fetch_from_imf_cofer(country_code, ind)
            if fb:
                snapshot["value"] = fb.get("value")
                snapshot["year"] = fb.get("year")
                snapshot["source"] = fb.get("source", "fallback")
                snapshot["note"] = "from_fallback"
                # country metadata
                if cc:
                    snapshot["country_currency"] = cc.get("currency")
                    snapshot["country_timezone"] = cc.get("timezone")
                apply_monthly_rules(ind, snapshot)
            preset["indicator_snapshot"][key] = snapshot
            cache[f"{country_code}:{ind}"] = snapshot
            continue

        # Normaler WB-Abruf
        res = fetch_worldbank_indicator(country_code, ind)
        snapshot = {"value": None, "year": None, "source": None, "indicator": ind}
        if res["status"] == "ok":
            entry = latest_value_from_data(res["data"])
            if entry:
                snapshot["value"] = entry.get("value")
                snapshot["year"] = entry.get("date")
                snapshot["source"] = "WB"
                if cc:
                    snapshot["country_currency"] = cc.get("currency")
                    snapshot["country_timezone"] = cc.get("timezone")
                apply_monthly_rules(ind, snapshot)
                logger.info("Got %s %s -> %s (year %s)", country_code, ind, snapshot["value"], snapshot.get("year"))
            else:
                snapshot["source"] = "WB_empty"
                snapshot["note"] = "no_values"
                logger.info("WB liefert keine Werte für %s %s", country_code, ind)
                if USE_FALLBACK:
                    fb = fallback_data.get(country_code, {}).get(ind) or fetch_from_imf_cofer(country_code, ind)
                    if fb:
                        snapshot["value"] = fb.get("value")
                        snapshot["year"] = fb.get("year")
                        snapshot["source"] = fb.get("source", "fallback")
                        snapshot["note"] = "wb_empty_used_fallback"
                        if cc:
                            snapshot["country_currency"] = cc.get("currency")
                            snapshot["country_timezone"] = cc.get("timezone")
                        apply_monthly_rules(ind, snapshot)
        elif res["status"] == "empty":
            snapshot["source"] = "WB_empty"
            snapshot["note"] = "empty"
            logger.info("WB empty für %s %s", country_code, ind)
            if USE_FALLBACK:
                fb = fallback_data.get(country_code, {}).get(ind) or fetch_from_imf_cofer(country_code, ind)
                if fb:
                    snapshot["value"] = fb.get("value")
                    snapshot["year"] = fb.get("year")
                    snapshot["source"] = fb.get("source", "fallback")
                    snapshot["note"] = "wb_empty_used_fallback"
                    if cc:
                        snapshot["country_currency"] = cc.get("currency")
                        snapshot["country_timezone"] = cc.get("timezone")
                    apply_monthly_rules(ind, snapshot)
        else:
            snapshot["source"] = "WB_error"
            snapshot["note"] = res.get("message") or res.get("raw")
            logger.warning("WB error für %s %s: %s", country_code, ind, snapshot["note"])
            if USE_FALLBACK:
                fb = fallback_data.get(country_code, {}).get(ind) or fetch_from_imf_cofer(country_code, ind)
                if fb:
                    snapshot["value"] = fb.get("value")
                    snapshot["year"] = fb.get("year")
                    snapshot["source"] = fb.get("source", "fallback")
                    snapshot["note"] = "wb_error_used_fallback"
                    if cc:
                        snapshot["country_currency"] = cc.get("currency")
                        snapshot["country_timezone"] = cc.get("timezone")
                    apply_monthly_rules(ind, snapshot)

        preset["indicator_snapshot"][key] = snapshot
        cache[f"{country_code}:{ind}"] = snapshot

    return preset

# ----------------- Validierung der erzeugten Presets (gewünscht) -----------------
def validate_generated_presets(schema_path="scripts/preset_schema.json"):
    import glob, json
    from jsonschema import validate, ValidationError
    schema = json.load(open(schema_path,"r",encoding="utf-8"))
    errs = 0
    for p in glob.glob("presets/*.json"):
        d = json.load(open(p,"r",encoding="utf-8"))
        try:
            validate(instance=d, schema=schema)
            print("OK:", p)
        except ValidationError as e:
            errs += 1
            print("INVALID:", p, e.message)
    if errs:
        raise SystemExit(f"{errs} invalid preset(s)")

# ----------------- CLI / Main -----------------
def main(validate_only: bool = False):
    indicators = load_indicators()
    logger.info("Indikatoren: %s", indicators)
    cache = load_cache()
    fallback_data = load_fallback_csv(FALLBACK_CSV) if USE_FALLBACK else {}
    country_codes = load_country_codes()

    if validate_only:
        logger.info("Validierungsmodus: prüfe Indikatoren und beende.")
        for ind in indicators:
            ok = validate_indicator(ind, cache)
            logger.info("Indicator %s valid=%s", ind, ok)
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    written = []
    for c in COUNTRIES:
        try:
            logger.info("Processing %s", c)
            preset = build_preset(c, indicators, cache, fallback_data, country_codes)
            out_path = os.path.join(OUTPUT_DIR, f"preset_{c}.json")
            save_json(out_path, preset)
            written.append(f"preset_{c}")
            logger.info("Wrote %s", out_path)
        except Exception as e:
            logger.exception("Fehler beim Verarbeiten von %s: %s", c, e)

    save_cache(cache)
    logger.info("Wrote presets: %s", written)
    print("Wrote presets:", written)

if __name__ == "__main__":
    validate_only = os.environ.get("VALIDATE_ONLY", "0") == "1"
    main(validate_only=validate_only)
    # Optional: nach erfolgreichem Run Presets validieren
    # Entferne das Kommentar, wenn du immer validieren willst:
    # validate_generated_presets("scripts/preset_schema.json")
