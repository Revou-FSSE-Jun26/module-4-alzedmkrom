"""Board listing, detail, edits, membership (BE-AZ-07, BE-SVC-02..04)."""
from collections import defaultdict

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import selectinload

from app.blueprints.boards.schema import (
    BoardCreateSchema,
    BoardListQuerySchema,
    BoardSchema,
    BoardUpdateSchema,
    MemberAddSchema,
    MemberSchema,
    MemberUpdateSchema,
)
from app.blueprints.cards.schema import CardSchema
from app.blueprints.columns.schema import ColumnSchema
from app.blueprints.notifications.service import notify
from app.errors import Conflict, NotFound, Unauthenticated, ValidationFailed
from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card, User
from app.pagination import paginate
from app.permissions import ADMIN, authorize, board_admin_ids, load_board, viewer_roles
from app.schemas import parse
from app.transactions import lock_board, transactional


def list_boards(user, payload):
    args = parse(BoardListQuerySchema, payload)
    scope = args.get("scope") or ("mine" if user else "public")
    if scope == "mine" and user is None:
        raise Unauthenticated()
    query = Board.query
    if scope == "mine":
        query = query.join(
            BoardMember, and_(BoardMember.board_id == Board.id, BoardMember.user_id == user.id)
        )
    else:
        query = query.filter(Board.is_public.is_(True))
    query = query.order_by(Board.created_at.desc(), Board.id)
    boards, total, pages = paginate(query, args["page"], args["per_page"])
    roles = viewer_roles(user, [b.id for b in boards])
    items = [{**BoardSchema().dump(b), "my_role": roles[b.id]} for b in boards]
    return {
        "items": items,
        "page": args["page"],
        "per_page": args["per_page"],
        "total": total,
        "pages": pages,
    }


@transactional
def create_board(user, payload):
    data = parse(BoardCreateSchema, payload)
    board = Board(name=data["name"], is_public=data["is_public"], created_by=user.id)
    db.session.add(board)
    db.session.flush()
    db.session.add(
        BoardMember(board_id=board.id, user_id=user.id, role=ADMIN, added_by=user.id)
    )
    return board


def get_board(user, board_id):
    """Board with columns and live cards, in a fixed number of queries (BE-SVC-02)."""
    board = load_board(board_id)
    role = authorize(user, "board:read", board)
    columns = (
        BoardColumn.query.filter(BoardColumn.board_id == board.id)
        .order_by(BoardColumn.order, BoardColumn.id)
        .all()
    )
    cards = (
        Card.active()
        .options(selectinload(Card.assignee))
        .filter(Card.board_id == board.id)
        .order_by(Card.column_id, Card.order, Card.id)
        .all()
    )
    cards_by_column = defaultdict(list)
    for card in cards:
        cards_by_column[card.column_id].append(CardSchema().dump(card))
    payload = {**BoardSchema().dump(board), "my_role": role}
    payload["columns"] = {
        "items": [
            {
                **ColumnSchema().dump(column),
                "cards": {"items": cards_by_column.get(column.id, [])},
            }
            for column in columns
        ]
    }
    return payload


@transactional
def update_board(user, board_id, payload):
    board = load_board(board_id)
    authorize(user, "board:update", board)
    data = parse(BoardUpdateSchema, payload)
    for key, value in data.items():
        setattr(board, key, value)
    return board


@transactional
def delete_board(user, board_id):
    board = load_board(board_id)
    authorize(user, "board:delete", board)
    db.session.delete(board)


def list_members(user, board_id):
    board = load_board(board_id)
    role = authorize(user, "board:members:read", board)
    rows = db.session.execute(
        select(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .where(BoardMember.board_id == board.id)
        .order_by(User.name, User.id)
    ).all()
    return [member_payload(member, person, role == ADMIN) for member, person in rows]


def member_payload(member, person, viewer_is_admin):
    """Email is visible to Admins of the board only (BE-VAL-04)."""
    return MemberSchema().dump(
        {
            "user_id": person.id,
            "name": person.name,
            "email": person.email if viewer_is_admin else None,
            "role": member.role,
            "created_at": member.created_at,
        }
    )


def _lock_admins(board_id):
    """DB-MEM-02: lock the admin rows before counting them."""
    return db.session.scalars(
        select(BoardMember)
        .where(BoardMember.board_id == board_id, BoardMember.role == ADMIN)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()


@transactional
def add_member(user, board_id, payload):
    board = load_board(board_id)
    authorize(user, "board:members:manage", board)
    data = parse(MemberAddSchema, payload)
    target = db.session.scalar(select(User).where(func.lower(User.email) == data["email"]))
    if target is None:
        raise ValidationFailed(details={"email": ["No user with this email."]})
    if db.session.get(BoardMember, (board.id, target.id)) is not None:
        raise Conflict("User is already a member of this board.", code="ALREADY_MEMBER")
    member = BoardMember(board_id=board.id, user_id=target.id, role=data["role"], added_by=user.id)
    db.session.add(member)
    db.session.flush()
    notify(
        [target.id, *board_admin_ids(board.id)],
        type="member_added",
        message=f'You were added to the board "{board.name}" as {data["role"]}.',
        board_id=board.id,
        actor_id=user.id,
    )
    return member, target


@transactional
def update_member(user, board_id, target_user_id, payload):
    board = load_board(board_id)
    authorize(user, "board:members:manage", board)
    data = parse(MemberUpdateSchema, payload)
    admins = _lock_admins(board.id)
    member = db.session.get(BoardMember, (board.id, target_user_id), populate_existing=True)
    if member is None:
        raise NotFound("Member not found.")
    if member.role == ADMIN and data["role"] != ADMIN and len(admins) <= 1:
        raise Conflict("A board must keep at least one Admin.", code="LAST_ADMIN")
    member.role = data["role"]
    person = db.session.get(User, target_user_id)
    return member, person


@transactional
def remove_member(user, board_id, target_user_id):
    board = load_board(board_id)
    authorize(user, "board:members:manage", board)
    admins = _lock_admins(board.id)
    member = db.session.get(BoardMember, (board.id, target_user_id), populate_existing=True)
    if member is None:
        raise NotFound("Member not found.")
    if member.role == ADMIN and len(admins) <= 1:
        raise Conflict("A board must keep at least one Admin.", code="LAST_ADMIN")
    db.session.execute(
        update(Card)
        .where(Card.board_id == board.id, Card.assignee_id == target_user_id)
        .values(assignee_id=None)
        .execution_options(synchronize_session=False)
    )
    db.session.delete(member)


