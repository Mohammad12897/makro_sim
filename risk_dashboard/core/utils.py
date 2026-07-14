# risk_dashboard/core/utils.py
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# optionaler Audit-Log (falls gewünscht)
_BASE_DIR = Path(__file__).resolve().parents[1]
_AUDIT_PATH = _BASE_DIR / "logs" / "utils_audit.jsonl"
_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

def _write_audit(entry: dict) -> None:
    entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with _AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- Ergänzende Hilfsfunktionen für Datums- und Preisnormalisierung ---
def get_latest_before(df: pd.DataFrame, date_col, target_date):
    import pandas as pd
    if df is None or df.empty:
        return None

    target_ts = pd.to_datetime(target_date, errors="coerce")
    if pd.isna(target_ts):
        return None

    # Index-Fallback
    if date_col is None or date_col == "index":
        idx = pd.to_datetime(df.index, errors="coerce")
        mask = idx <= target_ts
        if not mask.any():
            return None
        last_pos = [i for i, v in enumerate(mask) if v][-1]
        return df.iloc[last_pos]

    # Spaltenfall
    if date_col not in df.columns:
        return None
    s = pd.to_datetime(df[date_col], errors="coerce")
    mask = s <= target_ts
    if not mask.any():
        return None
    last_pos = [i for i, v in enumerate(mask) if v][-1]
    return df.iloc[last_pos]

