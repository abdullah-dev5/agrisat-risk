from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.auth import AuthUser, get_current_user
from app.schemas.domain import PortfolioSummaryResponse
from app.services import field_service
from app.services.report_service import generate_field_pdf, generate_portfolio_csv

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/portfolio/summary", response_model=PortfolioSummaryResponse)
async def portfolio_summary(user: AuthUser = Depends(get_current_user)):
    fields = field_service.list_fields(user.institution_id)
    risk_counts: dict[str, int] = {
        "normal": 0, "watch": 0, "elevated": 0, "high": 0, "insufficient_data": 0,
    }
    flagged = []
    for f in fields:
        tier = f.current_risk_tier.value if f.current_risk_tier else "normal"
        risk_counts[tier] = risk_counts.get(tier, 0) + 1
        if tier in ("elevated", "high"):
            flagged.append(f)
    return PortfolioSummaryResponse(
        total_fields=len(fields),
        risk_counts=risk_counts,
        flagged_fields=flagged,
    )


@router.get("/field/{field_id}/pdf")
async def field_pdf(field_id: str, user: AuthUser = Depends(get_current_user)):
    pdf_bytes = generate_field_pdf(field_id, user.institution_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="field-{field_id}.pdf"'},
    )


@router.get("/portfolio/csv")
async def portfolio_csv(user: AuthUser = Depends(get_current_user)):
    csv_content = generate_portfolio_csv(user.institution_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="portfolio-summary.csv"'},
    )
