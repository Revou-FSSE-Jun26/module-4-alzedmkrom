"""Smoke tests for app.models.queries against real PostgreSQL 18."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import (
    ActivityLog, Board, BoardColumn, BoardMember, Card, Notification, User,
)
from app.models import queries as q

UTC = timezone.utc


@pytest.fixture()
def s(session, monkeypatch):
    """Route queries' db.session to the rolled-back test session."""
    monkeypatch.setattr(db, "session", session)
    return session


def mk_user(s, name="u"):
    u = User(id=uuid.uuid4(), name=name, email=f"{uuid.uuid4().hex}@example.com", password_hash="x")
    s.add(u)
    s.flush()
    return u


def mk_board(s, owner, name="b"):
    b = Board(id=uuid.uuid4(), name=name, owner_id=owner.id)
    s.add(b)
    s.flush()
    return b


def mk_col(s, board, title="c", order=1.0):
    c = BoardColumn(id=uuid.uuid4(), board_id=board.id, title=title, order=order)
    s.add(c)
    s.flush()
    return c


def mk_card(s, col, user, title="t", order=1.0, **kw):
    c = Card(id=uuid.uuid4(), column_id=col.id, created_by=user.id, title=title, order=order, **kw)
    s.add(c)
    s.flush()
    return c


NOW = datetime(2024, 5, 15, 12, 0, tzinfo=UTC)  # Wednesday
MONDAY = datetime(2024, 5, 13, tzinfo=UTC)


