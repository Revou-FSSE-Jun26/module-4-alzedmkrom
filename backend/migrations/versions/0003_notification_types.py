"""Extend the notification type CHECK to the ten types of backend.md BE-NTF-03.

Downgrade removes notifications whose type is one of the six new types, because the
old CHECK cannot hold them. That loss is intended and documented.
"""

from alembic import op

revision = "0003_notification_types"
down_revision = "0002_v4_schema"
branch_labels = None
depends_on = None

OLD = "('card_assigned', 'card_moved', 'comment_added', 'member_added')"
NEW = (
    "('card_assigned', 'card_moved', 'comment_added', 'member_added', "
    "'card_created', 'card_deleted', 'column_deleted', 'board_deleted', "
    "'member_role_changed', 'member_removed')"
)


def upgrade():
    op.drop_constraint(op.f("ck_notifications_type"), "notifications", type_="check")
    op.create_check_constraint(op.f("ck_notifications_type"), "notifications", f"type IN {NEW}")


def downgrade():
    op.execute(f"DELETE FROM notifications WHERE type NOT IN {OLD}")
    op.drop_constraint(op.f("ck_notifications_type"), "notifications", type_="check")
    op.create_check_constraint(op.f("ck_notifications_type"), "notifications", f"type IN {OLD}")