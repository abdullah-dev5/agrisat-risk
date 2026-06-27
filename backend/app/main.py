from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth_routes, fields, health, reports
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AgriSat Risk API",
    description="Satellite-based crop risk platform for agricultural lenders and insurers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(fields.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "pilot_crop": settings.pilot_crop,
        "pilot_district": settings.pilot_district,
    }
