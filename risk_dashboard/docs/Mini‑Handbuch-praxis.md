# 📘 Mini‑Handbuch – Bedienung der Investment‑App

> Dieses Handbuch erklärt, wie du mit der App Aktien und ETFs analysierst, bewertest und verstehst – ganz ohne technische Vorkenntnisse.

---

## 🧭 1. Ausgangspunkt
Du hast im Internet oder in deiner Watchlist interessante Werte gefunden, z.B.:

| Name | Kürzel (Ticker) | Kurs | Veränderung |
|------|------------------|------|--------------|
| NVIDIA CORPORATION | NVDA | 225,16€ | −0,06% |
| iShares Core DAX ETF | EXS1.DE | 218,20€ | +0,11% |
| TECDAX | TDXP | 4092,20€ | −0,33% |

Diese Kürzel heißen **Ticker**.  
Ein **Ticker** ist der eindeutige Code, unter dem eine Aktie oder ein ETF an der Börse gehandelt wird.  
Beispiele:
- **NVDA** → NVIDIA Corporation  
- **EXS1.DE** → iShares Core DAX ETF  
- **AAPL** → Apple Inc.  
- **VWRL.L** → Vanguard FTSE All‑World ETF  

---

## 🧩 2. Erste Schritte in der App

### Schritt 1: Ticker eingeben
Im linken Bereich der App steht:
- **Ticker hinzufügen: z.B. AAPL oder CSPX.L**
- Gib hier den Ticker ein, den du analysieren willst.  
- Beispiel: `NVDA` oder `EXS1.DE`  
- Klicke auf **Analysieren**.

Die App lädt automatisch historische Kursdaten und zeigt Diagramme, Kennzahlen und Risiko‑Profile.

---

### Schritt 2: Portfolio zusammenstellen
Du kannst mehrere Ticker hinzufügen:
- Einzelaktien (z.B. NVDA, AAPL, MSFT)
- ETFs (z.B. EXS1.DE, VWRL.L)
- Cash oder Anleihen (z.B. AGGG.L)

Die App zeigt dein Portfolio als Tabelle:
| ticker | quantity | price | market_value |
|--------|-----------|-------|---------------|
| CSPX.L | 10 | 500 | 5000 |
| EQQQ.L | 5 | 300 | 1500 |
| AAPL | 20 | 150 | 3000 |
| MSFT | 10 | 350 | 3500 |
| VWRL.L | 5 | 80 | 400 |
| CASH | 1 | 100000 | 100000 |

---

### Schritt 3: Risiko‑Profil wählen
Im Abschnitt **Portfolio Profile** kannst du dein Risikoprofil festlegen:
- **Low Risk** → konservativ, wenig Schwankung  
- **Medium Risk** → ausgewogen  
- **High Risk** → wachstumsorientiert, höhere Schwankung  

Die App zeigt automatisch empfohlene ETFs für dein Profil:
- Low Risk: Anleihen, Staatsanleihen, Cash  
- Medium Risk: globale Aktien + Anleihen  
- High Risk: Technologie, Schwellenländer, Small Caps

---

### Schritt 4: Analyse starten
## Klicke auf **Berechnen**.  
## Die App zeigt Kennzahlen wie:
```json
{
  "sharpe": 0.85,
  "volatility": 0.12,
  "max_drawdown": 0.08
}
```
### Sharpe‑Ratio → Verhältnis von Rendite zu Risiko (je höher, desto besser).
### Volatilität → Schwankungsstärke des Portfolios.
### Max Drawdown → größter Verlust vom Höchststand.

## 📊 3. Ergebnisse verstehen
### Performance‑Panel
### Zeigt:

### Rendite über verschiedene Zeiträume
### Risiko‑Thermometer (Farben: grün = niedrig, orange = hoch)
### ETF vs Aktie – Absolute Gewichte (Live) → zeigt, wie stark ETFs und Aktien im Portfolio vertreten sind.

### Makro‑Daten (FRED)
### Unter Macro Data (FRED) kannst du Wirtschaftsdaten wie GDP, Inflation oder Arbeitslosenquote sehen.
### Diese Daten helfen, das Marktumfeld zu verstehen.

