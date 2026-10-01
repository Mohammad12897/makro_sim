# Portfolio Benutzerhandbuch

Dieses Handbuch erklärt in klarer, nutzerorientierter Sprache, wie du das Dashboard bedienst, um ein Portfolio aus Tickers zu verwalten, neue Positionen hinzuzufügen und die **Holdings‑Tabelle** sicher zu nutzen. Es enthält nur Bedienhinweise, Beispiele und Empfehlungen — keine technischen Details.

---

## Übersicht: Wo finde ich was?

- **Sidebar**  
  Die **Sidebar** ist die linke Seitenleiste des Dashboards. Sie bleibt sichtbar, während du durch das Dashboard navigierst. Dort befinden sich alle Eingabefelder für neue Positionen, die Menge, Buttons und Upload‑Optionen.

- **Ticker hinzufügen (Textbox)**  
  Direkt in der Sidebar findest du das Feld **„Ticker hinzufügen“**. Dort gibst du ein einzelnes Kürzel ein, z. B. `NVDA` oder `VWRL.L`.

- **Menge (Number Input)**  
  Direkt unter (oder neben) dem Ticker‑Feld in der Sidebar ist das Feld **„Menge“** (Number Input).  
  - **Standardwert:** 1  
  - **Eingabe:** ganze Zahl ≥ 0  
  - **Verwendung:** Wird beim Klick auf **Hinzufügen** für die neue Position übernommen, sofern nicht per CSV eine Menge vorgegeben wurde.

- **Hinzufügen (Button)**  
  Der Button **„Hinzufügen“** in der Sidebar bestätigt die Eingaben (Ticker + Menge) und legt die Position im Portfolio an. Nach dem Hinzufügen wechselt das Dashboard automatisch zur **Holdings Analyse**, damit du die neue Position prüfen kannst.

- **Upload‑Tab (Bulk‑Import)**  
  Im Tab **Upload** kannst du eine CSV hochladen, um viele Positionen auf einmal anzulegen. Die CSV‑Variante hat Vorrang vor der Sidebar‑Menge (siehe Abschnitt „Woher stammen die quantity‑Werte“).

---

## Eingabeformate: Wie gebe ich Ticker und Mengen ein?

### 1) Einzelne Position (empfohlen für 1–3 Ticker)
- **Schritt 1:** In Sidebar **Ticker hinzufügen** das Kürzel eingeben (z. B. `BTC`).  
- **Schritt 2:** Im Feld **Menge** die Anzahl eintragen (z. B. `2`).  
- **Schritt 3:** **Hinzufügen** klicken.  
- **Ergebnis:** Zeile `BTC | 2 | price | market_value` erscheint in der Holdings‑Tabelle.

### 2) Mehrere Ticker in einem Schritt (Textbox, mehrere Formate möglich)
- **Komma‑ oder Zeilengetrennt, nur Ticker (Menge = Sidebar‑Default)**  
  - Beispiel: `DAX, BTC, NVDA` → jede Position erhält die Sidebar‑Menge (z. B. 1).
- **Ticker mit Menge (einfaches Format)**  
  - Format A: `DAX:1, BTC:2, NVDA:5`  
  - Format B (Zeilen):  
    ```
    DAX 1
    BTC 2
    NVDA 5
    ```
  - **Beispiel:** `DAX:1, BTC:2` → legt DAX mit Menge 1 und BTC mit Menge 2 an.

> **Tipp:** Für viele Positionen ist der CSV‑Upload robuster und empfehlenswerter.

### 3) CSV‑Upload (empfohlen für Bulk‑Import)
- **Ort:** Tab **Upload**  
- **Erwartete Spalten:**  
  - `ticker` (erforderlich)  
  - `quantity` (optional)  
  - `market_value` (optional)  
- **Beispiel CSV:**
**ticker,quantity**
**DAX   ,1**
**BTC   ,2**
**NVDA  ,5**
- **Verhalten:** CSV‑`quantity` hat Vorrang vor Sidebar‑Menge. Wenn `market_value` angegeben ist, wird dieser Wert übernommen; fehlende Preise werden, wenn möglich, ergänzt.

---

