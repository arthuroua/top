from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.schemas import AdvisorReportRead


def _draw_line(pdf: canvas.Canvas, text: str, x: float, y: float, max_width: float) -> float:
    words = text.split(" ")
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if pdf.stringWidth(trial, "Helvetica", 10) <= max_width:
            current = trial
        else:
            pdf.drawString(x, y, current)
            y -= 5 * mm
            current = word
    if current:
        pdf.drawString(x, y, current)
        y -= 5 * mm
    return y


def build_report_pdf(report: AdvisorReportRead) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    left = 18 * mm
    right = 190 * mm
    y = 275 * mm

    pdf.setTitle(f"Advisor Report {report.id}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, "Car Import Advisor Report")
    y -= 8 * mm

    pdf.setFont("Helvetica", 10)
    y = _draw_line(pdf, f"Report ID: {report.id}", left, y, right - left)
    y = _draw_line(pdf, f"VIN: {report.vin}", left, y, right - left)
    y = _draw_line(pdf, f"Created at: {report.created_at.isoformat()}", left, y, right - left)

    y -= 2 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, y, "Advisor Output")
    y -= 7 * mm

    pdf.setFont("Helvetica", 10)
    y = _draw_line(pdf, f"Total no-bid costs: ${report.result.total_no_bid_usd:.2f}", left, y, right - left)
    y = _draw_line(pdf, f"Max bid (base): ${report.result.max_bid_usd:.2f}", left, y, right - left)

    for scenario in report.result.scenarios:
        y = _draw_line(pdf, f"Scenario {scenario.name}: ${scenario.max_bid_usd:.2f}", left, y, right - left)

    y -= 2 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, y, "Assumptions")
    y -= 7 * mm
    pdf.setFont("Helvetica", 10)

    assumptions = report.assumptions
    fields = [
        ("Target sell price", assumptions.target_sell_price_usd),
        ("Desired margin", assumptions.desired_margin_usd),
        ("Fees", assumptions.fees_usd),
        ("Logistics", assumptions.logistics_usd),
        ("Customs", assumptions.customs_usd),
        ("Repair", assumptions.repair_usd),
        ("Local costs", assumptions.local_costs_usd),
        ("Risk buffer", assumptions.risk_buffer_usd),
    ]

    for label, value in fields:
        y = _draw_line(pdf, f"{label}: ${value:.2f}", left, y, right - left)
        if y < 20 * mm:
            pdf.showPage()
            y = 275 * mm
            pdf.setFont("Helvetica", 10)

    pdf.save()
    return buffer.getvalue()
