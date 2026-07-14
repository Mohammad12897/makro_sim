# Dashboard‑Beschreibung und Gebrauchsanweisung


# makro_sim – Kochrezept mit Screenshots
Dieses Dokument erklärt Schritt für Schritt, wie man das makro_sim Dashboard benutzt — inklusive Screenshots, die du einfach ersetzen kannst.

## 1. Start des Dashboards
python -m streamlit run risk_dashboard/app.py
Öffnet sich unter:
http://localhost:8501


## 2. Überblick über die Oberfläche
Seitenleiste (links)
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Hauptbereich (rechts)
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 3. ETF‑Auswahl & Scoring
Schritt 1: Preset wählen
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Schritt 2: Index‑Universum wählen
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Schritt 3: Analyse starten
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Nach Klick auf Analysieren erscheint die Rangliste:

[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 4. Explainable Breakdown
Zeigt, wie der Score eines ETFs zustande kommt.

[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 5. Portfolio‑Zusammenstellung
Automatische Auswahl
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Manuelle Auswahl
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 6. Gewichtung
Automatisch (Optimierer)
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Manuell (Slider)
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 7. Backtest durchführen
Parameter einstellen
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Backtest starten
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

## 8. Ergebnisse verstehen
8.1 Kumulative Performance
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Was bedeutet das?

Startwert = 1.0

Wert 2.0 = Portfolio hat sich verdoppelt

Glatte Linie = stabil

Zacken = volatil

8.2 Gewichtsentwicklung
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

8.3 Kennzahlen
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

CAGR = durchschnittliche jährliche Rendite
Volatilität = Schwankungsbreite der Renditen

8.4 Rebalancing
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Rebalancing bedeutet:  
Die Portfolio‑Gewichte regelmäßig wieder auf die Zielverteilung zurücksetzen.

## 9. Portfolio‑Analyse: ETF vs Aktie – Absolute Gewichte
Dieses Modul zeigt, wie stark ETFs und Einzelaktien dein Gesamtportfolio beeinflussen.
Es eignet sich besonders, um:

ETF‑Quote vs. Aktienquote zu prüfen

Klumpenrisiken zu erkennen

Portfolio‑Struktur zu analysieren

### 9.1 Oberfläche (Screenshot)
![ETF vs Aktie Chart](docs/screenshots/etf_vs_stock_chart.png)

### 9.2 Schritt‑für‑Schritt‑Ablauf
1️⃣ CSV‑Datei hochladen
Das Modul erwartet eine Datei mit Portfolio‑Positionen.

Beispiel‑CSV:
ticker,quantity,price,market_value
CSPX.L,10,500,5000
EQQQ.L,5,300,1500
AAPL,20,150,3000
MSFT,10,350,3500

Wenn du keine CSV hochlädst, zeigt das Dashboard Beispielpositionen an.

Screenshot‑Platzhalter:
[SCREENSHOT: csv_upload.png]

2️⃣ Gesamtportfolio‑Wert eingeben
Du kannst den Gesamtwert manuell eingeben (z. B. 100 000 €).
Wenn du das Feld leer lässt, wird automatisch die Summe der CSV‑Werte verwendet.

Screenshot‑Platzhalter:
[SCREENSHOT: total_portfolio_value.png]

3️⃣ ETFs auswählen
Im Dropdown kannst du auswählen, welche ETFs du analysieren möchtest.

Beispiel:

CSPX.L

EQQQ.L

Screenshot‑Platzhalter:
[SCREENSHOT: etf_selection_dropdown.png]

4️⃣ Berechnen
Mit dem Button „Berechnen“ startet die Analyse.

Screenshot‑Platzhalter:
[SCREENSHOT: calculate_button.png]

### 9.3 Ergebnisdarstellung
Nach der Berechnung zeigt das Dashboard:

🔹 Tabelle: Absolute Gewichte
Marktwert pro Position

Anteil am Gesamtportfolio

ETF‑Quote

Aktienquote

Screenshot‑Platzhalter:
[SCREENSHOT: weights_table.png]

🔹 Diagramm: ETF vs Aktie
Ein Balken‑ oder Tortendiagramm zeigt:

ETF‑Anteil

Aktien‑Anteil

ggf. Cash‑Anteil

Screenshot‑Platzhalter:
[SCREENSHOT: etf_vs_stock_chart.png]

### 9.4 Code‑Beispiel (für Dokumentation)
Damit Nutzer verstehen, wie die Berechnung funktioniert, kannst du folgenden Code‑Block einfügen:

import pandas as pd

# CSV laden
df = pd.read_csv("portfolio.csv")

# Gesamtwert berechnen
total_value = df["market_value"].sum()

# Gewichte berechnen
df["weight_pct"] = df["market_value"] / total_value * 100

# ETF vs Aktie
df["type"] = df["ticker"].apply(lambda x: "ETF" if x.endswith(".L") else "Stock")

summary = df.groupby("type")["market_value"].sum()
summary_pct = summary / total_value * 100

print("Gesamtportfolio:", total_value)
print("ETF-Anteil:", summary_pct.get("ETF", 0))
print("Aktien-Anteil:", summary_pct.get("Stock", 0))

### 9.5 Interpretation
ETF‑Anteil hoch (>70 %)  
→ Portfolio breit diversifiziert, risikoarm

Aktien‑Anteil hoch (>50 %)  
→ Klumpenrisiko möglich, abhängig von Einzeltiteln

Einzelposition >10 %  
→ potenzielles Risiko (Übergewichtung)

## 10. Export der Ergebnisse
[Anscheinend war das Ergebnis nicht sicher anzuzeigen. Lassen Sie uns die Dinge ändern und etwas anderes ausprobieren!]

Exportiert nach:
risk_dashboard/export/


## 11. Glossar
Begriff                 Bedeutung
ETF	                    Börsengehandelter Indexfonds
TER	                    Kostenquote
AUM	                    Fondsgröße
Tracking Difference	    Abweichung vom Index
Replikation	            Physisch / Synthetisch
HRP	                    Hierarchical Risk Parity
CAGR	                  Durchschnittliche jährliche Rendite
Volatilität	            Schwankungsbreite
Rebalancing	            Wiederherstellung der Zielgewichte
Backtest	              Simulation historischer Performance

## 12. Hinweis zu Screenshots
Lege deine PNG‑Dateien hier ab:
docs/screenshots/
Beispiel‑Dateinamen:

sidebar.png

preset.png

ranking.png

breakdown.png

performance.png

export_button.png




## Kurzüberblick (tabellarisch)

| **Feature** | **Zweck** | **UI Ort** | **Was es bedeutet** | **Beispiel / Wie nutzen** |
|-------------|-----------|------------|---------------------|---------------------------|
| **Explainable Scoring** | Bewertet ETFs nach mehreren Kriterien | ETF Auswahl und Explainable Scoring | Zerlegt Gesamtbewertung in Komponenten (TER, AUM, Tracking, Replikation, Liquidity) | Schiebe Gewichte, öffne Explain‑Expander, sieh Komponenten‑Beitrag |
| **Portfolio‑Breakdowns** | Zeigt, welche Aktien in einem ETF stecken und deren Anteil am Portfolio | ETF vs Aktie — Absolute Gewichte (Live) | Rechnet ETF‑Marktwert auf Underlyings herunter (weight_in_etf → abs_weight) | Lade Holdings‑CSV oder aktiviere Demo, klicke **Berechnen** |
| **Backtests** | Simuliert historische Performance und Kennzahlen | ETF Auswahl → Backtest‑Panel | Liefert Chart + Kennzahlen (CAGR, Volatilität, Sharpe, Max Drawdown) | Wähle Zeitraum und Rebalancing → **Backtest starten** |
| **Profile / Presets** | Vordefinierte Allokationen und Scoring‑Prioritäten | Preset‑Selector oben rechts | Setzt Allokationsvorschlag und relative Wichtigkeit der Scoring‑Komponenten | Wähle Preset (z. B. balanced), passe bei Bedarf manuell an |
| **User‑Ticker / CSV‑Import** | Eigene Positionen hinzufügen und persistieren | Sidebar (Ticker hinzufügen) + ETF vs Aktie CSV‑Uploader | Ticker werden gespeichert; CSV ermöglicht Bulk‑Import von Positionen | Nutze `docs/examples/portfolio_example.csv` als Vorlage |

---

## Wichtige Begriffe – ganz einfach erklärt

| Begriff | Einfache Erklärung |
|--------|--------------------|
| **TER** | Die jährlichen Gebühren eines ETFs. Je niedriger, desto besser. |
| **AUM** | Wie viel Geld im ETF steckt. Viel Geld = stabiler & leichter handelbar. |
| **Tracking** | Wie gut der ETF seinem Index folgt. Kleine Abweichung = gut. |
| **Replikation** | Wie der ETF den Index nachbildet: echte Aktien (physisch) oder über Verträge (synthetisch). Physisch ist meist transparenter. |
| **Liquidity** | Wie leicht man den ETF kaufen/verkaufen kann. Hohe Liquidität = niedrige Kosten. |
| **Herfindahl‑Index** | Misst, wie breit ein ETF gestreut ist. Niedrig = gut diversifiziert. |
| **weight_in_etf** | Wie viel Prozent ein einzelner Wert (z. B. Apple) im ETF ausmacht. |
| **abs_weight** | Wie viel Prozent ein einzelner Wert im **gesamten Portfolio** ausmacht. |


## Aktien vs. ETFs – so erkennst du den Unterschied

| Merkmal | Aktie | ETF |
|---------|-------|------|
| **Was ist es?** | Ein einzelnes Unternehmen (z. B. Apple) | Ein Korb aus vielen Aktien/Anleihen |
| **Ticker Beispiel** | AAPL, MSFT, NVDA | VWRL, AGGH, QQQ |
| **Hat TER?** | ❌ Nein | ✔️ Ja |
| **Hat AUM?** | ❌ Nein | ✔️ Ja |
| **Hat Replikation?** | ❌ Nein | ✔️ Ja |
| **Hat Tracking‑Error?** | ❌ Nein | ✔️ Ja |
| **Wird im Explain‑Scoring bewertet?** | ❌ Nein | ✔️ Ja |
| **Wird im Breakdown angezeigt?** | ✔️ Ja (als Underlying) | ✔️ Ja (als ETF‑Position) |
| **Typische Nutzung** | Einzelwert‑Wette | Diversifiziertes Investment |

| **Key** | **Typ** | **Grund / Erkennungsregel** | **Vorgeschlagener Ticker** |
|---------|---------|-----------------------------|----------------------------|
| aggregate_bond_etf | ETF | Erwartete Metadaten (TER/AUM/replication) | AGGH / AGG |
| government_bonds | ETF | Bond‑Kategorie → Metadaten erwartet | GOVT / IEGA |
| emerging_markets | ETF | Equity‑Universe Key → Metadaten erwartet | IEMG / EEM |
| small_cap | ETF | Kategorie „small_cap“ → Metadaten erwartet | IWM / SMLL |
| short_term_cash | ETF | Cash/Short‑term → Metadaten erwartet | SHV / VGSH |
| investment_grade_corporates | ETF | Bond‑Kategorie → Metadaten erwartet | LQD / IGLB |
| qqq | ETF | Bekannter ETF‑Key | QQQ |
| arkk | ETF | Bekannter ETF‑Key | ARKK |
| voo | ETF | Bekannter ETF‑Key | VOO |
| aggh | ETF | Doppelter Bond‑Key (hedged) | AGGH |
| bndx | ETF | Bekannter Intl Bond ETF | BNDX |
| imeu_l | ETF | Europe Listing → Metadaten erwartet | IMEU.L / IEUR |
| iqq0_de | ETF | DE‑Listing → Metadaten erwartet | IQQ0.DE |
| xtrackers_dax | ETF | DAX‑ETF Key → Metadaten erwartet | XDAX / DAXX.DE |
| amundi_faz_100 | ETF | Produktname → Metadaten prüfen | (prüfen) |
| global_equity_etf | ETF | Welt‑ETF Key → Metadaten erwartet | VWRL / IWDA |
| amundi_dax50_esg | ETF | Produktname → Metadaten prüfen | (prüfen) |
| tech_package | Custom / Basket | Kein einzelner Ticker; Bündel/Strategie | (kein einzelner Ticker) |
| apple | Aktie | Einzelunternehmen (kein TER/AUM) | AAPL |
| microsoft | Aktie | Einzelunternehmen | MSFT |
| siemens | Aktie | Einzelunternehmen (DE‑Listing) | SIE.DE |
| nvda | Aktie | Einzelunternehmen | NVDA |
| amazon | Aktie | Einzelunternehmen | AMZN |

## Schnell‑Checkliste: ETF vs. Aktie & Wichtige Prüfungen

- **Unterscheidung ETF / Aktie**
  - Prüfe: Hat der Eintrag **TER** oder **AUM**? → **Ja** = ETF; **Nein** = Aktie.
  - Prüfe: Hat der Eintrag **Replikation** oder **Tracking‑Daten**? → **Ja** = ETF.

- **Vor dem Hinzufügen eines ETFs**
  - Prüfe Ticker‑Format (z. B. `.L`, `.DE`, ohne Listing prüfen).
  - Ergänze Metadaten: `ticker`, `name`, `expense_ratio`, `aum`, `replication`.
  - Lege Backup an: `copy etf_universe.yaml etf_universe.yaml.bak`.

- **Beim CSV‑Upload (Portfolio / Holdings)**
  - Portfolio CSV: Spalten `ticker,quantity,price,market_value`.
  - Holdings CSV: Spalten `ticker,weight_in_etf`.
  - Validiere: Summe `weight_in_etf` ≈ 1.0 (oder 100%).

- **Beim Scoring / Explain‑Expander**
  - Öffne Explain‑Expander: prüfe Komponenten (TER, AUM, Tracking, Replication, Liquidity).
  - Passe Slider‑Gewichte an; klicke **Aktualisieren** und vergleiche Rangliste.

- **Backtest‑Checks**
  - Prüfe Preisdaten: `download_prices()` liefert Werte für alle gewählten Ticker.
  - Setze Zeitraum und Rebalancing; vergleiche CAGR, Volatilität, Sharpe, Max Drawdown.

- **Nach manuellen Änderungen**
  - Leere Cache / migriere persistente Keys (`.cache/user_tickers.json`) falls Keys geändert wurden.
  - Suche/ersetze alte Keys im Repo; teste UI und Backtest lokal.

- **Schnelle Entscheidungshilfe**
  - **ETF** wählen wenn: Diversifikation + niedrige TER + hohe AUM wichtig.  
  - **Aktie** wählen wenn: gezielte Einzelwert‑Wette gewünscht.


## Quickstart (Tabellarisch, ausführlich)

| **Schritt** | **Aktion** | **UI Ort** | **Erwartetes Ergebnis** | **Hinweis** |
|-------------|------------|------------|-------------------------|-------------|
| 1 | **App starten** | Terminal / Projekt‑Root | Streamlit‑App öffnet sich im Browser | `python -m streamlit run risk_dashboard/app.py` |
| 2 | **Preset wählen** | Oben rechts im Dashboard | Preset wird geladen; Scoring‑Gewichte gesetzt | Siehe Preset‑Tabelle unten für Bedeutung |
| 3 | **Ticker manuell hinzufügen** | Sidebar (links) → *Ticker hinzufügen* | Ticker erscheint in der Sidebar‑Liste; persistiert in `.cache/user_tickers.json` | Beispiel: `VWRL.L`, `AGGB.L` |
| 4 | **Portfolio per CSV laden** | Tab *ETF vs Aktie — Absolute Gewichte* → *Portfolio CSV* | Portfolio‑Tabelle wird geladen; Marktwerte berechnet | CSV‑Format: `ticker,quantity,price,market_value` |
| 5 | **ETF‑Universe prüfen / erweitern** | Datei: `risk_dashboard/config/etf_candidates.py` | Zusätzliche ETFs erscheinen in Scoring/Rangliste | Nur ETFs mit Metadaten (TER/AUM/Replication) werden gerankt |
| 6 | **ETF Auswahl & Scoring prüfen** | Tab *ETF Auswahl and Explainable Scoring* | Rangliste mit Komponenten‑Scores; Top‑N auswählbar | Gewichte (TER/AUM/Tracking/Replication/Liquidity) per Slider anpassen |
| 7 | **Explain‑Expander öffnen** | In der Rangliste neben jedem ETF | Sicht auf Komponenten‑Scores und Beitrag zum Gesamt‑Score | Nutze das, um Entscheidungen nachzuvollziehen |
| 8 | **Backtest ausführen** | ETF‑Tab → Start/Enddatum → **Backtest starten** | Chart + Metriken (CAGR, Vol, Sharpe, MaxDD) | Rebalancing‑Intervall optional setzen |
| 9 | **ETF Breakdowns (Underlyings)** | Tab *ETF vs Aktie — Absolute Gewichte* → Holdings CSV oder Demo | Liste der Underlyings mit `weight_in_etf` und `abs_weight_in_portfolio` | Lade Holdings CSV: `ticker,weight_in_etf` |
| 10 | **Iterieren & vergleichen** | Überall | Neue Scoring‑Konfigurationen und Backtests vergleichen | Änderungen speichern, Ergebnisse dokumentieren |

---

### Presets (ausführlich)
| **Preset** | **Kurzbeschreibung** | **Typische Allokation / Fokus** |
|------------|----------------------|---------------------------------|
| **\<Neu\>** | Leeres / neues Preset zum Anlegen eigener Einstellungen | Keine Voreinstellung; du definierst Gewichte |
| **conservative** | Niedriges Risiko; Fokus auf Kapitalerhalt | Mehr Anleihen, weniger Aktien; TER sekundär |
| **conservative_(low)** | Sehr konservativ; besonders risikoarm | Hoher Anleihenanteil, sehr geringe Aktienquote |
| **balanced** | Moderates Risiko; ausgewogenes Wachstum vs. Stabilität | Ca. 40–60% Aktien, Rest Anleihen/Cash |
| **balanced_(medium)** | Leicht aktienbetonter als `balanced` | Etwas höhere Aktienquote für mehr Rendite |
| **aggressive** | Höheres Risiko; Fokus auf Wachstum | Hoher Aktienanteil; größere Schwankungen möglich |

---
**ticker,quantity,price,market_value**
- VWRL,10,80,800
- AGGB,50,20,1000
- AAPL,5,150,750
- CASH,1,1,10000

**Holdings CSV (für ETF‑Breakdown)**  
- ticker,weight_in_etf
- AAPL,0.30
- MSFT,0.25
- NVDA,0.15
- AMZN,0.10

---

**Tipps für Einsteiger**  
- Starte mit **balanced** und teste eine einzelne Änderung (z. B. TER‑Gewicht erhöhen).  
- Nutze `docs/examples/portfolio_example.csv` zum schnellen Testen.  
- Lege Screenshots in `docs/screenshots/` ab, damit die Dokumentation visuell unterstützt wird.


## Explain‑Expander (Was ist das und wie nutze ich es)

| **Element** | **UI Ort** | **Zweck** | **Kurzbeschreibung** | **Wie nutzen** |
|-------------|------------|----------:|---------------------|----------------|
| **Explain‑Expander** | Rangliste im Tab **ETF Auswahl und Explainable Scoring**, rechts neben jedem ETF | Erklärt, **warum** ein ETF so gerankt wurde | Zeigt Komponenten‑Scores (TER, AUM, Tracking, Replication, Liquidity) und deren gewichteten Beitrag zum Gesamt‑Score | Klick auf das Dreieck / „Details“ neben einem ETF, lies die Komponenten, passe Slider an und beobachte die Score‑Änderung |
| **Komponenten‑Zeile** | Innerhalb des Expander‑Panels | Detaillierte Bewertung einzelner Kriterien | z. B. „TER: 0.85 (niedrige Kosten) → +12 Punkte“ | Vergleiche zwischen ETFs; priorisiere Kriterien durch Slider |
| **Gesamt‑Score‑Bar** | Oben im Expander | Aggregierter Einfluss aller Komponenten | Prozentuale Aufteilung der Komponenten zum Total | Nutze als Entscheidungsgrundlage für Top‑N Auswahl |
| **Quellen / Metadaten** | Unten im Expander | Herkunft der Daten (Universe, CSV, API) | z. B. „TER aus etf_candidates; AUM aus Provider X“ | Prüfe Quelle bei Unklarheiten; ergänze Metadaten bei Bedarf |

---

### Schritt‑für‑Schritt: Explain‑Expander verwenden (Anfänger)
1. Öffne **ETF Auswahl and Explainable Scoring**.  
2. Suche den ETF in der Rangliste.  
3. Klicke das kleine Dreieck / „Details“ rechts neben dem ETF‑Namen.  
4. Lies die Komponenten‑Scores und kurze Kommentare.  
5. Passe die Slider für TER/AUM/Tracking/Replication/Liquidity an.  
6. Beobachte, wie sich **Gesamt‑Score** und Rangliste ändern.  
7. Triff eine Auswahl (Top‑N) basierend auf den erklärten Gründen.

---

### Beispiele (konkret, tabellarisch)
| **Szenario** | **Was du siehst im Expander** | **Empfohlene Aktion** |
|--------------|-------------------------------|-----------------------|
| Kostenfokus | TER‑Score niedrig → negativer Beitrag | TER‑Gewicht erhöhen (mehr Gewicht auf niedrige Kosten) |
| Liquidität wichtig | Liquidity‑Score niedrig → Warnung | AUM/Liquidity‑Gewicht erhöhen; ETFs mit höherer AUM bevorzugen |
| Tracking wichtig | Tracking‑Score schlecht → Abzug | Tracking‑Gewicht erhöhen; nach besser replizierenden ETFs filtern |

---

### Screenshot‑Platzhalter
Füge ein Bild ein, das den Expander zeigt (Platzhalter):  
`![Explain Expander](docs/screenshots/explain_expander.png)`  

(Lege die Datei `docs/screenshots/explain_expander.png` ab; die Bildunterschrift kann kurz erklären: *„Explain‑Expander: Komponenten‑Scores und Gesamt‑Score“*.)


## Tabs und UI‑Übersicht

| **Tab** | **Zweck** | **UI Ort** | **Eingaben** | **Ausgabe / Aktion** |
|---|---:|---|---|---|
| **Portfolio Eingabe** | Eigene Positionen erfassen und Gesamtportfolio definieren | **Sidebar (links)** oder *ETF vs Aktie — Absolute Gewichte* (CSV‑Uploader) | Manuelle Ticker‑Eingabe; CSV `ticker,quantity,price,market_value` | Persistierte Ticker (`.cache/user_tickers.json`); berechnete Marktwerte; Basis für Breakdowns und Backtests |
| **ETF Auswahl und Explainable Scoring** | ETFs bewerten, erklären und Kandidaten auswählen | **Tab: ETF Auswahl and Explainable Scoring** | Preset (z. B. balanced), ETF‑Universe, Gewichtungs‑Slider (TER/AUM/Tracking/Replication/Liquidity) | Rangliste mit **Komponenten‑Scores** und Gesamt‑Score; Top‑N Auswahl; Explain‑Expander pro ETF |
| **ETF vs Aktie — Absolute Gewichte (Live)** | ETF → Underlyings auf Portfolio‑Ebene aufschlüsseln | **Tab: ETF vs Aktie — Absolute Gewichte (Live)** | Portfolio (CSV oder manuelle Ticker), Holdings CSV pro ETF (`ticker,weight_in_etf`) oder Demo | Tabelle: `weight_in_etf`, `abs_weight_in_portfolio`; Visualisierung der Exposure zu Einzelaktien |
| **Backtest** | Historische Performance und Kennzahlen simulieren | **Backtest‑Panel im ETF‑Tab** (Start/Enddatum, Rebalancing) | Ausgewählte ETFs, Zeitfenster, Rebalancing‑Intervall | Chart (kumulative Performance); Kennzahlen: **CAGR**, **Volatilität**, **Sharpe**, **Max Drawdown**; Gewichtshistorie |
| **Lexikon / Hilfe** | Dokumentation, Glossar, Quickstart, FAQs | **Tab: Lexikon / Hilfe** oder neuer Dokumentations‑Tab | Keine (statische Inhalte) | Schritt‑für‑Schritt Anleitungen, Glossar, Screenshots, Troubleshooting |

---

## Explain‑Expander finden und nutzen

| **Element** | **UI Ort** | **Zweck** | **Kurzbeschreibung** | **Wie nutzen** |
|-------------|------------|----------:|---------------------|----------------|
| **Explain‑Expander** | Rechts neben jedem ETF in der Rangliste im Tab **ETF Auswahl and Explainable Scoring** | Erklärt, **warum** ein ETF so gerankt wurde | Zeigt Komponenten‑Scores (TER, AUM, Tracking, Replication, Liquidity) und deren gewichteten Beitrag zum Gesamt‑Score | Klick auf das kleine Dreieck / „Details“ neben dem ETF → lies die Komponenten → passe die Slider an → beobachte Score‑Änderung |
| **Komponenten‑Zeile** | Innerhalb des Expander‑Panels | Detaillierte Bewertung einzelner Kriterien | z. B. „TER: 0.85 (niedrige Kosten) → +12 Punkte“ | Vergleiche zwischen ETFs; erkenne Treiber für hohe/niedrige Platzierung |
| **Gesamt‑Score‑Bar** | Oben im Expander | Aggregierter Einfluss aller Komponenten | Prozentuale Aufteilung der Komponenten zum Total | Nutze als Entscheidungsgrundlage für Top‑N Auswahl |
| **Quellen / Metadaten** | Unten im Expander | Herkunft der Daten (Universe, CSV, API) | z. B. „TER aus etf_candidates; AUM aus Provider X“ | Prüfe Quelle bei Unklarheiten; ergänze Metadaten bei Bedarf |

---

### Schritt‑für‑Schritt: Explain‑Expander verwenden (Anfänger)
1. Öffne **ETF Auswahl and Explainable Scoring**.  
2. Suche den ETF in der Rangliste.  
3. Klicke das kleine Dreieck / „Details“ rechts neben dem ETF‑Namen (Explain‑Expander).  
4. Lies die Komponenten‑Scores und kurze Kommentare.  
5. Passe die Slider für TER/AUM/Tracking/Replication/Liquidity an.  
6. Beobachte, wie sich **Gesamt‑Score** und Rangliste ändern.  
7. Triff eine Auswahl (Top‑N) basierend auf den erklärten Gründen.

---

## Rebalancing — Definition (einfach)

Rebalancing ist die periodische Anpassung der Portfoliozusammensetzung, um eine **Zielallokation** (z. B. 60 % Aktien / 40 % Anleihen) wiederherzustellen. Es reduziert unbeabsichtigte Risikoänderungen, die durch unterschiedliche Wertentwicklungen entstehen.

## Häufige Rebalancing‑Strategien (Vergleichstabelle)

| **Strategie** | **Wie** | **Vorteil** | **Nachteil / Hinweis** |
|---------------|---------|-------------|------------------------|
| **Calendar (zeitbasiert)** | Rebalancen in festen Intervallen, z. B. jährlich oder vierteljährlich | Einfach umzusetzen; planbar | Kann unnötig handeln, wenn Abweichungen klein sind |
| **Threshold (schwellenbasiert)** | Rebalancen nur wenn Abweichung vom Ziel > Schwelle, z. B. ±5 % | Handel nur bei relevanter Drift; kosteneffizienter | Erfordert laufendes Monitoring; Auslösung unregelmäßig |
| **Hybrid (Zeit + Schwelle)** | Prüfe periodisch (z. B. jährlich) und rebalanciere nur wenn Drift > Schwelle | Kombiniert Disziplin mit Effizienz | Etwas komplexer zu implementieren |
| **Cash‑flow / Contribution** | Nutze neue Einlagen/Entnahmen, um Zielallokation wiederherzustellen (nur Käufe) | Minimiert Verkäufe; steuer‑ und kosteneffizient | Funktioniert nur bei regelmäßigem Zufluss |
| **Tolerance bands (mehrstufig)** | Unterschiedliche Schwellen pro Assetklasse (z. B. Aktien ±6%, Bonds ±4%) | Feiner steuerbare Reaktionen pro Asset | Komplexere Regeln und UI nötig |

## Kurzes Beispiel
Ziel: **60 % Aktien / 40 % Anleihen**  
Aktuell: **75 % Aktien / 25 % Anleihen** → Rebalancing verkauft Aktien im Umfang von 15 % des Portfoliowerts und kauft Anleihen, um wieder 60/40 zu erreichen.

## Praktische Empfehlungen
- Für die meisten Privatanleger ist **jährlich + Schwelle 5 %** ein guter Kompromiss.  
- Berücksichtige **Transaktionskosten** und **Steuern**; biete Option „nur neue Mittel verwenden“ für steueroptimiertes Rebalancing.  
- Im Backtest: simuliere Rebalancing‑Regeln und zeige Auswirkungen auf Rendite, Volatilität und Turnover.

### Beispiele (konkret, tabellarisch)

| **Szenario** | **Was du siehst im Expander** | **Empfohlene Aktion** |
|--------------|-------------------------------|-----------------------|
| Kostenfokus | TER‑Score niedrig → negativer Beitrag | TER‑Gewicht erhöhen (mehr Gewicht auf niedrige Kosten) |
| Liquidität wichtig | Liquidity‑Score niedrig → Warnung | AUM/Liquidity‑Gewicht erhöhen; ETFs mit höherer AUM bevorzugen |
| Tracking wichtig | Tracking‑Score schlecht → Abzug | Tracking‑Gewicht erhöhen; nach besser replizierenden ETFs filtern |

---

### Kurze Hinweise
- Einzelaktien zeigen keinen Explain‑Expander (fehlende ETF‑Metadaten).  
- Nutze `docs/examples/portfolio_example.csv` als Upload‑Vorlage.  
- Wenn Daten merkwürdig erscheinen, prüfe die Metadatenquelle (`risk_dashboard/config/etf_candidates.py`) und die Holdings‑CSV.


## Datenfluss & Zusammenhänge

| **Schritt** | **Prozess** | **Eingabe** | **Funktion / Code‑Referenz** | **Ausgabe / Ergebnis** | **Hinweis** |
|-------------|-------------|-------------|------------------------------|------------------------|-------------|
| 1 | **Input** | User‑Ticker (Sidebar) + vordefiniertes ETF‑Universe | — | Liste von Tickers/ETFs für weitere Verarbeitung | Ticker aus Sidebar werden in `.cache/user_tickers.json` persistiert |
| 2 | **Anreicherung** | ETF‑Liste aus Schritt 1 | Metadaten laden aus `risk_dashboard/config/etf_candidates.py` oder konfigurierten Dateien | Metadaten pro ETF (TER, AUM, Replication, evtl. Liquidity) | Fehlende Metadaten markieren; nur vollständige ETFs vollständig bewertbar |
| 3 | **Scoring** | ETF + Metadaten + gewählte Preset‑Gewichte | `compute_etf_score_components()` → berechnet Komponenten‑Scores; Aggregation mit Preset‑Gewichten | Komponenten‑Scores (TER, AUM, Tracking, Replication, Liquidity) und Gesamt‑Score | Preset steuert relative Gewichtung der Komponenten |
| 4 | **Auswahl** | Rangliste mit Scores | UI: Top‑N Auswahl oder manuelle Auswahl (Multiselect) | Ausgewählte ETFs für Backtest/Breakdown | Auswahl wird an nachfolgende Module weitergereicht |
| 5 | **Backtest** | Ausgewählte ETFs, Zeitfenster, Rebalancing‑Einstellungen | `download_prices()` → Preisdaten; `run_backtest()` → Simulation | Chart (kumulative Performance), Kennzahlen (CAGR, Vol, Sharpe, MaxDD), Gewichtshistorie | Prüfe, ob `download_prices()` valide Daten liefert; sonst Fehlermeldung |
| 6 | **Breakdown** | ETF‑Marktwert (aus Portfolio) + Holdings CSV (oder Demo) | `compute_etf_breakdown(etf_market_value, holdings_df, portfolio_value)` | Tabelle mit `ticker`, `weight_in_etf`, `abs_weight_in_portfolio` | Holdings CSV Format: `ticker,weight_in_etf`; Demo‑Holdings verfügbar wenn keine Datei |

---


## Wichtige Kennzahlen & Begriffe (Lexikon)

| **Begriff** | **Abkürzung** | **Kurzdefinition** | **Anwendung / Warum wichtig** |
|-------------|---------------|--------------------|-------------------------------|
| Total Expense Ratio | TER | Jährliche Kostenquote eines ETFs (in %). | Beeinflusst Netto‑Rendite; niedriger ist kostenvorteilhaft. |
| Assets Under Management | AUM | Gesamtvermögen, das ein Fonds verwaltet (Währungseinheit). | Höhere AUM → tendenziell bessere Liquidität und Stabilität. |
| Tracking Error | — | Statistische Abweichung der ETF‑Rendite vom Referenzindex. | Niedrigerer Tracking Error → bessere Indexabbildung. |
| Replikation | — | Art der Indexabbildung: physisch (Holdings) oder synthetisch (Derivate). | Physisch oft bevorzugt; Replikation beeinflusst Risiko/Transparenz. |
| Spread / Liquidität | — | Geld/Brief‑Spread und Handelsvolumen; misst Handelbarkeit. | Enger Spread & hohes Volumen → geringere Handelskosten. |
| Herfindahl‑Index | — | Konzentrationsmaß: Summe der quadrierten Gewichtanteile. | Niedriger Wert → bessere Diversifikation; hoher Wert → Konzentrationsrisiko. |
| Absolute Gewicht | — | Anteil einer Position am Gesamtportfolio (Marktwert / Portfoliowert). | Zeigt Exposure einzelner Positionen in Prozent. |
| weight_in_etf | — | Anteil eines Underlyings innerhalb eines ETFs (z. B. 0.30 = 30%). | Grundlage für ETF‑Breakdown und Exposure‑Berechnung. |
| abs_weight | — | Absolute Gewichtung eines Underlyings im Portfolio (ETF‑Anteil × weight_in_etf). | Zeigt tatsächliche Portfolio‑Exposure zu Einzelwerten. |
| CAGR | — | Annualisierte Wachstumsrate über einen Zeitraum (Compound Annual Growth Rate). | Standardmaß für langfristige Renditevergleiche. |
| Volatilität | — | Standardabweichung der Renditen (jährisiert). | Maß für Schwankungsbreite / Risiko. |
| Sharpe Ratio | — | Überschussrendite geteilt durch Volatilität. | Bewertet Rendite im Verhältnis zum Risiko; höher = besser. |
| Max Drawdown | — | Größter kumulativer Verlust vom Peak zum Tiefpunkt. | Misst Extremverlust‑Risiko; wichtig für Stress‑Tests. |

---

## Kurze Erläuterungen (1‑Zeiler)

- **TER**: Jährliche Kostenquote eines ETFs; senkt die Netto‑Rendite.  
- **AUM**: Fondsvolumen; größere AUM → bessere Liquidität und geringeres Schließungsrisiko.  
- **Tracking Error**: Wie stark die ETF‑Rendite vom Index abweicht; niedriger ist besser.  
- **Replikation**: Physisch vs. synthetisch; physisch bietet oft mehr Transparenz.  
- **Spread / Liquidität**: Handelskosten und Ausführbarkeit; enger Spread reduziert Kosten.  
- **Herfindahl‑Index**: Misst Konzentration; niedriger → breiter diversifiziert.  
- **Absolute Gewicht**: Anteil einer Position am Gesamtportfolio in Prozent.  
- **weight_in_etf**: Anteil eines Underlyings im ETF; Grundlage für Breakdowns.  
- **abs_weight**: Tatsächliche Portfolio‑Exposure eines Underlyings (ETF‑Anteil × weight_in_etf).  
- **CAGR**: Annualisierte Rendite über einen Zeitraum; nützlich für Vergleich.  
- **Volatilität**: Risiko‑Maß; zeigt Schwankungsbreite der Renditen.  
- **Sharpe Ratio**: Rendite pro Einheit Risiko; hilft bei Risiko‑adjustierten Vergleichen.  
- **Max Drawdown**: Größter historischer Verlust; wichtig für Risikotoleranz‑Checks.

## Manuelle Eingriffe & Best Practices

| **Aktion** | **Ort / Datei** | **Was tun** | **Beispiel / Hinweis** |
|------------|-----------------|-------------|------------------------|
| **ETF hinzufügen** | `risk_dashboard/config/etf_candidates.py` oder `etf_universe.yaml` | Ergänze Einträge mit `ticker`, `name`, `expense_ratio`, `aum`, `replication` | Format: `{"ticker":"VWRL.L","name":"Vanguard...","expense_ratio":0.0022,"aum":8000000000,"replication":"physical"}` |
| **Holdings hochladen** | UI: *ETF vs Aktie — Absolute Gewichte* → Holdings‑Upload | Lade CSV mit `ticker,weight_in_etf` für ETF‑Breakdown hoch; Demo‑Holdings nur zu Testzwecken | CSV‑Beispiel: `AAPL,0.30` |
| **Ticker‑Persistenz** | `.cache/user_tickers.json` | User‑Ticker werden automatisch gespeichert; vor manuellen Änderungen Backup anlegen | Backup: `copy .cache\user_tickers.json .cache\user_tickers.json.bak` |
| **Gewichte anpassen** | Tab *ETF Auswahl and Explainable Scoring* (Slider) | Nutze Presets oder passe TER/AUM/Tracking/Replication/Liquidity per Slider an; Rangliste neu berechnen | Nach Änderung auf **Aktualisieren** klicken, um neue Rangfolge zu sehen |
| **Aktien vs. ETFs** | UI + Config | Einzelaktien (z. B. AAPL) werden gespeichert und in Breakdowns angezeigt, aber nicht im ETF‑Scoring bewertet | Für Aktienanalysen separate Sektion/Workflow anlegen |
| **Dateiänderungen** | alle config/.py/.yaml Dateien | Vor manuellen Änderungen immer Backup erstellen; validiere Syntax nach Edit | Beispiel Backup: `Copy-Item risk_dashboard\config\etf_candidates.py risk_dashboard\config\etf_candidates.py.bak` |
| **Fehlerprüfung** | Logs / UI‑Meldungen | Prüfe Fehlermeldungen (z. B. fehlende Metadaten, keine Preisdaten) und korrigiere Metadaten oder CSV | `download_prices()` muss valide Daten liefern für Backtests |

## Was genau passiert, wenn du einen Preset‑Button klickst

- **Ersetzt die erlaubten Instrumente**  
  Die aktuelle Liste „Erlaubte ETFs/Instrumente“ wird durch die Preset‑Liste (z. B. Conservative/Balanced/Aggressive) **ersetzt**. Vorher ausgewählte ETFs werden entfernt und durch die Preset‑ETFs ersetzt.

- **Gewichte und Normalisierung**  
  Wenn **Auto‑normalize** aktiv ist, werden die Gewichte der neuen erlaubten ETFs automatisch so skaliert, dass sie zusammen 100 % ergeben. Wenn Auto‑normalize aus ist, bleiben die Gewichte unverändert und du musst manuell anpassen.

- **Zielallokation bleibt unverändert (Standardverhalten)**  
  Der Button ändert **nur**, welche Instrumente erlaubt sind. Die **Zielallokation** (z. B. 60 % Aktien / 40 % Anleihen), die in den Profil‑Einstellungen steht, wird **nicht** automatisch überschrieben, außer es gibt einen separaten Button oder eine Option „Mit Kategorie‑Defaults überschreiben“.

- **Keine echten Orders**  
  UI‑Änderungen erzeugen keine Käufe/Verkäufe. Trades werden nur erzeugt, wenn du danach explizit Rebalancing/Orders bestätigst oder exportierst.

## Wichtige Details und Fallen

- **Preset ersetzt, fügt nicht hinzu**  
  Klick = Austausch. Wenn du bestehende Auswahl behalten willst, kopiere sie vorher oder füge Preset‑ETFs manuell hinzu.

- **Key‑Namen müssen exakt übereinstimmen**  
  Presets referenzieren interne Keys (z. B. `cash`, `equity_etf`). Fehlt ein Key im `etf_universe.yaml`, bleibt der Platz leer und die UI zeigt eine Warnung.

- **Aktiviere/Deaktiviere Auto‑normalize bewusst**  
  Auto‑normalize verhindert Summenfehler, kann aber gewünschte manuelle Gewichtungen überschreiben.

- **Zielallokation vs. erlaubte Instrumente**  
  - *Erlaubte Instrumente* = welche ETFs/Assets im Portfolio verwendet werden dürfen.  
  - *Zielallokation* = prozentuale Aufteilung zwischen Assetklassen (z. B. Aktien/Bonds/Cash).  
  Standard: Preset‑Button ändert **nur** die erste Liste. Wenn du willst, dass die Zielallokation ebenfalls angepasst wird, nutze die separate Option **„Mit Kategorie‑Defaults überschreiben“** oder passe die Zielallokation manuell an.

- **Steuern, Kosten, Slippage**  
  Rebalancing nach Preset kann Transaktionskosten und steuerliche Realisationen auslösen. Simuliere Backtest/Costs vor Live‑Trades.

- **Custom/Basket Items**  
  Presets können auch Custom‑Keys (z. B. `tech_package`) setzen. Prüfe, ob diese Komponenten korrekt definiert sind (components + weights).

- **Backup vor Änderung**  
  Immer vorher `etf_universe.yaml` und aktuelle Auswahl exportieren oder Backup anlegen.

## Kurzbeispiel zur Verdeutlichung

- Vorher: erlaubte ETFs = [VWRL, AGGH], Zielallokation = 60/40  
- Klick: **Set Aggressive ETFs** → erlaubte ETFs = [QQQ, ARKK, VWRL] (alte Auswahl weg)  
- Ergebnis: Zielallokation bleibt 60/40, es sei denn du klickst zusätzlich **„Mit Kategorie‑Defaults überschreiben“**.


## Fehlerbehebung & FAQs
- **App startet nicht / SyntaxError**: Prüfe, ob versehentliches Clipboard‑Fragment (z. B. ``) in einer `.py`‑Datei steht. Entfernen und neu starten.  
- **Keine Preisdaten**: Prüfe Netzwerkzugang und Ticker‑Suffixe (.L, .DE, US‑Ticker).  
- **Backtest liefert leere Ergebnisse**: Prüfe, ob `download_prices()` Daten zurückliefert; Index‑Ticker korrekt?  
- **Persistenz funktioniert nicht**: Prüfe Schreibrechte für `.cache/`.

## Anhang: Wichtige Dateipfade
- `risk_dashboard/app.py` — Haupt‑Entry.  
- `risk_dashboard/ui/etf_selection_ui.py` — ETF Auswahl UI.  
- `risk_dashboard/core/etf_tools.py` — Scoring & Preis‑Download.  
- `risk_dashboard/utils/persistence.py` — save/load user tickers.  
- `risk_dashboard/config/etf_candidates.py` oder `risk_dashboard/config/etf_universe.yaml` — ETF‑Universe.  
- `docs/dashboard_guide.md` — diese Dokumentation.

## Kontakt / Weiteres
Wenn du möchtest, kann ich Beispiel‑ETFs in `etf_candidates.py` anlegen, Demo‑Holdings erweitern oder eine kurze Video‑Anleitung als Textskript schreiben.

### Beispiel Workflow ETF Breakdowns
1. Sidebar → CSV hochladen oder manuell Ticker hinzufügen (z. B. VWRL, AGGB).  
2. Tab "ETF Auswahl und Explainable Scoring" → Preset "Balanced" wählen → Top‑N auswählen.  
3. Tab "ETF vs Aktie — Absolute Gewichte" → Wähle VWRL aus Portfolio → Upload Holdings CSV oder aktiviere Demo‑Holdings.  
4. Klicke "Berechnen" → sieh die absolute Gewichtung der Underlyings (z. B. AAPL 30%, MSFT 30% …).

### Screenshots Platzhalter
 **Screenshot 1**: Sidebar mit "Ticker hinzufügen" und geladenen User‑Tickern.  
  `![Screenshot Sidebar](docs/screenshots/sidebar.png)`  
 **Screenshot 2**: ETF Auswahl Rangliste mit Explainable Scores.  
  `![Screenshot Scoring](docs/screenshots/scoring.png)`  
 **Screenshot 3**: ETF Breakdown Ergebnis (absolute Gewichte).  
  `![Screenshot Breakdown](docs/screenshots/breakdown.png)`

Hinweis: Lege die Bilder in `docs/screenshots/` ab. Die Platzhalter werden automatisch angezeigt, wenn die Dateien vorhanden sind.


| **Key** | **Vorgeschlagener Ticker** | **Name / Kommentar** |
|---------|----------------------------|----------------------|
| aggregate_bond_etf | AGGH / AGG | iShares Core Global Aggregate Bond (hedged / unhedged je Region) |
| government_bonds | GOVT / IEGA | Staatsanleihen‑ETF (regionale Varianten möglich) |
| emerging_markets | IEMG / EEM | Emerging Markets Equity ETF |
| small_cap | IWM / SMLL | US Small‑Cap / Small‑Cap ETF |
| short_term_cash | SHV / VGSH | Kurzfristige Staatsanleihen / Geldmarkt ETF |
| investment_grade_corporates | LQD / IGLB | Investment Grade Corporate Bond ETF |
| qqq | QQQ | Invesco QQQ Trust (NASDAQ‑100) |
| arkk | ARKK | ARK Innovation ETF |
| voo | VOO | Vanguard S&P 500 ETF |
| aggh | AGGH | iShares Global Aggregate Bond Hedged |
| bndx | BNDX | Vanguard Total International Bond ETF |
| imeu_l | IMEU.L / IEUR | iShares MSCI Europe (L‑Listing / IE Listing) |
| iqq0_de | IQQ0.DE | iShares Core DAX (DE‑Listing) |
| xtrackers_dax | XDAX / DAXX.DE | Xtrackers DAX UCITS ETF (je Listing) |
| amundi_faz_100 | (prüfen) | Amundi F.A.Z. 100 — lokales Tickerformat prüfen |
| global_equity_etf | VWRL / IWDA | Vanguard FTSE All‑World / iShares MSCI World All‑World |
| amundi_dax50_esg | (prüfen) | Amundi DAX 50 ESG — lokales Tickerformat prüfen |
| tech_package | (kein einzelner Ticker) | Custom Basket; alternativ: QQQ, VGT |
| apple | AAPL | Aktie Apple |
| microsoft | MSFT | Aktie Microsoft |
| siemens | SIE.DE | Aktie Siemens (DE‑Listing) |
| nvda | NVDA | Aktie NVIDIA |
| amazon | AMZN | Aktie Amazon |


## Empfohlene zusätzliche ETFs pro Risikoprofil

| **Risikoprofil** | **Empfohlene Keys** | **Warum diese?** |
|------------------|---------------------|------------------|
| **Low Risk** | aggregate_bond_etf, government_bonds, investment_grade_corporates, short_term_cash | Sehr defensiv, hohe Stabilität, geringe Volatilität |
| **Medium Risk** | global_equity_etf, aggregate_bond_etf, small_cap | Ausgewogen: Aktien + Bonds + etwas Wachstum |
| **High Risk** | global_equity_etf, emerging_markets, small_cap | Wachstumsorientiert, höhere Schwankungen |


## 1. Überblick
Das Dashboard dient zur Bewertung und Analyse von ETF‑Portfolios nach Risiko‑Profilen (Conservative, Balanced, Aggressive).

## 2. Tabs und Bereiche
| Bereich | Zweck | Eingriffsmöglichkeiten |
|----------|--------|------------------------|
| **Portfolio Eingabe** | Manuelle Ticker‑Eingabe oder Laden von Standard‑ETFs | Ticker hinzufügen, entfernen |
| **Portfolio Profile** | Auswahl des Risikoprofils und Asset‑Allocation | Presets laden, Werte anpassen |
| **Analyse Panel** | Bewertet TER, Konzentration, Stress‑Szenario | Kennzahlen prüfen, TER normalisieren |
| **ETF Auswahl & Explainable Scoring** | Bewertet ETF‑Kandidaten nach Kriterien | Gewichte anpassen, Index wechseln |

## 3. Wichtige Kennzahlen
- **TER (Total Expense Ratio)** – jährliche Kostenquote des ETFs  
- **Herfindahl‑Index** – misst Konzentration im Portfolio  
- **Stress‑Szenario** – simuliert Markt‑Schocks  

## 4. Manuelle Eingriffe
1. Ticker im Sidebar hinzufügen (z. B. AAPL, VWRL).  
2. Im Scoring‑Tab Gewichte anpassen (TER, AUM, Tracking …).  
3. Backtest starten, um Performance zu prüfen.  

## 5. Tipps
- Balanced = 45 % Equity / 45 % Bonds / 10 % Cash  
- Aggressive = mehr Aktien, höhere Rendite, höheres Risiko  
- Conservative = mehr Anleihen, geringere Schwankung  

---

### 💡 Ergebnis
Nach dieser Änderung:
- Der Tab heißt **„Dashboard‑Beschreibung und Gebrauchsanweisung“**.  
- Nutzer können dort alles nachlesen, ohne Code öffnen zu müssen.  
- Du kannst die Datei jederzeit erweitern (z. B. Screenshots, Tabellen, Beispiel‑Workflows).

---

Wenn du möchtest, kann ich dir jetzt **den vollständigen Patch‑Block** liefern, der:
1. den Expander in `profiles_ui.py` automatisch ersetzt,  
2. die neue Datei `docs/dashboard_guide.md` erstellt,  
3. und ein Backup anlegt.  

Möchtest du, dass ich diesen Patch‑Block vorbereite?