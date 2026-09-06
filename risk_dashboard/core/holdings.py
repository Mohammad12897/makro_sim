# risk_dashboard/core/holdings.py
from pathlib import Path
import json
import logging
import requests
import pandas as pd
import streamlit as st
from typing import Optional, Iterable, Sequence, Tuple, List
import io, os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


etf_to_isin_map = {
    # iShares
    "CSPX.L": "IE00B5BMR087",   # iShares Core S&P 500
    "EQQQ.L": "IE00B4L5Y983",   # iShares NASDAQ 100
    "IUSQ.L": "IE00BYX5MX67",   # iShares MSCI USA Quality
    "IWDA.AS": "IE00B4L5Y983",  # iShares MSCI World (Beispiel)

    # Vanguard
    "VWRL.L": "IE00B3RBWM25",   # Vanguard FTSE All-World
    "VUAA.L": "IE00B3XXRP09",   # Vanguard S&P 500

    # Xtrackers
    "XDAX.DE": "DE000A1E0HR9",  # Xtrackers DAX
    "XNAS.DE": "IE00BMFKG444",  # Xtrackers NASDAQ 100

    # Amundi
    "FZ100.DE": "DE000A2N6B44", # Amundi F.A.Z. 100
    "C6E.DE": "LU1681045370",   # Amundi MSCI World

    # Cash (keine ISIN)
    "CASH": None,
}

def load_ishares_holdings(isin: str) -> pd.DataFrame:
    """
    Lädt echte ETF-Holdings direkt von iShares (UK, DE, US).
    Versucht mehrere Domains und Produkt-IDs.
    Gibt ein DataFrame mit Spalten ['ticker', 'weight_in_etf'] zurück.
    """
    product_map = {
        "IE00B5BMR087": ["253741", "251802"],  # CSPX
        "IE00B4L5Y983": ["251802", "251615"],  # EQQQ
        "IE00B3RBWM25": ["251615"],            # VWRL
    }

    domains = [
        "https://www.ishares.com/uk/individual/en/products",
        "https://www.ishares.com/de/privatanleger/de/produkte",
        "https://www.ishares.com/us/products",
    ]

    if isin not in product_map:
        raise ValueError(f"Keine Produkt-ID für ISIN {isin} hinterlegt.")

    for domain in domains:
        for pid in product_map[isin]:
            url = f"{domain}/{pid}/{isin}/1467271812596.ajax?fileType=csv&fileName={isin}_holdings&dataType=fund"
            try:
                response = requests.get(url)
                if response.status_code == 200 and "Ticker" in response.text:
                    df = pd.read_csv(url, skiprows=9)
                    # Debug: zeigt dir, was wirklich eingelesen wurde
                    logger.debug(
                        "read df shape=%s columns=%s sample=%s",
                        getattr(df, 'shape', None),
                        list(df.columns),
                        df.head().to_dict(orient='records')[:3]
                    )
                    df = df.rename(columns={"Ticker": "ticker", "Weight (%)": "weight_pct"})
                    df["weight_in_etf"] = df["weight_pct"] / 100
                    return df[["ticker", "weight_in_etf"]]
            except Exception:
                continue

    raise FileNotFoundError(f"Keine gültige iShares-CSV für ISIN {isin} gefunden.")

def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suffix == ".ods":
        return pd.read_excel(path, engine="odf")

    try:
        df = pd.read_csv(path, sep=None, engine="python")
        logger.debug("read_table: auto-detected sep, shape=%s", getattr(df, "shape", None))
        return df
    except Exception as e:
        logger.debug("read_table: auto-detect failed: %s", e)

    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    seps = [",", ";", "\t", "|"]
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                logger.debug("read_table: success enc=%s sep=%r shape=%s", enc, sep, getattr(df, "shape", None))
                return df
            except Exception:
                continue

    try:
        import chardet
        raw = path.read_bytes()
        enc = chardet.detect(raw).get("encoding")
        if enc:
            try:
                df = pd.read_csv(path, encoding=enc, sep=None, engine="python")
                logger.debug("read_table: chardet detected %s", enc)
                return df
            except Exception:
                logger.debug("read_table: chardet read failed with encoding %s", enc)
    except Exception:
        logger.debug("read_table: chardet not available or failed")

    try:
        df = pd.read_csv(path, encoding="latin-1", sep=",")
        logger.debug("read_table: fallback latin-1, shape=%s", getattr(df, "shape", None))
        return df
    except Exception as e:
        logger.exception("read_table: all attempts failed for %s: %s", path, e)
        raise


