"""MeshMonitor API collector."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx
from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import aliased

from app.collectors.base import BaseCollector
from app.database import async_session_maker
from app.models import Channel, Message, Node, SolarProduction, Source, Telemetry, Traceroute
from app.models.packet_record import PacketRecord, PacketRecordType
from app.schemas.source import SourceTestResult
from app.telemetry_registry import CAMEL_TO_METRIC, METRIC_REGISTRY, SUBMESSAGE_TYPE_MAP

logger = logging.getLogger(__name__)


class CollectionStatus:
    """Status of historical data collection."""

    def __init__(self):
        self.status: str = "idle"  # idle, collecting, complete, error
        self.current_batch: int = 0
        self.max_batches: int = 0
        self.total_collected: int = 0
        self.last_error: str | None = None
        self.start_time: datetime | None = None  # When collection started
        self.last_completion_time: datetime | None = None  # When last node completed
        self.last_completed_count: int = 0  # Last completed count when we calculated rate
        self.smoothed_rate: float | None = None  # Exponential moving average of rate

    def to_dict(self) -> dict:
        """Convert status to dictionary, including calculated timing information."""
        elapsed_seconds = 0
        estimated_seconds_remaining = 0

        if self.status == "collecting" and self.start_time:
            # Calculate elapsed time (using local time)
            elapsed = datetime.now() - self.start_time
            elapsed_seconds = int(elapsed.total_seconds())

            # Calculate ETA based on actual progress
            if self.current_batch > 0 and self.max_batches > 0:
                # Get total number of nodes we need to import
                total_nodes = self.max_batches

                # Calculate remaining nodes to collect data from
                remaining_nodes = total_nodes - self.current_batch

                # Minimum nodes needed for accurate rate calculation
                min_nodes_for_accurate_rate = 20
                # Baseline rate based on observed performance: ~3-3.5 nodes/second with 10 parallel
                baseline_nodes_per_second = 3.2
                # Exponential smoothing factor (0.0-1.0, higher = more weight to recent values)
                smoothing_alpha = 0.3

                # Check if we have a new completion (current_batch increased)
                has_new_completion = self.current_batch > self.last_completed_count

                if elapsed_seconds > 0 and self.current_batch >= min_nodes_for_accurate_rate:
                    # Calculate instantaneous rate
                    instantaneous_rate = self.current_batch / elapsed_seconds

                    # Use exponential smoothing to reduce volatility
                    # Only update smoothed rate when we have new completions or on first calculation
                    if has_new_completion or self.smoothed_rate is None:
                        if self.smoothed_rate is None:
                            # Initialize with first calculated rate
                            self.smoothed_rate = instantaneous_rate
                        else:
                            # Exponential moving average: new = alpha * current + (1-alpha) * old
                            self.smoothed_rate = (
                                smoothing_alpha * instantaneous_rate
                                + (1 - smoothing_alpha) * self.smoothed_rate
                            )
                        self.last_completed_count = self.current_batch
                        self.last_completion_time = datetime.now()

                    # Use smoothed rate for ETA calculation
                    effective_nodes_per_second = self.smoothed_rate
                    estimated_seconds_remaining = int(remaining_nodes / effective_nodes_per_second)
                    calculation_method = "smoothed"
                elif elapsed_seconds > 0 and self.current_batch < min_nodes_for_accurate_rate:
                    # For early batches, use a hybrid approach:
                    # Blend baseline with actual rate (weighted by progress)
                    progress_ratio = self.current_batch / min_nodes_for_accurate_rate
                    actual_rate = self.current_batch / elapsed_seconds if elapsed_seconds > 0 else 0
                    # Gradually transition from baseline to actual as we approach MIN_NODES
                    effective_nodes_per_second = (
                        baseline_nodes_per_second * (1 - progress_ratio)
                        + actual_rate * progress_ratio
                    )
                    estimated_seconds_remaining = int(remaining_nodes / effective_nodes_per_second)
                    calculation_method = "hybrid"
                else:
                    # Use baseline estimate for very early stages
                    effective_nodes_per_second = baseline_nodes_per_second
                    estimated_seconds_remaining = int(remaining_nodes / baseline_nodes_per_second)
                    calculation_method = "baseline"

                # Log calculation details (INFO level for monitoring)
                # Only log every 10 nodes to avoid log spam, but always log first few
                if self.current_batch % 10 == 0 or self.current_batch <= 5:
                    logger.info(
                        f"ETA ({calculation_method}): elapsed={elapsed_seconds}s, completed={self.current_batch}/{total_nodes}, "
                        f"rate={effective_nodes_per_second:.2f} nodes/s, "
                        f"remaining={remaining_nodes}, ETA={estimated_seconds_remaining}s ({estimated_seconds_remaining / 60:.1f}m)"
                    )

        return {
            "status": self.status,
            "current_batch": self.current_batch,
            "max_batches": self.max_batches,
            "total_collected": self.total_collected,
            "last_error": self.last_error,
            "elapsed_seconds": elapsed_seconds,
            "estimated_seconds_remaining": estimated_seconds_remaining,
        }


class MeshMonitorCollector(BaseCollector):
    """Collector for MeshMonitor API sources."""

    def __init__(self, source: Source):
        super().__init__(source)
        self._running = False
        self._task: asyncio.Task | None = None
        self._historical_task: asyncio.Task | None = None
        self.collection_status = CollectionStatus()
        self._local_node_num: int | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Accept": "application/json"}
        if self.source.api_token:
            headers["Authorization"] = f"Bearer {self.source.api_token}"
        return headers

    async def _resolve_local_node(self) -> None:
        """Look up the local node (hops_away=0) for this source and cache it."""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Node.node_num).where(
                        Node.source_id == self.source.id,
                        Node.hops_away == 0,
                    ).order_by(Node.node_num).limit(1)
                )
                local_num = result.scalar()
                if local_num is not None:
                    self._local_node_num = local_num
                    logger.debug(
                        f"Resolved local node for {self.source.name}: {local_num}"
                    )
        except Exception as e:
            logger.error(f"Could not resolve local node for {self.source.name}: {e}")

    async def _api_get(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        params: dict | None = None,
        max_retries: int = 5,
        base_delay: float = 2.0,
    ) -> httpx.Response:
        """Make a GET request with 429 rate-limit retry and exponential backoff.

        If the server responds with HTTP 429, retries up to ``max_retries``
        times. The delay between retries honours the ``Retry-After`` header
        when present; otherwise it uses exponential backoff capped at 120 s.

        For any other status code (including other errors) the response is
        returned immediately for the caller to handle.
        """
        for attempt in range(max_retries):
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 429:
                return response

            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    delay = base_delay * (2**attempt)
            else:
                delay = base_delay * (2**attempt)
            delay = min(delay, 120.0)

            logger.warning(
                f"Rate limited (429), retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            await asyncio.sleep(delay)

        # Final attempt after all retries exhausted
        return await client.get(url, headers=headers, params=params)

    async def _get_remote_version(self, client: httpx.AsyncClient, headers: dict) -> str | None:
        """Get version from the remote MeshMonitor health endpoint."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/health",
                headers,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("version")
            return None
        except Exception as e:
            logger.debug(f"Could not get remote version: {e}")
            return None

    async def test_connection(self) -> SourceTestResult:
        """Test connection to the MeshMonitor API."""
        if not self.source.url:
            return SourceTestResult(success=False, message="No URL configured")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try the health endpoint first
                response = await self._api_get(
                    client,
                    f"{self.source.url}/api/health",
                    self._get_headers(),
                )
                if response.status_code != 200:
                    return SourceTestResult(
                        success=False,
                        message=f"Health check failed: {response.status_code}",
                    )

                # Try to get nodes (use v1 API for token auth)
                response = await self._api_get(
                    client,
                    f"{self.source.url}/api/v1/nodes",
                    self._get_headers(),
                )
                if response.status_code == 200:
                    data = response.json()
                    nodes = data if isinstance(data, list) else data.get("data", [])
                    return SourceTestResult(
                        success=True,
                        message="Connection successful",
                        nodes_found=len(nodes),
                    )
                else:
                    return SourceTestResult(
                        success=False,
                        message=f"Failed to fetch nodes: {response.status_code}",
                    )
        except httpx.TimeoutException:
            return SourceTestResult(success=False, message="Connection timeout")
        except httpx.RequestError as e:
            return SourceTestResult(success=False, message=f"Connection error: {e}")
        except Exception as e:
            return SourceTestResult(success=False, message=f"Error: {e}")

    async def collect(self) -> None:
        """Collect data from the MeshMonitor API."""
        if not self.source.url:
            logger.warning(f"Source {self.source.name} has no URL configured")
            return

        logger.info(f"Collecting from MeshMonitor: {self.source.name}")

        remote_version = None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = self._get_headers()

                # Fetch version from health endpoint
                remote_version = await self._get_remote_version(client, headers)

                # Collect nodes
                await self._collect_nodes(client, headers)

                # Collect position history for all nodes
                await self._collect_position_history(client, headers)

                # Collect channels
                await self._collect_channels(client, headers)

                # Infer names for unnamed channels from cross-source messages
                await self._infer_missing_channel_names()

                # Collect messages
                await self._collect_messages(client, headers)

                # Collect telemetry
                await self._collect_telemetry(client, headers)

                # Collect traceroutes
                await self._collect_traceroutes(client, headers)

                # Collect packet records (encrypted, unknown, nodeinfo)
                await self._collect_packet_records(client, headers)

                # Collect solar production data
                await self._collect_solar(client, headers)

            # Update last poll time and version
            async with async_session_maker() as db:
                result = await db.execute(select(Source).where(Source.id == self.source.id))
                source = result.scalar()
                if source:
                    source.last_poll_at = datetime.now(UTC)
                    source.last_error = None
                    if remote_version:
                        source.remote_version = remote_version
                    await db.commit()

            logger.info(f"Collection complete for {self.source.name}")

        except Exception as e:
            logger.error(f"Collection error for {self.source.name}: {e}")
            # Record the error
            async with async_session_maker() as db:
                result = await db.execute(select(Source).where(Source.id == self.source.id))
                source = result.scalar()
                if source:
                    source.last_error = str(e)
                    await db.commit()

    async def _collect_nodes(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect nodes from the API (uses v1 API for token auth)."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/nodes",
                headers,
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch nodes: {response.status_code}")
                return

            data = response.json()
            nodes_data = data if isinstance(data, list) else data.get("data", [])

            async with async_session_maker() as db:
                for node_data in nodes_data:
                    await self._upsert_node(db, node_data)
                await db.commit()

            # Refresh cached local node (may have changed after upsert)
            await self._resolve_local_node()

            logger.debug(f"Collected {len(nodes_data)} nodes")
        except Exception as e:
            logger.error(f"Error collecting nodes: {e}")

    async def _upsert_node(self, db, node_data: dict) -> None:
        """Insert or update a node."""
        from uuid import uuid4

        from app.models.telemetry import TelemetryType

        node_num = node_data.get("nodeNum") or node_data.get("num")
        if not node_num:
            return

        result = await db.execute(
            select(Node).where(
                Node.source_id == self.source.id,
                Node.node_num == node_num,
            )
        )
        node = result.scalar()
        node_existed = node is not None

        # MeshMonitor nests user info in a "user" object
        user_data = node_data.get("user", {}) or {}
        position = node_data.get("position", {}) or {}

        # Extract fields - try both nested and flat structures
        node_id = user_data.get("id") or node_data.get("nodeId") or node_data.get("id")
        short_name = user_data.get("shortName") or node_data.get("shortName")
        long_name = user_data.get("longName") or node_data.get("longName")
        hw_model = user_data.get("hwModel") or node_data.get("hwModel")
        role = user_data.get("role") or node_data.get("role")

        # Convert hw_model to string if it's a number
        if hw_model is not None:
            hw_model = str(hw_model)
        if role is not None:
            role = str(role)

        # Extract signal info
        snr = node_data.get("snr")
        rssi = node_data.get("rssi")
        hops_away = node_data.get("hopsAway")

        # Extract position - v1 API uses flat fields, older API uses nested position object
        # Try flat fields first (v1 API), then fall back to nested position object
        new_lat = (
            node_data.get("latitude")
            or node_data.get("lat")
            or position.get("latitude")
            or position.get("lat")
        )
        new_lon = (
            node_data.get("longitude")
            or node_data.get("lon")
            or position.get("longitude")
            or position.get("lon")
        )
        new_alt = (
            node_data.get("altitude")
            or node_data.get("alt")
            or position.get("altitude")
            or position.get("alt")
        )
        position_time = position.get("time")
        precision_bits = position.get("precisionBits")

        # Capture old position state before updating (for change detection below)
        old_position_time = node.position_time if node else None
        old_lat = node.latitude if node else None
        old_lon = node.longitude if node else None

        if node:
            # Update existing node - only update fields with values (don't overwrite with None)
            if node_id is not None:
                node.node_id = node_id
            if short_name is not None:
                node.short_name = short_name
            if long_name is not None:
                node.long_name = long_name
            if hw_model is not None:
                node.hw_model = hw_model
            if role is not None:
                node.role = role
            # Only update position if new data has it (don't overwrite with None)
            if new_lat is not None:
                node.latitude = new_lat
            if new_lon is not None:
                node.longitude = new_lon
            if new_alt is not None:
                node.altitude = new_alt
            if position_time:
                node.position_time = datetime.fromtimestamp(position_time, tz=UTC)
            if precision_bits is not None:
                node.position_precision_bits = precision_bits
            if snr is not None:
                node.snr = snr
            if rssi is not None:
                node.rssi = rssi
            if hops_away is not None:
                node.hops_away = hops_away
            if node_data.get("lastHeard"):
                node.last_heard = datetime.fromtimestamp(node_data["lastHeard"], tz=UTC)
            is_licensed = node_data.get("isLicensed")
            if is_licensed is not None:
                node.is_licensed = is_licensed
            node.updated_at = datetime.now(UTC)
        else:
            # Create new node
            node = Node(
                source_id=self.source.id,
                node_num=node_num,
                node_id=node_id,
                short_name=short_name,
                long_name=long_name,
                hw_model=hw_model,
                role=role,
                latitude=new_lat,
                longitude=new_lon,
                altitude=new_alt,
                position_precision_bits=precision_bits,
                snr=snr,
                rssi=rssi,
                hops_away=hops_away,
                is_licensed=node_data.get("isLicensed", False),
            )
            if position_time:
                node.position_time = datetime.fromtimestamp(position_time, tz=UTC)
            if node_data.get("lastHeard"):
                node.last_heard = datetime.fromtimestamp(node_data["lastHeard"], tz=UTC)
            db.add(node)

        # Insert position telemetry when position data has changed
        if new_lat is not None and new_lon is not None:
            position_changed = False
            if not node_existed:
                position_changed = True
            elif position_time and old_position_time:
                new_pt = datetime.fromtimestamp(position_time, tz=UTC)
                position_changed = new_pt != old_position_time
            elif old_lat != new_lat or old_lon != new_lon:
                position_changed = True

            if position_changed:
                received_at = (
                    datetime.fromtimestamp(position_time, tz=UTC)
                    if position_time
                    else datetime.now(UTC)
                )
                values = {
                    "id": str(uuid4()),
                    "source_id": self.source.id,
                    "node_num": node_num,
                    "telemetry_type": TelemetryType.POSITION,
                    "metric_name": "position",
                    "latitude": new_lat,
                    "longitude": new_lon,
                    "altitude": int(new_alt) if new_alt is not None else None,
                    "received_at": received_at,
                }
                stmt = (
                    pg_insert(Telemetry)
                    .values(**values)
                    .on_conflict_do_nothing(
                        index_elements=["source_id", "node_num", "received_at", "metric_name"]
                    )
                )
                await db.execute(stmt)

    async def _collect_channels(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect channel configuration from the v1 API."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/channels",
                headers,
            )
            if response.status_code == 404:
                # API not available on this MeshMonitor version
                logger.debug(f"Channels API not available on {self.source.name}")
                return
            if response.status_code != 200:
                logger.warning(f"Failed to fetch channels: {response.status_code}")
                return

            data = response.json()
            if not data.get("success"):
                logger.warning(f"Channels API returned error: {data}")
                return

            channels_data = data.get("data", [])

            async with async_session_maker() as db:
                for channel_data in channels_data:
                    await self._upsert_channel(db, channel_data)
                await db.commit()

            logger.debug(f"Collected {len(channels_data)} channels from {self.source.name}")
        except Exception as e:
            logger.error(f"Error collecting channels: {e}")

    async def _upsert_channel(self, db, channel_data: dict) -> None:
        """Insert or update a channel configuration."""
        channel_index = channel_data.get("id")
        if channel_index is None:
            return

        # Skip disabled channels (role 0)
        role = channel_data.get("role", 0)
        if role == 0:
            return

        result = await db.execute(
            select(Channel).where(
                Channel.source_id == self.source.id,
                Channel.channel_index == channel_index,
            )
        )
        channel = result.scalar()

        # Map role number to string
        role_name = channel_data.get("roleName", "").lower()
        if not role_name:
            role_map = {1: "primary", 2: "secondary"}
            role_name = role_map.get(role, "unknown")

        if channel:
            # Update existing channel
            channel.name = channel_data.get("name")
            channel.role = role_name
            channel.uplink_enabled = channel_data.get("uplinkEnabled", False)
            channel.downlink_enabled = channel_data.get("downlinkEnabled", False)
            channel.position_precision = channel_data.get("positionPrecision")
            channel.psk = channel_data.get("psk")
            channel.updated_at = datetime.now(UTC)
        else:
            # Create new channel
            channel = Channel(
                source_id=self.source.id,
                channel_index=channel_index,
                name=channel_data.get("name"),
                role=role_name,
                uplink_enabled=channel_data.get("uplinkEnabled", False),
                downlink_enabled=channel_data.get("downlinkEnabled", False),
                position_precision=channel_data.get("positionPrecision"),
                psk=channel_data.get("psk"),
            )
            db.add(channel)

    async def _infer_missing_channel_names(self) -> None:
        """Infer channel names for unnamed channels by cross-referencing messages.

        When a message (by meshtastic_id) appears in both this source and another
        source whose channel has a non-empty name, we adopt that name.  This
        handles the common case where MeshMonitor reports an empty name for the
        primary channel but MQTT knows it as e.g. "MediumFast".
        """
        try:
            async with async_session_maker() as db:
                # Find unnamed channels for this source
                unnamed_result = await db.execute(
                    select(Channel).where(
                        Channel.source_id == self.source.id,
                        or_(Channel.name.is_(None), Channel.name == ""),
                    )
                )
                unnamed_channels = unnamed_result.scalars().all()
                if not unnamed_channels:
                    return

                m1 = aliased(Message)  # message in this source
                m2 = aliased(Message)  # same message in another source

                updated = 0
                for ch in unnamed_channels:
                    # Find the most common channel name from cross-source
                    # message matches, so the majority vote wins.
                    result = await db.execute(
                        select(
                            Channel.name,
                            func.count().label("cnt"),
                        )
                        .select_from(m1)
                        .join(
                            m2,
                            (m1.meshtastic_id == m2.meshtastic_id) & (m1.source_id != m2.source_id),
                        )
                        .join(
                            Channel,
                            (m2.source_id == Channel.source_id)
                            & (m2.channel == Channel.channel_index),
                        )
                        .where(m1.source_id == self.source.id)
                        .where(m1.channel == ch.channel_index)
                        .where(m1.meshtastic_id.isnot(None))
                        .where(Channel.name.isnot(None))
                        .where(Channel.name != "")
                        .group_by(Channel.name)
                        .order_by(func.count().desc())
                        .limit(1)
                    )
                    row = result.first()
                    inferred_name = row.name if row else None
                    if inferred_name:
                        ch.name = inferred_name
                        updated += 1

                if updated:
                    await db.commit()
                    logger.info(f"Inferred {updated} channel name(s) for {self.source.name}")
        except Exception as e:
            logger.error(f"Error inferring channel names: {e}")

    async def _collect_messages(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect messages from the API."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/messages",
                headers,
                params={"limit": 100},
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch messages: {response.status_code}")
                return

            data = response.json()
            # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
            if isinstance(data, dict) and "data" in data:
                messages_data = data.get("data", [])
            elif isinstance(data, list):
                messages_data = data
            else:
                messages_data = data.get("messages", [])

            async with async_session_maker() as db:
                inserted_count = 0
                for msg_data in messages_data:
                    try:
                        inserted = await self._insert_message(db, msg_data)
                        if inserted:
                            inserted_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to insert message: {e}")
                        continue
                await db.commit()

            logger.debug(f"Collected {inserted_count} messages (of {len(messages_data)} fetched)")
        except Exception as e:
            logger.error(f"Error collecting messages: {e}")

    async def _insert_message(self, db, msg_data: dict) -> bool:
        """Insert a message if it doesn't exist using ON CONFLICT DO NOTHING.

        Returns:
            True if record was inserted, False if skipped (duplicate or error)
        """
        from uuid import uuid4

        packet_id = msg_data.get("packetId") or msg_data.get("id")
        if not packet_id:
            return False

        # Ensure packet_id is a string
        packet_id = str(packet_id)

        # Get received_at from timestamp (milliseconds) or createdAt
        timestamp_ms = msg_data.get("timestamp") or msg_data.get("createdAt")
        try:
            received_at = (
                datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                if timestamp_ms
                else datetime.now(UTC)
            )
        except (TypeError, ValueError, OSError) as e:
            logger.warning(f"Invalid timestamp {timestamp_ms}: {e}")
            received_at = datetime.now(UTC)

        # Get rx_time (milliseconds)
        rx_time = None
        rx_time_ms = msg_data.get("rxTime")
        if rx_time_ms:
            try:
                rx_time = datetime.fromtimestamp(rx_time_ms / 1000, tz=UTC)
            except (TypeError, ValueError, OSError) as e:
                logger.warning(f"Invalid rx_time {rx_time_ms}: {e}")

        # Handle broadcast address (0xFFFFFFFF = 4294967295)
        to_node_num = msg_data.get("toNodeNum") or msg_data.get("to")
        if to_node_num == 4294967295:
            to_node_num = None  # Store as NULL for broadcast messages

        # Extract raw Meshtastic packet ID from composite format
        meshtastic_id = None
        raw_part = packet_id.rsplit("_", 1)[-1] if "_" in packet_id else packet_id
        try:
            meshtastic_id = int(raw_part)
        except (ValueError, TypeError):
            pass

        # Build values dict for the insert
        values = {
            "id": str(uuid4()),
            "source_id": self.source.id,
            "packet_id": packet_id,
            "meshtastic_id": meshtastic_id,
            "from_node_num": msg_data.get("fromNodeNum") or msg_data.get("from"),
            "to_node_num": to_node_num,
            "channel": msg_data.get("channel", 0),
            "text": msg_data.get("text"),
            "reply_id": msg_data.get("replyId"),
            "emoji": self._decode_emoji(msg_data.get("emoji")),
            "hop_limit": msg_data.get("hopLimit"),
            "hop_start": msg_data.get("hopStart"),
            "rx_snr": msg_data.get("rxSnr"),
            "rx_rssi": msg_data.get("rxRssi"),
            "relay_node": msg_data.get("relayNode") or None,
            "gateway_node_num": self._local_node_num,  # Use local node as gateway
            "rx_time": rx_time,
            "received_at": received_at,
        }

        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
        # The unique index includes COALESCE(gateway_node_num, 0) so we must
        # match the full expression to satisfy PostgreSQL's conflict resolution.
        stmt = (
            pg_insert(Message)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[
                    "source_id",
                    "packet_id",
                    text("COALESCE(gateway_node_num, 0)"),
                ]
            )
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def collect_messages_historical(
        self, batch_size: int = 500, delay_seconds: float = 2.0, max_batches: int = 100
    ) -> None:
        """Collect historical messages in batches to avoid rate limiting.

        Args:
            batch_size: Number of records per batch
            delay_seconds: Delay between batches
            max_batches: Maximum number of batches to fetch
        """
        if not self.source.url:
            logger.warning(f"Source {self.source.name} has no URL configured")
            return

        logger.info(
            f"Starting historical message collection for {self.source.name} "
            f"(batch_size={batch_size}, delay={delay_seconds}s, max_batches={max_batches})"
        )

        total_collected = 0
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                for batch_num in range(max_batches):
                    if not self._running:
                        logger.info(f"Historical message collection stopped for {self.source.name}")
                        break

                    # Fetch a batch of messages
                    try:
                        response = await self._api_get(
                            client,
                            f"{self.source.url}/api/v1/messages",
                            headers,
                            params={"limit": batch_size, "offset": offset},
                        )
                        if response.status_code != 200:
                            logger.warning(
                                f"Failed to fetch messages batch {batch_num + 1}: {response.status_code}"
                            )
                            break

                        data = response.json()
                        # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
                        if isinstance(data, dict) and "data" in data:
                            messages_data = data.get("data", [])
                        elif isinstance(data, list):
                            messages_data = data
                        else:
                            messages_data = data.get("messages", [])

                        if not messages_data:
                            logger.info(f"No more historical messages for {self.source.name}")
                            break

                        # Insert messages
                        async with async_session_maker() as db:
                            batch_inserted = 0
                            for msg_data in messages_data:
                                try:
                                    inserted = await self._insert_message(db, msg_data)
                                    if inserted:
                                        batch_inserted += 1
                                except Exception as e:
                                    logger.debug(f"Failed to insert message: {e}")
                                    continue
                            await db.commit()

                        total_collected += batch_inserted
                        offset += batch_size

                        logger.debug(
                            f"Historical messages batch {batch_num + 1}: inserted {batch_inserted} "
                            f"of {len(messages_data)} fetched (total: {total_collected}) from {self.source.name}"
                        )

                        # If we got fewer messages than requested, we've reached the end
                        if len(messages_data) < batch_size:
                            logger.info(
                                f"Reached end of historical messages for {self.source.name}"
                            )
                            break

                        # Delay before next batch to avoid rate limiting
                        if batch_num < max_batches - 1:
                            await asyncio.sleep(delay_seconds)

                    except Exception as e:
                        logger.error(f"Error collecting messages batch {batch_num + 1}: {e}")
                        break

            logger.info(
                f"Historical message collection complete for {self.source.name}: "
                f"{total_collected} messages"
            )

        except Exception as e:
            logger.error(f"Error in historical message collection: {e}")

    async def _collect_telemetry(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect telemetry from the API."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/telemetry",
                headers,
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch telemetry: {response.status_code}")
                return

            data = response.json()
            # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
            if isinstance(data, dict) and "data" in data:
                telemetry_data = data.get("data", [])
            elif isinstance(data, list):
                telemetry_data = data
            else:
                telemetry_data = data.get("telemetry", [])

            async with async_session_maker() as db:
                for telem in telemetry_data:
                    await self._insert_telemetry(db, telem)
                await db.commit()

            logger.debug(f"Collected {len(telemetry_data)} telemetry records")
        except Exception as e:
            logger.error(f"Error collecting telemetry: {e}")

    async def _insert_telemetry(self, db, telem_data: dict, skip_duplicates: bool = False) -> bool:
        """Insert telemetry data using ON CONFLICT DO NOTHING for deduplication.

        Args:
            db: Database session
            telem_data: Telemetry data dict
            skip_duplicates: Unused, kept for backward compatibility.
                            Deduplication now always uses ON CONFLICT DO NOTHING.

        Returns:
            True if record was inserted, False if skipped (duplicate)
        """
        from uuid import uuid4

        from app.models.telemetry import TelemetryType

        node_num = telem_data.get("nodeNum") or telem_data.get("from")
        if not node_num:
            return False

        # MeshMonitor uses flat format with telemetryType field
        # e.g., {"nodeNum": 123, "telemetryType": "batteryLevel", "value": 86, "timestamp": ...}
        telem_type_field = telem_data.get("telemetryType", "")
        value = telem_data.get("value")

        # Handle MeshMonitor flat format
        if telem_type_field and value is not None:
            # Resolve type via registry
            metric_name_resolved = CAMEL_TO_METRIC.get(telem_type_field, telem_type_field)
            metric_def = METRIC_REGISTRY.get(metric_name_resolved)
            telem_type = metric_def.telemetry_type if metric_def else TelemetryType.DEVICE

            # Get timestamp from MeshMonitor data
            timestamp_ms = telem_data.get("timestamp") or telem_data.get("createdAt")
            received_at = datetime.now(UTC)
            if timestamp_ms:
                received_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)

            # Build values dict for the insert
            values = {
                "id": str(uuid4()),
                "source_id": self.source.id,
                "node_num": node_num,
                "metric_name": metric_name_resolved,
                "telemetry_type": telem_type,
                "received_at": received_at,
                "raw_value": float(value) if value is not None else None,
            }
            # Populate dedicated column if metric has one
            if metric_def and metric_def.dedicated_column:
                values[metric_def.dedicated_column] = value

            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
            stmt = (
                pg_insert(Telemetry)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["source_id", "node_num", "received_at", "metric_name"]
                )
            )
            result = await db.execute(stmt)
            return result.rowcount > 0
        else:
            # Handle nested format (deviceMetrics, environmentMetrics, etc.)
            # Dynamically iterate all known sub-message types from the registry
            inserted = False
            received_at = datetime.now(UTC)

            for submsg_key, sub_type in SUBMESSAGE_TYPE_MAP.items():
                sub_metrics = telem_data.get(submsg_key, {}) or {}
                if not isinstance(sub_metrics, dict):
                    continue
                for camel_key, metric_value in sub_metrics.items():
                    if metric_value is None or not isinstance(metric_value, (int, float)):
                        continue
                    resolved_name = CAMEL_TO_METRIC.get(camel_key, camel_key)
                    metric_def = METRIC_REGISTRY.get(resolved_name)
                    values = {
                        "id": str(uuid4()),
                        "source_id": self.source.id,
                        "node_num": node_num,
                        "metric_name": resolved_name,
                        "telemetry_type": sub_type,
                        "received_at": received_at,
                        "raw_value": float(metric_value),
                    }
                    if metric_def and metric_def.dedicated_column:
                        values[metric_def.dedicated_column] = metric_value
                    stmt = (
                        pg_insert(Telemetry)
                        .values(**values)
                        .on_conflict_do_nothing(
                            index_elements=["source_id", "node_num", "received_at", "metric_name"]
                        )
                    )
                    result = await db.execute(stmt)
                    if result.rowcount > 0:
                        inserted = True

            return inserted

    async def _collect_traceroutes(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect traceroutes from the API."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/traceroutes",
                headers,
                params={"limit": 100},  # Get recent traceroutes
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch traceroutes: {response.status_code}")
                return

            data = response.json()
            # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
            if isinstance(data, dict) and "data" in data:
                routes_data = data.get("data", [])
            elif isinstance(data, list):
                routes_data = data
            else:
                routes_data = data.get("traceroutes", [])

            async with async_session_maker() as db:
                for route in routes_data:
                    await self._insert_traceroute(db, route)
                await db.commit()

            logger.debug(f"Collected {len(routes_data)} traceroutes")
        except Exception as e:
            logger.error(f"Error collecting traceroutes: {e}")

    def _decode_emoji(self, value) -> str | None:
        """Decode an emoji value that may be an int codepoint or string."""
        if value is None:
            return None
        if isinstance(value, int):
            # Filter control characters (< 0x20) — e.g. Meshtastic sends 0x01 as a
            # "reaction present" flag, not a real emoji codepoint
            return chr(value) if 0x20 <= value <= 0x10FFFF else None
        if isinstance(value, str) and value:
            # If it's a numeric string (e.g. "128077"), convert to emoji
            try:
                codepoint = int(value)
                return chr(codepoint) if 0x20 <= codepoint <= 0x10FFFF else None
            except (ValueError, OverflowError):
                pass
            return value
        return None

    def _parse_array_field(self, value) -> list[int] | None:
        """Parse an array field that may be a string, list, or None."""
        import json

        if value is None:
            return None
        if isinstance(value, list):
            # Ensure all elements are integers
            return [int(x) for x in value if x is not None]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [int(x) for x in parsed if x is not None]
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def _parse_route_positions(self, value) -> dict | None:
        """Parse routePositions from the API response.

        The field may be a JSON string or a dict. Returns a dict mapping
        node number strings to {lat, lng, alt?}, or None if not available.
        """
        import json

        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return None
        if isinstance(value, dict):
            return value if value else None
        return None

    async def _insert_traceroute(self, db, route_data: dict) -> bool:
        """Insert a traceroute using ON CONFLICT DO NOTHING for deduplication.

        Returns:
            True if record was inserted, False if skipped (duplicate)
        """
        from uuid import uuid4

        from_node = route_data.get("fromNodeNum") or route_data.get("from")
        to_node = route_data.get("toNodeNum") or route_data.get("to")

        if not from_node or not to_node:
            return False

        route = self._parse_array_field(route_data.get("route"))
        route_back = self._parse_array_field(route_data.get("routeBack"))
        snr_towards = self._parse_array_field(route_data.get("snrTowards"))
        snr_back = self._parse_array_field(route_data.get("snrBack"))

        # Get timestamp from API response (milliseconds or seconds)
        timestamp_val = route_data.get("timestamp") or route_data.get("createdAt")
        if timestamp_val:
            # Handle both milliseconds and seconds timestamps
            if timestamp_val > 1e12:  # Likely milliseconds
                received_at = datetime.fromtimestamp(timestamp_val / 1000, tz=UTC)
            else:
                received_at = datetime.fromtimestamp(timestamp_val, tz=UTC)
        else:
            received_at = datetime.now(UTC)

        # Parse route_positions (historical node positions at traceroute time)
        route_positions = self._parse_route_positions(route_data.get("routePositions"))

        # Build values dict for the insert
        values = {
            "id": str(uuid4()),
            "source_id": self.source.id,
            "from_node_num": from_node,
            "to_node_num": to_node,
            "route": route or [],
            "route_back": route_back,
            "snr_towards": snr_towards,
            "snr_back": snr_back,
            "route_positions": route_positions,
            "received_at": received_at,
        }

        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
        stmt = (
            pg_insert(Traceroute)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["source_id", "from_node_num", "to_node_num", "received_at"]
            )
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    # Known portnums that are already collected by other methods
    _KNOWN_PORTNUMS = {1, 3, 67, 70}  # TEXT, POSITION, TELEMETRY, TRACEROUTE

    async def _collect_packet_records(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect packet records (encrypted, unknown, nodeinfo) from the packets API."""
        try:
            offset = 0
            limit = 100
            max_total = 10000
            inserted_count = 0

            while offset < max_total:
                response = await self._api_get(
                    client,
                    f"{self.source.url}/api/v1/packets",
                    headers,
                    params={"limit": limit, "offset": offset},
                )
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch packets: {response.status_code}")
                    return

                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    packets_data = data.get("data", [])
                elif isinstance(data, list):
                    packets_data = data
                else:
                    packets_data = []

                if not packets_data:
                    break

                async with async_session_maker() as db:
                    for pkt in packets_data:
                        inserted = await self._insert_packet_record(db, pkt)
                        if inserted:
                            inserted_count += 1
                    await db.commit()

                # Stop if we got fewer than the limit (last page)
                if len(packets_data) < limit:
                    break
                offset += limit

            logger.debug(f"Collected {inserted_count} packet records")
        except Exception as e:
            logger.error(f"Error collecting packet records: {e}")

    async def _insert_packet_record(self, db, pkt_data: dict) -> bool:
        """Classify and insert a packet record. Returns True if inserted."""
        from uuid import uuid4

        from_node = pkt_data.get("from_node")
        if not from_node:
            return False

        to_node = pkt_data.get("to_node")
        encrypted = pkt_data.get("encrypted", False)
        portnum = pkt_data.get("portnum")
        portnum_name = pkt_data.get("portnum_name")

        # Classify the packet
        if encrypted:
            packet_type = PacketRecordType.ENCRYPTED
        elif portnum == 4:  # NODEINFO_APP
            packet_type = PacketRecordType.NODEINFO
        elif portnum not in self._KNOWN_PORTNUMS:
            packet_type = PacketRecordType.UNKNOWN
        else:
            # Known portnum (text, position, telemetry, traceroute) — skip
            return False

        # Parse timestamp
        timestamp_val = pkt_data.get("timestamp")
        if timestamp_val:
            if timestamp_val > 1e12:  # Likely milliseconds
                received_at = datetime.fromtimestamp(timestamp_val / 1000, tz=UTC)
            else:
                received_at = datetime.fromtimestamp(timestamp_val, tz=UTC)
        else:
            received_at = datetime.now(UTC)

        # Extract meshtastic packet ID for cross-source dedup
        raw_pkt_id = pkt_data.get("packetId") or pkt_data.get("id")
        meshtastic_id = None
        if raw_pkt_id is not None:
            try:
                meshtastic_id = int(raw_pkt_id)
            except (TypeError, ValueError):
                pass

        values = {
            "id": str(uuid4()),
            "source_id": self.source.id,
            "from_node_num": from_node,
            "to_node_num": to_node,
            "meshtastic_id": meshtastic_id,
            "packet_type": packet_type,
            "portnum": portnum_name,
            "received_at": received_at,
        }

        stmt = (
            pg_insert(PacketRecord)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["source_id", "from_node_num", "packet_type", "received_at"]
            )
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def _collect_solar(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect solar production data from the API."""
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/solar",
                headers,
                params={"limit": 100},
            )
            if response.status_code == 404:
                # Solar endpoint not available on this MeshMonitor instance
                logger.debug(f"Solar endpoint not available for {self.source.name}")
                return
            if response.status_code != 200:
                logger.warning(f"Failed to fetch solar data: {response.status_code}")
                return

            data = response.json()
            # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
            if isinstance(data, dict) and "data" in data:
                solar_data = data.get("data", [])
            elif isinstance(data, list):
                solar_data = data
            else:
                solar_data = []

            if not solar_data:
                return

            async with async_session_maker() as db:
                for record in solar_data:
                    await self._insert_solar_record(db, record)
                await db.commit()

            logger.debug(f"Collected {len(solar_data)} solar production records")
        except Exception as e:
            logger.error(f"Error collecting solar data: {e}")

    async def _insert_solar_record(self, db, record: dict) -> bool:
        """Insert a solar production record using ON CONFLICT DO NOTHING.

        Args:
            db: Database session
            record: Solar production data dict with timestamp, wattHours, fetchedAt

        Returns:
            True if record was inserted, False if skipped (duplicate)
        """
        from uuid import uuid4

        # Get timestamp (Unix seconds)
        timestamp_sec = record.get("timestamp")
        if not timestamp_sec:
            return False

        # Convert to datetime
        timestamp = datetime.fromtimestamp(timestamp_sec, tz=UTC)

        # Get watt hours
        watt_hours = record.get("wattHours")
        if watt_hours is None:
            return False

        # Get fetchedAt if available
        fetched_at = None
        if record.get("fetchedAt"):
            fetched_at = datetime.fromtimestamp(record["fetchedAt"], tz=UTC)

        # Build values dict for the insert
        values = {
            "id": str(uuid4()),
            "source_id": self.source.id,
            "timestamp": timestamp,
            "watt_hours": float(watt_hours),
            "fetched_at": fetched_at,
            "received_at": datetime.now(UTC),
        }

        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
        stmt = (
            pg_insert(SolarProduction)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["source_id", "timestamp"])
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def collect_solar_historical(
        self,
        batch_size: int = 500,
        delay_seconds: float = 2.0,
        max_batches: int = 100,
    ) -> int:
        """Collect all historical solar production data.

        Fetches solar data going back as far as available.

        Args:
            batch_size: Records per batch
            delay_seconds: Delay between batches
            max_batches: Maximum batches to fetch

        Returns:
            Total number of records collected
        """
        if not self.source.url:
            return 0

        logger.info(f"Starting historical solar collection for {self.source.name}")

        total_collected = 0
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                for batch_num in range(max_batches):
                    params: dict = {"limit": batch_size}
                    if offset > 0:
                        params["offset"] = offset

                    response = await self._api_get(
                        client,
                        f"{self.source.url}/api/v1/solar",
                        headers,
                        params=params,
                    )

                    if response.status_code == 404:
                        logger.debug(f"Solar endpoint not available for {self.source.name}")
                        break

                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch solar data: {response.status_code}")
                        break

                    data = response.json()
                    if isinstance(data, dict) and "data" in data:
                        solar_data = data.get("data", [])
                    elif isinstance(data, list):
                        solar_data = data
                    else:
                        solar_data = []

                    if not solar_data:
                        logger.debug(f"No more solar data for {self.source.name}")
                        break

                    # Insert records
                    batch_inserted = 0
                    async with async_session_maker() as db:
                        for record in solar_data:
                            inserted = await self._insert_solar_record(db, record)
                            if inserted:
                                batch_inserted += 1
                        await db.commit()

                    total_collected += batch_inserted
                    offset += batch_size

                    logger.debug(
                        f"Solar batch {batch_num + 1}: fetched {len(solar_data)}, "
                        f"inserted {batch_inserted} (total: {total_collected})"
                    )

                    # If we got less than requested, we've reached the end
                    if len(solar_data) < batch_size:
                        break

                    # Delay before next batch
                    if batch_num < max_batches - 1:
                        await asyncio.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Error in solar historical collection: {e}")

        logger.info(f"Solar historical collection complete: {total_collected} records")
        return total_collected

    async def collect_historical_batch(
        self, batch_size: int = 500, delay_seconds: float = 5.0, max_batches: int = 20
    ) -> None:
        """Collect historical data in batches to avoid rate limiting.

        Args:
            batch_size: Number of records per batch
            delay_seconds: Delay between batches
            max_batches: Maximum number of batches to fetch
        """
        if not self.source.url:
            logger.warning(f"Source {self.source.name} has no URL configured")
            return

        logger.info(
            f"Starting historical data collection for {self.source.name} "
            f"(batch_size={batch_size}, delay={delay_seconds}s, max_batches={max_batches})"
        )

        # Initialize collection status
        self.collection_status.status = "collecting"
        self.collection_status.current_batch = 0
        self.collection_status.max_batches = max_batches
        self.collection_status.total_collected = 0
        self.collection_status.last_error = None
        self.collection_status.start_time = datetime.now()  # Use local time for ETA tracking
        self.collection_status.last_completion_time = None
        self.collection_status.last_completed_count = 0
        self.collection_status.smoothed_rate = None

        total_collected = 0
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                for batch_num in range(max_batches):
                    if not self._running:
                        logger.info(f"Historical collection stopped for {self.source.name}")
                        self.collection_status.status = "complete"
                        self.collection_status.start_time = None  # Clear start time when complete
                        break

                    # Update status
                    self.collection_status.current_batch = batch_num + 1

                    # Fetch a batch of telemetry
                    count = await self._collect_telemetry_batch(
                        client, headers, limit=batch_size, offset=offset
                    )

                    if count == 0:
                        logger.info(f"No more historical data for {self.source.name}")
                        self.collection_status.status = "complete"
                        self.collection_status.start_time = None  # Clear start time when complete
                        break

                    total_collected += count
                    self.collection_status.total_collected = total_collected
                    offset += batch_size

                    logger.debug(
                        f"Historical batch {batch_num + 1}: collected {count} records "
                        f"(total: {total_collected}) from {self.source.name}"
                    )

                    # Delay before next batch to avoid rate limiting
                    if batch_num < max_batches - 1:
                        await asyncio.sleep(delay_seconds)
                else:
                    # Completed all batches
                    self.collection_status.status = "complete"
                    self.collection_status.start_time = None  # Clear start time when complete

            logger.info(
                f"Historical data collection complete for {self.source.name}: "
                f"{total_collected} telemetry records"
            )

        except Exception as e:
            logger.error(f"Historical collection error for {self.source.name}: {e}")
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)
            self.collection_status.start_time = None  # Clear start time on error

    async def _get_telemetry_count(self, client: httpx.AsyncClient, headers: dict) -> int | None:
        """Get total telemetry count from the API.

        Returns the total count or None if the endpoint is not available.
        """
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/telemetry/count",
                headers,
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "count" in data:
                    return data["count"]
            return None
        except Exception as e:
            logger.debug(f"Could not get telemetry count: {e}")
            return None

    async def sync_all_data(self, batch_size: int = 500, delay_seconds: float = 5.0) -> None:
        """Sync all data from the source, skipping duplicates.

        This fetches ALL telemetry data (no batch limit) and inserts only
        new records that don't already exist in the database.

        Args:
            batch_size: Number of records per batch
            delay_seconds: Delay between batches to avoid rate limiting
        """
        if not self.source.url:
            logger.warning(f"Source {self.source.name} has no URL configured")
            return

        logger.info(
            f"Starting full data sync for {self.source.name} "
            f"(batch_size={batch_size}, delay={delay_seconds}s)"
        )

        # Initialize collection status
        self.collection_status.status = "collecting"
        self.collection_status.current_batch = 0
        self.collection_status.max_batches = 0  # Will be set after getting count
        self.collection_status.total_collected = 0
        self.collection_status.last_error = None
        self.collection_status.start_time = datetime.now()  # Use local time for ETA tracking
        self.collection_status.last_completion_time = None
        self.collection_status.last_completed_count = 0
        self.collection_status.smoothed_rate = None

        total_fetched = 0
        total_inserted = 0
        offset = 0
        batch_num = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                # Try to get total count for progress tracking
                total_count = await self._get_telemetry_count(client, headers)
                if total_count is not None:
                    self.collection_status.max_batches = (
                        total_count + batch_size - 1
                    ) // batch_size
                    logger.info(
                        f"Sync will process ~{total_count} records in "
                        f"~{self.collection_status.max_batches} batches"
                    )

                while self._running:
                    batch_num += 1
                    self.collection_status.current_batch = batch_num

                    # Fetch batch
                    params = {"limit": batch_size, "offset": offset}
                    response = await self._api_get(
                        client,
                        f"{self.source.url}/api/v1/telemetry",
                        headers,
                        params=params,
                    )

                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch telemetry: {response.status_code}")
                        self.collection_status.status = "error"
                        self.collection_status.last_error = f"HTTP {response.status_code}"
                        return

                    data = response.json()
                    if isinstance(data, dict) and "data" in data:
                        telemetry_data = data.get("data", [])
                    elif isinstance(data, list):
                        telemetry_data = data
                    else:
                        telemetry_data = data.get("telemetry", [])

                    if not telemetry_data:
                        logger.info(f"No more data for {self.source.name}")
                        break

                    total_fetched += len(telemetry_data)
                    batch_inserted = 0

                    # Insert with duplicate checking
                    async with async_session_maker() as db:
                        for telem in telemetry_data:
                            inserted = await self._insert_telemetry(db, telem, skip_duplicates=True)
                            if inserted:
                                batch_inserted += 1
                        await db.commit()

                    total_inserted += batch_inserted
                    self.collection_status.total_collected = total_inserted
                    offset += batch_size

                    logger.debug(
                        f"Sync batch {batch_num}: fetched {len(telemetry_data)}, "
                        f"inserted {batch_inserted} (total: {total_inserted}) "
                        f"from {self.source.name}"
                    )

                    # Delay before next batch
                    await asyncio.sleep(delay_seconds)

            self.collection_status.status = "complete"
            self.collection_status.start_time = None  # Clear start time when complete
            self.collection_status.max_batches = batch_num
            logger.info(
                f"Full sync complete for {self.source.name}: "
                f"fetched {total_fetched}, inserted {total_inserted} new records"
            )

        except Exception as e:
            logger.error(f"Sync error for {self.source.name}: {e}")
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)
            self.collection_status.start_time = None  # Clear start time on error

    async def _collect_telemetry_batch(
        self, client: httpx.AsyncClient, headers: dict, limit: int, offset: int = 0
    ) -> int:
        """Collect a batch of telemetry from the API.

        Returns the number of records collected.
        """
        try:
            params = {"limit": limit}
            if offset > 0:
                params["offset"] = offset

            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/telemetry",
                headers,
                params=params,
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch telemetry batch: {response.status_code}")
                return 0

            data = response.json()
            # MeshMonitor wraps data in {"success": true, "count": N, "data": [...]}
            if isinstance(data, dict) and "data" in data:
                telemetry_data = data.get("data", [])
            elif isinstance(data, list):
                telemetry_data = data
            else:
                telemetry_data = data.get("telemetry", [])

            if not telemetry_data:
                return 0

            async with async_session_maker() as db:
                for telem in telemetry_data:
                    await self._insert_telemetry(db, telem)
                await db.commit()

            return len(telemetry_data)
        except Exception as e:
            logger.error(f"Error collecting telemetry batch: {e}")
            return 0

    async def _collect_node_telemetry_history(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        node_id: str,
        since_ms: int | None = None,
        before_ms: int | None = None,
        limit: int = 500,
    ) -> tuple[int, int | None]:
        """Collect historical telemetry for a specific node using the per-node API.

        Uses the new /api/v1/telemetry/{nodeId} endpoint with time-based filtering.

        Args:
            client: HTTP client
            headers: Request headers including auth
            node_id: Node ID (e.g., "!a2e4ff4c")
            since_ms: Only fetch records after this timestamp (milliseconds)
            before_ms: Only fetch records before this timestamp (milliseconds)
            limit: Maximum records per request

        Returns:
            Tuple of (records_collected, oldest_timestamp_ms) for pagination
        """
        try:
            params: dict = {"limit": limit}
            if since_ms:
                params["since"] = since_ms
            if before_ms:
                params["before"] = before_ms

            # URL-encode the node_id since it contains '!' character
            encoded_node_id = quote(node_id, safe="")
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/telemetry/{encoded_node_id}",
                headers,
                params=params,
            )

            if response.status_code == 404:
                # Endpoint not available (older MeshMonitor version)
                return 0, None

            if response.status_code != 200:
                logger.warning(
                    f"Failed to fetch telemetry for node {node_id}: {response.status_code}"
                )
                return 0, None

            data = response.json()
            if isinstance(data, dict) and "data" in data:
                telemetry_data = data.get("data", [])
            elif isinstance(data, list):
                telemetry_data = data
            else:
                telemetry_data = []

            if not telemetry_data:
                return 0, None

            # Find the oldest timestamp for pagination
            oldest_ts = None
            for telem in telemetry_data:
                ts = telem.get("timestamp") or telem.get("createdAt")
                if ts and (oldest_ts is None or ts < oldest_ts):
                    oldest_ts = ts

            # Insert into database
            async with async_session_maker() as db:
                for telem in telemetry_data:
                    await self._insert_telemetry(db, telem)
                await db.commit()

            return len(telemetry_data), oldest_ts

        except Exception as e:
            logger.error(f"Error collecting telemetry for node {node_id}: {e}")
            return 0, None

    async def _collect_node_position_history(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        node_id: str,
        node_num: int,
        since_ms: int | None = None,
        limit: int = 1000,
    ) -> tuple[int, bool]:
        """Collect historical positions for a specific node.

        Uses GET /api/v1/nodes/{nodeId}/position-history with offset pagination.

        Args:
            client: HTTP client
            headers: Request headers including auth
            node_id: Node ID (e.g., "!a2e4ff4c")
            node_num: Numeric node ID for database inserts
            since_ms: Only fetch records after this timestamp (milliseconds)
            limit: Maximum records per request

        Returns:
            Tuple of (records_collected, endpoint_available).
            endpoint_available is False when the endpoint returns 404
            (older MeshMonitor without this feature).
        """
        from uuid import uuid4

        from app.models.telemetry import TelemetryType

        total_collected = 0
        offset = 0
        encoded_node_id = quote(node_id, safe="")

        try:
            while True:
                params: dict = {"limit": limit, "offset": offset}
                if since_ms is not None:
                    params["since"] = since_ms

                response = await self._api_get(
                    client,
                    f"{self.source.url}/api/v1/nodes/{encoded_node_id}/position-history",
                    headers,
                    params=params,
                )

                if response.status_code == 404:
                    return 0, False

                if response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch position history for node {node_id}: "
                        f"{response.status_code}"
                    )
                    return total_collected, True

                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    positions = data.get("data", [])
                    total_available = data.get("total", 0)
                    page_count = data.get("count", len(positions))
                elif isinstance(data, list):
                    positions = data
                    total_available = len(positions)
                    page_count = len(positions)
                else:
                    positions = []
                    total_available = 0
                    page_count = 0

                if not positions:
                    break

                inserted = 0
                async with async_session_maker() as db:
                    for pos in positions:
                        timestamp_ms = pos.get("timestamp")
                        if not timestamp_ms:
                            continue

                        received_at = datetime.fromtimestamp(
                            timestamp_ms / 1000, tz=UTC
                        )
                        lat = pos.get("latitude")
                        lon = pos.get("longitude")
                        packet_id = pos.get("packetId")

                        values = {
                            "id": str(uuid4()),
                            "source_id": self.source.id,
                            "node_num": node_num,
                            "metric_name": "position",
                            "telemetry_type": TelemetryType.POSITION,
                            "received_at": received_at,
                            "latitude": lat,
                            "longitude": lon,
                            "meshtastic_id": packet_id,
                            "raw_value": None,
                        }

                        stmt = (
                            pg_insert(Telemetry)
                            .values(**values)
                            .on_conflict_do_nothing(
                                index_elements=[
                                    "source_id",
                                    "node_num",
                                    "received_at",
                                    "metric_name",
                                ]
                            )
                        )
                        await db.execute(stmt)
                        inserted += 1
                    await db.commit()

                total_collected += inserted

                # Check if there are more pages
                if total_available > offset + page_count:
                    offset += page_count
                else:
                    break

            return total_collected, True

        except Exception as e:
            logger.error(f"Error collecting position history for node {node_id}: {e}")
            return total_collected, True

    async def _collect_position_history(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        since_ms: int | None = None,
    ) -> int:
        """Collect position history for all nodes from this source.

        Queries the local Node table, then fetches position history
        for each node. Stops early if the endpoint returns 404
        (older MeshMonitor without position-history support).

        Args:
            client: HTTP client
            headers: Request headers including auth
            since_ms: Optional override for the since timestamp (milliseconds).
                If None, uses Source.last_poll_at (or 24h ago on first run).

        Returns:
            Total number of position records collected
        """
        # Determine since_ms from last_poll_at if not provided
        if since_ms is None:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Source).where(Source.id == self.source.id)
                )
                source = result.scalar()
                if source and source.last_poll_at:
                    since_ms = int(source.last_poll_at.timestamp() * 1000)
                else:
                    # First run: go back 24 hours
                    since_ms = int(
                        (datetime.now(UTC) - timedelta(hours=24)).timestamp() * 1000
                    )

        # Get all nodes for this source that have a node_id
        async with async_session_maker() as db:
            nodes_result = await db.execute(
                select(Node.node_id, Node.node_num).where(
                    Node.source_id == self.source.id,
                    Node.node_id.isnot(None),
                )
            )
            nodes = nodes_result.all()

        if not nodes:
            return 0

        total_collected = 0
        for node_id, node_num in nodes:
            if not self._running:
                break

            count, available = await self._collect_node_position_history(
                client,
                headers,
                node_id,
                node_num,
                since_ms=since_ms,
            )
            total_collected += count

            if not available:
                logger.debug(
                    "Position history endpoint not available, "
                    "skipping remaining nodes"
                )
                break

            if count > 0:
                await asyncio.sleep(0.5)

        if total_collected > 0:
            logger.debug(f"Collected {total_collected} position history records")

        return total_collected

    async def collect_node_historical_telemetry(
        self,
        node_id: str,
        days_back: int = 7,
        batch_size: int = 500,
        delay_seconds: float = 2.0,
        max_batches: int = 100,
    ) -> int:
        """Collect historical telemetry for a specific node.

        Uses the new per-node API endpoint to fetch historical data going back
        a specified number of days.

        Args:
            node_id: Node ID (e.g., "!a2e4ff4c")
            days_back: How many days of history to fetch
            batch_size: Records per batch
            delay_seconds: Delay between batches
            max_batches: Maximum batches to fetch

        Returns:
            Total number of records collected
        """
        if not self.source.url:
            return 0

        # Calculate the cutoff timestamp
        cutoff_ms = int((datetime.now(UTC) - timedelta(days=days_back)).timestamp() * 1000)

        logger.info(
            f"Collecting historical telemetry for node {node_id} (up to {days_back} days back)"
        )

        total_collected = 0
        before_ms: int | None = None  # Start from now and work backwards

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                for batch_num in range(max_batches):
                    count, oldest_ts = await self._collect_node_telemetry_history(
                        client,
                        headers,
                        node_id,
                        since_ms=cutoff_ms,
                        before_ms=before_ms,
                        limit=batch_size,
                    )

                    if count == 0:
                        logger.debug(f"No more historical data for node {node_id}")
                        break

                    total_collected += count

                    # Update before_ms for next batch (go further back in time)
                    if oldest_ts:
                        before_ms = oldest_ts

                        # Check if we've gone back far enough
                        if oldest_ts <= cutoff_ms:
                            logger.debug(f"Reached cutoff date for node {node_id}")
                            break

                    logger.debug(
                        f"Node {node_id} batch {batch_num + 1}: "
                        f"collected {count} records (total: {total_collected})"
                    )

                    # Delay before next batch (minimal delay for faster collection)
                    if batch_num < max_batches - 1 and count == batch_size:
                        await asyncio.sleep(delay_seconds)

                    # Check if collection was cancelled
                    if not self._running:
                        break

        except Exception as e:
            logger.error(f"Error collecting historical telemetry for {node_id}: {e}")

        logger.info(f"Historical collection for node {node_id} complete: {total_collected} records")
        return total_collected

    async def collect_all_nodes_historical_telemetry(
        self,
        days_back: int = 7,
        batch_size: int = 500,
        delay_seconds: float = 2.0,
        max_concurrent: int = 10,
    ) -> int:
        """Collect historical telemetry for all known nodes.

        Fetches the list of nodes from the nodes endpoint, then collects
        historical telemetry for each one using the per-node API.
        Processes nodes in parallel for faster collection.

        Args:
            days_back: How many days of history to fetch per node
            batch_size: Records per batch
            delay_seconds: Delay between batches within a node
            max_concurrent: Maximum number of nodes to process in parallel

        Returns:
            Total number of records collected across all nodes
        """
        if not self.source.url:
            return 0

        logger.info(
            f"Starting historical telemetry collection for all nodes from {self.source.name} "
            f"(parallelism: {max_concurrent})"
        )

        # Initialize collection status
        self.collection_status.status = "collecting"
        self.collection_status.current_batch = 0
        self.collection_status.max_batches = 0
        self.collection_status.total_collected = 0
        self.collection_status.last_error = None
        self.collection_status.start_time = datetime.now()  # Use local time for ETA tracking
        self.collection_status.last_completion_time = None
        self.collection_status.last_completed_count = 0
        self.collection_status.smoothed_rate = None

        total_collected = 0

        try:
            nodes_url = f"{self.source.url}/api/v1/nodes"
            logger.debug(f"Fetching nodes from: {nodes_url}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                # First, get list of nodes
                response = await self._api_get(
                    client,
                    nodes_url,
                    headers,
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to fetch nodes: {response.status_code}")
                    self.collection_status.status = "error"
                    self.collection_status.last_error = f"HTTP {response.status_code}"
                    return 0

                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    nodes = data.get("data", [])
                elif isinstance(data, list):
                    nodes = data
                else:
                    nodes = []

                logger.info(f"Found {len(nodes)} nodes for historical collection")

                # Process nodes in parallel batches for faster collection
                semaphore = asyncio.Semaphore(max_concurrent)
                completed_nodes = 0
                completed_nodes_lock = (
                    asyncio.Lock()
                )  # Protect completed_nodes from race conditions

                async def collect_node_with_semaphore(node_data: dict, index: int) -> int:
                    """Collect data for a single node with semaphore limiting."""
                    async with semaphore:
                        # Check if collection was cancelled
                        if not self._running:
                            return 0

                        node_id = node_data.get("nodeId") or node_data.get("id")
                        if not node_id:
                            return 0

                        try:
                            count = await self.collect_node_historical_telemetry(
                                node_id=node_id,
                                days_back=days_back,
                                batch_size=batch_size,
                                delay_seconds=delay_seconds,
                            )

                            # Update progress only after successful collection
                            # Use lock to prevent race conditions when multiple coroutines complete simultaneously
                            async with completed_nodes_lock:
                                nonlocal completed_nodes
                                completed_nodes += 1
                                self.collection_status.current_batch = completed_nodes

                            return count
                        except Exception as e:
                            logger.error(f"Error collecting node {node_id}: {e}")
                            return 0

                # Create tasks for all nodes that have valid IDs
                tasks = [
                    collect_node_with_semaphore(node, i)
                    for i, node in enumerate(nodes)
                    if node.get("nodeId") or node.get("id")
                ]

                # Set max_batches to actual number of tasks created (nodes with valid IDs)
                # This ensures progress reaches 100% when all processable nodes are completed
                self.collection_status.max_batches = len(tasks)

                if len(tasks) < len(nodes):
                    logger.warning(
                        f"Skipping {len(nodes) - len(tasks)} nodes without valid nodeId/id "
                        f"(total nodes: {len(nodes)}, processable: {len(tasks)})"
                    )

                # Process in chunks to update progress more frequently
                chunk_size = max_concurrent * 2
                collection_cancelled = False
                for chunk_start in range(0, len(tasks), chunk_size):
                    if not self._running:
                        logger.info(f"Historical collection stopped for {self.source.name}")
                        self.collection_status.status = "cancelled"
                        self.collection_status.start_time = None  # Clear start time when cancelled
                        collection_cancelled = True
                        break

                    chunk = tasks[chunk_start : chunk_start + chunk_size]
                    results = await asyncio.gather(*chunk, return_exceptions=True)

                    # Sum up results
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Task error: {result}")
                        elif isinstance(result, int):
                            total_collected += result
                            self.collection_status.total_collected = total_collected

            # Only set status to "complete" if collection wasn't cancelled
            if not collection_cancelled:
                self.collection_status.status = "complete"
                self.collection_status.start_time = None  # Clear start time when complete

        except Exception as e:
            logger.error(f"Error in all-nodes historical collection: {e}", exc_info=True)
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)
            self.collection_status.start_time = None  # Clear start time on error

        logger.info(f"All-nodes historical collection complete: {total_collected} total records")
        return total_collected

    async def collect_since_last_poll(self) -> int:
        """Collect data that was missed since the last poll.

        This is called on startup to catch up on data that was missed while
        the collector was stopped. It uses the source's last_poll_at timestamp
        to determine what data to fetch.

        Returns:
            Total number of records collected
        """
        if not self.source.url:
            return 0

        # Get the latest last_poll_at from database
        async with async_session_maker() as db:
            result = await db.execute(select(Source).where(Source.id == self.source.id))
            source = result.scalar()
            if not source or not source.last_poll_at:
                logger.info(f"No last_poll_at for {self.source.name}, skipping catchup")
                return 0
            last_poll_at = source.last_poll_at

        # Calculate how long ago the last poll was
        now = datetime.now(UTC)
        time_since_last_poll = now - last_poll_at
        hours_since_last_poll = time_since_last_poll.total_seconds() / 3600

        # If less than 2x the poll interval, skip catchup (normal polling will handle it)
        min_catchup_hours = (self.source.poll_interval_seconds * 2) / 3600
        if hours_since_last_poll < min_catchup_hours:
            logger.debug(
                f"Skipping catchup for {self.source.name}: "
                f"only {hours_since_last_poll:.1f}h since last poll"
            )
            return 0

        logger.info(
            f"Starting catchup for {self.source.name}: "
            f"{hours_since_last_poll:.1f} hours since last poll"
        )

        # Convert to milliseconds for the API
        since_ms = int(last_poll_at.timestamp() * 1000)

        total_collected = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                # First get list of nodes to collect from
                response = await self._api_get(
                    client,
                    f"{self.source.url}/api/v1/nodes",
                    headers,
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to fetch nodes for catchup: {response.status_code}")
                    return 0

                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    nodes = data.get("data", [])
                elif isinstance(data, list):
                    nodes = data
                else:
                    nodes = []

                logger.info(f"Catching up {len(nodes)} nodes since {last_poll_at.isoformat()}")

                # Collect telemetry for each node since last_poll_at
                for node in nodes:
                    node_id = node.get("nodeId") or node.get("id")
                    if not node_id:
                        continue

                    # Collect all data since last_poll_at for this node
                    count, _ = await self._collect_node_telemetry_history(
                        client,
                        headers,
                        node_id,
                        since_ms=since_ms,
                        limit=500,
                    )
                    total_collected += count

                    # Small delay between nodes
                    if count > 0:
                        await asyncio.sleep(0.5)

                # Collect position history for each node since last_poll_at
                for node in nodes:
                    node_id = node.get("nodeId") or node.get("id")
                    node_num = node.get("nodeNum") or node.get("num")
                    if not node_id or not node_num:
                        continue

                    pos_count, available = await self._collect_node_position_history(
                        client,
                        headers,
                        node_id,
                        node_num,
                        since_ms=since_ms,
                    )
                    total_collected += pos_count

                    if not available:
                        break

                    if pos_count > 0:
                        await asyncio.sleep(0.5)

                # Also catch up solar data
                solar_count = await self._collect_solar_since(client, headers, since_ms)
                total_collected += solar_count

        except Exception as e:
            logger.error(f"Error during catchup for {self.source.name}: {e}")

        logger.info(f"Catchup complete for {self.source.name}: {total_collected} records")
        return total_collected

    async def _collect_solar_since(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        since_ms: int,
    ) -> int:
        """Collect solar data since a given timestamp.

        Args:
            client: HTTP client
            headers: Request headers
            since_ms: Only fetch records after this timestamp (milliseconds)

        Returns:
            Number of records collected
        """
        try:
            response = await self._api_get(
                client,
                f"{self.source.url}/api/v1/solar",
                headers,
                params={"since": since_ms, "limit": 500},
            )

            if response.status_code == 404:
                return 0

            if response.status_code != 200:
                logger.warning(f"Failed to fetch solar data: {response.status_code}")
                return 0

            data = response.json()
            if isinstance(data, dict) and "data" in data:
                solar_data = data.get("data", [])
            elif isinstance(data, list):
                solar_data = data
            else:
                solar_data = []

            if not solar_data:
                return 0

            count = 0
            async with async_session_maker() as db:
                for record in solar_data:
                    inserted = await self._insert_solar_record(db, record)
                    if inserted:
                        count += 1
                await db.commit()

            logger.debug(f"Collected {count} solar records during catchup")
            return count

        except Exception as e:
            logger.error(f"Error collecting solar data during catchup: {e}")
            return 0

    async def start(self, collect_history: bool = False) -> None:
        """Start periodic collection.

        Args:
            collect_history: If True, fetch historical data in the background
                           while also starting regular polling.
        """
        if self._running:
            return

        # Eagerly resolve the local node before any collection tasks start
        # so that _insert_message always uses a consistent gateway_node_num.
        await self._resolve_local_node()

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Started MeshMonitor collector: {self.source.name}")

        # Start historical collection in background if requested
        if collect_history:
            self._historical_task = asyncio.create_task(self._collect_historical_background())

    async def _collect_historical_positions(self, days_back: int = 7) -> int:
        """Collect historical position data for all nodes.

        Delegates to _collect_position_history with a since_ms computed
        from days_back.

        Args:
            days_back: How many days of history to fetch

        Returns:
            Total number of position records collected
        """
        if not self.source.url:
            return 0

        since_ms = int(
            (datetime.now(UTC) - timedelta(days=days_back)).timestamp() * 1000
        )

        logger.info(
            f"Collecting historical positions for {self.source.name} "
            f"(up to {days_back} days back)"
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()
                total = await self._collect_position_history(
                    client, headers, since_ms=since_ms
                )
        except Exception as e:
            logger.error(f"Error collecting historical positions: {e}")
            total = 0

        logger.info(
            f"Historical position collection complete for {self.source.name}: "
            f"{total} records"
        )
        return total

    async def _collect_historical_background(self) -> None:
        """Background task for historical data collection using per-node API."""
        try:
            # Wait a moment for the source to be fully committed and first poll to complete
            await asyncio.sleep(10)
            # Collect historical data for all nodes using per-node API
            # Use the source's configured historical_days_back value
            # Balanced approach considering:
            # - SQLite performance: avoid overwhelming MeshMonitor's database
            # - API token rate limits: ~10% of normal user limits
            # - Reasonable collection speed for initial sync
            await self.collect_all_nodes_historical_telemetry(
                days_back=self.source.historical_days_back,  # Use source configuration
                batch_size=500,
                delay_seconds=1.0,  # Balanced delay: faster than 2.0s but safer than 0.3s
                max_concurrent=5,  # Reduced from 10 to be gentler on SQLite and rate limits
            )
            # Also collect historical solar data
            await self.collect_solar_historical(
                batch_size=500,
                delay_seconds=2.0,
            )
            # Also collect historical messages
            await self.collect_messages_historical(
                batch_size=500,
                delay_seconds=2.0,
            )
            # Also collect historical position data
            await self._collect_historical_positions(
                days_back=self.source.historical_days_back,
            )
        except asyncio.CancelledError:
            logger.info(f"Historical collection cancelled for {self.source.name}")
            self.collection_status.status = "cancelled"
            raise
        except Exception as e:
            logger.error(f"Background historical collection failed: {e}")

    async def _poll_loop(self) -> None:
        """Polling loop."""
        while self._running:
            try:
                await self.collect()
            except Exception as e:
                logger.error(f"Poll error: {e}")

            # Wait for next poll
            await asyncio.sleep(self.source.poll_interval_seconds)

    async def stop(self) -> None:
        """Stop periodic collection."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Also stop historical collection if running
        if hasattr(self, "_historical_task") and self._historical_task:
            self._historical_task.cancel()
            try:
                await self._historical_task
            except asyncio.CancelledError:
                pass
            self.collection_status.status = "cancelled"
        logger.info(f"Stopped MeshMonitor collector: {self.source.name}")
