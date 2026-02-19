# ui/app.py
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ---------------------------------------------------------
# KORREKTE IMPORTS (bereinigt)
# ---------------------------------------------------------

from core.engine.assets import (
    fetch_prices,
    compute_ki_score_from_prices,
    compute_radar_data,
)

from core.storyline_engine import (
    generate_storyline,
    generate_executive_summary,
    compute_risk_score,
    risk_color,
)

from core.plots.risk_plots import plot_scenario_radar_overlay
from core.plots.heatmap_plots import plot_risk_heatmap

from core.presets import load_presets
from core.scenario_engine import scenario_radar_overlay
from core.portfolio_sim.scenario_compare import run_scenario_comparison
from core.risk_ampel import compute_risk_score, risk_color
from core.cluster_engine import compute_clusters

from core.data.market_data import (
    load_asset_series,
    get_etf,
    get_gold,
    get_bond,
)

from core.portfolio.portfolio_engine import (
    max_drawdown,
    simulate_portfolio,
    portfolio_stats,
    portfolio_volatility,
    portfolio_performance,
    simulate_portfolio_with_rebalancing,
)

from core.plots.portfolio_plots import plot_portfolio
from core.portfolio.portfolio_storyline import generate_portfolio_storyline

from core.country.country_compare import compare_countries, compute_country_metrics
from core.country.country_storyline import generate_country_storyline

from core.reporting.pdf_report import create_pdf_report, draw_portfolio_page

from core.data.etf_db import list_etf_tickers
from core.data.asset_map import resolve_asset
from core.data.etf_db_loader import list_etf_tickers, list_etf_by_region
from core.data.ticker_validation import validate_or_fix_ticker
from core.data.country_map import get_country_choices, resolve_country
from core.ui_helpers import countries_with_etfs

from core.data.etf_db_loader import load_etf_db
from core.analysis.market_data import get_metrics, get_fundamentals
from core.analysis.stock_compare import stock_compare
from core.utils.country_utils import get_all_countries

from core.visualization.radar import plot_radar
from core.analysis.portfolio_metrics import aggregate_portfolio
from core.visualization.lexicon import get_lexicon

from core.data.stock_list import load_stock_list
from core.visualization.radar_plotly import plot_radar_plotly
from core.analysis.stock_clusterin import cluster_stocks

from core.analysis.normalize import normalize_metrics
from core.data.ticker_country_map import map_ticker_to_country
from core.data.country_macro import get_country_macro

from core.backend.radar_builder import (
    build_country_radar,
    build_etf_radar,
    build_portfolio_radar,
    build_asset_radar,
    get_bitcoin_metrics,
)

from core.backend.ki_scanner import scan_assets
from core.backend.etf_scanner import scan_etf_list
from core.backend.stock_scanner import scan_stocks
from core.backend.portfolio_optimizer import (
    optimize_markowitz,
    optimize_risk_parity,
    optimize_ki_score,
)

from core.backend.heatmap import plot_correlation_heatmap

from core.backend.symbol_tools import (
    suggest_symbols,
    validate_symbol,
    detect_symbol_type,
    is_isin,
)

from core.backend.portfolio_manager import (
    list_portfolios,
    save_portfolio,
    delete_portfolio,
    get_portfolio,
)

from core.backend.portfolio_radar import portfolio_radar
from core.backend.portfolio_backtest import backtest_portfolio
from core.backend.portfolio_compare import compare_two_portfolios

from core.data.logging import log_buffer

from core.backend.ki_score import compute_ki_score, explain_ki_score
from core.data.assets import fetch_price_history
from core.backend.plots import plot_efficient_frontier
from core.backend.data_utils import clear_cache, load_isin_db

from ui.logic_screener import ui_etf_screener, ui_stock_screener
from ui.logic_bonds import ui_bond_analysis
from ui.logic_crypto import ui_crypto_analysis
from ui.logic_risk import ui_risk_dashboard
from ui.logic_portfolio import ui_portfolio_optimizer, ui_portfolio_studio
from ui.logic_scenario import ui_scenario_comparison

# ---------------------------------------------------------
# WICHTIG: Nur diese Funktionen aus db_assets importieren!
# ---------------------------------------------------------

from core.data.db_assets import (
    ETF_DB,
    STOCK_DB,
    find_asset,
    get_asset_full_profile,
)
print("Europa:", list_etf_by_region("Europa"))
print("USA:", list_etf_by_region("USA"))
print("Global:", list_etf_by_region("Global"))


# ---------------------------------------------------------
# NEUE, MODERNE UI-FUNKTIONEN (ersetzen alte Wrapper)
# ---------------------------------------------------------

def render_type_html(typ_text: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;padding:2px 6px;border-radius:4px;"
        f"background:{color};color:white;font-size:11px;font-weight:600;'>{typ_text}</span>"
    )


def process_asset_input(ticker: str):
    ticker = (ticker or "").strip()
    if not ticker:
        return "Unbekannt", "#6b7280", {}, None, {}

    profile = get_asset_full_profile(ticker)
    asset = profile.get("asset", {}) or {}
    ki_score = profile.get("ki_score")
    radar = profile.get("radar", {})
    typ = profile.get("typ", "Unbekannt")

    color = "#6b7280"
    if typ == "ETF":
        color = "#2563eb"
    elif typ == "Stock":
        color = "#16a34a"
    elif typ == "Krypto":
        color = "#f97316"

    return typ, color, asset, ki_score, radar


def ui_asset_wrapper(ticker: str):
    typ_text, color, asset, ki_score, radar = process_asset_input(ticker)
    html = render_type_html(typ_text, color)
    return html, asset, ki_score, radar


def ui_convert_isin(text: str):
    tickers = [t.strip() for t in (text or "").split(",") if t.strip()]
    results = []

    for t in tickers:
        asset, typ = find_asset(t)
        isin = asset.get("ISIN")
        if isin:
            results.append([t, isin])
        else:
            results.append([t, f"Keine ISIN für {t} gefunden."])

    return pd.DataFrame(results, columns=["Ticker", "ISIN"])


def ui_ki_scan(text: str):
    tickers = [t.strip() for t in (text or "").split(",") if t.strip()]
    results = []
    explanations = []

    for t in tickers:
        asset, typ = find_asset(t)
        yahoo = asset.get("Yahoo", t)

        prices = fetch_prices(yahoo)
        if prices is None or len(prices) < 120:
            results.append([t, None])
            explanations.append(f"Keine ausreichenden Daten für {t}.")
            continue

        score = compute_ki_score_from_prices(prices)
        results.append([t, score])
        explanations.append(f"{t}: KI‑Score = {round(score, 2)}")

    df = pd.DataFrame(results, columns=["Ticker", "KI‑Score"])
    return df, "\n\n---\n\n".join(explanations)

# ---------------------------------------------------------
# ALLE build_* FUNKTIONEN (unverändert)
# ---------------------------------------------------------

# (Hier fügst du einfach deine build_home(), build_etf_screener(),
#  build_stock_screener(), build_bond_analysis(), build_crypto_analysis(),
#  build_risk_dashboard(), build_portfolio_optimizer(), build_portfolio_studio(),
#  build_scenario_comparison(), build_settings_tab() ein — exakt wie du sie hast.)


