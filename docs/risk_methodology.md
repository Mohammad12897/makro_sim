## Modul 1 – Makroökonomisches Risiko („macro“)

### 1.1 Definition
Das Makro‑Risiko misst die strukturelle Stabilität einer Volkswirtschaft.  
Es bewertet die Fähigkeit eines Landes, externe Schocks abzufedern und interne Ungleichgewichte zu managen.

---

### 1.2 Relevanz
- Fundament der wirtschaftlichen Stabilität  
- Bestimmt Kreditwürdigkeit und Refinanzierungskosten  
- Hoher Einfluss auf Inflation, Wachstum und Kapitalflüsse  

---

### 1.3 Indikatoren
| Indikator | Wirkung |
|----------|---------|
| Verschuldung | ↑ Risiko |
| FX‑Schockempfindlichkeit | ↑ Risiko |
| Währungsreserven (Monate) | ↓ Risiko |

---

### 1.4 Risiko‑Mechanismen
- Hohe Verschuldung → fiskalische Verwundbarkeit  
- FX‑Sensitivität → Preisvolatilität, Importkosten  
- Niedrige Reserven → geringe Fähigkeit, Schocks zu absorbieren  

---

### 1.5 Normalisierung
- Verschuldung: exponentiell  
- FX‑Sensitivität: linear skaliert  
- Reserven: logarithmisch  

---

### 1.6 Aggregationsformel
macro = 0.5 * verschuldung_norm_exp + 0.3 * fx_norm + 0.2 * reserven_norm_log

---

### 1.7 Interpretation
| Score | Bedeutung |
|-------|-----------|
| 0.00–0.30 | stabil |
| 0.30–0.55 | moderat |
| 0.55–0.75 | erhöht |
| >0.75 | kritisch |

---

### 1.8 Typische Risikoprofile
- **Hoch:** Schwellenländer mit hoher Verschuldung  
- **Niedrig:** Länder mit großen Reserven und stabilen Haushalten  

---

### 1.9 Verbindung zu anderen Modulen
- beeinflusst Finanzrisiko  
- verstärkt Währungsrisiken  
- wirkt auf Resilienz im EWS  

---

### 1.10 Nutzung im Modell
- Radar  
- Szenarien (z. B. Zins‑Schock)  
- Prognosen 
### 1.11 Kritische Makro‑Parameter

| Parameter | Schwelle | Warum kritisch | Empfehlung |
|----------|----------|----------------|------------|
| **verschuldung > 1.0** | sehr hohe fiskalische Verwundbarkeit | Refinanzierungsrisiken | Konsolidierung |
| **FX_Schockempfindlichkeit > 1.2** | starke Preisvolatilität | Importkosten steigen | Hedging |
| **Reserven_Monate < 3** | geringe Puffer | Importfinanzierung gefährdet | Reserven erhöhen |

## Modul 2 – Geopolitisches Risiko („geo“)

### 2.1 Definition
Misst die Verwundbarkeit eines Landes gegenüber geopolitischen Spannungen, Abhängigkeiten und Sanktionsrisiken.

---

### 2.2 Relevanz
- Bestimmt Handels‑ und Zahlungsfähigkeit  
- Hoher Einfluss auf Energie‑ und Rohstoffimporte  
- Zentral für außenpolitische Stabilität  

---

### 2.3 Indikatoren
| Indikator | Wirkung |
|----------|---------|
| USD_Dominanz | ↑ Risiko |
| Sanktions_Exposure | ↑ Risiko |
| Alternativnetz_Abdeckung | ↓ Risiko |

---

### 2.4 Risiko‑Mechanismen
- USD‑Abhängigkeit → Zins‑ & Wechselkursrisiken  
- Sanktionen → Handelsunterbrechungen  
- Fehlende Alternativen → strukturelle Verwundbarkeit  

---

### 2.5 Normalisierung
- USD: clamp01  
- Sanktionen: verstärkt (`*2.0`)  
- Alternativnetz: invertiert  

---

### 2.6 Aggregationsformel
geo = 0.4 * usd_norm + 0.4 * sanktions_norm + 0.2 * (1 - alternativnetz_norm)^1.5

---

### 2.7 Interpretation
| Score | Bedeutung |
|-------|-----------|
| 0.00–0.30 | stabil |
| 0.30–0.55 | moderat |
| 0.55–0.75 | erhöht |
| >0.75 | kritisch |

