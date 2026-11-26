"""``flask seed [--force]``: idempotent demo data (DB-SEED-01, Requirement 12).

Ids are uuid5 values from fixed natural keys, so every run writes the same rows.
Every insert uses ON CONFLICT DO NOTHING, and the whole run is one transaction.
"""
import datetime as dt
import os
import uuid

import click
from flask.cli import with_appcontext
from sqlalchemy.dialects.postgresql import insert
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card, Comment, User

SEED_NAMESPACE = uuid.UUID("5b0f3c1e-7a4d-4e5b-9d3a-2f6c8a1b0e42")
# Documented demo value. Set SEED_PASSWORD to override. Never a real credential.
DEFAULT_SEED_PASSWORD = "revotask-dev"
# Fixed, so repeated runs write identical values.
DONE_COMPLETED_AT = dt.datetime(2026, 11, 16, 12, 0, tzinfo=dt.timezone.utc)


def _id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}")


def _insert(model, rows) -> None:
    if rows:
        db.session.execute(insert(model).values(rows).on_conflict_do_nothing())


def _insert_all() -> None:
    password_hash = generate_password_hash(
        os.environ.get("SEED_PASSWORD") or DEFAULT_SEED_PASSWORD
    )
    alice = _id("user", "alice@revotask.test")
    bob = _id("user", "bob@revotask.test")
    carol = _id("user", "carol@revotask.test")
    _insert(
        User,
        [
            {"id": alice, "name": "Alice", "email": "alice@revotask.test",
             "password_hash": password_hash},
            {"id": bob, "name": "Bob", "email": "bob@revotask.test",
             "password_hash": password_hash},
            # Guest: no board_members row anywhere (DB-SEED-01).
            {"id": carol, "name": "Carol", "email": "carol@revotask.test",
             "password_hash": password_hash},
        ],
    )

    demo = _id("board", "RevoTask Demo")
    sandbox = _id("board", "Private Sandbox")
    _insert(
        Board,
        [
            {"id": demo, "name": "RevoTask Demo", "is_public": True, "created_by": alice},
            {"id": sandbox, "name": "Private Sandbox", "is_public": False, "created_by": alice},
        ],
    )
    _insert(
        BoardMember,
        [
            {"board_id": demo, "user_id": alice, "role": "admin", "added_by": None},
            {"board_id": demo, "user_id": bob, "role": "member", "added_by": alice},
            {"board_id": sandbox, "user_id": alice, "role": "admin", "added_by": None},
        ],
    )

    # (board key, column name, position, is_done, card count)
    column_specs = [
        (demo, "To Do", 1.0, False, 2),
        (demo, "In Progress", 2.0, False, 2),
        (demo, "Done", 3.0, True, 1),
        (sandbox, "Backlog", 1.0, False, 1),
    ]
    columns, cards = [], []
    card_index = 0
    for board, name, position, is_done, card_count in column_specs:
        column_id = _id("column", f"{board}/{name}")
        columns.append(
            {"id": column_id, "board_id": board, "name": name, "order": position,
             "is_done": is_done, "created_by": alice}
        )
        for number in range(1, card_count + 1):
            cards.append(
                {
                    "id": _id("card", f"{board}/{name}/{number}"),
                    "board_id": board,
                    "column_id": column_id,
                    "title": f"{name} task {number}",
                    "description": f"Demo card {number} in {name}.",
                    "assignee_id": alice if card_index % 2 == 0 else bob,
                    "due_date": None,
                    "order": float(number),
                    "completed_at": DONE_COMPLETED_AT if is_done else None,
                    "created_by": alice,
                }
            )
            card_index += 1
    _insert(BoardColumn, columns)
    _insert(Card, cards)

    todo_first = _id("card", f"{demo}/To Do/1")
    todo_second = _id("card", f"{demo}/To Do/2")
    _insert(
        Comment,
        [
            {"id": _id("comment", "first"), "card_id": todo_first,
             "content": "Picked this up.", "created_by": bob},
            {"id": _id("comment", "second"), "card_id": todo_second,
             "content": "Needs a design review first.", "created_by": alice},
        ],
    )


@click.command("seed")
@click.option("--force", is_flag=True, help="Allow seeding when FLASK_ENV is production.")
@with_appcontext
def seed_command(force):
    """Insert demo users, boards, columns, cards and comments (idempotent)."""
    if os.environ.get("FLASK_ENV") == "production" and not force:
        raise click.ClickException("Refusing to seed in production without --force")
    try:
        _insert_all()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException(f"Seeding failed: {exc}")
    click.echo("Seeding finished.")
