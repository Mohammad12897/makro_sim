<<<<<<< HEAD
# core/utils.py
import json
import os

BASE_PATH = "/content/makro_sim/risk_dashboard/data"


def load_json(filename: str):
    """Hilfsfunktion zum Laden einer JSON-Datei."""
    path = os.path.join(BASE_PATH, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_presets():
    """
    Lädt die Länder-Presets aus slider_presets.json.
    """
    return load_json("slider_presets.json")


def load_scenarios():
    """
    Lädt die Szenarien aus scenarios.json.
    """
    return load_json("scenario_presets.json")
=======
# risk_dashboard/core/utils.py
from pathlib import Path
import pandas as pd
import yaml

# BASE_PATH zeigt auf das Projektverzeichnis "makro_sim"
BASE_PATH = Path(__file__).resolve().parents[3]

def load_config():
    config_path = BASE_PATH / "risk_dashboard" / "src" / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_data_path(cfg=None):
    cfg = cfg or load_config()
    return BASE_PATH / cfg["paths"]["data"]

def get_models_path(cfg=None):
    cfg = cfg or load_config()
    return BASE_PATH / cfg["paths"]["models"]


def get_latest_before(df, column, date):
    if df is None or df.empty:
        raise ValueError("DataFrame ist leer.")
    df2 = df.copy()
    if column is not None and column in df2.columns:
        df2[column] = pd.to_datetime(df2[column], errors="coerce")
        df2 = df2.dropna(subset=[column]).set_index(column).sort_index()
    else:
        if isinstance(df2.index, pd.DatetimeIndex):
            df2 = df2.sort_index()
        else:
            raise KeyError(f"Spalte '{column}' nicht gefunden und Index ist kein DatetimeIndex.")
    date = pd.to_datetime(date)
    idx = df2.index[df2.index <= date]
    if len(idx) == 0:
        raise ValueError(f"Kein Eintrag vor oder am {date.date()} gefunden.")
    return df2.loc[idx[-1]]



def validate_prophet_input(df):
    """
    Stellt sicher, dass Prophet mindestens 2 gültige Datenpunkte bekommt.
    Erwartet Spalten: ['ds', 'y'].
    """
    if df is None or len(df) == 0:
        raise ValueError("Prophet-Input ist leer.")

    if "y" not in df.columns:
        raise ValueError(f"Prophet-Input hat keine Spalte 'y'. Spalten: {df.columns.tolist()}")

    df = df.dropna(subset=["y"])

    if len(df) < 2:
        raise ValueError("Prophet benötigt mindestens 2 gültige Datenpunkte.")

    return df


def ensure_date_column(df):
    """
    Stellt sicher, dass ein DataFrame eine 'date'-Spalte besitzt.
    Akzeptiert:
    - DatetimeIndex
    - Spalten wie 'Date', 'DATE', 'time', 'timestamp'
    - beliebige Indexe, die in datetime konvertierbar sind
    """
    import pandas as pd

    # 1) Wenn 'date' bereits existiert → normalisieren
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        return df

    # 2) Wenn Index ein DatetimeIndex ist → in Spalte umwandeln
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={"index": "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        return df

    # 3) Alternative Spalten suchen
    alt_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
    if alt_cols:
        df = df.rename(columns={alt_cols[0]: "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        return df

    # 4) Letzter Versuch: Index in datetime konvertieren
    try:
        df["date"] = pd.to_datetime(df.index, errors="coerce")
        df = df.dropna(subset=["date"])
        return df
    except Exception:
        raise KeyError(
            "DataFrame besitzt weder eine 'date'-Spalte noch einen DatetimeIndex. "
            "Bitte Eingabedaten prüfen."
        )


def normalize_price_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Liefert ein DataFrame mit einer Spalte pro Ticker (Close-Preise).
        Unterstützt MultiIndex (ticker, field) und SingleIndex DataFrames.
        Gibt ein leeres DataFrame zurück, wenn nichts extrahierbar ist.
        """
        if df is None:
            return pd.DataFrame()

        # MultiIndex: (ticker, field)
        if isinstance(df.columns, pd.MultiIndex):
            # Versuche 'Close' oder 'Adj Close' im zweiten Level
            for field in ("Close", "Adj Close", "close", "adj close"):
                try:
                    out = df.xs(field, axis=1, level=1)
                    if not out.empty:
                        out.columns = [str(c) for c in out.columns]
                        return out
                except Exception:
                    pass
            # Fallback: nimm erste numerische Spalte pro Ticker
            out_dict = {}
            for t in df.columns.levels[0]:
                numeric = df[t].select_dtypes(include="number")
                if not numeric.empty:
                    out_dict[str(t)] = numeric.iloc[:, 0]
            if out_dict:
                return pd.DataFrame(out_dict)
            return pd.DataFrame()

        # SingleIndex: suche 'Adj Close' oder 'Close'
        cols = [c for c in df.columns]
        if "Adj Close" in cols:
            out = df["Adj Close"].copy()
            if isinstance(out, pd.Series):
                return out.to_frame(out.name or "Adj Close")
            return out
        if "Close" in cols:
            out = df["Close"].copy()
            if isinstance(out, pd.Series):
                return out.to_frame(out.name or "Close")
            return out

        # Fallback: numerische Spalten
        numeric = df.select_dtypes(include="number")
        if not numeric.empty:
            return numeric

        return pd.DataFrame()


def ensure_date_series(df):
    """
    Liefert eine Datetime Series für ein DataFrame.
    - Wenn DataFrame eine 'date' Spalte hat, wird diese verwendet.
    - Sonst, wenn der Index ein DatetimeIndex ist, wird der Index zurückgegeben.
    - Sonst wird eine leere Datetime Series zurückgegeben.
    """
    if df is None or df.empty:
        return pd.Series(dtype="datetime64[ns]")

    # 1) explizite 'date' Spalte (klein/groß prüfen)
    for col in ("date", "Date"):
        if col in df.columns:
            return pd.to_datetime(df[col], errors="coerce")

    # 2) DatetimeIndex verwenden
    if isinstance(df.index, pd.DatetimeIndex):
        return pd.to_datetime(df.index)

    # 3) nichts gefunden -> leere Series
    return pd.Series(dtype="datetime64[ns]")
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