---

### 2.8 Typische Risikoprofile
- **Hoch:** Länder mit Sanktionsrisiko  
- **Niedrig:** Staaten mit alternativen Zahlungssystemen  

---

### 2.9 Verbindung zu anderen Modulen
- beeinflusst currency  
- wirkt auf Handel & Lieferketten  

---

### 2.10 Nutzung im Modell
- Radar  
- Szenarien (z. B. SWIFT‑Ausschluss)
### 2.11 Kritische geopolitische Parameter

| Parameter | Schwelle | Warum kritisch | Empfehlung |
|----------|----------|----------------|------------|
| **USD_Dominanz > 0.75** | extreme Abhängigkeit vom USD‑System | Import‑ & Finanzrisiken | Diversifikation, RMB‑Clearing |
| **RMB_Akzeptanz < 0.05** | kaum Ausweichmöglichkeiten | hohe Verwundbarkeit | bilaterale Zahlungsrails |
| **Zugangsresilienz < 0.5** | hohe Unterbrechungsanfälligkeit | Störungen in Handel & Energie | Alternativnetzwerke ausbauen |
| **Sanktions_Exposure > 0.1** | reale Sanktionsrisiken | Handelsunterbrechungen | Lieferketten diversifizieren |
| **Alternativnetz_Abdeckung < 0.3** | kaum Ausweichsysteme | Zahlungsrisiken | CIPS, Swap‑Lines |

---

### 2.12 Erweiterte Risiko‑Mechanismen

- Hohe USD‑Dominanz koppelt das Land an US‑Zins‑ und Wechselkurspolitik  
- Geringe RMB‑Akzeptanz verhindert Diversifikation  
- Niedrige Zugangsresilienz erhöht die Wahrscheinlichkeit von Handelsunterbrechungen  
- Fehlende Alternativnetzwerke verstärken Sanktionsrisiken  


## Modul 3 – Governance‑Risiko („governance“)

### 3.1 Definition
Bewertet institutionelle Qualität, Rechtsstaatlichkeit und politische Stabilität.

---

### 3.2 Relevanz
- Fundament für Investitionssicherheit  
- Bestimmt politische Resilienz  
- Reduziert systemische Volatilität  

---

### 3.3 Indikatoren
| Indikator | Wirkung |
|----------|---------|
| Demokratie | ↓ Risiko |
| Korruption | ↑ Risiko |
| Innovation | ↓ Risiko |
| Fachkräfte | ↓ Risiko |

---

### 3.4 Risiko‑Mechanismen
- Schwache Institutionen → politische Instabilität  
- Korruption → Ineffizienz, Kapitalflucht  
- Innovationsschwäche → geringere Wettbewerbsfähigkeit  

---

### 3.5 Normalisierung
- Demokratie invertiert  
- Korruption linear  
- Innovation & Fachkräfte linear  

---

### 3.6 Aggregationsformel  
governance = 0.45 * (1 - demokratie) + 0.30 * korruption + 0.15 * (1 - innovation) + 0.10 * (1 - fachkraefte)

---

### 3.7 Interpretation
| Score | Bedeutung |
|-------|-----------|
| 0.00–0.30 | stabil |
| 0.30–0.55 | moderat |
| 0.55–0.75 | erhöht |
| >0.75 | kritisch |

---

### 3.8 Typische Risikoprofile
- **Hoch:** autoritäre Staaten, hohe Korruption  
- **Niedrig:** stabile Demokratien  

---

### 3.9 Verbindung zu anderen Modulen
- beeinflusst Resilienz  
- wirkt auf Makro‑ und Finanzrisiken  

---

### 3.10 Nutzung im Modell
- Radar  
- Prognosen  
- EWS  
### 3.11 Formel (vollständig)

Das Governance‑Risiko wird als gewichtete Kombination folgender Indikatoren berechnet:

- **Demokratie** (invertiert, stark gewichtet)  
- **Korruption** (stark gewichtet)  
- **Innovation** (linear, invers)  
- **Fachkräfte** (linear, invers)

**Formel:**
governance = 0.45 * (1 - demokratie) + 0.30 * korruption + 0.15 * (1 - innovation) + 0.10 * (1 - fachkraefte)

---

### 3.12 Schwellenwerte & Interpretation