## 🧠 4. Fachbegriffe einfach erklärt
| Begriff | Bedeutung |
|--------|---------------|
| Ticker | Kürzel einer Aktie oder eines ETFs |
| ETF	| Fonds, der viele Aktien bündelt |
| Index	| Gruppe von Aktien (z.B. DAX, NASDAQ100) |
| Volatilität	| Schwankungsstärke eines Kurses |
| Drawdown	| Größter Verlust vom Höchststand |
| Rendite	| Gewinn über einen Zeitraum |
| Sharpe‑Ratio | Verhältnis von Rendite zu Risiko |
| TER	| Kostenquote eines ETFs |
| Diversifikation	| Streuung über viele Werte |
| Backtest	| Simulation der Vergangenheit |
| Makro‑Daten	| Wirtschaftsdaten wie GDP, CPI, UNRATE |

## 🧮 5. Beispiel: ETF‑Bewertung mit der App
| Kennzahl | EXS1.DE | NVDA |
|--------|-----------|-------|
| 5‑Jahres‑Rendite	|	+45% | +180% |
| Volatilität	|	mittel | hoch |
| TER	 |	0,16% |	– |
| Diversifikation |	40DAX‑Unternehmen |	Einzelaktie |
| Fazit	|	Stabiler Deutschland‑ETF	|	Wachstumswert mit Risiko |

---
# Allgemein
## Was ist ein Ticker?  
### Kurz: „Kurzcode, unter dem eine Aktie oder ein ETF an der Börse gehandelt wird (z. B. NVDA, EXS1.DE).“

## Kurs  
### Kurz: „Aktueller Marktpreis des Werts.“

## Zeitraum  
### Kurz: „Wähle den Zeitraum, für den Kurs und Kennzahlen angezeigt werden (z. B. 1 Jahr).“

# Kennzahlen
## Rendite (1/3/5 Jahre)  
### Kurz: „Prozentuale Veränderung des Preises über den gewählten Zeitraum.“

## Volatilität  
### Kurz: „Wie stark der Kurs schwankt. Höhere Werte = größere Schwankungen.“

## Max Drawdown  
### Kurz: „Größter Rückgang vom Höchststand in der gewählten Periode.“

## Sharpe‑Ratio  
### Kurz: „Verhältnis von Rendite zu Risiko; höher ist besser für risikoadjustierte Rendite.“

## TER (Kostenquote)  
### Kurz: „Jährliche Kosten eines ETFs. Diese Gebühren mindern die Rendite.“

## Diversifikation  
### Kurz: „Wie breit ein ETF gestreut ist. Mehr Werte = weniger Einzelrisiko.“

## Benchmark  
### Kurz: „Vergleichsindex, an dem die Performance gemessen wird (z. B. DAX).“

# Portfolio & Backtest
## Portfolio‑Gewichte  
### Kurz: „Anteil eines Werts am Gesamtportfolio (in Prozent).“

## Rebalancing  
### Kurz: „Regelmäßiges Zurücksetzen der Gewichte, z. B. monatlich oder jährlich.“

## Backtest  
### Kurz: „Simulation, wie dein Portfolio in der Vergangenheit gelaufen wäre. Keine Garantie für die Zukunft.“

## Szenario‑Annahmen  
### Kurz: „Einfache Annahmen wie jährliche Sparrate oder Gebühren, die die Simulation beeinflussen.“

---


# App‑Hilfeseite – Interaktive Hilfe für deine Investment‑App

> Kurze, praktische Anleitung: Wie du die App bedienst, was ein Ticker ist, und wie du ETFs und Aktien analysierst. Ideal als Willkommens‑ oder Hilfeseite in der App.

---

## Schnellnavigation
- **Was ist ein Ticker?**  
- **Ticker eingeben** (einfacher Ablauf)  
- **Portfolio zusammenstellen**  
- **Analyse starten** (Charts, Kennzahlen, Backtest)  
- **Tooltip‑Texte** (kurze Erklärungen zu allen Kennzahlen)  
- **Beispiele** (ETF vs. Aktie)  
- **Troubleshooting & Tipps**