def build_home():
    gr.Markdown("""
    # 📘 Willkommen im MakroSim Dashboard

    Dieser Bereich erklärt die wichtigsten Begriffe, Radar‑Faktoren, KI‑Scores und Asset‑Typen.

    ## 📊 Was bedeuten die Radare?
    Ein Radar zeigt die technische Qualität eines Assets anhand von:
    - Momentum
    - Volatilität
    - Drawdown
    - Trendstabilität
    - Sharpe‑Ratio
    - Diversifikation

    Große Fläche = stark
    Kleine Fläche = schwach
    Gleichmäßig = stabil
    Verzerrt = Risiko

    ---
    ## 📘 Was ist ein Fonds?
            Ein Fonds ist ein großer Geldtopf, in den viele Anleger einzahlen.
            Ein Manager investiert dieses Geld in viele Wertpapiere (Aktien, Anleihen, Immobilien).
            Ein ETF ist ein **börsengehandelter Fonds**, der einen Index nachbildet.

    # 📘 Glossar

    ### ETF
    Ein ETF ist ein börsengehandelter Fonds, der einen Index nachbildet.

    ### Fonds
    Ein Fonds ist ein großer Geldtopf, der in viele Wertpapiere investiert wird.

    ### Anleihe
    Eine Anleihe ist ein Kredit an Staat oder Unternehmen.

    ### Sharpe‑Ratio
    Verhältnis von Rendite zu Risiko.

    ### Volatilität
    Schwankungsintensität eines Wertpapiers.

    ### TER
    Gesamtkostenquote eines ETFs.

    ### Diversifikation
    Risikoverteilung über viele Anlagen.

    ### 🪙 Bitcoin
    Bitcoin ist die erste und größte Kryptowährung.
    Sie funktioniert ohne zentrale Instanz und basiert auf einem Netzwerk von Computern,
    die gemeinsam die Blockchain betreiben.

    **Begriffe im Zusammenhang mit Bitcoin:**

    - **Blockchain** – öffentliches Register aller Transaktionen
    - **Halving** – Ereignis, bei dem die Blockbelohnung halbiert wird (alle ~4 Jahre)
    - **Mining** – Prozess, bei dem neue Bitcoins erzeugt werden
    - **Wallet** – digitale Geldbörse für Bitcoin
    - **Private Key** – kryptografischer Schlüssel, der den Besitz beweist
    - **On‑Chain / Off‑Chain** – Transaktionen auf oder außerhalb der Blockchain
    ---

    ### 🔗 Blockchain

    Eine Blockchain ist eine **dezentrale Datenstruktur**, die Transaktionen in einer
    verketteten Reihe von Blöcken speichert.
    Sie ist:

    - unveränderbar
    - transparent
    - kryptografisch gesichert
    - nicht von einer zentralen Instanz kontrolliert

    Sie bildet die Grundlage für Bitcoin und viele andere digitale Assets.
    """)

    gr.Markdown("""
    ### 🔗 Was ist die Blockchain?

    Die Blockchain ist ein **dezentrales, unveränderbares Register**, das alle Bitcoin‑Transaktionen speichert.
    Statt einer zentralen Datenbank wird sie von tausenden Computern weltweit gemeinsam betrieben.
    Jeder neue Block baut auf dem vorherigen auf – dadurch entsteht eine **fälschungssichere Kette**.

    ## 🔗 Blockchain – Einsteiger‑Erklärung

    Die Blockchain ist das technische Fundament von Bitcoin.
    Man kann sie sich wie ein **digitales Kassenbuch** vorstellen, das:

    - **öffentlich einsehbar** ist
    - **nicht manipuliert** werden kann
    - **von tausenden Computern gleichzeitig geführt** wird
    - **jede Transaktion dauerhaft speichert**

    Jeder Block enthält:
    - eine Liste von Transaktionen
    - einen Zeitstempel
    - einen kryptografischen Fingerabdruck (Hash)
    - den Hash des vorherigen Blocks

    Durch diese Struktur entsteht eine **Kette von Blöcken**, die praktisch nicht gefälscht werden kann.
    """)

    gr.Markdown("""
    ## 🧩 Wie funktioniert eine Blockchain?

    Stell dir die Blockchain wie eine **Kette aus nummerierten Blöcken** vor:

    1. **Transaktionen sammeln**
        Neue Bitcoin‑Transaktionen werden gesammelt und zu einem Block zusammengefasst.

    2. **Block erzeugen (Mining)**
        Miner lösen ein kryptografisches Puzzle.
        Wer es zuerst löst, darf den neuen Block an die Kette anhängen.

    3. **Block enthält Hash + Vorgänger‑Hash**
        Jeder Block speichert:
        - seinen eigenen Hash
        - den Hash des vorherigen Blocks
        Dadurch entsteht eine **fälschungssichere Kette**.

    4. **Verteilung im Netzwerk**
        Der neue Block wird an tausende Computer verteilt.
        Alle aktualisieren ihre Kopie der Blockchain.

    5. **Unveränderbarkeit**
        Wenn jemand einen alten Block ändern würde,
        müssten **alle folgenden Blöcke neu berechnet** werden – praktisch unmöglich.

    So bleibt die Blockchain **transparent, sicher und dezentral**.

    ## 📊 Blockchain vs. klassische Datenbank

    | Merkmal | Blockchain | Klassische Datenbank |
    |--------|------------|----------------------|
    | **Kontrolle** | dezentral (viele Teilnehmer) | zentral (eine Organisation) |
    | **Manipulation** | praktisch unmöglich | möglich durch Admins |
    | **Transparenz** | öffentlich einsehbar | meist privat |
    | **Datenstruktur** | verkettete Blöcke | Tabellen, Zeilen, Spalten |
    | **Sicherheit** | kryptografisch gesichert | Zugriffskontrolle |
    | **Geschwindigkeit** | langsamer (Konsens nötig) | sehr schnell |
    | **Anwendungsfall** | Bitcoin, Smart Contracts | Firmen‑Datenbanken, Web‑Apps |
    | **Verfügbarkeit** | global verteilt | abhängig vom Server |


    ## 🪙 Bitcoin vs. 📈 ETF – Was ist der Unterschied?

    ### **Bitcoin**
    - digitale Währung
    - keine Firma, kein Index, kein Fonds
    - extrem volatil
    - begrenzte Menge (21 Mio.)
    - keine Dividenden
    - keine TER oder Verwaltungskosten
    - basiert auf Blockchain‑Technologie

    ### **ETF**
    - Fonds, der einen Index abbildet
    - enthält viele Aktien oder Anleihen
    - geringe Kosten (TER)
    - hohe Diversifikation
    - reguliert und überwacht
    - stabile, langfristige Struktur

    ### **Warum beide im Asset‑Radar?**

    Weil das Radar **Risiko und Performance** vergleicht — unabhängig vom Asset‑Typ.

    Das Radar beantwortet:
    - Wie volatil ist Bitcoin im Vergleich zu ETFs?
    - Wie ist die Sharpe‑Ratio im Vergleich zu Aktien?
    - Wie korreliert Bitcoin mit SPY oder Gold?
    - Welche Rolle spielt Bitcoin im Portfolio‑Risiko?

    So entsteht ein **einheitliches Analyse‑Framework** für alle Vermögenswerte.


    # 🎯 Wie lese ich ein Radar?
    - Große Fläche = stark
    - Kleine Fläche = schwach
    - Gleichmäßige Form = stabil
    - Verzerrte Form = Risiko oder Ungleichgewicht
    """)


def build_etf_screener():
    gr.Markdown("""
    # 📊  ETF‑Screener (justETF)
    Gib eine Liste von ISINs ein oder lade eine Region.
    Der Screener zeigt TER, Fondsgröße, Replikation und Tracking‑Differenz.
    """)

    with gr.Row():
        region = gr.Dropdown(["Global", "USA", "Europa", "Emerging Markets"], label="Region")
        category = gr.Dropdown(["Aktien", "Anleihen", "Sektoren", "Themen"], label="Kategorie")
        btn = gr.Button("Screener starten")

    table = gr.Dataframe(label="ETF‑Ergebnisse")

    btn.click(
        ui_etf_screener,
        inputs=[region, category],
        outputs=[table]
    )

def build_stock_screener():
    gr.Markdown("""
    # 📈  Aktien‑Screener (Fundamentaldaten)
    Der Screener lädt KGV, KUV, PEG, Verschuldung, Cashflow und Wachstum.
    """)

    with gr.Row():
        sector = gr.Dropdown(["Alle", "Tech", "Finanzen", "Industrie", "Gesundheit"], label="Sektor")
        country = gr.Dropdown(["USA", "Deutschland", "Europa", "Global"], label="Land")
        btn = gr.Button("Screener starten")

    table = gr.Dataframe(label="Aktien‑Ergebnisse")

    btn.click(
        ui_stock_screener,
        inputs=[sector, country],
        outputs=[table]
    )


def build_bond_analysis():
    gr.Markdown("## 🧾 Anleihen‑Analyse")

    gr.Markdown("""
    Dieser Bereich wird später erweitert:
    - Rendite (Yield)
    - Duration
    - Spread‑Analyse
    - Risiko‑Radar
    """)

    with gr.Row():
        bond_input = gr.Textbox(label="Anleihe‑Ticker", placeholder="z. B. IEF, TLT, BND")
        btn = gr.Button("Analysieren")

    table = gr.Dataframe(label="Anleihe‑Daten")
    radar = gr.Plot(label="Radar‑Analyse")

    btn.click(
        ui_bond_analysis,
        inputs=[bond_input],
        outputs=[table, radar]
    )


def build_crypto_analysis():
    gr.Markdown("## 🪙 Krypto‑Analyse")

    with gr.Row():
        crypto_input = gr.Textbox(label="Krypto‑Ticker", placeholder="BTC-USD, ETH-USD")
        btn = gr.Button("Analysieren")

    table = gr.Dataframe(label="Krypto‑Daten")
    radar = gr.Plot(label="Radar‑Analyse")

    btn.click(
        ui_crypto_analysis,
        inputs=[crypto_input],
        outputs=[table, radar]
    )


