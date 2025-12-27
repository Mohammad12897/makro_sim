#!/usr/bin/env python3
# coding: utf-8
"""
generate_presets.py
- Erzeugt presets/preset_<COUNTRY>.json aus World Bank + Fallbacks
- Wendet Monatsregeln an
- Speichert Cache und Logs
- Ruft run_validation aus scripts/validate_presets.py auf (wenn verfügbar)
- Quarantänisiert nur bei kritischen Validierungsfehlern (Schema oder kritische cross_checks)
"""
from __future__ import annotations
import os
import json
import time
import logging
import requests
import glob
import shutil
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# jsonschema wird nur in optionalen Validierungsfunktionen benötigt
try:
    from jsonschema import validate as js_validate, ValidationError
except Exception:
    js_validate = None
    ValidationError = Exception

# Versuche, run_validation importierbar zu machen
try:
    from scripts.validate_presets import run_validation
except Exception:
    run_validation = None  # Fallback: CLI call möglich

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
COUNTRIES = ["DE", "CN", "US", "IR", "BR", "IN", "GR", "FR", "GB"]
USE_FALLBACK = True
FALLBACK_CSV = "scripts/fallback_data.csv"
COUNTRY_CODES_FILE = "scripts/country_codes.json"
INVALID_LOG = "scripts/invalid_indicators.json"
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
                    parts = [p.strip() for p in s.split(",")]
                    if len(parts) >= 2 and parts[1]:
                        inds.append(parts[1])
                    else:
                        inds.append(parts[0])
        return inds
    logger.info("Keine Indikator-Datei gefunden, verwende eingebaute Liste")
    return [
        "FI.RES.TOTL.MO",
        "NE.IMP.GNFS.CD",
        "DT.DOD.DECT.CD",
        "NY.GDP.MKTP.CD",
        "FP.CPI.TOTL.ZG",
        "NE.EXP.GNFS.CD",
        "BX.KLT.DINV.CD.WD",
        "GC.XPN.TOTL.GD.ZS",
    ]

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

def save_preset_atomic(path: str, data: Dict[str, Any]) -> None:
    tmp_dir = os.path.join(os.path.dirname(path), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, os.path.basename(path))
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp_path, path)

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

    if not valid:
        fails = cache.get("fail_counts", {})
        fails[indicator] = fails.get(indicator, 0) + 1
        cache["fail_counts"] = fails
        if fails[indicator] >= 3:
            bad = {}
            if os.path.exists(INVALID_LOG):
                try:
                    with open(INVALID_LOG, "r", encoding="utf-8") as f:
                        bad = json.load(f)
                except Exception:
                    bad = {}
            bad[indicator] = {"first_failed_at": now, "reason": "wb_invalid", "fail_count": fails[indicator]}
            try:
                with open(INVALID_LOG, "w", encoding="utf-8") as f:
                    json.dump(bad, f, ensure_ascii=False, indent=2)
                logger.warning("Auto-skip: %s marked as invalid and logged in %s", indicator, INVALID_LOG)
            except Exception as e:
                logger.warning("Could not write invalid log %s: %s", INVALID_LOG, e)

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