def test_week_bounds_utc():
    assert q.week_bounds_utc(NOW) == (MONDAY, MONDAY + timedelta(days=7))
    # Sunday 23:30 at UTC-5 is Monday 04:30 UTC -> following week
    plus = datetime(2024, 5, 19, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert q.week_bounds_utc(plus)[0] == datetime(2024, 5, 20, tzinfo=UTC)
    assert q.week_bounds_utc(MONDAY)[0] == MONDAY


def test_card_counts_per_column(s):
    u = mk_user(s)
    b = mk_board(s, u)
    c1 = mk_col(s, b, "a", 1.0)
    c2 = mk_col(s, b, "empty", 2.0)
    c3 = mk_col(s, b, "gone", 3.0)
    c3.soft_delete()
    mk_card(s, c1, u, "x", 1.0)
    mk_card(s, c1, u, "y", 2.0)
    d = mk_card(s, c1, u, "deleted", 3.0)
    d.soft_delete()
    mk_card(s, c3, u)
    s.flush()
    rows = q.card_counts_per_column(b.id)
    assert [(r.title, r.card_count) for r in rows] == [("a", 2), ("empty", 0)]


def test_completed_this_week_boundaries(s):
    u = mk_user(s)
    b = mk_board(s, u)
    c = mk_col(s, b)
    mk_card(s, c, u, "before", 1.0, completed_at=MONDAY - timedelta(microseconds=1))
    mk_card(s, c, u, "start", 2.0, completed_at=MONDAY)
    mk_card(s, c, u, "mid", 3.0, completed_at=NOW)
    mk_card(s, c, u, "end", 4.0, completed_at=MONDAY + timedelta(days=7))
    mk_card(s, c, u, "none", 5.0)
    dl = mk_card(s, c, u, "del", 6.0, completed_at=NOW)
    dl.soft_delete()
    s.flush()
    assert q.completed_this_week(b.id, NOW) == 2


def test_member_activity(s):
    owner, idle, former = mk_user(s, "owner"), mk_user(s, "idle"), mk_user(s, "former")
    b = mk_board(s, owner)
    other = mk_board(s, owner, "other")
    s.add_all([BoardMember(board_id=b.id, user_id=owner.id, role="admin"),
               BoardMember(board_id=b.id, user_id=idle.id, role="member")])
    s.add_all([ActivityLog(board_id=b.id, user_id=owner.id, action="a"),
               ActivityLog(board_id=b.id, user_id=owner.id, action="b"),
               ActivityLog(board_id=b.id, user_id=former.id, action="c"),
               ActivityLog(board_id=other.id, user_id=idle.id, action="d")])
    s.flush()
    got = {r.name: r.actions for r in q.member_activity(b.id)}
    assert got == {"owner": 2, "idle": 0, "former": 1}


def test_my_tasks(s):
    me, other = mk_user(s, "me"), mk_user(s, "other")
    bz = mk_board(s, me, "Zeta")
    ba = mk_board(s, me, "Alpha")
    bd = mk_board(s, me, "Deleted")
    bd.soft_delete()
    cz, ca, cd = mk_col(s, bz), mk_col(s, ba), mk_col(s, bd)
    mk_card(s, cz, me, "z1", assignee_id=me.id)
    mk_card(s, ca, me, "a1", assignee_id=me.id)
    mk_card(s, ca, me, "not mine", 2.0, assignee_id=other.id)
    mk_card(s, cd, me, "hidden", assignee_id=me.id)
    gone = mk_card(s, ca, me, "gone", 3.0, assignee_id=me.id)
    gone.soft_delete()
    s.flush()
    rows = q.my_tasks(me.id)
    assert [(r[1], r[2].title) for r in rows] == [("Alpha", "a1"), ("Zeta", "z1")]


def test_search_cards(s):
    u = mk_user(s)
    b = mk_board(s, u)
    c = mk_col(s, b)
    hit = mk_card(s, c, u, "Fix Login", 1.0)
    desc = mk_card(s, c, u, "other", 2.0, description="about LOGIN page")
    pct = mk_card(s, c, u, "100% done", 3.0)
    mk_card(s, c, u, "1000 done", 4.0)
    und = mk_card(s, c, u, "a_b", 5.0)
    mk_card(s, c, u, "axb", 6.0)
    dc = mk_card(s, c, u, "login deleted card", 7.0)
    dc.soft_delete()
    c2 = mk_col(s, b, "gone", 2.0)
    c2.soft_delete()
    mk_card(s, c2, u, "login in deleted column")
    b2 = mk_board(s, u, "b2")
    b2.soft_delete()
    mk_card(s, mk_col(s, b2), u, "login in deleted board")
    s.flush()
    assert {x.id for x in q.search_cards("login")} == {hit.id, desc.id}
    assert [x.id for x in q.search_cards("%")] == [pct.id]
    assert [x.id for x in q.search_cards("_")] == [und.id]
    # membership filter
    assert q.search_cards("login", user_id=u.id) == []
    s.add(BoardMember(board_id=b.id, user_id=u.id, role="admin"))
    s.flush()
    assert len(q.search_cards("login", user_id=u.id)) == 2
    for bad in ("", "x" * 201):
        with pytest.raises(ValueError):
            q.search_cards(bad)
    assert q.search_cards("x" * 200) == []


def test_notifications_page(s):
    u = mk_user(s)
    b = mk_board(s, u)
    for i in range(5):
        s.add(Notification(user_id=u.id, board_id=b.id, type="t", message=f"m{i}",
                           created_at=NOW + timedelta(minutes=i)))
    other = mk_user(s)
    s.add(Notification(user_id=other.id, board_id=b.id, type="t", message="x", created_at=NOW))
    s.flush()
    assert [n.message for n in q.notifications_page(u.id, 3)] == ["m4", "m3", "m2"]
    assert [n.message for n in q.notifications_page(u.id, 3, 3)] == ["m1", "m0"]
    for kw in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 1_000_001}):
        with pytest.raises(ValueError):
            q.notifications_page(u.id, **kw)
    q.notifications_page(u.id, 100, 1_000_000)


def test_load_board(s):
    u = mk_user(s)
    b = mk_board(s, u)
    c1, c2 = mk_col(s, b, "c1", 1.0), mk_col(s, b, "c2", 2.0)
    c3 = mk_col(s, b, "c3", 3.0)
    c3.soft_delete()
    k2 = mk_card(s, c1, u, "k2", 2.0)
    k1 = mk_card(s, c1, u, "k1", 1.0)
    mk_card(s, c1, u, "dead", 3.0).soft_delete()
    mk_card(s, c3, u, "in dead col")
    s.flush()
    s.expire_all()
    from sqlalchemy import event
    stmts = []
    eng = s.get_bind()
    def on_exec(conn, cursor, statement, *a):
        stmts.append(statement)
    event.listen(eng, "before_cursor_execute", on_exec)
    try:
        board, cols, cards = q.load_board(b.id)
    finally:
        event.remove(eng, "before_cursor_execute", on_exec)
    assert board.id == b.id
    assert [c.title for c in cols] == ["c1", "c2"]
    assert [c.id for c in cards] == [k1.id, k2.id]
    assert len(stmts) == 3
