"""Schema shape against the migrated PostgreSQL 18 database (DB-IDX-01, DB-CAS-01, DB-SCH-01).

These tests read the catalog, so they check what was migrated, not the models.
"""

from sqlalchemy import text

# DB-IDX-01 rows, plus DB-ORD-02 and DB-DON-02. Thirteen indexes in total.
# Value: fragments the partial predicate must contain. [] means a full index.
# PostgreSQL prints predicates with parentheses, so only the fragments are checked.
EXPECTED_INDEXES = {
    "uq_users_email_lower": [],
    "ix_board_members_user_id": [],
    "ix_boards_created_at_public": ["is_public"],
    "ix_columns_board_id_position": [],
    "uq_columns_board_id_done": ["is_done"],
    "ix_cards_column_id_position": ["deleted_at IS NULL"],
    "ix_cards_assignee_id": ["assignee_id IS NOT NULL", "deleted_at IS NULL"],
    "ix_cards_board_id_created_by": ["deleted_at IS NULL"],
    "ix_cards_board_id_completed_at": ["completed_at IS NOT NULL", "deleted_at IS NULL"],
    "ix_comments_card_id_created_at": [],
    "ix_comments_created_by": [],
    "ix_notifications_user_id_created_at": [],
    "ix_notifications_user_id_unread": ["NOT is_read"],
}

# DB-CAS-01. Key: (table, foreign key name). Value: confdeltype letter.
# c = CASCADE, n = SET NULL, r = RESTRICT, a = NO ACTION.
EXPECTED_FK_RULES = {
    ("board_members", "fk_board_members_board_id_boards"): "c",
    ("board_members", "fk_board_members_user_id_users"): "c",
    ("board_members", "fk_board_members_added_by_users"): "n",
    ("boards", "fk_boards_created_by_users"): "n",
    ("columns", "fk_columns_board_id_boards"): "c",
    ("columns", "fk_columns_created_by_users"): "n",
    ("cards", "fk_cards_column_id_columns"): "c",
    ("cards", "fk_cards_assignee_id_users"): "n",
    ("cards", "fk_cards_created_by_users"): "n",
    ("comments", "fk_comments_card_id_cards"): "c",
    ("comments", "fk_comments_created_by_users"): "n",
    ("notifications", "fk_notifications_user_id_users"): "c",
}


def test_thirteen_indexes_exist_and_no_others(session):
    rows = session.execute(
        text(
            """
            SELECT i.relname AS name, pg_get_expr(x.indpred, x.indrelid) AS predicate
            FROM pg_index x
            JOIN pg_class i ON i.oid = x.indexrelid
            JOIN pg_class t ON t.oid = x.indrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND NOT x.indisprimary
              AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = x.indexrelid)
            """
        )
    ).all()
    found = {row.name: row.predicate for row in rows}

    assert set(found) == set(EXPECTED_INDEXES)
    assert len(found) == 13
    for name, fragments in EXPECTED_INDEXES.items():
        if not fragments:
            assert found[name] is None, (name, found[name])
        for fragment in fragments:
            assert fragment in found[name], (name, found[name])


def test_foreign_keys_match_the_db_cas_01_table(session):
    rows = session.execute(
        text(
            """
            SELECT t.relname AS tbl, c.conname AS name, c.confdeltype AS rule
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.contype = 'f' AND n.nspname = 'public'
            """
        )
    ).all()
    found = {(row.tbl, row.name): row.rule for row in rows}
    assert found == EXPECTED_FK_RULES


def test_notifications_board_id_has_no_foreign_key(session):
    count = session.execute(
        text(
            """
            SELECT count(*) FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f' AND c.conrelid = 'notifications'::regclass
              AND a.attname = 'board_id'
            """
        )
    ).scalar_one()
    assert count == 0


def test_database_defaults_apply_without_the_orm(session):
    """Rows inserted with raw SQL still get the defaults (DB-VIS-01 and friends)."""
    user_id = session.execute(
        text(
            "INSERT INTO users (name, email, password_hash) "
            "VALUES ('Raw', 'raw-defaults@example.com', 'h') RETURNING id"
        )
    ).scalar_one()
    board = session.execute(
        text("INSERT INTO boards (name, created_by) VALUES ('Raw board', :u) "
             "RETURNING id, is_public"),
        {"u": user_id},
    ).one()
    assert board.is_public is True
    column = session.execute(
        text("INSERT INTO columns (board_id, name, position) VALUES (:b, 'Raw', 1.0) "
             "RETURNING id, is_done"),
        {"b": board.id},
    ).one()
    assert column.is_done is False
    notification_read = session.execute(
        text("INSERT INTO notifications (user_id, type, message) "
             "VALUES (:u, 'member_added', 'hi') RETURNING is_read"),
        {"u": user_id},
    ).scalar_one()
    assert notification_read is False


def test_position_is_double_precision_and_no_activity_table(session):
    types = {
        (row.table_name, row.column_name): row.data_type
        for row in session.execute(
            text(
                "SELECT table_name, column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'public' AND column_name = 'position'"
            )
        ).all()
    }
    assert types == {("columns", "position"): "double precision",
                     ("cards", "position"): "double precision"}
    tables = set(
        session.scalars(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).all()
    )
    assert "activity_logs" not in tables


def test_deleted_at_exists_only_on_cards(session):
    tables = set(
        session.scalars(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND column_name = 'deleted_at'"
            )
        ).all()
    )
    assert tables == {"cards"}
