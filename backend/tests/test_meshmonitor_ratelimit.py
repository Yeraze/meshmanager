"""Tests for MeshMonitorCollector._api_get rate-limit handling."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.collectors.meshmonitor import MeshMonitorCollector


@pytest.fixture()
def collector():
    """Create a MeshMonitorCollector with a fake source."""
    source = SimpleNamespace(
        id="source-1",
        name="test-source",
        url="http://localhost",
        api_token="test-token",
        poll_interval_seconds=60,
        historical_days_back=7,
    )
    return MeshMonitorCollector(source)


def _mock_response(status_code: int, headers: dict | None = None) -> httpx.Response:
    """Build a minimal httpx.Response with the given status and headers."""
    resp = httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("GET", "http://localhost/test"),
    )
    return resp


@pytest.mark.asyncio
async def test_returns_immediately_on_200(collector):
    """A 200 response is returned without any retry."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200))

    resp = await collector._api_get(client, "http://localhost/test", {"Accept": "application/json"})

    assert resp.status_code == 200
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_returns_immediately_on_non_429_error(collector):
    """Non-429 error responses are returned without retry."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(500))

    resp = await collector._api_get(client, "http://localhost/test", {"Accept": "application/json"})

    assert resp.status_code == 500
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(collector):
    """A 429 followed by a 200 succeeds after one retry."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=[_mock_response(429), _mock_response(200)])

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        resp = await collector._api_get(
            client, "http://localhost/test", {"Accept": "application/json"}
        )

    assert resp.status_code == 200
    assert client.get.call_count == 2


@pytest.mark.asyncio
async def test_respects_retry_after_header(collector):
    """The delay uses the Retry-After header value when present."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(
        side_effect=[
            _mock_response(429, headers={"Retry-After": "7"}),
            _mock_response(200),
        ]
    )

    with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
        resp = await collector._api_get(
            client, "http://localhost/test", {"Accept": "application/json"}
        )

    assert resp.status_code == 200
    mock_sleep.assert_awaited_once_with(7.0)


@pytest.mark.asyncio
async def test_exponential_backoff_without_retry_after(collector):
    """Without Retry-After, backoff doubles each attempt (base_delay * 2^attempt)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(
        side_effect=[
            _mock_response(429),
            _mock_response(429),
            _mock_response(429),
            _mock_response(200),
        ]
    )

    with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
        resp = await collector._api_get(
            client,
            "http://localhost/test",
            {"Accept": "application/json"},
            base_delay=1.0,
        )

    assert resp.status_code == 200
    delays = [call.args[0] for call in mock_sleep.await_args_list]
    assert delays == [1.0, 2.0, 4.0]  # 1*2^0, 1*2^1, 1*2^2


@pytest.mark.asyncio
async def test_backoff_capped_at_120_seconds(collector):
    """Exponential backoff is capped at 120 seconds."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(
        side_effect=[
            _mock_response(429),
            _mock_response(200),
        ]
    )

    with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
        resp = await collector._api_get(
            client,
            "http://localhost/test",
            {"Accept": "application/json"},
            base_delay=200.0,  # 200 * 2^0 = 200, capped to 120
        )

    assert resp.status_code == 200
    mock_sleep.assert_awaited_once_with(120.0)


@pytest.mark.asyncio
async def test_gives_up_after_max_retries(collector):
    """After max_retries 429s, the final attempt response is returned."""
    client = AsyncMock(spec=httpx.AsyncClient)
    # max_retries=3 means 3 retries in the loop + 1 final attempt = 4 total GETs
    client.get = AsyncMock(return_value=_mock_response(429))

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        resp = await collector._api_get(
            client,
            "http://localhost/test",
            {"Accept": "application/json"},
            max_retries=3,
        )

    # 3 retries in the loop + 1 final attempt
    assert client.get.call_count == 4
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_passes_params_through(collector):
    """Query params are forwarded to the underlying client.get call."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200))

    params = {"limit": 100, "offset": 50}
    await collector._api_get(
        client, "http://localhost/test", {"Accept": "application/json"}, params=params
    )

    client.get.assert_called_once_with(
        "http://localhost/test",
        headers={"Accept": "application/json"},
        params=params,
    )