| Score | Bedeutung |
|-------|-----------|
| **0.00–0.30** | stabile Governance |
| **0.30–0.55** | moderat |
| **0.55–0.75** | erhöht |
| **> 0.75** | kritisch |

---

### 3.13 Kritische Governance‑Indikatoren

| Parameter | Schwelle | Warum kritisch | Empfehlung |
|----------|----------|----------------|------------|
| **demokratie < 0.3** | sehr geringe Rechenschaft | erhöht politisches Risiko | Governance‑Reformen |
| **korruption > 0.6** | systemische Ineffizienz | Kapitalflucht, Instabilität | Anti‑Korruptionsmaßnahmen |
| **innovation < 0.4** | geringe Wettbewerbsfähigkeit | langfristige Wachstumsrisiken | F&E‑Investitionen |
| **fachkraefte < 0.5** | Fachkräftemangel | Produktivitätsrisiken | Bildung & Migration |




## Modul 4 – Handelsrisiko („handel“)

### 4.1 Definition
Bewertet strukturelle Abhängigkeiten im Außenhandel.

---

### 4.2 Relevanz
- Bestimmt Export‑ und Importstabilität  
- Hoher Einfluss auf Versorgungssicherheit  
- Kritisch für offene Volkswirtschaften  

---

### 4.3 Indikatoren
| Indikator | Wirkung |
|----------|---------|
| Exportkonzentration | ↑ Risiko |
| Import kritischer Güter | ↑ Risiko |
| Partner‑Konzentration | ↑ Risiko |

---

### 4.4 Risiko‑Mechanismen
- Abhängigkeit von wenigen Produkten/Partnern  
- Störungen → direkte wirtschaftliche Schäden  
- Kritische Güter → strategische Verwundbarkeit  

---

### 4.5 Normalisierung
- alle linear (clamp01)  

---

### 4.6 Aggregationsformel
handel = 0.4 * export_konz + 0.3 * import_krit + 0.3 * partner_konz

---

### 4.7 Interpretation
| Score | Bedeutung |
|-------|-----------|
| 0.00–0.30 | stabil |
| 0.30–0.55 | moderat |
| 0.55–0.75 | erhöht |
| >0.75 | kritisch |

---

### 4.8 Typische Risikoprofile
- **Hoch:** Rohstoffexporteure, Monostrukturen  
- **Niedrig:** diversifizierte Volkswirtschaften  

---

### 4.9 Verbindung zu anderen Modulen
- wirkt auf Lieferketten  
- beeinflusst Makro  

---

### 4.10 Nutzung im Modell
- Radar  
- Benchmarking  
### 4.11 Kritische Handelsparameter

| Parameter | Schwelle | Warum kritisch |
|----------|----------|----------------|
| **export_konzentration > 0.6** | Abhängigkeit von wenigen Produkten |
| **import_kritische_gueter > 0.5** | strategische Verwundbarkeit |
| **partner_konzentration > 0.5** | geopolitische Abhängigkeit |

## Modul 5 – Lieferkettenrisiko („supply_chain“)

### 5.1 Definition
Misst die Verwundbarkeit globaler Produktions‑ und Logistiknetzwerke.

---

### 5.2 Relevanz
- Kritisch für Industrie‑ und Exportländer  
- Hoher Einfluss auf Produktionsstabilität  
- Zentral für Energie‑ und Rohstoffimporte  

---

### 5.3 Indikatoren
- Chokepoint‑Abhängigkeit  
- Just‑in‑Time‑Anteil  
- Produktionskonzentration  
- Lagerpuffer  

---

### 5.4 Risiko‑Mechanismen
- Engpässe → Produktionsausfälle  
- Naturkatastrophen → Unterbrechungen  
- Geopolitik → Transportstörungen  

---

### 5.5 Normalisierung
- linear (clamp01)  

---

### 5.6 Aggregationsformel
supply_chain = compute_supply_chain_risk(p)

---

### 5.7 Interpretation
wie bei anderen Dimensionen  

---

### 5.8 Verbindung zu anderen Modulen
- Handel  
- Energie  
- Geo  

---

### 5.9 Nutzung im Modell
- Radar  
- Szenarien (Lieferketten‑Schock)  
### 5.11 Kritische Lieferkettenparameter

