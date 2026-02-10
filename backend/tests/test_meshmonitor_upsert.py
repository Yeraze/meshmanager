"""Tests for MeshMonitor _upsert_node — ensures node fields aren't overwritten with None."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.meshmonitor import MeshMonitorCollector
from app.models import Node, Source


@pytest.fixture
def meshmonitor_source():
    """Create a mock MeshMonitor source."""
    source = MagicMock(spec=Source)
    source.id = "test-source-id"
    source.name = "test-meshmonitor"
    source.meshmonitor_url = "http://localhost:8080"
    source.meshmonitor_api_key = "test-key"
    return source


@pytest.fixture
def collector(meshmonitor_source):
    """Create a MeshMonitorCollector instance."""
    return MeshMonitorCollector(meshmonitor_source)


def _mock_db_with_existing_node(node):
    """Create a mock DB session that returns an existing node on query."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=node)
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestUpsertNodePreservesExistingFields:
    """Regression tests: partial node data must not overwrite existing fields with None."""

    async def test_empty_user_preserves_existing_fields(self, collector):
        """A node update with no user data must not blank existing identity fields."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            long_name="Wynwood Solar Weather Station",
            short_name="WSWS",
            hw_model="TBEAM",
            snr=10.5,
            rssi=-80,
            hops_away=2,
            is_licensed=True,
        )
        db = _mock_db_with_existing_node(existing)

        await collector._upsert_node(db, {"nodeNum": 12345678})

        assert existing.long_name == "Wynwood Solar Weather Station"
        assert existing.short_name == "WSWS"
        assert existing.node_id == "!abcdef12"
        assert existing.hw_model == "TBEAM"
        assert existing.snr == 10.5
        assert existing.rssi == -80
        assert existing.hops_away == 2
        assert existing.is_licensed is True

    async def test_partial_update_only_overwrites_provided_fields(self, collector):
        """A node update with only shortName should update that and leave the rest."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            long_name="Wynwood Solar Weather Station",
            short_name="WSWS",
            hw_model="TBEAM",
            role="2",
        )
        db = _mock_db_with_existing_node(existing)

        await collector._upsert_node(db, {
            "nodeNum": 12345678,
            "user": {"shortName": "NEW1"},
        })

        assert existing.short_name == "NEW1"
        assert existing.long_name == "Wynwood Solar Weather Station"
        assert existing.node_id == "!abcdef12"
        assert existing.hw_model == "TBEAM"
        assert existing.role == "2"

    async def test_full_update_overwrites_all_fields(self, collector):
        """A node update with all fields should update everything."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            long_name="Old Name",
            short_name="OLD1",
            hw_model="TBEAM",
            snr=5.0,
            rssi=-90,
        )
        db = _mock_db_with_existing_node(existing)

        await collector._upsert_node(db, {
            "nodeNum": 12345678,
            "user": {
                "id": "!newid123",
                "longName": "New Name",
                "shortName": "NEW1",
                "hwModel": "HELTEC",
                "role": "3",
            },
            "snr": 12.0,
            "rssi": -70,
            "hopsAway": 1,
            "isLicensed": True,
        })

        assert existing.node_id == "!newid123"
        assert existing.long_name == "New Name"
        assert existing.short_name == "NEW1"
        assert existing.hw_model == "HELTEC"
        assert existing.role == "3"
        assert existing.snr == 12.0
        assert existing.rssi == -70
        assert existing.hops_away == 1
        assert existing.is_licensed is True

    async def test_is_licensed_not_overwritten_when_absent(self, collector):
        """A node update without isLicensed must not reset it to False."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            is_licensed=True,
        )
        db = _mock_db_with_existing_node(existing)

        await collector._upsert_node(db, {
            "nodeNum": 12345678,
            "user": {"shortName": "TEST"},
        })

        assert existing.is_licensed is True

    async def test_new_node_created_with_sparse_data(self, collector):
        """A node update for an unknown node should create a new record."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        await collector._upsert_node(db, {
            "nodeNum": 99999999,
            "user": {"longName": "Brand New Node"},
        })

        assert db.add.call_count == 1
        node = db.add.call_args[0][0]
        assert isinstance(node, Node)
        assert node.node_num == 99999999
        assert node.long_name == "Brand New Node"
