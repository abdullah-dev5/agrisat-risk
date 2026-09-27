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
            f"Growth stage: day {assessment.get('days_since_sowing', 'N/A')}",
            f"Index value: {assessment.get('index_value', 'N/A')}",
        ])
        if assessment.get("rainfall_mm") is not None:
            lines.append(
                f"Rainfall: {assessment['rainfall_mm']:.1f} mm "
                f"({assessment.get('rainfall_anomaly_pct', 0):+.0f}% vs 5-yr avg)"
            )
        readings = detail.get("vegetation_readings") or []
        if readings:
            latest = readings[-1]
            lines.extend([
                "",
                f"Latest scene: {latest.get('acquisition_date')} ({latest.get('data_tier', 'N/A')})",
                f"Latest NDVI: {latest.get('ndvi', 'N/A')}",
            ])
        lines.extend([
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


def _current_assessments_by_field(sb, field_ids: list[str], columns: str) -> dict[str, dict]:
    """Batch-load current risk assessments for a set of fields (avoids one query per field)."""
    if not field_ids:
        return {}
    resp = (
        sb.table("risk_assessments")
        .select(columns)
        .in_("field_id", field_ids)
        .eq("is_current", True)
        .execute()
    )
    return {row["field_id"]: row for row in resp.data}


def generate_portfolio_csv(institution_id: str) -> str:
    sb = get_supabase_admin()
    fields = sb.table("fields").select("*").eq("institution_id", institution_id).eq("status", "active").execute().data
    assessments = _current_assessments_by_field(
        sb, [f["id"] for f in fields], "field_id, risk_tier, z_score, explanation"
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "field_id", "name", "crop_type", "sowing_date", "area_hectares",
        "farmer_ref_id", "loan_ref_id", "risk_tier", "z_score", "explanation",
    ])

    for f in fields:
        a = assessments.get(f["id"], {})
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


def generate_portfolio_pdf(institution_id: str) -> bytes:
    sb = get_supabase_admin()
    fields = (
        sb.table("fields")
        .select("*")
        .eq("institution_id", institution_id)
        .eq("status", "active")
        .order("created_at")
        .execute()
        .data
        or []
    )
    assessments = _current_assessments_by_field(
        sb, [f["id"] for f in fields], "field_id, risk_tier, z_score, explanation"
    )

    risk_counts: dict[str, int] = {
        "normal": 0,
        "watch": 0,
        "elevated": 0,
        "high": 0,
        "insufficient_data": 0,
    }
    rows: list[tuple[str, str, str, str, str]] = []

    for f in fields:
        a = assessments.get(f["id"], {})
        tier = a.get("risk_tier", "normal")
        risk_counts[tier] = risk_counts.get(tier, 0) + 1
        label = f.get("name") or f.get("farmer_ref_id") or f["id"][:8]
        rows.append((
            label[:28],
            str(f.get("crop_type", "")),
            str(f.get("sowing_date", "")),
            f"{f.get('area_hectares', '—')} ha",
            tier.upper(),
        ))

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "AgriSat Risk — Portfolio Summary")
    y -= 1.2 * cm

    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    y -= 0.7 * cm
    c.drawString(2 * cm, y, f"Active fields: {len(fields)}")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Risk distribution")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    for tier, count in risk_counts.items():
        if count:
            c.drawString(2.2 * cm, y, f"{tier.replace('_', ' ').title()}: {count}")
            y -= 0.5 * cm
    y -= 0.4 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Field register")
    y -= 0.6 * cm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2 * cm, y, "Field")
    c.drawString(7 * cm, y, "Crop")
    c.drawString(9.5 * cm, y, "Sowing")
    c.drawString(12.5 * cm, y, "Area")
    c.drawString(15 * cm, y, "Risk")
    y -= 0.45 * cm
    c.setFont("Helvetica", 9)

    for label, crop, sowing, area, tier in rows:
        if y < 2.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 9)
        c.drawString(2 * cm, y, label)
        c.drawString(7 * cm, y, crop[:10])
        c.drawString(9.5 * cm, y, sowing[:10])
        c.drawString(12.5 * cm, y, area[:12])
        c.drawString(15 * cm, y, tier[:12])
        y -= 0.42 * cm

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(2 * cm, 1.5 * cm, "Decision-support only — not an automated loan or claims decision.")
    c.save()
    return buffer.getvalue()
