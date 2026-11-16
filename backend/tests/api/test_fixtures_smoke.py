"""Smoke test: the API fixtures build a graph, isolate tests and record queries."""
from sqlalchemy import text


def test_factories_snapshot_and_query_count(
    make_user, make_board, make_column, make_card, make_comment,
    make_notification, auth_headers, snapshot, count_queries, client,
):
    owner, other = make_user(), make_user()
    board = make_board(owner, members=[other])
    col = make_column(board)
    card = make_card(col, owner, assignee=other)
    make_comment(card, other)
    make_notification(other, board, card)

    snap = snapshot()
    assert snap["users"]["count"] == 2
    assert snap["board_members"]["count"] == 2
    assert snap["cards"]["count"] == 1
    assert snap["notifications"]["count"] == 1
    assert snapshot() == snap
    assert auth_headers(owner)["Authorization"].startswith("Bearer ")
    assert client is not None

    from app.extensions import db

    with count_queries() as stmts:
        db.session.execute(text("SELECT 1"))
    assert len(stmts) == 1


def test_clean_db_isolates_tests(snapshot):
    assert all(v["count"] == 0 for v in snapshot().values())
