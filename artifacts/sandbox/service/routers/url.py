"""
URL Shortening, Redirection, and Metadata Endpoints.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from src.service.core.validator import ValidationError
from src.service.models import ShortenRequest, ShortenResponse
from src.service.service import AliasConflictError, URLExpiredError, URLNotFoundError, URLShortenerService

router = APIRouter(tags=["URL Operations"])

# Dependency provider (will be overridden or default instantiated)
_service_instance: URLShortenerService | None = None

def get_service() -> URLShortenerService:
    global _service_instance
    if _service_instance is None:
        _service_instance = URLShortenerService()
    return _service_instance

def set_service(svc: URLShortenerService) -> None:
    global _service_instance
    _service_instance = svc

@router.post(
    "/api/v1/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Shortened URL"
)
async def shorten_url(
    req: ShortenRequest,
    svc: URLShortenerService = Depends(get_service)
):
    try:
        return svc.shorten_url(req)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AliasConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")

@router.get(
    "/api/v1/url/{short_code}",
    response_model=ShortenResponse,
    summary="Get Short URL Details (without redirecting)"
)
async def get_url_details(
    short_code: str,
    svc: URLShortenerService = Depends(get_service)
):
    try:
        record = svc.repo.get_url(short_code)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Short code '{short_code}' not found")
        from src.service.config import SETTINGS
        return ShortenResponse(
            short_code=record.short_code,
            short_url=f"{SETTINGS.base_url}/{record.short_code}",
            original_url=record.original_url,
            created_at=record.created_at,
            expires_at=record.expires_at,
            is_custom_alias=bool(record.custom_alias),
            tags=record.tags
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/{short_code}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Redirect to Destination URL"
)
async def redirect_url(
    short_code: str,
    request: Request,
    svc: URLShortenerService = Depends(get_service)
):
    # Extract client IP and headers for analytics
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Respect Forwarded-For proxy headers if present
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    try:
        target_url, _ = svc.resolve_url(
            short_code=short_code,
            client_ip=client_ip,
            user_agent=user_agent,
            referrer=referrer
        )
        return RedirectResponse(url=target_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Short code '{short_code}' not found")
    except URLExpiredError as e:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
