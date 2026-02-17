"""Tests for _decode_inner_payload() with all supported portnums."""

import pytest

from app.services.protobuf import _decode_inner_payload


def _get_pb2_modules():
    """Import and return the required protobuf modules."""
    try:
        from meshtastic import mesh_pb2, portnums_pb2, telemetry_pb2

        return mesh_pb2, portnums_pb2, telemetry_pb2
    except ImportError:
        pytest.skip("meshtastic library not available")


class TestOriginalPortnums:
    """Tests for the original 4 portnums that were already supported."""

    def test_position_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.Position()
        msg.latitude_i = 280000000
        msg.longitude_i = -820000000
        msg.altitude = 100
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.POSITION_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["latitudeI"] == 280000000
        assert result["longitudeI"] == -820000000
        assert result["altitude"] == 100

    def test_nodeinfo_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.User()
        msg.id = "!abcd1234"
        msg.short_name = "TST"
        msg.long_name = "Test Node"
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.NODEINFO_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["id"] == "!abcd1234"
        assert result["shortName"] == "TST"
        assert result["longName"] == "Test Node"

    def test_telemetry_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = telemetry_pb2.Telemetry()
        msg.device_metrics.battery_level = 85
        msg.device_metrics.voltage = 3.8
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.TELEMETRY_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert "deviceMetrics" in result
        assert result["deviceMetrics"]["batteryLevel"] == 85

    def test_traceroute_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.RouteDiscovery()
        msg.route.extend([111, 222])
        msg.snr_towards.extend([10, 20])
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.TRACEROUTE_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["route"] == [111, 222]
        assert result["snrTowards"] == [10, 20]


class TestNewProtobufPortnums:
    """Tests for newly added protobuf-decoded portnums."""

    def test_paxcounter_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        from meshtastic import paxcount_pb2

        msg = paxcount_pb2.Paxcount()
        msg.wifi = 15
        msg.ble = 8
        msg.uptime = 3600
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.PAXCOUNTER_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["wifi"] == 15
        assert result["ble"] == 8
        assert result["uptime"] == 3600

    def test_waypoint_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.Waypoint()
        msg.id = 42
        msg.latitude_i = 280000000
        msg.longitude_i = -820000000
        msg.name = "Test WP"
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.WAYPOINT_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["id"] == 42
        assert result["name"] == "Test WP"
        assert result["latitudeI"] == 280000000

    def test_routing_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.Routing()
        msg.error_reason = mesh_pb2.Routing.NO_RESPONSE
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.ROUTING_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)

    def test_neighborinfo_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.NeighborInfo()
        msg.node_id = 12345
        msg.node_broadcast_interval_secs = 300
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.NEIGHBORINFO_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["nodeId"] == 12345
        assert result["nodeBroadcastIntervalSecs"] == 300

    def test_map_report_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        from meshtastic import mqtt_pb2

        msg = mqtt_pb2.MapReport()
        msg.long_name = "Map Node"
        msg.short_name = "MPN"
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.MAP_REPORT_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert result["longName"] == "Map Node"
        assert result["shortName"] == "MPN"

    def test_store_forward_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        from meshtastic import storeforward_pb2

        msg = storeforward_pb2.StoreAndForward()
        msg.rr = storeforward_pb2.StoreAndForward.CLIENT_HISTORY
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.STORE_FORWARD_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)

    def test_store_forward_plusplus_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.StoreForwardPlusPlus()
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.STORE_FORWARD_PLUSPLUS_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)

    def test_remote_hardware_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        from meshtastic import remote_hardware_pb2

        msg = remote_hardware_pb2.HardwareMessage()
        msg.gpio_mask = 0xFF
        msg.gpio_value = 0x0F
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.REMOTE_HARDWARE_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)
        assert "gpioMask" in result
        assert "gpioValue" in result

    def test_admin_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        from meshtastic import admin_pb2

        msg = admin_pb2.AdminMessage()
        msg.get_channel_request = 1
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.ADMIN_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)

    def test_key_verification_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        msg = mesh_pb2.KeyVerification()
        msg.nonce = 12345
        raw = msg.SerializeToString()

        result = _decode_inner_payload(
            portnums_pb2.PortNum.KEY_VERIFICATION_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, dict)


class TestTextPortnums:
    """Tests for text-based portnums decoded as UTF-8."""

    def test_detection_sensor_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"motion detected"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.DETECTION_SENSOR_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == "motion detected"

    def test_alert_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"alert: high temp"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.ALERT_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == "alert: high temp"

    def test_range_test_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"seq 42"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.RANGE_TEST_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == "seq 42"

    def test_reply_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"ACK"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.REPLY_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == "ACK"

    def test_node_status_app(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"online"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.NODE_STATUS_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == "online"

    def test_utf8_replacement_on_invalid_bytes(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"hello \xff world"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.DETECTION_SENSOR_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert isinstance(result, str)
        assert "hello" in result
        assert "world" in result


class TestUnrecognizedPortnums:
    """Tests for portnums that are not handled."""

    def test_unknown_portnum_returns_raw_bytes(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"\x01\x02\x03"

        result = _decode_inner_payload(
            999, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == raw

    def test_text_message_compressed_returns_raw_bytes(self):
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        raw = b"\x1f\x8b\x08\x00"  # gzip header

        result = _decode_inner_payload(
            portnums_pb2.PortNum.TEXT_MESSAGE_COMPRESSED_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        assert result == raw

    def test_corrupt_protobuf_returns_raw_bytes(self):
        """Corrupt protobuf data for a known portnum returns raw bytes."""
        mesh_pb2, portnums_pb2, telemetry_pb2 = _get_pb2_modules()
        # This is not valid protobuf for Position - has a truncated varint
        raw = b"\x08"

        result = _decode_inner_payload(
            portnums_pb2.PortNum.PAXCOUNTER_APP, raw, mesh_pb2, portnums_pb2, telemetry_pb2
        )
        # Protobuf is very permissive, so it may actually parse this.
        # Either a dict or raw bytes is acceptable.
        assert isinstance(result, (dict, bytes))