def ensure_date_column(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """
    Stellt sicher, dass DataFrame eine Datums-Spalte hat.
    - Wenn date_col existiert: in datetime konvertieren.
    - Wenn Index datetime-like ist: Spalte erzeugen.
    """
    df = df.copy()
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        return df
    try:
        idx = pd.to_datetime(df.index)
        df[date_col] = idx
        return df
    except Exception:
        raise ValueError(f"ensure_date_column: Weder Spalte '{date_col}' noch datetime-Index vorhanden.")

def ensure_date_series(obj, date_col: str = "date") -> pd.Series:
    """
    Liefert eine Series mit datetime-Index.
    - Wenn obj Series: Index wird in datetime konvertiert.
    - Wenn obj DataFrame: versucht, 'date' zu verwenden oder Index zu konvertieren; gibt erste Spalte als Series zurück.
    """
    if isinstance(obj, pd.Series):
        s = obj.copy()
        s.index = pd.to_datetime(s.index, errors="coerce")
        return s.sort_index().dropna()
    if isinstance(obj, pd.DataFrame):
        df = obj.copy()
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.set_index(date_col)
        else:
            df.index = pd.to_datetime(df.index, errors="coerce")
        if df.shape[1] == 0:
            raise ValueError("ensure_date_series: DataFrame enthält keine Spalten.")
        s = df.iloc[:, 0].copy()
        s.index = pd.to_datetime(s.index, errors="coerce")
        return s.sort_index().dropna()
    raise TypeError("ensure_date_series erwartet pandas Series oder DataFrame.")

def normalize_price_df(df: pd.DataFrame, price_col: Optional[str] = None) -> pd.DataFrame:
    """
    Normalisiert Preis-DataFrames:
    - setzt Index auf Datum (falls 'date' vorhanden)
    - wählt eine Preisspalte (Adj Close > Close > first numeric)
    - sortiert, entfernt Duplikate
    Rückgabe: DataFrame mit einer Preis-Spalte als erste Spalte.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Falls 'date' Spalte vorhanden -> Index setzen
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date")
    else:
        df.index = pd.to_datetime(df.index, errors="coerce")

    # Wenn price_col explizit übergeben wurde, prüfe sie
    if price_col:
        if price_col in df.columns:
            out = df[[price_col]].copy()
            out.columns = [price_col]
        else:
            raise ValueError(f"normalize_price_df: Preis-Spalte '{price_col}' nicht gefunden.")
    else:
        # Heuristische Auswahl: Adj Close, Close, erste numerische Spalte
        for candidate in ["Adj Close", "Close", "adj_close", "close"]:
            if candidate in df.columns:
                out = df[[candidate]].copy()
                out.columns = [candidate]
                break
        else:
            # fallback: erste numerische Spalte
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                out = df[[numeric_cols[0]]].copy()
                out.columns = [numeric_cols[0]]
            else:
                # nichts gefunden
                raise ValueError("normalize_price_df: Keine geeignete Preisspalte gefunden.")

    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out

def validate_prophet_input(df: pd.DataFrame) -> pd.DataFrame:
    """
    Minimalvalidierung für Prophet: gibt DataFrame mit Spalten 'ds' und 'y' zurück.
    Erwartet: Datumsspalte 'date' oder Index; Zielspalte 'value' oder erste numerische Spalte.
    """
    if df is None or df.empty:
        raise ValueError("validate_prophet_input: leeres DataFrame")

    df = df.copy()
    if "date" in df.columns:
        df["ds"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df.index = pd.to_datetime(df.index, errors="coerce")
        df["ds"] = df.index

    # Zielspalte finden
    if "y" in df.columns:
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
    else:
        numeric = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric:
            raise ValueError("validate_prophet_input: keine numerische Zielspalte gefunden")
        df["y"] = pd.to_numeric(df[numeric[0]], errors="coerce")

    df = df[["ds", "y"]].dropna()
    return df


def resolve_components(selection: List[str], etf_universe: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float]]:
    """
    Wandelt Auswahl in flache Liste (key, weight).
    - Einzelinstrumente -> weight 1.0
    - Pakete mit 'components' -> Komponenten normalisiert auf 1.0 (relativ zum Paket)
    Rückgabe: [(key, weight), ...] aggregiert (gleiche Keys summiert).
    """
    resolved = []
    for key in selection:
        item = etf_universe.get(key, {})
        comps = item.get("components")
        if comps and isinstance(comps, dict):
            total = sum(comps.values()) or 1.0
            for comp_key, w in comps.items():
                resolved.append((comp_key, float(w) / total))
        else:
            resolved.append((key, 1.0))
    aggregated: Dict[str, float] = {}
    for k, w in resolved:
        aggregated[k] = aggregated.get(k, 0.0) + w
    return list(aggregated.items())

def normalize_ter_value(raw_ter: float):
    """
    Versucht plausibles TER-Format zu erkennen und normalisiert.
    Rückgabe: (normalized_ter_decimal, note)
    """
    if raw_ter is None:
        return 0.0, "missing"
    try:
        raw = float(raw_ter)
    except Exception:
        return 0.0, "invalid"
    if raw == 0.0:
        return 0.0, "zero"
    # sehr groÃŸe Werte -> vermutlich Prozent (22 -> 0.22)
    if raw > 5:
        return raw / 100.0, "divided_by_100 (suspected percent)"
    # mittlere Werte (0.5..5) -> vermutlich percent like 0.5% stored as 0.5
    if 0.5 <= raw <= 5:
        return raw / 100.0, "divided_by_100 (likely percent)"
    # kleine Werte (0 < x < 0.5) -> plausibel as decimal
    if 0 < raw < 0.5:
        if raw > 0.05:
            return raw / 100.0, "divided_by_100 (edge case)"
        return raw, "ok"
    return raw, "ok"

def _validate_ter_values(df: pd.DataFrame):
    """
    Prüft TER-Werte auf Plausibilität und aggregiert.
    Liefert: (aggregated_ter, ter_warnings:list, df_with_notes)
    """
    ter_warnings = []
    if "ter_pct" not in df.columns:
        df["ter_pct"] = 0.0
    # normalize per-row and keep notes
    notes = []
    normalized = []
    for raw in df["ter_pct"].fillna(0.0).tolist():
        norm, note = normalize_ter_value(raw)
        normalized.append(norm)
        notes.append(note)
    df["_ter_normalized"] = normalized
    df["_ter_note"] = notes
    if (df["_ter_normalized"] > 5).any():
        ter_warnings.append("Einige TER-Werte erscheinen ungewöhnlich hoch (>5).")
    if (df["_ter_normalized"] == 0.0).all():
        ter_warnings.append("Für alle Komponenten fehlt TER-Angabe (0.0). Aggregierte TER ist nicht aussagekräftig.")
    aggregated_ter = (df["abs_weight"] * df["_ter_normalized"]).sum()
    return aggregated_ter, ter_warnings, df

def analyze_portfolio_components(etf_universe: Dict[str, Dict[str, Any]],
                                 resolved_holdings: List[Tuple[str, float]],
                                 eq: float, bd: float, cs: float,
                                 vol_map: Dict[str, float],
                                 ter_threshold_warn: float = 0.01,
                                 herfindahl_warn: float = 0.15):
    """
    Erweiterte Analyse mit Validierung, TER-Fix Vorschlag, Warnregeln und Audit.
    """
    rows = []
    for key, rel in resolved_holdings:
        meta = etf_universe.get(key, {})
        rows.append({
            "key": key,
            "name": meta.get("name", ""),
            "ticker": meta.get("ticker", ""),
            "asset_class": meta.get("asset_class", "equity"),
            "rel_weight": rel,
            "ter_pct": meta.get("ter_pct", 0.0)
        })
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Keine Instrumente ausgewählt für Analyse.")
        return df

    # Distribute class shares -> absolute weights
    class_shares = {"equity": eq / 100.0, "bond": bd / 100.0, "cash": cs / 100.0}
    abs_weights: Dict[str, float] = {}
    for cls in ["equity", "bond", "cash"]:
        cls_df = df[df["asset_class"] == cls]
        total_rel = cls_df["rel_weight"].sum() if not cls_df.empty else 0.0
        if total_rel > 0:
            for _, r in cls_df.iterrows():
                abs_w = (r["rel_weight"] / total_rel) * class_shares[cls]
                abs_weights[r["key"]] = abs_weights.get(r["key"], 0.0) + abs_w

    df["abs_weight"] = df["key"].map(abs_weights).fillna(0.0)
    df = df.sort_values("abs_weight", ascending=False)

    # Volatility & risk contribution
    df["volatility_pct"] = df["asset_class"].map(lambda c: vol_map.get(c, 10))
    df["risk_contribution"] = df["abs_weight"] * df["volatility_pct"]

    # TER validation & normalization
    aggregated_ter, ter_warnings, df = _validate_ter_values(df)

    # Herfindahl
    herfindahl = (df["abs_weight"] ** 2).sum()

    # Explanations
    explanations: List[str] = []
    if aggregated_ter >= ter_threshold_warn:
        explanations.append(
            f"Aggregierte TER Schätzung: {aggregated_ter*100:.2f}% p.a. → sehr hoch; "
            "dies deutet auf fehlerhafte TER-Angaben oder extrem teure/kleine Fonds hin."
        )
    else:
        explanations.append(f"Aggregierte TER Schätzung: {aggregated_ter*100:.2f}% p.a. → akzeptabel.")

    if herfindahl >= herfindahl_warn:
        explanations.append(
            f"Herfindahl Index: {herfindahl:.4f} → deutliche Konzentration (einige wenige Positionen dominieren)."
        )
    else:
        explanations.append(f"Herfindahl Index: {herfindahl:.4f} → Diversifikation erscheint ausreichend.")

    for w in ter_warnings:
        explanations.append(f"TER Validierung: {w}")

    # Missing fields
    missing_fields = []
    if df["asset_class"].isnull().any():
        missing_fields.append("asset_class")
    if df["_ter_normalized"].isnull().any() or (df["_ter_normalized"] == 0.0).any():
        missing_fields.append("ter_pct (fehlend oder 0)")
    missing_components = [k for k, _ in resolved_holdings if k not in etf_universe]
    if missing_components:
        missing_fields.append(f"fehlende Komponenten im Universe: {', '.join(missing_components)}")
    if missing_fields:
        explanations.append("Datenhinweis: Fehlende oder unvollständige Felder: " + ", ".join(missing_fields) + ".")

    # UI display
    st.subheader("Analyse Panel")
    for ex in explanations:
        if "sehr hoch" in ex or "deutliche Konzentration" in ex or "fehlend" in ex or "TER Validierung" in ex:
            st.error(ex)
        else:
            st.info(ex)

    st.markdown("**Top Komponenten nach absolutem Gewicht**")
    st.table(df.head(10)[["key", "name", "ticker", "abs_weight"]].assign(abs_weight=lambda d: (d["abs_weight"]*100).round(2).astype(str) + "%"))

    # Charts
    if not df.empty:
        fig_pie = px.pie(df, names="name", values="abs_weight", title="Absolute Gewichte")
        st.plotly_chart(fig_pie, width='stretch')
        fig_bar = px.bar(df, x="name", y="risk_contribution", title="Risiko Beitrag (vereinfachte Volatilität)")
        st.plotly_chart(fig_bar, width='stretch')

    # TER-Fix preview and apply
    st.markdown("**TER Normalisierung (Vorschau)**")
    preview_df = df[["key", "name", "ticker", "ter_pct", "_ter_normalized", "_ter_note", "abs_weight"]].copy()
    preview_df["_ter_normalized_pct"] = (preview_df["_ter_normalized"] * 100).round(4)
    st.table(preview_df[["key", "name", "ticker", "ter_pct", "_ter_normalized_pct", "_ter_note"]])

    if any(note != "ok" for note in preview_df["_ter_note"].tolist()):
        if st.button("TER Normalisierung übernehmen (Audit wird geschrieben)"):
            # apply normalization to etf_universe file entries if possible (best-effort)
            # We only write audit here; actual persistence should be handled centrally in config loader if desired.
            for _, row in preview_df.iterrows():
                if row["_ter_note"] != "ok":
                    _write_audit({"action": "ter_normalize_suggestion_applied", "key": row["key"], "original_ter": row["ter_pct"], "normalized_ter": row["_ter_normalized"]})
            st.success("TER Normalisierung als Vorschlag auditiert. Bitte aktualisiere etf_universe.yaml falls gewünscht.")
    else:
        st.info("Keine TER-Anomalien erkannt.")

    # Stress-Szenario
    st.markdown("**Stress Szenario**")
    shock = {"equity": -0.20, "bond": -0.05, "cash": 0.0}
    df["shock_return"] = df["asset_class"].map(lambda c: shock.get(c, 0.0))
    portfolio_shock = (df["abs_weight"] * df["shock_return"]).sum()
    st.markdown(f"Geschätzter Portfolio-Impact bei Shock (Equity -20%, Bond -5%): **{portfolio_shock*100:.2f}%**")

    # Additional warnings
    if aggregated_ter >= ter_threshold_warn:
        st.warning("Aggregierte TER liegt über dem Schwellenwert. Prüfe TER-Quellen und korrigiere falsche Formate.")
    if herfindahl >= herfindahl_warn:
        st.warning("Hohe Konzentration erkannt. Prüfe Top-Holdings und mögliche Ãœberschneidungen zwischen Paketen.")

    return df


def prepare_prices_for_backtest(hdf: pd.DataFrame, project_root: Path, load_price_data_func):
    """
    Build etf_universe dict from holdings DataFrame and call load_price_data_func.
    Returns: prices DataFrame
    """
    tickers = [t for t in hdf["ticker"].unique()]
    etf_universe_dict = {t: {"ticker": t} for t in tickers}
    logger.debug("prepare_prices_for_backtest: etf_universe_dict keys=%s", list(etf_universe_dict.keys()))

    try:
        prices = load_price_data_func(etf_universe_dict)
        return prices
    except Exception as e:
        logger.exception("prepare_prices_for_backtest: load_price_data failed: %s", e)
        price_path = Path(project_root) / "risk_dashboard" / "data" / "price_data.csv"
        logger.debug("prepare_prices_for_backtest: falling back to %s", price_path)
        prices = pd.read_csv(price_path, parse_dates=True, index_col=0)
        return prices


def detect_price_format(prices):
    """
    Returns: dict with keys:
      - is_multiindex: bool
      - has_ohlc_level: bool
      - close_columns: list of tickers or column names to use as close series
    """
    result = {"is_multiindex": False, "has_ohlc_level": False, "close_columns": []}
    if hasattr(prices.columns, "nlevels") and prices.columns.nlevels > 1:
        result["is_multiindex"] = True
        # try to find level names or labels that indicate 'Close'
        level_names = list(prices.columns.levels[-1])
        if any(str(x).lower() in ("close","adj close","adjclose") for x in level_names):
            result["has_ohlc_level"] = True
            # collect close columns as top-level tickers
            close_cols = []
            for col in prices.columns:
                if str(col[-1]).lower() in ("close","adj close","adjclose"):
                    close_cols.append(col[0])
            result["close_columns"] = close_cols
    else:
        # flat columns: check for OHLC pattern per ticker prefix or generic 'Close'
        cols_lower = [c.lower() for c in prices.columns.astype(str)]
        if any(x in cols_lower for x in ("close","adj close","adjclose")):
            result["has_ohlc_level"] = False
            # if columns are like 'AAPL Close' or 'AAPL_Close' try to parse tickers
            if any(" " in c or "_" in c for c in prices.columns.astype(str)):
                # heuristic: split and take those ending with close
                close_cols = []
                for c in prices.columns.astype(str):
                    parts = c.replace("_"," ").split()
                    if parts[-1].lower() in ("close","adj","adjclose","adjclose"):
                        close_cols.append(c)
                result["close_columns"] = close_cols or ["Close"] if "Close" in prices.columns else []
            else:
                # assume columns are tickers and represent close prices
                result["close_columns"] = list(prices.columns)
    return result

def extract_close_series(prices):
    info = detect_price_format(prices)
    if info["is_multiindex"] and info["has_ohlc_level"]:
        # prices[(ticker, 'Close')] -> produce DataFrame with ticker columns
        close_df = prices.xs("Close", axis=1, level=-1, drop_level=True)
    elif info["close_columns"]:
        # if close_columns are column names or tickers
        close_df = prices[info["close_columns"]]
        # if names are like 'AAPL Close', rename to ticker
        new_cols = {c: str(c).split()[0] for c in close_df.columns}
        close_df = close_df.rename(columns=new_cols)
    else:
        # fallback: assume columns are tickers and already close prices
        close_df = prices.copy()
    # ensure datetime index
    close_df.index = pd.to_datetime(close_df.index)
    return close_df

def compute_market_value_from_holdings(hdf, prices, portfolio_value):
    """
    Returns hdf with 'market_value' column.
    Priority:
      1. If 'weight_in_etf' present -> market_value = weight_in_etf * portfolio_value
      2. Else if 'shares' present and prices available -> market_value = shares * last_price
      3. Else -> equal distribution fallback
    """
    h = hdf.copy()
    if "weight_in_etf" in h.columns:
        h["market_value"] = h["weight_in_etf"].astype(float) * float(portfolio_value)
        method = "weight_in_etf"
    else:
        # try shares * last_price
        if "shares" in h.columns:
            last_prices = extract_close_series(prices).iloc[-1]
            h = h.set_index("ticker")
            # map last price; missing tickers -> NaN
            h["last_price"] = h.index.map(last_prices.to_dict())
            # if many NaNs, fallback to equal distribution
            if h["last_price"].isna().sum() / len(h) > 0.5:
                # too many missing prices -> fallback
                n = max(len(h), 1)
                h["market_value"] = float(portfolio_value) / n
                method = "fallback_equal_due_to_missing_prices"
            else:
                h["market_value"] = h["shares"].astype(float) * h["last_price"].astype(float)
                method = "shares_times_last_price"
            h = h.reset_index()
        else:
            # equal distribution fallback
            n = max(len(h), 1)
            h["market_value"] = float(portfolio_value) / n
            method = "equal_distribution"
    return h, method
