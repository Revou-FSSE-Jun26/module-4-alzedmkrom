from flask import Blueprint

from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document
from app.common.validation import load_query

from . import service
from .schema import (
    NotificationListQuerySchema,
    NotificationOutSchema,
    NotificationPageOutSchema,
)

bp = Blueprint("notifications", __name__)


@bp.get("/api/notifications")
@document(
    summary="List my notifications (paginated, newest first)",
    query=NotificationListQuerySchema,
    success=NotificationPageOutSchema,
    status=200,
)
@protected
def list_notifications():
    user = current_user()
    params = load_query(NotificationListQuerySchema())
    page = service.list_notifications(user, params["page"], params["per_page"])
    return ok(NotificationPageOutSchema().dump(page))


@bp.patch("/api/notifications/<notification_id>/read")
@document(
    summary="Mark one of my notifications as read",
    success=NotificationOutSchema,
    status=200,
    conflict=True,
)
@protected
def mark_read(notification_id):
    user = current_user()
    notification = service.mark_read(user, notification_id)
    return ok(NotificationOutSchema().dump(notification))