| Parameter | Schwelle | Risiko |
|----------|----------|--------|
| **chokepoint_abhaengigkeit > 0.5** | Engpassrisiko |
| **just_in_time_anteil > 0.7** | geringe Puffer |
| **lager_puffer < 0.3** | hohe Störanfälligkeit |


## Modul 6 – Währungs‑ & Zahlungsabhängigkeit („currency“)

### 6.1 Definition
Die Dimension *currency* misst die strukturelle Abhängigkeit eines Landes von internationalen Leitwährungen, globalen Zahlungssystemen und externen Finanzinfrastrukturen.  
Hohe Werte bedeuten erhöhte Verwundbarkeit gegenüber geopolitischen, regulatorischen oder finanzmarktgetriebenen Schocks.

---

### 6.2 Relevanz
Diese Dimension ist zentral für:
- Handel und Zahlungsfähigkeit  
- Energie‑ und Rohstoffimporte  
- Finanzmarktstabilität  
- Sanktionsresilienz  
- Makroökonomische Schockrobustheit  

---

### 6.3 Einflussfaktoren (Indikatoren)

| Indikator | Wirkung auf Risiko |
|----------|--------------------|
| **USD_Dominanz** | ↑ Risiko durch Abhängigkeit von USD‑System |
| **Sanktions_Exposure** | ↑ Risiko durch potenzielle Zahlungsunterbrechungen |
| **FX_Schockempfindlichkeit** | ↑ Risiko durch Wechselkursvolatilität |
| **fremdwaehrungs_refinanzierung** | ↑ Risiko durch externe Finanzierung |
| **kapitalmarkt_abhaengigkeit** | ↑ Risiko durch globale Kapitalmarktzyklen |
| **Alternativnetz_Abdeckung** | ↓ Risiko durch alternative Zahlungssysteme |

---

### 6.4 Risiko‑Mechanismen

**Erhöhtes Risiko durch:**
- Ausschluss aus SWIFT oder anderen Zahlungssystemen  
- US‑Zins‑ und Wechselkurspolitik  
- Kapitalflucht und Refinanzierungsprobleme  
- Währungskrisen und Liquiditätsengpässe  

**Reduziertes Risiko durch:**
- RMB‑Clearing, CIPS, bilaterale Swap‑Lines  
- Diversifizierte Währungsreserven  
- Starke inländische Finanzinfrastruktur  

---

### 6.5 Normalisierung
Alle Indikatoren werden auf den Bereich [0,1] normalisiert:

- clamp01(x) für lineare Indikatoren  
- Verstärkung bei Sanktionsrisiko (`*2.0`)  
- FX‑Sensitivität skaliert (`/2.0`)  
- Alternativnetz wirkt risikomindernd (`-0.10 * alt_norm`)  

---

### 6.6 Aggregationsformel
currency = 0.30 * USD_Dominanz_norm + 0.25 * Sanktions_Exposure_norm + 0.20 * FX_Schockempfindlichkeit_norm + 0.15 * Fremdwährungsrefinanzierung_norm + 0.10 * Kapitalmarktabhängigkeit_norm – 0.10 * Alternativnetz_Abdeckung_norm

---

### 6.7 Interpretation

| Score | Bedeutung |
|-------|-----------|
| **0.00–0.30** | geringe Abhängigkeit, hohe Resilienz |
| **0.30–0.55** | moderat, potenzielle Verwundbarkeit |
| **0.55–0.75** | erhöht, strukturelle Risiken |
| **> 0.75** | kritisch, hohe geopolitische Anfälligkeit |

---

### 6.8 Typische Risikoprofile

**Hohes Risiko (Beispiele):**
- Länder mit USD‑Fixierung  
- Staaten mit hohem Sanktionsrisiko  
- Schwellenländer mit hoher FX‑Refinanzierung  

**Niedriges Risiko (Beispiele):**
- Länder mit diversifizierten Reserven  
- Staaten mit alternativen Zahlungssystemen  
- Volkswirtschaften mit starker Binnenfinanzierung  

---

### 6.9 Verbindung zu anderen Modulen

- **Makro**: Währungskrisen → Inflation, Kapitalflucht  
- **Geo**: Sanktionen → Zahlungsunterbrechungen  
- **Finanz**: FX‑Refinanzierung → Zins‑ und Liquiditätsrisiken  
- **Handel**: Zahlungsstörungen → Importkosten, Lieferketten  

---

