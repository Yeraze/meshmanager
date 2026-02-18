"""Tests for MeshMonitorCollector position history collection."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.collectors.meshmonitor import MeshMonitorCollector
from app.models.telemetry import TelemetryType


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


def _mock_response(status_code: int, data: dict | list | None = None) -> httpx.Response:
    """Build a minimal httpx.Response with JSON body."""
    content = json.dumps(data or {}).encode()
    resp = httpx.Response(
        status_code=status_code,
        content=content,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "http://localhost/test"),
    )
    return resp


def _extract_all_values(db_mock) -> list[dict]:
    """Extract values dicts from all pg_insert calls."""
    results = []
    for call in db_mock.execute.call_args_list:
        stmt = call[0][0]
        compile = stmt.compile()
        results.append(compile.params)
    return results


class TestCollectNodePositionHistory:
    """Tests for _collect_node_position_history per-node fetcher."""

    @pytest.mark.asyncio
    async def test_basic_insert(self, collector):
        """Position records are inserted with correct fields."""
        api_response = {
            "success": True,
            "count": 2,
            "total": 2,
            "offset": 0,
            "limit": 1000,
            "data": [
                {
                    "timestamp": 1700000000000,
                    "latitude": 26.3913472,
                    "longitude": -80.1046528,
                    "packetId": 12345678,
                },
                {
                    "timestamp": 1700000060000,
                    "latitude": 26.3914000,
                    "longitude": -80.1047000,
                    "packetId": 12345679,
                },
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = _mock_response(200, api_response)
        collector._api_get = AsyncMock(return_value=mock_resp)

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_db.execute = AsyncMock(return_value=result_mock)

        with patch("app.collectors.meshmonitor.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            count, available = await collector._collect_node_position_history(
                client,
                {"Accept": "application/json"},
                "!a2e4ff4c",
                node_num=2732916556,
                since_ms=1699999000000,
            )

        assert count == 2
        assert available is True

        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 2

        # Check first record
        vals = all_vals[0]
        assert vals["node_num"] == 2732916556
        assert vals["metric_name"] == "position"
        assert vals["telemetry_type"] == TelemetryType.POSITION
        assert vals["latitude"] == 26.3913472
        assert vals["longitude"] == -80.1046528
        assert vals["meshtastic_id"] == 12345678
        assert vals["received_at"] == datetime.fromtimestamp(1700000000, tz=UTC)

    @pytest.mark.asyncio
    async def test_pagination(self, collector):
        """When total > offset + count, the next page is fetched."""
        page1 = {
            "success": True,
            "count": 2,
            "total": 3,
            "offset": 0,
            "limit": 2,
            "data": [
                {"timestamp": 1700000000000, "latitude": 26.0, "longitude": -80.0, "packetId": 1},
                {"timestamp": 1700000060000, "latitude": 26.1, "longitude": -80.1, "packetId": 2},
            ],
        }
        page2 = {
            "success": True,
            "count": 1,
            "total": 3,
            "offset": 2,
            "limit": 2,
            "data": [
                {"timestamp": 1700000120000, "latitude": 26.2, "longitude": -80.2, "packetId": 3},
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        collector._api_get = AsyncMock(
            side_effect=[_mock_response(200, page1), _mock_response(200, page2)]
        )

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_db.execute = AsyncMock(return_value=result_mock)

        with patch("app.collectors.meshmonitor.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            count, available = await collector._collect_node_position_history(
                client,
                {"Accept": "application/json"},
                "!a2e4ff4c",
                node_num=123,
                since_ms=1699999000000,
                limit=2,
            )

        assert count == 3
        assert available is True
        # Should have been called twice (two pages)
        assert collector._api_get.call_count == 2

    @pytest.mark.asyncio
    async def test_404_returns_not_available(self, collector):
        """A 404 response returns (0, False) indicating endpoint not available."""
        client = AsyncMock(spec=httpx.AsyncClient)
        collector._api_get = AsyncMock(return_value=_mock_response(404))

        count, available = await collector._collect_node_position_history(
            client,
            {"Accept": "application/json"},
            "!a2e4ff4c",
            node_num=123,
        )

        assert count == 0
        assert available is False

    @pytest.mark.asyncio
    async def test_null_packet_id(self, collector):
        """Null packetId results in meshtastic_id being None."""
        api_response = {
            "success": True,
            "count": 1,
            "total": 1,
            "offset": 0,
            "limit": 1000,
            "data": [
                {
                    "timestamp": 1700000000000,
                    "latitude": 26.39,
                    "longitude": -80.10,
                    "packetId": None,
                },
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        collector._api_get = AsyncMock(return_value=_mock_response(200, api_response))

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_db.execute = AsyncMock(return_value=result_mock)

        with patch("app.collectors.meshmonitor.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            count, available = await collector._collect_node_position_history(
                client,
                {"Accept": "application/json"},
                "!a2e4ff4c",
                node_num=123,
            )

        assert count == 1
        assert available is True

        vals = _extract_all_values(mock_db)
        assert vals[0]["meshtastic_id"] is None

    @pytest.mark.asyncio
    async def test_dedup_via_on_conflict_do_nothing(self, collector):
        """Insert uses on_conflict_do_nothing for deduplication."""
        api_response = {
            "success": True,
            "count": 1,
            "total": 1,
            "offset": 0,
            "limit": 1000,
            "data": [
                {
                    "timestamp": 1700000000000,
                    "latitude": 26.39,
                    "longitude": -80.10,
                    "packetId": 100,
                },
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        collector._api_get = AsyncMock(return_value=_mock_response(200, api_response))

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_db.execute = AsyncMock(return_value=result_mock)

        with patch("app.collectors.meshmonitor.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            await collector._collect_node_position_history(
                client,
                {"Accept": "application/json"},
                "!a2e4ff4c",
                node_num=123,
            )

        # Verify the statement uses on_conflict_do_nothing
        call_args = mock_db.execute.call_args_list[0]
        stmt = call_args[0][0]
        # The compiled statement should contain ON CONFLICT DO NOTHING
        compiled = stmt.compile().string
        assert "ON CONFLICT" in compiled

    @pytest.mark.asyncio
    async def test_skips_records_without_timestamp(self, collector):
        """Records missing a timestamp are skipped."""
        api_response = {
            "success": True,
            "count": 2,
            "total": 2,
            "offset": 0,
            "limit": 1000,
            "data": [
                {
                    "timestamp": None,
                    "latitude": 26.39,
                    "longitude": -80.10,
                    "packetId": 100,
                },
                {
                    "timestamp": 1700000000000,
                    "latitude": 26.40,
                    "longitude": -80.11,
                    "packetId": 101,
                },
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        collector._api_get = AsyncMock(return_value=_mock_response(200, api_response))

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_db.execute = AsyncMock(return_value=result_mock)

        with patch("app.collectors.meshmonitor.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            count, available = await collector._collect_node_position_history(
                client,
                {"Accept": "application/json"},
                "!a2e4ff4c",
                node_num=123,
            )

        # count includes all items from data list, but only 1 was inserted
        assert available is True
        # Only 1 execute call (the record with a timestamp)
        assert mock_db.execute.call_count == 1
