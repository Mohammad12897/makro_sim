# Lexikon

## Equity weight
**Definition:** Anteil des Portfolios, der in Aktien investiert ist.  
**Warum wichtig:** Aktien bieten langfristig hÃ¶here Renditen, erhÃ¶hen aber VolatilitÃ¤t und Drawdownâ€‘Risiko.

## Bond weight
**Definition:** Anteil des Portfolios in Anleihen (Staatsanleihen, Unternehmensanleihen).  
**Warum wichtig:** DÃ¤mpft Schwankungen und reduziert erwarteten Drawdown.

## Cash
**Definition:** LiquiditÃ¤tsreserve in Form von Bargeld oder kurzfristigen Geldmarktinstrumenten.  
**Warum wichtig:** Dient als Puffer fÃ¼r kurzfristige Ausgaben und Rebalancing.

## Target annual return
**Definition:** Erwartete durchschnittliche Jahresrendite (SchÃ¤tzwert).  
**Warum wichtig:** Dient zur Simulation und Zielsetzung; keine Garantie.

## Max drawdown tolerance
**Definition:** Maximal tolerierter RÃ¼ckgang vom HÃ¶chststand in Prozent.  
**Warum wichtig:** Hilft bei Risikosteuerung, Stopâ€‘Lossâ€‘Regeln und psychologischer Planung.

## Rebalance frequency
**Definition:** Wie oft das Portfolio automatisch wieder auf Zielgewichte gebracht wird (z. B. monthly, quarterly).  
**Warum wichtig:** HÃ¤ufigeres Rebalancing reduziert Drift, kann aber Transaktionskosten erhÃ¶hen.

## Allowed instruments
**Definition:** Liste erlaubter Assetâ€‘Klassen oder ETFs (z. B. global_equity_etf).  
**Warum wichtig:** BeschrÃ¤nkt die Auswahl bei automatischen Strategien und Screening.

## Drawdown
**Definition:** Prozentualer RÃ¼ckgang vom letzten HÃ¶chststand eines Portfolios.  
**Warum wichtig:** Misst das Risiko eines Portfolios in Stressphasen.

## VolatilitÃ¤t
**Definition:** Statistische Schwankungsbreite der Renditen (Standardabweichung).  
**Warum wichtig:** HÃ¶here VolatilitÃ¤t bedeutet grÃ¶ÃŸere Schwankungen und potenziell grÃ¶ÃŸere Drawdowns.




# Lexikon â€” Risiko Dashboard

Dieses Lexikon erklÃ¤rt die wichtigsten Begriffe und UIâ€‘Felder im Risk Dashboard in einfacher Sprache.

## Profil / Profilname
**Was:** Ein gespeichertes Set von Einstellungen (Allocation, Ziele, erlaubte ETFs).  
**Warum:** ErmÃ¶glicht schnelles Wechseln zwischen Strategien (z. B. konservativ, ausgewogen, aggressiv).

## Risikokategorie
**Low / Medium / High** â€” Basisvorgaben fÃ¼r ein Profil.  
**Low:** Kapitalerhalt; niedrige VolatilitÃ¤t.  
**Medium:** Ausgewogenes Wachstum mit Schutz.  
**High:** Langfristiges Wachstum; hÃ¶here VolatilitÃ¤t.

## Equity weight (Aktienanteil)
**Was:** Prozentualer Anteil des Portfolios in Aktien.  
**Hinweis:** HÃ¶herer Aktienanteil â†’ hÃ¶here Renditeerwartung, aber auch hÃ¶here Schwankungen.

## Bond weight (Anleihenanteil)
**Was:** Prozentualer Anteil in Anleihen.  
**Hinweis:** DÃ¤mpft Schwankungen und reduziert Drawdown.

## Cash
**Was:** LiquiditÃ¤tsreserve in Prozent.  
**Warum:** Puffer fÃ¼r kurzfristige Ausgaben oder Rebalancing.

## Target annual return (Ziel Jahresrendite)
**Was:** Erwartete durchschnittliche Jahresrendite (SchÃ¤tzwert).  
**Hinweis:** Keine Garantie â€” dient zur Simulation.

