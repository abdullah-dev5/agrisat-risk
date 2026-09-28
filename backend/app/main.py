import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import auth_routes, fields, health, reports
from app.core.config import get_settings
from app.core.middleware import SecurityHeadersMiddleware
from app.core.security import public_error_message

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="AgriSat Risk API",
    description="Satellite-based crop risk platform for agricultural lenders and insurers",
    version="0.2.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

if settings.trusted_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Registration-Secret"],
)

app.include_router(health.router)
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(fields.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.exception_handler(APIError)
async def supabase_api_error_handler(_request: Request, exc: APIError):
    if getattr(exc, "code", "") == "PGRST116":
        return JSONResponse(status_code=404, content={"detail": "Record not found"})
    logger.warning("Supabase API error: %s", exc)
    detail = str(exc) if settings.health_detail_enabled else "Database query failed"
    return JSONResponse(status_code=502, content={"detail": detail})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": public_error_message(exc)},
    )


@app.on_event("startup")
async def on_startup():
    from app.services.job_runner import start_reconciliation_loop

    start_reconciliation_loop(settings)

    if settings.is_production and settings.allow_open_registration:
        logger.warning(
            "ALLOW_OPEN_REGISTRATION is true in a production environment — "
            "anyone can self-register a new institution + admin account. "
            "Set ALLOW_OPEN_REGISTRATION=false after bootstrapping the first "
            "institution (see docs/PRODUCTION.md)."
        )


@app.on_event("shutdown")
async def on_shutdown():
    from app.services.job_runner import shutdown_executor, stop_reconciliation_loop

    stop_reconciliation_loop()
    shutdown_executor()


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
