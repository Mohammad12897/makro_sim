#core/reporting/pdf_report.py
from fpdf import FPDF

def generate_portfolio_report(metrics, figs, scenario_df, filename="portfolio_report.pdf"):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="Portfolio Analyse Report", ln=True)

    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(200, 10, txt="Kennzahlen:", ln=True)

    for k, v in metrics.items():
        pdf.cell(200, 8, txt=f"{k}: {v}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Szenario-Vergleich:", ln=True)

    for idx, row in scenario_df.iterrows():
        pdf.cell(200, 8, txt=str(row.values), ln=True)

    pdf.output(filename)