# ----------------- Fallback CSV loader -----------------
def load_fallback_csv(path: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    fallback = {}
    if not os.path.exists(path):
        return {}
    import csv as _csv
    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
        f.seek(0)
        has_header = "," in first and not first.strip().split(",")[0].isalpha()
        f.seek(0)
        if has_header:
            reader = _csv.DictReader(f)
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
        else:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = [p.strip() for p in s.split(",")]
                if len(parts) < 4:
                    continue
                c, ind, year, val = parts[0], parts[1], parts[2], parts[3]
                src = parts[4] if len(parts) > 4 else "fallback_csv"
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
                    return y or ""
            latest = max(entries, key=year_key)
            reduced[c][ind] = latest
    return reduced

# ----------------- Fallback placeholder for IMF/COFER -----------------
def fetch_from_imf_cofer(country: str, indicator: str) -> Optional[Dict[str, Any]]:
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

# ----------------- Monatsregeln -----------------
def apply_monthly_rules(indicator: str, snapshot: Dict[str, Any]) -> None:
    val = snapshot.get("value")
    if val is None:
        return
    if indicator == "NE.IMP.GNFS.CD":
        snapshot["monthly_imports_usd"] = val / 12.0
    elif indicator in ("FI.RES.TOTL", "FI.RES.TOTL.MO"):
        # If FI.RES.TOTL.MO is provided, keep it; if FI.RES.TOTL (USD) provided, compute months elsewhere
        if indicator == "FI.RES.TOTL":
            snapshot["monthly_reserves_usd"] = val / 12.0
    elif indicator == "NY.GDP.MKTP.CD":
        snapshot["monthly_gdp_usd"] = val / 12.0
    elif indicator == "NE.EXP.GNFS.CD":
        snapshot["monthly_exports_usd"] = val / 12.0
    elif indicator == "BX.KLT.DINV.CD.WD":
        snapshot["monthly_fdi_net_usd"] = val / 12.0
    if indicator in ("FP.CPI.TOTL.ZG", "GC.XPN.TOTL.GD.ZS"):
        snapshot["latest_annual_change"] = val

# ----------------- Preset-Building -----------------
def build_preset(country_code: str, indicators: List[str], cache: Dict[str, Any],
                 fallback_data: Dict[str, Any], country_codes: Dict[str, Any]) -> Dict[str, Any]:
    cc = country_codes.get(country_code, {}) or {}
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
        if os.path.exists(INVALID_LOG):
            try:
                invalids = set(json.load(open(INVALID_LOG, "r", encoding="utf-8")).keys())
            except Exception:
                invalids = set()
            if ind in invalids:
                logger.info("Skipping indicator %s because it is marked invalid", ind)
                continue

        key = ind.replace(".", "_")
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
                if cc:
                    snapshot["country_currency"] = cc.get("currency")
                    snapshot["country_timezone"] = cc.get("timezone")
                apply_monthly_rules(ind, snapshot)
            preset["indicator_snapshot"][key] = snapshot
            cache[f"{country_code}:{ind}"] = snapshot
            continue

        res = fetch_worldbank_indicator(country_code, ind)
        snapshot = {"value": None, "year": None, "source": None, "indicator": ind}
        if res.get("status") == "ok":
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
        elif res.get("status") == "empty":
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

# ----------------- Validierung der erzeugten Presets (optional) -----------------
def handle_validation_report(report_path: str = "reports/validation_report.json", quarantine_dir: str = "presets/quarantine"):
    """
    Read report_path and move only presets with critical validation errors to quarantine.
    'stale' errors are treated as warnings and do not trigger quarantine.
    """
    if not os.path.exists(report_path):
        logger.info("Validation report not found: %s", report_path)
        return
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            rep = json.load(f)
    except Exception as e:
        logger.error("Could not read validation report %s: %s", report_path, e)
        return

    os.makedirs(quarantine_dir, exist_ok=True)
    critical_checks = {"trade_vs_gdp"}

    for r in rep.get("reports", []):
        status = r.get("status")
        pfile = r.get("preset_file")
        if not pfile or not os.path.exists(pfile):
            continue
        errors = r.get("errors", [])
        is_critical = False
        for e in errors:
            if e.get("type") == "schema":
                is_critical = True
                break
            if e.get("type") == "cross_check" and e.get("check") in critical_checks:
                is_critical = True
                break
        if is_critical:
            dest = os.path.join(quarantine_dir, os.path.basename(pfile))
            try:
                shutil.move(pfile, dest)
                logger.warning("Moved %s to quarantine due to status=%s", pfile, status)
                with open("reports/audit.jsonl", "a", encoding="utf-8") as af:
                    af.write(json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "action": "quarantine_preset",
                        "file": pfile,
                        "status": status
                    }) + "\n")
            except Exception as ex:
                logger.error("Failed to move %s to quarantine: %s", pfile, ex)
        else:
            # write a warning audit entry for non-critical issues (including stale)
            with open("reports/audit.jsonl", "a", encoding="utf-8") as af:
                af.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "validation_warning",
                    "file": pfile,
                    "status": status,
                    "errors": errors
                }) + "\n")

