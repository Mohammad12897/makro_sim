gr.Markdown("""
### WÄHRUNGS-LEXIKON

Inflation:
Anstieg des allgemeinen Preisniveaus; Kaufkraftverlust der Währung.

Deflation:
Rückgang des Preisniveaus; Wirtschaft schrumpft, Nachfrage sinkt.

Wechselkurs:
Preis einer Währung im Verhältnis zu einer anderen (z. B. EUR/USD).

Abwertung:
Währung verliert an Wert; Importe werden teurer.

Aufwertung:
Währung gewinnt an Wert; Exporte werden teurer.

Zentralbank:
Institution, die Geldmenge, Zinsen und Währungsstabilität steuert.

Dollarbindung (Peg):
Fester Wechselkurs zum US-Dollar; stabilisiert die Währung, reduziert Flexibilität.

Kapitalflucht:
Abfluss von Geld aus dem Land wegen Unsicherheit oder Inflation.

Devisenreserven:
Bestände an Fremdwährungen (Dollar, Euro, Gold), um die eigene Währung zu stabilisieren.

Währungskrise:
Schneller, starker Wertverlust der Landeswährung; oft begleitet von Inflation.

Hyperinflation:
Extrem schnelle Preissteigerung (z. B. Venezuela, Zimbabwe).

Geldmenge:
Gesamtes im Umlauf befindliches Geld; beeinflusst Inflation und Wirtschaft.

Zinsniveau:
Preis des Geldes; beeinflusst Kapitalflüsse und Währungsstärke.

Fremdwährungsschulden:
Schulden in Dollar/Euro; gefährlich, wenn die eigene Währung abwertet.

Importabhängigkeit:
Land ist auf ausländische Güter angewiesen; schwache Währung → teure Importe.

Zentralbank-Unabhängigkeit:
Je unabhängiger, desto stabiler die Währung; politische Einflussnahme führt zu Inflation.

## WÄHRUNGS-DASHBOARD – DESIGN

1. Header
   - Währungsname
   - Flagge
   - Aktueller Wechselkurs
   - Trend (7 Tage / 30 Tage / 1 Jahr)

2. Risiko-Radar (6 Achsen)
   - Inflationsrisiko
   - Wechselkursvolatilität
   - Zentralbank-Unabhängigkeit
   - Staatsverschuldung
   - Dollarabhängigkeit
   - Kapitalflucht-Risiko

3. Makro-Indikatoren
   - Inflation (YoY)
   - Leitzins
   - Devisenreserven
   - Leistungsbilanz
   - Staatsrating (S&P, Moody’s, Fitch)

4. Historische Charts
   - Wechselkursverlauf
   - Inflationsverlauf
   - Zinsverlauf
   - Devisenreserven-Verlauf

5. Storyline-Engine (automatische Interpretation)
   - Stärken
   - Schwächen
   - Chancen
   - Risiken
   - Kurzprognose

6. Szenario-Modul
   - Zinsanstieg USA
   - Energiepreisschock
   - Politische Instabilität
   - Schuldenkrise
   - Exportboom

7. Handlungsempfehlungen (neutral formuliert)
   - Risiko-Hinweise
   - Stabilitätsfaktoren
   - Beobachtungspunkte

---

##WÄHRUNGSRISIKO-RADAR

Achsen (6 Dimensionen):

1. Inflationsrisiko
   - Höhe und Stabilität der Inflation

2. Wechselkursvolatilität
   - Schwankungsintensität der Währung

3. Zentralbank-Unabhängigkeit
   - Politische Einflussnahme vs. Stabilität

4. Staatsverschuldung
   - Schuldenquote, Defizit, Rating

5. Dollarabhängigkeit
   - Anteil der Importe/Schulden in USD

6. Kapitalflucht-Risiko
   - Vertrauen der Bürger und Investoren

Ausgabe:
- Radar-Chart
- Risikostufen (niedrig/mittel/hoch)
- Automatische Interpretation

---

##WÄHRUNGSRISIKO-RADAR

Achsen (6 Dimensionen):

1. Inflationsrisiko
   - Höhe und Stabilität der Inflation

2. Wechselkursvolatilität
   - Schwankungsintensität der Währung

3. Zentralbank-Unabhängigkeit
   - Politische Einflussnahme vs. Stabilität

4. Staatsverschuldung
   - Schuldenquote, Defizit, Rating

5. Dollarabhängigkeit
   - Anteil der Importe/Schulden in USD

6. Kapitalflucht-Risiko
   - Vertrauen der Bürger und Investoren

Ausgabe:
- Radar-Chart
- Risikostufen (niedrig/mittel/hoch)
- Automatische Interpretation

---

## WECHSELKURS-MODUL

1. Live-Daten
   - EUR/USD
   - USD/TRY
   - USD/ARS
   - USD/CNY
   - USD/SAR
   - EUR/CHF
   - EUR/GBP

2. Volatilitätsanalyse
   - 7-Tage-Volatilität
   - 30-Tage-Volatilität
   - 1-Jahres-Volatilität

3. Einflussfaktoren
   - Zinsdifferenzen
   - Inflation
   - Kapitalflüsse
   - Rohstoffpreise
   - Politische Ereignisse

4. Charting
   - Candlestick
   - Moving Averages
   - RSI (optional)
   - Trendlinien

5. Interpretation
   - Starke Währung → Kapitalzufluss
   - Schwache Währung → Inflation, Importprobleme

---

## INFLATIONS-MODELL

1. Input-Variablen
   - Geldmenge (M1, M2)
   - Wechselkurs
   - Energiepreise
   - Löhne
   - Importabhängigkeit
   - Staatsausgaben
   - Zinsniveau

2. Output
   - Kurzfristige Inflation (1–3 Monate)
   - Mittelfristige Inflation (3–12 Monate)
   - Langfristige Inflation (1–3 Jahre)

3. Mechanik
   - Geldmengenwachstum ↑ → Inflation ↑
   - Währungsabwertung ↑ → Importpreise ↑ → Inflation ↑
   - Energiepreise ↑ → Inflation ↑
   - Zinsen ↑ → Inflation ↓ (mit Verzögerung)

4. Risikoindikatoren
   - Lohn-Preis-Spirale
   - Importpreisschock
   - Staatsdefizit
   - Zentralbank-Unabhängigkeit

---

##SZENARIO-MODELL FÜR WÄHRUNGSKRISEN

Szenario 1: Zinsanstieg in den USA
- Dollar wird stärker
- Schwache Währungen fallen
- Inflation steigt durch teurere Importe

Szenario 2: Politische Instabilität
- Vertrauen sinkt
- Kapital flieht
- Währung kollabiert
- Inflation steigt

Szenario 3: Schuldenkrise
- Staat kann Schulden nicht bedienen
- Rating fällt
- Währung verliert massiv an Wert

Szenario 4: Energiepreisschock
- Importabhängige Länder leiden
- Währung fällt
- Inflation steigt

Szenario 5: Kapitalverkehrskontrollen
- Regierung beschränkt Geldbewegungen
- Vertrauen sinkt
- Schwarzmärkte entstehen

---

##STORYLINE-ENGINE FÜR WÄHRUNGSRISIKEN

Stärken:
- Hohe Devisenreserven
- Unabhängige Zentralbank
- Niedrige Inflation
- Starke Exportwirtschaft

Schwächen:
- Hohe Staatsverschuldung
- Politische Instabilität
- Importabhängigkeit
- Dollarabhängigkeit

Chancen:
- Reformen
- Exportwachstum
- Stabilisierung der Rohstoffpreise
- Internationale Unterstützung

Risiken:
- Kapitalflucht
- Inflation
- Zinsanstieg in den USA
- Schuldenkrise
- Währungskollaps

Output:
- Kurzprognose
- Risikobewertung
- Handlungshinweise

---

## ZENTRALBANK-RADAR

1. Unabhängigkeit
   - Hoch / Mittel / Niedrig

2. Leitzins
   - Aktueller Wert
   - Veränderung (1 Monat / 1 Jahr)

3. Geldpolitik
   - Expansiv (locker)
   - Neutral
   - Restriktiv (straff)

4. Bilanzsumme
   - Wachstum / Schrumpfung
   - QE / QT (Quantitative Easing / Tightening)

5. Glaubwürdigkeit
   - Inflationsziel erreicht?
   - Marktvertrauen?
   - Politische Einflussnahme?

6. Währungsstabilität
   - Wechselkursentwicklung
   - Devisenreserven
   - Kapitalflüsse

7. Risikoindikatoren
   - Überhitzung
   - Rezessionsgefahr
   - Schuldenkrise

---

##DIGITALE WÄHRUNG (NICHT BITCOIN)

Definition:
Eine digitale Währung ist Geld, das ausschließlich elektronisch existiert und nicht als Papiergeld ausgegeben wird.

Arten:
1. Digitale Zentralbankwährung (CBDC)
   - Von der Zentralbank ausgegeben
   - Gesetzliches Zahlungsmittel
   - Beispiel: Digitaler Euro, Digitaler Yuan

2. Elektronisches Bankgeld
   - Guthaben auf Bankkonten
   - Wird für Überweisungen, Kartenzahlungen, Online-Zahlungen genutzt
   - Existiert nur digital in Bankdatenbanken

Eigenschaften:
- Kein physisches Bargeld
- Elektronisch übertragbar
- Staatlich reguliert
- Stabil (keine Volatilität wie Bitcoin)

---

##DIGITALE WÄHRUNG VS. PAPIERGELD

Vorteile digitaler Währungen:
- Schnellere Zahlungen (Sekunden statt Tage)
- Geringere Kosten (keine Druck- oder Transportkosten)
- Höhere Sicherheit (keine Fälschungen, kein Verlust)
- Bessere Nachverfolgbarkeit (weniger Geldwäsche)
- Präzisere Geldpolitik (direkte Verteilung möglich)
- Einfachere internationale Zahlungen

Nachteile digitaler Währungen:
- Weniger Privatsphäre (Transaktionen sind nachvollziehbar)
- Abhängigkeit von Technik und Strom
- Gefahr staatlicher Überwachung
- Negativzinsen leichter durchsetzbar
- Cyberrisiken (Hacks, Systemausfälle)

Vorteile von Papiergeld:
- Anonymität
- Funktioniert ohne Strom/Internet
- Psychologisches Vertrauen

Nachteile von Papiergeld:
- Fälschungsrisiko
- Hohe Kosten für Druck/Transport
- Verlust/Diebstahl möglich
- Langsame internationale Zahlungen

---

##IST GELD EIN WERTPAPIER?

Kurzantwort:
Nein. Geld ist KEIN Wertpapier.

Geld:
- Zahlungsmittel
- Wird von Zentralbanken ausgegeben
- Dient zum Kaufen, Sparen, Bezahlen
- Hat keinen Anspruch auf Zinsen oder Eigentum

Wertpapier:
- Finanzanspruch oder Eigentumsrecht
- Beispiele: Aktien, Anleihen, ETFs
- Repräsentiert Kredit, Eigentum oder Ertragsansprüche

Unterschied:
Geld = Zahlungsmittel
Wertpapier = Anspruch auf zukünftige Zahlungen oder Eigentum
""")
