"""Best-effort redaction for sensitive identifiers and common credential formats."""

from __future__ import annotations

import re
from typing import Final

REDACTED_MASK: Final[str] = "<REDACTED_BY_CRASHLOOM>"
SENSITIVE_KEY_PATTERNS: Final[tuple[str, ...]] = (
    "password", "passwd", "pwd", "secret", "api_key", "apikey", "access_key",
    "private_key", "client_secret", "auth_token", "access_token", "refresh_token", "token", "jwt",
    "bearer", "authorization", "dsn", "database_url", "stripe_key", "openai_api_key",
)

# These patterns deliberately target recognizable token formats and explicit
# credential assignments. They are useful safeguards, not a guarantee that all
# secrets can be identified in arbitrary application data.
SECRET_VALUE_REGEXES: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("AWS", re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b")),
    ("STRIPE", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_-]{8,}\b")),
    ("API_TOKEN", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GITHUB", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("SLACK", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("BEARER", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")),
)

SECRET_ASSIGNMENT_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?P<prefix>['\"]?(?:api[-_ ]?key|apikey|access[-_ ]?key|private[-_ ]?key|"
    r"client[-_ ]?secret|openai[-_ ]?api[-_ ]?key|stripe[-_ ]?key|password|passwd|pwd|"
    r"secret|access[-_ ]?token|refresh[-_ ]?token|auth[-_ ]?token|api[-_ ]?token|id[-_ ]?token|token|jwt|authorization|bearer|"
    r"database[-_ ]?url|dsn)['\"]?\s*[:=]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^,\s;&}]+)"
)


class SecretRedactor:
    """Redact sensitive variable names and a curated set of credential patterns."""

    def __init__(self, extra_sensitive_keys: tuple[str, ...] = (), entropy_threshold: float = 4.35):
        self.sensitive_keys = SENSITIVE_KEY_PATTERNS + tuple(k.lower() for k in extra_sensitive_keys)
        # Kept for API compatibility; entropy-based detection is not currently enabled.
        self.entropy_threshold = entropy_threshold

    def is_sensitive_identifier(self, name: str) -> bool:
        normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name.strip()).lower().replace("-", "_").replace(" ", "_")
        return any(pattern in normalized for pattern in self.sensitive_keys)

    def redact_string(self, text: str) -> tuple[str, bool]:
        if not text:
            return text, False

        result, assignment_count = SECRET_ASSIGNMENT_REGEX.subn(
            lambda match: f"{match.group('prefix')}{REDACTED_MASK}", text
        )
        redacted = assignment_count > 0
        for _label, regex in SECRET_VALUE_REGEXES:
            result, count = regex.subn(REDACTED_MASK, result)
            redacted = redacted or count > 0
        return result, redacted
