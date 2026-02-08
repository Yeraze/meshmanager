"""Protobuf decoding for Meshtastic packets."""

import logging
from typing import Any

from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)


def decode_meshtastic_packet(payload: bytes) -> dict | None:
    """
    Decode a Meshtastic protobuf packet, including inner payloads.

    Decodes the outer ServiceEnvelope/MeshPacket and then decodes the inner
    payload based on portnum (Position, User, Telemetry, RouteDiscovery, etc.)
    into dicts so downstream handlers receive structured data instead of raw bytes.
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

            if packet.HasField("decoded"):
                portnum = packet.decoded.portnum
                decoded["portnum"] = portnums_pb2.PortNum.Name(portnum)
                raw_payload = packet.decoded.payload
                if packet.decoded.reply_id:
                    decoded["replyId"] = packet.decoded.reply_id
                if packet.decoded.emoji:
                    decoded["emoji"] = packet.decoded.emoji

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
