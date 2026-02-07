"""Protobuf decoding for Meshtastic packets."""

import logging

logger = logging.getLogger(__name__)


def decode_meshtastic_packet(payload: bytes) -> dict | None:
    """
    Decode a Meshtastic protobuf packet.

    This is a simplified decoder. For full functionality, you would need
    to compile the Meshtastic protobuf definitions.
    """
    try:
        # Try to import compiled protobufs if available
        try:
            from meshtastic import mesh_pb2, portnums_pb2

            service_envelope = mesh_pb2.ServiceEnvelope()
            service_envelope.ParseFromString(payload)

            packet = service_envelope.packet
            decoded = {
                "from": packet.from_,
                "to": packet.to,
                "id": packet.id,
                "hopLimit": packet.hop_limit,
                "hopStart": packet.hop_start,
            }

            if packet.HasField("decoded"):
                portnum = packet.decoded.portnum
                decoded["portnum"] = portnums_pb2.PortNum.Name(portnum)
                decoded["payload"] = packet.decoded.payload
                if packet.decoded.reply_id:
                    decoded["replyId"] = packet.decoded.reply_id
                if packet.decoded.emoji:
                    decoded["emoji"] = packet.decoded.emoji

            return decoded

        except ImportError:
            # Fall back to basic parsing without compiled protos
            logger.debug("Meshtastic protobuf library not available")
            return None

    except Exception as e:
        logger.debug(f"Failed to decode protobuf: {e}")
        return None