def build_risk_dashboard():
    gr.Markdown("## ⚠️ Risiko‑Dashboard")

    with gr.Row():
        tickers = gr.Textbox(label="Ticker‑Liste", placeholder="AAPL, SPY, BTC-USD")
        btn = gr.Button("Risiko analysieren")

    vol_table = gr.Dataframe(label="Volatilität")
    dd_table = gr.Dataframe(label="Drawdowns")
    corr_plot = gr.Plot(label="Korrelation‑Heatmap")

    btn.click(
        ui_risk_dashboard,
        inputs=[tickers],
        outputs=[vol_table, dd_table, corr_plot]
    )


def build_portfolio_optimizer():
    gr.Markdown("## 🎯 Portfolio‑Optimierer")

    with gr.Row():
        tickers = gr.Textbox(label="Assets", placeholder="AAPL, SPY, GLD, BTC-USD")
        btn = gr.Button("Optimieren")

    weights = gr.Dataframe(label="Optimale Gewichtung")
    frontier = gr.Plot(label="Effizienzkurve")

    btn.click(
        ui_portfolio_optimizer,
        inputs=[tickers],
        outputs=[weights, frontier]
    )

def build_portfolio_studio():
    gr.Markdown("## 📂 Portfolio‑Studio")

    with gr.Row():
        tickers = gr.Textbox(label="Portfolio‑Assets", placeholder="AAPL, SPY, BTC-USD")
        btn = gr.Button("Backtest starten")

    perf_plot = gr.Plot(label="Performance")
    stats_table = gr.Dataframe(label="Kennzahlen")

    btn.click(
        ui_portfolio_studio,
        inputs=[tickers],
        outputs=[perf_plot, stats_table]
    )

def build_scenario_comparison():
    gr.Markdown("## 📈 Szenario‑Vergleich")
    with gr.Row():
        tickers = gr.Textbox(label="Assets", placeholder="AAPL, SPY, BTC-USD")
        scenario = gr.Dropdown(["Rezession", "Inflation", "Zinsanstieg", "Ölkrise"], label="Szenario")
        btn = gr.Button("Simulieren")

    result = gr.Dataframe(label="Szenario‑Ergebnisse")

    btn.click(
        ui_scenario_comparison,
        inputs=[tickers, scenario],
        outputs=[result]
    )


def ui_show_isin_db():
    db = load_isin_db()
    rows = [(k, v) for k, v in db.items()]
    return pd.DataFrame(rows, columns=["Ticker", "ISIN"])


def ui_clear_cache():
    try:
        clear_cache()
        return "Cache erfolgreich gelöscht."
    except Exception as e:
        return f"Fehler: {e}"

def build_settings_tab():
    gr.Markdown("## ⚙️ Einstellungen / Daten / ISIN‑DB")

    with gr.Row():
        btn_load = gr.Button("ISIN‑Datenbank anzeigen")
        btn_clear = gr.Button("Cache leeren")

    isin_table = gr.Dataframe(label="ISIN‑Datenbank")

    btn_load.click(
        ui_show_isin_db,
        inputs=[],
        outputs=[isin_table]
    )

    btn_clear.click(
        ui_clear_cache,
        inputs=[],
        outputs=[]
    )

def build_etf_lexikon():
    gr.Markdown("""
    # 📘 ETF‑Lexikon

    ## TER (Total Expense Ratio)
    Gesamtkostenquote eines ETFs pro Jahr.

    ## Replikation
    Wie der ETF den Index nachbildet:
    - physisch
    - optimiert
    - synthetisch

    ## Tracking‑Differenz
    Abweichung zwischen ETF‑Performance und Index‑Performance.

    ## Fondsvolumen
    Größe des ETF – wichtig für Liquidität und Stabilität.

    ## Diversifikation
    Verteilung des Risikos über viele Positionen.

    ## Volatilität
    Schwankungsintensität eines ETFs.

    ## Sharpe‑Ratio
    Rendite im Verhältnis zum Risiko.

    ## ISIN
    Internationale Wertpapierkennnummer.
    """)

def build_etf_goal_setting():
    gr.Markdown("""
    # 🎯 Ziel‑Setzung für ETF‑Auswahl

    ## 1. Anlagehorizont
    - Kurzfristig (0–2 Jahre)
    - Mittelfristig (2–7 Jahre)
    - Langfristig (7+ Jahre)

    ## 2. Risikoprofil
    - Defensiv
    - Ausgewogen
    - Wachstum
    - Spekulativ

    ## 3. Ziele
    - Vermögensaufbau
    - Kapitalerhalt
    - Altersvorsorge
    - Zusatzeinkommen

    ## 4. ETF‑Empfehlungslogik
    - Defensiv → Anleihen‑ETFs, Minimum‑Volatility‑ETFs
    - Ausgewogen → Welt‑ETFs, Qualitätsaktien‑ETFs
    - Wachstum → Tech‑ETFs, Emerging Markets
    - Spekulativ → Themen‑ETFs, Small Caps

    ## 5. Verbindung zum Dashboard
    - ETF‑Screener zeigt passende ETFs
    - Portfolio‑Optimierer nutzt dein Zielprofil
    - Risiko‑Dashboard zeigt Risiken passend zu deinem Profil
    """)

def build_stock_lexikon():
    gr.Markdown("""
    # 📘 Aktien‑Lexikon

    ## KGV (Kurs‑Gewinn‑Verhältnis)
    Wie viele Jahre der Gewinn benötigt, um den Aktienpreis zu decken.
    Niedrig = günstig, Hoch = teuer.

    ## KUV (Kurs‑Umsatz‑Verhältnis)
    Verhältnis von Umsatz zu Marktkapitalisierung.
    Gut für Wachstumsunternehmen.

    ## PEG‑Ratio
    KGV im Verhältnis zum Gewinnwachstum.
    < 1 gilt oft als attraktiv.

    ## Verschuldung (Debt/Equity)
    Verhältnis von Schulden zu Eigenkapital.
    Niedrig = stabiler.

    ## Cashflow
    Wie viel Geld das Unternehmen tatsächlich erwirtschaftet.
    Wichtiger als Gewinn.

    ## Wachstum
    Umsatz‑ und Gewinnwachstum über mehrere Jahre.

    ## Dividendenrendite
    Verhältnis von Dividende zu Aktienkurs.

    ## Beta
    Maß für die Schwankung im Vergleich zum Gesamtmarkt.
    > 1 = volatil, < 1 = defensiv.
    """)

def build_stock_goal_setting():
    gr.Markdown("""
    # 🎯 Ziel‑Setzung für Aktien‑Auswahl

    ## 1. Anlagestrategien

    ### 🔹 Value
    - günstige Bewertung (niedriges KGV/KUV)
    - stabile Cashflows
    - solide Dividenden

    ### 🔹 Growth
    - hohes Umsatz‑ und Gewinnwachstum
    - hohe KUV/KGV normal
    - Fokus auf Zukunftsmärkte

    ### 🔹 Quality
    - starke Bilanz
    - hohe Profitabilität
    - stabile Margen

    ### 🔹 Dividende
    - hohe Dividendenrendite
    - stabile Ausschüttungen
    - defensive Branchen

    ## 2. Risikoprofil

    - Defensiv → Quality, Dividende
    - Ausgewogen → Mix aus Value & Quality
    - Wachstum → Growth‑Aktien
    - Spekulativ → Small Caps, Tech, Emerging Markets

    ## 3. Verbindung zum Dashboard

    - Aktien‑Screener zeigt passende Kennzahlen
    - Risiko‑Dashboard zeigt Volatilität & Drawdown
    - Portfolio‑Optimierer nutzt dein Zielprofil
    """)

def build_risk_lexikon():
    gr.Markdown("""
    # 📘 Risiko‑Lexikon

    Dieses Lexikon erklärt alle wichtigen Risikobegriffe, die im Dashboard verwendet werden.

    ## 📉 Volatilität
    Maß für die Schwankungsintensität eines Assets.
    Hohe Volatilität = starke Ausschläge, niedrige Volatilität = stabile Kurse.

    ## 📉 Standardabweichung
    Mathematische Grundlage der Volatilität.
    Misst, wie stark tägliche Renditen vom Durchschnitt abweichen.

    ## 📉 Drawdown
    Verlust vom letzten Hochpunkt bis zum Tiefpunkt.
    Beispiel: 100 → 70 = −30 % Drawdown.

    ## 📉 Maximum Drawdown (MDD)
    Größter historischer Drawdown über den gesamten Zeitraum.
    Zeigt, wie schlimm ein Crash für ein Asset war.

    ## 📊 Beta
    Wie stark ein Asset im Vergleich zum Gesamtmarkt schwankt.
    - > 1 = stärker als der Markt
    - < 1 = defensiver
    - = 1 = bewegt sich wie der Markt

    ## 🔗 Korrelation
    Wie stark zwei Assets gemeinsam steigen oder fallen.
    - +1 = identisch
    - 0 = unabhängig
    - −1 = gegensätzlich

    ## 📉 Value‑at‑Risk (VaR)
    Maximaler Verlust mit einer bestimmten Wahrscheinlichkeit.
    Beispiel: „Mit 95 % Wahrscheinlichkeit verlierst du nicht mehr als 5 % pro Tag.“

    ## 📈 Sharpe‑Ratio
    Rendite im Verhältnis zum Risiko.
    Höher = besser.

    ## 📈 Sortino‑Ratio
    Wie Sharpe, aber bestraft nur negative Schwankungen.

    ## ⚠️ Tail‑Risk
    Risiko extremer Verluste („schwarze Schwäne“).
    Besonders relevant bei Krypto, Small Caps, Hebelprodukten.

    ## 🧮 Risikobeitrag (Risk Contribution)
    Wie viel jedes Asset zum Gesamtrisiko des Portfolios beiträgt.

    ## ⚖️ Risikoparität (Risk Parity)
    Strategie, bei der jedes Asset denselben Risikobeitrag liefert.

    ## 🎯 Volatility Targeting
    Portfolio passt Positionsgrößen an, um eine feste Ziel‑Volatilität zu halten.

    ## 🧪 Stress‑Test
    Simulation extremer Marktbedingungen (z. B. 2008, Corona‑Crash).
    """)

