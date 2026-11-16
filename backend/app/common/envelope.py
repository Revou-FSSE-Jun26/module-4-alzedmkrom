from typing import Any, Mapping

from flask import Response, jsonify


def ok(payload: Any, status: int = 200) -> Response:
    response = jsonify({"data": payload})
    response.status_code = status
    return response


def error_response(status: int, message: str) -> Response:
    response = jsonify({"error": message})
    response.status_code = status
    return response


def _leaves(value: Any, path: str) -> list[tuple[str, str]]:
    if isinstance(value, Mapping):
        out: list[tuple[str, str]] = []
        for key in sorted(value, key=str):
            child = str(key) if not path else f"{path}.{key}"
            out.extend(_leaves(value[key], child))
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for index, item in enumerate(value):
            if isinstance(item, (Mapping, list, tuple)):
                child = str(index) if not path else f"{path}.{index}"
                out.extend(_leaves(item, child))
            else:
                out.append((path, str(item)))
        return out
    return [(path, str(value))]


def format_field_errors(messages: Mapping[str, Any]) -> str:
    """One ``<field>: <message>`` entry per leaf error, joined with ``; ``."""
    entries = []
    for path, message in _leaves(messages, ""):
        if path == "_schema" or path.endswith("._schema") or not path:
            entries.append(message)
        else:
            entries.append(f"{path}: {message}")
    return "; ".join(entries)
