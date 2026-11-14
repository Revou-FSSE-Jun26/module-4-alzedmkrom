"""``flask seed [--force]``: insert deterministic demo data (Requirement 12)."""
import os
import uuid

import click
from flask.cli import with_appcontext
from sqlalchemy.dialects.postgresql import insert
from werkzeug.security import generate_password_hash

from app.db_config import running_on_railway
from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card, User

SEED_NAMESPACE = uuid.UUID("5b0f3c1e-7a4d-4e5b-9d3a-2f6c8a1b0e42")
DEFAULT_SEED_PASSWORD = "revotask-dev"


def _id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}")


def _insert(model, rows):
    db.session.execute(insert(model).values(rows).on_conflict_do_nothing())


def _insert_all() -> None:
    password_hash = generate_password_hash(
        os.environ.get("SEED_PASSWORD") or DEFAULT_SEED_PASSWORD
    )
    alice = _id("user", "alice@revotask.test")
    bob = _id("user", "bob@revotask.test")
    board = _id("board", "RevoTask Demo")

    _insert(
        User,
        [
            {"id": alice, "name": "Alice", "email": "alice@revotask.test",
             "password_hash": password_hash},
            {"id": bob, "name": "Bob", "email": "bob@revotask.test",
             "password_hash": password_hash},
        ],
    )
    _insert(Board, [{"id": board, "name": "RevoTask Demo", "owner_id": alice}])
    _insert(
        BoardMember,
        [
            {"board_id": board, "user_id": alice, "role": "admin"},
            {"board_id": board, "user_id": bob, "role": "member"},
        ],
    )

    column_specs = [("To Do", 1.0, 2), ("In Progress", 2.0, 2), ("Done", 3.0, 1)]
    columns, cards = [], []
    n = 0
    for title, order, card_count in column_specs:
        column_id = _id("column", f"RevoTask Demo/{title}")
        columns.append(
            {"id": column_id, "board_id": board, "title": title, "order": order}
        )
        for position in range(1, card_count + 1):
            cards.append(
                {
                    "id": _id("card", f"RevoTask Demo/{title}/{position}"),
                    "column_id": column_id,
                    "title": f"{title} task {position}",
                    "description": f"Demo card {position} in {title}.",
                    "assignee_id": alice if n % 2 == 0 else bob,
                    "created_by": alice,
                    "order": float(position),
                }
            )
            n += 1
    _insert(BoardColumn, columns)
    _insert(Card, cards)


@click.command("seed")
@click.option("--force", is_flag=True, help="Allow seeding a Railway database.")
@with_appcontext
def seed_command(force):
    """Insert demo users, a board, columns and cards (idempotent)."""
    if running_on_railway() and not force:
        raise click.ClickException("Refusing to seed a Railway database without --force")
    try:
        _insert_all()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException(f"Seeding failed: {exc}")
    click.echo("Seeding finished.")
