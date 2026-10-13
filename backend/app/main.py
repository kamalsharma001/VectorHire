"""
VectorHire FastAPI Application Entrypoint.
Initializes FastAPI, mounts CORS middleware, configures typed exception handlers,
and registers public API routes.
"""

# Ensure compatibility between Starlette 1.x Router and FastAPI 0.115 APIRouter
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__

    def _compat_router_init(self, *args, on_startup=None, on_shutdown=None, **kwargs):
        _orig_router_init(self, *args, **kwargs)
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

    starlette.routing.Router.__init__ = _compat_router_init
except Exception:
    pass

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import router
from app.core.config import get_settings
from app.core.exceptions import (
    DocumentProcessingError,
    InvalidEvidenceStateError,
    ProviderAPIError,
    RubricValidationError,
    VectorHireError,
)

logger = logging.getLogger("vectorhire")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("Initializing %s API v1.1.0 in environment (Debug=%s)...", settings.APP_NAME, settings.DEBUG)
    yield
    logger.info("Shutting down %s API...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Factory function for FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} Resume Intelligence API",
        version="1.1.0",
        description=(
            "In-memory, multi-agent decision support platform for job-specific resume screening, "
            "verifiable evidence provenance, and deterministic rubric-based candidate comparison."
        ),
        lifespan=lifespan,
    )
    app.max_body_size = None

    # CORS configuration
    base_origins = [
        "https://vectorhire-platform.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    configured_origins = [
        o.strip()
        for o in settings.CORS_ORIGINS.split(",")
        if o.strip() and o.strip() != "*"
    ]
    cors_origins = list(dict.fromkeys(base_origins + configured_origins))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain exception handlers
    @app.exception_handler(DocumentProcessingError)
    async def document_processing_handler(request: Request, exc: DocumentProcessingError):
        logger.warning("DocumentProcessingError on %s: %s", request.url.path, exc.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "DocumentProcessingError", "message": exc.message},
        )

    @app.exception_handler(RubricValidationError)
    async def rubric_validation_handler(request: Request, exc: RubricValidationError):
        logger.warning("RubricValidationError on %s: %s", request.url.path, exc.message)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "RubricValidationError", "message": exc.message},
        )

    @app.exception_handler(ProviderAPIError)
    async def provider_api_handler(request: Request, exc: ProviderAPIError):
        logger.error("ProviderAPIError on %s: %s", request.url.path, exc.message)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "ProviderAPIError",
                "message": "Upstream AI provider error. The request could not be completed at this time.",
            },
        )

    @app.exception_handler(VectorHireError)
    async def domain_error_handler(request: Request, exc: VectorHireError):
        logger.warning("VectorHireError on %s: %s", request.url.path, exc.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": type(exc).__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s: %s", request.url.path, str(exc)[:200], exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during processing.",
            },
        )

    # Register API routes
    app.include_router(router)

    return app


app = create_app()
