# ui/app.py

import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from core.reporting.pdf_report import create_pdf_report
from core.storyline_engine import (
    generate_storyline,
    generate_executive_summary,
    compute_risk_score,
    risk_color,
)
from core.plots.risk_plots import plot_scenario_radar_overlay
from core.plots.heatmap_plots import plot_risk_heatmap  # falls du Heatmap im PDF willst

from core.presets import load_presets
from core.scenario_engine import scenario_radar_overlay
from core.portfolio_sim.scenario_compare import run_scenario_comparison
from core.plots.risk_plots import plot_scenario_radar_overlay
from core.risk_ampel import compute_risk_score, risk_color
from core.plots.heatmap_plots import plot_risk_heatmap
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
from core.backend.portfolio_optimizer import optimize_markowitz, optimize_risk_parity, optimize_ki_score
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


print("Europa:", list_etf_by_region("Europa"))
print("USA:", list_etf_by_region("USA"))
print("Global:", list_etf_by_region("Global"))


# ---------------------------------------------------------
# Theme
# ---------------------------------------------------------

theme = gr.themes.Soft()

# ---------------------------------------------------------
# Radar Overlay
# ---------------------------------------------------------

def compute_radar_overlay(land, we, wb, wg, yrs):
    presets_all = load_presets()
    base_scores = presets_all[land]

    score = compute_risk_score(base_scores)
    ampel = risk_color(score)

    metrics = scenario_radar_overlay(base_scores)
    fig = plot_scenario_radar_overlay(metrics)

    story = generate_storyline(base_scores)
    return ampel, fig, story


# ---------------------------------------------------------
# Szenario-Vergleich (Tabelle)
# ---------------------------------------------------------

def scenario_table_wrapper(land, we, wb, wg, yrs):
    presets_all = load_presets()
    base_scores = presets_all[land]

    results = run_scenario_comparison(land, base_scores, [we, wb, wg], yrs)

    rows = []
    for scen_name, scores in results.items():
        for key, val in scores.items():
            if isinstance(val, (int, float)):
                rows.append([scen_name, key, val])

    df = pd.DataFrame(rows, columns=["Szenario", "Indikator", "Wert"])
    return df

