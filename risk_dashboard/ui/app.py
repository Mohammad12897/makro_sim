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


#--------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def app():

    presets_all = load_presets()
    #countries = list(presets_all.keys())  # <-- dynamisch aus JSON

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

        with gr.Tab("Home / Was bedeuten die Radare?"):
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
            build_etf_screener()

        with gr.Tab("Aktien‑Screener"):
            build_stock_screener()

        with gr.Tab("🧾 Anleihen‑Analyse"):
            build_bond_analysis()   # Platzhalter für später

        with gr.Tab("🪙 Krypto‑Analyse"):
            build_crypto_analysis()   # KI‑Score + Radar funktionieren bereits

        with gr.Tab("⚠️ Risiko‑Dashboard"):
            build_risk_dashboard()   # Korrelation‑Heatmap wird hier integriert

        with gr.Tab("Portfolio‑Optimierer"):
            build_portfolio_optimizer()

        with gr.Tab("📂 Portfolio‑Studio"):
            build_portfolio_studio()


        with gr.Tab("## 📈 Szenario‑Vergleich"):
            build_scenario_comparison()

        with gr.Tab("## ⚙️ Einstellungen / Daten / ISIN‑DB"):
            build_settings_tab()   # ISIN‑DB, Cache, Logs, API‑Status           


    return demo
