import re
from typing import Any, Callable, TypeVar

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Flask
from marshmallow import Schema, fields

F = TypeVar("F", bound=Callable[..., Any])

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

# Endpoint function names of the documentation routes (added by register_docs).
DOCS_ENDPOINTS = frozenset({"docs_page", "openapi_json", "swagger_asset"})

_PATH_ARG = re.compile(r"<(?:[^:>]+:)?([^>]+)>")
_RESOURCE_ID = re.compile(r"/(?:boards|columns|cards|comments)/<")
_ERROR_REF = {"$ref": "#/components/schemas/ErrorEnvelope"}


class OpenAPIError(RuntimeError):
    """Raised at startup when the OpenAPI document cannot be built."""


class OneOfData(fields.Field):
    """Field whose apispec schema is a oneOf of arrays of the given schemas."""

    def __init__(self, *schemas: type[Schema], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.schemas = schemas


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


def _schema_name(schema: Any) -> str:
    name = schema.__name__ if isinstance(schema, type) else type(schema).__name__
    if name.endswith("Schema") and name != "Schema":
        name = name[: -len("Schema")]
    return name


def _error_response(description: str) -> dict:
    return {
        "description": description,
        "content": {"application/json": {"schema": _ERROR_REF}},
    }


def build_openapi(app: Flask) -> dict:
    """Build the OpenAPI 3 document from the URL map and the `document` metadata."""
    try:
        return _build(app)
    except OpenAPIError:
        raise
    except Exception as exc:  # any apispec or schema failure
        raise OpenAPIError(f"OpenAPI: cannot generate the document: {exc}") from exc


def _build(app: Flask) -> dict:
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
            "properties": {"error": {"type": "string"}},
            "required": ["error"],
        },
    )

    def one_of_data(converter: Any, field: Any, **_: Any) -> dict:
        # apispec binds attribute functions as methods of the field converter.
        if not isinstance(field, OneOfData):
            return {}
        return {
            "oneOf": [
                {"type": "array", "items": converter.resolve_nested_schema(s)}
                for s in field.schemas
            ]
        }

    plugin.converter.add_attribute_function(one_of_data)

    envelopes: dict[tuple[Any, bool], type[Schema]] = {}

    def envelope(inner: type[Schema] | None, many: bool) -> type[Schema]:
        key = (inner, many)
        if key not in envelopes:
            if inner is None:
                data = fields.Dict(required=True)
                name = "DataEnvelope"
            else:
                data = fields.Nested(inner, many=many, required=True)
                name = _schema_name(inner) + ("ListEnvelope" if many else "Envelope")
            envelopes[key] = Schema.from_dict({"data": data}, name=name)
        return envelopes[key]

    def cards_envelope() -> type[Schema]:
        from app.blueprints.cards.schema import TaskGroupOutSchema
        from app.common.schemas import CardOutSchema

        key = ("cards-one-of", True)
        if key not in envelopes:
            data = OneOfData(TaskGroupOutSchema, CardOutSchema, required=True)
            envelopes[key] = Schema.from_dict({"data": data}, name="CardsListEnvelope")
        return envelopes[key]

    rules = sorted(
        (
            r
            for r in app.url_map.iter_rules()
            if r.rule.startswith("/api/")
            and r.endpoint.rsplit(".", 1)[-1] not in DOCS_ENDPOINTS
        ),
        key=lambda r: r.rule,
    )
    for rule in rules:
        view = app.view_functions[rule.endpoint]
        meta = getattr(view, "__openapi__", None)
        if meta is None:
            raise OpenAPIError(f"OpenAPI: route {rule.rule} has no documentation")

        path = _PATH_ARG.sub(r"{\1}", rule.rule)
        arg_names = _PATH_ARG.findall(rule.rule)
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            parameters: list[dict] = [
                {
                    "in": "path",
                    "name": name,
                    "required": True,
                    "schema": {"type": "string", "format": "uuid"},
                }
                for name in arg_names
            ]
            if meta["query"] is not None:
                parameters.append({"in": "query", "schema": meta["query"]})

            if method == "GET" and rule.rule == "/api/cards":
                success_schema = cards_envelope()
            else:
                success_schema = envelope(meta["success"], meta["many"])
            status = meta["status"] or 200
            responses: dict[str, dict] = {
                str(status): {
                    "description": "Success",
                    "content": {"application/json": {"schema": success_schema}},
                }
            }
            if not meta["public"]:
                responses["401"] = _error_response("Unauthorized")
            if arg_names:
                responses["404"] = _error_response("Not found")
            if _RESOURCE_ID.search(rule.rule):
                responses["403"] = _error_response("Forbidden")
            if meta["request"] is not None or meta["query"] is not None:
                responses["400"] = _error_response("Validation error")
            if meta["conflict"]:
                responses["409"] = _error_response("Conflict")

            operation: dict[str, Any] = {
                "tags": [rule.endpoint.split(".")[0]],
                "summary": meta["summary"],
                "responses": responses,
                "security": [] if meta["public"] else [{"bearerAuth": []}],
            }
            if parameters:
                operation["parameters"] = parameters
            if meta["request"] is not None:
                operation["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": meta["request"]}},
                }
            spec.path(path=path, operations={method.lower(): operation})

    return spec.to_dict()


_DOCS_HTML = """<!DOCTYPE html>
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
  window.ui = SwaggerUI({url: "/api/openapi.json", dom_id: "#swagger-ui"});
};
</script>
</body>
</html>
"""


def register_docs(app: Flask) -> None:
    """Add GET /api/docs, GET /api/openapi.json and GET /swagger-ui/<path>."""
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
