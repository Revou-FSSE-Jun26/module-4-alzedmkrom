"""OpenAPI 3 document generation and Swagger UI routes (BE-DOC-01, BE-DOC-03, BE-DOC-04).

`document(...)` is a decorator that attaches metadata to a route function as
`fn.__openapi__`.  It changes no runtime behaviour.

`build_openapi(app)` walks the URL map, reads that metadata, and returns a
dict that conforms to OpenAPI 3.0.3.  It raises `OpenAPIError` at startup if
any ``/api/`` route lacks metadata or if ``apispec`` fails.

`register_docs(app)` calls ``build_openapi`` once and wires three GET-only
routes onto the app (not a Blueprint):
  GET /api/docs            – Swagger UI HTML
  GET /api/openapi.json    – raw OpenAPI JSON
  GET /swagger-ui/<path>   – Swagger UI static assets
"""
from __future__ import annotations

import re
from typing import Any, Callable, TypeVar

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Flask
from marshmallow import Schema

F = TypeVar("F", bound=Callable[..., Any])

# Blueprint names used as OpenAPI tags (one per blueprint + health).
TAGS = (
    "auth",
    "users",
    "boards",
    "columns",
    "cards",
    "comments",
    "notifications",
    "analytics",
    "health",
)

# Endpoint names of the docs routes themselves — excluded from the document.
_DOCS_ENDPOINTS = frozenset({"docs_page", "openapi_json", "swagger_asset"})

_PATH_ARG = re.compile(r"<(?:[^:>]+:)?([^>]+)>")
_RESOURCE_ID = re.compile(r"/(?:boards|columns|cards|comments|notifications)/<")
_ERROR_REF = {"$ref": "#/components/schemas/ErrorEnvelope"}


class OpenAPIError(RuntimeError):
    """Raised at startup when the OpenAPI document cannot be built."""


def document(
    *,
    summary: str,
    tags: list[str],
    request: type[Schema] | None = None,
    success: type[Schema] | None = None,
    many: bool = False,
    query: type[Schema] | None = None,
    public: bool = False,
    status: int | None = None,
    conflict: bool = False,
) -> Callable[[F], F]:
    """Attach OpenAPI metadata to a route function (BE-DOC-03).

    Does not change runtime behaviour; only sets ``fn.__openapi__``.
    """
    meta: dict[str, Any] = {
        "summary": summary,
        "tags": tags,
        "request": request,
        "success": success,
        "many": many,
        "query": query,
        "public": public,
        "status": status,
        "conflict": conflict,
    }

    def decorator(fn: F) -> F:
        fn.__openapi__ = meta  # type: ignore[attr-defined]
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _schema_name(schema: Any) -> str:
    name = schema.__name__ if isinstance(schema, type) else type(schema).__name__
    if name.endswith("Schema") and name != "Schema":
        name = name[: -len("Schema")]
    return name


def _error_response(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": _ERROR_REF}},
    }


def _envelope(
    plugin: MarshmallowPlugin,
    envelopes: dict[tuple[Any, bool], type[Schema]],
    inner: type[Schema] | None,
    many: bool,
) -> type[Schema]:
    """Return (or create) an envelope schema that wraps *inner*."""
    from marshmallow import fields as mfields

    key = (inner, many)
    if key not in envelopes:
        if inner is None:
            data: Any = mfields.Dict(required=True)
            name = "DataEnvelope"
        else:
            data = mfields.Nested(inner, many=many, required=True)
            name = _schema_name(inner) + ("ListEnvelope" if many else "Envelope")
        envelopes[key] = Schema.from_dict({"data": data}, name=name)
    return envelopes[key]


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------

def build_openapi(app: Flask) -> dict[str, Any]:
    """Build the OpenAPI 3 document.  Raises ``OpenAPIError`` on failure."""
    try:
        return _build(app)
    except OpenAPIError:
        raise
    except Exception as exc:
        raise OpenAPIError(f"OpenAPI: cannot generate the document: {exc}") from exc


