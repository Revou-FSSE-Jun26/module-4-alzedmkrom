"""Fixture isolation: each test starts with empty tables and the role fixtures are wired."""
from app.extensions import db
from app.models import Board, User
from tests.api.conftest import TABLES


def test_role_fixtures_build_the_expected_memberships(board, private_board, outside_board, people):
    from app.models import BoardMember

    assert db.session.get(BoardMember, (board.id, people["admin"].id)).role == "admin"
    assert db.session.get(BoardMember, (board.id, people["member"].id)).role == "member"
    assert db.session.get(BoardMember, (board.id, people["guest"].id)) is None
    assert private_board.is_public is False
    assert outside_board.is_public is True


def test_previous_test_data_is_not_visible(board):
    # `board` exists in this test only. The autouse truncate removes earlier rows.
    assert db.session.query(Board).count() == 1
    assert db.session.query(User).count() == 5
    assert set(TABLES) >= {"boards", "users"}
