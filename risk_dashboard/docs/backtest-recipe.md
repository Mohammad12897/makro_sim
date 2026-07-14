# Backtest Rezept

**Ziel**  
Kurz: Backtest für einen ETF ausführen und Ergebnisse (portfolio_value, metrics, weights_over_time) zuverlässig speichern und verifizieren.

---

## Voraussetzungen
- **Python** 3.10+ in virtueller Umgebung.  
- Abhängigkeiten installiert aus `requirements.txt`.  
- Schreibrechte für `risk_dashboard/data/backtests`.  
- `price_close` DataFrame und `weights_for_backtest` vorhanden.  
- `backtest_dir` als `Path` konfiguriert.

---

## Vorbereitung
1. Projekt‑Ordner prüfen:
   - **Pfad**: `risk_dashboard/data/backtests`  
   - Erstellen falls nötig:
     ```python
     backtest_dir.mkdir(parents=True, exist_ok=True)
     ```
2. Syntax prüfen:
   ```bash
   python -m py_compile risk_dashboard/core/backtest.py

   Schritt für Schritt
   Backtest ausführen
   Was passiert  
   Die Backtest‑Funktion simuliert die historische Entwicklung des Portfolios anhand von price_close und weights_for_backtest. Ergebnis sind portfolio_value, metrics und weights_over_time.

   Warum  
   Diese Daten zeigen Performance, Risiko und Allokationsverlauf und sind Grundlage für Reporting und Entscheidungen.

Code
   
   try:
    bt_output = call_run_portfolio_backtest_safe(
        run_portfolio_backtest,
        price_close,
        weights_for_backtest,
        macro_df
    )
except Exception as e:
    results.setdefault("results", {}).setdefault(etf, {})["status"] = "failed"
    results["results"][etf]["error"] = str(e)
    logger.exception("run_portfolio_backtest failed for %s: %s", etf, e)
    continue

   Was die Begriffe bedeuten

      Portfolio Value  
      Zeitreihe des Gesamtwerts des Portfolios (Index = Datum, Spalte = Wert). Grundlage für Renditen und Drawdowns.

      Metrics  
      Zusammengefasste Kennzahlen (z. B. CAGR, Volatilität, Sharpe, Max Drawdown).

      Weights Over Time  
      DataFrame mit Datum × Assets; zeigt Rebalancing, Drift und Positionsänderungen.

Verifikation
   assert isinstance(bt_output, dict)
   pv = bt_output.get("portfolio_value")
   if isinstance(pv, pd.Series):
       pv = pv.to_frame("value")
   assert isinstance(pv, pd.DataFrame) and not pv.empty
   metrics = bt_output.get("metrics", {})
   assert all(k in metrics for k in ("cagr","vol","sharpe","max_dd"))
   wot = bt_output.get("weights_over_time")
   assert isinstance(wot, pd.DataFrame)
   assert np.allclose(wot.sum(axis=1).values, 1.0, atol=1e-6)

Fehlerbehandlung

      pv ist Series → pv = pv.to_frame("value").

      KeyError beim Schreiben in results → immer results.setdefault("results", {}).setdefault(etf, {}) vor Zugriff.

      Datei wird nicht geschrieben → backtest_dir.mkdir(parents=True, exist_ok=True) und os.access(backtest_dir, os.W_OK) prüfen.

      Syntaxfehler durch Fremdtext → entferne nicht‑Python Blöcke aus .py Dateien.

Speichern der Ergebnisse

Portfolio Value
   
   pv = bt_output.get("portfolio_value")
   if isinstance(pv, pd.Series):
       pv = pv.to_frame("value")

   backtest_dir.mkdir(parents=True, exist_ok=True)

   if isinstance(pv, pd.DataFrame) and not pv.empty:
       pv_path = (backtest_dir / f"{etf}_portfolio_value.csv").resolve()
       pv.to_csv(pv_path, index=True)
       results.setdefault("portfolio_value_files", {})[etf] = str(pv_path)
       results.setdefault("results", {}).setdefault(etf, {})["portfolio_value_file"] = str(pv_path)
   else:
       results.setdefault("results", {}).setdefault(etf, {})["portfolio_value_file"] = None

Metrics

   metrics = bt_output.get("metrics", {})
if metrics:
    metrics_path = backtest_dir / f"{etf}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    results.setdefault("metrics_files", {})[etf] = str(metrics_path)
    results.setdefault("results", {}).setdefault(etf, {})["metrics_file"] = str(metrics_path)

Weights Over Time

   wot = bt_output.get("weights_over_time")
   if isinstance(wot, pd.DataFrame) and not wot.empty:
       wot_path = (backtest_dir / f"{etf}_weights_over_time.csv").resolve()
       wot.to_csv(wot_path, index=True)
       results.setdefault("results", {}).setdefault(etf, {})["weights_over_time_file"] = str(wot_path)

Bilder und Dateinamen
Lege Screenshots in risk_dashboard/docs/images/:

backtest-portfolio-value.png

backtest-metrics.png

backtest-weights.png