### 6.10 Nutzung im Modell
- fließt in `compute_risk_scores()` ein  
- wird im Radar angezeigt  
- beeinflusst Szenarien (z. B. Dollar‑Schock, SWIFT‑Ausschluss)  
- wird im Early‑Warning‑System hervorgehoben  

## Modul 7 – Finanzielle Abhängigkeit („financial“)

### 7.1 Definition
Misst die strukturelle Verwundbarkeit gegenüber externen Kapitalquellen und Finanzmärkten.

---

### 7.2 Relevanz
- bestimmt Refinanzierungskosten  
- beeinflusst Kapitalflüsse  
- zentral für Finanzstabilität  

---

### 7.3 Indikatoren
- Auslandsverschuldung  
- FX‑Refinanzierung  
- Kapitalmarktintegration  
- Investorenstruktur  

---

### 7.4 Risiko‑Mechanismen
- Kapitalabflüsse  
- Zinsanstiege  
- Währungsschocks  

---

### 7.5 Normalisierung
linear  

---

### 7.6 Aggregationsformel
financial = compute_financial_dependency(p)

---

### 7.7 Interpretation
wie üblich  

---

### 7.8 Verbindung zu anderen Modulen
- Makro  
- Currency  

---

### 7.9 Nutzung im Modell
- Radar  
- Szenarien (Bankenkrise)  
### 7.11 Kritische Finanzparameter

| Parameter | Schwelle | Risiko |
|----------|----------|--------|
| **auslandsverschuldung > 0.6** | Refinanzierungsrisiko |
| **kapitalmarkt_abhaengigkeit > 0.5** | Zins‑ & Liquiditätsrisiken |
| **fremdwaehrungs_refinanzierung > 0.5** | Währungsrisiken |


## Modul 8 – Technologische Abhängigkeit („tech“)

### 8.1 Definition
Misst die Abhängigkeit eines Landes von kritischen Technologien und digitalen Infrastrukturen.

---

### 8.2 Relevanz
- zentral für Wettbewerbsfähigkeit  
- bestimmt digitale Souveränität  
- beeinflusst Innovationskraft  

---

### 8.3 Indikatoren
- Halbleiterabhängigkeit  
- Cloud‑/Software‑Abhängigkeit  
- IP‑Lizenzabhängigkeit  
- Schlüsseltechnologie‑Importe  

---

### 8.4 Risiko‑Mechanismen
- Lieferstopps → Produktionsausfälle  
- Lizenzentzug → Funktionsstörungen  
- digitale Abhängigkeit → Cyberrisiken  

---

### 8.5 Normalisierung
linear  

---

### 8.6 Aggregationsformel
tech = compute_tech_dependency(p)

---

### 8.7 Verbindung zu anderen Modulen
- Supply Chain  
- Geo  

---

### 8.8 Nutzung im Modell
- Radar  
- Szenarien (Cyberangriff)  
### 8.11 Kritische Tech‑Parameter

| Parameter | Schwelle | Risiko |
|----------|----------|--------|
| **halbleiter_abhaengigkeit > 0.6** | Produktionsrisiken |
| **software_cloud_abhaengigkeit > 0.7** | digitale Souveränität |
| **ip_lizenzen_abhaengigkeit > 0.5** | Funktionsrisiken |

## Modul 9 – Energieabhängigkeit („energie“)

### 9.1 Definition
Misst die strukturelle Abhängigkeit eines Landes von Energieimporten und Energieträgern.

---

### 9.2 Relevanz
- zentral für Industrieproduktion  
- bestimmt Versorgungssicherheit  
- hoher Einfluss auf Inflation  

---

### 9.3 Indikatoren
- Energieimportabhängigkeit  
- Diversifikation  
- Anteil kritischer Lieferländer  

---

### 9.4 Risiko‑Mechanismen
- Lieferstopps → Produktionsausfälle  
- Preisschocks → Inflation  
- geopolitische Risiken → Versorgungslücken  

---

### 9.5 Normalisierung
linear  

---

### 9.6 Aggregationsformel
energie = p.get("energie", 0.5)

---

### 9.7 Verbindung zu anderen Modulen
- Makro  
- Geo  
- Supply Chain  

---

### 9.8 Nutzung im Modell
- Radar  
- Szenarien (Energieembargo)  
### 9.11 Kritische Energieparameter

