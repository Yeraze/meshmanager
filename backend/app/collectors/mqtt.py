"""MQTT collector for Meshtastic data."""

import asyncio
import json
import logging
from datetime import UTC, datetime

import aiomqtt
from sqlalchemy.exc import IntegrityError

from app.collectors.base import BaseCollector
from app.database import async_session_maker
from app.models import Channel, Message, Node, Source, Telemetry, Traceroute
from app.schemas.source import SourceTestResult
from app.services.protobuf import decode_meshtastic_packet

logger = logging.getLogger(__name__)


class MqttCollector(BaseCollector):
    """Collector for MQTT sources."""

    def __init__(self, source: Source):
        super().__init__(source)
        self._running = False
        self._task: asyncio.Task | None = None
        self._client: aiomqtt.Client | None = None

    async def test_connection(self) -> SourceTestResult:
        """Test connection to the MQTT broker."""
        if not self.source.mqtt_host:
            return SourceTestResult(success=False, message="No MQTT host configured")

        hostname = self.source.mqtt_host.strip()
        try:
            async with aiomqtt.Client(
                hostname=hostname,
                port=self.source.mqtt_port or 1883,
                username=self.source.mqtt_username,
                password=self.source.mqtt_password,
                tls_context=None,  # TODO: Add TLS support
            ) as client:
                # Subscribe briefly to test
                if self.source.mqtt_topic_pattern:
                    await client.subscribe(self.source.mqtt_topic_pattern)

                return SourceTestResult(
                    success=True,
                    message="Connection successful",
                )
        except aiomqtt.MqttError as e:
            return SourceTestResult(
                success=False, message=f"MQTT error connecting to {hostname}: {e}"
            )
        except Exception as e:
            return SourceTestResult(success=False, message=f"Connection error for {hostname}: {e}")

    async def collect(self) -> None:
        """MQTT uses continuous streaming, not polling."""
        pass

    async def start(self) -> None:
        """Start MQTT subscription."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._subscribe_loop())
        logger.info(f"Started MQTT collector: {self.source.name}")

    async def _subscribe_loop(self) -> None:
        """Main MQTT subscription loop with reconnection."""
        while self._running:
            try:
                hostname = (self.source.mqtt_host or "localhost").strip()
                async with aiomqtt.Client(
                    hostname=hostname,
                    port=self.source.mqtt_port or 1883,
                    username=self.source.mqtt_username,
                    password=self.source.mqtt_password,
                ) as client:
                    self._client = client

                    # Subscribe to configured topic
                    if self.source.mqtt_topic_pattern:
                        await client.subscribe(self.source.mqtt_topic_pattern)
                        logger.info(
                            f"Subscribed to {self.source.mqtt_topic_pattern} "
                            f"on {self.source.mqtt_host}"
                        )

                    # Update source status
                    await self._update_source_status(None)

                    # Process messages
                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._process_message(message)

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT error for {self.source.name} ({hostname}): {e}")
                await self._update_source_status(str(e))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Unexpected error in MQTT loop for {self.source.name} ({hostname}): {e}"
                )
                await self._update_source_status(str(e))

            if self._running:
                # Reconnect after delay
                logger.info(f"Reconnecting to {self.source.name} in 10 seconds...")
                await asyncio.sleep(10)

    async def _update_source_status(self, error: str | None) -> None:
        """Update source status in database."""
        try:
            async with async_session_maker() as db:
                from sqlalchemy import select

                result = await db.execute(select(Source).where(Source.id == self.source.id))
                source = result.scalar()
                if source:
                    source.last_poll_at = datetime.now(UTC)
                    source.last_error = error
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to update source status: {e}")

    async def _process_message(self, message: aiomqtt.Message) -> None:
        """Process an incoming MQTT message."""
        try:
            topic = str(message.topic)
            payload = message.payload

            # Try to decode as JSON first
            try:
                if isinstance(payload, bytes):
                    data = json.loads(payload.decode("utf-8"))
                else:
                    data = json.loads(payload)
                await self._process_json_message(topic, data)
                return
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

            # Try to decode as protobuf
            if isinstance(payload, bytes):
                await self._process_protobuf_message(topic, payload)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    async def _process_json_message(self, topic: str, data: dict) -> None:
        """Process a JSON-encoded Meshtastic message."""
        msg_type = data.get("type", "").lower()

        try:
            async with async_session_maker() as db:
                await self._ensure_channel(db, data)
                if msg_type == "text" or "text" in data:
                    await self._handle_text_message(db, data)
                elif msg_type == "position" or "position" in data:
                    await self._handle_position(db, data)
                elif msg_type == "telemetry" or "telemetry" in data:
                    await self._handle_telemetry(db, data)
                elif msg_type == "nodeinfo" or "nodeinfo" in data:
                    await self._handle_nodeinfo(db, data)
                elif msg_type == "traceroute":
                    await self._handle_traceroute(db, data)
                await db.commit()
        except IntegrityError as e:
            err = str(e)
            if "ix_messages_source_packet" in err:
                logger.debug("Duplicate message ignored (likely overlapping topics)")
            elif "idx_traceroutes_unique" in err:
                logger.debug("Duplicate traceroute ignored")
            else:
                logger.error(f"Unexpected integrity error: {e}")
                raise

    async def _ensure_channel(self, db, data: dict) -> None:
        """Ensure a channel record exists for MQTT messages."""
        channel_index = data.get("channel")
        if channel_index is None:
            return
        try:
            channel_index = int(channel_index)
        except (TypeError, ValueError):
            return

        from sqlalchemy import select

        result = await db.execute(
            select(Channel).where(
                Channel.source_id == self.source.id,
                Channel.channel_index == channel_index,
            )
        )
        channel = result.scalar()
        if channel:
            return

        channel = Channel(
            source_id=self.source.id,
            channel_index=channel_index,
            name=data.get("channel_name") or data.get("channelName"),
        )
        db.add(channel)

    async def _process_protobuf_message(self, topic: str, payload: bytes) -> None:
        """Process a protobuf-encoded Meshtastic message."""
        try:
            decoded = decode_meshtastic_packet(payload)
            if decoded:
                async with async_session_maker() as db:
                    await self._handle_decoded_packet(db, decoded)
                    await db.commit()
        except Exception as e:
            logger.debug(f"Failed to decode protobuf: {e}")

    async def _handle_text_message(self, db, data: dict) -> None:
        """Handle a text message."""
        from_node = data.get("from") or data.get("fromId")
        if not from_node:
            return

        # Convert hex ID to number if needed
        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)

        to_node = data.get("to") or data.get("toId")
        if isinstance(to_node, str) and to_node.startswith("!"):
            to_node = int(to_node[1:], 16)

        rx_time = self._parse_rx_time(data.get("rxTime"))

        raw_id = data.get("id")
        meshtastic_id = int(raw_id) if raw_id is not None else None

        # Extract reply_id (JSON: replyId or reply_id; protobuf: replyId)
        reply_id = self._first_key(data, "replyId", "reply_id")
        if reply_id is not None:
            reply_id = int(reply_id)

        # Extract emoji — protobuf sends a Unicode codepoint (int), JSON may
        # send a codepoint or an actual emoji string.
        raw_emoji = data.get("emoji")
        emoji = None
        if raw_emoji is not None:
            if isinstance(raw_emoji, int):
                emoji = chr(raw_emoji) if 0 < raw_emoji <= 0x10FFFF else None
            elif isinstance(raw_emoji, str) and raw_emoji:
                emoji = raw_emoji

        message = Message(
            source_id=self.source.id,
            packet_id=str(raw_id) if raw_id is not None else None,
            meshtastic_id=meshtastic_id,
            from_node_num=from_node,
            to_node_num=to_node,
            channel=data.get("channel", 0),
            text=data.get("text") or self._extract_text(data.get("payload")),
            reply_id=reply_id,
            emoji=emoji,
            hop_limit=data.get("hopLimit"),
            hop_start=data.get("hopStart"),
            rx_time=rx_time,
            rx_snr=data.get("rxSnr"),
            rx_rssi=data.get("rxRssi"),
        )
        db.add(message)
        logger.debug(f"Received text message from {from_node}")

    @staticmethod
    def _extract_text(payload) -> str | None:
        """Extract text from a payload that may be a string, bytes, or dict."""
        if payload is None:
            return None
        if isinstance(payload, bytes):
            text = payload.decode("utf-8", errors="replace")
            return text if text else None
        if isinstance(payload, str):
            return payload if payload else None
        if isinstance(payload, dict):
            return payload.get("text")
        return str(payload)

    @staticmethod
    def _first_key(data: dict, *keys: str):
        """Return the value for the first key present in data, or None.

        Unlike chaining with `or`, this correctly handles falsy values like 0.
        """
        for key in keys:
            if key in data:
                return data[key]
        return None

    @staticmethod
    def _parse_rx_time(value) -> datetime | None:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                ts = float(value)
                if ts > 2_000_000_000_000:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts, UTC)
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OSError):
            return None
        return None

    async def _handle_position(self, db, data: dict) -> None:
        """Handle a position update."""
        from_node = data.get("from") or data.get("fromId")
        if not from_node:
            return

        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)

        # MQTT JSON nests position data in "payload"; MeshMonitor uses "position"
        position = data.get("payload", data.get("position", data))

        lat = self._extract_coordinate(position, "latitude", "lat", "latitude_i")
        lon = self._extract_coordinate(position, "longitude", "lon", "longitude_i")
        alt = position.get("altitude") or position.get("alt")

        if lat is None and lon is None:
            return

        # Update or create node
        from sqlalchemy import select

        result = await db.execute(
            select(Node).where(
                Node.source_id == self.source.id,
                Node.node_num == from_node,
            )
        )
        node = result.scalar()

        if node:
            node.latitude = lat
            node.longitude = lon
            node.altitude = alt
            node.position_time = datetime.now(UTC)
            node.last_heard = datetime.now(UTC)
        else:
            node = Node(
                source_id=self.source.id,
                node_num=from_node,
                latitude=lat,
                longitude=lon,
                altitude=alt,
                position_time=datetime.now(UTC),
                last_heard=datetime.now(UTC),
            )
            db.add(node)

        logger.debug(f"Received position from {from_node}")

    @staticmethod
    def _extract_coordinate(
        data: dict, float_key: str, short_key: str, int_key: str
    ) -> float | None:
        """Extract a coordinate, handling both float and integer (1e-7) formats."""
        val = data.get(float_key)
        if val is None:
            val = data.get(short_key)
        if val is not None:
            return float(val)
        int_val = data.get(int_key)
        if int_val is not None:
            return int(int_val) / 1e7
        return None

    async def _handle_telemetry(self, db, data: dict) -> None:
        """Handle telemetry data."""
        from app.models.telemetry import TelemetryType

        from_node = data.get("from") or data.get("fromId")
        if not from_node:
            return

        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)

        # MQTT JSON nests metrics in "payload"; MeshMonitor uses "telemetry"
        telem = data.get("telemetry", data)
        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}

        # Try camelCase nested (MeshMonitor/protobuf), then check payload for flat keys
        device_metrics = (
            telem.get("deviceMetrics")
            or payload.get("deviceMetrics")
            or payload.get("device_metrics")
            or {}
        )
        env_metrics = (
            telem.get("environmentMetrics")
            or payload.get("environmentMetrics")
            or payload.get("environment_metrics")
            or {}
        )

        # MQTT JSON may put device metrics flat in payload
        if not device_metrics and any(
            k in payload for k in ("battery_level", "voltage", "channel_utilization", "air_util_tx")
        ):
            device_metrics = payload
        if not env_metrics and any(
            k in payload for k in ("temperature", "relative_humidity", "barometric_pressure")
        ):
            env_metrics = payload

        telemetry = Telemetry(
            source_id=self.source.id,
            node_num=from_node,
            telemetry_type=TelemetryType.DEVICE if device_metrics else TelemetryType.ENVIRONMENT,
            battery_level=self._first_key(device_metrics, "batteryLevel", "battery_level"),
            voltage=device_metrics.get("voltage"),
            channel_utilization=self._first_key(
                device_metrics, "channelUtilization", "channel_utilization"
            ),
            air_util_tx=self._first_key(device_metrics, "airUtilTx", "air_util_tx"),
            uptime_seconds=self._first_key(device_metrics, "uptimeSeconds", "uptime_seconds"),
            temperature=env_metrics.get("temperature"),
            relative_humidity=self._first_key(env_metrics, "relativeHumidity", "relative_humidity"),
            barometric_pressure=self._first_key(
                env_metrics, "barometricPressure", "barometric_pressure"
            ),
        )
        db.add(telemetry)
        logger.debug(f"Received telemetry from {from_node}")

    async def _handle_nodeinfo(self, db, data: dict) -> None:
        """Handle node info update."""
        from_node = data.get("from") or data.get("fromId")
        if not from_node:
            return

        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)

        # MQTT JSON: flat fields in "payload"; MeshMonitor: nested in "nodeinfo.user"
        nodeinfo = data.get("nodeinfo", data)
        user = nodeinfo.get("user", {})
        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}

        # Try camelCase (MeshMonitor/protobuf) then lowercase (MQTT JSON)
        node_id = self._first_key(user, "id") or payload.get("id")
        short_name = self._first_key(user, "shortName") or payload.get("shortname")
        long_name = self._first_key(user, "longName") or payload.get("longname")
        hw_model = self._first_key(user, "hwModel") or payload.get("hardware")
        role = self._first_key(user, "role") or payload.get("role")
        is_licensed = self._first_key(user, "isLicensed") or payload.get("is_licensed") or False

        # Convert integer hw_model/role to string if needed
        if isinstance(hw_model, int):
            hw_model = str(hw_model)
        if isinstance(role, int):
            role = str(role)

        from sqlalchemy import select

        result = await db.execute(
            select(Node).where(
                Node.source_id == self.source.id,
                Node.node_num == from_node,
            )
        )
        node = result.scalar()

        if node:
            node.node_id = node_id
            node.short_name = short_name
            node.long_name = long_name
            node.hw_model = hw_model
            node.role = role
            node.is_licensed = is_licensed
            node.last_heard = datetime.now(UTC)
        else:
            node = Node(
                source_id=self.source.id,
                node_num=from_node,
                node_id=node_id,
                short_name=short_name,
                long_name=long_name,
                hw_model=hw_model,
                role=role,
                is_licensed=is_licensed,
                last_heard=datetime.now(UTC),
            )
            db.add(node)

        logger.debug(f"Received nodeinfo from {from_node}")

    async def _handle_traceroute(self, db, data: dict) -> None:
        """Handle a traceroute response."""
        from_node = data.get("from") or data.get("fromId")
        to_node = data.get("to") or data.get("toId")
        if not from_node or not to_node:
            return

        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)
        if isinstance(to_node, str) and to_node.startswith("!"):
            to_node = int(to_node[1:], 16)

        payload = data.get("payload", {})

        # Protobuf: payload is raw bytes, decode via RouteDiscovery
        if isinstance(payload, bytes):
            try:
                from meshtastic import mesh_pb2

                route_discovery = mesh_pb2.RouteDiscovery()
                route_discovery.ParseFromString(payload)
                route = list(route_discovery.route) or []
                snr_towards = list(route_discovery.snr_towards) or None
                route_back = list(route_discovery.route_back) or None
                snr_back = list(route_discovery.snr_back) or None
            except Exception as e:
                logger.debug(f"Failed to decode traceroute protobuf: {e}")
                return
        elif isinstance(payload, dict):
            # JSON: fields already decoded
            route = payload.get("route", [])
            snr_towards = payload.get("snrTowards") or payload.get("snr_towards")
            route_back = payload.get("routeBack") or payload.get("route_back")
            snr_back = payload.get("snrBack") or payload.get("snr_back")
        else:
            # Top-level JSON fields (some MQTT bridges flatten them)
            route = data.get("route", [])
            snr_towards = data.get("snrTowards") or data.get("snr_towards")
            route_back = data.get("routeBack") or data.get("route_back")
            snr_back = data.get("snrBack") or data.get("snr_back")

        # Some MQTT JSON decoders resolve node numbers to names (strings).
        # Resolve string names back to node numbers via DB lookup.
        route = await self._resolve_route_names(db, route or [])
        route_back = await self._resolve_route_names(db, route_back or []) or None

        # SNR values: protobuf sends raw ints (already dB*4), but JSON decoders
        # may send floats (actual dB).  Convert floats to int (dB * 4) to match
        # MeshMonitor convention and the BIGINT column type.
        snr_towards = self._coerce_snr_array(snr_towards)
        snr_back = self._coerce_snr_array(snr_back)

        # In TRACEROUTE_APP replies, 'from' is the responder and 'to' is the
        # requester.  Swap so from_node_num = requester, to_node_num = responder
        # (matches MeshMonitor convention).
        from_node, to_node = to_node, from_node

        rx_time = self._parse_rx_time(data.get("rxTime") or data.get("timestamp"))

        traceroute = Traceroute(
            source_id=self.source.id,
            from_node_num=from_node,
            to_node_num=to_node,
            route=route or [],
            route_back=route_back,
            snr_towards=snr_towards,
            snr_back=snr_back,
            received_at=rx_time or datetime.now(UTC),
        )
        db.add(traceroute)
        logger.debug(f"Received MQTT traceroute from {from_node} to {to_node}")

    async def _resolve_route_names(self, db, route: list) -> list[int]:
        """Resolve a route array that may contain string node names to node numbers.

        MQTT JSON decoders often replace integer node numbers with display names.
        This looks up each string entry in the nodes table (by long_name) and
        replaces it with the corresponding node_num.  Unresolvable names are dropped.
        """
        if not route:
            return []

        # Separate ints from strings
        names = [n for n in route if isinstance(n, str)]
        if not names:
            # All entries are already ints
            return [n for n in route if isinstance(n, int)]

        # Batch-lookup all string names in one query
        from sqlalchemy import select

        result = await db.execute(
            select(Node.long_name, Node.node_num)
            .where(Node.long_name.in_(names))
        )
        name_to_num = {row.long_name: row.node_num for row in result}

        resolved = []
        for entry in route:
            if isinstance(entry, int):
                resolved.append(entry)
            elif isinstance(entry, str) and entry in name_to_num:
                resolved.append(name_to_num[entry])
            else:
                logger.debug(f"Could not resolve route node name: {entry!r}")
        return resolved

    @staticmethod
    def _coerce_snr_array(values: list | None) -> list[int] | None:
        """Convert an SNR array to BIGINT-compatible ints.

        Protobuf already provides dB*4 integers.  JSON decoders may provide
        raw dB floats — multiply by 4 and round to match the convention.
        """
        if not values:
            return None
        result = []
        for v in values:
            if isinstance(v, float):
                result.append(int(round(v * 4)))
            elif isinstance(v, int):
                result.append(v)
        return result or None

    async def _handle_decoded_packet(self, db, decoded: dict) -> None:
        """Handle a decoded protobuf packet."""
        portnum = decoded.get("portnum", "")

        if portnum == "TEXT_MESSAGE_APP":
            await self._handle_text_message(db, decoded)
        elif portnum == "POSITION_APP":
            await self._handle_position(db, decoded)
        elif portnum == "TELEMETRY_APP":
            await self._handle_telemetry(db, decoded)
        elif portnum == "NODEINFO_APP":
            await self._handle_nodeinfo(db, decoded)
        elif portnum == "TRACEROUTE_APP":
            await self._handle_traceroute(db, decoded)

    async def stop(self) -> None:
        """Stop MQTT subscription."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped MQTT collector: {self.source.name}")
