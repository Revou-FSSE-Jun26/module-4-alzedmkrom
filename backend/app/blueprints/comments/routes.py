from flask import Blueprint, jsonify, request

from app.auth_utils import auth_optional, auth_required, current_user
from app.blueprints.comments import service
from app.blueprints.comments.schema import CommentCreateSchema, CommentSchema, CommentUpdateSchema
from app.openapi import document

bp = Blueprint("comments", __name__)


@bp.get("/api/cards/<uuid:card_id>/comments")
@auth_optional
@document(
    summary="List comments on a card",
    tags=["comments"],
    success=CommentSchema,
    many=True,
    public=True,
)
def list_comments(card_id):
    comments = service.list_comments(current_user(), card_id)
    return jsonify({"items": [CommentSchema().dump(c) for c in comments]}), 200


@bp.post("/api/cards/<uuid:card_id>/comments")
@auth_required
@document(
    summary="Add a comment",
    tags=["comments"],
    request=CommentCreateSchema,
    success=CommentSchema,
    status=201,
)
def create_comment(card_id):
    comment = service.create_comment(current_user(), card_id, request.get_json(silent=True))
    return jsonify(CommentSchema().dump(comment)), 201


@bp.patch("/api/comments/<uuid:comment_id>")
@auth_required
@document(
    summary="Edit a comment",
    tags=["comments"],
    request=CommentUpdateSchema,
    success=CommentSchema,
)
def update_comment(comment_id):
    comment = service.update_comment(
        current_user(), comment_id, request.get_json(silent=True)
    )
    return jsonify(CommentSchema().dump(comment)), 200


@bp.delete("/api/comments/<uuid:comment_id>")
@auth_required
@document(
    summary="Delete a comment",
    tags=["comments"],
    success=None,
    status=204,
)
def delete_comment(comment_id):
    service.delete_comment(current_user(), comment_id)
    return "", 204
