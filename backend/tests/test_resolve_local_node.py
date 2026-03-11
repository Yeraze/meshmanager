"""Tests for MeshMonitor _resolve_local_node — ensures correct gateway resolution."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.collectors.meshmonitor import MeshMonitorCollector
from app.models import Source


@pytest.fixture
def meshmonitor_source():
    """Create a mock MeshMonitor source."""
    source = MagicMock(spec=Source)
    source.id = "test-source-id"
    source.name = "test-meshmonitor"
    source.url = "http://localhost:8080"
    source.api_token = "test-token"
    source.local_node_num = None
    return source


@pytest.fixture
def collector(meshmonitor_source):
    """Create a MeshMonitorCollector instance."""
    return MeshMonitorCollector(meshmonitor_source)


def _mock_status_response(node_num, status_code=200):
    """Create a mock httpx.Response for /api/status."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    if status_code == 200:
        response.json.return_value = {
            "status": "ok",
            "connection": {
                "connected": True,
                "localNode": {
                    "nodeNum": node_num,
                    "nodeId": "!abcdef12",
                    "longName": "Test Node",
                    "shortName": "TST",
                },
            },
        }
    else:
        response.json.return_value = {"error": "not found"}
    return response


class TestResolveLocalNode:
    """Tests for _resolve_local_node gateway resolution."""

    @patch("app.collectors.meshmonitor.async_session_maker")
    async def test_successful_fetch_from_api_status(self, mock_session_maker, collector):
        """Successful /api/status fetch sets _local_node_num and persists to DB."""
        mock_source = MagicMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = mock_source
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=_mock_status_response(12345678))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num == 12345678
        mock_source.local_node_num = 12345678  # Would have been set

    @patch("app.collectors.meshmonitor.async_session_maker")
    async def test_api_failure_falls_back_to_cached_value(self, mock_session_maker, collector):
        """When /api/status fails and _local_node_num is already cached, keep it."""
        collector._local_node_num = 99999999

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num == 99999999

    async def test_api_failure_falls_back_to_stored_source_value(self, collector):
        """When /api/status fails and no cache, use source.local_node_num."""
        collector.source.local_node_num = 77777777

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num == 77777777

    async def test_api_returns_no_local_node_falls_back(self, collector):
        """When /api/status returns no localNode, fall back to stored value."""
        collector.source.local_node_num = 55555555

        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {
            "status": "ok",
            "connection": {"connected": False, "localNode": None},
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num == 55555555

    async def test_api_returns_500_falls_back(self, collector):
        """When /api/status returns non-200, fall back to stored value."""
        collector.source.local_node_num = 33333333

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=_mock_status_response(None, status_code=500))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num == 33333333

    async def test_no_fallback_available_leaves_none(self, collector):
        """When everything fails, _local_node_num stays None."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._resolve_local_node()

        assert collector._local_node_num is None
