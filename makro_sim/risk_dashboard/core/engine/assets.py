#core/engine/assets.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf
import numpy as np


# -------------------------------------------------------------------
# Kursdaten laden
# -------------------------------------------------------------------
def fetch_prices(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Lädt historische Kursdaten über yfinance.
    """
    if not ticker:
        return None

    ticker = ticker.strip()
    end = datetime.today()
    start = end - timedelta(days=days)

    try:
        data = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=True,
            threads=False
        )

        if data is None or data.empty:
            return None
        return data
    except Exception as e:
        print(f"[fetch_prices] Fehler beim Laden von {ticker}: {e}")
        return None


# -------------------------------------------------------------------
# KI-Score aus Kursdaten
# -------------------------------------------------------------------
def compute_ki_score_from_prices(prices: pd.DataFrame | None) -> float | None:
    if prices is None or len(prices) < 60:
        return None

    # Close-Preis bestimmen
    close = prices["Adj Close"] if "Adj Close" in prices.columns else prices["Close"]

    # Renditen
    returns = close.pct_change().dropna()
    if len(returns) == 0:
        return None

    # 1) Momentum (6 Monate)
    try:
        mom_raw = (close.iloc[-1] / close.iloc[max(0, len(close) - 126)]) - 1
        momentum = float(mom_raw.item() if hasattr(mom_raw, "item") else mom_raw)
    except Exception:
        momentum = None

    # 2) Volatilität (immer Float!)
    vol = returns.std()
    if hasattr(vol, "mean"):
        vol = float(vol.mean())

    vol_score = 1 / (1 + vol) if vol is not None else None

    # 3) Max Drawdown
    roll_max = close.cummax()
    dd_raw = (close / roll_max - 1).min()
    drawdown = float(dd_raw.item() if hasattr(dd_raw, "item") else dd_raw)
    dd_score = 1 + drawdown

    # 4) Sharpe-Proxy
    mean_raw = returns.mean()
    mean_ret = float(mean_raw.item() if hasattr(mean_raw, "item") else mean_raw)
    sharpe = mean_ret / vol if (vol is not None and vol > 0) else 0

    # Normierung
    def norm(x: Any, a: float, b: float) -> Optional[float]:
        try:
            x = float(x)
        except Exception:
            return None
        x = max(min(x, b), a)
        return (x - a) / (b - a)

    m_score = norm(momentum, -0.5, 0.5)
    s_score = norm(sharpe, -1, 1)

    # Gesamt-Score
    ki = (
        0.4 * (m_score or 0)
        + 0.2 * (vol_score or 0)
        + 0.2 * (dd_score or 0)
        + 0.2 * (s_score or 0)
    )

    return round(ki * 100, 2)


# -------------------------------------------------------------------
# Radar-Daten aus Asset + Kursen
# -------------------------------------------------------------------
def compute_radar_data(asset: Dict[str, Any],
                       prices: pd.DataFrame | None,
                       typ: str) -> Dict[str, Optional[float]]:
    """
    Gibt ein Dict zurück: {achse: wert_0_100, ...}
    """
    radar: Dict[str, Optional[float]] = {}

    # Hilfsfunktion: Normierung 0–100
    def scale(x: Any, a: float, b: float) -> Optional[float]:
        try:
            x = float(x)
        except Exception:
            return None
        x = max(min(x, b), a)
        return round((x - a) / (b - a) * 100, 1)

    # Kursbasis
    close = None
    returns = None

    if prices is not None and not prices.empty:
        close = prices["Adj Close"] if "Adj Close" in prices.columns else prices["Close"]
        returns = close.pct_change().dropna()

    # Gemeinsame Kennzahlen
    momentum: Optional[float] = None
    vol: Optional[float] = None
    dd: Optional[float] = None

    # Momentum
    if close is not None and len(close) > 30:
        try:
            mom_raw = (close.iloc[-1] / close.iloc[max(0, len(close) - 126)]) - 1
            momentum = float(mom_raw.item() if hasattr(mom_raw, "item") else mom_raw)
        except Exception:
            momentum = None

    # Volatilität (immer Float!)
    if returns is not None and len(returns) > 0:
        vol_tmp = returns.std()
        if hasattr(vol_tmp, "mean"):
            vol = float(vol_tmp.mean())
        else:
            vol = float(vol_tmp)

    # Drawdown
    if close is not None and len(close) > 0:
        roll_max = close.cummax()
        try:
            dd_raw = (close / roll_max - 1).min()
            dd = float(dd_raw.item() if hasattr(dd_raw, "item") else dd_raw)
        except Exception:
            dd = None

    # Typ normalisieren
    typ = (typ or "Unknown").capitalize()

    # Radar je nach Asset-Typ
    if typ == "Stock":
        radar["Momentum"] = scale(momentum, -0.5, 0.5)
        radar["Volatilität (stabil)"] = scale(1 / (1 + (vol or 0)), 0, 1)

        kgv = asset.get("KGV")
        wachstum = asset.get("Wachstum")
        cashflow = asset.get("Cashflow")

        radar["KGV (günstig)"] = scale(-1 * (kgv or 0), -40, 0) if kgv is not None else None
        radar["Wachstum"] = scale(wachstum, -0.1, 0.3) if wachstum is not None else None
        radar["Cashflow‑Qualität"] = scale(cashflow, -0.1, 0.3) if cashflow is not None else None

    elif typ == "Etf":
        ter = asset.get("TER")
        volumen = asset.get("Volumen")
        td = asset.get("TD")
        repl = asset.get("Replikation")

        radar["Momentum"] = scale(momentum, -0.3, 0.3)
        radar["TER (günstig)"] = scale(-1 * (ter or 0), -1.0, 0) if ter is not None else None
        radar["Volumen"] = scale(volumen, 1e6, 1e10) if volumen is not None else None
        radar["Tracking‑Diff (gut)"] = scale(-1 * (td or 0), -0.05, 0) if td is not None else None
        radar["Replikation (physisch=100)"] = 100 if (repl or "").lower().startswith("phys") else 50

    elif typ == "Crypto":
        radar["Momentum"] = scale(momentum, -1.0, 1.0)
        radar["Volatilität (stabil)"] = scale(1 / (1 + (vol or 0)), 0, 1)
        radar["Drawdown (robust)"] = scale(1 + (dd or -0.9), 0, 1)

        if momentum is not None and vol not in (None, 0):
            radar["Trendstabilität"] = scale(momentum / vol, -2, 2)
        else:
            radar["Trendstabilität"] = None

        radar["On‑Chain‑Proxy"] = 50  # Platzhalter

    elif typ == "Index":
        radar["Momentum"] = scale(momentum, -0.3, 0.3)
        radar["Volatilität (stabil)"] = scale(1 / (1 + (vol or 0)), 0, 1)
        radar["Drawdown (robust)"] = scale(1 + (dd or -0.6), 0, 1)

        if momentum is not None and vol not in (None, 0):
            radar["Trendstabilität"] = scale(momentum / vol, -1, 1)
        else:
            radar["Trendstabilität"] = None

        radar["Marktbreite"] = 50  # Platzhalter

    else:
        # Unknown
        radar["Momentum"] = scale(momentum, -0.5, 0.5)
        radar["Volatilität (stabil)"] = scale(1 / (1 + (vol or 0)), 0, 1)

    return radar

