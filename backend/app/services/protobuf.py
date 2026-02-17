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

            # Extract gateway_id from the envelope (e.g., "!abcd1234")
            gw_id = service_envelope.gateway_id
            gateway_node_num = None
            if gw_id and gw_id.startswith("!"):
                try:
                    gateway_node_num = int(gw_id[1:], 16)
                except ValueError:
                    pass

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
                "relayNode": packet.relay_node or None,
                "gatewayNodeNum": gateway_node_num,
                "channelId": service_envelope.channel_id or None,
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
                    # Protobuf emoji field is a fixed32 Unicode codepoint.
                    # Values < 0x20 are control chars (e.g. 0x01 = "reaction present" flag)
                    if data_msg.emoji >= 0x20:
                        try:
                            decoded["emoji"] = chr(data_msg.emoji)
                        except (ValueError, OverflowError):
                            pass

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
) -> dict | str | bytes:
    """Decode the inner payload bytes into a dict based on portnum.

    Returns the decoded dict (or UTF-8 string for text-based portnums)
    on success, or the original raw bytes if decoding fails or the portnum
    is unrecognized.
    """
    pn = portnums_pb2.PortNum

    # Protobuf message-based portnums: (module, class_name)
    proto_portnums: dict[int, tuple[Any, str]] = {
        pn.POSITION_APP: (mesh_pb2, "Position"),
        pn.NODEINFO_APP: (mesh_pb2, "User"),
        pn.TELEMETRY_APP: (telemetry_pb2, "Telemetry"),
        pn.TRACEROUTE_APP: (mesh_pb2, "RouteDiscovery"),
        pn.WAYPOINT_APP: (mesh_pb2, "Waypoint"),
        pn.ROUTING_APP: (mesh_pb2, "Routing"),
        pn.NEIGHBORINFO_APP: (mesh_pb2, "NeighborInfo"),
        pn.STORE_FORWARD_PLUSPLUS_APP: (mesh_pb2, "StoreForwardPlusPlus"),
        pn.KEY_VERIFICATION_APP: (mesh_pb2, "KeyVerification"),
    }

    # Text-based portnums (decode as UTF-8)
    text_portnums: set[int] = {
        pn.DETECTION_SENSOR_APP,
        pn.ALERT_APP,
        pn.RANGE_TEST_APP,
        pn.REPLY_APP,
        pn.NODE_STATUS_APP,
    }

    try:
        # Check protobuf message-based portnums
        if portnum in proto_portnums:
            module, class_name = proto_portnums[portnum]
            msg = getattr(module, class_name)()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        # Lazy-imported protobuf modules for less common portnums
        if portnum == pn.PAXCOUNTER_APP:
            from meshtastic import paxcount_pb2

            msg = paxcount_pb2.Paxcount()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == pn.MAP_REPORT_APP:
            from meshtastic import mqtt_pb2 as mqtt_pb2_mod

            msg = mqtt_pb2_mod.MapReport()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == pn.STORE_FORWARD_APP:
            from meshtastic import storeforward_pb2

            msg = storeforward_pb2.StoreAndForward()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == pn.REMOTE_HARDWARE_APP:
            from meshtastic import remote_hardware_pb2

            msg = remote_hardware_pb2.HardwareMessage()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == pn.ADMIN_APP:
            from meshtastic import admin_pb2

            msg = admin_pb2.AdminMessage()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        if portnum == getattr(pn, "ATAK_PLUGIN", None):
            from meshtastic.protobuf import atak_pb2

            msg = atak_pb2.TAKPacket()
            msg.ParseFromString(raw_payload)
            return MessageToDict(msg)

        # Text-based portnums
        if portnum in text_portnums:
            return raw_payload.decode("utf-8", errors="replace")

        # TEXT_MESSAGE_COMPRESSED_APP: leave as raw bytes (compressed)

    except Exception as e:
        logger.debug(f"Failed to decode inner payload for portnum {portnum}: {e}")

    return raw_payload
