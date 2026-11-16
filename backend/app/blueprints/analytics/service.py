from typing import Any

from app.models import queries


def get_analytics(board_id) -> dict[str, Any]:
    """Compose the board analytics from the reference queries (Req 15.1, 15.2,
    15.3, 15.5, 15.6). Access control is done by the caller."""
    return {
        "cards_per_column": [
            {"column_id": row.id, "title": row.title, "card_count": row.card_count}
            for row in queries.card_counts_per_column(board_id)
        ],
        "completed_this_week": queries.completed_this_week(board_id) or 0,
        "member_activity": [
            {"user_id": row.id, "name": row.name, "actions": row.actions}
            for row in queries.member_activity(board_id)
        ],
    }
