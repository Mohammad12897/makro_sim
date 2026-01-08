# Risiko-Modell – Methodikdokumentation

### Interpretation
Interpretation: Status‑Radar (Makro, Geo, Governance, Finanz, Sozial)
Das Status‑Radar zeigt das aktuelle Risikoprofil eines Landes über fünf Dimensionen.
Jede Achse liegt zwischen 0 = niedriges Risiko und 1 = hohes Risiko.

Achsen:
- Makro → Wachstum, Inflation, Haushaltslage
- Geo → geopolitische Spannungen, Abhängigkeiten
- Governance → Institutionen, Rechtsstaatlichkeit, Korruption
- Finanz → Schulden, Liquidität, Bankenstabilität
- Sozial → gesellschaftliche Stabilität

### Interpretation:
- Kleine kompakte Fläche → geringes Risiko
- Große ausgefranste Fläche → mehrere Risikotreiber erhöht
- Einzelne Spitzen → spezifische Schwachstellen
- Symmetrisch → breit verteilte Risiken
- Asymmetrisch → einzelne dominante Faktoren

Grenzwerte:
| **Risiko‑Scorer** | **Interpretation** |
|---|---:|
| **< 0.30** | **niedrig (grün)** |
| **0.30–0.50** | **moderat (gelb)** |
| **0.50–0.70** | **erhöht (orange)** |
| **> 0.70** | **kritisch (rot)** |


### Interpretation: Delta‑Radar (Veränderungen gegenüber Default)
Das Delta‑Radar zeigt wie sich das Risikoprofil verändert, wenn Parameter angepasst oder Szenarien angewendet werden.

Bedeutung:
- Positive Werte (nach außen) → Risiko steigt
- Negative Werte (nach innen) → Risiko sinkt
- Null-Linie → keine Veränderung

### Interpretation:
- Große Ausschläge → starke Veränderung
- Breite Ausdehnung → systemische Risikoänderung
- Einzelne Spitzen → gezielte Effekte (z. B. Governance‑Schock)
- Symmetrisch → breit gestreute Veränderungen

Grenzwerte:
| **Delta** | **Interpretation** |
|---|---:|
| **< ±0.05** | **vernachlässigbar** |
| **±0.05–0.15** | **spürbare Veränderung** |
| **±0.15–0.30** | **deutliche Veränderung** |
| **> ±0.30** | **struktureller Risiko‑Shift** |

Interpretation: Risiko‑vs‑Resilienz‑Radar
Dieses Radar zeigt die Balance zwischen Risiko und Widerstandsfähigkeit eines Landes.

Achsen:
- Risiko → Gesamt‑Risiko‑Score
- Resilienz → 1 − Risiko
- Governance → institutionelle Stabilität
- Finanz → finanzielle Puffer
- Sozial → gesellschaftliche Kohäsion

### Interpretation:
- Große Resilienz‑Fläche → hohe Schockrobustheit
- Große Risiko‑Fläche → erhöhte Verwundbarkeit
- Governance/Finanz/Sozial erklären die Resilienz
- Ausgewogene Form → stabile Struktur
- Asymmetrische Form → einzelne Schwachstellen

Grenzwerte:
| **Risiko** | **Resilienz** | **Interpretation** |
|---|---:|---:|
| **< 0.30** | **>0.70** | **sehr hohe Resilienz** |
| **0.30–0.50** | **0.50–0.70** | **ausgewogene Lage** |
| **0.50–0.70** | **0.30–0.50** | **erhöhte Verwundbarkeit** |
| **> 0.70** | **< 0.30** | **skritische Lage** |


### Interpretation: Risiko-Heatmap nach Ländern

Die Risiko-Heatmap zeigt die relative Risikolage verschiedener Länder über mehrere Dimensionen.
Jede Zelle ist farblich codiert und ermöglicht einen schnellen visuellen Vergleich.

Achsen / Spalten:
- Makro: Wachstum, Inflation, fiskalische Stabilität
- Geo: geopolitische Risiken, Abhängigkeiten, Sanktionsrisiken
- Governance: Institutionenqualität, Rechtsstaatlichkeit, Korruption
- Total: Gesamt-Risiko-Score

Interpretation:
- Grün: niedriges Risiko
- Gelb: moderates Risiko
- Orange: erhöhtes Risiko
- Rot: kritisches Risiko

Nutzung:
- Länder mit vielen roten/orangen Feldern weisen strukturelle Schwächen auf.
- Länder mit überwiegend grünen Feldern gelten als stabil.
- Unterschiede zwischen Makro, Geo und Governance zeigen, welche Faktoren das Risiko dominieren.
- Der Total-Score fasst alle Dimensionen zusammen und dient als Gesamtindikator.