---

## Was ist ein Ticker?
Ein **Ticker** ist der kurze Code, unter dem eine Aktie oder ein ETF an der Börse gehandelt wird.  
Beispiele:
- `NVDA` → NVIDIA Corporation  
- `AAPL` → Apple Inc.  
- `EXS1.DE` → iShares Core DAX ETF (Deutschland, Börse: DE)  
- `VWRL.L` → Vanguard FTSE All‑World (Börse: L)

**Wie sieht ein Ticker aus?**
- Meist 3–6 Zeichen (z.B. `AAPL`, `MSFT`)  
- Bei ETFs oder ausländischen Börsen oft mit Ländercode: `EXS1.DE`, `VWRL.L`  
- Tipp: Wenn du unsicher bist, suche kurz den Namen + „Ticker“ im Internet und kopiere den Code.

---

## Schritt‑für‑Schritt: Ticker hinzufügen und analysieren

### 1) Ticker hinzufügen (einfach)
1. Öffne die App und gehe zum Feld **„Ticker hinzufügen“**.  
2. Tippe oder füge den Ticker ein (z.B. `NVDA` oder `EXS1.DE`).  
3. Drücke **Enter** oder klicke **Hinzufügen**.  
4. Wiederhole für weitere Werte.

**Was passiert danach?**  
Die App lädt automatisch historische Kursdaten für jeden hinzugefügten Ticker und zeigt eine Zeile in deiner Watchlist.

---

### 2) Portfolio zusammenstellen
- Du kannst mehrere Ticker in eine Liste packen.  
- Optional: Trage für jeden Ticker eine Menge/Anzahl ein (z.B. 10 Aktien) oder ein Gewicht (z.B. 20% des Portfolios).  
- Die App zeigt die aktuelle Marktbewertung (Anzahl × Kurs) und die Gesamtaufstellung.

---

### 3) Analyse starten (ein Klick)
Klicke **Analysieren** oder **Berechnen**. Die App führt automatisch aus:
- Datenvalidierung (prüft, ob Kurse vorhanden sind)  
- Diagramme (Kursverlauf, Performance)  
- Kennzahlen (Rendite, Volatilität, Drawdown, Sharpe)  
- ETF‑Infos (TER, Anzahl enthaltene Werte, Region)  
- Optional: Backtest (Simulation historischer Performance)

---

### 4) Ergebnisse lesen (was du siehst)
- **Chart**: Kursverlauf über die gewählte Zeitspanne.  
- **Performance‑Panel**: Renditen für 1/3/5 Jahre.  
- **Risiko‑Panel**: Volatilität, Max Drawdown.  
- **Portfolio‑Aufteilung**: Gewichtung nach ETF/Aktie/Branche/Region.  
- **Backtest‑Ergebnis**: Simulierte Portfolio‑Entwicklung, jährliche Rendite, maximale Verluste.

---

## Interaktive Elemente & Bedienungshinweise
- **Datumsauswahl**: Wähle Start‑ und Enddatum, um Zeiträume zu vergleichen.  
- **Zeitraum‑Buttons**: 1M / 3M / 1Y / 3Y / 5Y / All — schnelle Ansicht wechseln.  
- **Tooltip‑Icons**: Über jedem Kennzahlen‑Label findest du ein kleines „i“ – klicke oder fahre mit der Maus darüber, um die Kurzdefinition zu sehen.  
- **Filter**: Nach Region, Branche oder ETF‑Typ filtern.  
- **Szenarien**: Lege einfache Annahmen fest (z.B. jährliche Sparrate, Rebalancing‑Intervall) und starte eine Simulation.

---

## Tooltip‑Texte (kurze Erklärungen, direkt neben den Zahlen)

