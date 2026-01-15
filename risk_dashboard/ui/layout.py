# ui/layout.py

import gradio as gr


# ---------------------------------------------------------
# Standard-Container für Sektionen
# ---------------------------------------------------------

def section(title: str):
    """
    Erstellt eine optisch klare Sektion mit Überschrift.
    """
    gr.Markdown(f"## {title}")


def sub_section(title: str):
    """
    Kleinere Untersektion.
    """
    gr.Markdown(f"### {title}")


# ---------------------------------------------------------
# Layout-Blöcke für Tabs
# ---------------------------------------------------------

def layout_country_profile():
    """
    Layout für den Tab 'Länderprofil'.
    """
    section("Länderprofil")
    with gr.Row():
        with gr.Column(scale=1):
            country = gr.Dropdown(label="Land auswählen")
            btn_radar = gr.Button("Radar anzeigen")
            btn_story = gr.Button("Storyline erzeugen")
            btn_ews = gr.Button("EWS anzeigen")

        with gr.Column(scale=2):
            radar_out = gr.Plot()
            storyline_out = gr.Markdown()
            ews_out = gr.Markdown()

    return {
        "country": country,
        "btn_radar": btn_radar,
        "btn_story": btn_story,
        "btn_ews": btn_ews,
        "radar_out": radar_out,
        "storyline_out": storyline_out,
        "ews_out": ews_out,
    }


def layout_comparison():
    """
    Layout für den Tab 'Vergleich'.
    """
    section("Ländervergleich")
    multi_select = gr.CheckboxGroup(label="Länder auswählen")
    btn_multi = gr.Button("Vergleich anzeigen")
    multi_radar_out = gr.Plot()

    return {
        "multi_select": multi_select,
        "btn_multi": btn_multi,
        "multi_radar_out": multi_radar_out,
    }


def layout_heatmaps():
    """
    Layout für den Tab 'Heatmaps'.
    """
    section("Heatmaps")

    with gr.Row():
        with gr.Column():
            btn_heat = gr.Button("Risiko-Heatmap")
            heat_out = gr.Dataframe()

        with gr.Column():
            btn_pol = gr.Button("Politische Abhängigkeit")
            pol_out = gr.Dataframe()

    with gr.Row():
        with gr.Column():
            btn_auto = gr.Button("Strategische Autonomie")
            auto_out = gr.Dataframe()

        with gr.Column():
            btn_comb = gr.Button("Kombinierte Analyse")
            comb_out = gr.Dataframe()

    return {
        "btn_heat": btn_heat,
        "heat_out": heat_out,
        "btn_pol": btn_pol,
        "pol_out": pol_out,
        "btn_auto": btn_auto,
        "auto_out": auto_out,
        "btn_comb": btn_comb,
        "comb_out": comb_out,
    }


def layout_scenarios():
    """
    Layout für den Tab 'Szenarien'.
    """
    section("Szenarioanalyse")

    with gr.Row():
        with gr.Column(scale=1):
            country_s = gr.Dropdown(label="Land auswählen")
            scenario_s = gr.Dropdown(label="Szenario auswählen")
            btn_scen = gr.Button("Szenario ausführen")
            btn_decision = gr.Button("Decision Support")

        with gr.Column(scale=2):
            scen_radar_out = gr.Plot()
            scen_decision_out = gr.Markdown()

    return {
        "country_s": country_s,
        "scenario_s": scenario_s,
        "btn_scen": btn_scen,
        "btn_decision": btn_decision,
        "scen_radar_out": scen_radar_out,
        "scen_decision_out": scen_decision_out,
    }


def layout_cluster():
    """
    Layout für den Tab 'Cluster'.
    """
    section("Clusteranalyse")
    btn_cluster = gr.Button("Cluster berechnen")
    cluster_out = gr.Dataframe()

    return {
        "btn_cluster": btn_cluster,
        "cluster_out": cluster_out,
    }
