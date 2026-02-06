"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.schemas.source import MeshMonitorSourceCreate, MqttSourceCreate, MqttSourceUpdate


class TestAuthSchemas:
    """Tests for authentication schemas."""

    def test_login_request_valid(self):
        """LoginRequest should accept valid data."""
        request = LoginRequest(username="testuser", password="password123")
        assert request.username == "testuser"
        assert request.password == "password123"

    def test_login_request_missing_username(self):
        """LoginRequest should reject missing username."""
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_login_request_missing_password(self):
        """LoginRequest should reject missing password."""
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser")

    def test_register_request_valid(self):
        """RegisterRequest should accept valid data."""
        request = RegisterRequest(
            username="testuser",
            password="password123",
        )
        assert request.username == "testuser"
        assert request.password == "password123"
        assert request.email is None
        assert request.display_name is None

    def test_register_request_with_optional_fields(self):
        """RegisterRequest should accept optional email and display_name."""
        request = RegisterRequest(
            username="testuser",
            password="password123",
            email="test@example.com",
            display_name="Test User",
        )
        assert request.email == "test@example.com"
        assert request.display_name == "Test User"

    def test_register_request_missing_password(self):
        """RegisterRequest should reject missing password."""
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser")

    def test_register_request_short_username(self):
        """RegisterRequest should reject username less than 3 chars."""
        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", password="password123")

    def test_register_request_short_password(self):
        """RegisterRequest should reject password less than 8 chars."""
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", password="short")

    def test_change_password_request_valid(self):
        """ChangePasswordRequest should accept valid data."""
        request = ChangePasswordRequest(
            current_password="oldpassword",
            new_password="newpassword123",
        )
        assert request.current_password == "oldpassword"
        assert request.new_password == "newpassword123"

    def test_change_password_short_new_password(self):
        """ChangePasswordRequest should reject new password less than 8 chars."""
        with pytest.raises(ValidationError):
            ChangePasswordRequest(
                current_password="oldpassword",
                new_password="short",
            )


