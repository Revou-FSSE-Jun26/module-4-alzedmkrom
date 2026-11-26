"""Pagination envelope helper (BE-ERR-03)."""
import math


def paginate(query, page, per_page):
    """Return (items, total, pages) for a Flask-SQLAlchemy query. Out-of-range input is rejected by the schema."""
    total = query.order_by(None).count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    pages = math.ceil(total / per_page) if total else 0
    return items, total, pages


def envelope(items, page, per_page, total, pages):
    return {"items": items, "page": page, "per_page": per_page, "total": total, "pages": pages}
