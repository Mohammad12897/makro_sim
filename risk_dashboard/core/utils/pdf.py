# core/utils/pdf.py

from fpdf import FPDF
import plotly.io as pio
import io
import re
import tempfile
import os


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, self.title, ln=True, align="L")
        self.ln(5)


def extract_svg_from_html(html: str) -> bytes:
    """
    Extrahiert das <svg>-Element aus Plotly-HTML.
    """
    match = re.search(r"(<svg.*?</svg>)", html, re.DOTALL)
    if not match:
        raise ValueError("SVG konnte nicht aus Plotly HTML extrahiert werden.")
    return match.group(1).encode("utf-8")


def export_radar_pdf(fig, metrics: dict, title: str, mode: str) -> str:
    """
    Erzeugt ein PDF mit Radar-Plot und Kennzahlen.
    - Kein Kaleido
    - Kein reportlab
    - Rückgabe: Pfad zu einer temporären PDF-Datei (für gr.File(type="filepath"))
    """

    # 1) Plotly-HTML mit eingebettetem JS erzeugen → garantiert SVG
    html = pio.to_html(
        fig,
        include_plotlyjs=True,
        full_html=False
    )

    # 2) SVG extrahieren
    svg_bytes = extract_svg_from_html(html)
    svg_stream = io.BytesIO(svg_bytes)

    # 3) PDF erzeugen
    pdf = PDF()
    pdf.set_title(f"Radar-Analyse: {title} ({mode})")
    pdf.add_page()

    # 4) SVG einfügen
    pdf.image(svg_stream, x=10, y=30, w=180)

    # 5) Kennzahlen
    pdf.ln(120)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Kennzahlen:", ln=True)

    pdf.set_font("Helvetica", size=10)
    for k, v in metrics.items():
        if isinstance(v, (int, float, str)):
            pdf.cell(0, 8, f"{k}: {v}", ln=True)

    # 6) Temporäre Datei schreiben und Pfad zurückgeben
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    tmp.close()

    return tmp.name