Hinweis:
Die Heatmap dient der schnellen Orientierung. Für detaillierte Analysen sollten Radar-Diagramme, Szenarien und Sensitivitätsanalysen hinzugezogen werden.



### Interpretation: Szenario-Analyse

Die Szenario-Engine zeigt, wie sich das Risikoprofil eines Landes verändert, wenn bestimmte Parameter gezielt verändert werden.
Ein Szenario kann makroökonomische, geopolitische oder Governance-bezogene Schocks simulieren.

Bedeutung:
- Positive Änderungen → Risiko steigt
- Negative Änderungen → Risiko sinkt
- Die Bedeutung (hoch/mittel/gering) zeigt, wie stark der Parameter das Gesamtrisiko beeinflusst.

Interpretation:
- Hohe Bedeutung + starke Änderung → struktureller Risikotreiber
- Mittlere Bedeutung → relevante, aber nicht dominante Wirkung
- Geringe Bedeutung → Parameter hat nur begrenzten Einfluss
- Rote Farbe → Risiko steigt
- Grüne Farbe → Risiko sinkt

Nutzung:
- Identifikation der wichtigsten Risikotreiber
- Bewertung politischer oder wirtschaftlicher Maßnahmen
- Simulation von Stressszenarien (z. B. Governance-Schock, Energiekrise, Finanzstress)



Interpretation: Sensitivitätsanalyse

Die Sensitivitätsanalyse zeigt, welche Parameter das Gesamtrisiko eines Landes am stärksten beeinflussen.
Jeder Parameter wird einzeln leicht verändert, um seine Wirkung auf den Risiko-Score zu messen.

Bedeutung:
- Δ Risiko → Veränderung des Gesamt-Risikos bei kleiner Parameteränderung
- Hohe Bedeutung → starker Einfluss auf das Risiko
- Mittlere Bedeutung → relevanter Einfluss
- Geringe Bedeutung → kaum Einfluss

Interpretation:
- Hohe Δ-Werte → zentrale Risikotreiber
- Niedrige Δ-Werte → Parameter mit geringer Relevanz
- Rote Farbe → Risiko steigt bei Parametererhöhung
- Grüne Farbe → Risiko sinkt bei Parametererhöhung

Nutzung:
- Priorisierung politischer Maßnahmen
- Identifikation der wichtigsten Stellhebel
- Unterstützung bei Reformstrategien



Interpretation: Prognose (Deterministisch & Monte-Carlo)

Die Prognose zeigt, wie sich das Risiko eines Landes langfristig entwickeln könnte.
Es werden zwei Methoden verwendet:

1. Deterministische Prognose:
   - Parameter entwickeln sich nach festen Annahmen (z. B. Innovation steigt leicht, Verschuldung steigt moderat).
   - Ergebnis: eine einzelne Risiko-Kurve.

2. Monte-Carlo-Prognose:
   - Parameter entwickeln sich zufällig innerhalb realistischer Schwankungsbreiten.
   - Ergebnis: viele mögliche Risiko-Pfade.
   - Der Median zeigt den typischen Verlauf.
   - Das 5–95%-Band zeigt die Unsicherheit.

Interpretation:
- Steigende Kurve → Risiko nimmt langfristig zu
- Fallende Kurve → Risiko sinkt
- Breites Unsicherheitsband → hohe Unsicherheit über die Zukunft
- Enges Band → stabile Entwicklung

Nutzung:
- Bewertung langfristiger Stabilität
- Analyse von Reformbedarf
- Risikoabschätzung unter Unsicherheit



### Interpretation: Risiko-Dashboard

Das Risiko-Dashboard bietet eine kompakte Gesamtübersicht über die Risikolage eines Landes.
Es kombiniert mehrere Analyseinstrumente, um sowohl den aktuellen Zustand als auch Trends, Veränderungen und strukturelle Schwachstellen sichtbar zu machen.

Elemente des Dashboards:

1. Gesamt-Risiko-Ampel:
   - Zeigt den aktuellen Risiko-Score in einer Farbstufe (grün, gelb, orange, rot).
   - Dient als schnelle Einschätzung der Gesamtlage.

2. Status-Radar:
   - Visualisiert die Risikostruktur über fünf Dimensionen: Makro, Geo, Governance, Finanz, Sozial.
   - Zeigt, welche Bereiche stabil oder kritisch sind.