def build_risk_profile():
    gr.Markdown("""
    # 🎯 Risikoprofil – Welcher Anlegertyp bist du?

    Das Risikoprofil hilft dir, dein Portfolio und deine ETF‑/Aktienauswahl
    an deine persönliche Risikobereitschaft anzupassen.

    ---

    ## 🟩 1. Defensiv (Sicherheitsorientiert)

    **Ziel:** Kapitalerhalt, geringe Schwankungen
    **Typische Assets:**
    - Staatsanleihen
    - Geldmarkt
    - Gold
    - Minimum‑Volatility‑ETFs
    - Dividendenaktien

    **Risiko:** niedrig
    **Erwartete Rendite:** niedrig bis moderat
    **Drawdowns:** gering

    ---

    ## 🟦 2. Ausgewogen (Balanced)

    **Ziel:** Mischung aus Wachstum und Stabilität
    **Typische Assets:**
    - Welt‑ETFs (MSCI World, ACWI)
    - Qualitätsaktien
    - Unternehmensanleihen
    - Rohstoffe

    **Risiko:** moderat
    **Erwartete Rendite:** moderat
    **Drawdowns:** mittel

    ---

    ## 🟧 3. Wachstum (Growth)

    **Ziel:** langfristiger Vermögensaufbau
    **Typische Assets:**
    - Tech‑Aktien
    - Emerging Markets
    - Themen‑ETFs
    - Small Caps

    **Risiko:** hoch
    **Erwartete Rendite:** hoch
    **Drawdowns:** groß

    ---

    ## 🟥 4. Spekulativ (Aggressiv)

    **Ziel:** maximale Rendite, akzeptiert hohe Verluste
    **Typische Assets:**
    - Kryptowährungen
    - Hebelprodukte
    - Biotech
    - Penny Stocks
    - Frontier Markets

    **Risiko:** sehr hoch
    **Erwartete Rendite:** sehr hoch
    **Drawdowns:** extrem

    ---

    ## 🔗 Verbindung zum Dashboard

    - **Portfolio‑Optimierer** nutzt dein Risikoprofil für Gewichtungen
    - **ETF‑Screener** zeigt passende Kategorien
    - **Aktien‑Screener** filtert nach Value/Growth/Quality
    - **Risiko‑Dashboard** zeigt Warnungen bei zu hohem Risiko
    - **Portfolio‑Studio** bewertet, ob dein Portfolio zu deinem Profil passt
    - **Szenario‑Vergleich** zeigt, wie dein Profil in Krisen reagiert
    """)

def build_portfolio_lexikon():
    gr.Markdown("""
    # 📘 Portfolio‑Lexikon

    Dieses Lexikon erklärt alle wichtigen Begriffe, die bei der Portfolio‑Analyse,
    Optimierung und Bewertung verwendet werden.

    ---

    ## 📈 Rendite
    Durchschnittliche jährliche Wertentwicklung eines Portfolios oder Assets.

    ## 📉 Volatilität
    Schwankungsintensität der Renditen.
    Hohe Volatilität = hohes Risiko.

    ## 📉 Maximum Drawdown (MDD)
    Größter historischer Verlust vom letzten Hochpunkt.
    Zeigt, wie schlimm ein Crash für das Portfolio war.

    ## 📊 Sharpe‑Ratio
    Rendite im Verhältnis zum Risiko.
    Höher = besser.

    ## 📊 Sortino‑Ratio
    Wie Sharpe, aber bestraft nur negative Schwankungen.

    ## 🔗 Korrelation
    Wie stark zwei Assets gemeinsam steigen oder fallen.
    Wichtig für Diversifikation.

    ## ⚖️ Risikobeitrag (Risk Contribution)
    Wie viel jedes Asset zum Gesamtrisiko beiträgt.

    ## ⚖️ Risikoparität (Risk Parity)
    Strategie, bei der jedes Asset denselben Risikobeitrag liefert.

    ## 🎯 Markowitz‑Optimierung
    Klassische Portfolio‑Optimierung:
    Maximiert Rendite bei minimalem Risiko.

    ## 🎯 Effizienzkurve (Efficient Frontier)
    Zeigt alle optimalen Portfolios für verschiedene Risikoniveaus.

    ## 🧮 Rebalancing
    Regelmäßiges Anpassen der Gewichte, um das Zielportfolio zu halten.

    ## 🧪 Backtest
    Historische Simulation eines Portfolios, um Performance und Risiko zu bewerten.

    ## 🧩 Diversifikation
    Verteilung des Risikos über verschiedene Anlageklassen.

    ## 🪙 Asset Allocation
    Aufteilung des Portfolios auf verschiedene Asset‑Typen (Aktien, ETFs, Anleihen, Krypto).
    """)

def build_portfolio_goal_setting():
    gr.Markdown("""
    # 🎯 Ziel‑Setzung für Portfolios

    Die Ziel‑Setzung hilft dir, dein Portfolio an deine persönlichen Ziele
    und deine Risikobereitschaft anzupassen.

    ---

    ## 🟩 1. Defensiv (Sicherheitsorientiert)

    **Ziel:** Kapitalerhalt, geringe Schwankungen
    **Typische Portfolio‑Struktur:**
    - 60–80 % Anleihen
    - 10–20 % Aktien
    - 10–20 % Gold / Rohstoffe
    - kaum Krypto

    **Geeignet für:**
    - kurze Anlagehorizonte
    - risikoaverse Anleger

    ---

    ## 🟦 2. Ausgewogen (Balanced)

    **Ziel:** Stabilität + Wachstum
    **Typische Portfolio‑Struktur:**
    - 40–60 % Aktien
    - 20–40 % Anleihen
    - 10–20 % Rohstoffe / Gold
    - 0–5 % Krypto

    **Geeignet für:**
    - langfristige Anleger
    - moderates Risiko

    ---

    ## 🟧 3. Wachstum (Growth)

    **Ziel:** langfristiger Vermögensaufbau
    **Typische Portfolio‑Struktur:**
    - 60–80 % Aktien
    - 10–20 % Emerging Markets
    - 0–10 % Krypto
    - 10–20 % Anleihen / Gold

    **Geeignet für:**
    - hohe Risikobereitschaft
    - langer Anlagehorizont

    ---

    ## 🟥 4. Spekulativ (Aggressiv)

    **Ziel:** maximale Rendite
    **Typische Portfolio‑Struktur:**
    - 70–90 % Aktien
    - 10–20 % Krypto
    - 0–10 % Rohstoffe
    - kaum Anleihen

    **Geeignet für:**
    - sehr risikofreudige Anleger
    - spekulative Strategien

    ---

    ## 🔗 Verbindung zum Dashboard

    - **Portfolio‑Optimierer** nutzt dein Zielprofil für die Gewichtung
    - **Portfolio‑Studio** bewertet, ob dein Portfolio zu deinem Profil passt
    - **ETF‑Screener** zeigt passende ETFs
    - **Risiko‑Dashboard** zeigt Warnungen bei zu hohem Risiko
    - **Szenario‑Vergleich** zeigt, wie dein Profil in Krisen reagiert
    """)