def map_holdings_to_pricecols(holdings: Iterable, price_columns: Sequence[str]) -> Tuple[List[str], List[str]]:
    """
    Fallback-Implementation:
    - holdings: Liste/Iterable von holdings-Objekten oder dicts oder Strings (z.B. ticker)
    - price_columns: sequence of column names (z.B. prices.columns)
    Rückgabe:
      mapped_cols: Liste der Spalten/Keys, die in price_columns gefunden wurden (in gleicher Reihenfolge wie holdings)
      missing: Liste der holdings, die nicht gemappt werden konnten
    Hinweis: Ersetze durch die echte Implementierung sobald verfügbar.
    """
    try:
        price_set = {str(c).upper() for c in price_columns}
        mapped = []
        missing = []

        # Unterstütze verschiedene holdings-Formate: dict mit 'ticker', tuple, oder plain string
        for h in holdings:
            cand = None
            # dict-like
            try:
                if isinstance(h, dict):
                    cand = h.get("ticker") or h.get("symbol") or h.get("isin") or h.get("id")
                elif hasattr(h, "ticker"):
                    cand = getattr(h, "ticker")
                else:
                    cand = str(h)
            except Exception:
                cand = str(h)

            if cand is None:
                missing.append(h)
                continue

            cand_norm = str(cand).strip().upper()
            # direkte Übereinstimmung
            if cand_norm in price_set:
                mapped.append(cand_norm)
            else:
                # heuristik: prüfe Varianten (mit/ohne .DE, L, etc.)
                alt = cand_norm.replace(".DE", "").replace(".L", "")
                found = None
                for pc in price_set:
                    if alt and alt in pc:
                        found = pc
                        break
                if found:
                    mapped.append(found)
                else:
                    missing.append(cand_norm)

        return mapped, missing
    except Exception:
        logger.exception("map_holdings_to_pricecols fallback failed")
        return [], list(holdings)


def load_holdings_with_fallback(etf: str, category: str, isin: Optional[str], df_key: str, holdings_dir: Path) -> pd.DataFrame:
    etf = (etf or "").strip()
    holdings_dir = Path(holdings_dir)
    holdings_dir.mkdir(parents=True, exist_ok=True)

    if category == "iShares" and isin:
        try:
            hdf = load_ishares_holdings(isin)
            if isinstance(hdf, pd.DataFrame) and not hdf.empty:
                try:
                    (holdings_dir / f"{etf}.csv").write_text(hdf.to_csv(index=False))
                except Exception:
                    logger.debug("Could not save iShares holdings to disk for %s", etf)
                try:
                    st.session_state[df_key] = hdf
                except Exception:
                    pass
                logger.info("Echte iShares-Holdings geladen für %s", etf)
                return hdf
        except Exception as e:
            logger.warning("iShares holdings load failed for %s: %s", etf, e)

    candidates = sorted(holdings_dir.glob(f"{etf}.*"))
    logger.debug("Looking for holdings for %r in %s -> candidates=%s", etf, holdings_dir.resolve(), [str(p.name) for p in candidates])
    for path in candidates:
        try:
            s = path.suffix.lower()
            if s == ".csv":
                df = read_table(path)
            elif s in (".xlsx", ".xls"):
                df = pd.read_excel(path)
            elif s == ".ods":
                df = pd.read_excel(path, engine="odf")
            else:
                logger.debug("Skipping unknown suffix %s for %s", s, path)
                continue

            logger.debug(
                "read df shape=%s columns=%s sample=%s from %s",
                getattr(df, "shape", None),
                list(df.columns),
                df.head().to_dict(orient="records")[:3],
                path
            )

            df.columns = [str(c).strip().lower() for c in df.columns]
            if "weight" in df.columns and "weight_in_etf" not in df.columns:
                df = df.rename(columns={"weight": "weight_in_etf"})
            if "ticker" not in df.columns and "symbol" in df.columns:
                df = df.rename(columns={"symbol": "ticker"})

            if "ticker" in df.columns and "weight_in_etf" in df.columns:
                df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
                df["weight_in_etf"] = df["weight_in_etf"].astype(str).str.replace(",", ".").astype(float)

                try:
                    df.to_csv(holdings_dir / f"{etf}.csv", index=False)
                    logger.debug("Saved normalized holdings to %s", holdings_dir / f"{etf}.csv")
                except Exception:
                    logger.debug("Could not save normalized holdings for %s", etf)

                try:
                    st.session_state[df_key] = df
                except Exception:
                    pass

                logger.info("Holdings geladen von %s", path)
                return df
            else:
                logger.warning("Holdings %s hat falsche Spalten: %s", path, df.columns.tolist())
        except Exception as e:
            logger.exception("Fehler beim Lesen von %s: %s", path, e)
            continue

    logger.info("Keine Holdings gefunden für %s — Demo verwenden", etf)
    demo = pd.DataFrame([
        {"ticker": "AAPL", "weight_in_etf": 0.30},
        {"ticker": "MSFT", "weight_in_etf": 0.30},
        {"ticker": "NVDA", "weight_in_etf": 0.20},
        {"ticker": "AMZN", "weight_in_etf": 0.20},
    ])
    try:
        demo.to_csv(holdings_dir / f"{etf}.csv", index=False)
    except Exception:
        logger.debug("Konnte Demo-Holdings nicht speichern.")
    try:
        st.session_state[df_key] = demo
    except Exception:
        pass
    return demo