## Woher stammen die `quantity`‑Werte in der Tabelle?

Priorität der Quellen:
1. **CSV** (falls importiert und `quantity` angegeben)  
2. **Sidebar‑Eingabe** (Number Input `Menge`) beim Einzel‑Hinzufügen  
3. **Default** (z. B. 1), wenn weder CSV noch Sidebar‑Eingabe vorhanden sind

Du kannst die Menge jederzeit in der Holdings‑Tabelle nachträglich bearbeiten; danach werden Marktwert und Gewicht automatisch neu berechnet.

---

## Beispiel: So entsteht eine Tabellenzeile

Wenn du `CSPX.L` mit Menge `10` hinzufügst und der letzte Preis `500,00` ist:

- **ticker:** `CSPX.L`  
- **quantity:** `10`  
- **price:** `500,00`  
- **market_value:** `10 × 500,00 = 5.000,00`  
- **weight:** automatisch berechnet (Anteil am Gesamtportfolio)

---

## Die Holdings‑Tabelle (Übersicht)

| **ticker** | **quantity** | **price** | **market_value** | **weight** |
|---|---:|---:|---:|---:|
| CSPX.L | 10 | 500,00 | 5.000,00 | 4,37 % |
| EQQQ.L | 5 | 300,00 | 1.500,00 | 1,31 % |
| AAPL | 20 | 150,00 | 3.000,00 | 2,62 % |
| MSFT | 10 | 350,00 | 3.500,00 | 3,06 % |
| VWRL.L | 5 | 80,00 | 400,00 | 0,35 % |
| VOO | 2 | 420,00 | 840,00 | 0,73 % |
| CASH | 1 | 100.000,00 | 100.000,00 | 87,47 % |
| DAX | 1 | — | 44.608,00 | 0,04 % |
| BTC | 1 | — | 36,97 | 0,03 % |

**Hinweise zur Tabelle**
- **Fehlender Preis:** `—` oder leeres Feld bedeutet: kein Preis gefunden. Marktwert bleibt 0 oder wird aus CSV übernommen.  
- **Menge = 0:** Position ist angelegt, hat aber keinen wirtschaftlichen Wert.  
- **Bearbeiten:** Menge (und ggf. Marktwert) kann direkt in der Tabelle geändert werden; Gewichte werden neu berechnet.  
- **Sortieren / Filtern:** Nutze Spaltenüberschriften und Filter, um z. B. nur Positionen ohne Preis anzuzeigen.  
- **Cash‑Position:** Beeinflusst die Gewichtsverteilung stark; prüfe Cash‑Einträge bei unerwarteten Gewichten.

---

## Visualisierungen in der Holdings Analyse

- **Gewichtsdiagramm**  
Balkendiagramm mit prozentualen Anteilen jeder Position — ideal, um Konzentrationen zu erkennen.

- **Performance Chart (historisch)**  
Zeigt die tatsächliche, historische Entwicklung des Portfoliowerts (kumuliert), sofern historische Preisdaten vorhanden sind. Interaktive Tooltips zeigen Datum und Wert.

- **Szenario‑/Prognose‑Ansicht (modelliert)**  
- Monte‑Carlo‑Simulationen, Median‑Pfad und Konfidenzbänder (z. B. 5–95 %) visualisieren mögliche Zukunftspfade.  
- **Wichtig:** Diese Darstellungen sind Projektionen, keine Vorhersagen. Zeige stets die zugrunde liegenden Annahmen (Zeithorizont, Anzahl Simulationen, Volatilitätsannahme, Rebalancing).

- **Top Holdings**  
Liste der größten Positionen nach Gewicht.

- **Kennzahlen**  
Total Return, CAGR, Volatilität, Sharpe Ratio, Max Drawdown — werden angezeigt, wenn ausreichend Daten vorliegen.

---

## KI‑Funktionen: Was sie leisten und wie du sie nutzen solltest

- **Was KI kann (nützlich)**  
- Portfolio‑Checks (Diversifikation, Konzentration)  
- Mehrere Optimierungs‑Vorschläge anzeigen (z. B. Risiko‑Parität, Minimum‑Varianz, HRP)  
- Backtests historischer Performance für Vorschläge  
- Szenario‑Analysen und Monte‑Carlo‑Simulationen zur Abschätzung möglicher Zukunftspfade

