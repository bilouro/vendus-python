"""Logging with PII redaction.

The `vendus` logger has a filter that scrubs fiscal_id, email, phone, mobile,
address, and postalcode from log records. Never bypass this logger.
"""

from __future__ import annotations

import logging
import re
from typing import Any

_logger = logging.getLogger("vendus")

# Patterns are deliberately broad — false positives are fine; false negatives are not.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'"fiscal_id"\s*:\s*"[^"]*"'), '"fiscal_id": "[REDACTED]"'),
    (re.compile(r'"email"\s*:\s*"[^"]*"'), '"email": "[REDACTED]"'),
    (re.compile(r'"billing_email"\s*:\s*"[^"]*"'), '"billing_email": "[REDACTED]"'),
    (re.compile(r'"phone"\s*:\s*"[^"]*"'), '"phone": "[REDACTED]"'),
    (re.compile(r'"mobile"\s*:\s*"[^"]*"'), '"mobile": "[REDACTED]"'),
    (re.compile(r'"address"\s*:\s*"[^"]*"'), '"address": "[REDACTED]"'),
    (re.compile(r'"postalcode"\s*:\s*"[^"]*"'), '"postalcode": "[REDACTED]"'),
)


def _redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class _PIIRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            record.args = (
                tuple(_redact(a) if isinstance(a, str) else a for a in record.args)
                if isinstance(record.args, tuple)
                else record.args
            )
        return True


def get_logger() -> logging.Logger:
    """Return the SDK logger with PII redaction installed."""
    if not any(isinstance(f, _PIIRedactionFilter) for f in _logger.filters):
        _logger.addFilter(_PIIRedactionFilter())
    return _logger


# Public helper for tests
def redact(value: Any) -> str:
    """Redact PII from an arbitrary value's str() representation."""
    return _redact(str(value))
