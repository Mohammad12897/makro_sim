# risk_dashboard/ui_helpers.py
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
from pandas import io
import streamlit as st
import tempfile
import os
import logging


from risk_dashboard.core.yf_helper import _safe_read_csv_text
from risk_dashboard.data_utils import find_price_for_ticker, fetch_last_prices, safe_rerun, fetch_prices_for_ticker, normalize_prices
from risk_dashboard.ticker_utils import normalize_ticker, normalize_ticker_simple
from risk_dashboard.time_utils import _harmonize_index_tz, _make_index_naive
from risk_dashboard.price_utils import _pick_price_column, _extract_price_series_from_yf
from risk_dashboard.utils.parsers import safe_read_csv, safe_head_preview, DUMP_MARKERS
from risk_dashboard.config import DEFAULT_START_STR

logger = logging.getLogger(__name__)


# --- Helpers ---
@st.cache_data
def load_markdown_safe(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")

def status_legend():
    c1, c2, c3 = st.columns([1,6,6])
    with c1:
        st.markdown("<span style='color:green; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**iShares (UK/US)** – echte Holdings verfügbar")
    with c3:
        st.markdown("")
    st.markdown("---")
    c1, c2 = st.columns([1,10])
    with c1:
        st.markdown("<span style='color:orange; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**Vanguard / Amundi / Xtrackers** – Demo‑Holdings")
    c1, c2 = st.columns([1,10])
    with c1:
        st.markdown("<span style='color:red; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**Cash / Nicht‑ETF** – keine Holdings")

def show_intro(md_path: str):
    md = load_markdown_safe(md_path)
    if md:
        with st.expander("Einführung", expanded=True):
            st.markdown(md, unsafe_allow_html=False)
    else:
        st.info("Einführungsdokument nicht gefunden.")

def analyze_single_ticker_flow(prefix):
    ticker = st.session_state.get("add_ticker_input", "").strip()
    if not ticker:
        st.warning("Bitte Ticker eingeben.")
        return

    t_norm = normalize_ticker_simple(ticker).upper()
    try:
        success, failed, combined_prices = add_tickers_and_fetch(
            [t_norm],
            prefix=prefix,
            start=DEFAULT_START_STR,
            end=str(pd.Timestamp.today()),
        )
    except Exception:
        logger.exception("Konnte add_tickers_and_fetch nicht ausführen")
        st.error("Fehler beim Laden der Preisdaten")
        success, failed, combined_prices = [], [t_norm], pd.DataFrame()

    if isinstance(combined_prices, pd.DataFrame) and not combined_prices.empty:
        combined_prices.columns = [str(c).strip().upper() for c in combined_prices.columns]
        st.session_state["prices_for_bt"] = combined_prices
    else:
        st.session_state["prices_for_bt"] = st.session_state.get("prices_for_bt", pd.DataFrame())

    # letzte Preiszahl extrahieren
    def last_price(df, t):
        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.NA
        col = next((c for c in df.columns if normalize_ticker_simple(c).upper() == normalize_ticker_simple(t).upper()), None)
        if col is None:
            return pd.NA
        s = df[col].ffill().dropna()
        return float(s.iloc[-1]) if not s.empty else pd.NA

    last = last_price(st.session_state.get("prices_for_bt", pd.DataFrame()), t_norm)
    if pd.isna(last):
        st.warning(f"Keine Preisdaten für {t_norm}.")
    else:
        st.session_state["analysis_result"] = {"ticker": t_norm, "last_price": last}
        st.session_state["navigate_to"] = "Analyse"
        safe_rerun(stop=False)


def atomic_write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


import gzip
import shutil

def persist_dataframe_csv(
    df: pd.DataFrame,
    persist_dir: Path,
    base_name: str = "combined_prices",
    timestamp: bool = True,
    encoding: str = "utf-8-sig",
    sep: str = ";",
    decimal: str = ",",
    index: bool = True,
    compress: Optional[str] = None
) -> Path:
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ") if timestamp else ""
    filename = f"{base_name}_{ts}.csv" if ts else f"{base_name}.csv"
    path = persist_dir / filename

    # write to temp file then replace atomically
    fd, tmp = tempfile.mkstemp(dir=str(persist_dir))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            df.to_csv(f, index=index, sep=sep, decimal=decimal)
        if compress is None:
            os.replace(tmp, str(path))
            return path
        else:
            comp = compress.lower()
            if comp == "gzip":
                comp_path = path.with_suffix(path.suffix + ".gz")
                with open(tmp, "rb") as src, gzip.open(comp_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.remove(tmp)
                return comp_path
            else:
                # fallback: no other compressions implemented here
                os.replace(tmp, str(path))
                return path
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def persist_dataframe(df: pd.DataFrame, persist_dir: Path, base_name: str = "prices", fmt: str = "parquet", compress: str = "snappy"):
    """
    Persist DataFrame to disk. fmt in {'parquet','csv','feather','pickle'}.
    Returns Path to written file.
    """
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{base_name}_{ts}"
    if fmt == "parquet":
        path = persist_dir / f"{filename}.parquet"
        # write to temp then replace
        tmp = path.with_suffix(".parquet.tmp")
        df.to_parquet(tmp, engine="pyarrow", compression=compress, index=True)
        os.replace(tmp, path)
    elif fmt == "csv":
        path = persist_dir / f"{filename}.csv"
        tmp = path.with_suffix(".csv.tmp")
        df.to_csv(tmp, index=True)
        os.replace(tmp, path)
    elif fmt == "feather":
        path = persist_dir / f"{filename}.feather"
        tmp = path.with_suffix(".feather.tmp")
        df.reset_index().to_feather(tmp)
        os.replace(tmp, path)
    elif fmt == "pickle":
        path = persist_dir / f"{filename}.pkl"
        tmp = path.with_suffix(".pkl.tmp")
        df.to_pickle(tmp)
        os.replace(tmp, path)
    else:
        raise ValueError("Unsupported format")
    return path

def persist_per_ticker(df: pd.DataFrame, persist_dir: Path, fmt="parquet"):
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        s_df = series.to_frame(name=col)
        persist_dataframe(s_df, persist_dir / col, base_name=col, fmt=fmt)


def prepare_portfolio_with_latest_prices(portfolio_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a copy of portfolio_df with columns:
    ticker, quantity, price (from CSV if present), last_price (from prices_df), used_price, market_value
    """
    df = portfolio_df.copy()
    # ensure ticker uppercase normalized
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    # build last price map from prices_df
    last_prices = {}
    if isinstance(prices_df, pd.DataFrame) and not prices_df.empty:
        for col in prices_df.columns:
            col_norm = str(col).strip().upper()
            s = prices_df[col].ffill().dropna()
            if not s.empty:
                last_prices[col_norm] = float(s.iloc[-1])

    # compute last_price, used_price, market_value
    def get_last_price(t):
        return last_prices.get(str(t).strip().upper())

    df["last_price"] = df["ticker"].apply(get_last_price)
    # if user provided a manual price column, keep it; otherwise NaN
    if "price" not in df.columns:
        df["price"] = pd.NA
    df["used_price"] = df["price"].fillna(df["last_price"])
    df["market_value"] = df["quantity"].astype(float) * df["used_price"].fillna(0.0).astype(float)

    # reorder / format as desired
    cols = ["ticker", "quantity", "price", "last_price", "used_price", "market_value"]
    return df[cols]

def make_csv_bytes(df: pd.DataFrame, sep=";", decimal=",", encoding="utf-8-sig", index=False) -> bytes:
    """
    Return CSV bytes ready for download. Use utf-8-sig + semicolon + comma decimal for Excel DE.
    """
    buf = io.StringIO()
    df.to_csv(buf, sep=sep, decimal=decimal, index=index)
    return buf.getvalue().encode(encoding)

def offer_portfolio_download(prefix="profile"):
    portfolio_df = st.session_state.get("portfolio_df", pd.DataFrame())
    prices_df = st.session_state.get("prices_for_bt", pd.DataFrame())

    if portfolio_df is None or portfolio_df.empty:
        st.info("Keine Portfolio‑Daten vorhanden.")
        return

    df_for_download = prepare_portfolio_with_latest_prices(portfolio_df, prices_df)

    # create CSV bytes
    csv_bytes = make_csv_bytes(df_for_download, sep=";", decimal=",", encoding="utf-8-sig", index=False)

    # filename with timestamp
    fname = f"portfolio_with_prices_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"

    # Streamlit download button
    st.download_button(
        label="Portfolio als CSV herunterladen",
        data=csv_bytes,
        file_name=fname,
        mime="text/csv"
    )

    # optional: also show preview
    st.dataframe(df_for_download.head(20))


def persist_csv_bytes(csv_bytes: bytes, persist_dir: Path, filename: str) -> Path:
    """
    Atomically write csv_bytes to persist_dir/filename and return the Path.
    """
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / filename

    # write to temp file in same directory then replace atomically
    fd, tmp_path = tempfile.mkstemp(dir=str(persist_dir))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(csv_bytes)
        os.replace(tmp_path, str(path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return path


# Beispiel nach make_csv_bytes:
# saved = persist_csv_bytes(csv_bytes, Path.cwd() / "data" / "exports", fname)
# st.success(f"CSV gespeichert: {saved}")

# from pathlib import Path
# fname = f"portfolio_with_prices_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
# saved_path = persist_csv_bytes(csv_bytes, Path.cwd() / "data" / "exports", fname)
# st.success(f"CSV serverseitig gespeichert: {saved_path}")


# Defensive import for safe_rerun helper (module scope)
try:
    from risk_dashboard.data_utils import safe_rerun
except Exception:
    safe_rerun = None

def handle_portfolio_upload_with_price_lookup(
    prefix: str = "profile",
    persist_path: Optional[Path] = None,
    persist_if_requested: bool = False
) -> Optional[pd.DataFrame]:
    """
    Upload handler for portfolio CSV.
    - Reads the uploaded file once, normalizes columns and tickers,
      parses numerics, computes market_value if possible, groups by ticker,
      stores cleaned df in st.session_state['portfolio_df'].
    - Optionally persists the raw uploaded file if persist_path is provided
      or persist_if_requested==True (then uses uploaded.name).
    - Fetches prices once via add_tickers_and_fetch and fills missing market_value.
    - Sets st.session_state['prices_for_bt'], 'portfolio_df', 'portfolio_total_value'
      and navigates to 'Holdings Analyse' (safe_rerun).
    """
    uploader_key = f"portfolio_uploader_{prefix}"
    uploaded = st.file_uploader("Portfolio-CSV (ticker, quantity, price or market_value)", type=["csv"], key=uploader_key)
    if not uploaded:
        return None

    # --- Read uploaded once (ensure pointer at start) ---
    try:
        uploaded.seek(0)
    except Exception:
        # some UploadedFile implementations don't support seek; ignore
        pass

    try:
        raw_df = pd.read_csv(uploaded)
    except Exception as e:
        logger.exception("Fehler beim Einlesen der hochgeladenen CSV: %s", e)
        st.error(f"Fehler beim Einlesen der CSV: {e}")
        return None

    # --- Normalize column names and map canonical names ---
    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    colmap = {c.lower(): c for c in raw_df.columns}

    if "ticker" not in colmap and "symbol" not in colmap:
        st.error("CSV benötigt Spalte 'ticker' oder 'symbol'.")
        return None

    df = raw_df.rename(columns={
        colmap.get("ticker", ""): "ticker",
        colmap.get("symbol", ""): "ticker",
        colmap.get("quantity", ""): "quantity",
        colmap.get("shares", ""): "quantity",
        colmap.get("price", ""): "price",
        colmap.get("market_value", ""): "market_value"
    })

    # --- Normalize tickers and parse numerics ---
    df["ticker"] = df["ticker"].astype(str).apply(lambda x: normalize_ticker_simple(x).strip().upper())

    df["quantity"] = pd.to_numeric(df.get("quantity", 0).astype(str).str.replace(",", "."), errors="coerce").fillna(0)
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "."), errors="coerce")
    if "market_value" in df.columns:
        df["market_value"] = pd.to_numeric(df["market_value"].astype(str).str.replace(",", "."), errors="coerce")

    # --- Compute market_value if possible ---
    if "market_value" not in df.columns or df["market_value"].isna().any():
        if "price" in df.columns and not df["price"].isna().all():
            df["market_value"] = df["quantity"] * df["price"]
        else:
            df["market_value"] = df.get("market_value", pd.Series([pd.NA] * len(df)))

    # --- Drop rows without ticker and defensive normalization ---
    df = df.dropna(subset=["ticker"])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    # --- Group / aggregate ---
    agg_map = {"quantity": "sum", "market_value": "sum"}
    if "price" in df.columns:
        agg_map["price"] = lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA

    df_grouped = df.groupby("ticker", as_index=False).agg(agg_map)

    # --- Types & NaN handling ---
    df_grouped["quantity"] = pd.to_numeric(df_grouped.get("quantity", 0), errors="coerce").fillna(0)
    df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce").fillna(0.0)

    # --- Persist raw upload if requested or persist_path provided ---
    if persist_path is None and persist_if_requested:
        # derive path from uploaded.name if available, else default filename
        filename = getattr(uploaded, "name", "portfolio.csv")
        persist_path = Path.cwd() / "data" / "holdings" / filename

    if persist_path is not None:
        try:
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(persist_path, "wb") as f:
                f.write(uploaded.getbuffer())
            logger.debug("Persisted uploaded portfolio to %s", persist_path)
        except Exception:
            logger.exception("Konnte hochgeladene Datei nicht persistieren an %s", persist_path)
            st.warning("Konnte hochgeladene Datei nicht speichern (Berechtigung/Path).")

    # --- Store normalized df in session ---
    df_normalized = df_grouped
    st.session_state["portfolio_df"] = df_normalized
    logger.debug("persisting portfolio_df columns=%s head=%s", list(df_normalized.columns), safe_head_preview(df_normalized, DUMP_MARKERS) if 'DUMP_MARKERS' in globals() else df_normalized.head().to_dict())

    # --- Fetch prices ONCE for all tickers ---
    tickers = [t for t in df_normalized["ticker"].unique() if t]
    try:
        from risk_dashboard.ui_helpers import add_tickers_and_fetch  # adjust import path if needed
    except Exception:
        # fallback: assume function is available in current module
        try:
            from risk_dashboard.data_utils import add_tickers_and_fetch
        except Exception:
            add_tickers_and_fetch = None

    if add_tickers_and_fetch is None:
        logger.debug("add_tickers_and_fetch not available; skipping price fetch")
        success, failed, combined_prices = [], tickers, pd.DataFrame()
    else:
        try:
            success, failed, combined_prices = add_tickers_and_fetch(
                tickers,
                prefix=prefix,
                start=DEFAULT_START_STR,
                end=str(pd.Timestamp.today()),
            )
        except Exception:
            logger.exception("Konnte add_tickers_and_fetch nicht ausführen")
            success, failed, combined_prices = [], tickers, pd.DataFrame()

    # --- Normalize and persist prices_for_bt once ---
    # after add_tickers_and_fetch returned combined_prices
    if isinstance(combined_prices, pd.DataFrame) and not combined_prices.empty:
        # make an explicit copy to avoid aliasing / side effects
        combined_prices = combined_prices.copy()

        # normalize column names for consistent matching
        combined_prices.columns = [str(c).strip().upper() for c in combined_prices.columns]

        # Persist as CSV instead of Parquet
        try:
            persist_dir = Path.cwd() / "risk_dashboard" / "data" / "prices"   # oder konfigurierbarer Pfad
            persist_dir.mkdir(parents=True, exist_ok=True)
            file_path = persist_dir / f"combined_prices_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
            saved_path = persist_dataframe_csv(
                combined_prices,
                persist_dir,
                base_name="combined_prices",
                timestamp=True,
                encoding="utf-8-sig",
                sep=";",        # setze ";" falls du Semikolon bevorzugst
                decimal=",",    # setze "," falls du Komma als Dezimaltrennzeichen brauchst
                index=True,      # True speichert Datumsindex als erste Spalte
                compress="gzip"  # optional
            )

            logger.debug("Saved combined_prices CSV to %s", saved_path)
        except Exception:
            logger.exception("Failed to persist combined_prices as CSV")

        # set session state to the safe copy
        st.session_state["prices_for_bt"] = combined_prices
        logger.debug("set prices_for_bt cols=%s", list(combined_prices.columns))
    else:
        st.session_state["prices_for_bt"] = st.session_state.get("prices_for_bt", pd.DataFrame())
        logger.debug("no combined_prices returned; prices_for_bt unchanged")

    # --- Fill missing market_value from last prices if any market_value == 0 ---
    try:
        prices = st.session_state.get("prices_for_bt", pd.DataFrame())
        if isinstance(prices, pd.DataFrame) and not prices.empty:
            last_prices = {}
            for col in prices.columns:
                col_norm = normalize_ticker_simple(str(col)).upper()
                s = prices[col].ffill().dropna()
                if not s.empty:
                    last_prices[col_norm] = float(s.iloc[-1])

            def fill_mv(row):
                mv = row.get("market_value", 0)
                if pd.notna(mv) and float(mv) > 0:
                    return float(mv)
                t = normalize_ticker_simple(row["ticker"]).upper()
                p = last_prices.get(t)
                if p is not None:
                    return float(row["quantity"]) * float(p)
                return 0.0

            df_normalized["market_value"] = df_normalized.apply(fill_mv, axis=1)
            st.session_state["portfolio_df"] = df_normalized
            st.session_state["portfolio_total_value"] = float(df_normalized["market_value"].sum())
    except Exception:
        logger.exception("Failed to fill market_value from prices_for_bt")

    # --- Inform user about failed tickers (if any) ---
    if 'failed' in locals() and failed:
        st.warning(f"Keine Preisdaten für: {', '.join(failed)}. Bitte prüfen oder manuell Preis eingeben.")
        logger.debug("failed tickers from add_tickers_and_fetch: %s", failed)

    # --- Navigation to analysis and safe rerun (LAST) ---
    st.session_state["navigate_to"] = "Holdings Analyse"
    if safe_rerun is not None:
        try:
            safe_rerun(stop=False)
        except Exception:
            logger.exception("safe_rerun failed")
    else:
        try:
            st.experimental_rerun()
        except Exception:
            logger.debug("No rerun available")

    return df_normalized


def add_new_tickers_to_portfolio(new_tickers: List[str], default_qty: int = 1):
    if not new_tickers:
        return
    # if input already contains pairs (ticker, qty), detect and delegate
    if all(isinstance(x, (list, tuple)) and len(x) == 2 for x in new_tickers):
        pairs = [(normalize_ticker(str(t)).upper(), int(q) if q is not None else int(default_qty)) for t, q in new_tickers]
        add_new_tickers_to_portfolio_with_quantities(pairs, default_qty=int(default_qty))
        return

    # otherwise existing behavior
    new_tickers_norm = [normalize_ticker(str(t)).upper() for t in new_tickers if t and str(t).strip()]
    if not new_tickers_norm:
        return
    # build pairs (ticker, qty)
    pairs = [(t, int(default_qty)) for t in new_tickers_norm]
    # delegate to the quantity-aware helper
    add_new_tickers_to_portfolio_with_quantities(pairs, default_qty=int(default_qty))
    # ensure portfolio_df exists and has correct columns/types
    portfolio = st.session_state.get("portfolio_df")
    if portfolio is None or portfolio.empty:
        portfolio = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # normalize existing tickers and ensure dtypes
    portfolio = portfolio.copy()
    if "ticker" not in portfolio.columns:
        portfolio["ticker"] = ""
    portfolio["ticker"] = portfolio["ticker"].astype(str).str.strip().str.upper()
    if "quantity" not in portfolio.columns:
        portfolio["quantity"] = 0
    portfolio["quantity"] = pd.to_numeric(portfolio["quantity"], errors="coerce").fillna(0).astype(int)

    # build list of tickers to actually add (avoid duplicates)
    existing_set = set(portfolio["ticker"].tolist())
    to_add = [t for t in new_tickers_norm if t and t.upper() not in existing_set]

    if not to_add:
        # nothing to add
        st.info("Keine neuen Ticker zum Hinzufügen.")
        st.session_state["portfolio_df"] = portfolio
        logger.debug("persisting portfolio_df columns=%s head=%s", list(portfolio.columns), safe_head_preview(portfolio, DUMP_MARKERS))
        return

    # create DataFrame for new rows with correct dtypes
    new_rows = pd.DataFrame([{"ticker": t.upper(), "quantity": int(default_qty), "price": pd.NA, "market_value": pd.NA, "weight": pd.NA} for t in to_add])
    # ensure dtypes
    new_rows["ticker"] = new_rows["ticker"].astype(str)
    new_rows["quantity"] = pd.to_numeric(new_rows["quantity"], errors="coerce").fillna(0).astype(int)

    # append and consolidate
    portfolio = pd.concat([portfolio, new_rows], ignore_index=True)
    portfolio = portfolio.groupby(portfolio["ticker"].astype(str).str.strip().str.upper(), as_index=False).agg({
        "quantity": "sum",
        "price": lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA,
        "market_value": "sum",
        "weight": "first"
    })

    # persist
    st.session_state["portfolio_df"] = portfolio
    logger.debug("persisting portfolio_df columns=%s head=%s", list(portfolio.columns), safe_head_preview(portfolio, DUMP_MARKERS))
    st.success(f"{len(to_add)} neue Ticker hinzugefügt.")
    return


def _safe_preview(obj, max_len: int = 1000) -> str:
    """
    Kurze, sichere Vorschau für Logging / Sidebar.
    - DataFrame: nur Spaltenliste + Indexbereich
    - dict/list: redigiere bekannte sensible Keys und kürze Inhalte
    - sonst: kurze Stringrepräsentation
    """
    try:
        if isinstance(obj, pd.DataFrame):
            cols = list(obj.columns)
            try:
                idx_min = obj.index.min()
                idx_max = obj.index.max()
            except Exception:
                idx_min = None
                idx_max = None
            return f"DataFrame cols={cols} index_range=({idx_min},{idx_max})"
        if isinstance(obj, (list, tuple)):
            preview_items = []
            for i, it in enumerate(obj):
                if i >= 5:
                    break
                s = str(it)
                preview_items.append(s[:200] + ("…" if len(s) > 200 else ""))
            return f"{type(obj).__name__} len={len(obj)} sample={preview_items}"
        s = str(obj)
        return s[:max_len] + ("…" if len(s) > max_len else "")
    except Exception:
        return "<preview failed>"


def add_new_tickers_to_portfolio_with_quantities(
    pairs: List[Tuple[str, int]],
    default_qty: int = 1,
) -> None:
    def _coerce_qty(q, fallback):
        try:
            return int(q)
        except Exception:
            try:
                return int(float(str(q).replace(",", ".")))
            except Exception:
                return int(fallback)

    logger.debug("add_new_tickers_to_portfolio_with_quantities: incoming pairs=%s", pairs)

    # 0) Input normalisieren: akzeptiere auch reine ticker-Strings
    norm_pairs: List[Tuple[str, int]] = []
    for item in pairs:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            t_raw, q_raw = item
            t = normalize_ticker(str(t_raw)).upper()
            q = _coerce_qty(q_raw, default_qty)
            if t:
                norm_pairs.append((t, q))
        else:
            t = normalize_ticker(str(item)).upper()
            if t:
                norm_pairs.append((t, int(default_qty)))

    if not norm_pairs:
        logger.debug("add_new_tickers: no valid pairs to add")
        return

    # 1) Load or create portfolio_df
    df = st.session_state.get("portfolio_df")
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])
    df = df.copy()

    # 2) Ensure ticker/quantity columns exist and have safe dtypes
    if "ticker" not in df.columns:
        df["ticker"] = ""
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    if "quantity" not in df.columns:
        df["quantity"] = 0
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)

    # 3) Prepare price cache safely
    prices_cache = st.session_state.get("prices_for_bt")
    logger.debug("add_new_tickers: prices_for_bt preview=%s", _safe_preview(prices_cache))
    prices_df = prices_cache if isinstance(prices_cache, pd.DataFrame) and not prices_cache.empty else None

    # 4) Build existing set BEFORE logging it
    existing_set = set(df["ticker"].astype(str).str.upper().tolist())
    logger.debug("add_new_tickers: existing_set=%s", existing_set)

    # 5) Try to find last prices for new tickers, collect need_fetch
    last_prices: Dict[str, Optional[float]] = {}
    need_fetch: List[str] = []

    for t, q in norm_pairs:
        t = str(t).strip().upper()
        q = _coerce_qty(q, default_qty)

        if t in existing_set:
            # accumulate into existing rows (we'll consolidate later)
            try:
                df.loc[df["ticker"] == t, "quantity"] = df.loc[df["ticker"] == t, "quantity"].astype(int) + int(q)
                # update market_value incrementally if existing price present
                try:
                    existing_price = pd.to_numeric(df.loc[df["ticker"] == t, "price"], errors="coerce").iloc[0]
                    if pd.notna(existing_price):
                        df.loc[df["ticker"] == t, "market_value"] = pd.to_numeric(df.loc[df["ticker"] == t, "market_value"], errors="coerce").fillna(0) + int(q) * float(existing_price)
                except Exception:
                    pass
            except Exception:
                df = pd.concat(
                    [df, pd.DataFrame([{"ticker": t, "quantity": int(q), "price": pd.NA, "market_value": pd.NA, "weight": pd.NA}])],
                    ignore_index=True,
                )
            continue

        price_found = None
        if prices_df is not None:
            for col in prices_df.columns:
                try:
                    if normalize_ticker(str(col)).upper() == t:
                        series = prices_df[col]
                        last_valid = series.ffill().dropna()
                        if not last_valid.empty:
                            price_found = float(last_valid.iloc[-1])
                            break
                except Exception:
                    price_found = None

        if price_found is not None:
            last_prices[t] = price_found
        else:
            need_fetch.append(t)

    # 6) Fetch missing prices as fallback
    if need_fetch:
        try:
            fetched = fetch_last_prices(need_fetch, lookback_days=365)  # erwartet dict ticker->price
            if isinstance(fetched, dict):
                for k, v in fetched.items():
                    if k:
                        last_prices[normalize_ticker(k).upper()] = v
        except Exception:
            logger.exception("add_new_tickers: fetch_last_prices failed for %s", need_fetch)

    # 7) Build new_rows for tickers not in existing_set (set market_value if price known)
    new_rows = []
    for t, q in norm_pairs:
        t = str(t).strip().upper()
        qn = _coerce_qty(q, default_qty)
        if t in existing_set:
            continue
        price_val = last_prices.get(t, pd.NA)
        mv_val = float(price_val) * int(qn) if (price_val is not None and pd.notna(price_val)) else pd.NA
        new_rows.append({"ticker": t, "quantity": int(qn), "price": price_val, "market_value": mv_val, "weight": pd.NA})

    if new_rows:
        logger.debug("add_new_tickers: appending new_rows count=%d sample=%s", len(new_rows), new_rows[:5])
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    # 8) Consolidate duplicates and ensure numeric types
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["market_value"] = pd.to_numeric(df.get("market_value", 0), errors="coerce").fillna(0.0)

    # aggregate: sum quantities and market_value, pick first numeric price if present
    def _first_numeric_price(s):
        try:
            s2 = s.dropna().astype(str).str.replace(",", ".")
            nums = pd.to_numeric(s2, errors="coerce").dropna()
            return float(nums.iloc[0]) if not nums.empty else pd.NA
        except Exception:
            return pd.NA

    df = df.groupby("ticker", as_index=False).agg({
        "quantity": "sum",
        "price": _first_numeric_price,
        "market_value": "sum"
    })

    # --- ensure price is numeric and compute market_value fallback (single place) ---
    df["price"] = pd.to_numeric(df.get("price", pd.Series([pd.NA] * len(df))).astype(str).str.replace(",", "."), errors="coerce")
    df["market_value"] = pd.to_numeric(df.get("market_value", 0), errors="coerce").fillna(0.0)

    mask_price_available = df["price"].notna() & (df["quantity"].fillna(0) != 0)
    df.loc[mask_price_available, "market_value"] = (df.loc[mask_price_available, "quantity"].astype(float)
                                                    * df.loc[mask_price_available, "price"].astype(float))

    df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0.0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)

    # compute weights (percent)
    total_mv = float(df["market_value"].sum()) if not df.empty else 0.0
    if total_mv > 0:
        df["weight"] = (df["market_value"] / total_mv) * 100.0
    else:
        df["weight"] = 0.0

    # 9) Persist back to session_state
    st.session_state["portfolio_df"] = df
    logger.debug("add_new_tickers: portfolio_df updated rows=%d", len(df))
    logger.debug("persisting portfolio_df columns=%s head=%s", list(df.columns), _safe_preview(df))
    st.session_state["portfolio_total_value"] = total_mv

    # update price cache: prefer DataFrame; if not, merge last_prices into dict
    if isinstance(prices_df, pd.DataFrame) and not prices_df.empty:
        st.session_state["prices_for_bt"] = prices_df
    else:
        existing_cache = st.session_state.get("prices_for_bt", {})
        if isinstance(existing_cache, dict):
            existing_cache.update(last_prices)
            st.session_state["prices_for_bt"] = existing_cache
        else:
            st.session_state["prices_for_bt"] = last_prices

    # user feedback counts
    added_count = len(new_rows)
    updated_count = sum(1 for t, _ in norm_pairs if t in existing_set)
    try:
        st.success(f"{added_count} neue Ticker hinzugefügt, {updated_count} bestehende aktualisiert, Gesamtwert {total_mv:,.2f}")
    except Exception:
        logger.debug("Could not write success message to Streamlit UI")

    return


def consolidate_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereinigt und konsolidiert portfolio_df:
    - Normalisiert ticker (Uppercase, trim)
    - Entfernt angehängte Mengenreste (z. B. 'DAX 3' -> 'DAX')
    - Gruppiert nach ticker, summiert quantity und market_value
    - Rechnet weight neu
    """
    if df is None or df.empty:
        # Gib ein leeres DataFrame mit Standardspalten zurück
        return pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    df = df.copy()

    # 1) Normalisiere ticker
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["ticker"] = df["ticker"].str.split().str[0]  # 'DAX 3' -> 'DAX'

    # 2) Stelle sicher, dass die erwarteten Spalten existieren
    expected_cols = {
        "quantity": 0,
        "market_value": 0.0,
        "price": None
    }
    for col, default in expected_cols.items():
        if col not in df.columns:
            df[col] = default

    # 3) Typkonvertierung mit Fallbacks
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0.0)

    # 4) Gruppieren: nur existierende Spalten in agg verwenden
    agg_map = {}
    if "quantity" in df.columns:
        agg_map["quantity"] = "sum"
    if "market_value" in df.columns:
        agg_map["market_value"] = "sum"
    # price: last if present
    if "price" in df.columns:
        agg_map["price"] = "last"

    # Falls agg_map leer wäre (sehr unwahrscheinlich), lege Standardaggregation an
    if not agg_map:
        agg_map = {"quantity": "sum", "market_value": "sum", "price": "last"}

    df_grouped = df.groupby("ticker", as_index=False).agg(agg_map)

    # 5) Recompute weights
    total_mv = df_grouped.get("market_value", pd.Series([0.0])).sum()
    if total_mv > 0:
        df_grouped["weight"] = (df_grouped["market_value"] / total_mv) * 100.0
    else:
        df_grouped["weight"] = 0.0

    # 6) Sicherstellen, dass alle Spalten in der erwarteten Reihenfolge vorhanden sind
    cols = ["ticker", "quantity", "price", "market_value", "weight"]
    for c in cols:
        if c not in df_grouped.columns:
            df_grouped[c] = None if c == "price" else 0.0

    return df_grouped[cols]


def add_tickers_and_fetch(tickers_with_qty, prefix="etf", start=None, end=None):
    qty_map = {}
    if tickers_with_qty and isinstance(tickers_with_qty[0], (list, tuple)):
        tickers = [str(t).strip().upper() for t, _ in tickers_with_qty]
        qty_map = {str(t).strip().upper(): int(q) for t, q in tickers_with_qty}
    else:
        tickers = [str(t).strip().upper() for t in tickers_with_qty] if tickers_with_qty else []

    success = []
    failed = []
    prices_accum = {}

    for t in tickers:
        if not t:
            continue
        try:
            df = fetch_prices_for_ticker(t, start=start, end=end, auto_adjust=True, threads=False)
        except Exception:
            logger.exception("add_tickers_and_fetch: fetch_prices_for_ticker raised for %s", t)
            failed.append(t)
            continue

        if df is None or (hasattr(df, "empty") and df.empty):
            failed.append(t)
            logger.debug("add_tickers_and_fetch: no data for %s", t)
            continue

        try:
            df_norm = normalize_prices(df)
        except Exception:
            logger.exception("add_tickers_and_fetch: normalize_prices failed for %s", t)
            failed.append(t)
            continue

        if df_norm is None or (hasattr(df_norm, "empty") and df_norm.empty):
            failed.append(t)
            logger.debug("add_tickers_and_fetch: normalized empty for %s", t)
            continue

        # pick sensible column and set normalized series name
        try:
            col = _pick_price_column(df_norm)
            series = df_norm[col].copy()
            series.name = normalize_ticker(t)
            prices_accum[series.name] = series
            success.append(t)
        except Exception:
            logger.exception("add_tickers_and_fetch: error selecting price series for %s", t)
            failed.append(t)
            continue

    # Build combined DataFrame from accumulated series (dict of Series -> clean columns)
    combined = pd.DataFrame()
    if prices_accum:
        try:
            combined = pd.concat(prices_accum, axis=1)
            # ensure simple string column names
            if isinstance(combined.columns, pd.MultiIndex):
                combined.columns = ["_".join(map(str, c)).strip() for c in combined.columns]
            else:
                combined.columns = [str(c).strip() for c in combined.columns]
        except Exception:
            try:
                combined = pd.DataFrame(prices_accum)
            except Exception:
                logger.exception("add_tickers_and_fetch: failed to build combined DataFrame")
                combined = pd.DataFrame()

    # Persist user_tickers
    st.session_state.setdefault("user_tickers", [])
    for t in success:
        if t not in st.session_state["user_tickers"]:
            st.session_state["user_tickers"].append(t)

    # Merge into existing prices_for_bt (harmonize tz first)
    existing = st.session_state.get("prices_for_bt")
    logger.debug("prices_for_bt type=%s shape=%s cols=%s", type(existing), getattr(existing,'shape',None), list(getattr(existing,'columns',[])))
    if isinstance(existing, pd.DataFrame) and not existing.empty:
        logger.debug("prices_for_bt sample=%s", safe_head_preview(existing, DUMP_MARKERS))

    if existing is None or (hasattr(existing, "empty") and existing.empty):
        st.session_state["prices_for_bt"] = combined
    else:
        existing = st.session_state.get("prices_for_bt", pd.DataFrame())

        # If combined contains OHLC multi-columns, extract price series
        combined = _extract_price_series_from_yf(combined, prefer="ADJ CLOSE")

        # Harmonize tz (recommended: UTC)
        existing = _harmonize_index_tz(existing, target_tz="UTC")
        combined = _harmonize_index_tz(combined, target_tz="UTC")

        # sort indices
        try:
            existing = existing.sort_index()
            combined = combined.sort_index()
        except Exception:
            pass

        # attempt concat, with fallback to making indices naive if tz mismatch persists
        try:
            merged = pd.concat([existing, combined], axis=1)
        except TypeError as e:
            logger.warning("Concat TypeError, trying naive fallback: %s", e)
            try:
                existing = _make_index_naive(existing)
                combined = _make_index_naive(combined)
                merged = pd.concat([existing, combined], axis=1)
            except Exception as e2:
                logger.error("add_tickers_and_fetch: merging prices_for_bt failed after fallback: %s; replacing with combined", e2)
                st.session_state["prices_for_bt"] = combined
                merged = None

        if merged is not None:
            merged = merged.loc[:, ~merged.columns.duplicated()]
            st.session_state["prices_for_bt"] = merged

    # Update portfolio quantities from qty_map
    if qty_map:
        portfolio = st.session_state.get("portfolio")
        if portfolio is None or portfolio.empty:
            portfolio = pd.DataFrame(columns=["ticker", "quantity"])
        # ensure types
        if "ticker" not in portfolio.columns:
            portfolio["ticker"] = portfolio.get("ticker", pd.Series(dtype=str))
        if "quantity" not in portfolio.columns:
            portfolio["quantity"] = portfolio.get("quantity", pd.Series(dtype=int))
        portfolio["ticker"] = portfolio["ticker"].astype(str)
        portfolio["quantity"] = pd.to_numeric(portfolio["quantity"], errors="coerce").fillna(0).astype(int)

        for t in success:
            q = int(qty_map.get(t, 1))
            if t in portfolio["ticker"].values:
                portfolio.loc[portfolio["ticker"] == t, "quantity"] += q
            else:
                new_row = pd.DataFrame([{"ticker": t, "quantity": q}])
                portfolio = pd.concat([portfolio, new_row], ignore_index=True)

        portfolio = portfolio.groupby("ticker", as_index=False).agg({"quantity": "sum"})
        st.session_state["portfolio"] = portfolio

    # final_df: what we actually stored
    final_df = st.session_state.get("prices_for_bt", combined)

    # debug tz info
    try:
        logger.debug("prices_for_bt index tz=%s combined index tz=%s",
                     getattr(final_df.index, "tz", None),
                     getattr(combined.index, "tz", None))
    except Exception:
        pass

    return success, failed, final_df

def persist_portfolio_df(df: pd.DataFrame):
    # normalize columns
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0).astype(int)
    for col in ("price","market_value","weight"):
        if col not in df.columns:
            df[col] = None
    st.session_state["portfolio_df"] = df[["ticker","quantity","price","market_value","weight"]]
    logger.debug("persisting portfolio_df columns=%s head=%s", list(df.columns), safe_head_preview(df, DUMP_MARKERS))

