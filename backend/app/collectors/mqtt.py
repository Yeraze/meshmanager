"""MQTT collector for Meshtastic data."""

import asyncio
import json
import logging
from datetime import UTC, datetime

import aiomqtt
from sqlalchemy.exc import IntegrityError

from app.collectors.base import BaseCollector
from app.database import async_session_maker
from app.models import Channel, Message, Node, Source, Telemetry
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
            return SourceTestResult(
                success=False, message=f"Connection error for {hostname}: {e}"
            )

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

                result = await db.execute(
                    select(Source).where(Source.id == self.source.id)
                )
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

                await db.commit()
        except IntegrityError:
            # Duplicate message from overlapping MQTT topics — safe to ignore
            pass

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

        message = Message(
            source_id=self.source.id,
            packet_id=str(data["id"]) if data.get("id") is not None else None,
            from_node_num=from_node,
            to_node_num=to_node,
            channel=data.get("channel", 0),
            text=data.get("text") or self._extract_text(data.get("payload")),
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
        """Extract text from a payload that may be a string or dict."""
        if payload is None:
            return None
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return payload.get("text")
        return str(payload)

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

        position = data.get("position", data)

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
            node.latitude = position.get("latitude") or position.get("lat")
            node.longitude = position.get("longitude") or position.get("lon")
            node.altitude = position.get("altitude") or position.get("alt")
            node.position_time = datetime.now(UTC)
            node.last_heard = datetime.now(UTC)
        else:
            node = Node(
                source_id=self.source.id,
                node_num=from_node,
                latitude=position.get("latitude") or position.get("lat"),
                longitude=position.get("longitude") or position.get("lon"),
                altitude=position.get("altitude") or position.get("alt"),
                position_time=datetime.now(UTC),
                last_heard=datetime.now(UTC),
            )
            db.add(node)

        logger.debug(f"Received position from {from_node}")

    async def _handle_telemetry(self, db, data: dict) -> None:
        """Handle telemetry data."""
        from app.models.telemetry import TelemetryType

        from_node = data.get("from") or data.get("fromId")
        if not from_node:
            return

        if isinstance(from_node, str) and from_node.startswith("!"):
            from_node = int(from_node[1:], 16)

        telem = data.get("telemetry", data)
        device_metrics = telem.get("deviceMetrics", {})
        env_metrics = telem.get("environmentMetrics", {})

        telemetry = Telemetry(
            source_id=self.source.id,
            node_num=from_node,
            telemetry_type=TelemetryType.DEVICE if device_metrics else TelemetryType.ENVIRONMENT,
            battery_level=device_metrics.get("batteryLevel"),
            voltage=device_metrics.get("voltage"),
            channel_utilization=device_metrics.get("channelUtilization"),
            air_util_tx=device_metrics.get("airUtilTx"),
            uptime_seconds=device_metrics.get("uptimeSeconds"),
            temperature=env_metrics.get("temperature"),
            relative_humidity=env_metrics.get("relativeHumidity"),
            barometric_pressure=env_metrics.get("barometricPressure"),
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

        nodeinfo = data.get("nodeinfo", data)
        user = nodeinfo.get("user", {})

        from sqlalchemy import select

        result = await db.execute(
            select(Node).where(
                Node.source_id == self.source.id,
                Node.node_num == from_node,
            )
        )
        node = result.scalar()

        if node:
            node.node_id = user.get("id")
            node.short_name = user.get("shortName")
            node.long_name = user.get("longName")
            node.hw_model = user.get("hwModel")
            node.role = user.get("role")
            node.is_licensed = user.get("isLicensed", False)
            node.last_heard = datetime.now(UTC)
        else:
            node = Node(
                source_id=self.source.id,
                node_num=from_node,
                node_id=user.get("id"),
                short_name=user.get("shortName"),
                long_name=user.get("longName"),
                hw_model=user.get("hwModel"),
                role=user.get("role"),
                is_licensed=user.get("isLicensed", False),
                last_heard=datetime.now(UTC),
            )
            db.add(node)

        logger.debug(f"Received nodeinfo from {from_node}")

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
