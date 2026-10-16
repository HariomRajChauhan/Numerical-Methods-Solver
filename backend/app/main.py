"""FastAPI application factory for the Numerical Methods Solver backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import export, health, methods, solve
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.rate_limit import limiter


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load every solver module so the registry is complete before serving."""
    del app
    from app.solvers import load_all

    load_all()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Optional settings instance; defaults to the global cached one.

    Returns:
        The configured ASGI application.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = limiter
    register_exception_handlers(app)

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(methods.router, prefix=settings.api_prefix)
    app.include_router(solve.router, prefix=settings.api_prefix)
    app.include_router(export.router, prefix=settings.api_prefix)
    return app


app = create_app()
