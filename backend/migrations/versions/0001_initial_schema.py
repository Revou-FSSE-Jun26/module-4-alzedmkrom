"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00.000000

Autogenerate cannot see CHECK constraints or triggers, so this revision was
reviewed and edited by hand: CHECK constraints, the lower(email) unique index,
gen_random_uuid() server defaults, set_updated_at() and its triggers.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

UPDATED_AT_TABLES = ("users", "boards", "columns", "cards", "comments")

SET_UPDATED_AT_FUNCTION = """
CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.created_at := OLD.created_at;
    NEW.updated_at := GREATEST(now(), OLD.updated_at);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""


def _create_index(name, table, cols, **kw):
    try:
        op.create_index(name, table, cols, **kw)
    except Exception as exc:
        raise RuntimeError(f"Failed to create index {name}") from exc


def _uuid_pk(table):
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    ), sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}"))


def _tstz(name, **kw):
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def _created_at():
    return _tstz("created_at", server_default=sa.text("now()"), nullable=False)


def _updated_at():
    return _tstz("updated_at", server_default=sa.text("now()"), nullable=False)


def _uuid_fk(name, target, ondelete, nullable, table):
    return (
        sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable),
        sa.ForeignKeyConstraint(
            [name],
            [f"{target}.id"],
            name=op.f(f"fk_{table}_{name}_{target}"),
            ondelete=ondelete,
        ),
    )


def upgrade():
    # users
    id_col, pk = _uuid_pk("users")
    op.create_table(
        "users",
        id_col,
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        _created_at(),
        _updated_at(),
        pk,
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255", name=op.f("ck_users_name_length")
        ),
        sa.CheckConstraint(
            "char_length(email) BETWEEN 3 AND 254", name=op.f("ck_users_email_length")
        ),
    )
    _create_index(
        "uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True
    )

    # boards
    id_col, pk = _uuid_pk("boards")
    owner_col, owner_fk = _uuid_fk("owner_id", "users", "RESTRICT", False, "boards")
    op.create_table(
        "boards",
        id_col,
        sa.Column("name", sa.Text(), nullable=False),
        owner_col,
        _created_at(),
        _updated_at(),
        _tstz("deleted_at", nullable=True),
        owner_fk,
        pk,
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255", name=op.f("ck_boards_name_length")
        ),
    )

    # board_members
    bm_board, bm_board_fk = _uuid_fk(
        "board_id", "boards", "CASCADE", False, "board_members"
    )
    bm_user, bm_user_fk = _uuid_fk(
        "user_id", "users", "CASCADE", False, "board_members"
    )
    op.create_table(
        "board_members",
        bm_board,
        bm_user,
        sa.Column("role", sa.Text(), nullable=False),
        _created_at(),
        bm_board_fk,
        bm_user_fk,
        sa.PrimaryKeyConstraint("board_id", "user_id", name=op.f("pk_board_members")),
        sa.CheckConstraint(
            "role IN ('member', 'admin')", name=op.f("ck_board_members_role_valid")
        ),
    )
    _create_index("ix_board_members_user_id", "board_members", ["user_id"])

    # columns
    id_col, pk = _uuid_pk("columns")
    board_col, board_fk = _uuid_fk("board_id", "boards", "CASCADE", False, "columns")
    op.create_table(
        "columns",
        id_col,
        board_col,
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("order", sa.Float(), nullable=False),
        _created_at(),
        _updated_at(),
        _tstz("deleted_at", nullable=True),
        board_fk,
        pk,
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 255",
            name=op.f("ck_columns_title_length"),
        ),
        sa.CheckConstraint(
            "\"order\" > 0 AND \"order\" < 'Infinity'",
            name=op.f("ck_columns_order_positive"),
        ),
    )
    _create_index("ix_columns_board_id_order", "columns", ["board_id", "order"])

    # cards
    id_col, pk = _uuid_pk("cards")
    column_col, column_fk = _uuid_fk("column_id", "columns", "CASCADE", False, "cards")
    assignee_col, assignee_fk = _uuid_fk(
        "assignee_id", "users", "SET NULL", True, "cards"
    )
    creator_col, creator_fk = _uuid_fk(
        "created_by", "users", "RESTRICT", False, "cards"
    )
    op.create_table(
        "cards",
        id_col,
        column_col,
        assignee_col,
        creator_col,
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Float(), nullable=False),
        _tstz("completed_at", nullable=True),
        _created_at(),
        _updated_at(),
        _tstz("deleted_at", nullable=True),
        column_fk,
        assignee_fk,
        creator_fk,
        pk,
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 255", name=op.f("ck_cards_title_length")
        ),
        sa.CheckConstraint(
            "description IS NULL OR char_length(description) <= 10000",
            name=op.f("ck_cards_description_length"),
        ),
        sa.CheckConstraint(
            "\"order\" > 0 AND \"order\" < 'Infinity'",
            name=op.f("ck_cards_order_positive_finite"),
        ),
    )
    _create_index("ix_cards_column_id_order", "cards", ["column_id", "order"])
    _create_index("ix_cards_assignee_id", "cards", ["assignee_id"])
    _create_index("ix_cards_completed_at", "cards", ["completed_at"])

    # comments
    id_col, pk = _uuid_pk("comments")
    card_col, card_fk = _uuid_fk("card_id", "cards", "CASCADE", False, "comments")
    user_col, user_fk = _uuid_fk("user_id", "users", "RESTRICT", False, "comments")
    op.create_table(
        "comments",
        id_col,
        card_col,
        user_col,
        sa.Column("body", sa.Text(), nullable=False),
        _created_at(),
        _updated_at(),
        _tstz("deleted_at", nullable=True),
        card_fk,
        user_fk,
        pk,
        sa.CheckConstraint(
            r"body ~ '\S' AND char_length(body) <= 5000",
            name=op.f("ck_comments_body_valid"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at", name=op.f("ck_comments_updated_after_created")
        ),
    )
    _create_index("ix_comments_card_id", "comments", ["card_id"])

    # notifications
    id_col, pk = _uuid_pk("notifications")
    n_user, n_user_fk = _uuid_fk("user_id", "users", "CASCADE", False, "notifications")
    n_board, n_board_fk = _uuid_fk(
        "board_id", "boards", "CASCADE", False, "notifications"
    )
    n_card, n_card_fk = _uuid_fk("card_id", "cards", "SET NULL", True, "notifications")
    op.create_table(
        "notifications",
        id_col,
        n_user,
        n_board,
        n_card,
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        _created_at(),
        n_user_fk,
        n_board_fk,
        n_card_fk,
        pk,
        sa.CheckConstraint(
            "char_length(type) BETWEEN 1 AND 50",
            name=op.f("ck_notifications_type_length"),
        ),
        sa.CheckConstraint(
            "char_length(message) BETWEEN 1 AND 500",
            name=op.f("ck_notifications_message_length"),
        ),
    )
    _create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
    )

    # activity_logs
    id_col, pk = _uuid_pk("activity_logs")
    a_board, a_board_fk = _uuid_fk(
        "board_id", "boards", "CASCADE", False, "activity_logs"
    )
    a_user, a_user_fk = _uuid_fk("user_id", "users", "RESTRICT", False, "activity_logs")
    a_card, a_card_fk = _uuid_fk("card_id", "cards", "SET NULL", True, "activity_logs")
    op.create_table(
        "activity_logs",
        id_col,
        a_board,
        a_user,
        a_card,
        sa.Column("action", sa.Text(), nullable=False),
        _created_at(),
        a_board_fk,
        a_user_fk,
        a_card_fk,
        pk,
        sa.CheckConstraint(
            "char_length(action) BETWEEN 1 AND 100",
            name=op.f("ck_activity_logs_action_length"),
        ),
    )
    _create_index(
        "ix_activity_logs_board_id_created_at",
        "activity_logs",
        ["board_id", "created_at"],
    )

    # updated_at maintenance
    op.execute(SET_UPDATED_AT_FUNCTION)
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_set_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade():
    for table in reversed(UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_index("ix_activity_logs_board_id_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_comments_card_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_cards_completed_at", table_name="cards")
    op.drop_index("ix_cards_assignee_id", table_name="cards")
    op.drop_index("ix_cards_column_id_order", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_columns_board_id_order", table_name="columns")
    op.drop_table("columns")

    op.drop_index("ix_board_members_user_id", table_name="board_members")
    op.drop_table("board_members")

    op.drop_table("boards")

    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
