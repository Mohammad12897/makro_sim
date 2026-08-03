# Dashboard‑Beschreibung und Gebrauchsanweisung

Dieses Dokument erklärt Schritt für Schritt, wie man das **makro_sim** Dashboard benutzt — inklusive Platzhaltern für Screenshots, Beispiel‑Workflows und Quickchecks. Kopiere den gesamten Inhalt in `docs/dashboard_guide.md`.

---

## 1 Start des Dashboards


```bash
python -m streamlit run risk_dashboard/app.py
```

Öffnet sich unter: http://localhost:8501

## 2 Überblick über die Oberfläche
Seitenleiste (links)  
Navigation, Presets, Uploads, Filter, Ticker‑Persistenz.

Hauptbereich (rechts)  
Ranking, Explainable Breakdown, Charts, Backtest‑Panel, Export.

## 3 Quickstart

| **Schritt** | **Aktion** | **UI Ort** | **Erwartetes Ergebnis** | **Hinweis** |
|---|---|---|---|---|
| 1 | App starten | Terminal / Projekt‑Root | Streamlit‑App öffnet im Browser | `python -m streamlit run risk_dashboard/app.py` |
| 2 | Preset wählen | Oben rechts | Preset lädt Scoring‑Gewichte | Siehe Preset‑Tabelle |
| 3 | Ticker hinzufügen | Sidebar → Ticker hinzufügen | Ticker in Sidebar; persistiert in `.cache/user_tickers.json` | Beispiele: `VWRL.L`, `AGGB.L` |
| 4 | Portfolio per CSV laden | Tab *ETF vs Aktie — Absolute Gewichte* | Portfolio‑Tabelle + Marktwerte | CSV: `ticker,quantity,price,market_value` |
| 5 | Scoring prüfen | Tab *ETF Auswahl & Explainable Scoring* | Rangliste mit Komponenten‑Scores | Slider: TER/AUM/Tracking/Replication/Liquidity |
| 6 | Backtest ausführen | Backtest‑Panel | Chart + Metriken (CAGR, Vol, Sharpe, MaxDD) | Rebalancing‑Intervall optional |
| 7 | ETF Breakdowns | *ETF vs Aktie* → Holdings CSV | Underlyings mit `weight_in_etf` und `abs_weight` | Holdings CSV: `ticker,weight_in_etf` |

## 4 ETF Auswahl, Scoring und Explain‑Expander
Explain‑Expander

Ort: Rangliste im Tab ETF Auswahl and Explainable Scoring, rechts neben jedem ETF.

Zeigt: Komponenten‑Scores (TER, AUM, Tracking, Replication, Liquidity), gewichtete Beiträge, Quellen/Metadaten.

Nutzung: Dreieck/Details anklicken → Komponenten lesen → Slider anpassen → Aktualisieren klicken → Rangliste beobachten.

Komponenten‑Zeilen  
Beispiel: TER: 0.85 (niedrige Kosten) → +12 Punkte.

Kurzworkflow

Preset wählen. 2. ETF in Rangliste finden. 3. Expander öffnen. 4. Slider anpassen. 5. Auswahl (Top‑N) treffen.

Screenshot‑Platzhalter  
docs/screenshots/explain_expander.png

## 5 Portfolio Eingabe und Holdings
Portfolio CSV

Erwartete Spalten: ticker,quantity,price,market_value.

Beispiel:
ticker,quantity,price,market_value
VWRL,10,80,800
AGGB,50,20,1000
AAPL,5,150,750
CASH,1,1,10000
## Holdings CSV (ETF Breakdowns)

Erwartete Spalten: ticker,weight_in_etf.

Validierung: Summe weight_in_etf ≈ 1.0 (oder 100%).

Beispiel:
ticker,weight_in_etf
AAPL,0.30
MSFT,0.25
NVDA,0.15
AMZN,0.10
Workflow

CSV hochladen oder Demo‑Holdings nutzen → Berechnen → Tabelle mit weight_in_etf und abs_weight_in_portfolio anzeigen.

## 6 Backtests und Rebalancing
Backtest‑Checks

Prüfe Preisdaten: download_prices() muss Werte für allen gewählten Ticker liefern.

Parameter: Start/Enddatum, Startkapital, DCA, Rebalancing‑Intervall.

Ausgabe: Chart (kumulative Performance), Kennzahlen (CAGR, Volatilität, Sharpe, Max Drawdown), Gewichtshistorie.

Rebalancing — Definition  
Periodische Anpassung zur Wiederherstellung einer Zielallokation (z. B. 60/40).

Strategien

Calendar (zeitbasiert)

Threshold (schwellenbasiert)

Hybrid (Zeit + Schwelle)

Cash‑flow / Contribution

Tolerance bands (mehrstufig)

Empfehlung  
Für Privatanleger: jährlich + Schwelle 5 % als guter Kompromiss.

## 7 Presets und Profile

| **Preset** | **Kurzbeschreibung** |
|---|---|
| **<Neu>** | Leeres Preset zum Anlegen eigener Einstellungen |
| **conservative** | Niedriges Risiko; Fokus Kapitalerhalt |
| **conservative_(low)** | Sehr risikoarm; hoher Anleihenanteil |
| **balanced** | Moderates Risiko; ausgewogen |
| **balanced_(medium)** | Leicht aktienbetonter |
| **aggressive** | Fokus Wachstum; höhere Schwankungen |

Preset‑Verhalten

Preset ersetzt die erlaubten Instrumente (nicht automatisch Zielallokation).