def _build(app: Flask) -> dict[str, Any]:
    plugin = MarshmallowPlugin(schema_name_resolver=_schema_name)
    spec = APISpec(
        title="RevoTask API",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[plugin],
    )
    for tag in TAGS:
        spec.tag({"name": tag})
    spec.components.security_scheme(
        "bearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    )
    spec.components.schema(
        "ErrorEnvelope",
        {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {
                            "nullable": True,
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                }
            },
        },
    )

    envelopes: dict[tuple[Any, bool], type[Schema]] = {}

    rules = sorted(
        (
            r
            for r in app.url_map.iter_rules()
            if r.rule.startswith("/api/")
            and r.endpoint not in _DOCS_ENDPOINTS
            and r.endpoint.rsplit(".", 1)[-1] not in _DOCS_ENDPOINTS
        ),
        key=lambda r: r.rule,
    )

    for rule in rules:
        view = app.view_functions[rule.endpoint]
        meta: dict[str, Any] | None = getattr(view, "__openapi__", None)
        if meta is None:
            raise OpenAPIError(
                f"OpenAPI: route {rule.rule!r} (endpoint {rule.endpoint!r}) "
                "has no @document metadata"
            )

        path = _PATH_ARG.sub(r"{\1}", rule.rule)
        arg_names = _PATH_ARG.findall(rule.rule)

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            parameters: list[dict[str, Any]] = [
                {
                    "in": "path",
                    "name": name,
                    "required": True,
                    "schema": {"type": "string", "format": "uuid"},
                }
                for name in arg_names
            ]
            if meta["query"] is not None:
                query_schema = meta["query"]()
                for field_name, field_obj in query_schema.fields.items():
                    field_schema = plugin.converter.field2property(field_obj)
                    param: dict[str, Any] = {
                        "in": "query",
                        "name": field_name,
                        "required": field_obj.required,
                        "schema": field_schema,
                    }
                    parameters.append(param)

            # Build success response
            success_schema = meta["success"]
            status_code = meta["status"] or (201 if method == "POST" else 200)
            if status_code == 204 or success_schema is None:
                success_response: dict[str, Any] = {"description": "Success"}
            else:
                wrapped = _envelope(plugin, envelopes, success_schema, meta["many"])
                success_response = {
                    "description": "Success",
                    "content": {"application/json": {"schema": wrapped}},
                }

            responses: dict[str, Any] = {str(status_code): success_response}
            if not meta["public"]:
                responses["401"] = _error_response("Unauthorized")
            if arg_names:
                responses["404"] = _error_response("Not found")
            if _RESOURCE_ID.search(rule.rule) and not meta["public"]:
                responses["403"] = _error_response("Forbidden")
            if meta["request"] is not None or meta["query"] is not None:
                responses["422"] = _error_response("Validation error")
            if meta["conflict"]:
                responses["409"] = _error_response("Conflict")

            operation: dict[str, Any] = {
                "tags": meta["tags"],
                "summary": meta["summary"],
                "responses": responses,
                "security": [] if meta["public"] else [{"bearerAuth": []}],
            }
            if parameters:
                operation["parameters"] = parameters
            if meta["request"] is not None:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": plugin.converter.schema2jsonschema(meta["request"]()),
                        }
                    },
                }

            spec.path(path=path, operations={method.lower(): operation})

    return spec.to_dict()


# ---------------------------------------------------------------------------
# Swagger UI HTML template
# ---------------------------------------------------------------------------

_DOCS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RevoTask API</title>
<link rel="stylesheet" href="/swagger-ui/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="/swagger-ui/swagger-ui-bundle.js"></script>
<script>
window.onload = function () {
  window.ui = SwaggerUI({ url: "/api/openapi.json", dom_id: "#swagger-ui" });
};
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register_docs(app: Flask) -> None:
    """Add the three documentation routes to *app* (BE-DOC-01).

    Called from ``create_app`` only when ``settings.swagger_enabled`` is true.
    The document is built once at startup; any error in a route's metadata
    raises ``OpenAPIError`` immediately so it is never silently swallowed.
    """
    import json

    from flask import Response, send_from_directory
    from swagger_ui_bundle import swagger_ui_path

    body = json.dumps(build_openapi(app), sort_keys=True).encode("utf-8")

    def docs_page() -> Response:
        return Response(_DOCS_HTML, mimetype="text/html")

    def openapi_json() -> Response:
        return Response(body, mimetype="application/json")

    def swagger_asset(filename: str) -> Response:
        return send_from_directory(swagger_ui_path, filename)

    app.add_url_rule("/api/docs", "docs_page", docs_page, methods=["GET"])
    app.add_url_rule("/api/openapi.json", "openapi_json", openapi_json, methods=["GET"])
    app.add_url_rule(
        "/swagger-ui/<path:filename>", "swagger_asset", swagger_asset, methods=["GET"]
    )
