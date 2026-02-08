"""Tests for protobuf decryption in protobuf service."""

import base64
import struct

import pytest

from app.services.protobuf import (
    MESHTASTIC_DEFAULT_KEY,
    _decrypt_packet,
    _expand_psk,
    decode_meshtastic_packet,
)


class TestExpandPsk:
    """Tests for _expand_psk() key expansion."""

    def test_default_key_byte_1(self):
        """Single byte 0x01 (AQ==) returns default key unchanged."""
        key = _expand_psk("AQ==")
        assert key == MESHTASTIC_DEFAULT_KEY
        assert len(key) == 16

    def test_single_byte_variant(self):
        """Single byte 0x02 replaces last byte of default key."""
        key = _expand_psk("Ag==")
        assert key is not None
        assert len(key) == 16
        assert key[-1:] == b"\x02"
        assert key[:-1] == MESHTASTIC_DEFAULT_KEY[:-1]

    def test_full_16_byte_key(self):
        """16-byte key is used as-is."""
        raw = b"\x01" * 16
        b64 = base64.b64encode(raw).decode()
        key = _expand_psk(b64)
        assert key == raw

    def test_full_32_byte_key(self):
        """32-byte key is used as-is (AES-256)."""
        raw = b"\xab" * 32
        b64 = base64.b64encode(raw).decode()
        key = _expand_psk(b64)
        assert key == raw

    def test_empty_string_returns_none(self):
        """Empty base64 (empty bytes) returns None."""
        assert _expand_psk("") is None

    def test_zero_byte_returns_none(self):
        """Single zero byte returns None (no encryption)."""
        assert _expand_psk("AA==") is None

    def test_invalid_base64_returns_none(self):
        """Invalid base64 input returns None."""
        assert _expand_psk("not-valid-base64!!!") is None

    def test_default_key_base64_roundtrip(self):
        """The default key base64 string decodes correctly."""
        key = _expand_psk("1PG7OiApB1nwvP+rz05pAQ==")
        assert key == MESHTASTIC_DEFAULT_KEY


