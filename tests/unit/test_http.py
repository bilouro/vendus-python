"""Tests for HttpTransport — auth header, retries, status code mapping."""

from __future__ import annotations

import base64

import httpx
import pytest
import respx

from vendus._auth import basic_auth
from vendus._http import HttpTransport
from vendus.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    TransportError,
)

_BASE = "https://www.vendus.pt/ws"


def _make_transport(max_retries: int = 3) -> HttpTransport:
    return HttpTransport(
        auth=basic_auth("test-key"),
        base_url=_BASE,
        timeout=1.0,
        max_retries=max_retries,
        backoff_factor=0.0,  # No real wait in tests
    )


@pytest.fixture
def transport() -> HttpTransport:
    return _make_transport()


class TestAuthHeader:
    def test_basic_auth_header_is_sent(self, transport: HttpTransport) -> None:
        expected = base64.b64encode(b"test-key:").decode()
        with respx.mock(base_url=_BASE) as router:
            route = router.get("/v1.1/documents/1").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": 1,
                        "type": "FT",
                        "number": "x",
                        "amount_gross": "0",
                        "amount_net": "0",
                    },
                )
            )
            transport.request("GET", "/v1.1/documents/1")
            sent = route.calls.last.request
            assert sent.headers["authorization"] == f"Basic {expected}"


class TestStatusMapping:
    @pytest.mark.parametrize(
        ("status", "exc"),
        [
            (401, AuthenticationError),
            (403, AuthorizationError),
            (404, NotFoundError),
            (429, RateLimitError),
            (400, APIError),
            (500, APIError),
        ],
    )
    def test_status_maps_to_exception(
        self, transport: HttpTransport, status: int, exc: type[Exception]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(
                return_value=httpx.Response(status, json={"error": "boom"})
            )
            # Stop retries from masking the final exception for retryable codes
            t = _make_transport(max_retries=0) if status in (429, 500) else transport
            with pytest.raises(exc):
                t.request("GET", "/v1.1/documents/1")

    def test_error_message_extracted(self, transport: HttpTransport) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(
                return_value=httpx.Response(404, json={"message": "Not found"})
            )
            with pytest.raises(NotFoundError, match="Not found"):
                transport.request("GET", "/v1.1/documents/1")


class TestRetries:
    def test_get_retries_on_503(self) -> None:
        transport = _make_transport(max_retries=2)
        with respx.mock(base_url=_BASE) as router:
            route = router.get("/v1.1/documents").mock(
                side_effect=[
                    httpx.Response(503),
                    httpx.Response(503),
                    httpx.Response(200, json=[]),
                ]
            )
            response = transport.request("GET", "/v1.1/documents")
            assert response.status_code == 200
            assert route.call_count == 3

    def test_post_does_not_retry_without_external_reference(self) -> None:
        transport = _make_transport(max_retries=3)
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(503, json={"error": "down"})
            )
            with pytest.raises(APIError):
                transport.request("POST", "/v1.1/documents", json={"type": "FT"})
            assert route.call_count == 1

    def test_post_retries_with_external_reference(self) -> None:
        transport = _make_transport(max_retries=2)
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                side_effect=[
                    httpx.Response(503),
                    httpx.Response(
                        200,
                        json={
                            "id": 1,
                            "type": "FT",
                            "number": "x",
                            "amount_gross": "0",
                            "amount_net": "0",
                        },
                    ),
                ]
            )
            response = transport.request(
                "POST",
                "/v1.1/documents",
                json={"type": "FT", "external_reference": "order-1"},
            )
            assert response.status_code == 200
            assert route.call_count == 2

    def test_delete_never_retries(self) -> None:
        transport = _make_transport(max_retries=3)
        with respx.mock(base_url=_BASE) as router:
            route = router.delete("/v1.1/documents/1").mock(
                return_value=httpx.Response(503, json={"error": "x"})
            )
            with pytest.raises(APIError):
                transport.request("DELETE", "/v1.1/documents/1")
            assert route.call_count == 1


class TestTransportFailures:
    def test_timeout_raises_transport_error(self) -> None:
        transport = _make_transport(max_retries=0)
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents").mock(side_effect=httpx.TimeoutException("boom"))
            with pytest.raises(TransportError):
                transport.request("GET", "/v1.1/documents")


class TestAsync:
    async def test_async_basic_get(self) -> None:
        transport = _make_transport()
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": 1,
                        "type": "FT",
                        "number": "x",
                        "amount_gross": "0",
                        "amount_net": "0",
                    },
                )
            )
            response = await transport.request_async("GET", "/v1.1/documents/1")
            assert response.status_code == 200

    async def test_async_post_retries_with_external_reference(self) -> None:
        transport = _make_transport(max_retries=2)
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                side_effect=[
                    httpx.Response(503),
                    httpx.Response(
                        200,
                        json={
                            "id": 1,
                            "type": "FT",
                            "number": "x",
                            "amount_gross": "0",
                            "amount_net": "0",
                        },
                    ),
                ]
            )
            response = await transport.request_async(
                "POST",
                "/v1.1/documents",
                json={"type": "FT", "external_reference": "order-1"},
            )
            assert response.status_code == 200
            assert route.call_count == 2