def build_portfolio_stats():
    gr.Markdown("""
    # 📊 Portfolio‑Kennzahlen

    Dieser Bereich zeigt alle wichtigen quantitativen Kennzahlen deines Portfolios.

    ## Enthaltene Kennzahlen:

    ### 📈 Rendite
    Durchschnittliche jährliche Wertentwicklung des Portfolios.

    ### 📉 Volatilität
    Schwankungsintensität der täglichen oder monatlichen Renditen.

    ### 📉 Maximum Drawdown (MDD)
    Größter historischer Verlust vom letzten Hochpunkt.

    ### 📊 Sharpe‑Ratio
    Rendite im Verhältnis zum Risiko.
    Höher = besser.

    ### 📊 Sortino‑Ratio
    Wie Sharpe, aber bestraft nur negative Schwankungen.

    ### 🔗 Korrelationen
    Wie stark die einzelnen Assets miteinander zusammenhängen.

    ### ⚖️ Risikobeiträge
    Wie viel jedes Asset zum Gesamtrisiko beiträgt.

    ### 🧮 Effizienzkurve
    Position des Portfolios im Vergleich zur Efficient Frontier.

    ## Hinweis
    Die Kennzahlen werden automatisch berechnet, sobald du im Portfolio‑Studio
    ein Portfolio geladen oder erstellt hast.
    """)

def build_portfolio_story():
    gr.Markdown("""
    # 🧠 Portfolio‑Interpretation (Storyline)

    Dieser Bereich liefert eine qualitative Analyse deines Portfolios:
    Stärken, Schwächen, Chancen, Risiken und strategische Einordnung.

    ## Enthaltene Elemente:

    ### ⭐ Stärken
    - Welche Bereiche gut performen
    - Welche Assets stabilisieren das Portfolio
    - Welche Diversifikationseffekte wirken

    ### ⚠️ Schwächen
    - Klumpenrisiken
    - Übergewichtungen
    - hohe Volatilität oder Drawdowns

    ### 📈 Chancen
    - Wachstumstreiber
    - Trend‑ oder Momentum‑Signale
    - Makro‑ oder Sektor‑Vorteile

    ### 📉 Risiken
    - Marktrisiken
    - Zinsrisiken
    - Währungsrisiken
    - Tail‑Risks

    ### 🎯 Abgleich mit deinem Risikoprofil
    - Passt das Portfolio zu deinem Profil?
    - Ist es zu riskant oder zu defensiv?
    - Welche Anpassungen wären sinnvoll?

    ### 🧭 Handlungsempfehlungen
    - mögliche Rebalancing‑Strategien
    - Optimierungsideen
    - Diversifikationsvorschläge

    ## Hinweis
    Die Storyline wird automatisch generiert, sobald du im Portfolio‑Studio
    ein Portfolio analysierst.
    """)

def build_scenario_radar():
    gr.Markdown("""
    # 📊 Szenario‑Radar

    Das Szenario‑Radar zeigt die Unterschiede zwischen zwei Markt‑ oder Portfolio‑Szenarien
    in einer klaren, visuellen Form. Es hilft dir zu verstehen, wie sich verschiedene
    Faktoren unter unterschiedlichen Bedingungen verändern.

    ## Was zeigt das Radar?

    ### 🔹 Risiko
    Wie stark das Portfolio im jeweiligen Szenario schwankt.

    ### 🔹 Rendite
    Erwartete oder simulierte Performance.

    ### 🔹 Drawdown
    Wie tief das Portfolio im Stressfall fallen könnte.

    ### 🔹 Momentum
    Trendstärke im jeweiligen Szenario.

    ### 🔹 Volatilität
    Schwankungsintensität der Renditen.

    ### 🔹 Diversifikation
    Wie gut das Portfolio im Szenario diversifiziert ist.

    ## Wie wird das Radar berechnet?

    Das Radar basiert auf:
    - historischen Daten
    - simulierten Szenarien
    - KI‑basierten Risikomodellen
    - Portfolio‑Kennzahlen

    ## Hinweis
    Das Radar wird automatisch generiert, sobald du im Szenario‑Vergleich
    zwei Szenarien auswählst und vergleichst.
    """)

def build_scenario_story():
    gr.Markdown("""
    # 🧠 Szenario‑Interpretation (Storyline)

    Dieses Modul liefert eine qualitative Analyse der beiden Szenarien,
    die du im Szenario‑Vergleich ausgewählt hast.

    ## Enthaltene Elemente:

    ### ⭐ Stärken des Szenarios
    - Welche Faktoren positiv wirken
    - Welche Marktbedingungen vorteilhaft sind
    - Welche Asset‑Klassen profitieren

    ### ⚠️ Schwächen des Szenarios
    - Risiken und Unsicherheiten
    - mögliche Drawdowns
    - erhöhte Volatilität

    ### 📈 Chancen
    - Wachstumstreiber
    - Momentum‑Signale
    - Sektor‑ oder Länder‑Vorteile

    ### 📉 Risiken
    - Marktrisiken
    - Zinsrisiken
    - Währungsrisiken
    - Tail‑Risks

    ### 🔄 Vergleich der beiden Szenarien
    - Welches Szenario ist defensiver?
    - Welches bietet mehr Wachstum?
    - Wo liegen die größten Unterschiede?

    ### 🎯 Strategische Einordnung
    - Welche Strategie passt zu welchem Szenario?
    - Wie könnte ein Portfolio angepasst werden?
    - Welche Asset‑Klassen sind sinnvoll?

    ## Hinweis
    Die Storyline wird automatisch generiert, sobald du im Szenario‑Vergleich
    zwei Szenarien analysierst.
    """)

def build_cache_tools():
    gr.Markdown("""
    # 🧹 Cache‑Verwaltung

    Hier kannst du den internen Cache des Dashboards verwalten.
    Der Cache speichert:
    - Preis‑Daten
    - Radar‑Daten
    - KI‑Scores
    - Portfolio‑Berechnungen
    - Szenario‑Simulationen

    ## Warum Cache leeren?

    - Wenn Daten veraltet wirken
    - Wenn du neue Datenquellen geladen hast
    - Wenn du Fehler beheben möchtest
    - Wenn du Speicher freigeben willst

    ## Hinweis
    Das Leeren des Caches kann die Performance kurzzeitig beeinflussen,
    da Daten neu geladen werden müssen.
    """)

    clear_btn = gr.Button("Cache leeren")
    output = gr.Markdown("")

    def _clear():
        clear_cache()
        return "✅ Cache wurde erfolgreich geleert."

    clear_btn.click(_clear, outputs=output)

def build_log_viewer():
    gr.Markdown("""
    # 📜 Log‑Viewer

    Hier kannst du die internen Logs des Systems einsehen.
    Die Logs enthalten:
    - Fehler
    - Warnungen
    - Debug‑Informationen
    - Backend‑Meldungen

    Dies ist besonders hilfreich für:
    - Fehlersuche
    - Datenvalidierung
    - Performance‑Analyse
    """)

    log_output = gr.Textbox(label="System‑Logs", lines=20)

    def _load_logs():
        return "\n".join(log_buffer[-500:]) if log_buffer else "Keine Logs vorhanden."

    refresh_btn = gr.Button("Logs aktualisieren")
    refresh_btn.click(_load_logs, outputs=log_output)

def build_system_info():
    gr.Markdown("""
    # 🖥 System‑Informationen

    Dieser Bereich zeigt technische Informationen über das Dashboard,
    Datenquellen und Systemstatus.

    ## Enthaltene Informationen:
    - Version des Dashboards
    - Anzahl geladener ETFs und Aktien
    - Status der ISIN‑Datenbank
    - Cache‑Status
    - Datenquellen
    - Backend‑Module
    """)

    info_box = gr.JSON(label="System‑Status")

    def _system_info():
        return {
            "Dashboard-Version": "1.0.0",
            "ETFs geladen": len(ETF_DB),
            "Aktien geladen": len(STOCK_DB),
            "ISIN‑DB geladen": bool(load_isin_db()),
            "Cache‑Status": "aktiv",
            "Datenquellen": [
                "Yahoo Finance",
                "Interne ETF‑DB",
                "Interne Aktien‑DB",
                "ISIN‑Datenbank"
            ],
            "Module": [
                "KI‑Scanner",
                "Portfolio‑Engine",
                "Radar‑Engine",
                "Szenario‑Engine"
            ]
        }

    refresh_btn = gr.Button("Systeminfo aktualisieren")
    refresh_btn.click(_system_info, outputs=info_box)


