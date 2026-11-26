from flask import Blueprint, jsonify

from app.auth_utils import auth_required, current_user
from app.blueprints.analytics import service
from app.openapi import document
from app.schemas import to_utc_iso

bp = Blueprint("analytics", __name__)


@bp.get("/api/boards/<uuid:board_id>/analytics")
@auth_required
@document(
    summary="Board analytics for the current week",
    tags=["analytics"],
    success=None,  # Response shape is a free-form dict (BE-ANL-01); no marshmallow output schema.
    status=200,
)
def board_analytics(board_id):
    data = service.board_analytics(current_user(), board_id)
    data["week_start"] = to_utc_iso(data["week_start"])
    return jsonify(data), 200
