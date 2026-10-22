"""
Analytics and Observability Endpoints for URL Shortener Service.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from src.service.models import AnalyticsSummary, SystemStats
from src.service.routers.url import get_service
from src.service.service import URLNotFoundError, URLShortenerService

router = APIRouter(prefix="/api/v1", tags=["Analytics & System"])

@router.get(
    "/analytics/{short_code}",
    response_model=AnalyticsSummary,
    summary="Get Detailed Click Analytics"
)
async def get_analytics(
    short_code: str,
    svc: URLShortenerService = Depends(get_service)
):
    try:
        return svc.get_analytics(short_code)
    except URLNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analytics available for non-existent short code '{short_code}'"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/system/stats",
    response_model=SystemStats,
    summary="Get System Health and Aggregate Statistics"
)
async def get_system_stats(
    svc: URLShortenerService = Depends(get_service)
):
    try:
        return svc.get_system_stats()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
