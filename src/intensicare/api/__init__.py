"""Rotas da API v1."""

from intensicare.api.vitals import router as vitals_router
from intensicare.api.patients import router as patients_router

__all__ = ["vitals_router", "patients_router"]
