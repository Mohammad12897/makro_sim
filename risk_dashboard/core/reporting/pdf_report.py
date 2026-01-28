#core/preporting/pdf_report.py
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Color Emoji']

def draw_footer(ax, text="MakroSim – Risikoanalyse"):
    ax.text(0.5, 0.02, text, ha="center", fontsize=8)


def draw_title_page(pdf, land, logo_path: str | None = None):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4
    ax.axis("off")

    today = datetime.date.today().strftime("%d.%m.%Y")

    ax.text(0.5, 0.8, f"Risikoanalyse – {land}", ha="center", fontsize=28, weight="bold")
    ax.text(0.5, 0.72, "Makroökonomische Szenarien & Risikoindikatoren", ha="center", fontsize=16)
    ax.text(0.5, 0.64, f"Erstellt am: {today}", ha="center", fontsize=12)

    if logo_path:
        try:
            img = plt.imread(logo_path)
            ax.imshow(img, extent=[0.65, 0.95, 0.8, 0.95], aspect="auto")
        except Exception:
            pass

    draw_footer(ax)
    pdf.savefig(fig)
    plt.close(fig)


def draw_executive_summary(pdf, summary_text: str):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    ax.text(0.05, 0.95, "Executive Summary", fontsize=20, weight="bold", va="top")
    ax.text(0.05, 0.9, summary_text, fontsize=12, va="top", wrap=True)

    draw_footer(ax)
    pdf.savefig(fig)
    plt.close(fig)


def draw_risk_traffic_light(pdf, ampel_text: str):
    fig, ax = plt.subplots(figsize=(8.27, 3))
    ax.axis("off")

    if "Geringes Risiko" in ampel_text:
        color = "#2ca02c"
    elif "Mittleres Risiko" in ampel_text:
        color = "#ffbf00"
    else:
        color = "#d62728"

    circle = plt.Circle((0.15, 0.5), 0.1, color=color)
    ax.add_patch(circle)

    ax.text(0.35, 0.5, f"Risiko‑Ampel: {ampel_text}", fontsize=16, va="center")

    draw_footer(ax)
    pdf.savefig(fig)
    plt.close(fig)


def draw_radar_page(pdf, radar_fig):
    pdf.savefig(radar_fig)
    plt.close(radar_fig)


def draw_table_page(pdf, df):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellLoc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    draw_footer(ax)
    pdf.savefig(fig)
    plt.close(fig)


def draw_storyline_page(pdf, storyline_text: str):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    ax.text(0.05, 0.95, "Storyline", fontsize=20, weight="bold", va="top")
    ax.text(0.05, 0.9, storyline_text, fontsize=12, wrap=True, va="top")

    draw_footer(ax)
    pdf.savefig(fig)
    plt.close(fig)


def draw_heatmap_page(pdf, heatmap_fig):
    pdf.savefig(heatmap_fig)
    plt.close(heatmap_fig)


def draw_portfolio_page(pdf, fig_portfolio, stats_df, weights_dict):
    # Seite: Portfolio-Performance + Kennzahlen + Gewichte
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    ax.text(0.05, 0.95, "Portfolio-Analyse", fontsize=20, weight="bold", va="top")

    # Platz für eingebettete Performance-Grafik
    # Wir speichern die Figur separat in den PDF-Stream
    pdf.savefig(fig_portfolio)

    # Neue Seite für Kennzahlen + Gewichte
    fig2, ax2 = plt.subplots(figsize=(8.27, 11.69))
    ax2.axis("off")

    ax2.text(0.05, 0.95, "Portfolio-Kennzahlen", fontsize=16, weight="bold", va="top")
    ax2.table(
        cellText=stats_df.values,
        colLabels=stats_df.columns,
        loc="upper left",
        cellLoc="center"
    )

    ax2.text(0.05, 0.5, "Gewichtungen", fontsize=16, weight="bold", va="top")
    weights_text = "\n".join([f"{k}: {v:.1%}" for k, v in weights_dict.items()])
    ax2.text(0.05, 0.45, weights_text, fontsize=12, va="top")

    pdf.savefig(fig2)
    plt.close(fig2)

def create_pdf_report(
    filename,
    land,
    radar_fig,
    df,
    storyline_text,
    ampel_text,
    summary_text,
    heatmap_fig=None,
    logo_path: str | None = None,
):
    with PdfPages(filename) as pdf:
        draw_title_page(pdf, land, logo_path=logo_path)
        draw_executive_summary(pdf, summary_text)
        draw_risk_traffic_light(pdf, ampel_text)
        draw_radar_page(pdf, radar_fig)
        draw_table_page(pdf, df)
        draw_storyline_page(pdf, storyline_text)

        if heatmap_fig is not None:
            draw_heatmap_page(pdf, heatmap_fig)