- **Ticker**: Kürzel, unter dem der Wert gehandelt wird.  
- **Kurs**: Aktueller Marktpreis.  
- **Rendite (1/3/5 Jahre)**: Prozentuale Veränderung des Preises über den Zeitraum.  
- **Volatilität**: Wie stark der Kurs schwankt; höhere Werte = größere Schwankungen.  
- **Max Drawdown**: Größter Rückgang vom Höchststand in der betrachteten Periode.  
- **Sharpe‑Ratio**: Verhältnis von Rendite zu Risiko; höher ist besser.  
- **TER**: Jahreskosten eines ETFs; mindert die Rendite.  
- **Diversifikation**: Anzahl und Streuung der enthaltenen Werte; mehr = weniger Einzelrisiko.  
- **Backtest**: Simulation, wie das Portfolio historisch gelaufen wäre (keine Garantie für die Zukunft).  
- **Benchmark**: Vergleichsindex (z.B. DAX), an dem die Performance gemessen wird.

---

## Beispiele: Was du konkret tust

### Beispiel A – Einzelaktie prüfen
1. Ticker `NVDA` eingeben.  
2. Auf **Analysieren** klicken.  
3. Chart ansehen: Steigt der Kurs langfristig?  
4. Tooltip bei Volatilität lesen: Ist die Schwankung für dich akzeptabel?  
5. Wenn ja: Menge eingeben und Marktwert prüfen.

### Beispiel B – ETF vergleichen
1. Ticker `EXS1.DE` und `VWRL.L` hinzufügen.  
2. Beide analysieren lassen.  
3. Vergleiche TER, Diversifikation und 5‑Jahres‑Rendite.  
4. Entscheide: ETF A als Kern, ETF B als Ergänzung.

---

## Backtest: So nutzt du ihn sinnvoll
- Wähle Portfolio (Ticker + Gewichte).  
- Wähle Zeitraum (z.B. 2015–2025).  
- Wähle Rebalancing‑Intervall (monatlich, jährlich).  
- Starte Backtest.  
- Lies: kumulative Rendite, jährliche Durchschnittsrendite, Max Drawdown.  
- Nutze das Ergebnis als Orientierung, nicht als Vorhersage.

---

## Häufige Fragen (FAQ)
**Q: Was, wenn ein Ticker nicht gefunden wird?**  
A: Prüfe Schreibweise und Börsen‑Suffix (z.B. `.DE`, `.L`). Wenn weiterhin nicht gefunden, suche den Ticker kurz im Internet und füge ihn erneut ein.

**Q: Woher kommen die Daten?**  
A: Die App lädt historische Kurse und Kennzahlen automatisch aus verlässlichen Datenquellen. Du musst nichts manuell importieren.

**Q: Kann die App mir sagen, was ich kaufen soll?**  
A: Die App liefert Informationen und Simulationen. Sie trifft keine Anlageentscheidungen für dich. Für persönliche Empfehlungen wende dich an einen Finanzberater.

**Q: Was bedeutet „TER“?**  
A: TER ist die jährliche Kostenquote eines ETFs. Sie reduziert die Rendite und sollte bei Vergleichen berücksichtigt werden.

---

## Troubleshooting & Tipps
- **Langsame Datenladung**: Prüfe Internetverbindung; bei vielen Tickers dauert das Laden länger.  
- **Fehlende historische Daten**: Manche Werte haben nur kurze Historie; wähle kürzeren Zeitraum.  
- **Unklare Spalten/Labels**: Fahre mit der Maus über das Label – der Tooltip erklärt es.  
- **App zeigt Fehler**: Notiere die Fehlermeldung und starte die App neu; wenn das Problem bleibt, kontaktiere Support mit der Fehlermeldung.

---

## Kurze Checkliste vor jeder Analyse
- [ ] Ticker korrekt eingegeben (inkl. Börsen‑Suffix falls nötig)  
- [ ] Gewichte/Mengen eingetragen (falls Portfolio‑Analyse)  
- [ ] Zeitraum gewählt (z.B. 3 Jahre)  
- [ ] Rebalancing‑Intervall festgelegt (falls Backtest)  
- [ ] Ergebnis‑Tooltips gelesen und verstanden

---

## Abschluss
Diese Seite ist deine **interaktive Hilfe**:  
- Nutze die Tooltips für schnelle Erklärungen.  
- Folge dem Schritt‑für‑Schritt‑Ablauf für saubere Analysen.  
- Verwende Backtests als Orientierung, nicht als Garantie.