# ETF Guidance

**Zweck**  
Praktischer Leitfaden, wie ETFs im `risk_dashboard` ausgewählt, validiert und in Backtests verwendet werden. Enthält eine kompakte Attributtabelle (Praxisbeispiel), Entscheidungsprinzipien, Allokations‑Orientierungen, technische Vorgaben für die App‑Integration und konkrete Handlungsschritte für die Analyse‑Pipeline.

---

## 1. Auswahlkriterien für ETFs
- **Diversifikation**: Bevorzuge breit gestreute ETFs (Large Cap, Total Market).  
- **Liquidität**: Prüfe durchschnittliches Handelsvolumen und Spread; niedrige Spreads reduzieren Slippage.  
- **Kosten**: Achte auf **TER** und Handelskosten; niedrige TER ist vorteilhaft für langfristige Backtests.  
- **Repräsentativität**: Verwende ETFs, die den gewünschten Index sauber abbilden.  
- **Historische Verfügbarkeit**: Nur ETFs verwenden, die für den gewünschten Zeitraum vollständige Kursdaten liefern.

---

## 2. ETF Attributtabelle (Praxisbeispiel)
| **Attribut** | **ETF** | **Einzelaktie** | **Krypto (BTC)** | **Mix (Portfolio)** |
|---|---:|---:|---:|---:|
| **Diversifikation** | Hoch; mehrere Werte in einem Produkt | Niedrig; einzelnes Unternehmen | Sehr niedrig; einzelner Vermögenswert | Sehr hoch möglich |
| **Volatilität** | Mittel bis hoch (je nach ETF) | Hoch | Sehr hoch | Abhängig von Gewichtung |
| **Liquidität** | Meist hoch | Meist hoch (Blue Chips) | Hoch, aber 24/7 | Kombiniert |
| **Kosten** | Niedrigere TER; Handelskosten | Handelskosten; ggf. Steuern | Handelsgebühren; Wallet‑Kosten | Kombiniert |
| **Steuerliche Komplexität (DE)** | Standard‑Kapitalertragsteuer | Standard‑Kapitalertragsteuer; ggf. Teilfreistellung bei ETFs | Komplexer (Haltedauer, Mining, Wallet) | Abhängig von Komponenten |
| **Eignung für Kernposition** | Sehr gut | Eher als Satellit | Eher als kleiner Satellit | Optimal für Diversifikation |

---

## 3. Was die genannten Symbole bedeuten für die Entscheidung
- **NVDA, AAPL** — Einzelaktien mit hohem Wachstumspotenzial, aber auch hohem Unternehmens‑ und Kursrisiko; eher **Satelliten**‑Positionen.  
- **EXS1.DE, DAX** — Index/ETF‑ähnliche Produkte; breite Markt‑Abdeckung; gut für **Core**‑Positionen und Diversifikation.  
- **BTC** — sehr hohe Volatilität, geringe stabile Korrelation zu Aktien; nur als kleiner, spekulativer **Satellit**.  
- **MBG** (Anleihe/Branchenprodukt) — reduziert typischerweise Volatilität; gut zur **Stabilisierung**.

---

## 4. Entscheidungsprinzipien
- **Ziel & Zeithorizont:** Langfristige Ziele (≥10 Jahre) vertragen höhere Aktienquoten; kurzfristige Ziele brauchen Stabilität.  
- **Risikotoleranz:** Wer Schwankungen nicht aushält, erhöht ETF/Anleihen‑Anteil.  
- **Diversifikation:** Einzelaktien erhöhen Klumpenrisiko; ETFs reduzieren dieses effizient.  
- **Liquiditätsbedarf:** Kurzfristiger Bedarf → mehr Cash/kurzfristige Anleihen.  
- **Kosten & Steuern:** TER, Handelskosten und steuerliche Behandlung beeinflussen Rendite.  
- **Krypto:** Nur kleiner Prozentsatz, da sehr spekulativ.

---

## 5. Praktische Allokations‑Beispiele (Orientierung, keine Anlageempfehlung)
- **Konservativ:** ETFs **70–80%** | Anleihen/MBG **15–25%** | Einzelaktien **0–5%** | BTC **0–2%**  
- **Ausgewogen / Moderat:** ETFs **50–60%** | Einzelaktien **20–30%** | Anleihen/MBG **10–15%** | BTC **1–5%**  
- **Wachstum / Aggressiv:** ETFs **30–40%** | Einzelaktien **40–50%** | Anleihen/MBG **0–10%** | BTC **2–10%**

---

## 6. Konkrete Vorgehensweise (Core‑Satellite + Analyse‑Pipeline)
1. **Core‑Satellite:** ETFs als Core (breite Markt‑Abdeckung); NVDA/AAPL als Satelliten; BTC nur kleiner Satellit.  
2. **Positionsgrößen:** Einzelaktien‑Positionen begrenzen (z. B. **3–7%** pro Aktie bei moderatem Risiko).  
3. **Korrelation prüfen:** Korrelationen zwischen Positionen berechnen; hohe Korrelation erhöht Gesamtrisiko.  
4. **Rebalancing:** Regeln festlegen (z. B. jährliches Rebalancing oder Schwellen ±5–10%).  
5. **Steuern klären:** Steuerliche Behandlung in Deutschland prüfen (Kapitalertragsteuer, Krypto‑Regeln).  
6. **Backtest / Simulation:** Historische Simulationen durchführen (Rendite, Volatilität, Max Drawdown, Recovery).  
7. **Score & Kurz‑Einschätzung:** Automatisiertes Scoring (z. B. 0–100) aus Kennzahlen (CAGR, Volatilität, Sharpe, MaxDD, Liquidität) erzeugen und in der UI als Ampel/Score + Text‑Begründung anzeigen.

---

## 7. Technische Vorgaben für die App‑Integration

### 7.1 Datenvalidierung
- **Existenz:** `isinstance(df, pd.DataFrame) and not df.empty`.  
- **Index:** Zeitindex muss `DatetimeIndex` sein und sortiert.  
- **Mindestlänge:** z. B. ≥ 252 Handelstage für 1‑Jahres‑Analysen.  
- **NaN‑Handling:** Fehlende Werte entweder füllen (forward/backfill) oder ablehnen, je nach Strategie.

### 7.2 removed_tickers
- Vor dem Backtest Ticker gegen `prices_df.columns` prüfen und entfernte Ticker in `removed_tickers` dokumentieren:
```py
original = list(available)
available = [t for t in available if t in prices_df.columns]
removed = [t for t in original if t not in available]
