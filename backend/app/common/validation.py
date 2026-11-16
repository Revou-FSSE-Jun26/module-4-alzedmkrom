import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import request
from marshmallow import EXCLUDE, RAISE, Schema, ValidationError, fields, validate

from app.common.errors import NotFound, ValidationFailed

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_DIGITS_RE = re.compile(r"[0-9]{1,18}")


class Text(fields.String):
    """str only. Rejects NUL and values that cannot be encoded as UTF-8 (D11)."""

    default_error_messages = {
        "invalid": "Not a valid string.",
        "invalid_chars": "Contains characters that are not allowed.",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str):
            raise self.make_error("invalid")
        if "\x00" in value:
            raise self.make_error("invalid_chars")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise self.make_error("invalid_chars") from None
        return value


class Email(Text):
    """Trim, lower-case, then 3..254 characters and marshmallow validate.Email."""

    default_error_messages = {"invalid_email": "Not a valid email address."}

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs).strip().lower()
        if not 3 <= len(value) <= 254:
            raise ValidationError("Length must be between 3 and 254.")
        try:
            validate.Email()(value)
        except ValidationError:
            raise self.make_error("invalid_email") from None
        return value


class StrictUUID(fields.UUID):
    """str in canonical 8-4-4-4-12 hexadecimal form only."""

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
            raise self.make_error("invalid_uuid")
        return uuid.UUID(value)


class OrderValue(fields.Float):
    """JSON number only (not bool, not str), finite, greater than 0."""

    default_error_messages = {"invalid": "Not a valid number."}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_nan", False)
        if kwargs.get("validate") is None:
            kwargs["validate"] = validate.Range(min=0, min_inclusive=False)
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise self.make_error("invalid")
        try:
            number = float(value)
        except OverflowError:
            raise self.make_error("invalid") from None
        if not math.isfinite(number):
            raise self.make_error("special")
        return number


class StrictBoolean(fields.Boolean):
    """isinstance(value, bool) only."""

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, bool):
            raise self.make_error("invalid", input=value)
        return value


class DigitsInt(fields.Integer):
    """Query integers: str of 1 to 18 ASCII digits only."""

    default_error_messages = {"invalid": "Not a valid integer."}

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str) or not _DIGITS_RE.fullmatch(value):
            raise self.make_error("invalid")
        return int(value)


class UTCDateTime(fields.DateTime):
    """Output: the same instant in UTC, written with the offset +00:00."""

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()


class StrictSchema(Schema):
    class Meta:
        unknown = RAISE


class LenientSchema(Schema):
    class Meta:
        unknown = EXCLUDE


def parse_uuid(raw: str) -> uuid.UUID:
    if not isinstance(raw, str) or not _UUID_RE.fullmatch(raw):
        raise NotFound()
    return uuid.UUID(raw)


def _load(schema: Schema, data: Any) -> dict:
    try:
        return schema.load(data)
    except ValidationError as e:
        raise ValidationFailed(e.messages) from None


def load_body(schema: Schema) -> dict:
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        raise ValidationFailed("Request body must be a JSON object")
    return _load(schema, data)


def load_query(schema: Schema) -> dict:
    known = {f.data_key or name for name, f in schema.fields.items()}
    data: dict[str, str] = {}
    repeated: dict[str, list[str]] = {}
    for key in request.args:
        values = request.args.getlist(key)
        if len(values) > 1 and key in known:
            repeated[key] = ["Repeated query parameter."]
        else:
            data[key] = values[0]
    try:
        result = schema.load(data)
    except ValidationError as e:
        messages = dict(e.messages) if isinstance(e.messages, dict) else {}
        for key, errs in repeated.items():
            messages[key] = errs + list(messages.get(key, []))
        raise ValidationFailed(messages) from None
    if repeated:
        raise ValidationFailed(repeated)
    return result
