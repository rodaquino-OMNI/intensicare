"""API v1 routes."""

from intensicare.api.v1.auth import router as auth_router
from intensicare.api.v1.alerts import router as alerts_router
from intensicare.api.vitals import router as vitals_router
from intensicare.api.patients import router as patients_router

__all__ = [
    "auth_router",
    "alerts_router",
    "vitals_router",
    "patients_router",
]
