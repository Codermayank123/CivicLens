"""
CivicLens Backend — FastAPI Application Entry Point

Sets up the FastAPI app with:
- CORS middleware
- Security headers
- Request ID tracking
- Structured logging
- Global exception handlers
- API router mounting
- Health check endpoint
"""

from __future__ import annotations

import uuid
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.rate_limit import limiter
from app.database import get_database, init_db, close_db
from app.services.deadline_service import run_deadline_scan
from app.exceptions import CivicLensError

settings = get_settings()
logger = structlog.get_logger()


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info("civiclens.startup", env=settings.APP_ENV, debug=settings.DEBUG)
    await init_db()
    deadline_task = asyncio.create_task(_deadline_loop())
    yield
    deadline_task.cancel()
    try:
        await deadline_task
    except asyncio.CancelledError:
        pass
    await close_db()
    logger.info("civiclens.shutdown")


async def _deadline_loop() -> None:
    """Run deadline automation without making request handlers responsible for it."""
    interval = max(30, get_settings().DEADLINE_SCAN_INTERVAL_SECONDS)
    while True:
        try:
            await run_deadline_scan(get_database())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("deadline_scan.failed", error=str(exc))
        await asyncio.sleep(interval)


# ── App Factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-Powered, Accessible and Offline-First Civic Issue Resolution Platform. "
            "Report public infrastructure problems, track resolutions, and verify fixes."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Middleware ────────────────────────────────────────────────────────
    _setup_middleware(app)

    # ── Exception Handlers ───────────────────────────────────────────────
    _setup_exception_handlers(app)

    # ── Routes ───────────────────────────────────────────────────────────
    _setup_routes(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Register all middleware."""

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=(self)"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response

    # Request logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next: Any) -> Any:
        log = logger.bind(
            request_id=getattr(request.state, "request_id", "unknown"),
            method=request.method,
            path=request.url.path,
        )
        log.info("request.start")
        response = await call_next(request)
        log.info("request.end", status_code=response.status_code)
        return response


def _setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(CivicLensError)
    async def civiclens_error_handler(
        request: Request, exc: CivicLensError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "civiclens.error",
            error_code=exc.error_code,
            message=exc.message,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        # Never expose internal error details to the client
        logger.exception(
            "civiclens.unhandled_error",
            error_type=type(exc).__name__,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
                "request_id": request_id,
            },
        )


def _setup_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, Any]:
        """Liveness probe — process is running."""
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/health/ready", tags=["System"], response_model=None)
    async def readiness_check() -> JSONResponse | dict[str, Any]:
        """Readiness probe — dependencies required to serve traffic."""
        from app.core.health import readiness_report

        checks = await readiness_report(settings)
        ready = all(checks.values())
        payload = {
            "status": "ready" if ready else "degraded",
            "service": settings.APP_NAME,
            "checks": checks,
        }
        if not ready:
            return JSONResponse(status_code=503, content=payload)
        return payload

    from app.api.v1.router import api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")


# ── Application Instance ─────────────────────────────────────────────────────
app = create_app()