class TestDecryptPacket:
    """Tests for _decrypt_packet() AES-CTR decryption."""

    def _encrypt(self, data_bytes: bytes, key: bytes, packet_id: int, from_node: int) -> bytes:
        """Helper: encrypt bytes using AES-CTR with Meshtastic nonce format."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        nonce = struct.pack("<QI", packet_id, from_node) + b"\x00" * 4
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
        encryptor = cipher.encryptor()
        return encryptor.update(data_bytes) + encryptor.finalize()

    def test_decrypt_with_correct_key(self):
        """Decryption succeeds with the correct key."""
        try:
            from meshtastic import mesh_pb2, portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        # Build a Data message
        data_msg = mesh_pb2.Data()
        data_msg.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
        data_msg.payload = b"Hello, mesh!"
        serialized = data_msg.SerializeToString()

        packet_id = 12345
        from_node = 0xDEADBEEF
        encrypted = self._encrypt(serialized, MESHTASTIC_DEFAULT_KEY, packet_id, from_node)

        result = _decrypt_packet(encrypted, packet_id, from_node, [MESHTASTIC_DEFAULT_KEY])
        assert result is not None
        assert result.portnum == portnums_pb2.PortNum.TEXT_MESSAGE_APP
        assert result.payload == b"Hello, mesh!"

    def test_decrypt_with_wrong_key_returns_none(self):
        """Decryption with wrong key returns None."""
        try:
            from meshtastic import mesh_pb2, portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        data_msg = mesh_pb2.Data()
        data_msg.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
        data_msg.payload = b"Secret"
        serialized = data_msg.SerializeToString()

        packet_id = 99999
        from_node = 0x12345678
        encrypted = self._encrypt(serialized, MESHTASTIC_DEFAULT_KEY, packet_id, from_node)

        wrong_key = b"\xff" * 16
        result = _decrypt_packet(encrypted, packet_id, from_node, [wrong_key])
        assert result is None

    def test_decrypt_tries_multiple_keys(self):
        """Decryption tries each key and succeeds on the matching one."""
        try:
            from meshtastic import mesh_pb2, portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        data_msg = mesh_pb2.Data()
        data_msg.portnum = portnums_pb2.PortNum.POSITION_APP
        data_msg.payload = b"\x08\x01"
        serialized = data_msg.SerializeToString()

        packet_id = 55555
        from_node = 0xAABBCCDD
        real_key = b"\x42" * 16
        encrypted = self._encrypt(serialized, real_key, packet_id, from_node)

        wrong_key = b"\x00" * 16
        result = _decrypt_packet(encrypted, packet_id, from_node, [wrong_key, real_key])
        assert result is not None
        assert result.portnum == portnums_pb2.PortNum.POSITION_APP

    def test_empty_keys_returns_none(self):
        """Empty key list returns None."""
        result = _decrypt_packet(b"\x00" * 20, 1, 1, [])
        assert result is None


class TestDecryptIntegration:
    """Integration tests for decode_meshtastic_packet with encryption."""

    def _build_encrypted_envelope(
        self, key: bytes, portnum: int, payload: bytes, packet_id: int = 1000, from_node: int = 42
    ) -> bytes:
        """Build a ServiceEnvelope with an encrypted MeshPacket."""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from meshtastic import mesh_pb2, mqtt_pb2
        except ImportError:
            pytest.skip("meshtastic or cryptography not available")

        # Build the inner Data message
        data_msg = mesh_pb2.Data()
        data_msg.portnum = portnum
        data_msg.payload = payload
        data_serialized = data_msg.SerializeToString()

        # Encrypt it
        nonce = struct.pack("<QI", packet_id, from_node) + b"\x00" * 4
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(data_serialized) + encryptor.finalize()

        # Build the MeshPacket with encrypted field
        packet = mesh_pb2.MeshPacket()
        setattr(packet, "from", from_node)
        packet.to = 0xFFFFFFFF
        packet.id = packet_id
        packet.encrypted = encrypted

        # Wrap in ServiceEnvelope
        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.packet.CopyFrom(packet)
        return envelope.SerializeToString()

    def test_encrypted_text_message_decoded(self):
        """An encrypted TEXT_MESSAGE_APP is decrypted and decoded."""
        try:
            from meshtastic import portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        envelope_bytes = self._build_encrypted_envelope(
            key=MESHTASTIC_DEFAULT_KEY,
            portnum=portnums_pb2.PortNum.TEXT_MESSAGE_APP,
            payload=b"Hello from encrypted!",
        )

        result = decode_meshtastic_packet(envelope_bytes, encryption_keys=[MESHTASTIC_DEFAULT_KEY])
        assert result is not None
        assert result.get("portnum") == "TEXT_MESSAGE_APP"
        assert result.get("text") == "Hello from encrypted!"

    def test_encrypted_position_decoded(self):
        """An encrypted POSITION_APP is decrypted and the inner protobuf decoded."""
        try:
            from meshtastic import mesh_pb2, portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        pos = mesh_pb2.Position()
        pos.latitude_i = 259560000
        pos.longitude_i = -801810000
        pos_bytes = pos.SerializeToString()

        envelope_bytes = self._build_encrypted_envelope(
            key=MESHTASTIC_DEFAULT_KEY,
            portnum=portnums_pb2.PortNum.POSITION_APP,
            payload=pos_bytes,
        )

        result = decode_meshtastic_packet(envelope_bytes, encryption_keys=[MESHTASTIC_DEFAULT_KEY])
        assert result is not None
        assert result.get("portnum") == "POSITION_APP"
        payload = result.get("payload")
        assert isinstance(payload, dict)
        assert "latitudeI" in payload

    def test_no_keys_skips_encrypted(self):
        """Without encryption keys, encrypted packets return no portnum."""
        try:
            from meshtastic import portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        envelope_bytes = self._build_encrypted_envelope(
            key=MESHTASTIC_DEFAULT_KEY,
            portnum=portnums_pb2.PortNum.TEXT_MESSAGE_APP,
            payload=b"Secret",
        )

        result = decode_meshtastic_packet(envelope_bytes, encryption_keys=None)
        assert result is not None
        assert "portnum" not in result  # encrypted, but no keys to decrypt

    def test_wrong_keys_skips_encrypted(self):
        """With wrong encryption keys, encrypted packets return no portnum."""
        try:
            from meshtastic import portnums_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        envelope_bytes = self._build_encrypted_envelope(
            key=MESHTASTIC_DEFAULT_KEY,
            portnum=portnums_pb2.PortNum.TEXT_MESSAGE_APP,
            payload=b"Secret",
        )

        wrong_key = b"\xff" * 16
        result = decode_meshtastic_packet(envelope_bytes, encryption_keys=[wrong_key])
        assert result is not None
        assert "portnum" not in result
