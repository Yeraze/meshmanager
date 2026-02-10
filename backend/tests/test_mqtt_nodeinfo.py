"""Tests for MQTT nodeinfo handling — ensures node fields aren't overwritten with None."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.mqtt import MqttCollector
from app.models import Node, Source


@pytest.fixture
def mqtt_source():
    """Create a mock MQTT source."""
    source = MagicMock(spec=Source)
    source.id = "test-source-id"
    source.name = "test-mqtt"
    source.mqtt_host = "localhost"
    source.mqtt_port = 1883
    source.mqtt_username = None
    source.mqtt_password = None
    source.mqtt_topic_pattern = "msh/US/#"
    return source


@pytest.fixture
def collector(mqtt_source):
    """Create an MqttCollector instance."""
    return MqttCollector(mqtt_source)


def _mock_db_with_existing_node(node):
    """Create a mock DB session that returns an existing node on query."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=node)
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestNodeinfoPreservesExistingFields:
    """Regression tests: nodeinfo with None fields must not overwrite existing data."""

    async def test_null_long_name_preserves_existing(self, collector):
        """A nodeinfo packet with no long_name must not blank an existing long_name."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            long_name="Wynwood Solar Weather Station",
            short_name="WSWS",
            hw_model="TBEAM",
        )
        db = _mock_db_with_existing_node(existing)

        await collector._handle_nodeinfo(db, {
            "from": 12345678,
            "nodeinfo": {"user": {}},
        })

        assert existing.long_name == "Wynwood Solar Weather Station"
        assert existing.short_name == "WSWS"
        assert existing.node_id == "!abcdef12"
        assert existing.hw_model == "TBEAM"

    async def test_partial_update_only_overwrites_provided_fields(self, collector):
        """A nodeinfo packet with only short_name should update that and leave the rest."""
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

        await collector._handle_nodeinfo(db, {
            "from": 12345678,
            "nodeinfo": {"user": {"shortName": "NEW1"}},
        })

        assert existing.short_name == "NEW1"
        assert existing.long_name == "Wynwood Solar Weather Station"
        assert existing.node_id == "!abcdef12"
        assert existing.hw_model == "TBEAM"
        assert existing.role == "2"

    async def test_full_update_overwrites_all_fields(self, collector):
        """A nodeinfo packet with all fields should update everything."""
        existing = Node(
            source_id="test-source-id",
            node_num=12345678,
            node_id="!abcdef12",
            long_name="Old Name",
            short_name="OLD1",
            hw_model="TBEAM",
        )
        db = _mock_db_with_existing_node(existing)

        await collector._handle_nodeinfo(db, {
            "from": 12345678,
            "nodeinfo": {
                "user": {
                    "id": "!newid123",
                    "longName": "New Name",
                    "shortName": "NEW1",
                    "hwModel": "HELTEC",
                    "role": "3",
                },
            },
        })

        assert existing.node_id == "!newid123"
        assert existing.long_name == "New Name"
        assert existing.short_name == "NEW1"
        assert existing.hw_model == "HELTEC"
        assert existing.role == "3"

    async def test_new_node_created_with_none_fields(self, collector):
        """A nodeinfo for an unknown node should create a new record even with sparse data."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        await collector._handle_nodeinfo(db, {
            "from": 99999999,
            "nodeinfo": {"user": {"longName": "Brand New Node"}},
        })

        assert db.add.call_count == 1
        node = db.add.call_args[0][0]
        assert isinstance(node, Node)
        assert node.node_num == 99999999
        assert node.long_name == "Brand New Node"
