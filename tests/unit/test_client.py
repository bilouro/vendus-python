"""Smoke tests for VendusClient construction."""

from __future__ import annotations

import pytest

from vendus import VendusClient
from vendus.services.documents import DocumentsService


def test_requires_api_key() -> None:
    with pytest.raises(ValueError, match="api_key is required"):
        VendusClient(api_key="")


def test_documents_property_returns_service() -> None:
    client = VendusClient(api_key="x")
    assert isinstance(client.documents, DocumentsService)


def test_documents_property_is_cached() -> None:
    client = VendusClient(api_key="x")
    assert client.documents is client.documents


def test_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VENDUS_API_KEY", "env-key")
    client = VendusClient.from_env()
    assert isinstance(client, VendusClient)


def test_from_env_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VENDUS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="VENDUS_API_KEY"):
        VendusClient.from_env()
