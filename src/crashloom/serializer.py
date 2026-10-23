"""Bounded, best-effort secret-aware serialization of captured values."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from crashloom.models import SerializedValue
from crashloom.redactor import REDACTED_MASK, SecretRedactor


class SafeSerializer:
    def __init__(self, redactor: SecretRedactor | None = None, max_depth: int = 4, max_items: int = 25, max_str_len: int = 500):
        self.redactor = redactor or SecretRedactor()
        self.max_depth = max_depth
        self.max_items = max_items
        self.max_str_len = max_str_len

    def _clean_text(self, value: str) -> tuple[str, bool, bool]:
        clean, redacted = self.redactor.redact_string(value)
        truncated = len(clean) > self.max_str_len
        if truncated:
            clean = clean[: self.max_str_len] + "…"
        return clean, redacted, truncated

    def serialize(
        self,
        value: Any,
        identifier_name: str = "",
        _depth: int = 0,
        _visited: set[int] | None = None,
    ) -> SerializedValue:
        if _visited is None:
            _visited = set()

        type_name = type(value).__qualname__
        if identifier_name and self.redactor.is_sensitive_identifier(identifier_name):
            mask_repr = repr(REDACTED_MASK)
            return SerializedValue(
                type_name=type_name,
                repr_str=mask_repr,
                is_reconstructible=True,
                python_expr=mask_repr,
                redacted=True,
                summary=REDACTED_MASK,
            )

        if value is None or isinstance(value, (bool, int)):
            rendered = repr(value)
            return SerializedValue(
                type_name=type_name,
                repr_str=rendered,
                is_reconstructible=True,
                python_expr=rendered,
                summary=value,
            )

        if isinstance(value, float):
            rendered = repr(value)
            if math.isnan(value):
                expression, summary = "float('nan')", "nan"
            elif math.isinf(value):
                summary = "-inf" if value < 0 else "inf"
                expression = "float('-inf')" if value < 0 else "float('inf')"
            else:
                expression, summary = rendered, value
            return SerializedValue(
                type_name=type_name,
                repr_str=rendered,
                is_reconstructible=True,
                python_expr=expression,
                summary=summary,
            )

        if isinstance(value, str):
            clean, was_redacted, truncated = self._clean_text(value)
            rendered = repr(clean)
            return SerializedValue(
                type_name="str",
                repr_str=rendered,
                is_reconstructible=True,
                python_expr=rendered,
                redacted=was_redacted,
                truncated=truncated,
                summary=clean,
            )

        is_mapping = isinstance(value, Mapping)
        is_sequence = isinstance(value, (list, tuple, set, frozenset))
        if is_mapping or is_sequence:
            ident = id(value)
            if ident in _visited:
                placeholder = f"<{type_name}: circular reference>"
                return SerializedValue(type_name, repr(placeholder), False, summary=placeholder)
            if _depth >= self.max_depth:
                placeholder = f"<{type_name}: max depth reached>"
                return SerializedValue(type_name, repr(placeholder), False, truncated=True, summary=placeholder)

            _visited.add(ident)
            try:
                truncated = len(value) > self.max_items
                if is_mapping:
                    parts: list[str] = []
                    summary: dict[str, Any] = {}
                    for index, (key, item) in enumerate(value.items()):
                        if index >= self.max_items:
                            break
                        try:
                            key_text = str(key)
                        except Exception:
                            key_text = f"key_{index}"
                        clean_key, key_redacted, key_truncated = self._clean_text(key_text)
                        item_serialized = self.serialize(item, key_text, _depth + 1, _visited)
                        safe_value = repr(REDACTED_MASK) if self.redactor.is_sensitive_identifier(key_text) else item_serialized.repr_str
                        parts.append(f"{clean_key!r}: {safe_value}")
                        summary[clean_key] = REDACTED_MASK if self.redactor.is_sensitive_identifier(key_text) else item_serialized.summary
                        truncated = truncated or key_redacted or key_truncated or item_serialized.truncated
                    body = ", ".join(parts)
                    rendered = "{" + body + (", …" if truncated and parts else "…" if truncated else "") + "}"
                    rendered, body_redacted, body_truncated = self._clean_text(rendered)
                    return SerializedValue(
                        type_name=type_name, repr_str=rendered, is_reconstructible=False,
                        redacted=body_redacted or any(self.redactor.is_sensitive_identifier(str(k)) for k in value.keys()),
                        truncated=truncated or body_truncated, summary=summary,
                    )

                items: list[str] = []
                summary_items: list[Any] = []
                was_redacted = False
                for index, item in enumerate(value):
                    if index >= self.max_items:
                        break
                    item_serialized = self.serialize(item, "", _depth + 1, _visited)
                    items.append(item_serialized.repr_str)
                    summary_items.append(item_serialized.summary)
                    was_redacted = was_redacted or item_serialized.redacted
                    truncated = truncated or item_serialized.truncated
                if isinstance(value, list):
                    rendered = "[" + ", ".join(items) + (", …" if truncated and items else "…" if truncated else "") + "]"
                elif isinstance(value, tuple):
                    inner = ", ".join(items) + (", …" if truncated and items else "…" if truncated else "")
                    rendered = "(" + inner + ("," if len(items) == 1 and not truncated else "") + ")"
                else:
                    rendered = "{" + ", ".join(items) + (", …" if truncated and items else "…" if truncated else "") + "}"
                rendered, was_redacted_text, text_truncated = self._clean_text(rendered)
                return SerializedValue(
                    type_name=type_name, repr_str=rendered, is_reconstructible=False,
                    redacted=was_redacted or was_redacted_text,
                    truncated=truncated or text_truncated, summary=summary_items,
                )
            finally:
                _visited.discard(ident)

        try:
            raw_repr = repr(value)
        except Exception:
            raw_repr = f"<{type_name}: repr unavailable>"
        safe_repr, was_redacted, truncated = self._clean_text(raw_repr)
        try:
            raw_summary = str(value)
        except Exception:
            raw_summary = safe_repr
        safe_summary, summary_redacted, summary_truncated = self._clean_text(raw_summary)
        return SerializedValue(
            type_name=type_name,
            repr_str=safe_repr,
            is_reconstructible=False,
            python_expr=None,
            redacted=was_redacted or summary_redacted,
            truncated=truncated or summary_truncated,
            summary=safe_summary,
        )
