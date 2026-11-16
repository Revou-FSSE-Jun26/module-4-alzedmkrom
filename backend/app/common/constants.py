from enum import Enum


class Role(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"


class ActivityAction(str, Enum):
    COLUMN_CREATED = "column_created"
    CARD_CREATED = "card_created"
    CARD_UPDATED = "card_updated"
    CARD_COMPLETED = "card_completed"
    CARD_MOVED = "card_moved"
    CARD_DELETED = "card_deleted"
    COMMENT_ADDED = "comment_added"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"


class NotificationType(str, Enum):
    CARD_ASSIGNED = "card_assigned"
    CARD_MOVED = "card_moved"
    COMMENT_ADDED = "comment_added"
    MEMBER_ADDED = "member_added"


NOTIFICATION_MESSAGE_MAX = 500
# Equal to the limits in app/models/queries.py.
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
OFFSET_MAX = 1_000_000
MIN_GAP = 1e-6
