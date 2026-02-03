# core/utils/pdf.py

from fpdf import FPDF
import plotly.io as pio
import io


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, self.title, ln=True, align="L")
        self.ln(5)


def export_radar_pdf(fig, metrics: dict, title: str, mode: str):
    """
    PDF-Export ohne Kaleido und ohne reportlab.
    Nutzt:
    - Plotly SVG Export (funktioniert ohne Kaleido)
    - FPDF2 für PDF-Erzeugung
    """

    # 1) Radar als SVG exportieren
    svg_bytes = fig.to_image(format="svg")
    svg_stream = io.BytesIO(svg_bytes)

    # 2) PDF erzeugen
    pdf = PDF()
    pdf.set_title(f"Radar-Analyse: {title} ({mode})")
    pdf.add_page()

    # 3) SVG einfügen
    pdf.image(svg_stream, x=10, y=30, w=180)

    # 4) Kennzahlen darunter
    pdf.ln(120)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Kennzahlen:", ln=True)

    pdf.set_font("Helvetica", size=10)
    for k, v in metrics.items():
        if isinstance(v, (int, float, str)):
            pdf.cell(0, 8, f"{k}: {v}", ln=True)

    # 5) PDF als Bytes zurückgeben
    output = pdf.output(dest="S").encode("latin1")
    return io.BytesIO(output)
