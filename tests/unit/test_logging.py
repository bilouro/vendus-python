"""Tests for PII redaction in logs."""

from __future__ import annotations

import logging

from vendus._logging import get_logger, redact


class TestRedaction:
    def test_redacts_fiscal_id(self) -> None:
        text = '{"fiscal_id": "123456789", "amount": "10"}'
        assert "123456789" not in redact(text)
        assert "[REDACTED]" in redact(text)

    def test_redacts_email(self) -> None:
        assert "alice@example.com" not in redact('{"email": "alice@example.com"}')

    def test_redacts_phone_and_mobile(self) -> None:
        s = '{"phone": "+351912345678", "mobile": "+351912345678"}'
        out = redact(s)
        assert "+351912345678" not in out

    def test_redacts_address(self) -> None:
        assert "Rua X" not in redact('{"address": "Rua X 123"}')

    def test_leaves_non_pii_alone(self) -> None:
        s = '{"type": "FT", "amount": "10.00"}'
        assert redact(s) == s


class TestFilter:
    def test_filter_applied_to_logger(self, caplog: logging.LogRecord) -> None:
        logger = get_logger()
        logger.setLevel(logging.INFO)
        with caplog.at_level(logging.INFO, logger="vendus"):
            logger.info('{"fiscal_id": "123456789"}')
        # The record's message has been redacted
        assert "123456789" not in caplog.text
