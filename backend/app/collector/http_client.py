"""Resilient HTTP client for the Prozorro API.

The Prozorro feed is read over an unauthenticated public endpoint with no published
service-level guarantees. We treat 5xx responses, timeouts, connection errors and 429
"Too Many Requests" as transient and retry them with exponential backoff. Other 4xx
responses are permanent client errors and are raised immediately without retry, since
repeating the same request cannot produce a different outcome.
"""

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

# Retry policy — 1, 2, 4, 8, 16, 32 seconds, six attempts total.
MAX_ATTEMPTS = 6
INITIAL_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 32.0

# Default timeout for a single attempt. The cumulative time across all retries can
# therefore reach ~3 minutes in the worst case, which is acceptable for a background
# collector but should not be reduced without considering tail-latency impact.
DEFAULT_TIMEOUT_SECONDS = 30.0


def create_client(
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    """Build an httpx client tuned for the Prozorro API (HTTP/2 enabled)."""
    return httpx.AsyncClient(http2=True, timeout=timeout)


async def http_get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
) -> httpx.Response:
    """GET ``url`` through ``client`` with exponential-backoff retry.

    Returns the successful response. Raises the last seen exception (network error
    or ``httpx.HTTPStatusError``) once the attempt budget is exhausted, or
    immediately on a non-retryable 4xx status.
    """
    last_exc: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            log.warning(
                "transient network error on attempt %d/%d for %s: %s",
                attempt + 1,
                MAX_ATTEMPTS,
                url,
                exc,
            )
        else:
            status = response.status_code
            if status < 400:
                return response
            if status != 429 and status < 500:
                # Permanent client error — repeating the same request cannot help.
                response.raise_for_status()
            # Otherwise the status is 5xx or 429 — retryable.
            last_exc = httpx.HTTPStatusError(
                f"transient HTTP {status}",
                request=response.request,
                response=response,
            )
            log.warning(
                "transient HTTP %d on attempt %d/%d for %s",
                status,
                attempt + 1,
                MAX_ATTEMPTS,
                url,
            )

        if attempt < MAX_ATTEMPTS - 1:
            delay = min(INITIAL_DELAY_SECONDS * (2**attempt), MAX_DELAY_SECONDS)
            await asyncio.sleep(delay)

    # Loop exhausted without returning — re-raise the last failure.
    assert last_exc is not None
    raise last_exc
