from flask import Blueprint

from app.common.envelope import ok
from app.common.openapi import document

from . import service
from .schema import HealthOutSchema

bp = Blueprint("health", __name__)


@bp.get("/api/health")
@document(
    summary="Health check",
    success=HealthOutSchema,
    status=200,
    public=True,
)
def health():
    return ok(HealthOutSchema().dump(service.get_status()))
