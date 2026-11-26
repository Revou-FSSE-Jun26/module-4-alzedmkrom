from flask import Blueprint, jsonify, request

from app.auth_utils import auth_required, current_user
from app.blueprints.notifications import service
from app.blueprints.notifications.schema import NotificationSchema
from app.schemas import PaginationQuerySchema, parse

bp = Blueprint("notifications", __name__)


@bp.get("/api/notifications")
@auth_required
def list_notifications():
    args = parse(PaginationQuerySchema, request.args.to_dict())
    items, total, pages, unread = service.list_notifications(
        current_user(), args["page"], args["per_page"]
    )
    return jsonify(
        {
            "items": [NotificationSchema().dump(n) for n in items],
            "page": args["page"],
            "per_page": args["per_page"],
            "total": total,
            "pages": pages,
            "unread_count": unread,
        }
    ), 200


@bp.patch("/api/notifications/<uuid:notification_id>/read")
@auth_required
def mark_read(notification_id):
    notification = service.mark_read(current_user(), notification_id)
    return jsonify(NotificationSchema().dump(notification)), 200
