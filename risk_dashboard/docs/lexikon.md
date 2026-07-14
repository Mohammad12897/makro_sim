# Lexikon

## Equity weight
**Definition:** Anteil des Portfolios, der in Aktien investiert ist.  
**Warum wichtig:** Aktien bieten langfristig höhere Renditen, erhöhen aber Volatilität und Drawdown‑Risiko.

## Bond weight
**Definition:** Anteil des Portfolios in Anleihen (Staatsanleihen, Unternehmensanleihen).  
**Warum wichtig:** Dämpft Schwankungen und reduziert erwarteten Drawdown.

## Cash
**Definition:** Liquiditätsreserve in Form von Bargeld oder kurzfristigen Geldmarktinstrumenten.  
**Warum wichtig:** Dient als Puffer für kurzfristige Ausgaben und Rebalancing.

## Target annual return
**Definition:** Erwartete durchschnittliche Jahresrendite (Schätzwert).  
**Warum wichtig:** Dient zur Simulation und Zielsetzung; keine Garantie.

## Max drawdown tolerance
**Definition:** Maximal tolerierter Rückgang vom Höchststand in Prozent.  
**Warum wichtig:** Hilft bei Risikosteuerung, Stop‑Loss‑Regeln und psychologischer Planung.

## Rebalance frequency
**Definition:** Wie oft das Portfolio automatisch wieder auf Zielgewichte gebracht wird (z. B. monthly, quarterly).  
**Warum wichtig:** Häufigeres Rebalancing reduziert Drift, kann aber Transaktionskosten erhöhen.

## Allowed instruments
**Definition:** Liste erlaubter Asset‑Klassen oder ETFs (z. B. global_equity_etf).  
**Warum wichtig:** Beschränkt die Auswahl bei automatischen Strategien und Screening.

## Drawdown
**Definition:** Prozentualer Rückgang vom letzten Höchststand eines Portfolios.  
**Warum wichtig:** Misst das Risiko eines Portfolios in Stressphasen.

## Volatilität
**Definition:** Statistische Schwankungsbreite der Renditen (Standardabweichung).  
**Warum wichtig:** Höhere Volatilität bedeutet größere Schwankungen und potenziell größere Drawdowns.




# Lexikon - Risiko Dashboard

Dieses Lexikon erklärt die wichtigsten Begriffe und UI‑Felder im Risk Dashboard in einfacher Sprache.

## Profil / Profilname
**Was:** Ein gespeichertes Set von Einstellungen (Allocation, Ziele, erlaubte ETFs).  
**Warum:** Ermöglicht schnelles Wechseln zwischen Strategien (z. B. konservativ, ausgewogen, aggressiv).

## Risikokategorie
**Low / Medium / High** Basisvorgaben für ein Profil.  
**Low:** Kapitalerhalt; niedrige Volatilität.  
**Medium:** Ausgewogenes Wachstum mit Schutz.  
**High:** Langfristiges Wachstum; höhere Volatilität.

## Equity weight (Aktienanteil)
**Was:** Prozentualer Anteil des Portfolios in Aktien.  
**Hinweis:** Höherer Aktienanteil → höhere Renditeerwartung, aber auch höhere Schwankungen.

## Bond weight (Anleihenanteil)
**Was:** Prozentualer Anteil in Anleihen.  
**Hinweis:** Dämpft Schwankungen und reduziert Drawdown.

## Cash
**Was:** Liquiditätsreserve in Prozent.  
**Warum:** Puffer für kurzfristige Ausgaben oder Rebalancing.

## Target annual return (Ziel Jahresrendite)
**Was:** Erwartete durchschnittliche Jahresrendite (Schätzwert).  
**Hinweis:** Keine Garantie → dient zur Simulation.

## Max drawdown tolerance (Max. Drawdown)
**Was:** Maximal tolerierter Rückgang vom Höchststand in Prozent.  
**Warum:** Hilft bei Alarmen und Risikosteuerung.

## Rebalance Häufigkeit
**Optionen:** monthly, quarterly, yearly, threshold.  
**Was:** Wie oft das Portfolio automatisch wieder auf Zielgewichte gebracht wird.

## Allowed instruments / ETFs
**Was:** Liste erlaubter ETFs oder Asset‑Keys.  
**Wie nutzen:** Wähle aus dem vordefinierten ETF‑Universe oder gib eigene Keys ein.

## Auto‑normalize
**Was:** Normiert Equity+Bonds+Cash automatisch auf 100%.  
**Wann nutzen:** Empfohlen für Einsteiger.

## Presets
**Was:** Vorgefertigte Profile (Conservative, Balanced, Aggressive).  
**Wie nutzen:** Wähle ein Preset, passe Werte an, speichere als eigenes Profil.

## Hinweise zur Sicherheit und Daten
- **Datenquellen:** Historische Daten und Modelle sind nur zur Simulation.  
- **Verantwortung:** Entscheidungen bleiben beim Nutzer; das Tool liefert Analysen und Vorschläge.

## Kurzanleitung (Quickstart)
1. Öffne **Profile** → wähle ein Preset (z. B. Balanced).  
2. Prüfe Asset Allocation; aktiviere **Auto‑normalize**.  
3. Wähle erlaubte ETFs oder nutze Preset‑ETFs.  
4. Klicke **Profil speichern**.  
5. Wechsle zur Strategie/Simulation und wende das Profil an.




# Makro- und Risiko-Lexikon

- **gdp_growth**: BIP-Wachstum einer Volkswirtschaft.
- **inflation**: Verbraucherpreisindex, misst Preissteigerungen.
- **interest_rate**: Leitzins der Zentralbank.
- **unemployment**: Arbeitslosenquote.
- **oil_price**: Rohölpreis.
- **fx_rate**: Wechselkurs, z.B. USD/EUR.
- **total_risk**: Aggregierter Risikoscore aus allen Komponenten.
- **inflation_risk**: Risiko aus Inflation und Ölpreis.
- **interest_risk**: Risiko aus Zinsniveau.
- **growth_risk**: Risiko aus schwachem Wachstum.
- **labor_risk**: Risiko aus Arbeitsmarkt.
- **fx_risk**: Risiko aus FX-Volatilität.
- **market_stress**: Marktstress, aktuell Proxy über FX-Volatilität.

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
  Rohölpreis.

- **fx_rate**  
  Wechselkurs, z.B. USD/EUR.

---

## Risiko-Komponenten

- **inflation_risk**  
  Risiko aus Inflation und Ölpreis.

- **interest_risk**  
  Risiko aus Zinsniveau.

- **growth_risk**  
  Risiko aus schwachem Wachstum.

- **labor_risk**  
  Risiko aus Arbeitsmarkt.

- **fx_risk**  
  Risiko aus FX-Volatilität.

- **market_stress**  
  Marktstress, aktuell Proxy über FX-Volatilität.

- **total_risk**  
  Aggregierter Risikoscore aus allen Komponenten.