def try_relaxed_holdings(path_or_df):
    """
    Versucht einfache 2-Spalten-Holdings (ticker, weight_in_etf) zu akzeptieren.
    Rückgabe: (True, df) wenn akzeptiert, sonst (False, reason_str).
    """
    if isinstance(path_or_df, (str, Path)):
        try:
            df = pd.read_csv(path_or_df)
        except Exception as e:
            return False, f"read failed: {e}"
    elif isinstance(path_or_df, pd.DataFrame):
        df = path_or_df.copy()
    else:
        return False, "unsupported input type"

    df.columns = [c.strip() for c in df.columns]
    cols_lower = {c.lower() for c in df.columns}

    if cols_lower == {"ticker", "weight_in_etf"} or cols_lower == {"ticker", "weight"}:
        rename_map = {}
        for c in df.columns:
            if c.lower() == "weight":
                rename_map[c] = "weight_in_etf"
            elif c.lower() == "weight_in_etf":
                rename_map[c] = "weight_in_etf"
            elif c.lower() == "ticker":
                rename_map[c] = "ticker"
        df = df.rename(columns=rename_map)

        try:
            df["weight_in_etf"] = pd.to_numeric(df["weight_in_etf"], errors="coerce").fillna(0.0)
        except Exception as e:
            return False, f"weight parse failed: {e}"

        s = float(df["weight_in_etf"].sum())
        if not (0.99 <= s <= 1.01):
            logger.warning("Relaxed holdings: sum weights = %s (not ~1.0)", s)
        logger.info("Accepted relaxed holdings CSV (sum=%s)", s)
        return True, df

    return False, "not a relaxed holdings format"

@st.cache_data(ttl=3600)
def fetch_from_api(ticker: str, api_key: str) -> pd.DataFrame:
    url = "https://apidata.fin2dev.com/v1/etfholdings"  # Beispiel
    params = {"key": api_key, "ticker": ticker}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("result", {}).get("holdings", [])
    rows = []
    for h in data:
        try:
            rows.append({"ticker": h["ticker"], "weight_in_etf": float(h.get("percent_value", 0)) / 100.0})
        except Exception:
            continue
    return pd.DataFrame(rows)

