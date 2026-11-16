from bisect import bisect_right
from dataclasses import dataclass
from typing import Iterable, Sequence
from uuid import UUID

from app.common.constants import MIN_GAP

__all__ = ["MIN_GAP", "MovePlan", "next_order", "plan_move"]


def next_order(existing: Iterable[float]) -> float:
    """max(existing) + 1.0, or 1.0 when empty."""
    values = list(existing)
    return max(values) + 1.0 if values else 1.0


@dataclass(frozen=True)
class MovePlan:
    rebalanced: bool
    orders: dict[UUID, float]


def plan_move(
    siblings: Sequence[tuple[UUID, float]], moved_id: UUID, requested: float
) -> MovePlan:
    """Plan a move. ``siblings`` excludes the moved row."""
    if all(abs(order - requested) >= MIN_GAP for _, order in siblings):
        return MovePlan(False, {moved_id: requested})

    ordered = sorted(siblings, key=lambda s: (s[1], s[0]))
    index = bisect_right([order for _, order in ordered], requested)
    sequence = [row_id for row_id, _ in ordered]
    sequence.insert(index, moved_id)
    return MovePlan(
        True, {row_id: float(position) for position, row_id in enumerate(sequence, 1)}
    )