3. Risiko-vs.-Resilienz-Radar:
   - Stellt Risiko und Widerstandsfähigkeit gegenüber.
   - Zeigt, ob ein Land Schocks gut absorbieren kann.

4. Delta-Radar:
   - Zeigt Veränderungen gegenüber dem Ausgangszustand.
   - Macht sichtbar, welche Faktoren sich verschlechtert oder verbessert haben.

5. Frühwarnindikatoren:
   - Textbasierte Hinweise auf kritische Entwicklungen.
   - Identifiziert Risikobereiche, die besondere Aufmerksamkeit erfordern.

6. Mini-Prognose:
   - Zeigt den erwarteten Risiko-Trend der nächsten Jahre.
   - Unterstützt langfristige Einschätzungen.

7. Mini-Heatmap:
   - Vergleich mit anderen Ländern.
   - Zeigt relative Stärken und Schwächen.

Das Dashboard ermöglicht eine schnelle, umfassende und intuitive Einschätzung der Risikolage und unterstützt datenbasierte Entscheidungen.



### Interpretation: Länder-Benchmarking

Das Benchmarking-Modul ermöglicht den strukturierten Vergleich eines Landes mit mehreren anderen Ländern.
Es kombiniert Radar-Diagramme, Heatmaps, Rankings und automatische Textinterpretationen, um Unterschiede und Gemeinsamkeiten sichtbar zu machen.

Elemente des Benchmarkings:

1. Multi-Radar:
   - Vergleicht die Risikostruktur über fünf Dimensionen.
   - Zeigt, welche Länder ähnliche Muster aufweisen.
   - Identifiziert Ausreißer und strukturelle Schwächen.

2. Mini-Heatmap:
   - Farblich codierter Vergleich der Risiko-Dimensionen.
   - Zeigt relative Stärken und Schwächen der Länder.

3. Ranking-Tabelle:
   - Sortiert Länder nach Gesamt-Risiko oder einzelnen Dimensionen.
   - Erlaubt eine schnelle Einordnung im internationalen Vergleich.

4. Automatische Benchmark-Interpretation:
   - Liefert eine textbasierte Analyse der wichtigsten Unterschiede.
   - Hebt Stärken, Schwächen und Besonderheiten hervor.
   - Unterstützt datenbasierte Entscheidungen.

Das Benchmarking-Modul bietet eine umfassende, intuitive und vergleichende Sicht auf die Risikolage mehrerer Länder.



### Interpretation: Handel & Lieferketten

Die Dimension „Handel & Lieferketten“ beschreibt die strukturellen Abhängigkeiten eines Landes von internationalen Warenströmen, kritischen Importen, 
Exportmärkten und globalen Produktionsnetzwerken. Sie ist ein zentraler Treiber für wirtschaftliche Stabilität, geopolitische Verwundbarkeit und makroökonomische Resilienz.

1. Export-Konzentration
Eine hohe Export-Konzentration bedeutet, dass ein Land stark von wenigen Produkten oder Branchen abhängig ist. Beispiele sind Öl-Exporte, 
Automobilindustrie oder Halbleiterproduktion. Je stärker die Konzentration, desto größer das Risiko bei Nachfrageschocks, technologischen Umbrüchen oder 
geopolitischen Konflikten. Länder mit diversifizierten Exportstrukturen sind widerstandsfähiger gegenüber globalen Krisen.

2. Import kritischer Güter
Importabhängigkeit bei kritischen Gütern wie Energie, Medikamenten, Maschinen, Halbleitern oder Nahrungsmitteln erhöht die Verwundbarkeit. 
Lieferstopps, Sanktionen oder Transportstörungen können direkte Auswirkungen auf Produktion, Versorgungssicherheit und Preisstabilität haben. 
Eine hohe Importabhängigkeit in sicherheitsrelevanten Bereichen gilt als strategisches Risiko.

3. Partner-Konzentration
Wenn ein Land stark von wenigen Handelspartnern abhängig ist, entsteht ein geopolitisches Risiko. Politische Spannungen, 
Sanktionen oder wirtschaftliche Schocks in diesen Partnerländern können die eigene Wirtschaft unmittelbar treffen. Eine breite Diversifizierung der 
Handelspartner reduziert diese Abhängigkeit und erhöht die strategische Autonomie.

4. Lieferkettenrisiko
Globale Lieferketten sind komplex und anfällig für Störungen. Hohe Abhängigkeit von einzelnen Produktionsstandorten, Just-in-Time-Logistik, 
geringe Lagerpuffer oder die Nutzung kritischer Seewege (z. B. Suezkanal, Taiwanstraße) erhöhen das Risiko. Naturkatastrophen, geopolitische Konflikte oder 
Transportengpässe können zu Produktionsausfällen und Preisschocks führen.

