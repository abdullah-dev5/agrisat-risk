"""PDF and CSV report generation (FR-7.x)."""

import csv
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.core.supabase_client import get_supabase_admin
from app.services.field_service import get_field_detail


def generate_field_pdf(field_id: str, institution_id: str) -> bytes:
    detail = get_field_detail(field_id, institution_id)
    field = detail["field"]
    assessment = detail.get("current_assessment")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "AgriSat Risk — Field Report")
    y -= 1 * cm

    c.setFont("Helvetica", 11)
    lines = [
        f"Field: {field.name or field.id}",
        f"Crop: {field.crop_type} | Sowing: {field.sowing_date}",
        f"Area: {field.area_hectares or 'N/A'} ha | District: {field.pilot_district}",
        f"Farmer ref: {field.farmer_ref_id or '—'} | Loan ref: {field.loan_ref_id or '—'}",
        "",
        "Decision-support information only — not an automated loan or claims decision.",
    ]
    if assessment:
        lines.extend([
            "",
            f"Risk tier: {assessment['risk_tier'].upper()}",
            f"Z-score: {assessment.get('z_score', 'N/A')}",
            f"Data tier: {assessment.get('primary_data_tier', 'N/A')}",
            "",
            "Explanation:",
            assessment["explanation"],
        ])

    for line in lines:
        c.drawString(2 * cm, y, line[:100])
        y -= 0.55 * cm
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2 * cm, 1.5 * cm, f"Generated {datetime.utcnow().isoformat()}Z")
    c.save()
    return buffer.getvalue()


def generate_portfolio_csv(institution_id: str) -> str:
    sb = get_supabase_admin()
    fields = sb.table("fields").select("*").eq("institution_id", institution_id).eq("status", "active").execute().data

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "field_id", "name", "crop_type", "sowing_date", "area_hectares",
        "farmer_ref_id", "loan_ref_id", "risk_tier", "z_score", "explanation",
    ])

    for f in fields:
        assessment = (
            sb.table("risk_assessments")
            .select("*")
            .eq("field_id", f["id"])
            .eq("is_current", True)
            .limit(1)
            .execute()
            .data
        )
        a = assessment[0] if assessment else {}
        writer.writerow([
            f["id"],
            f.get("name", ""),
            f["crop_type"],
            f["sowing_date"],
            f.get("area_hectares", ""),
            f.get("farmer_ref_id", ""),
            f.get("loan_ref_id", ""),
            a.get("risk_tier", ""),
            a.get("z_score", ""),
            a.get("explanation", ""),
        ])

    return output.getvalue()
