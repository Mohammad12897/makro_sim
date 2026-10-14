# risk_dashboard/src/core/fx_model.py
import pandas as pd
import joblib
import streamlit as st
import logging


logger = logging.getLogger(__name__)
from risk_dashboard.utils import get_data_path, get_models_path


@st.cache_resource
def load_fx_model():
    models_path = get_models_path()
    model_file = models_path / "rf_model_usd_eur.joblib"
    return joblib.load(model_file)


def create_fx_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Erwartet df mit Spalte 'fx' oder 'close' (oder Index=Datum und eine Preisspalte).
    Liefert DataFrame mit Features: lag1, lag2, lag3, ma5, ma20, volatility.
    """
    df = df.copy()
    # Standardspalte finden
    price_col = next((c for c in df.columns if c.lower() in ("fx","close","price")), df.columns[0])
    s = pd.to_numeric(df[price_col], errors="coerce").ffill().bfill()
    feat = pd.DataFrame(index=s.index)
    feat["lag1"] = s.shift(1)
    feat["lag2"] = s.shift(2)
    feat["lag3"] = s.shift(3)
    feat["ma5"] = s.rolling(5, min_periods=1).mean()
    feat["ma20"] = s.rolling(20, min_periods=1).mean()
    feat["volatility"] = s.pct_change().rolling(20, min_periods=1).std().fillna(0)
    feat = feat.dropna(how="all")
    return feat

def get_fx_forecast() -> float:
    data_path = get_data_path()
    csv_path = data_path / "fx_data_usd_eur.csv"
    if not csv_path.exists():
        logger.error("FX data file not found: %s", csv_path)
        raise FileNotFoundError(f"{csv_path} not found")

    df = pd.read_csv(csv_path)
    from risk_dashboard.utils.parsers import safe_head_preview, DUMP_MARKERS
    logger.debug("read df shape=%s columns=%s sample=%s", getattr(df,'shape',None), list(df.columns), safe_head_preview(df, DUMP_MARKERS))
    if df.empty:
        logger.error("FX data file is empty: %s", csv_path)
        raise ValueError("FX data empty")

    df_feat = create_fx_features(df)
    if df_feat is None or df_feat.empty:
        logger.error("create_fx_features returned empty")
        raise RuntimeError("Feature creation failed")

    last_row = df_feat.iloc[-1]
    required = ["lag1", "lag2", "lag3", "ma5", "ma20", "volatility"]
    if not all(col in last_row.index for col in required):
        logger.error("Missing FX features in last row: %s", last_row.index.tolist())
        raise RuntimeError("Missing features for FX model")

    X = last_row[required].values.reshape(1, -1)
    model = load_fx_model()
    if model is None:
        logger.error("FX model could not be loaded")
        raise RuntimeError("FX model load failed")

    try:
        pred = model.predict(X)[0]
    except Exception as e:
        logger.exception("Model prediction failed: %s", e)
        raise

    return float(pred)
