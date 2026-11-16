from flask import Blueprint

from app.common.access import (
    get_card_for_user,
    get_comment_for_user,
    require_comment_owner,
)
from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document
from app.common.schemas import IdOutSchema
from app.common.validation import load_body

from . import service
from .schema import CommentOutSchema, CommentSchema

bp = Blueprint("comments", __name__)


@bp.post("/api/cards/<card_id>/comments")
@document(
    summary="Add a comment to a card",
    request=CommentSchema,
    success=CommentOutSchema,
    status=201,
    conflict=True,
)
@protected
def create_comment(card_id):
    user = current_user()
    access = get_card_for_user(user.id, card_id)
    data = load_body(CommentSchema())
    comment = service.create_comment(user, access, data)
    return ok(CommentOutSchema().dump(comment), 201)


@bp.get("/api/cards/<card_id>/comments")
@document(
    summary="List comments on a card",
    success=CommentOutSchema,
    many=True,
    status=200,
)
@protected
def list_comments(card_id):
    user = current_user()
    access = get_card_for_user(user.id, card_id)
    comments = service.list_comments(access)
    return ok(CommentOutSchema(many=True).dump(comments))


@bp.patch("/api/comments/<comment_id>")
@document(
    summary="Edit a comment (author only)",
    request=CommentSchema,
    success=CommentOutSchema,
    status=200,
    conflict=True,
)
@protected
def update_comment(comment_id):
    user = current_user()
    access = get_comment_for_user(user.id, comment_id)
    require_comment_owner(access, user.id)
    data = load_body(CommentSchema())
    comment = service.update_comment(user, access, data)
    return ok(CommentOutSchema().dump(comment))


@bp.delete("/api/comments/<comment_id>")
@document(
    summary="Delete a comment (author only)",
    success=IdOutSchema,
    status=200,
    conflict=True,
)
@protected
def delete_comment(comment_id):
    user = current_user()
    access = get_comment_for_user(user.id, comment_id)
    require_comment_owner(access, user.id)
    result = service.delete_comment(user, access)
    return ok(IdOutSchema().dump(result))