## Max drawdown tolerance (Max. Drawdown)
**Was:** Maximal tolerierter RÃ¼ckgang vom HÃ¶chststand in Prozent.  
**Warum:** Hilft bei Alarmen und Risikosteuerung.

## Rebalance HÃ¤ufigkeit
**Optionen:** monthly, quarterly, yearly, threshold.  
**Was:** Wie oft das Portfolio automatisch wieder auf Zielgewichte gebracht wird.

## Allowed instruments / ETFs
**Was:** Liste erlaubter ETFs oder Assetâ€‘Keys.  
**Wie nutzen:** WÃ¤hle aus dem vordefinierten ETFâ€‘Universe oder gib eigene Keys ein.

## Autoâ€‘normalize
**Was:** Normiert Equity+Bonds+Cash automatisch auf 100%.  
**Wann nutzen:** Empfohlen fÃ¼r Einsteiger.

## Presets
**Was:** Vorgefertigte Profile (Conservative, Balanced, Aggressive).  
**Wie nutzen:** WÃ¤hle ein Preset, passe Werte an, speichere als eigenes Profil.

## Hinweise zur Sicherheit und Daten
- **Datenquellen:** Historische Daten und Modelle sind nur zur Simulation.  
- **Verantwortung:** Entscheidungen bleiben beim Nutzer; das Tool liefert Analysen und VorschlÃ¤ge.

## Kurzanleitung (Quickstart)
1. Ã–ffne **Profile** â†’ wÃ¤hle ein Preset (z. B. Balanced).  
2. PrÃ¼fe Asset Allocation; aktiviere **Autoâ€‘normalize**.  
3. WÃ¤hle erlaubte ETFs oder nutze Presetâ€‘ETFs.  
4. Klicke **Profil speichern**.  
5. Wechsle zur Strategie/Simulation und wende das Profil an.




# Makro- und Risiko-Lexikon

- **gdp_growth**: BIP-Wachstum einer Volkswirtschaft.
- **inflation**: Verbraucherpreisindex, misst Preissteigerungen.
- **interest_rate**: Leitzins der Zentralbank.
- **unemployment**: Arbeitslosenquote.
- **oil_price**: RohÃ¶lpreis.
- **fx_rate**: Wechselkurs, z.â€¯B. USD/EUR.
- **total_risk**: Aggregierter Risikoscore aus allen Komponenten.
- **inflation_risk**: Risiko aus Inflation und Ã–lpreis.
- **interest_risk**: Risiko aus Zinsniveau.
- **growth_risk**: Risiko aus schwachem Wachstum.
- **labor_risk**: Risiko aus Arbeitsmarkt.
- **fx_risk**: Risiko aus FX-VolatilitÃ¤t.
- **market_stress**: Marktstress, aktuell Proxy Ã¼ber FX-VolatilitÃ¤t.

# Makro- und Risiko-Lexikon

## Makrovariablen

- **gdp_growth**  
  BIP-Wachstum einer Volkswirtschaft.

- **inflation**  
  Verbraucherpreisindex, misst Preissteigerungen.

- **interest_rate**  
  Leitzins der Zentralbank.

- **unemployment**  
  Arbeitslosenquote.

- **oil_price**  
  RohÃ¶lpreis.

- **fx_rate**  
  Wechselkurs, z.â€¯B. USD/EUR.

---

## Risiko-Komponenten

- **inflation_risk**  
  Risiko aus Inflation und Ã–lpreis.

- **interest_risk**  
  Risiko aus Zinsniveau.

- **growth_risk**  
  Risiko aus schwachem Wachstum.

- **labor_risk**  
  Risiko aus Arbeitsmarkt.

- **fx_risk**  
  Risiko aus FX-VolatilitÃ¤t.

- **market_stress**  
  Marktstress, aktuell Proxy Ã¼ber FX-VolatilitÃ¤t.

- **total_risk**  
  Aggregierter Risikoscore aus allen Komponenten.

