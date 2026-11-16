from typing import Any, Callable, TypeVar

from marshmallow import Schema

F = TypeVar("F", bound=Callable[..., Any])


class OpenAPIError(RuntimeError):
    """Raised at startup when the OpenAPI document cannot be built."""


def document(
    *,
    summary: str,
    request: type[Schema] | None = None,
    query: type[Schema] | None = None,
    success: type[Schema] | None = None,
    many: bool = False,
    status: int | None = None,
    public: bool = False,
    conflict: bool = False,
) -> Callable[[F], F]:
    """Attach documentation metadata to the view function. Changes no behavior."""

    def decorator(fn: F) -> F:
        fn.__openapi__ = {  # type: ignore[attr-defined]
            "summary": summary,
            "request": request,
            "query": query,
            "success": success,
            "many": many,
            "status": status,
            "public": public,
            "conflict": conflict,
        }
        return fn

    return decorator