5. Gesamtinterpretation
Ein hohes Handels- und Lieferkettenrisiko weist auf strukturelle Verwundbarkeiten hin, die sich in Krisenzeiten schnell materialisieren können. 
Länder mit hoher Export- oder Importkonzentration, wenigen Handelspartnern oder fragilen Lieferketten sind besonders anfällig für externe Schocks. 
Eine diversifizierte Handelsstruktur, robuste Logistik und strategische Lagerhaltung erhöhen die Resilienz.

Die Dimension „Handel & Lieferketten“ ergänzt das bestehende Risiko-Modell um eine zentrale Perspektive, die sowohl wirtschaftliche als auch 
geopolitische Stabilität beeinflusst. Sie ermöglicht eine präzisere Bewertung der strukturellen Abhängigkeiten eines Landes und unterstützt datenbasierte Entscheidungen 
in Risikoanalyse, Szenarioplanung und strategischer Politikgestaltung.



### Kritische Werte und Hinweise

| **Parameter** | **Risiko Schwelle** | **Warum kritisch** | **Empfohlene Aktion** |
|---|---:|---|---|
| **USD_Dominanz** | **> 0.75** | Starke Abhängigkeit vom US‑Dollar erhöht Import‑ und Finanzrisiko | Diversifikation prüfen; RMB_Akzeptanz erhöhen |
| **RMB_Akzeptanz** | **< 0.05** | Sehr geringe Akzeptanz reduziert Ausweichmöglichkeiten | Zahlungsrails und Handelsabkommen fördern |
| **Zugangsresilienz** | **< 0.5** | Niedrige Resilienz → hohe Unterbrechungsanfälligkeit | Infrastruktur und Alternativnetz ausbauen |
| **Reserven_Monate** | **< 3** Monate | Geringe Puffer für Importfinanzierung | Reserven aufstocken; Kreditlinien sichern |
| **FX_Schockempfindlichkeit** | **> 1.2** | Hohe Empfindlichkeit → starke Preisvolatilität | Hedging, Liquiditätsmanagement verstärken |
| **Sanktions_Exposure** | **> 0.1** | Hohes Exposure → reale Handelsrisiken | Lieferketten diversifizieren; Compliance prüfen |
| **Alternativnetz_Abdeckung** | **< 0.3** | Wenig Ausweichnetz → eingeschränkte Optionen bei Störungen | Alternative Zahlungswege aufbauen |
| **Liquiditaetsaufschlag** | **> 0.05** | Hohe Zusatzkosten bei Knappheit | Liquiditätsreserven erhöhen |
| **CBDC_Nutzung** | **< 0.1 oder > 0.9** | Sehr niedrig: verpasste Effizienz; sehr hoch: neue Abhängigkeiten | Technologie und Governance prüfen |
| **Golddeckung** | **< 0.05** | Sehr geringe Golddeckung reduziert Krisenpuffer | Diversifikation der Reserven erwägen |
| **verschuldung** | **> 1.0 (UI Skala)** | Sehr hohe Verschuldung erhöht fiskalische Verwundbarkeit | Konsolidierung, externe Finanzierung prüfen |
| **demokratie** | **< 0.3** | Geringe Rechenschaft → erhöhtes politisches Risiko | Governance Maßnahmen und Transparenz stärken |

### A) Makro‑Risiko (40%)
- **Verschuldung**
- **Inflation**
- **FX‑Schockempfindlichkeit**
- **Reserven**
- **macro =**
- **0.5 * (verschuldung_norm_exp) +**
- **0.3 * (fx_norm) +**
- **0.2 * (reserven_norm_log)**


### B) Geopolitisches Risiko (35%)
- **USD‑Dominanz**
- **Sanktions‑Exposure**
- **Alternativnetz‑Abdeckung (invertiert)**
- **geo =**
- **0.4 * usd_dom_norm +**
- **0.4 * sanktions_norm +**
- **0.2 * (1 - alternativnetz_norm)^1.5**

### C) Governance‑Risiko (25%)
- **Demokratie (invertiert und stärker gewichtet)**
- **Korruption (stark gewichtet)**
- **Innovation (linear)**
- **Fachkräfte (linear)**
- **gov =**
- **0.45 * (1 - demokratie) +**
- **0.30 * korruption +**
- **0.15 * (1 - innovation) +**
- **0.10 * (1 - fachkraefte)**

### Gesamt‑Risiko: 0.4 * risk_macro(p) + 0.3 * risk_geo(p) + 0.2 * risk_governance(p)