#--------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def app():

    presets_all = load_presets()

    with gr.Blocks(title="MakroSim Dashboard") as demo:
        # -------------------------------------------------
        # TAB: Asset‑Analyse
        # -------------------------------------------------
        with gr.Tab("Asset‑Analyse"):
            asset_input = gr.Textbox(label="Ticker", placeholder="z. B. AAPL")
            asset_btn = gr.Button("Analysieren")
            asset_type_html = gr.HTML()
            asset_json = gr.JSON()
            asset_ki = gr.Number()
            asset_radar = gr.JSON()

            asset_btn.click(
                ui_asset_wrapper,
                inputs=[asset_input],
                outputs=[asset_type_html, asset_json, asset_ki, asset_radar],
            )

        # -------------------------------------------------
        # TAB: KI‑Ranking
        # -------------------------------------------------
        with gr.Tab("KI‑Ranking"):
            ki_input = gr.Textbox(label="Ticker‑Liste", placeholder="AAPL, SPY, EIMI")
            ki_btn = gr.Button("Scannen")
            ki_table = gr.Dataframe(label="KI‑Ranking")
            ki_explain = gr.Markdown()

            ki_btn.click(
                ui_ki_scan,
                inputs=[ki_input],
                outputs=[ki_table, ki_explain],
            )
            gr.Markdown("""
            ### GLOBAL WÄHRUNGS-RANKING (BEISPIEL)

            1. CHF – Schweizer Franken – Score 92
            2. SGD – Singapur Dollar – Score 90
            3. AED – UAE Dirham – Score 88
            4. NOK – Norwegische Krone – Score 86
            5. SAR – Saudi Riyal – Score 84
            6. QAR – Katar Riyal – Score 82
            7. OMR – Oman Rial – Score 78
            8. USD – US Dollar – Score 76
            9. EUR – Euro – Score 74
            10. GBP – Britisches Pfund – Score 72

            ---

            ## GOLF-WÄHRUNGEN – VERGLEICH (OMR, SAR, AED, QAR)

            Oman – OMR (Rial Omani)
            - Sehr stabiler USD-Peg
            - Kleine Wirtschaft, hohe Öl-Abhängigkeit
            - Moderate Devisenreserven
            - Niedrige Inflation
            - Weniger diversifiziert als UAE/Saudi

            Saudi-Arabien – SAR (Saudi Riyal)
            - Größte Volkswirtschaft im GCC
            - Sehr hohe Ölreserven und Staatsfonds (PIF)
            - Starker USD-Peg, hohe Glaubwürdigkeit
            - Moderate Inflation
            - Politisch und wirtschaftlich systemrelevant

            UAE – AED (Dirham)
            - Sehr diversifizierte Wirtschaft (Finanzen, Tourismus, Handel)
            - Hohe Devisenreserven
            - Sehr stabiler USD-Peg
            - Geringe Inflation
            - Starke internationale Integration

            Katar – QAR (Qatari Riyal)
            - Extrem hohe Pro-Kopf-Einkommen
            - Gasreich, LNG-Dominanz
            - Starker USD-Peg
            - Politische Risiken (Blockade 2017)
            - Sehr hohe Reserven und Staatsfonds (QIA)

            ---

            ## RISIKO-RANKING GOLF-WÄHRUNGEN (0 = sehr stabil, 100 = sehr riskant)

            1. UAE – AED → Score ~ 12
              - Höchste Diversifizierung
              - Sehr starke Reserven
              - Extrem stabiler Peg

            2. Saudi-Arabien – SAR → Score ~ 16
              - Größte Wirtschaft im GCC
              - Hohe Ölreserven, großer Staatsfonds
              - Politisch stabil

            3. Katar – QAR → Score ~ 18
              - Sehr reich, gasbasiert
              - Politische Spannungen als Risikofaktor

            4. Oman – OMR → Score ~ 22
              - Stabiler Peg, aber kleinere Wirtschaft
              - Höhere Verwundbarkeit bei Ölpreis-Schocks

            ---

            ## GOLF-WÄHRUNGEN-DASHBOARD – UI-MOCKUP

            ## [HEADER – VERGLEICH]

            | Land | Währung | Peg | Inflation | Rating | Score |
            | ----| --------| ----| ----------| -------| ------|
            | **Oman** | OMR | USD | 1.2% | A | 78  |
            | **Saudi**| SAR | USD | 2.0% | A+ | 84 |
            | **UAE**  | AED | USD | 1.5% | AA | 88 |
            | **Katar**| QAR | USD | 1.8% | AA- | 82 |


            [SEKTION 1 – RISIKO-RADAR]
            Tabs: Oman | Saudi | UAE | Katar
            - Radar-Chart mit 6 Achsen:
              - Inflationsrisiko
              - FX-Volatilität
              - Zentralbank-Risiko
              - Staatsverschuldung
              - Dollarabhängigkeit
              - Kapitalflucht-Risiko

            [SEKTION 2 – MAKRO-KACHELN]
            - Inflation YoY
            - Leitzins
            - Devisenreserven
            - Leistungsbilanz (% BIP)
            - Staatsrating

            [SEKTION 3 – ZEITREIHEN]
            - Wechselkursverlauf (Peg → flache Linie)
            - Inflation
            - Zinsen
            - Reserven

            [SEKTION 4 – STORYLINES]
            4 Spalten:
            - Oman – Kurzstory
            - Saudi – Kurzstory
            - UAE – Kurzstory
            - Katar – Kurzstory

            [SEKTION 5 – SZENARIO-ENGINE]
            Dropdown:
            - US-Zinsanstieg
            - Ölpreis-Schock
            - Regionale Instabilität

            Impact-Balken je Land:
            - niedrig / mittel / hoch

            ---


            ## AUTOMATISCHES WÄHRUNGS-SCORING-SYSTEM

            Ziel:
            - Score 0–100 (100 = sehr stabil)

            Input (0–1 normalisiert):
            - IR  = Inflationsrisiko
            - FXR = FX-Volatilitätsrisiko
            - CBR = Zentralbank-Risiko
            - SDR = Staatsverschuldungsrisiko
            - USDR = Dollarabhängigkeitsrisiko
            - KFR = Kapitalflucht-Risiko

            Formel:
            Score = 100 * [
                0.20 * (1 - IR) +
                0.15 * (1 - FXR) +
                0.20 * (1 - CBR) +
                0.20 * (1 - SDR) +
                0.10 * (1 - USDR) +
                0.15 * (1 - KFR)
            ]

            Interpretation:
            - 80–100: Sehr stabil
            - 60–79: Stabil
            - 40–59: Erhöhtes Risiko
            - < 40: Hohe Risiken

            Beispielwerte:
            - UAE (AED): Score ~ 88
            - Saudi (SAR): Score ~ 84
            - Katar (QAR): Score ~ 82
            - Oman (OMR): Score ~ 78

            ---

            ## FRÜHWARNSYSTEM FÜR WÄHRUNGSKRISEN

            Trigger 1: Inflation
            - Warnung: Inflation > 8 %
            - Alarm: Inflation > 15 %

            Trigger 2: Devisenreserven
            - Warnung: Reserven fallen 10 % in 3 Monaten
            - Alarm: Reserven fallen 20 % in 3 Monaten

            Trigger 3: Wechselkurs
            - Warnung: Abwertung > 5 % in 30 Tagen
            - Alarm: Abwertung > 10 % in 30 Tagen

            Trigger 4: Zinsen
            - Warnung: Leitzins steigt 2× in 60 Tagen
            - Alarm: Notfallzinserhöhung > 200 Basispunkte

            Trigger 5: Kapitalflucht
            - Warnung: Kapitalabfluss > 3 % BIP
            - Alarm: Kapitalabfluss > 5 % BIP

            Trigger 6: Politische Instabilität
            - Warnung: Regierungswechsel, Proteste, SankStionen
            - Alarm: Staatskrise, Putsch, Krieg

            Output:
            - Ampel (grün/gelb/rot)
            - Risiko-Score
            - Handlungsempfehlung

            ---

            ## GCC-ERWEITERUNG – KUWAIT & BAHRAIN

            Kuwait – KWD
            - Sehr starke Währung (eine der „teuersten“ der Welt)
            - Ölreich, hoher Wohlstand
            - Peg: Korb aus Währungen mit starkem USD-Anteil
            - Hohe Reserven, relativ konservative Politik
            - Risiko: Ölpreis, regionale Politik

            Bahrain – BHD
            - Kleine, offene Wirtschaft
            - Peg an den US-Dollar
            - Weniger Reserven als Saudi/UAE/Katar/Kuwait
            - Teilweise Unterstützung durch Nachbarländer (Saudi, UAE)
            - Risiko: Schulden, Abhängigkeit von externer Hilfe

            Erweiterung im Dashboard:
            - Region „GCC“ umfasst:
              - Saudi-Arabien (SAR)
              - UAE (AED)
              - Katar (QAR)
              - Oman (OMR)
              - Kuwait (KWD)
              - Bahrain (BHD)
            - Vergleichstabelle + Risiko-Ranking + Radar pro Land

            ---

            ## GLOBALER WÄHRUNGSVERGLEICH – TR, AR, CH

            Türkei – TRY
            - Hohe und volatile Inflation
            - Zentralbank politisch beeinflusst
            - Starke Währungsabwertung in den letzten Jahren
            - Hohe Fremdwährungsschulden im Privatsektor
            - Kapitalflucht-Tendenzen
            → Hohe Währungsrisiken

            Argentinien – ARS
            - Chronisch hohe Inflation (oft zweistellig bis dreistellig)
            - Mehrfache Staatspleiten in der Geschichte
            - Kapitalkontrollen, Parallelmärkte (Schwarzmarkt-Dollar)
            - Sehr geringes Vertrauen in die Landeswährung
            → Extrem hohes Währungsrisiko, strukturell

            Schweiz – CHF
            - Sehr niedrige Inflation
            - Starke, unabhängige Zentralbank (SNB)
            - Sichere Anlagewährung („Safe Haven“)
            - Hohe Devisenreserven
            - Stabile Politik, starke Wirtschaft
            → Eine der stabilsten Währungen der Welt

            ---

            ## GLOBALER WÄHRUNGS-SCORE (0–100, 100 = sehr stabil)

            Schweiz – CHF
            - IR=0.05, FXR=0.10, CBR=0.05, SDR=0.20, USDR=0.20, KFR=0.05
            → Score ≈ 92 (sehr stabil)

            Türkei – TRY
            - IR=0.80, FXR=0.70, CBR=0.80, SDR=0.50, USDR=0.60, KFR=0.70
            → Score ≈ 30 (hohes Risiko)

            Argentinien – ARS
            - IR=0.95, FXR=0.85, CBR=0.90, SDR=0.70, USDR=0.70, KFR=0.90
            → Score ≈ 18 (extrem hohes Risiko)

            ---

            ## GLOBALE WÄHRUNGS-STORYLINE-ENGINE

            Input:
            - stability_score (0–100)
            - inflation_yoy
            - fx_volatility_risk
            - cb_independence_risk
            - sovereign_debt_risk
            - capital_flight_risk
            - peg_type (fixed/managed/float)
            - region

            Regel-Templates:

            1) Stabilitäts-Level
            - Score ≥ 85:
              -> "Die Währung zählt zu den stabilsten weltweit und wird häufig als sicherer Hafen betrachtet."
            - 70 ≤ Score < 85:
              -> "Die Währung gilt als stabil, mit überschaubaren Risiken."
            - 50 ≤ Score < 70:
              -> "Die Währung weist erhöhte Risiken auf, bleibt aber grundsätzlich funktionsfähig."
            - Score < 50:
              -> "Die Währung ist mit erheblichen Risiken behaftet; Krisen sind möglich oder bereits sichtbar."

            2) Inflations-Kommentar
            - inflation_yoy < 3 %:
              -> "Die Inflation ist niedrig und gut kontrolliert."
            - 3–8 %:
              -> "Die Inflation ist erhöht und sollte beobachtet werden."
            - > 8 %:
              -> "Die hohe Inflation belastet die Kaufkraft und erhöht das Währungsrisiko deutlich."

            3) Zentralbank-Kommentar
            - cb_independence_risk niedrig:
              -> "Die Zentralbank gilt als unabhängig und glaubwürdig."
            - hoch:
              -> "Politische Einflussnahme auf die Zentralbank schwächt das Vertrauen in die Währung."

            4) Kapitalflucht-Kommentar
            - capital_flight_risk hoch:
              -> "Es besteht ein erhöhtes Risiko, dass Kapital das Land verlässt, was zusätzlichen Druck auf die Währung ausüben kann."

            5) Peg vs. Float
            - peg_type = fixed:
              -> "Die Währung ist an eine Leitwährung gekoppelt, was kurzfristig Stabilität, aber langfristig Abhängigkeiten schafft."
            - peg_type = float:
              -> "Die Währung wird frei gehandelt und reagiert sensibel auf Markt- und Politikereignisse."

            Output (Beispielstruktur):
            - Stärken: [Liste generierter Sätze]
            - Schwächen: [Liste generierter Sätze]
            - Kurzprognose (1–3 Sätze), z. B.:
              -> "Kurzfristig bleibt die Währung stabil, mittelfristig hängen die Risiken vor allem von Inflation und Politik ab."
            """)

        # -------------------------------------------------
        # TAB: Ticker → ISIN
        # -------------------------------------------------
        with gr.Tab("Ticker → ISIN"):
            isin_input = gr.Textbox(label="Ticker", placeholder="AAPL")
            isin_btn = gr.Button("Konvertieren")
            isin_table = gr.Dataframe(label="Ticker → ISIN")

            isin_btn.click(
                ui_convert_isin,
                inputs=[isin_input],
                outputs=[isin_table],
            )

        with gr.Tab("Home"):
            build_home()

        with gr.Tab("🤖 KI‑Asset‑Scanner"):
            gr.Markdown("""
            ### 🤖 KI‑Asset‑Scanner – Erklärung & Lexikon

            Der KI‑Asset‑Scanner hilft dir dabei, Aktien, ETFs und Kryptowährungen schnell zu bewerten, zu filtern und nach einem KI‑Score zu sortieren.
            Damit du genau weißt, was hier passiert, findest du hier die wichtigsten Begriffe:

            ---

            ## 📌 Was ist ein *Screener*?
            Ein Screener ist ein **Filter‑Werkzeug**.
            Du gibst Kriterien vor (z. B. Region, Branche, Risiko, KI‑Score), und der Scanner zeigt dir nur die passenden Assets.

            Beispiele:
            - „Zeige mir alle ETFs mit niedriger Volatilität“
            - „Zeige mir Aktien mit hohem KI‑Score“
            - „Zeige mir Kryptowährungen mit starkem Momentum“

            ---

            ## 📌 Was ist ein *Asset*?
            Ein Asset ist ein **Anlageobjekt**, also etwas, in das man investieren kann.
            Beispiele:
            - Aktien (z. B. Apple, BMW)
            - ETFs (z. B. MSCI World)
            - Kryptowährungen (z. B. Bitcoin, Ethereum)
            - Rohstoffe (z. B. Gold)

            ---

            ## 📌 Was bedeutet *KI‑Ranking*?
            Die KI analysiert jedes Asset anhand verschiedener Merkmale:
            - Trendstärke
            - Volatilität
            - Risiko
            - Muster in der Kursentwicklung
            - Korrelation zu anderen Assets
            - Stabilität

            Daraus entsteht ein **KI‑Score** (0–100).
            Der Scanner sortiert automatisch:

            - **Oben (80–100):** Hohe Qualität, starke Muster
            - **Mitte (40–80):** Neutral bis solide
            - **Unten (0–40):** Schwache Muster, hohes Risiko

            ---

            ## 📌 Was ist eine *ISIN*?
            Die ISIN ist die **internationale Wertpapierkennnummer**.
            Sie identifiziert ein Wertpapier eindeutig – wie ein Reisepass für Finanzprodukte.

            Beispiele:
            - Apple → **US0378331005**
            - iShares MSCI World ETF → **IE00B4L5Y983**

            ⚠️ **Wichtig:**
            Kryptowährungen haben **keine ISIN** (Bitcoin, Ethereum, Solana usw.).

            ---

            ## 📌 Wie entsteht eine ISIN‑Liste?
            Du gibst einfach Ticker ein, z. B.:
            AAPL, SPY, EUNL.DE, BTC-USD

            Der Scanner erkennt automatisch:
            - Aktien → ISIN wird geholt
            - ETFs → ISIN wird geholt
            - Krypto → keine ISIN (wird übersprungen)

            Ergebnis:
            US0378331005 US78462F1030 IE00B4L5Y983

            ---

            ## 📌 Wozu brauche ich eine ISIN‑Liste?
            - Für ETF‑Analysen
            - Für Portfolio‑Optimierung
            - Für Watchlists
            - Für Datenimporte in Excel oder Broker‑Tools

            Der KI‑Asset‑Scanner kann dir diese Liste automatisch erzeugen.
            """)

            gr.Markdown("""
            ### 📌 Ticker → ISIN Konverter
            Gib einfach Ticker ein (z. B. AAPL, SPY, EUNL.DE, BTC-USD).
            Der Scanner erkennt automatisch, ob eine ISIN existiert.
            """)

            # -----------------------------
            # 1. ISIN-KONVERTER
            # -----------------------------
            isin_input = gr.Textbox(
                label="Ticker-Liste (Komma-getrennt)",
                placeholder="z. B. AAPL, SPY, EUNL.DE, BTC-USD"
            )
            isin_btn = gr.Button("ISIN-Liste erzeugen")
            isin_table = gr.Dataframe(label="Ticker → ISIN", interactive=False)

            isin_btn.click(ui_convert_isin, inputs=[isin_input], outputs=[isin_table])

            # -----------------------------
            # 2. KI-SCORE (einfacher KI-Scan)
            # -----------------------------
            gr.Markdown("""
            ### 🤖 KI‑Score (0–100) – Einzel‑Scan

            Der KI‑Score bewertet jedes Asset (Aktie, ETF, Krypto) anhand seines Kursverhaltens der letzten Monate.
            Er kombiniert Momentum, Trendstabilität, Volatilität, Drawdown, Sharpe‑Ratio und weitere technische Faktoren zu einer einzigen Kennzahl zwischen 0 und 100.
            Ein hoher Score bedeutet ein starkes, stabiles Trendmuster; ein niedriger Score deutet auf Schwäche oder hohe Unsicherheit hin.

            **Was bedeutet der KI‑Score?**

            - **80–100:** Sehr starke Muster, stabile Trends, attraktives Risiko‑Profil
            - **60–80:** Gute Qualität, solide Entwicklung
            - **40–60:** Neutral, weder besonders stark noch schwach
            - **20–40:** Schwache Muster, erhöhte Risiken
            - **0–20:** Chaotisch, instabil, hohe Verlustgefahr

            Der Einzel‑Scan eignet sich, wenn du **einfach nur wissen willst, wie gut ein Asset aktuell aussieht**, ohne Vergleich oder Profil‑Analyse.
            """)

            ki_input = gr.Textbox(
                label="Ticker-Liste (Komma-getrennt)",
                placeholder="z. B. AAPL, SPY, BTC-USD"
            )
            ki_btn = gr.Button("KI‑Score berechnen")

            ki_table = gr.Dataframe(label="KI‑Ranking")
            ki_explain = gr.Markdown()
            ki_btn.click(ui_ki_scan, inputs=[ki_input], outputs=[ki_table, ki_explain])

            # -----------------------------
            # 3. KI-PROFIL-SCAN (mit Radar)
            # -----------------------------
            gr.Markdown("""
            ### 🧠 KI‑Profil‑Scan (mit Radar‑Vergleich)

            Der KI‑Profil‑Scan analysiert mehrere Assets gleichzeitig und bewertet sie nach einem ausgewählten Profil
            (z. B. *stabil*, *momentum*, *growth*, *diversifikation*, *krypto*, *etf*).

            **Was macht der Profil‑Scan?**

            1. Jedes Asset wird nach dem gewählten Profil bewertet
            2. Die Ergebnisse werden in einer Tabelle sortiert (bestes Asset oben)
            3. Zusätzlich wird ein **Radar‑Diagramm** erzeugt, das die wichtigsten Faktoren zeigt:
               - Momentum
               - Volatilität
               - Drawdown
               - Trendstabilität
               - Sharpe‑Ratio
               - Diversifikation

            **Warum Radar?**
            Das Radar zeigt die **technischen Faktoren** auf einer Skala von **0–1**, damit du die Stärken und Schwächen eines Assets auf einen Blick erkennst.

            **Unterschied zum KI‑Score:**

            - **KI‑Score (0–100):** Gesamtbewertung eines einzelnen Assets
            - **KI‑Profil‑Scan:** Vergleich mehrerer Assets + Radar‑Visualisierung + Profil‑Logik

            Der Profil‑Scan ist ideal, wenn du **mehrere Assets vergleichen** oder **ein bestimmtes Anlagestil‑Profil** analysieren möchtest.
            """)

            region = gr.Dropdown(
                label="Region (optional)",
                choices=["Keine", "Europa", "USA", "Global"],
                value="Keine"
            )
            gr.Markdown("""
            ### 🧠 KI‑Profil‑Erklärungen

            Jedes KI‑Profil bewertet Assets nach einem bestimmten Anlagestil.
            Die KI passt Gewichtungen, Faktoren und Prioritäten automatisch an.

            ---

            ## 🔹 Profil: **ki** (Standard)
            Das Standard‑Profil kombiniert alle Faktoren ausgewogen:
            - Momentum
            - Volatilität
            - Trendstabilität
            - Drawdown
            - Sharpe Ratio
            - Diversifikation

            **Ziel:** Ein möglichst objektiver Gesamt‑Score (0–100).

            ---

            ## 🔹 Profil: **stabil**
            Bevorzugt stabile, risikoarme Assets:
            - niedrige Volatilität
            - geringer Drawdown
            - hohe Trendstabilität

            **Ideal für:** defensive Anleger, langfristige Strategien.

            ---

            ## 🔹 Profil: **momentum**
            Bevorzugt starke Trends:
            - hohes Momentum
            - hohe Trendstärke
            - klare Aufwärtsbewegungen

            **Ideal für:** Trendfolger, kurzfristige Chancen.

            ---

            ## 🔹 Profil: **growth**
            Bevorzugt wachstumsorientierte Assets:
            - hohe Trenddynamik
            - starke Kursbeschleunigung
            - überdurchschnittliche Performance

            **Ideal für:** wachstumsorientierte Strategien.

            ---

            ## 🔹 Profil: **diversifikation**
            Bevorzugt Assets, die gut kombinierbar sind:
            - niedrige Korrelation
            - stabilisierende Eigenschaften
            - risikoausgleichende Faktoren

            **Ideal für:** Portfolio‑Optimierung.

            ---

            ## 🔹 Profil: **krypto**
            Bevorzugt starke Muster in volatilen Märkten:
            - Momentum
            - Trendstabilität
            - Risikoanpassung für hohe Volatilität

            **Ideal für:** Krypto‑Trader.

            ---

            ## 🔹 Profil: **etf**
            Bevorzugt ETFs mit:
            - stabilen Trends
            - niedriger Volatilität
            - guter Diversifikation

            **Ideal für:** langfristige ETF‑Investoren.
            """)



            profile = gr.Dropdown(
                label="KI‑Profil",
                choices=["ki", "stabil", "momentum", "growth", "diversifikation", "krypto", "etf"],
                value="ki"
            )

            asset_list = gr.Textbox(
                label="Assets eingeben (Komma‑getrennt)",
                placeholder="z. B. SPY, QQQ, VTI, BTC-USD, AAPL, MSFT"
            )

            scan_button = gr.Button("KI‑Profil‑Scan starten")
            scan_table = gr.Dataframe(label="KI‑Ranking", interactive=False)
            scan_plot = gr.Plot(label="Radar‑Vergleich")

            scan_button.click(
                scan_assets,
                inputs=[asset_list, profile, region],
                outputs=[scan_table, scan_plot]
            )

        with gr.Tab("ETF‑Screener"):
            with gr.Tabs():

                with gr.Tab("Screener"):
                    build_etf_screener()

                with gr.Tab("Lexikon"):
                    build_etf_lexikon()

                with gr.Tab("Ziel‑Setzung"):
                    build_etf_goal_setting()

        with gr.Tab("Aktien‑Screener"):
          with gr.Tabs():

              with gr.Tab("Screener"):
                  build_stock_screener()

              with gr.Tab("Lexikon"):
                  build_stock_lexikon()

              with gr.Tab("Ziel‑Setzung"):
                  build_stock_goal_setting()

        with gr.Tab("🧾 Anleihen‑Analyse"):
            build_bond_analysis()   # Platzhalter für später

        with gr.Tab("🪙 Krypto‑Analyse"):
            build_crypto_analysis()   # KI‑Score + Radar funktionieren bereits

        with gr.Tab("⚠️ Risiko‑Dashboard"):
            build_risk_dashboard()   # Korrelation‑Heatmap wird hier integriert
            with gr.Tabs():

                with gr.Tab("Analyse"):
                    build_risk_dashboard()

                with gr.Tab("Lexikon"):
                    build_risk_lexikon()

                with gr.Tab("Risikoprofil"):
                    build_risk_profile()


        with gr.Tab("Portfolio‑Optimierer"):
            with gr.Tabs():

                with gr.Tab("Optimierer"):
                    build_portfolio_optimizer()

                with gr.Tab("Ziel‑Setzung"):
                    build_portfolio_goal_setting()

                with gr.Tab("Lexikon"):
                    build_portfolio_lexikon()

        with gr.Tab("📂 Portfolio‑Studio"):
            build_portfolio_studio()
            with gr.Tabs():

                with gr.Tab("Backtest"):
                    build_portfolio_studio()

                with gr.Tab("Kennzahlen"):
                    build_portfolio_stats()

                with gr.Tab("Interpretation"):
                    build_portfolio_story()

        with gr.Tab("## 📈 Szenario‑Vergleich"):
          with gr.Tabs():

              with gr.Tab("Simulation"):
                  build_scenario_comparison()

              with gr.Tab("Radar"):
                  build_scenario_radar()

              with gr.Tab("Storyline"):
                  build_scenario_story()

        with gr.Tab("## ⚙️ Einstellungen / Daten / ISIN‑DB"):

            with gr.Tabs():
                with gr.Tab("ISIN‑DB"):
                    build_settings_tab()

                with gr.Tab("Cache"):
                    build_cache_tools()

                with gr.Tab("Logs"):
                    build_log_viewer()

                with gr.Tab("System"):
                    build_system_info()


    return demo
