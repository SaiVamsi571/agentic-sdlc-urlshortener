"""
FastAPI Application Entry Point for URL Shortener Service.
Embeds Sliding-Window Rate Limiting Middleware, CORS, and Router Mounting.
"""

from __future__ import annotations
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.constants import SERVICE_DESCRIPTION, SERVICE_TITLE
from src.service.config import SETTINGS
from src.service.core.rate_limiter import SlidingWindowRateLimiter
from src.service.routers import analytics, url

_DEFAULT_CLIENT_IP = "127.0.0.1"


def create_app(db_path: str | None = None) -> FastAPI:
    """Creates and configures the URL Shortener FastAPI application."""
    app = FastAPI(
        title=SERVICE_TITLE,
        version="1.0.0",
        description=SERVICE_DESCRIPTION,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    rate_limiter = SlidingWindowRateLimiter(
        default_limit=SETTINGS.rate_limit_write_per_min,
        window_seconds=60,
    )

    @app.middleware("http")
    async def rate_limiting_middleware(request: Request, call_next):
        """Apply sliding-window rate limiting based on path & method."""
        client_ip = request.client.host if request.client else _DEFAULT_CLIENT_IP
        is_write = request.method == "POST" and "/shorten" in request.url.path
        limit = (
            SETTINGS.rate_limit_write_per_min
            if is_write
            else SETTINGS.rate_limit_read_per_min
        )

        allowed, remaining, reset_in = rate_limiter.is_allowed(client_ip, limit=limit)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": (
                        f"Allowed maximum {limit} requests per minute. "
                        f"Try again in {reset_in} seconds."
                    ),
                    "reset_in_seconds": reset_in,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "Retry-After": str(int(reset_in) + 1),
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Liveness probe for the URL Shortener service."""
        return {"status": "HEALTHY", "service": SETTINGS.service_name}

    # Mount routers: system/analytics first, url redirect catch-all last
    app.include_router(analytics.router)
    app.include_router(url.router)

    return app


app = create_app()
