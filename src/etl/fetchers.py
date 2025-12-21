# src/etl/fetchers.py
import json
import csv
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

class DataAPI:
    def __init__(self, country_iso="DE", reporter_code="276", cache_dir=Path("data")):
        self.country_iso = country_iso.upper()
        self.reporter_code = reporter_code
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # optional test overrides (set externally for quick tests)
        self.test_overrides = None

    # ----------------- simple dummy fallbacks (kept for robustness) -----------------
    def get_central_bank_reserves(self, start="2015-01"):
        """
        Erzeugt eine monatliche Zeitreihe (ME) von Dummy-Reserven als Fallback.
        Achtung: erzeugt naive Timestamps (ohne tz) damit pd.date_range keine TZ-Fehler wirft.
        """
        # parse start in ein pandas Timestamp (naive)
        try:
            start_ts = pd.to_datetime(start, errors="coerce")
            if pd.isna(start_ts):
                start_ts = pd.Timestamp(year=2015, month=1, day=31)
            # ensure naive (drop tz if present)
            if getattr(start_ts, "tzinfo", None) is not None:
                start_ts = start_ts.tz_convert(None).tz_localize(None)
        except Exception:
            start_ts = pd.Timestamp(year=2015, month=1, day=31)

        # end as naive Timestamp (no timezone)
        end_ts = pd.Timestamp.now(tz=None)

        # build monthly-end range
        rng = pd.date_range(start=start_ts, end=end_ts, freq="ME")
        # create a simple linear dummy series (adjust as needed)
        reserves = np.linspace(200e9, 250e9, len(rng)) if len(rng) > 0 else np.array([200e9])
        return pd.DataFrame({"ts": rng, "reserves_usd": reserves})

    def get_monthly_imports(self, start_year=2015):
        dates, values = [], []
        end_year = datetime.now(timezone.utc).year
        for y in range(int(start_year), end_year+1):
            for m in range(1,13):
                ts = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(1)
                dates.append(ts)
                values.append(1e11 + 2e10 * np.sin(m/12 * np.pi))
        df = pd.DataFrame({"ts": dates, "imports_usd": values})
        return df

    # ----------------- World Bank helper with logging -----------------
    def fetch_worldbank_indicator(self, indicator_id, per_page=100):
        """
        Robuster World Bank fetcher:
        - loggt URL + Status + raw head
        - prüft Format und überspringt fehlerhafte Einträge
        - gibt DataFrame(date,value) aufsteigend zurück
        """
        try:
            url = f"https://api.worldbank.org/v2/country/{self.country_iso}/indicator/{indicator_id}"
            params = {"format":"json", "per_page": per_page}
            r = requests.get(url, params=params, timeout=20)
            # Debug logging: URL, Status, raw head
            print("WB GET", r.url, "status", r.status_code)
            print("WB raw head:", (r.text or "")[:800])
            r.raise_for_status()
            data = r.json()

            # Erwartetes Format: [meta, [records...]]
            if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
                print(f"[fetch_worldbank_indicator] unexpected format for {self.country_iso} {indicator_id}")
                return pd.DataFrame(columns=["date","value"])

            records = data[1]
            rows = []
            for i, rec in enumerate(records):
                try:
                    if not isinstance(rec, dict):
                        continue
                    date_raw = rec.get("date")
                    val_raw = rec.get("value")
                    if val_raw is None:
                        continue
                    # parse date: World Bank often uses year strings
                    try:
                        dt = pd.to_datetime(str(date_raw), format="%Y", errors="coerce")
                        if pd.isna(dt):
                            dt = pd.to_datetime(date_raw, errors="coerce")
                    except Exception:
                        dt = pd.to_datetime(date_raw, errors="coerce")
                    if pd.isna(dt):
                        continue
                    rows.append({"date": dt, "value": float(val_raw)})
                except Exception as rec_err:
                    print(f"[fetch_worldbank_indicator] skip record #{i} for {indicator_id}: {rec_err}")
                    continue

            if not rows:
                return pd.DataFrame(columns=["date","value"])
            df = pd.DataFrame(rows).dropna().sort_values("date")
            return df
        except Exception as e:
            print(f"[fetch_worldbank_indicator] error for {self.country_iso} {indicator_id}: {e}")
            return pd.DataFrame(columns=["date","value"])

    # ----------------- COFER / currency shares (local file or defaults) -----------------
    def get_cofer_share(self):
        """
        Versucht lokale COFER-Dateien (JSON/CSV) zu lesen, sonst differenzierte Defaults.
        Rückgabe: dict e.g. {'USD':0.6, 'RMB':0.02, 'GOLD_share':0.03}
        """
        # 1) local JSON
        p_json = self.cache_dir / f"cofer_{self.country_iso}.json"
        if p_json.exists():
            try:
                return json.loads(p_json.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 2) local CSV
        p_csv = self.cache_dir / f"cofer_{self.country_iso}.csv"
        if p_csv.exists():
            try:
                out = {}
                with open(p_csv, newline='', encoding='utf-8') as fh:
                    reader = csv.DictReader(fh)
                    for r in reader:
                        cur = (r.get("currency") or r.get("cur") or r.get("code") or "").upper()
                        share = r.get("share") or r.get("value")
                        if cur and share is not None:
                            try:
                                out[cur] = float(share)
                            except Exception:
                                continue
                s = sum(out.values())
                if s > 0:
                    for k in out: out[k] = out[k] / s
                return out
            except Exception:
                pass

        # 3) Differenzierte defaults (more realistic per country)
        defaults_by_country = {
            "US": {"USD": 0.85, "RMB": 0.01, "GOLD_share": 0.02},
            "CN": {"USD": 0.50, "RMB": 0.12, "GOLD_share": 0.03},
            "DE": {"USD": 0.55, "RMB": 0.02, "GOLD_share": 0.04},
            "BR": {"USD": 0.70, "RMB": 0.01, "GOLD_share": 0.05},
            "IR": {"USD": 0.30, "RMB": 0.00, "GOLD_share": 0.15},
            "IN": {"USD": 0.65, "RMB": 0.02, "GOLD_share": 0.02},
        }
        return defaults_by_country.get(self.country_iso, {"USD": 0.6, "RMB": 0.02, "GOLD_share": 0.03})

    # ----------------- Reserves timeseries (local -> WB -> empty) -----------------
    def get_reserves_timeseries(self):
        p_csv = self.cache_dir / f"reserves_{self.country_iso}.csv"
        p_json = self.cache_dir / f"reserves_{self.country_iso}.json"
        if p_csv.exists():
            try:
                df = pd.read_csv(p_csv, parse_dates=["ts"])
                if "reserves_usd" not in df.columns:
                    raise ValueError("missing reserves_usd column in local CSV")
                return df[["ts", "reserves_usd"]]
            except Exception as e:
                print(f"[get_reserves_timeseries] failed reading {p_csv}: {e}")

        if p_json.exists():
            try:
                j = json.loads(p_json.read_text(encoding="utf-8"))
                df = pd.DataFrame(j)
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
                if "reserves_usd" not in df.columns:
                    raise ValueError("missing reserves_usd in local JSON")
                return df[["ts", "reserves_usd"]]
            except Exception as e:
                print(f"[get_reserves_timeseries] failed reading {p_json}: {e}")

        # 2) try World Bank (annual -> monthly)
        df_wb = self.fetch_worldbank_indicator("FI.RES.TOTL")
        if df_wb.empty:
            # return empty DataFrame so caller can set None and confidence low
            return pd.DataFrame(columns=["ts", "reserves_usd"])
        # df_wb has columns ['date','value']
        df_monthly = df_wb.set_index("date").resample("ME").ffill().reset_index().rename(columns={"date":"ts","value":"reserves_usd"})
        return df_monthly

    def get_monthly_imports_from_wb(self):
        df = self.fetch_worldbank_indicator("NE.IMP.GNFS.CD")
        if df.empty:
            return self.get_monthly_imports()
        df["year"] = df["date"].dt.year
        rows = []
        for _, row in df.iterrows():
            year = int(row["year"])
            annual = float(row["value"])
            monthly = annual / 12.0
            for m in range(1,13):
                ts = pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd(1)
                rows.append({"ts": ts, "imports_usd": monthly})
        return pd.DataFrame(rows)

    # ----------------- High-level snapshot builder -----------------
    def build_indicators_snapshot(self):
        """
        Liefert ein Dict mit wichtigsten Indikatoren (roh) und Quellenhinweisen.
        Unterstützt self.test_overrides für schnelle Tests.
        """
        # if test overrides provided, use them (quick test mode)
        if getattr(self, "test_overrides", None):
            print(f"[DataAPI] using test_overrides for {self.country_iso}")
            inds = dict(self.test_overrides)
            # ensure keys exist
            inds.setdefault("reserves_source", "test_override")
            inds.setdefault("imports_source", "test_override")
            inds.setdefault("cofer_source", "test_override")
            inds.setdefault("external_debt_to_gdp", None)
            return inds

        indicators = {}

        # reserves (local -> WB -> empty)
        res_df = self.get_reserves_timeseries()
        if not res_df.empty:
            indicators["reserves_usd"] = float(res_df["reserves_usd"].iloc[-1])
            indicators["reserves_source"] = "local/WB"
        else:
            indicators["reserves_usd"] = None
            indicators["reserves_source"] = "missing"

        # monthly imports
        imp_df = self.get_monthly_imports_from_wb()
        if not imp_df.empty:
            indicators["monthly_imports_usd"] = float(imp_df["imports_usd"].iloc[-1])
            indicators["imports_source"] = "WB"
        else:
            indicators["monthly_imports_usd"] = None
            indicators["imports_source"] = "missing"

        # cofer
        cofer = self.get_cofer_share()
        indicators["cofer_usd_share"] = float(cofer.get("USD", 0.6))
        indicators["cofer_rmb_share"] = float(cofer.get("RMB", 0.0))
        indicators["gold_share"] = float(cofer.get("GOLD_share", cofer.get("GOLD", 0.0)))
        indicators["cofer_source"] = "local/heuristic" if (self.cache_dir.joinpath(f"cofer_{self.country_iso}.json").exists() or self.cache_dir.joinpath(f"cofer_{self.country_iso}.csv").exists()) else "default_heuristic"

        # external debt to gdp
        ext_debt = self.fetch_worldbank_indicator("DT.DOD.DECT.GN.ZS")
        if not ext_debt.empty:
            indicators["external_debt_to_gdp"] = float(ext_debt["value"].iloc[-1])
            indicators["debt_source"] = "WB"
        else:
            indicators["external_debt_to_gdp"] = None
            indicators["debt_source"] = "missing"

        # placeholders for proxies (can be enriched later)
        indicators.setdefault("short_term_debt_to_reserves", None)
        indicators.setdefault("sanktions_proxy", 0.05)
        indicators.setdefault("alternativnetz", 0.3)
        indicators.setdefault("cbdc_proxy", 0.0)
        indicators.setdefault("liquidity_premium", 0.02)
        indicators.setdefault("democracy_index", 0.7)
        indicators.setdefault("innovation_proxy", 0.5)
        indicators.setdefault("labor_skill_proxy", 0.5)
        indicators.setdefault("stability_proxy", 0.6)
        indicators.setdefault("energy_cost_proxy", 0.5)

        # confidence heuristic (compute after all indicators set)
        missing_count = sum(1 for k in ("reserves_usd","monthly_imports_usd","cofer_usd_share","external_debt_to_gdp") if indicators.get(k) in (None, 0))
        indicators["confidence"] = "low" if missing_count >= 2 else ("medium" if missing_count == 1 else "high")

        # debug print summary
        print(f"[build_indicators_snapshot] {self.country_iso} -> reserves:{indicators['reserves_usd']}, imports:{indicators['monthly_imports_usd']}, cofer_usd:{indicators['cofer_usd_share']}, ext_debt_to_gdp:{indicators['external_debt_to_gdp']}")
        return indicators

    # convenience: build preset (requires map_indicators_to_preset in transforms)
    def build_country_preset(self):
        """
        Baut ein Preset aus den Indikatoren und gibt (preset_dict, metadata) zurück.
        map_indicators_to_preset wird erwartet, ein Tupel (preset, meta) zurückzugeben.
        """
        inds = self.build_indicators_snapshot()
        from .transforms import map_indicators_to_preset
        preset, meta = map_indicators_to_preset(inds, country_iso=self.country_iso)

        # ensure preset contains Reserven_Monate even if map didn't set it
        reserves = inds.get("reserves_usd")
        monthly = inds.get("monthly_imports_usd")
        if reserves is None or monthly is None or monthly == 0:
            # leave mapping decision to map_indicators_to_preset but ensure a sensible default
            preset.setdefault("Reserven_Monate", 0)
            meta.setdefault("confidence", "low")
        else:
            preset.setdefault("Reserven_Monate", int(max(0, min(24, reserves / monthly))))

        # attach some metadata fields if not present
        meta.setdefault("country", self.country_iso)
        meta.setdefault("fetched_at", datetime.now(timezone.utc).isoformat())
        meta.setdefault("sources", {
            "reserves": inds.get("reserves_source"),
            "imports": inds.get("imports_source"),
            "cofer": inds.get("cofer_source"),
            "debt": inds.get("debt_source")
        })
        return preset, meta
