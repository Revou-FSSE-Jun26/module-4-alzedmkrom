"""Float ordering for columns and cards (BE-ORD-01, BE-ORD-02)."""
from bisect import bisect_right
from dataclasses import dataclass

ORDER_STEP = 1024.0
MIN_GAP = 1e-6


def end_order(last):
    """Order for a new item appended after `last` (None when the container is empty)."""
    return ORDER_STEP if last is None else last + ORDER_STEP


@dataclass(frozen=True)
class Placement:
    """New orders for the items whose stored value changes."""

    orders: dict
    rebalanced: bool

    def siblings(self):
        if not self.rebalanced:
            return []
        return [{"id": key, "order": value} for key, value in self.orders.items()]


def plan_order(siblings, moved_key, new_order):
    """Place `moved_key` at `new_order` among `siblings` (list of (key, order)).

    A tie with a sibling puts the moved item after that sibling. If any two
    adjacent orders end up closer than MIN_GAP, the whole container is renumbered
    to multiples of ORDER_STEP, keeping the relative order.
    """
    others = sorted(((k, o) for k, o in siblings if k != moved_key), key=lambda p: p[1])
    index = bisect_right([o for _, o in others], new_order)
    sequence = others[:index] + [(moved_key, new_order)] + others[index:]
    gaps_ok = all(b[1] - a[1] >= MIN_GAP for a, b in zip(sequence, sequence[1:]))
    if gaps_ok:
        return Placement(orders={moved_key: new_order}, rebalanced=False)
    orders = {key: ORDER_STEP * (i + 1) for i, (key, _) in enumerate(sequence)}
    return Placement(orders=orders, rebalanced=True)
