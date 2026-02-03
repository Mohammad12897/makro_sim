#core/utils/pdf.py
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from plotly.io import to_image


def export_radar_pdf(fig, metrics: dict, title: str, mode: str):
    """
    Erzeugt ein PDF mit:
    - Titel
    - Radar-Grafik
    - Kennzahlen-Tabelle (kurz)
    Gibt BytesIO zurück, das du direkt an gr.File geben kannst.
    """

    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Radar-Analyse: {title} ({mode})")

    # Plotly-Figur als PNG
    img_bytes = to_image(fig, format="png", width=800, height=600)
    img_buffer = io.BytesIO(img_bytes)

    # Bild einfügen
    c.drawImage(img_buffer, 50, height - 650, width=500, height=500, preserveAspectRatio=True, mask='auto')

    # Kennzahlen kurz darunter
    c.setFont("Helvetica", 10)
    y = height - 680
    for k, v in metrics.items():
        if isinstance(v, (int, float, str)):
            c.drawString(50, y, f"{k}: {v}")
            y -= 12
            if y < 50:
                c.showPage()
                y = height - 50

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