### finanz = gewicht1 * verschuldung
       + gewicht2 * FX_Schockempfindlichkeit
       + gewicht3 * Liquiditaetsaufschlag
       - gewicht4 * Reserven
       - gewicht5 * Golddeckung

### Finanz‑Risiko als normierter Wert zwischen 0 und 1 liegt.
- **0.0 – 0.3 → stabil**
- **0.3 – 0.5 → moderat**
- **0.5 – 0.7 → erhöht**
- **> 0.7 → kritisch**

### Finanz
- **Verwendet nur:**
- **verschuldung**
- **FX_Schockempfindlichkeit**
- **\mathrm{finanz}=\min \left( 1,\  rac{\mathrm{verschuldung}}{2}+rac{\mathrm{FX\_ Schockempfindlichkeit}}{2}ight)** 
- **Alles andere in den Presets (RMB, Zugangsresilienz, CBDC, Gold, etc.) hat keinen Einfluss auf finanz**


### sozial = gewicht1 * korruption
       + gewicht2 * instabilitaet
       - gewicht3 * demokratie
       - gewicht4 * fachkraefte
       - gewicht5 * energie

### Sozial-Risiko als normierter Wert zwischen 0 und 1 liegt
- **0.0 – 0.3 → hohe soziale Stabilität**
- **0.3 – 0.5 → moderat**
- **0.5 – 0.7 → erhöhte Risiken**
- **> 0.7 → kritische Lage**

### Sozial
- **Verwendet nur:**
- **fachkraefte**
- **demokratie**
- **\mathrm{sozial}=\min \left( 1,\  0.5\cdot (1-\mathrm{fachkraefte})+0.5\cdot (1-\mathrm{demokratie})ight)** 
- **Auch hier: Energie, Stabilität, Korruption etc. gehen nicht in sozial ein.**

### Ranking: Makro‑Risiko + Geopolitisches Risiko + Governance‑Risiko + finanz + sozial

### Ranking
- **Für jedes Land:**
- **es werden die Preset‑Parameter geladen (presets["DE"], presets["US"], …)**
- **daraus wird scores = compute_risk_scores(params) berechnet**
- **das Ranking sortiert dann nach scores["total"]:**
- **\mathrm{total}=0.40\cdot \mathrm{macro}+0.35\cdot \mathrm{geo}+0.25\cdot \mathrm{gov}**
- **Länder mit niedrigerem total → besserer Rang.**




### Farbliche Markierung (kritisch / warnend / stabil)
| **Score** | **Kategorie** | **Farbe** |
|---|---|---|
| **0.00–0.33** | **Stabil** | Grün |
| **0.34–0.66** | **Warnung** | Gelb |
| **0.67–1.00** | **Kritisch** | Rot |
| **netto_resilienz=** | **Zugangsresilienz * (1 - risk_macro)** |
| **importkosten_mult=** | **1 + risk_geo * 0.2** |
| **system_volatilitaet=** | **0.1 + risk_governance * 0.3** |

#### Validierungsregeln beim Import
- **Typprüfung**: `Reserven_Monate` muss **int** sein; andere numerische Parameter **float**.
- **Bereichsprüfung**: Werte außerhalb der UI‑Grenzen werden **geclamped** (auf nächstzulässigen Wert) oder als Fehler markiert.
- **Sanity Checks**: Kombinationen wie `Reserven_Monate < 3` und `USD_Dominanz > 0.7` erzeugen eine **Kritisch**‑Warnung.
- **UI Verhalten**: In der Import‑Vorschau werden Presets mit `Warnung` oder `Kritisch` markiert; beim Bestätigen wird eine Zusammenfassung angezeigt.

### Neuer Parameter: Demokratie (`demokratie`)
- **Definition**
  - Skala **0.0 – 1.0**; 0 = autoritär/geringe Rechenschaftspflicht, 1 = stabile, inklusive Demokratie mit funktionierenden Institutionen.
- **Direkte Effekte im Modell**
  - **Resilienz**: Demokratie erhöht `netto_resilienz` (z. B. additiv), weil Rechtsstaat, Transparenz und Rechenschaft Investitions‑ und Anpassungsfähigkeit fördern.
  - **Volatilität**: Demokratie reduziert `system_volatilitaet` (z. B. kleinerer Basiseffekt), da Informationsflüsse und Institutionen Schocks dämpfen.
  - **Importkosten**: Demokratie kann `importkosten_mult` leicht senken durch besseren Eigentumsschutz und geringere Transaktionskosten.