def _normalize_weight_column(df: pd.DataFrame) -> pd.DataFrame:
    candidates = {
        "ticker": ["ticker", "holding", "symbol"],
        "weight": ["weight_in_etf", "weight", "percent", "percent_value"]
    }
    tcol = next((c for c in candidates["ticker"] if c in df.columns), None)
    wcol = next((c for c in candidates["weight"] if c in df.columns), None)
    if tcol is None or wcol is None:
        logger.debug("Could not find ticker/weight columns: cols=%s", list(df.columns))
        return pd.DataFrame()
    out = df[[tcol, wcol]].rename(columns={tcol: "ticker", wcol: "weight_in_etf"}).copy()
    out["weight_in_etf"] = pd.to_numeric(out["weight_in_etf"], errors="coerce")
    out = out.dropna(subset=["ticker"])
    if (out["weight_in_etf"].abs() > 1).any():
        out["weight_in_etf"] = out["weight_in_etf"] / 100.0
    return out[["ticker", "weight_in_etf"]]

@st.cache_data(ttl=3600)
def fetch_from_provider_csv(ticker: str) -> pd.DataFrame:
    provider_template = os.environ.get("HOLDINGS_PROVIDER_URL")
    if not provider_template:
        logger.debug("No HOLDINGS_PROVIDER_URL configured; skipping provider CSV fetch")
        return pd.DataFrame()

    csv_url = provider_template.format(ticker=ticker)
    # local file handling
    if csv_url.startswith("file://"):
        parsed = urlparse(csv_url)
        path = parsed.path
        # Windows: path may start with /C:/..., remove leading slash if present
        if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path.lstrip("/")
        # also handle percent-encoding
        path = os.path.normpath(path)
        if not os.path.exists(path):
            logger.warning("Local holdings file not found for %s: %s", ticker, path)
            return pd.DataFrame()
        try:
            df = pd.read_csv(path, encoding="utf8")
        except Exception as e:
            logger.warning("Failed to read local holdings file %s: %s", path, e)
            return pd.DataFrame()
    else:
        # HTTP(S) provider
        try:
            r = requests.get(csv_url, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.warning("fetch_from_provider_csv failed for %s: %s", ticker, e)
            return pd.DataFrame()
        try:
            df = pd.read_csv(io.StringIO(r.text))
        except Exception as e:
            logger.warning("Failed to parse CSV from %s: %s", csv_url, e)
            return pd.DataFrame()

    return _normalize_weight_column(df)

def get_holdings_for_etf(ticker: str, api_key: str | None = None) -> pd.DataFrame:
    if api_key:
        try:
            df = fetch_from_api(ticker, api_key)
            if not df.empty:
                return df
        except Exception as e:
            logger.warning("fetch_from_api failed for %s: %s", ticker, e)
    # provider CSV fallback (only if configured)
    try:
        df = fetch_from_provider_csv(ticker)
        if not df.empty:
            return df
    except Exception as e:
        logger.warning("fetch_from_provider_csv failed for %s: %s", ticker, e)
    return pd.DataFrame()

def get_etf_holdings(ticker: str, api_key: str | None = None) -> pd.DataFrame:
    """Versucht API -> CSV -> etf_scraper. Gibt DataFrame oder pd.DataFrame() zurück."""
    # 1. API
    try:
        if api_key:
            df = fetch_from_api(ticker, api_key)
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.debug("Holdings from API for %s: %d rows", ticker, len(df))
                return df
    except Exception as e:
        logger.exception("API holdings failed for %s: %s", ticker, e)

    # 2. Provider CSV
    try:
        df = fetch_from_provider_csv(ticker)
        if isinstance(df, pd.DataFrame) and not df.empty:
            logger.debug("Holdings from provider CSV for %s: %d rows", ticker, len(df))
            return df
    except Exception as e:
        logger.exception("Provider CSV failed for %s: %s", ticker, e)

    # 3. etf_scraper fallback
    try:
        from etf_scraper import ETFScraper
        s = ETFScraper()
        hdf = s.query_holdings(ticker)
        if hdf is None or len(hdf) == 0:
            logger.warning("etf_scraper returned no holdings for %s", ticker)
            return pd.DataFrame()
        df = pd.DataFrame({"ticker": hdf["ticker"], "weight_in_etf": hdf["weight"] / 100.0})
        logger.debug("Holdings from etf_scraper for %s: %d rows", ticker, len(df))
        return df
    except Exception as e:
        logger.exception("etf_scraper fallback failed for %s: %s", ticker, e)

    # Fallback: leeres DF
    logger.warning("No holdings found for %s (all sources failed)", ticker)
    return pd.DataFrame()
