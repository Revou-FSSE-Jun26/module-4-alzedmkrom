from flask import Blueprint

from app.common.access import get_board_for_user, require_admin
from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document

from . import service
from .schema import AnalyticsOutSchema

bp = Blueprint("analytics", __name__)


@bp.get("/api/boards/<board_id>/analytics")
@document(
    summary="Board analytics (admin only)",
    success=AnalyticsOutSchema,
    status=200,
)
@protected
def get_analytics(board_id):
    access = get_board_for_user(current_user().id, board_id)
    require_admin(access)
    return ok(AnalyticsOutSchema().dump(service.get_analytics(access.board_id)))
