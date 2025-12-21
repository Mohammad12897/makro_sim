# src/etl/transforms.py
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from .fetchers import DataAPI
from .persistence import store_indicator

# ----------------- Hilfsfunktionen -----------------
def clamp(x, lo, hi):
    try:
        xv = float(x)
    except Exception:
        return lo
    return max(lo, min(hi, xv))

# ----------------- bestehende Funktion: fetch_reserves -----------------
def fetch_reserves(api: DataAPI):
    """
    Holt Reserves- und Import-Zeitreihen vom API-Objekt, normalisiert und speichert
    einen Indikator 'Reserven_Monate' lokal via store_indicator.
    Rückgabe: (Series, path, flag)
    """
    # Unterstützte API-Keys: "central_bank_reserves" und "monthly_imports"
    cb = api.get("central_bank_reserves")
    imp = api.get("monthly_imports")

    def normalize(df, value_col):
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        if "ts" not in df.columns:
            # falls erste Spalte Zeitstempel ist
            df.rename(columns={df.columns[0]: "ts"}, inplace=True)
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=["ts", value_col]).sort_values("ts")
        return df.set_index("ts").resample("ME").last()

    df_res = normalize(cb, "reserves_usd")
    df_imp = normalize(imp, "imports_usd")
    if df_res.empty or df_imp.empty:
        s = pd.Series(dtype=float)
        flag = "empty"
        path = store_indicator("Reserven_Monate", s, source="CB_API", quality_flag=flag)
        return s, path, flag

    df = df_res.join(df_imp, how="inner")
    denom = np.maximum(1.0, df["imports_usd"].values)
    s = pd.Series(df["reserves_usd"].values / denom, index=df.index)
    flag = "ok" if len(s) > 0 else "empty"
    path = store_indicator("Reserven_Monate", s, source="CB_API", quality_flag=flag)
    return s, path, flag

