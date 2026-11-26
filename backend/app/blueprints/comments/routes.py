from flask import Blueprint, jsonify, request

from app.auth_utils import auth_optional, auth_required, current_user
from app.blueprints.comments import service
from app.blueprints.comments.schema import CommentSchema

bp = Blueprint("comments", __name__)


@bp.get("/api/cards/<uuid:card_id>/comments")
@auth_optional
def list_comments(card_id):
    comments = service.list_comments(current_user(), card_id)
    return jsonify({"items": [CommentSchema().dump(c) for c in comments]}), 200


@bp.post("/api/cards/<uuid:card_id>/comments")
@auth_required
def create_comment(card_id):
    comment = service.create_comment(current_user(), card_id, request.get_json(silent=True))
    return jsonify(CommentSchema().dump(comment)), 201


@bp.patch("/api/comments/<uuid:comment_id>")
@auth_required
def update_comment(comment_id):
    comment = service.update_comment(current_user(), comment_id, request.get_json(silent=True))
    return jsonify(CommentSchema().dump(comment)), 200


@bp.delete("/api/comments/<uuid:comment_id>")
@auth_required
def delete_comment(comment_id):
    service.delete_comment(current_user(), comment_id)
    return "", 204
