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


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def app():

    presets_all = load_presets()
    countries = list(presets_all.keys())  # <-- dynamisch aus JSON

    with gr.Blocks() as demo:

        # ---------------- Radar Overlay ----------------
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
            benchmark = gr.Checkbox(label="SPY als Benchmark hinzufügen")
            btn = gr.Button("Radar anzeigen")

            # Ausgabe
            radar_plot = gr.Plot(label="Radar-Chart")
            radar_table = gr.Dataframe(label="Kennzahlen", interactive=False)
            lexikon_table = gr.Dataframe(label="Lexikon", interactive=False)

            # --- Cluster Analyse UI ---
            cluster_btn = gr.Button("Cluster-Analyse")
            cluster_table = gr.Dataframe(label="Cluster-Ergebnis", interactive=False)

            def build_stock_radar(tickers, benchmark):

                if not tickers:
                    return None, pd.DataFrame(), pd.DataFrame()

                rows = []
                for t in tickers:
                    entry = {"ticker": t, "name": t, "region": "Global", "asset_class": "Equity"}
                    metrics = get_metrics(entry)
                    fund = get_fundamentals(t)
                    metrics.update(fund)
                    rows.append(metrics)

                if benchmark:
                    spy_entry = {"ticker": "SPY", "name": "SPY", "region": "USA", "asset_class": "Equity"}
                    spy_metrics = get_metrics(spy_entry)
                    rows.append(spy_metrics)

                rows = normalize_metrics(rows)

                fig = plot_radar_plotly(rows)
                lex = get_lexicon("aktien")

                return fig, pd.DataFrame(rows), pd.DataFrame(lex)


            def run_cluster(tickers):
                if not tickers:
                    return pd.DataFrame({"Fehler": ["Bitte mindestens eine Aktie auswählen"]})

                rows = []
                for t in tickers:
                    entry = {"ticker": t, "name": t, "region": "Global", "asset_class": "Equity"}
                    metrics = get_metrics(entry)
                    fund = get_fundamentals(t)
                    metrics.update(fund)
                    rows.append(metrics)

                df = cluster_stocks(rows)
                return df
            btn.click(build_stock_radar, inputs=[aktien, benchmark], outputs=[radar_plot, radar_table, lexikon_table])
            cluster_btn.click(run_cluster, inputs=[aktien], outputs=[cluster_table])

        with gr.Tab("Radar Länder"):

            region_map = {
                "USA": ["SPY"],
                "Europa": ["EUNA.DE"],
                "Japan": ["EWJ"],
                "China": ["FXI"],
                "Emerging Markets": ["EEM"],
            }

            regions = gr.CheckboxGroup(choices=list(region_map.keys()), label="Regionen auswählen")
            radar_plot = gr.Plot()
            radar_table = gr.Dataframe(interactive=False)
            lexikon_table = gr.Dataframe(interactive=False)

            def build_region_radar(selected):
                if not selected:
                    return None, pd.DataFrame(), pd.DataFrame()

                db = load_etf_db()
                rows = []

                for r in selected:
                    for t in region_map[r]:
                        entry = next((e for e in db if e["ticker"] == t), None)
                        if entry:
                            m = get_metrics(entry)
                            if m:
                                m["Ticker"] = r
                                rows.append(m)
                            break
                if not rows:
                    return None, pd.DataFrame(), pd.DataFrame()

                fig = plot_radar(rows)
                lex = get_lexicon("laender")

                return fig, pd.DataFrame(rows), pd.DataFrame(lex)

            regions.change(build_region_radar, inputs=[regions], outputs=[radar_plot, radar_table, lexikon_table])

        with gr.Tab("Radar Portfolio"):

            db = load_etf_db()
            all_etfs = [e["ticker"] for e in db]

            tickers = gr.CheckboxGroup(choices=all_etfs, label="Portfolio-ETFs")
            weights = gr.Textbox(label="Gewichte (optional, z.B. 0.5,0.3,0.2)")
            btn = gr.Button("Portfolio-Radar")
            radar_plot = gr.Plot()
            radar_table = gr.Dataframe(interactive=False)
            lexikon_table = gr.Dataframe(interactive=False)

            def build_portfolio_radar(sel, w_str):
                import pandas as pd

                if not sel:
                    return None, pd.DataFrame(), pd.DataFrame()

                # Auto-Gewichte
                if not w_str.strip():
                    ws = [1 / len(sel)] * len(sel)
                else:
                    try:
                        ws = [float(x.strip()) for x in w_str.split(",") if x.strip()]
                    except:
                        return None, pd.DataFrame({"Fehler": ["Ungültige Gewichte"]}), pd.DataFrame()

                    if len(ws) != len(sel):
                        ws = [1 / len(sel)] * len(sel)

                s = sum(ws)
                ws = [w / s for w in ws]

                rows = []
                for t in sel:
                    entry = next((e for e in db if e["ticker"] == t), None)
                    if entry:
                        m = get_metrics(entry)
                        if m:
                            rows.append(m)

                if not rows:
                    return None, pd.DataFrame(), pd.DataFrame()

                portfolio_row = aggregate_portfolio(rows, ws)
                fig = plot_radar([portfolio_row])
                lex = get_lexicon("portfolio")

                return fig, pd.DataFrame([portfolio_row]), pd.DataFrame(lex)

            btn.click(build_portfolio_radar, inputs=[tickers, weights], outputs=[radar_plot, radar_table, lexikon_table])

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
