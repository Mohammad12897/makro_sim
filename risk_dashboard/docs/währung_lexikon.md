gr.Markdown("""
### WÃ„HRUNGS-LEXIKON

Inflation:
Anstieg des allgemeinen Preisniveaus; Kaufkraftverlust der WÃ¤hrung.

Deflation:
RÃ¼ckgang des Preisniveaus; Wirtschaft schrumpft, Nachfrage sinkt.

Wechselkurs:
Preis einer WÃ¤hrung im VerhÃ¤ltnis zu einer anderen (z. B. EUR/USD).

Abwertung:
WÃ¤hrung verliert an Wert; Importe werden teurer.

Aufwertung:
WÃ¤hrung gewinnt an Wert; Exporte werden teurer.

Zentralbank:
Institution, die Geldmenge, Zinsen und WÃ¤hrungsstabilitÃ¤t steuert.

Dollarbindung (Peg):
Fester Wechselkurs zum US-Dollar; stabilisiert die WÃ¤hrung, reduziert FlexibilitÃ¤t.

Kapitalflucht:
Abfluss von Geld aus dem Land wegen Unsicherheit oder Inflation.

Devisenreserven:
BestÃ¤nde an FremdwÃ¤hrungen (Dollar, Euro, Gold), um die eigene WÃ¤hrung zu stabilisieren.

WÃ¤hrungskrise:
Schneller, starker Wertverlust der LandeswÃ¤hrung; oft begleitet von Inflation.

Hyperinflation:
Extrem schnelle Preissteigerung (z. B. Venezuela, Zimbabwe).

Geldmenge:
Gesamtes im Umlauf befindliches Geld; beeinflusst Inflation und Wirtschaft.

Zinsniveau:
Preis des Geldes; beeinflusst KapitalflÃ¼sse und WÃ¤hrungsstÃ¤rke.

FremdwÃ¤hrungsschulden:
Schulden in Dollar/Euro; gefÃ¤hrlich, wenn die eigene WÃ¤hrung abwertet.

ImportabhÃ¤ngigkeit:
Land ist auf auslÃ¤ndische GÃ¼ter angewiesen; schwache WÃ¤hrung â†’ teure Importe.

Zentralbank-UnabhÃ¤ngigkeit:
Je unabhÃ¤ngiger, desto stabiler die WÃ¤hrung; politische Einflussnahme fÃ¼hrt zu Inflation.

## WÃ„HRUNGS-DASHBOARD â€“ DESIGN

1. Header
   - WÃ¤hrungsname
   - Flagge
   - Aktueller Wechselkurs
   - Trend (7 Tage / 30 Tage / 1 Jahr)

2. Risiko-Radar (6 Achsen)
   - Inflationsrisiko
   - WechselkursvolatilitÃ¤t
   - Zentralbank-UnabhÃ¤ngigkeit
   - Staatsverschuldung
   - DollarabhÃ¤ngigkeit
   - Kapitalflucht-Risiko

3. Makro-Indikatoren
   - Inflation (YoY)
   - Leitzins
   - Devisenreserven
   - Leistungsbilanz
   - Staatsrating (S&P, Moodyâ€™s, Fitch)

4. Historische Charts
   - Wechselkursverlauf
   - Inflationsverlauf
   - Zinsverlauf
   - Devisenreserven-Verlauf

5. Storyline-Engine (automatische Interpretation)
   - StÃ¤rken
   - SchwÃ¤chen
   - Chancen
   - Risiken
   - Kurzprognose

6. Szenario-Modul
   - Zinsanstieg USA
   - Energiepreisschock
   - Politische InstabilitÃ¤t
   - Schuldenkrise
   - Exportboom

7. Handlungsempfehlungen (neutral formuliert)
   - Risiko-Hinweise
   - StabilitÃ¤tsfaktoren
   - Beobachtungspunkte

---

##WÃ„HRUNGSRISIKO-RADAR

Achsen (6 Dimensionen):

1. Inflationsrisiko
   - HÃ¶he und StabilitÃ¤t der Inflation

2. WechselkursvolatilitÃ¤t
   - SchwankungsintensitÃ¤t der WÃ¤hrung

3. Zentralbank-UnabhÃ¤ngigkeit
   - Politische Einflussnahme vs. StabilitÃ¤t

4. Staatsverschuldung
   - Schuldenquote, Defizit, Rating

5. DollarabhÃ¤ngigkeit
   - Anteil der Importe/Schulden in USD

6. Kapitalflucht-Risiko
   - Vertrauen der BÃ¼rger und Investoren

Ausgabe:
- Radar-Chart
- Risikostufen (niedrig/mittel/hoch)
- Automatische Interpretation

---

##WÃ„HRUNGSRISIKO-RADAR

Achsen (6 Dimensionen):

1. Inflationsrisiko
   - HÃ¶he und StabilitÃ¤t der Inflation

2. WechselkursvolatilitÃ¤t
   - SchwankungsintensitÃ¤t der WÃ¤hrung

3. Zentralbank-UnabhÃ¤ngigkeit
   - Politische Einflussnahme vs. StabilitÃ¤t

4. Staatsverschuldung
   - Schuldenquote, Defizit, Rating

5. DollarabhÃ¤ngigkeit
   - Anteil der Importe/Schulden in USD

6. Kapitalflucht-Risiko
   - Vertrauen der BÃ¼rger und Investoren

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

2. VolatilitÃ¤tsanalyse
   - 7-Tage-VolatilitÃ¤t
   - 30-Tage-VolatilitÃ¤t
   - 1-Jahres-VolatilitÃ¤t

3. Einflussfaktoren
   - Zinsdifferenzen
   - Inflation
   - KapitalflÃ¼sse
   - Rohstoffpreise
   - Politische Ereignisse

4. Charting
   - Candlestick
   - Moving Averages
   - RSI (optional)
   - Trendlinien

5. Interpretation
   - Starke WÃ¤hrung â†’ Kapitalzufluss
   - Schwache WÃ¤hrung â†’ Inflation, Importprobleme

---

## INFLATIONS-MODELL

1. Input-Variablen
   - Geldmenge (M1, M2)
   - Wechselkurs
   - Energiepreise
   - LÃ¶hne
   - ImportabhÃ¤ngigkeit
   - Staatsausgaben
   - Zinsniveau

2. Output
   - Kurzfristige Inflation (1â€“3 Monate)
   - Mittelfristige Inflation (3â€“12 Monate)
   - Langfristige Inflation (1â€“3 Jahre)

3. Mechanik
   - Geldmengenwachstum â†‘ â†’ Inflation â†‘
   - WÃ¤hrungsabwertung â†‘ â†’ Importpreise â†‘ â†’ Inflation â†‘
   - Energiepreise â†‘ â†’ Inflation â†‘
   - Zinsen â†‘ â†’ Inflation â†“ (mit VerzÃ¶gerung)

4. Risikoindikatoren
   - Lohn-Preis-Spirale
   - Importpreisschock
   - Staatsdefizit
   - Zentralbank-UnabhÃ¤ngigkeit

---

##SZENARIO-MODELL FÃœR WÃ„HRUNGSKRISEN

Szenario 1: Zinsanstieg in den USA
- Dollar wird stÃ¤rker
- Schwache WÃ¤hrungen fallen
- Inflation steigt durch teurere Importe

Szenario 2: Politische InstabilitÃ¤t
- Vertrauen sinkt
- Kapital flieht
- WÃ¤hrung kollabiert
- Inflation steigt

Szenario 3: Schuldenkrise
- Staat kann Schulden nicht bedienen
- Rating fÃ¤llt
- WÃ¤hrung verliert massiv an Wert

Szenario 4: Energiepreisschock
- ImportabhÃ¤ngige LÃ¤nder leiden
- WÃ¤hrung fÃ¤llt
- Inflation steigt

Szenario 5: Kapitalverkehrskontrollen
- Regierung beschrÃ¤nkt Geldbewegungen
- Vertrauen sinkt
- SchwarzmÃ¤rkte entstehen

---

##STORYLINE-ENGINE FÃœR WÃ„HRUNGSRISIKEN

StÃ¤rken:
- Hohe Devisenreserven
- UnabhÃ¤ngige Zentralbank
- Niedrige Inflation
- Starke Exportwirtschaft

SchwÃ¤chen:
- Hohe Staatsverschuldung
- Politische InstabilitÃ¤t
- ImportabhÃ¤ngigkeit
- DollarabhÃ¤ngigkeit

Chancen:
- Reformen
- Exportwachstum
- Stabilisierung der Rohstoffpreise
- Internationale UnterstÃ¼tzung

Risiken:
- Kapitalflucht
- Inflation
- Zinsanstieg in den USA
- Schuldenkrise
- WÃ¤hrungskollaps

Output:
- Kurzprognose
- Risikobewertung
- Handlungshinweise

---

## ZENTRALBANK-RADAR

1. UnabhÃ¤ngigkeit
   - Hoch / Mittel / Niedrig

2. Leitzins
   - Aktueller Wert
   - VerÃ¤nderung (1 Monat / 1 Jahr)

3. Geldpolitik
   - Expansiv (locker)
   - Neutral
   - Restriktiv (straff)

4. Bilanzsumme
   - Wachstum / Schrumpfung
   - QE / QT (Quantitative Easing / Tightening)

5. GlaubwÃ¼rdigkeit
   - Inflationsziel erreicht?
   - Marktvertrauen?
   - Politische Einflussnahme?

6. WÃ¤hrungsstabilitÃ¤t
   - Wechselkursentwicklung
   - Devisenreserven
   - KapitalflÃ¼sse

7. Risikoindikatoren
   - Ãœberhitzung
   - Rezessionsgefahr
   - Schuldenkrise

---

##DIGITALE WÃ„HRUNG (NICHT BITCOIN)

Definition:
Eine digitale WÃ¤hrung ist Geld, das ausschlieÃŸlich elektronisch existiert und nicht als Papiergeld ausgegeben wird.

Arten:
1. Digitale ZentralbankwÃ¤hrung (CBDC)
   - Von der Zentralbank ausgegeben
   - Gesetzliches Zahlungsmittel
   - Beispiel: Digitaler Euro, Digitaler Yuan

2. Elektronisches Bankgeld
   - Guthaben auf Bankkonten
   - Wird fÃ¼r Ãœberweisungen, Kartenzahlungen, Online-Zahlungen genutzt
   - Existiert nur digital in Bankdatenbanken

Eigenschaften:
- Kein physisches Bargeld
- Elektronisch Ã¼bertragbar
- Staatlich reguliert
- Stabil (keine VolatilitÃ¤t wie Bitcoin)

---

##DIGITALE WÃ„HRUNG VS. PAPIERGELD

Vorteile digitaler WÃ¤hrungen:
- Schnellere Zahlungen (Sekunden statt Tage)
- Geringere Kosten (keine Druck- oder Transportkosten)
- HÃ¶here Sicherheit (keine FÃ¤lschungen, kein Verlust)
- Bessere Nachverfolgbarkeit (weniger GeldwÃ¤sche)
- PrÃ¤zisere Geldpolitik (direkte Verteilung mÃ¶glich)
- Einfachere internationale Zahlungen

Nachteile digitaler WÃ¤hrungen:
- Weniger PrivatsphÃ¤re (Transaktionen sind nachvollziehbar)
- AbhÃ¤ngigkeit von Technik und Strom
- Gefahr staatlicher Ãœberwachung
- Negativzinsen leichter durchsetzbar
- Cyberrisiken (Hacks, SystemausfÃ¤lle)

Vorteile von Papiergeld:
- AnonymitÃ¤t
- Funktioniert ohne Strom/Internet
- Psychologisches Vertrauen

Nachteile von Papiergeld:
- FÃ¤lschungsrisiko
- Hohe Kosten fÃ¼r Druck/Transport
- Verlust/Diebstahl mÃ¶glich
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
- ReprÃ¤sentiert Kredit, Eigentum oder ErtragsansprÃ¼che

Unterschied:
Geld = Zahlungsmittel
Wertpapier = Anspruch auf zukÃ¼nftige Zahlungen oder Eigentum
""")