class TestSourceSchemas:
    """Tests for source schemas."""

    def test_meshmonitor_source_create_valid(self):
        """MeshMonitorSourceCreate should accept valid data."""
        source = MeshMonitorSourceCreate(
            name="Test MeshMonitor",
            url="https://meshmonitor.example.com",
        )
        assert source.name == "Test MeshMonitor"
        assert source.url == "https://meshmonitor.example.com"
        assert source.enabled is True  # Default value
        assert source.poll_interval_seconds == 300  # Default value

    def test_meshmonitor_source_create_with_enabled_false(self):
        """MeshMonitorSourceCreate should accept enabled=False."""
        source = MeshMonitorSourceCreate(
            name="Test MeshMonitor",
            url="https://meshmonitor.example.com",
            enabled=False,
        )
        assert source.enabled is False

    def test_meshmonitor_source_create_with_api_token(self):
        """MeshMonitorSourceCreate should accept api_token."""
        source = MeshMonitorSourceCreate(
            name="Test MeshMonitor",
            url="https://meshmonitor.example.com",
            api_token="my-secret-token",
        )
        assert source.api_token == "my-secret-token"

    def test_meshmonitor_source_create_strips_trailing_slash(self):
        """MeshMonitorSourceCreate should strip trailing slash from URL."""
        source = MeshMonitorSourceCreate(
            name="Test MeshMonitor",
            url="https://meshmonitor.example.com/",
        )
        assert source.url == "https://meshmonitor.example.com"

    def test_meshmonitor_source_create_missing_url(self):
        """MeshMonitorSourceCreate should reject missing URL."""
        with pytest.raises(ValidationError):
            MeshMonitorSourceCreate(name="Test MeshMonitor")

    def test_meshmonitor_source_create_missing_name(self):
        """MeshMonitorSourceCreate should reject missing name."""
        with pytest.raises(ValidationError):
            MeshMonitorSourceCreate(url="https://meshmonitor.example.com")

    def test_meshmonitor_source_create_invalid_url_scheme(self):
        """MeshMonitorSourceCreate should reject URLs without http(s) scheme."""
        with pytest.raises(ValidationError):
            MeshMonitorSourceCreate(
                name="Test MeshMonitor",
                url="ftp://meshmonitor.example.com",
            )

    def test_mqtt_source_create_valid(self):
        """MqttSourceCreate should accept valid data."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="mqtt.example.com",
            mqtt_port=1883,
            mqtt_topic_pattern="meshtastic/#",
        )
        assert source.name == "Test MQTT"
        assert source.mqtt_host == "mqtt.example.com"
        assert source.mqtt_port == 1883
        assert source.mqtt_topic_pattern == "meshtastic/#"

    def test_mqtt_source_create_with_auth(self):
        """MqttSourceCreate should accept authentication credentials."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="mqtt.example.com",
            mqtt_topic_pattern="meshtastic/#",
            mqtt_username="user",
            mqtt_password="pass",
        )
        assert source.mqtt_username == "user"
        assert source.mqtt_password == "pass"

    def test_mqtt_source_create_with_tls(self):
        """MqttSourceCreate should accept TLS flag."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="mqtt.example.com",
            mqtt_port=8883,
            mqtt_topic_pattern="meshtastic/#",
            mqtt_use_tls=True,
        )
        assert source.mqtt_use_tls is True

    def test_mqtt_source_create_missing_host(self):
        """MqttSourceCreate should reject missing host."""
        with pytest.raises(ValidationError):
            MqttSourceCreate(
                name="Test MQTT",
                mqtt_port=1883,
                mqtt_topic_pattern="meshtastic/#",
            )

    def test_mqtt_source_create_missing_topic_pattern(self):
        """MqttSourceCreate should reject missing topic pattern."""
        with pytest.raises(ValidationError):
            MqttSourceCreate(
                name="Test MQTT",
                mqtt_host="mqtt.example.com",
            )

    def test_mqtt_source_create_default_port(self):
        """MqttSourceCreate should have default port of 1883."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="mqtt.example.com",
            mqtt_topic_pattern="msh/#",
        )
        assert source.mqtt_port == 1883

    def test_mqtt_source_create_default_tls_false(self):
        """MqttSourceCreate should have default TLS as False."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="mqtt.example.com",
            mqtt_topic_pattern="msh/#",
        )
        assert source.mqtt_use_tls is False

    def test_mqtt_source_create_invalid_port(self):
        """MqttSourceCreate should reject invalid port numbers."""
        with pytest.raises(ValidationError):
            MqttSourceCreate(
                name="Test MQTT",
                mqtt_host="mqtt.example.com",
                mqtt_port=0,  # Invalid
                mqtt_topic_pattern="msh/#",
            )

        with pytest.raises(ValidationError):
            MqttSourceCreate(
                name="Test MQTT",
                mqtt_host="mqtt.example.com",
                mqtt_port=70000,  # Invalid - over 65535
                mqtt_topic_pattern="msh/#",
            )

    def test_mqtt_source_create_strips_host_whitespace(self):
        """MqttSourceCreate should strip whitespace from mqtt_host."""
        source = MqttSourceCreate(
            name="Test MQTT",
            mqtt_host="  mqtt.example.com  ",
            mqtt_topic_pattern="msh/#",
        )
        assert source.mqtt_host == "mqtt.example.com"

    def test_mqtt_source_update_strips_host_whitespace(self):
        """MqttSourceUpdate should strip whitespace from mqtt_host."""
        update = MqttSourceUpdate(mqtt_host="mqtt.example.com ")
        assert update.mqtt_host == "mqtt.example.com"

    def test_mqtt_source_update_none_host_unchanged(self):
        """MqttSourceUpdate should allow None mqtt_host."""
        update = MqttSourceUpdate()
        assert update.mqtt_host is None