- **Was KI nicht kann**  
- Keine Garantie für „beste Rendite“  
- Keine persönliche Anlageberatung — für verbindliche Entscheidungen kontaktiere einen Finanzberater

- **Nutzerkommunikation (unbedingt sichtbar)**  
- **Disclaimer** unter jedem KI‑Ergebnis:  
  > *Hinweis: Analysen und Simulationen dienen nur Informationszwecken und stellen keine Anlageberatung dar. Historische Ergebnisse sind kein verlässlicher Indikator für zukünftige Entwicklungen.*  
- Zeige die **Annahmen** offen an (Zeithorizont, Simulationen, Rebalancing).

---

## Umsetzungsschritte (Priorisierte To‑Do‑Liste)

1. **Accidental paste entfernen**  
 - Suche projektweit nach Debug/Browser‑Dump‑Blöcken (z. B. `edge_all_open_tabs`) und entferne sie vollständig.  
 - Committe die Änderung und starte das Dashboard neu.

2. **UI: Menge‑Feld sichtbar platzieren**  
 - Platziere das Number‑Input **Menge** direkt unter dem Ticker‑Feld in der Sidebar mit Label: *Menge (Anteile)*.  
 - Setze Default = 1.

3. **Analyse‑Modal implementieren**  
 - Dropdown **Optimierungsverfahren** (HRP, Minimum‑Varianz, Risiko‑Parität)  
 - Checkbox **Szenarien anzeigen** (Monte‑Carlo)  
 - Eingabefelder: **Zeithorizont**, **Anzahl Simulationen**, **Rebalancing‑Intervall**  
 - Button **Run Analysis** mit Ladeindikator

4. **Ergebnisdarstellung**  
 - **Tabelle mit Vorschlägen** (Gewichte, erwartete Kennzahlen)  
 - **Chart**: historische Portfoliokurve + Szenario‑Bänder (Median + Konfidenz)  
 - **Erläuterungstexte & Disclaimer** sichtbar neben/unter den Ergebnissen

5. **Test**  
 - Füge mehrere Ticker hinzu (Einzel/CSV), führe Analysen aus, vergleiche Vorschläge und Backtests.

6. **UX‑Feinschliff**  
 - Ladeindikatoren bei langen Berechnungen  
 - Verständliche Fehlermeldungen (z. B. „Für Ticker X kein Preis gefunden“)  
 - Eindeutige Button‑Keys und keine doppelten UI‑IDs

---

## Fehlerfälle und was zu tun ist

- **Kein Preis gefunden**  
- Prüfe Schreibweise; ergänze ggf. Börsen‑Suffix (z. B. `.L`, `.DE`).  
- Alternativ: trage `market_value` in der CSV ein oder ergänze Preis/Menge manuell.

- **Menge = 0**  
- Position ist angelegt, hat aber keinen Marktwert. Trage die korrekte Menge nach.

- **Doppelte Positionen**  
- Entferne Duplikate in der Sidebar oder bearbeite die Position in der Tabelle.

---

## FAQ (Kurz)

**Kann ich mehrere Ticker gleichzeitig hinzufügen?**  
Ja — per CSV oder durch Eingabe mehrerer Ticker im Textfeld (siehe Formate oben).

**Was passiert, wenn kein Preis gefunden wird?**  
Die Position wird angelegt; der Marktwert bleibt 0, bis ein Preis ergänzt wird.

**Wie aktuell sind die Preise?**  
Das Dashboard zeigt den zuletzt verfügbaren Schlusskurs an.

**Ist das eine Anlageberatung?**  
Nein. Diese Anleitung erklärt nur die Bedienung des Dashboards und stellt keine Anlageberatung dar.

---

## Support / Kontakt
- **Fehler melden:** Notiere Ticker, Zeitpunkt und Fehlermeldung und sende diese an den Support.  
- **Verbesserungswünsche:** Wünsche für zusätzliche Felder oder Visualisierungen bitte per E‑Mail oder Ticket einreichen.