Auto‑normalize skaliert Gewichte auf 100% falls aktiviert.

UI‑Änderungen erzeugen keine echten Orders.

## 8 Kennzahlen und Glossar

| **Begriff** | **Kurzdefinition** |
|---|---|
| **TER** | Total Expense Ratio — jährliche Kostenquote eines ETFs |
| **AUM** | Assets Under Management — Fondsvolumen |
| **Tracking Error** | Abweichung der ETF‑Rendite vom Referenzindex |
| **Replikation** | Physisch vs. synthetisch (Art der Indexabbildung) |
| **Herfindahl‑Index** | Konzentrationsmaß (Diversifikation) |
| **weight_in_etf** | Anteil eines Underlyings im ETF |
| **abs_weight** | Anteil eines Underlyings im Gesamtportfolio |
| **CAGR** | Annualisierte Wachstumsrate |
| **Volatilität** | Standardabweichung der Renditen |
| **Sharpe Ratio** | Rendite pro Einheit Risiko |
| **Max Drawdown** | Größter kumulativer Verlust vom Peak zum Tief |

## 9 Keys, Ticker und empfohlene ETFs

| **Key** | **Vorgeschlagener Ticker** | **Name / Kommentar** |
|---|---|---|
| aggregate_bond_etf | AGGH / AGG | iShares Core Global Aggregate Bond (hedged / unhedged) |
| government_bonds | GOVT / IEGA | Staatsanleihen‑ETF (regionale Varianten) |
| emerging_markets | IEMG / EEM | Emerging Markets Equity ETF |
| small_cap | IWM / SMLL | US Small‑Cap ETF |
| short_term_cash | SHV / VGSH | Kurzfristige Staatsanleihen / Geldmarkt ETF |
| investment_grade_corporates | LQD / IGLB | Investment Grade Corporate Bond ETF |
| qqq | QQQ | Invesco QQQ Trust (NASDAQ‑100) |
| arkk | ARKK | ARK Innovation ETF |
| voo | VOO | Vanguard S&P 500 ETF |
| aggh | AGGH | iShares Global Aggregate Bond Hedged |
| bndx | BNDX | Vanguard Total International Bond ETF |
| imeu_l | IMEU.L / IEUR | iShares MSCI Europe (L‑Listing / IE Listing) |
| iqq0_de | IQQ0.DE | iShares Core DAX (DE‑Listing) |
| xtrackers_dax | XDAX / DAXX.DE | Xtrackers DAX UCITS ETF |
| amundi_faz_100 | (prüfen) | Amundi F.A.Z. 100 — lokales Tickerformat prüfen |
| global_equity_etf | VWRL / IWDA | Vanguard FTSE All‑World / iShares MSCI World |
| amundi_dax50_esg | (prüfen) | Amundi DAX 50 ESG — lokales Tickerformat prüfen |
| tech_package | (kein einzelner Ticker) | Custom Basket; alternativ: QQQ, VGT |
| apple | AAPL | Aktie Apple |
| microsoft | MSFT | Aktie Microsoft |
| siemens | SIE.DE | Aktie Siemens (DE‑Listing) |
| nvda | NVDA | Aktie NVIDIA |
| amazon | AMZN | Aktie Amazon |


## Empfohlene ETFs pro Risikoprofil

| **Risikoprofil** | **Empfohlene Keys** |
|---|---|
| **Low Risk** | aggregate_bond_etf, government_bonds, investment_grade_corporates, short_term_cash |
| **Medium Risk** | global_equity_etf, aggregate_bond_etf, small_cap |
| **High Risk** | global_equity_etf, emerging_markets, small_cap |

## 10 Manuelle Eingriffe und Best Practices
ETF hinzufügen: risk_dashboard/config/etf_candidates.py oder etf_universe.yaml ergänzen (ticker, name, expense_ratio, aum, replication).

Holdings hochladen: UI → ETF vs Aktie — Absolute Gewichte → Holdings‑Upload (CSV ticker,weight_in_etf).

Ticker‑Persistenz: .cache/user_tickers.json (Backup vor Änderungen).

Caches löschen: __pycache__ und *.pyc entfernen nach manuellen Änderungen.

Backup: Vor Änderungen Copy-Item path path.bak -Force.

## 11 Fehlerbehebung und FAQs
App startet nicht / SyntaxError: Prüfe, ob versehentliches Clipboard‑Fragment in einer .py‑Datei steht; entfernen und neu starten.

Keine Preisdaten: Prüfe Netzwerkzugang und Ticker‑Suffixe (.L, .DE, US‑Ticker).

Backtest liefert leere Ergebnisse: Prüfe download_prices() und Index‑Ticker.

Persistenz funktioniert nicht: Prüfe Schreibrechte für .cache/.

## 12 Screenshots und Dateipfade
Screenshots Ordner: docs/screenshots/  
Beispiel‑Dateinamen: sidebar.png, preset.png, ranking.png, breakdown.png, performance.png, explain_expander.png

Wichtige Dateipfade

risk_dashboard/app.py — Haupt‑Entry

risk_dashboard/ui/etf_selection_ui.py — ETF Auswahl UI

risk_dashboard/core/etf_tools.py — Scoring & Preis‑Download

risk_dashboard/utils/persistence.py — save/load user tickers

risk_dashboard/config/etf_candidates.py oder risk_dashboard/config/etf_universe.yaml — ETF‑Universe

docs/dashboard_guide.md — diese Dokumentation