# ----------------- Neue Funktion: map_indicators_to_preset -----------------
def map_indicators_to_preset(indicators: dict, country_iso: str = "XX"):
    """
    Mappt rohe Indikatoren auf das Preset-Format (PARAM_SLIDERS).
    Erwartet keys in `indicators` wie:
      - reserves_usd (float | None)
      - monthly_imports_usd (float | None)
      - cofer_usd_share (0..1)
      - cofer_rmb_share (0..1)
      - gold_share (0..1)
      - external_debt_to_gdp (percent, float | None)
      - short_term_debt_to_reserves (float | None)
      - sanktions_proxy, alternativnetz, cbdc_proxy, liquidity_premium, democracy_index, ...
    Liefert: (preset_dict, metadata_dict)
    """
    preset = {}
    meta = {
        "source_map": {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "confidence": indicators.get("confidence", "low"),
        "country": country_iso,
        "notes": ""
    }

    # --- Reserven Monate (Reserven_Monate) ---
    reserves = indicators.get("reserves_usd")
    monthly = indicators.get("monthly_imports_usd")
    if reserves is None or monthly is None or monthly == 0:
        preset["Reserven_Monate"] = 0
        # confidence wird weiter unten ggf. überschrieben
        meta["source_map"]["Reserven_Monate"] = indicators.get("reserves_source", "missing")
    else:
        preset["Reserven_Monate"] = int(clamp(reserves / monthly, 0, 24))
        meta["source_map"]["Reserven_Monate"] = indicators.get("reserves_source", "local/WB")

    # --- USD Dominanz (COFER) ---
    usd_share = indicators.get("cofer_usd_share", 0.6)
    preset["USD_Dominanz"] = clamp(usd_share, 0.0, 1.0)
    meta["source_map"]["USD_Dominanz"] = indicators.get("cofer_source", "default_heuristic")

    # --- RMB Akzeptanz ---
    rmb_share = indicators.get("cofer_rmb_share", 0.0)
    preset["RMB_Akzeptanz"] = clamp(rmb_share, 0.0, 1.0)
    meta["source_map"]["RMB_Akzeptanz"] = indicators.get("cofer_source", "default_heuristic")

    # --- Golddeckung ---
    gold_share = indicators.get("gold_share", 0.0)
    preset["Golddeckung"] = clamp(gold_share, 0.0, 1.0)
    meta["source_map"]["Golddeckung"] = indicators.get("cofer_source", "default_heuristic")

    # --- Verschuldung (external_debt_to_gdp) skaliert auf 0..2 ---
    ed_gdp = indicators.get("external_debt_to_gdp")
    if ed_gdp is None:
        preset["verschuldung"] = 0.0
    else:
        preset["verschuldung"] = clamp(ed_gdp / 100.0, 0.0, 2.0)
    meta["source_map"]["verschuldung"] = indicators.get("debt_source", "missing")

    # --- FX Schockempfindlichkeit ---
    short_term_ratio = indicators.get("short_term_debt_to_reserves")
    if short_term_ratio is None:
        # fallback heuristic: external_debt_to_gdp relative zu (reserves / (monthly*6))
        if reserves and monthly:
            denom = max(1.0, reserves / (monthly * 6.0))
            short_term_ratio = (indicators.get("external_debt_to_gdp") or 0.0) / max(1.0, denom)
        else:
            short_term_ratio = 0.0
    preset["FX_Schockempfindlichkeit"] = clamp(short_term_ratio, 0.0, 2.0)
    meta["source_map"]["FX_Schockempfindlichkeit"] = "derived"

    # --- Sanktions Exposure (Proxy) ---
    preset["Sanktions_Exposure"] = clamp(indicators.get("sanktions_proxy", 0.05), 0.0, 1.0)
    meta["source_map"]["Sanktions_Exposure"] = indicators.get("sanktions_source", "proxy")

    # --- Alternativnetz Abdeckung ---
    preset["Alternativnetz_Abdeckung"] = clamp(indicators.get("alternativnetz", 0.3), 0.0, 1.0)
    meta["source_map"]["Alternativnetz_Abdeckung"] = indicators.get("alternativnetz_source", "proxy")

    # --- CBDC Nutzung, Liquiditätsaufschlag, Zugangsresilienz, Demokratie ---
    preset["CBDC_Nutzung"] = clamp(indicators.get("cbdc_proxy", 0.0), 0.0, 1.0)
    preset["Liquiditaetsaufschlag"] = clamp(indicators.get("liquidity_premium", 0.02), 0.0, 0.2)
    preset["Zugangsresilienz"] = clamp(1.0 - preset["Sanktions_Exposure"], 0.0, 1.0)
    preset["demokratie"] = clamp(indicators.get("democracy_index", 0.7), 0.0, 1.0)

    # --- Innovation / Fachkräfte / Stabilität / Energie (Proxies) ---
    preset["innovation"] = clamp(indicators.get("innovation_proxy", 0.5), 0.0, 1.0)
    preset["fachkraefte"] = clamp(indicators.get("labor_skill_proxy", 0.5), 0.0, 1.0)
    preset["stabilitaet"] = clamp(indicators.get("stability_proxy", 0.6), 0.0, 1.0)
    preset["energie"] = clamp(indicators.get("energy_cost_proxy", 0.5), 0.0, 1.0)

    # --- Finales Confidence-Handling ---
    # Wenn indicators bereits eine confidence enthält, nutze diese; sonst heuristisch bestimmen
    if "confidence" in indicators:
        meta["confidence"] = indicators.get("confidence")
    else:
        missing_count = sum(1 for k in ("reserves_usd", "monthly_imports_usd", "cofer_usd_share", "external_debt_to_gdp") if indicators.get(k) in (None, 0))
        meta["confidence"] = "low" if missing_count >= 2 else ("medium" if missing_count == 1 else "high")

    return preset, meta
