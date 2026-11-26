"""Per-board roles and the permission matrix (BE-AZ-01, BE-AZ-02, BE-AZ-03).

Route functions never compare roles. Services call `authorize` once, right after
they load the resource. The check order is 401 (no user), 404 (private board,
non-member), 403 (role or ownership), then body validation and conflicts.
"""
from dataclasses import dataclass

from sqlalchemy import select

from app.errors import Forbidden, NotFound, Unauthenticated
from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card

ANONYMOUS = "anonymous"
GUEST = "guest"
MEMBER = "member"
ADMIN = "admin"

ALL_ROLES = frozenset({ANONYMOUS, GUEST, MEMBER, ADMIN})
MEMBER_ROLES = frozenset({MEMBER, ADMIN})
ADMIN_ROLES = frozenset({ADMIN})


@dataclass(frozen=True)
class Rule:
    """`roles` may perform the action. Roles in `own_only_roles` may act only on items they created."""

    roles: frozenset
    own_only_roles: frozenset = frozenset()


RULES = {
    "board:read": Rule(ALL_ROLES),
    "board:update": Rule(ADMIN_ROLES),
    "board:delete": Rule(ADMIN_ROLES),
    "board:members:read": Rule(MEMBER_ROLES),
    "board:members:manage": Rule(ADMIN_ROLES),
    "board:analytics": Rule(ADMIN_ROLES),
    "column:create": Rule(MEMBER_ROLES),
    "column:update": Rule(MEMBER_ROLES),
    "column:set_done": Rule(ADMIN_ROLES),
    "column:delete": Rule(MEMBER_ROLES, own_only_roles=frozenset({MEMBER})),
    "card:create": Rule(MEMBER_ROLES),
    "card:update": Rule(MEMBER_ROLES),
    "card:move": Rule(MEMBER_ROLES),
    "card:delete": Rule(MEMBER_ROLES, own_only_roles=frozenset({MEMBER})),
    "comment:create": Rule(MEMBER_ROLES),
    "comment:modify": Rule(MEMBER_ROLES, own_only_roles=MEMBER_ROLES),
}

READ_ACTIONS = frozenset({"board:read"})


def resolve_board_role(user, board):
    """Role of `user` on `board`, read from board_members on every call (BE-AUTH-03)."""
    if user is None:
        return ANONYMOUS
    member = db.session.get(BoardMember, (board.id, user.id))
    return GUEST if member is None else member.role


def authorize(user, action, board, item=None):
    """Raise the matching error, or return the caller's role. `item` is the resource the action touches."""
    rule = RULES[action]
    if user is None and action not in READ_ACTIONS:
        raise Unauthenticated()
    role = resolve_board_role(user, board)
    if role in (ANONYMOUS, GUEST) and not board.is_public:
        raise NotFound()
    if role not in rule.roles:
        raise Forbidden()
    if role in rule.own_only_roles and (item is None or item.created_by != user.id):
        raise Forbidden()
    return role


def board_admin_ids(board_id):
    return db.session.scalars(
        select(BoardMember.user_id).where(
            BoardMember.board_id == board_id, BoardMember.role == ADMIN
        )
    ).all()


def viewer_roles(user, board_ids):
    """Role of `user` on each board in one query. Guests are reported as guest."""
    if user is None:
        return {board_id: ANONYMOUS for board_id in board_ids}
    if not board_ids:
        return {}
    rows = db.session.execute(
        select(BoardMember.board_id, BoardMember.role).where(
            BoardMember.user_id == user.id, BoardMember.board_id.in_(board_ids)
        )
    ).all()
    found = {board_id: role for board_id, role in rows}
    return {board_id: found.get(board_id, GUEST) for board_id in board_ids}


def load_board(board_id):
    board = db.session.get(Board, board_id)
    if board is None:
        raise NotFound()
    return board


def load_column(column_id):
    column = db.session.get(BoardColumn, column_id)
    if column is None:
        raise NotFound()
    return column


def load_card(card_id):
    """A live card only. Soft-deleted cards behave as nonexistent (BE-SVC-06)."""
    card = Card.active().filter(Card.id == card_id).first()
    if card is None:
        raise NotFound()
    return card