def parse_weights(text, n):
    if not text or not text.strip():
        return [1 / n] * n
    parts = [p.strip() for p in text.split(",") if p.strip()]
    vals = []
    for p in parts:
        try:
            vals.append(float(p))
        except Exception:
            vals.append(0.0)
    if len(vals) < n:
        vals += [0.0] * (n - len(vals))
    vals = vals[:n]
    s = sum(vals)
    if s == 0:
        return [1 / n] * n
    return [v / s for v in vals]


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def app():

    presets_all = load_presets()
    countries = list(presets_all.keys())  # <-- dynamisch aus JSON

    with gr.Blocks() as demo:

        # ---------------- Radar Overlay ----------------
        with gr.Tab("Was bedeuten die Radare?"):

            gr.Markdown("""
            # ℹ️ Was bedeuten die Radare?

            ## 🌍 Länder‑Radar
            Das Länder‑Radar bewertet die wirtschaftliche Stärke eines Landes anhand von:
            - BIP‑Wachstum
            - Inflation
            - Zinsen
            - Arbeitslosenquote
            - Staatsverschuldung
            - Währungsstärke

            Es beantwortet: **Wie stabil und attraktiv ist ein Land wirtschaftlich?**

            ---

            ## 📈 ETF‑Radar
            Das ETF‑Radar bewertet ETFs anhand von:
            - Performance (1Y, 5Y)
            - Volatilität
            - Sharpe‑Ratio
            - TER (Kosten)
            - Tracking Error
            - Fondsgröße (AUM)
            - Dividendenrendite

            Es beantwortet: **Wie gut ist ein ETF im Verhältnis zu Risiko, Kosten und Performance?**

            ---

            ## 💼 Portfolio‑Radar
            Das Portfolio‑Radar bewertet:
            - gewichtete Sharpe‑Ratio
            - gewichtete Volatilität
            - Diversifikation
            - Regionen‑Exposure
            - Gesamt‑Performance

            Es beantwortet: **Wie stabil, diversifiziert und ausgewogen (Gesamtqualität) ist mein Portfolio?**

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
            Eine Anleihe ist ein Kredit, den du einem Staat oder Unternehmen gibst und dafür Zinsen erhältst.

            ### Sharpe‑Ratio
            Verhältnis von Rendite zu Risiko.

            ### Volatilität
            Schwankungsintensität eines Wertpapiers.

            ### TER
            Gesamtkostenquote eines ETFs.

            ### Diversifikation
            Verteilung des Risikos über viele Anlagen.

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

        with gr.Tab("Radar Aktien"):
            # Aktienliste laden

            stock_list = load_stock_list()
            # Eingabe
            aktien = gr.Dropdown(
                choices=stock_list,
                multiselect=True,
                label="Aktien auswählen (beliebig viele)",
                info="Autocomplete aktiviert"
            )
            benchmark_dropdown = gr.Dropdown(
                choices=["SPY", "QQQ", "VT", "None"],
                value="None",
                label="Benchmark auswählen"
            )

            mode_dropdown = gr.Dropdown(
                choices=["einsteiger", "experte"],
                value="einsteiger",
                label="Modus",
            )

            stock_button = gr.Button("Radar erstellen")

            # Ausgabe
            stock_radar_plot = gr.Plot(label="Radar-Chart")
            stock_radar_table = gr.Dataframe(label="Daten")
            stock_lexikon_table = gr.Dataframe(label="Lexikon")

            # --- Cluster Analyse UI ---
            cluster_btn = gr.Button("Cluster-Analyse")
            cluster_table = gr.Dataframe(label="Cluster-Ergebnis", interactive=False)

            def build_stock_radar(tickers, benchmark_choice, mode):

                if not tickers:
                    return None, pd.DataFrame(), pd.DataFrame()

                rows = []
                for t in tickers:
                    entry = {"ticker": t, "name": t}
                    metrics = get_metrics(entry)
                    if metrics is None:
                        continue
                    fund = get_fundamentals(t)
                    metrics.update(fund)

                    country = map_ticker_to_country(t)
                    macro = get_country_macro(country)
                    metrics.update(macro)
                    metrics["country"] = country
                    rows.append(metrics)

                if benchmark_choice != "None":
                    entry = {"ticker": benchmark_choice, "name": benchmark_choice}
                    bm = get_metrics(entry)
                    fund_bm = get_fundamentals(benchmark_choice)
                    bm.update(fund_bm)

                    country_bm = map_ticker_to_country(benchmark_choice)
                    bm.update(get_country_macro(country_bm))
                    bm["country"] = country_bm   # ← WICHTIG

                    rows.append(bm)

                rows = normalize_metrics(rows)

                fig = plot_radar_plotly(rows, mode=mode)
                lex = get_lexicon("aktien", mode=mode)

                return fig, pd.DataFrame(rows), pd.DataFrame(lex)


            def run_cluster(tickers):
                if not tickers:
                    return pd.DataFrame({"Fehler": ["Bitte mindestens eine Aktie auswählen"]})

                rows = []
                for t in tickers:
                    entry = {"ticker": t, "name": t}
                    metrics = get_metrics(entry)
                    if metrics is None:
                        continue
                    fund = get_fundamentals(t)
                    metrics.update(fund)
                    country = map_ticker_to_country(t)
                    macro = get_country_macro(country)
                    metrics.update(macro)
                    metrics["country"] = country
                    rows.append(metrics)

                rows = normalize_metrics(rows)
                df = cluster_stocks(rows)
                return df

            stock_button.click(build_stock_radar, inputs=[aktien, benchmark_dropdown, mode_dropdown], outputs=[stock_radar_plot, stock_radar_table, stock_lexikon_table])
            cluster_btn.click(run_cluster, inputs=[aktien], outputs=[cluster_table])

        with gr.Tab("Radar Länder"):
            gr.Markdown("""
            ## 🌍 Länder‑Radar
            Das Länder‑Radar bewertet die wirtschaftliche Stärke eines Landes anhand von:
            - BIP‑Wachstum
            - Inflation
            - Zinsen
            - Arbeitslosenquote
            - Staatsverschuldung
            - Währungsstärke

            **Frage, die das Radar beantwortet:**
            *Wie stabil, wachstumsstark und wirtschaftlich attraktiv ist ein Land?*
            """)

            laender_input = gr.Dropdown(
                choices=["USA", "Deutschland", "Japan", "UK", "Frankreich", "China", "Indien"],
                multiselect=True,
                label="Länder auswählen",
                info="Mehrere Länder möglich"
            )

            laender_mode = gr.Dropdown(
                ["einsteiger", "experte"],
                value="einsteiger",
                label="Modus",
                info = "Das Länder‑Radar zeigt die wirtschaftliche Stärke eines Landes anhand zentraler Makro‑Kennzahlen."
            )

            laender_button = gr.Button("Länder-Radar erstellen")

            laender_radar_plot = gr.Plot(label="Länder-Radar")
            laender_table = gr.Dataframe(label="Makro-Daten", interactive=False)
            laender_lexicon = gr.Dataframe(label="Lexikon", interactive=False)

            laender_button.click(
                build_country_radar,
                inputs=[laender_input, laender_mode],
                outputs=[laender_radar_plot, laender_table, laender_lexicon],
            )

        with gr.Tab("Radar ETF / Assets"):
            gr.Markdown("""
            ### 🪙 Was ist Bitcoin?

            Bitcoin ist eine **digitale, dezentrale Währung**, die ohne Banken oder Staaten funktioniert.
            Sie basiert auf der **Blockchain**, einem öffentlichen, unveränderbaren Register aller Transaktionen.

            **Wesentliche Eigenschaften:**
            - begrenzte Menge (max. 21 Millionen)
            - hohe Volatilität
            - wird oft als „digitales Gold“ bezeichnet
            - kann weltweit in Sekunden übertragen werden
            - keine zentrale Kontrolle

            **Warum im Asset‑Radar?**
            Bitcoin ist kein ETF und keine Aktie — aber ein **Asset**, das wie andere Vermögenswerte
            über Risiko‑ und Performance‑Kennzahlen analysiert werden kann.

            ## 🪙 Bitcoin‑Radar
            Bitcoin wird im Asset‑Radar wie ein eigenständiges Asset behandelt.
            Es besitzt eigene Kennzahlen, die sich von ETFs und Aktien unterscheiden:

            - **Volatilität** – misst die Schwankungsintensität
            - **Sharpe‑Ratio** – Verhältnis von Rendite zu Risiko
            - **Max Drawdown** – größter Verlust vom Hoch zum Tief
            - **SMA‑Trend (50/200)** – zeigt langfristige Trendrichtung
            - **Korrelation zu SPY** – Zusammenhang mit dem Aktienmarkt
            - **Korrelation zu Gold** – Vergleich zu einem klassischen Wertspeicher

            **Warum ist Bitcoin im Radar?**
            Weil es ein global handelbares Asset ist, das in Portfolios eine wichtige Rolle spielt:
            Diversifikation, Trendverhalten, Risiko‑Rendite‑Profil.
            """)

            gr.Markdown("""
            ## 📈 ETF‑Radar
            Das ETF‑Radar bewertet ETFs anhand von:
            - Performance (1Y, 5Y)
            - Volatilität
            - Sharpe‑Ratio
            - TER (Kosten)
            - Tracking Error
            - Fondsgröße (AUM)
            - Dividendenrendite

            **Frage, die das Radar beantwortet:**
            *Wie gut ist ein ETF im Verhältnis zu Risiko, Kosten und Performance?*
            """)

            etf_input = gr.Dropdown(
                choices=["SPY", "QQQ", "VT", "VEA", "VWO", "EWJ", "EEM", "BTC-USD"],
                multiselect=True,
                label="ETFs auswählen",
                info="Wähle ETFs, Aktien oder Bitcoin aus."
            )

            custom_symbol = gr.Textbox(
                label="Eigenes Symbol eingeben (optional)",
                placeholder="z. B. BMW.DE, TSLA, NESN.SW, ETH-USD",
                info="Hier kannst du jedes beliebige Symbol eingeben."
            )

            etf_mode = gr.Dropdown(
                ["einsteiger", "experte"],
                value="einsteiger",
                label="Modus",
                info="Einsteiger = einfache Darstellung, Experte = detaillierte Analyse."
            )

            etf_button = gr.Button("ETF-Radar erstellen")
            etf_radar_plot = gr.Plot(label="Asset-Radar")
            etf_table = gr.Dataframe(label="Asset-Daten", interactive=False)
            etf_lexicon = gr.Dataframe(label="Lexikon", interactive=False)


            etf_button.click(
                build_asset_radar,
                inputs=[etf_input,  custom_symbol, etf_mode],
                outputs=[etf_radar_plot, etf_table, etf_lexicon],
            )


        with gr.Tab("Radar Portfolio"):
            gr.Markdown("""
            ## 💼 Portfolio‑Radar
            Das Portfolio‑Radar bewertet:
            - gewichtete Sharpe‑Ratio
            - gewichtete Volatilität
            - Diversifikation
            - Regionen‑Exposure
            - Gesamt‑Performance

            **Frage, die das Radar beantwortet:**
            *Wie stabil, diversifiziert und ausgewogen ist mein Portfolio?*
            """)

            portfolio_name = gr.Textbox(
                label="Portfolioname",
                value="Mein Portfolio",
                info="Name des Portfolios, das analysiert werden soll."
            )

            portfolio_mode = gr.Dropdown(
                ["einsteiger", "experte"],
                value="einsteiger",
                label="Modus",
                info="Einsteiger = einfache Darstellung, Experte = detaillierte Analyse."
            )

            portfolio_button = gr.Button("Portfolio-Radar erstellen")

            portfolio_radar_plot = gr.Plot(label="Portfolio-Radar")
            portfolio_table = gr.Dataframe(label="Portfolio-Daten", interactive=False)
            portfolio_lexicon = gr.Dataframe(label="Lexikon", interactive=False)
             # WICHTIG: type="filepath"

            portfolio_pdf = gr.File(label="Radar-Analyse PDF" , type="filepath")


            portfolio_button.click(
                build_portfolio_radar,
                inputs=[portfolio_name, portfolio_mode],
                outputs=[portfolio_radar_plot, portfolio_table, portfolio_lexicon, portfolio_pdf],
            )

        with gr.Tab("KI-Asset‑Scanner"):

            gr.Markdown("""
            # 🤖 KI‑Asset‑Scanner

            - Wähle eine Region **oder** gib eigene Assets ein.
            - Wähle ein KI‑Profil (z. B. stabil, momentum, growth).
            - Die KI bewertet alle Assets nach Risiko, Rendite, Trend und Sharpe‑Ratio.
            """)


            region = gr.Dropdown(
                label="Region (optional)",
                choices=["Keine", "Europa", "USA", "Global"],
                value="Keine"
            )

            asset_list = gr.Textbox(
                label="Assets eingeben (Komma‑getrennt)",
                placeholder="z. B. SPY, QQQ, VTI, BTC-USD, AAPL, MSFT"
            )

            profile = gr.Dropdown(
                label="KI‑Profil",
                choices=["ki", "stabil", "momentum", "growth", "diversifikation", "krypto", "etf"],
                value="ki"
            )

            scan_button = gr.Button("KI-Scan starten")

            scan_table = gr.Dataframe(label="KI‑Ranking", interactive=False)
            scan_plot = gr.Plot(label="Radar‑Vergleich")

            scan_button.click(
                scan_assets,
                inputs=[asset_list, profile, region],
                outputs=[scan_table, scan_plot]
            )

        with gr.Tab("ETF‑Screener"):
            gr.Markdown("""
            # 📘 ETF‑Screener (justETF)
            Gib eine Liste von ISINs ein oder lade eine Region.
            Der Screener zeigt TER, Fondsgröße, Replikation und Tracking‑Differenz.
            """)

            etf_isins = gr.Textbox(
                label="ETF‑ISINs (Komma‑getrennt)",
                placeholder="z. B. IE00B4L5Y983, IE00B5BMR087"
            )

            etf_button = gr.Button("ETF‑Daten abrufen")

            etf_table = gr.Dataframe(label="ETF‑Daten", interactive=False)

            etf_button.click(
                fn=scan_etf_list,
                inputs=[etf_isins],
                outputs=[etf_table]
            )

        with gr.Tab("Aktien‑Screener"):
            gr.Markdown("""
            # 📊 Aktien‑Screener (Fundamentaldaten)
            Der Screener lädt KGV, KUV, PEG, Verschuldung, Cashflow und Wachstum.
            """)

            stock_symbols = gr.Textbox(
                label="Aktien‑Symbole (Komma‑getrennt)",
                placeholder="z. B. AAPL, MSFT, AMZN, TSLA"
            )

            stock_button = gr.Button("Aktien‑Daten abrufen")

            stock_table = gr.Dataframe(label="Fundamentaldaten", interactive=False)

            stock_button.click(
                fn=scan_stocks,
                inputs=[stock_symbols],
                outputs=[stock_table]
            )

        with gr.Tab("Portfolio‑Optimierer"):
            gr.Markdown("""
            # 🎯 Portfolio‑Optimierer
            Wähle eine Optimierungsstrategie:
            - Markowitz (Sharpe‑Maximierung)
            - Risiko‑Parität
            - KI‑Portfolio‑Score
            """)

            port_symbols = gr.Textbox(
                label="Assets (Komma‑getrennt)",
                placeholder="z. B. SPY, VTI, GLD, BTC-USD"
            )

            strategy = gr.Dropdown(
                label="Optimierungs‑Methode",
                choices=["Markowitz", "Risiko‑Parität", "KI‑Score"],
                value="Markowitz"
            )

            port_button = gr.Button("Portfolio optimieren")

            port_table = gr.Dataframe(label="Portfolio‑Gewichtung", interactive=False)

            def run_optimizer(symbols, strategy):
                symbols = [s.strip().upper() for s in symbols.split(",")]

                if strategy == "Markowitz":
                    return optimize_markowitz(symbols)
                elif strategy == "Risiko‑Parität":
                    return optimize_risk_parity(symbols)
                else:
                    # KI‑Score benötigt vorherigen KI‑Scan
                    df = scan_assets(",".join(symbols), "ki", "Keine")[0]
                    return optimize_ki_score(df)

            port_button.click(
                fn=run_optimizer,
                inputs=[port_symbols, strategy],
                outputs=[port_table]
            )

        with gr.Tab("Korrelation‑Heatmap"):
            gr.Markdown("""
            # 🔥 Korrelation‑Heatmap
            Zeigt die Zusammenhänge zwischen Assets.
            Ideal für Diversifikation und Risikoanalyse.
            """)

            heat_symbols = gr.Textbox(
                label="Assets (Komma‑getrennt)",
                placeholder="z. B. SPY, VTI, GLD, BTC-USD, AAPL"
            )

            heat_button = gr.Button("Heatmap erzeugen")

            heat_plot = gr.Plot(label="Korrelation‑Matrix")

            def run_heatmap(symbols):
                symbols = [s.strip().upper() for s in symbols.split(",")]
                return plot_correlation_heatmap(symbols)

            heat_button.click(
                fn=run_heatmap,
                inputs=[heat_symbols],
                outputs=[heat_plot]
            )


        with gr.Tab("📂 Portfolio‑Studio"):

            with gr.Tab("Portfolio‑Manager"):
                gr.Markdown("### Portfolios speichern, laden und verwalten")

                port_name = gr.Textbox(label="Portfolioname")
                port_symbols = gr.Textbox(
                    label="Assets (Komma‑getrennt)",
                    placeholder="z. B. SPY, EUNL.DE, BTC-USD",
                )
                port_weights = gr.Textbox(
                    label="Gewichte (Komma‑getrennt, optional)",
                    placeholder="z. B. 0.5, 0.3, 0.2",
                )

                save_btn = gr.Button("Portfolio speichern")
                delete_btn = gr.Button("Portfolio löschen")
                refresh_btn = gr.Button("Liste aktualisieren")

                port_list = gr.Dataframe(label="Gespeicherte Portfolios", interactive=False)
                status_msg = gr.Markdown()

                def ui_save_portfolio(name, symbols_text, weights_text):
                    symbols = [s.strip().upper() for s in symbols_text.split(",") if s.strip()]
                    if not symbols:
                        return "❌ Keine Symbole angegeben.", list_portfolios()
                    weights = parse_weights(weights_text, len(symbols))
                    msg = save_portfolio(name, symbols, weights)
                    return f"✅ {msg}", list_portfolios()

                def ui_delete_portfolio(name):
                    msg = delete_portfolio(name)
                    return msg, list_portfolios()

                def ui_list_portfolios():
                    ports = list_portfolios()
                    if not ports:
                        return []
                    return ports

                save_btn.click(ui_save_portfolio,
                               inputs=[port_name, port_symbols, port_weights],
                               outputs=[status_msg, port_list])

                delete_btn.click(ui_delete_portfolio,
                                 inputs=[port_name],
                                 outputs=[status_msg, port_list])

                refresh_btn.click(ui_list_portfolios,
                                  inputs=None,
                                  outputs=port_list)

            with gr.Tab("Portfolio‑Radar"):
                gr.Markdown("### Radar‑Ansicht für ein gespeichertes Portfolio")
                sel_port_name = gr.Textbox(label="Portfolioname")
                radar_btn = gr.Button("Radar anzeigen")
                radar_plot = gr.Plot(label="Portfolio‑Radar")

                def ui_portfolio_radar(name):
                    df, meta = get_portfolio(name)
                    if meta is None:
                        return None
                    return portfolio_radar(meta["symbols"], meta["weights"])

                radar_btn.click(ui_portfolio_radar,
                                inputs=[sel_port_name],
                                outputs=[radar_plot])

            with gr.Tab("Portfolio‑Backtest"):
                gr.Markdown("### Historische Performance eines Portfolios")
                bt_name = gr.Textbox(label="Portfolioname")
                bt_btn = gr.Button("Backtest starten")
                
                bt_plot = gr.Plot(label="Backtest‑Performance")

                def ui_backtest(name):
                    df, meta = get_portfolio(name)
                    if meta is None:
                        fig, ax = plt.subplots()
                        ax.text(0.5, 0.5, "Portfolio nicht gefunden", ha="center")
                        ax.axis("off")
                        return fig

                    series = backtest_portfolio(meta["symbols"], meta["weights"], period="5y")
                    if series is None or series.empty:
                        fig, ax = plt.subplots()
                        ax.text(0.5, 0.5, "Keine Daten für Backtest", ha="center")
                        ax.axis("off")
                        return fig

                    fig, ax = plt.subplots()
                    ax.plot(series.index, series.values, label=name)
                    ax.set_title(f"Backtest: {name}")
                    ax.set_xlabel("Datum")
                    ax.set_ylabel("Wert (normiert)")
                    ax.legend()
                    fig.autofmt_xdate()
                    return fig


                bt_btn.click(ui_backtest,
                             inputs=[bt_name],
                             outputs=[bt_plot])

            with gr.Tab("Portfolio‑Vergleich"):
                gr.Markdown("### Zwei Portfolios direkt vergleichen")

                p1_name = gr.Textbox(label="Portfolio A")
                p2_name = gr.Textbox(label="Portfolio B")
                cmp_btn = gr.Button("Vergleichen")
                cmp_plot = gr.Plot(label="Vergleich")
                
                def ui_compare(a, b):
                    df1, meta1 = get_portfolio(a)
                    df2, meta2 = get_portfolio(b)
                    if meta1 is None or meta2 is None:
                        fig, ax = plt.subplots()
                        ax.text(0.5, 0.5, "Portfolio A oder B nicht gefunden", ha="center")
                        ax.axis("off")
                        return fig

                    joined = compare_two_portfolios(meta1, meta2, period="5y")
                    if joined is None or joined.empty:
                        fig, ax = plt.subplots()
                        ax.text(0.5, 0.5, "Keine Daten für Vergleich", ha="center")
                        ax.axis("off")
                        return fig

                    fig, ax = plt.subplots()
                    for col in joined.columns:
                        ax.plot(joined.index, joined[col], label=col)
                    ax.set_title(f"Vergleich: {a} vs. {b}")
                    ax.set_xlabel("Datum")
                    ax.set_ylabel("Wert (normiert)")
                    ax.legend()
                    fig.autofmt_xdate()
                    return fig

                cmp_btn.click(ui_compare,
                              inputs=[p1_name, p2_name],
                              outputs=[cmp_plot])

            with gr.Tab("Symbol‑Tools"):
                gr.Markdown("### Symbole prüfen, Typ erkennen, Vorschläge anzeigen")
                sym_input = gr.Textbox(label="Symbol oder ISIN",
                                       placeholder="z. B. QQQM, NFLX, GC=F, ETH-USD, IE00B4L5Y983")
                sym_type = gr.Markdown()
                sym_valid = gr.Markdown()
                sym_suggest = gr.Dropdown(label="Vorschläge", choices=[], interactive=True)
                check_btn = gr.Button("Symbol prüfen")

                def ui_symbol_tools(text):
                    if not text or text.strip() == "":
                        return ("Typ: —", "Gültig: Nein", gr.update(choices=[]))

                    t = detect_symbol_type(text)
                    ok = True if is_isin(text) else validate_symbol(text)
                    sugg = suggest_symbols(text)

                    return (f"Typ: **{t}**",
                            f"Gültig: **{'Ja' if ok else 'Nein'}**",
                            gr.update(choices=sugg))

                check_btn.click(ui_symbol_tools,
                                inputs=[sym_input],
                                outputs=[sym_type, sym_valid, sym_suggest])

            with gr.Tab("Debug‑Log"):
                gr.Markdown("### 🛠 Debug‑Log (letzte Meldungen)")
                log_box = gr.Textbox(label="Log", lines=20)

                def load_log():
                    return "\n".join(log_buffer[-100:])

                refresh_btn = gr.Button("Log aktualisieren")
                refresh_btn.click(load_log, inputs=None, outputs=log_box)

        with gr.Tab("Radar-Overlay"):
            # Auswahl: mehrere Ticker
            all_etfs = [e["ticker"] for e in load_etf_db()]
            tickers_multi = gr.CheckboxGroup(
                choices=all_etfs,
                label="ETFs/Aktien für Radar-Overlay auswählen",
                value=all_etfs[:3]  # Default: erste 3
            )

            radar_plot = gr.Plot()
            radar_table = gr.Dataframe(interactive=False, label="Kennzahlen (Rohwerte)")

            def build_radar(selected):
                db = load_etf_db()
                rows = []
                for e in db:
                    if e["ticker"] in selected:
                        m = get_metrics(e)
                        if m:
                            rows.append(m)
                if not rows:
                    return None, pd.DataFrame()
                fig = plot_radar(rows)

                return fig, pd.DataFrame(rows)

            tickers_multi.change(build_radar, inputs=[tickers_multi], outputs=[radar_plot, radar_table])

            gr.Markdown("""
### Interpretation des Radar-Overlays

- **Rendite 1Y / 5Y:** weiter außen = höhere Rendite
- **Volatilität:** weiter außen = höheres Risiko (wird intern so skaliert, dass "besser" außen liegt)
- **Sharpe Ratio:** weiter außen = bessere risikobereinigte Rendite
- **Max Drawdown:** weiter außen = geringerer maximaler Verlust
- **Beta:** weiter außen = näher an 1 (marktähnliches Verhalten)

Die Tabelle darunter zeigt die **exakten Werte** der Kennzahlen.

## 📘 Finanzkennzahlen – Lexikon

### Rendite (1Y, 5Y)
Wie stark der Wert gestiegen ist.
- **1Y** = letztes Jahr
- **5Y** = letzte fünf Jahre

---

### Volatilität
Wie stark der Kurs schwankt.
- Hohe Volatilität = hohes Risiko
- Niedrige Volatilität = stabiler

---

### Sharpe Ratio
Rendite pro Risiko.
- **1.0 = gut**
- **2.0 = sehr gut**

---

### Max Drawdown
Größter Verlust vom letzten Hoch.
Zeigt, wie schlimm ein Crash war.

---

### Beta
Sensitivität zum Markt.
- **1.0 = bewegt sich wie der Markt**
- **> 1.0 = aggressiver**
- **< 1.0 = defensiver**

---

### Korrelation
Wie ähnlich sich zwei Werte bewegen.
- **1.0 = identisch**
- **0.0 = unabhängig**
- **−1.0 = gegensätzlich**
""")

            pdf_button = gr.Button("Portfolio als PDF exportieren")
            pdf_file = gr.File()

        # ---------------- Szenario-Vergleich ----------------
        with gr.Tab("Szenario-Vergleich"):
            scen_country = gr.Dropdown(choices=countries, label="Land")
            scen_w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
            scen_w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
            scen_w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
            scen_years = gr.Slider(1, 20, value=10, step=1, label="Jahre")

            scen_button = gr.Button("Szenarien vergleichen")
            scen_table = gr.Dataframe()

            scen_button.click(
                scenario_table_wrapper,
                [scen_country, scen_w_equity, scen_w_bond, scen_w_gold, scen_years],
                scen_table,
            )

        with gr.Tab("Ländervergleich"):

            country_list = get_country_choices()
            countries = gr.CheckboxGroup(country_list, label="Länder/Indizes auswählen")
            run_button = gr.Button("Vergleich starten")

            table_output = gr.Dataframe()
            story_output = gr.Markdown()

            def run_country_compare(selected):
                if not selected:
                    return None, "Bitte mindestens ein Land auswählen."


                tickers = [resolve_country(c) for c in selected]
                df = compare_countries(tickers)
                story = generate_country_storyline(df)

                return df, story

            run_button.click(
                run_country_compare,
                [countries],
                [table_output, story_output]
            )

        with gr.Tab("ETF-Tabelle"):
            def build_table():
                rows = []
                for e in load_etf_db():
                    m = get_metrics(e)
                    if m:
                        rows.append(m)
                return pd.DataFrame(rows)

            etf_df = gr.Dataframe(
                value=build_table,
                interactive=True,
                label="ETF-Kennzahlen (sortierbar)",
                row_count=20,     # erlaubt
                col_count=None    # erlaubt

            )

            gr.Markdown("""
### 📘 Finanzkennzahlen – Lexikon

**Rendite (1Y, 5Y)** – Wertentwicklung über 1 bzw. 5 Jahre
**Volatilität** – Schwankungsbreite (Risiko)
**Sharpe Ratio** – Rendite pro Risiko
**Max Drawdown** – Größter Verlust vom Hoch
**Beta** – Sensitivität zum Markt
**TER** – Kostenquote des ETFs
""")

        with gr.Tab("Aktienvergleich"):

            t1 = gr.Textbox(label="Ticker 1", value="AAPL")
            t2 = gr.Textbox(label="Ticker 2", value="MSFT")
            btn = gr.Button("Vergleichen")
            out = gr.Markdown()

            btn.click(stock_compare, inputs=[t1, t2], outputs=out)

        with gr.Tab("Länderauswahl"):
            country = gr.Dropdown(
                choices=get_all_countries(),
                label="Land auswählen"
            )

            gr.Markdown("Dieses Dropdown enthält **alle Länder der Welt**.")

        with gr.Tab("ETF Länder-Check"):
            country_input = gr.Textbox(
                value="Deutschland (DAX), USA (S&P 500), Frankreich, UK, Japan",
                label="Länder (Komma-getrennt)"
            )
            check_btn = gr.Button("Prüfen")
            result_md = gr.Markdown("Ergebnis erscheint hier")

            def run_country_check(text):
                countries = [c.strip() for c in text.split(",") if c.strip()]
                res = countries_with_etfs(countries)
                lines = ["**Länder → Region → Anzahl ETFs → Ticker**\n"]
                for c in countries:
                    info = res.get(c, {"tickers": [], "count": 0, "region": "Unbekannt"})
                    if info["count"]:
                        lines.append(f"- **{c}** ({info['region']}): {info['count']} → {', '.join(info['tickers'])}")
                    else:
                        lines.append(f"- **{c}** ({info['region']}): _keine ETFs in der DB_")
                return "\n\n".join(lines)

            check_btn.click(run_country_check, inputs=[country_input], outputs=[result_md])

        with gr.Tab("ETF-Auswahl"):

            # 1. Länder-Dropdown (mit lesbaren Namen)
            country_dropdown = gr.Dropdown(
                choices=get_country_choices(),
                label="Land auswählen"
            )

            # 2. ETF-Liste (zunächst leer)
            etf_assets = gr.CheckboxGroup(
                choices=[],
                label="Verfügbare ETFs"
            )

            # 3. Update-Funktion
            def update_etf_list(country):
                # Debug-Log (erscheint im Server-Log)
                print(f"[DEBUG] update_etf_list called with country={country}")
                region = (
                    "Europa" if country == "Deutschland (DAX)" else
                    "USA" if country == "USA (S&P 500)" else
                    "Global"
                )
                tickers = list_etf_by_region(region)
                print(f"[DEBUG] list_etf_by_region({region}) -> {tickers}")

                # WICHTIG: gib ein gr.update zurück, damit Gradio die CheckboxGroup sofort neu rendert
                return gr.update(choices=tickers, value=None, interactive=True)

            # 4. Gradio-Verknüpfung
            country_dropdown.change(
                update_etf_list,
                inputs=[country_dropdown],
                outputs=[etf_assets]
            )

            # Initialbefüllung beim Laden der App
            def init_etf():
                return gr.update(
                    choices=list_etf_by_region("Global"),
                    value=None,
                    interactive=True
                )

            demo.load(init_etf, inputs=None, outputs=[etf_assets])

        with gr.Tab("Portfolio-Simulator"):
            asset_list = [
                "AAPL", "MSFT", "AMZN", "GOOGL", "META",
                "SPY", "VTI", "EUNL.DE", "EUNA.DE",
                "GLD", "SGLN.L", "4GLD.DE", "AGG"
            ] + list_etf_tickers()
            portfolio_assets = gr.CheckboxGroup(asset_list, label="Assets auswählen")
            weights = gr.Slider(0, 1, step=0.05, label="Gewicht pro Asset", value=0.2)
            run_button = gr.Button("Portfolio simulieren")


            plot_output = gr.Plot(label="Buy & Hold")
            plot_output_rb = gr.Plot(label="Rebalancing")
            stats_output = gr.Dataframe()
            story_output = gr.Markdown()

            def run_portfolio_simulation(assets_selected, weight):
                if not assets_selected:
                    return None, None, None, "Bitte mindestens ein Asset auswählen."

                # automatische Asset-Erkennung + ETF-Korrektur
                tickers = [validate_or_fix_ticker(resolve_asset(t)) for t in assets_selected]

                # ungültige Ticker herausfiltern
                invalid = [t for t in tickers if t is None]
                if invalid:
                    return None, None, None, f"Folgende ETFs sind ungültig oder delisted: {invalid}"

                tickers = [t for t in tickers if t is not None]

                # Gewichte normalisieren
                w = {t: weight for t in tickers}
                s = sum(w.values())
                w = {k: v/s for k, v in w.items()}

                # Daten laden
                data = {t: load_asset_series(t) for t in tickers}

                # Simulationen
                result = simulate_portfolio(data, w)
                result_rb = simulate_portfolio_with_rebalancing(data, w, freq="M")
                # Plots
                fig = plot_portfolio(result["portfolio"])
                fig_rb = plot_portfolio(result_rb["portfolio_rebal"])

                # Kennzahlen
                stats = portfolio_stats(result["portfolio"])

                # Storyline
                story = generate_portfolio_storyline(w, stats)

                return fig, fig_rb, pd.DataFrame([stats]), story

            run_button.click(
                run_portfolio_simulation,
                [portfolio_assets, weights],
                [plot_output, plot_output_rb, stats_output, story_output]
            )

            # PDF-Export nur hier!
            pdf_button = gr.Button("Portfolio als PDF exportieren")
            pdf_file = gr.File()

            def export_portfolio_pdf(tickers, weight):
                if not tickers:
                    return None

                tickers = [resolve_asset(t) for t in tickers]

                w = {t: weight for t in tickers}
                s = sum(w.values())
                w = {k: v/s for k, v in w.items()}

                data = {t: load_asset_series(t) for t in tickers}
                result = simulate_portfolio(data, w)
                stats = portfolio_stats(result["portfolio"])
                fig = plot_portfolio(result["portfolio"])

                stats_df = pd.DataFrame([stats])
                filename = "/tmp/portfolio_report.pdf"
                with PdfPages(filename) as pdf:
                    draw_portfolio_page(pdf, fig, stats_df, w)

                return filename

            pdf_button.click(
                export_portfolio_pdf,
                [portfolio_assets, weights],
                pdf_file
            )

        with gr.Tab("Heatmap & Cluster"):
            h_button = gr.Button("Analyse starten")
            h_plot = gr.Plot()
            h_table = gr.Dataframe()

            def run_heatmap_cluster():
                presets_all = load_presets()
                heatmap = plot_risk_heatmap(presets_all)
                clusters = compute_clusters(presets_all)
                return heatmap, clusters

            h_button.click(run_heatmap_cluster, None, [h_plot, h_table])


            pdf_button = gr.Button("Portfolio als PDF exportieren")
            pdf_file = gr.File()

            def export_portfolio_pdf(assets_selected, weight):
                if not assets_selected:
                    return None

                # gleiche Logik wie run_portfolio_sim
                w = {a: weight for a in assets_selected}
                s = sum(w.values())
                w = {k: v/s for k, v in w.items()}

                data = {a: load_asset_series(a) for a in assets_selected}
                result = simulate_portfolio(data, w)
                stats = portfolio_stats(result["portfolio"])
                fig = plot_portfolio(result["portfolio"])

                stats_df = pd.DataFrame([stats])

                filename = "/tmp/portfolio_report.pdf"
                with PdfPages(filename) as pdf:
                    draw_portfolio_page(pdf, fig, stats_df, w)

                return filename

            pdf_button.click(
                export_portfolio_pdf,
                [portfolio_assets, weights],
                pdf_file
            )

            # --- ETF Länder-Check (automatisch eingefügt) ---
            with gr.Tab("ETF Länder-Check"):
                country_input = gr.Textbox(
                    value="Deutschland (DAX), USA (S&P 500), Frankreich, UK, Japan",
                    label="Länder (Komma-getrennt)"
                )
                check_btn = gr.Button("Prüfen")
                result_md = gr.Markdown("Ergebnis erscheint hier")

                def run_country_check(text):
                    countries = [c.strip() for c in text.split(",") if c.strip()]
                    from core.ui_helpers import countries_with_etfs
                    res = countries_with_etfs(countries)
                    lines = ["**Länder → Region → Anzahl ETFs → Ticker**\n"]
                    for c in countries:
                        info = res.get(c, {"tickers": [], "count": 0, "region": "Unbekannt"})
                        if info["count"]:
                            lines.append(f"- **{c}** ({info['region']}): {info['count']} → {', '.join(info['tickers'])}")
                        else:
                            lines.append(f"- **{c}** ({info['region']}): _keine ETFs in der DB_")
                    return "\n\n".join(lines)

                check_btn.click(run_country_check, inputs=[country_input], outputs=[result_md])
            # --- Ende ETF Länder-Check ---


    return demo
