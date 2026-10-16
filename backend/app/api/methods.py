"""Method catalogue endpoints (thin: all logic lives in the registry)."""

from fastapi import APIRouter

from app.core import registry
from app.core.models import MethodCatalog, MethodMeta

router = APIRouter(tags=["methods"])


@router.get("/methods", response_model=MethodCatalog, summary="List chapters and methods")
def list_methods() -> MethodCatalog:
    """Return every registered method plus the six chapter cards."""
    return registry.build_catalog()


@router.get("/methods/{method_id}", response_model=MethodMeta, summary="Method metadata")
def get_method(method_id: str) -> MethodMeta:
    """Return the full metadata (schema, theory, pseudocode) for one method."""
    return registry.get_entry(method_id).meta
