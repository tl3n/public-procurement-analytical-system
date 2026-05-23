"""Tests for the resilient HTTP client."""

import httpx
import pytest

from app.collector import http_client


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Collapse backoff delays to zero so retry tests run instantly."""
    monkeypatch.setattr(http_client, "INITIAL_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(http_client, "MAX_DELAY_SECONDS", 0.0)


async def test_retries_5xx_then_succeeds():
    """A 503 followed by a 200 should produce one retry and return the 200."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await http_client.http_get_with_retry(
            client, "https://example.test/tenders"
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(calls) == 2


async def test_4xx_raises_without_retry():
    """A 400 is permanent — no retry, error raised immediately."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400, json={"error": "bad request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await http_client.http_get_with_retry(
                client, "https://example.test/tenders"
            )

    assert excinfo.value.response.status_code == 400
    assert len(calls) == 1


async def test_429_is_retried():
    """429 Too Many Requests is treated as transient and retried."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await http_client.http_get_with_retry(
            client, "https://example.test/tenders"
        )

    assert response.status_code == 200
    assert len(calls) == 2


async def test_persistent_5xx_exhausts_attempts():
    """When every attempt fails, the final HTTPStatusError is raised."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await http_client.http_get_with_retry(
                client, "https://example.test/tenders"
            )

    assert len(calls) == http_client.MAX_ATTEMPTS
