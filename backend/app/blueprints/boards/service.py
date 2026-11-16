from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update

from app.common.access import BoardAccess
from app.common.constants import ActivityAction, NotificationType, Role
from app.common.db import commit_or_conflict, lock_board
from app.common.errors import Conflict, NotFound
from app.common.events import (
    create_notification,
    fit_message,
    log_activity,
    message_member_added,
)
from app.extensions import db
from app.models import queries
from app.models.board import Board, BoardMember
from app.models.card import Card
from app.models.column import BoardColumn
from app.models.user import User

_CARD_FIELDS = (
    "id",
    "title",
    "description",
    "assignee_id",
    "created_by",
    "order",
    "completed_at",
    "created_at",
    "updated_at",
)
_COLUMN_FIELDS = ("id", "board_id", "title", "order", "created_at", "updated_at")


def _board_dict(board: Board, role: str) -> dict[str, Any]:
    return {
        "id": board.id,
        "name": board.name,
        "owner_id": board.owner_id,
        "role": role,
        "created_at": board.created_at,
        "updated_at": board.updated_at,
    }


def create_board(user: User, data: dict[str, Any]) -> dict[str, Any]:
    """Board and the creator's admin membership in one transaction (Req 4.5)."""
    board = Board(name=data["name"], owner_id=user.id)
    db.session.add(board)
    db.session.flush()
    db.session.add(
        BoardMember(board_id=board.id, user_id=user.id, role=Role.ADMIN.value)
    )
    commit_or_conflict()
    db.session.refresh(board)
    return _board_dict(board, Role.ADMIN.value)


def list_boards(user: User) -> list[dict[str, Any]]:
    rows = db.session.execute(
        select(Board, BoardMember.role)
        .join(
            BoardMember,
            (BoardMember.board_id == Board.id) & (BoardMember.user_id == user.id),
        )
        .where(Board.deleted_at.is_(None))
        .order_by(Board.updated_at.desc(), Board.id.asc())
    ).all()
    return [_board_dict(board, role) for board, role in rows]


def get_board_detail(access: BoardAccess) -> dict[str, Any]:
    """Three queries through queries.load_board, no lazy relationships (Req 22)."""
    board, columns, cards = queries.load_board(access.board_id)
    if board is None:  # pragma: no cover - access helper already found the board
        raise NotFound()
    cards_by_column: dict[UUID, list[dict[str, Any]]] = {}
    for card in cards:
        cards_by_column.setdefault(card.column_id, []).append(
            {name: getattr(card, name) for name in _CARD_FIELDS}
        )
    detail = _board_dict(board, access.role)
    detail["columns"] = [
        {
            **{name: getattr(column, name) for name in _COLUMN_FIELDS},
            "cards": cards_by_column.get(column.id, []),
        }
        for column in columns
    ]
    return detail


def _load_board(access: BoardAccess) -> Board:
    board = db.session.get(Board, access.board_id)
    if board is None or board.deleted_at is not None:  # pragma: no cover
        raise NotFound()
    return board


def rename_board(access: BoardAccess, data: dict[str, Any]) -> dict[str, Any]:
    board = _load_board(access)
    board.name = data["name"]
    commit_or_conflict()
    db.session.refresh(board)
    return _board_dict(board, access.role)


def delete_board(access: BoardAccess) -> dict[str, Any]:
    """Soft-delete the board only; columns and cards stay untouched (Req 5.5)."""
    board = _load_board(access)
    board.soft_delete()
    commit_or_conflict()
    return {"id": board.id}

def _member_dict(member: BoardMember, user: User) -> dict[str, Any]:
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": member.role,
        "created_at": member.created_at,
    }


def list_members(access: BoardAccess) -> list[dict[str, Any]]:
    rows = db.session.execute(
        select(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .where(BoardMember.board_id == access.board_id)
        .order_by(BoardMember.created_at.asc(), BoardMember.user_id.asc())
    ).all()
    return [_member_dict(member, user) for member, user in rows]


def _get_membership(board_id: UUID, user_id: UUID) -> tuple[BoardMember, User]:
    row = db.session.execute(
        select(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .where(BoardMember.board_id == board_id, BoardMember.user_id == user_id)
    ).first()
    if row is None:
        raise NotFound()
    return row[0], row[1]


def _admin_count(board_id: UUID) -> int:
    return db.session.execute(
        select(func.count())
        .select_from(BoardMember)
        .where(
            BoardMember.board_id == board_id,
            BoardMember.role == Role.ADMIN.value,
        )
    ).scalar_one()


def add_member(access: BoardAccess, user: User, data: dict[str, Any]) -> dict[str, Any]:
    board = _load_board(access)
    lock_board(access.board_id)
    target = db.session.execute(
        select(User).where(func.lower(User.email) == data["email"].lower())
    ).scalar_one_or_none()
    if target is None:
        raise NotFound()
    exists = db.session.execute(
        select(BoardMember.user_id).where(
            BoardMember.board_id == access.board_id,
            BoardMember.user_id == target.id,
        )
    ).first()
    if exists is not None:
        raise Conflict("User is already a member of this board")
    member = BoardMember(
        board_id=access.board_id,
        user_id=target.id,
        role=data.get("role", Role.MEMBER.value),
    )
    db.session.add(member)
    db.session.flush()
    log_activity(access.board_id, user.id, ActivityAction.MEMBER_ADDED)
    create_notification(
        target.id,
        access.board_id,
        NotificationType.MEMBER_ADDED,
        fit_message(message_member_added, board.name),
    )
    commit_or_conflict()
    db.session.refresh(member)
    return _member_dict(member, target)


def change_member_role(
    access: BoardAccess, user: User, target_id: UUID, data: dict[str, Any]
) -> dict[str, Any]:
    lock_board(access.board_id)
    member, target = _get_membership(access.board_id, target_id)
    new_role = data["role"]
    if (
        member.role == Role.ADMIN.value
        and new_role != Role.ADMIN.value
        and _admin_count(access.board_id) <= 1
    ):
        raise Conflict("Board must keep at least one admin")
    member.role = new_role
    log_activity(access.board_id, user.id, ActivityAction.MEMBER_ROLE_CHANGED)
    commit_or_conflict()
    db.session.refresh(member)
    return _member_dict(member, target)


def remove_member(access: BoardAccess, user: User, target_id: UUID) -> dict[str, Any]:
    lock_board(access.board_id)
    member, _target = _get_membership(access.board_id, target_id)
    if member.role == Role.ADMIN.value and _admin_count(access.board_id) <= 1:
        raise Conflict("Board must keep at least one admin")
    column_ids = select(BoardColumn.id).where(
        BoardColumn.board_id == access.board_id,
        BoardColumn.deleted_at.is_(None),
    )
    db.session.execute(
        update(Card)
        .where(
            Card.assignee_id == target_id,
            Card.deleted_at.is_(None),
            Card.column_id.in_(column_ids),
        )
        .values(assignee_id=None)
        .execution_options(synchronize_session=False)
    )
    db.session.delete(member)
    log_activity(access.board_id, user.id, ActivityAction.MEMBER_REMOVED)
    commit_or_conflict()
    return {"user_id": target_id}
