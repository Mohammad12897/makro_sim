# risk_dashboard/core/holdings.py
from pathlib import Path
import json
import logging
import requests
import pandas as pd
from typing import Optional

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
                    import streamlit as st
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
                    import streamlit as st
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
        import streamlit as st
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