def handle_validation_report_from_result(result: Dict[str, Any], quarantine_dir: str = "presets/quarantine"):
    """
    Process validation result dict returned by run_validation.
    Move only presets with critical errors to quarantine.
    Treat 'stale' as warning (do not quarantine).
    Critical errors:
      - any error with type == 'schema'
      - cross_check errors for checks considered critical (e.g., 'trade_vs_gdp')
    """
    reports = result.get("reports", [])
    os.makedirs(quarantine_dir, exist_ok=True)
    critical_checks = {"trade_vs_gdp"}  # extend if needed

    for r in reports:
        pfile = r.get("preset_file")
        if not pfile or not os.path.exists(pfile):
            continue
        errors = r.get("errors", [])
        is_critical = False
        for e in errors:
            etype = e.get("type")
            if etype == "schema":
                is_critical = True
                break
            if etype == "cross_check":
                check = e.get("check")
                if check in critical_checks:
                    is_critical = True
                    break
        if is_critical:
            dest = os.path.join(quarantine_dir, os.path.basename(pfile))
            try:
                shutil.move(pfile, dest)
                logger.warning("Moved %s to quarantine due to critical validation errors", pfile)
                with open("reports/audit.jsonl", "a", encoding="utf-8") as af:
                    af.write(json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "action": "quarantine_preset",
                        "file": pfile,
                        "status": r.get("status"),
                        "reason": "critical_validation"
                    }) + "\n")
            except Exception as ex:
                logger.error("Failed to move %s to quarantine: %s", pfile, ex)
        else:
            # non-critical: keep file in place and write a warning audit entry
            with open("reports/audit.jsonl", "a", encoding="utf-8") as af:
                af.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "validation_warning",
                    "file": pfile,
                    "status": r.get("status"),
                    "errors": r.get("errors")
                }) + "\n")

# ----------------- CLI / Main -----------------
def main(validate_only: bool = False, no_validate: bool = False):
    indicators = load_indicators()

    invalids = set()
    if os.path.exists(INVALID_LOG):
        try:
            invalids = set(json.load(open(INVALID_LOG, "r", encoding="utf-8")).keys())
        except Exception:
            invalids = set()
    if invalids:
        logger.info("Skipping permanently invalid indicators: %s", ", ".join(sorted(invalids)))
        indicators = [i for i in indicators if i not in invalids]

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
            save_preset_atomic(out_path, preset)
            written.append(f"preset_{c}")
            logger.info("Wrote %s", out_path)
        except Exception as e:
            logger.exception("Fehler beim Verarbeiten von %s: %s", c, e)

    save_cache(cache)
    logger.info("Wrote presets: %s", written)
    print("Wrote presets:", written)

    # optional: run validation (use run_validation result to avoid race conditions)
    if not no_validate:
        try:
            if run_validation:
                result = run_validation(presets_dir=OUTPUT_DIR, schema_path="scripts/preset_schema.json", out_dir="reports")
                logger.info("Validation result: %s", result.get("summary", {}))
                handle_validation_report_from_result(result, quarantine_dir=os.path.join(OUTPUT_DIR, "quarantine"))
            else:
                # fallback to CLI invocation (legacy)
                import subprocess
                subprocess.run(["python", "scripts/validate_presets.py", "--presets", OUTPUT_DIR, "--schema", "scripts/preset_schema.json", "--out", "reports"], check=False)
                handle_validation_report("reports/validation_report.json", quarantine_dir=os.path.join(OUTPUT_DIR, "quarantine"))
        except Exception as e:
            logger.error("Validation failed: %s", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate presets and optionally validate them.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate configured indicators and exit")
    parser.add_argument("--no-validate", action="store_true", help="Do not run validation after generation")
    args = parser.parse_args()

    # Backwards compatible env var
    validate_only_env = os.environ.get("VALIDATE_ONLY", "0") == "1"
    validate_only = args.validate_only or validate_only_env

    main(validate_only=validate_only, no_validate=args.no_validate)
