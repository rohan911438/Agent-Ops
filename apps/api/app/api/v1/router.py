from fastapi import APIRouter

from app.api.v1 import (
    activity,
    agents,
    auth,
    connectors,
    marketplace,
    overview,
    pricing,
    recommendations,
    scans,
    settings,
    verification,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(recommendations.router)
api_router.include_router(activity.router)
api_router.include_router(overview.router)
api_router.include_router(settings.router)
api_router.include_router(connectors.router)
api_router.include_router(scans.router)
api_router.include_router(verification.router)
api_router.include_router(pricing.router)
api_router.include_router(marketplace.router)
