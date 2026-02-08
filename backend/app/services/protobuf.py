"""Protobuf decoding for Meshtastic packets."""

import base64
import logging
import struct
from typing import Any

from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)

# Meshtastic default channel key (AES-128, "LongFast" / simple key index 1)
MESHTASTIC_DEFAULT_KEY = base64.b64decode("1PG7OiApB1nwvP+rz05pAQ==")


def _expand_psk(psk_b64: str) -> bytes | None:
    """Expand a Meshtastic PSK from base64 to an AES key.

    Meshtastic PSK formats:
    - Empty / zero byte  -> no encryption, return None
    - Single byte (1-255)-> replace the last byte of the default key
    - 16 or 32 bytes     -> use as-is (AES-128 or AES-256)
    """
    try:
        raw = base64.b64decode(psk_b64)
    except Exception:
        return None

    if not raw or raw == b"\x00":
        return None

    if len(raw) == 1:
        # Single-byte PSK: replace last byte of default key
        return MESHTASTIC_DEFAULT_KEY[:-1] + raw

    if len(raw) in (16, 32):
        return raw

    # Unknown length — try using it anyway
    return raw


def _decrypt_packet(
    encrypted_bytes: bytes,
    packet_id: int,
    from_node_num: int,
    keys: list[bytes],
) -> Any | None:
    """Try to decrypt a Meshtastic encrypted packet with a list of AES keys.

    Uses AES-128-CTR (or AES-256-CTR) with a nonce constructed from the
    packet_id and from_node_num as per the Meshtastic protocol.

    Returns the decoded mesh_pb2.Data message on success, or None.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        logger.debug("cryptography library not available for decryption")
        return None

    # Meshtastic nonce: 8 bytes packet_id (little-endian) + 4 bytes from_node (LE) + 4 zero bytes
    nonce = struct.pack("<QI", packet_id, from_node_num) + b"\x00" * 4

    try:
        from meshtastic import mesh_pb2
    except ImportError:
        return None

    for key in keys:
        try:
            cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

            # Try parsing as a Data protobuf
            data_msg = mesh_pb2.Data()
            data_msg.ParseFromString(decrypted)

            # Validate: portnum should be in a reasonable range
            if data_msg.portnum < 0 or data_msg.portnum > 511:
                continue

            # portnum 0 (UNKNOWN_APP) with empty payload is likely a bad decrypt
            if data_msg.portnum == 0 and not data_msg.payload:
                continue

            return data_msg
        except Exception:
            continue

    return None


def decode_meshtastic_packet(
    payload: bytes,
    encryption_keys: list[bytes] | None = None,
) -> dict | None:
    """
    Decode a Meshtastic protobuf packet, including inner payloads.

    Decodes the outer ServiceEnvelope/MeshPacket and then decodes the inner
    payload based on portnum (Position, User, Telemetry, RouteDiscovery, etc.)
    into dicts so downstream handlers receive structured data instead of raw bytes.

    If the packet is encrypted and encryption_keys are provided, attempts
    decryption with each key until one succeeds.
    """
    try:
        try:
            from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2, telemetry_pb2

            service_envelope = mqtt_pb2.ServiceEnvelope()
            service_envelope.ParseFromString(payload)

            packet = service_envelope.packet
            decoded = {
                "from": getattr(packet, "from"),
                "to": packet.to,
                "id": packet.id,
                "channel": packet.channel,
                "hopLimit": packet.hop_limit,
                "hopStart": packet.hop_start,
                "rxTime": packet.rx_time or None,
                "rxSnr": packet.rx_snr,
                "rxRssi": packet.rx_rssi,
            }

            data_msg = None

            if packet.HasField("decoded"):
                data_msg = packet.decoded
            elif packet.encrypted and encryption_keys:
                data_msg = _decrypt_packet(
                    packet.encrypted,
                    packet.id,
                    getattr(packet, "from"),
                    encryption_keys,
                )

            if data_msg is not None:
                portnum = data_msg.portnum
                decoded["portnum"] = portnums_pb2.PortNum.Name(portnum)
                raw_payload = data_msg.payload
                if data_msg.reply_id:
                    decoded["replyId"] = data_msg.reply_id
                if data_msg.emoji:
                    decoded["emoji"] = data_msg.emoji

                # Decode inner payload based on portnum
                decoded["payload"] = _decode_inner_payload(
                    portnum, raw_payload, mesh_pb2, portnums_pb2, telemetry_pb2
                )

                # For TEXT_MESSAGE_APP, also set top-level "text" key
                if portnum == portnums_pb2.PortNum.TEXT_MESSAGE_APP:
                    decoded["text"] = raw_payload.decode("utf-8", errors="replace")

            return decoded

        except ImportError:
            logger.debug("Meshtastic protobuf library not available")
            return None

    except Exception as e:
        logger.debug(f"Failed to decode protobuf: {e}")
        return None


def _decode_inner_payload(
    portnum: int,
    raw_payload: bytes,
    mesh_pb2: Any,
    portnums_pb2: Any,
    telemetry_pb2: Any,
) -> dict | bytes:
    """Decode the inner payload bytes into a dict based on portnum.

    Returns the decoded dict on success, or the original raw bytes if decoding
    fails or the portnum is unrecognized.
    """
    try:
        if portnum == portnums_pb2.PortNum.POSITION_APP:
            msg = mesh_pb2.Position()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == portnums_pb2.PortNum.NODEINFO_APP:
            msg = mesh_pb2.User()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == portnums_pb2.PortNum.TELEMETRY_APP:
            msg = telemetry_pb2.Telemetry()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == portnums_pb2.PortNum.TRACEROUTE_APP:
            msg = mesh_pb2.RouteDiscovery()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

    except Exception as e:
        logger.debug(f"Failed to decode inner payload for portnum {portnum}: {e}")

    return raw_payload
