#core/reporting/pdf_report.py
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

def create_pdf_report(filename, radar_fig, table_df, storyline_text, ampel_text):
    with PdfPages(filename) as pdf:

        # Radar
        pdf.savefig(radar_fig)

        # Tabelle
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.axis("off")
        ax.table(cellText=table_df.values,
                 colLabels=table_df.columns,
                 loc="center")
        pdf.savefig(fig)

        # Storyline
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.axis("off")
        ax.text(0, 1, storyline_text, va="top", wrap=True)
        pdf.savefig(fig)

        # Ampel
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.axis("off")
        ax.text(0.1, 0.5, f"Risiko‑Ampel: {ampel_text}", fontsize=14)
        pdf.savefig(fig)