| Parameter | Schwelle | Risiko |
|----------|----------|--------|
| **energie > 0.6** | hohe Importabhängigkeit |
| **geringe Diversifikation** | Versorgungslücken |
| **kritische Lieferländer** | geopolitische Risiken |

## Modul 10 – Politische & sicherheitspolitische Abhängigkeit („political_security“)

### 10.1 Definition
Die politische und sicherheitspolitische Abhängigkeit beschreibt, wie stark ein Land auf andere Staaten, Bündnisse oder externe Akteure angewiesen ist, um seine außen‑, sicherheits‑ und verteidigungspolitischen Interessen durchzusetzen.  
Hohe Abhängigkeit reduziert die strategische Autonomie und erhöht die Verwundbarkeit gegenüber geopolitischen Spannungen.

---

### 10.2 Relevanz
Diese Dimension ist zentral für:
- nationale Sicherheit  
- außenpolitische Handlungsfreiheit  
- Stabilität von Handels‑ und Investitionsbeziehungen  
- Resilienz gegenüber geopolitischem Druck  

---

### 10.3 Einflussfaktoren (Indikatoren)

| Indikator | Wirkung auf Risiko |
|----------|--------------------|
| Sicherheitsgarantien durch fremde Staaten | ↑ Risiko (Abhängigkeit) |
| Stationierung ausländischer Truppen | ↑ Risiko (Einfluss externer Akteure) |
| Abhängigkeit von außenpolitischer Unterstützung | ↑ Risiko |
| Einfluss externer Akteure auf Innenpolitik | ↑ Risiko |
| Sanktions‑ und Embargo‑Verwundbarkeit | ↑ Risiko |
| Diplomatische Resilienz / Alternativen | ↓ Risiko |

---

### 10.4 Risiko‑Mechanismen

**Erhöhtes Risiko durch:**
- politische Konflikte mit Schutz‑ oder Partnerstaaten  
- Abhängigkeit von einem dominanten geopolitischen Akteur  
- außenpolitischen Druck (Sanktionen, Embargos, diplomatische Isolation)  
- Einflussnahme auf innenpolitische Entscheidungen  

**Reduziertes Risiko durch:**
- multilaterale Bündnisse  
- diversifizierte außenpolitische Beziehungen  
- starke diplomatische Netzwerke  
- eigene militärische Fähigkeiten  

---

### 10.5 Normalisierung
Alle Indikatoren werden auf den Bereich \([0,1]\) normalisiert:

- direkte Abhängigkeiten → linear (clamp01)  
- Einfluss externer Akteure → verstärkt  
- diplomatische Alternativen → risikomindernd  

---

### 10.6 Aggregationsformel (Vorschlag)
political_security = 0.35 * sicherheitsgarantien_norm + 0.25 * aussenpolitische_abhaengigkeit_norm + 0.20 * externer_einfluss_norm + 0.20 * sanktionsverwundbarkeit_norm – 0.20 * diplomatische_resilienz_norm

---

### 10.7 Interpretation

| Score | Bedeutung |
|-------|-----------|
| 0.00–0.30 | hohe Autonomie, geringe Abhängigkeit |
| 0.30–0.55 | moderat |
| 0.55–0.75 | erhöhte Verwundbarkeit |
| >0.75 | kritisch, strategische Abhängigkeit |

---

### 10.8 Typische Risikoprofile

**Hohes Risiko:**
- Staaten mit starken sicherheitspolitischen Abhängigkeiten  
- Länder unter geopolitischem Druck  
- Staaten mit hoher Sanktionsverwundbarkeit  

**Niedriges Risiko:**
- Länder mit breiten diplomatischen Netzwerken  
- Staaten mit eigener militärischer Kapazität  
- geopolitisch neutrale oder diversifizierte Länder  

---

### 10.9 Verbindung zu anderen Modulen
- **Geo:** politische Abhängigkeit verstärkt Sanktionsrisiken  
- **Handel:** politische Konflikte → Handelsunterbrechungen  
- **Currency:** Ausschluss aus Zahlungssystemen als politisches Druckmittel  
- **Energie:** Abhängigkeit von Lieferländern → politisches Risiko  

---

### 10.10 Nutzung im Modell
- Radar (als zusätzliche Dimension)  
- Szenarien (z. B. diplomatische Krise, Bündnisbruch)  
- Early‑Warning‑System  
- Benchmarking  
