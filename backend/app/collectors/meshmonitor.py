"""MeshMonitor API collector."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.collectors.base import BaseCollector
from app.database import async_session_maker
from app.models import Channel, Message, Node, Source, Telemetry, Traceroute
from app.schemas.source import SourceTestResult

logger = logging.getLogger(__name__)


class CollectionStatus:
    """Status of historical data collection."""

    def __init__(self):
        self.status: str = "idle"  # idle, collecting, complete, error
        self.current_batch: int = 0
        self.max_batches: int = 0
        self.total_collected: int = 0
        self.last_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_batch": self.current_batch,
            "max_batches": self.max_batches,
            "total_collected": self.total_collected,
            "last_error": self.last_error,
        }


class MeshMonitorCollector(BaseCollector):
    """Collector for MeshMonitor API sources."""

    def __init__(self, source: Source):
        super().__init__(source)
        self._running = False
        self._task: asyncio.Task | None = None
        self._historical_task: asyncio.Task | None = None
        self.collection_status = CollectionStatus()

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Accept": "application/json"}
        if self.source.api_token:
            headers["Authorization"] = f"Bearer {self.source.api_token}"
        return headers

    async def _get_remote_version(
        self, client: httpx.AsyncClient, headers: dict
    ) -> str | None:
        """Get version from the remote MeshMonitor health endpoint."""
        try:
            response = await client.get(
                f"{self.source.url}/api/health",
                headers=headers,
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
                response = await client.get(
                    f"{self.source.url}/api/health",
                    headers=self._get_headers(),
                )
                if response.status_code != 200:
                    return SourceTestResult(
                        success=False,
                        message=f"Health check failed: {response.status_code}",
                    )

                # Try to get nodes
                response = await client.get(
                    f"{self.source.url}/api/nodes",
                    headers=self._get_headers(),
                )
                if response.status_code == 200:
                    data = response.json()
                    nodes = data if isinstance(data, list) else data.get("nodes", [])
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

                # Collect messages
                await self._collect_messages(client, headers)

                # Collect telemetry
                await self._collect_telemetry(client, headers)

                # Collect traceroutes
                await self._collect_traceroutes(client, headers)

            # Update last poll time and version
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Source).where(Source.id == self.source.id)
                )
                source = result.scalar()
                if source:
                    source.last_poll_at = datetime.now(timezone.utc)
                    source.last_error = None
                    if remote_version:
                        source.remote_version = remote_version
                    await db.commit()

            logger.info(f"Collection complete for {self.source.name}")

        except Exception as e:
            logger.error(f"Collection error for {self.source.name}: {e}")
            # Record the error
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Source).where(Source.id == self.source.id)
                )
                source = result.scalar()
                if source:
                    source.last_error = str(e)
                    await db.commit()

    async def _collect_nodes(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect nodes from the API."""
        try:
            response = await client.get(
                f"{self.source.url}/api/nodes",
                headers=headers,
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch nodes: {response.status_code}")
                return

            data = response.json()
            nodes_data = data if isinstance(data, list) else data.get("nodes", [])

            async with async_session_maker() as db:
                for node_data in nodes_data:
                    await self._upsert_node(db, node_data)
                await db.commit()

            logger.debug(f"Collected {len(nodes_data)} nodes")
        except Exception as e:
            logger.error(f"Error collecting nodes: {e}")

    async def _upsert_node(self, db, node_data: dict) -> None:
        """Insert or update a node."""
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

        if node:
            # Update existing node
            node.node_id = node_id
            node.short_name = short_name
            node.long_name = long_name
            node.hw_model = hw_model
            node.role = role
            node.latitude = position.get("latitude") or position.get("lat")
            node.longitude = position.get("longitude") or position.get("lon")
            node.altitude = position.get("altitude") or position.get("alt")
            if position.get("time"):
                node.position_time = datetime.fromtimestamp(
                    position["time"], tz=timezone.utc
                )
            node.position_precision_bits = position.get("precisionBits")
            node.snr = snr
            node.rssi = rssi
            node.hops_away = hops_away
            if node_data.get("lastHeard"):
                node.last_heard = datetime.fromtimestamp(
                    node_data["lastHeard"], tz=timezone.utc
                )
            node.is_licensed = node_data.get("isLicensed", False)
            node.updated_at = datetime.now(timezone.utc)
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
                latitude=position.get("latitude") or position.get("lat"),
                longitude=position.get("longitude") or position.get("lon"),
                altitude=position.get("altitude") or position.get("alt"),
                position_precision_bits=position.get("precisionBits"),
                snr=snr,
                rssi=rssi,
                hops_away=hops_away,
                is_licensed=node_data.get("isLicensed", False),
            )
            if position.get("time"):
                node.position_time = datetime.fromtimestamp(
                    position["time"], tz=timezone.utc
                )
            if node_data.get("lastHeard"):
                node.last_heard = datetime.fromtimestamp(
                    node_data["lastHeard"], tz=timezone.utc
                )
            db.add(node)

    async def _collect_messages(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect messages from the API."""
        try:
            response = await client.get(
                f"{self.source.url}/api/v1/messages",
                headers=headers,
                params={"limit": 100},
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch messages: {response.status_code}")
                return

            data = response.json()
            messages_data = data if isinstance(data, list) else data.get("messages", [])

            async with async_session_maker() as db:
                for msg_data in messages_data:
                    await self._insert_message(db, msg_data)
                await db.commit()

            logger.debug(f"Collected {len(messages_data)} messages")
        except Exception as e:
            logger.error(f"Error collecting messages: {e}")

    async def _insert_message(self, db, msg_data: dict) -> None:
        """Insert a message if it doesn't exist."""
        packet_id = msg_data.get("packetId") or msg_data.get("id")
        if not packet_id:
            return

        # Check if message already exists
        result = await db.execute(
            select(Message).where(
                Message.source_id == self.source.id,
                Message.packet_id == packet_id,
            )
        )
        if result.scalar():
            return  # Already exists

        message = Message(
            source_id=self.source.id,
            packet_id=packet_id,
            from_node_num=msg_data.get("fromNodeNum") or msg_data.get("from"),
            to_node_num=msg_data.get("toNodeNum") or msg_data.get("to"),
            channel=msg_data.get("channel", 0),
            text=msg_data.get("text"),
            reply_id=msg_data.get("replyId"),
            emoji=msg_data.get("emoji"),
            hop_limit=msg_data.get("hopLimit"),
            hop_start=msg_data.get("hopStart"),
            rx_snr=msg_data.get("rxSnr"),
            rx_rssi=msg_data.get("rxRssi"),
        )
        if msg_data.get("rxTime"):
            message.rx_time = datetime.fromtimestamp(msg_data["rxTime"], tz=timezone.utc)
        db.add(message)

    async def _collect_telemetry(self, client: httpx.AsyncClient, headers: dict) -> None:
        """Collect telemetry from the API."""
        try:
            response = await client.get(
                f"{self.source.url}/api/v1/telemetry",
                headers=headers,
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

        # Determine telemetry type based on the field
        if telem_type_field in ("batteryLevel", "voltage", "channelUtilization", "airUtilTx", "uptimeSeconds"):
            telem_type = TelemetryType.DEVICE
        elif telem_type_field in ("temperature", "relativeHumidity", "barometricPressure", "humidity", "pressure"):
            telem_type = TelemetryType.ENVIRONMENT
        elif telem_type_field in ("snr_local", "snr_remote", "rssi"):
            telem_type = TelemetryType.DEVICE  # Signal metrics go with device
        elif telem_type_field in ("latitude", "longitude", "altitude", "estimated_latitude", "estimated_longitude"):
            telem_type = TelemetryType.POSITION
        else:
            # Check old nested format
            telem_type_str = telem_data.get("type", "device").lower()
            try:
                telem_type = TelemetryType(telem_type_str)
            except ValueError:
                telem_type = TelemetryType.DEVICE

        # Handle MeshMonitor flat format
        if telem_type_field and value is not None:
            # Get timestamp from MeshMonitor data
            timestamp_ms = telem_data.get("timestamp") or telem_data.get("createdAt")
            received_at = datetime.now(timezone.utc)
            if timestamp_ms:
                received_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

            # Use metric_name for deduplication (the telemetryType field)
            metric_name = telem_type_field

            # Build values dict for the insert
            values = {
                "id": str(uuid4()),
                "source_id": self.source.id,
                "node_num": node_num,
                "metric_name": metric_name,
                "telemetry_type": telem_type,
                "received_at": received_at,
                "battery_level": int(value) if telem_type_field == "batteryLevel" else None,
                "voltage": float(value) if telem_type_field == "voltage" else None,
                "channel_utilization": float(value) if telem_type_field == "channelUtilization" else None,
                "air_util_tx": float(value) if telem_type_field == "airUtilTx" else None,
                "uptime_seconds": int(value) if telem_type_field == "uptimeSeconds" else None,
                "temperature": float(value) if telem_type_field == "temperature" else None,
                "relative_humidity": float(value) if telem_type_field in ("relativeHumidity", "humidity") else None,
                "barometric_pressure": float(value) if telem_type_field in ("barometricPressure", "pressure") else None,
                "snr_local": float(value) if telem_type_field == "snr_local" else None,
                "snr_remote": float(value) if telem_type_field == "snr_remote" else None,
                "rssi": float(value) if telem_type_field == "rssi" else None,
                "latitude": float(value) if telem_type_field in ("latitude", "estimated_latitude") else None,
                "longitude": float(value) if telem_type_field in ("longitude", "estimated_longitude") else None,
                "altitude": int(value) if telem_type_field == "altitude" else None,
                # Always store the raw value for any metric type
                "raw_value": float(value) if value is not None else None,
            }

            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
            stmt = pg_insert(Telemetry).values(**values).on_conflict_do_nothing(
                index_elements=["source_id", "node_num", "received_at", "metric_name"]
            )
            result = await db.execute(stmt)
            return result.rowcount > 0
        else:
            # Handle old nested format (deviceMetrics, environmentMetrics)
            # For this format, insert each metric as a separate record
            device_metrics = telem_data.get("deviceMetrics", {}) or {}
            env_metrics = telem_data.get("environmentMetrics", {}) or {}

            if not device_metrics and not env_metrics:
                return False

            inserted = False
            received_at = datetime.now(timezone.utc)

            # Insert device metrics one by one
            metric_mapping = [
                ("batteryLevel", "battery_level", device_metrics.get("batteryLevel")),
                ("voltage", "voltage", device_metrics.get("voltage")),
                ("channelUtilization", "channel_utilization", device_metrics.get("channelUtilization")),
                ("airUtilTx", "air_util_tx", device_metrics.get("airUtilTx")),
                ("uptimeSeconds", "uptime_seconds", device_metrics.get("uptimeSeconds")),
                ("temperature", "temperature", env_metrics.get("temperature")),
                ("relativeHumidity", "relative_humidity", env_metrics.get("relativeHumidity")),
                ("barometricPressure", "barometric_pressure", env_metrics.get("barometricPressure")),
            ]

            for metric_name, column_name, metric_value in metric_mapping:
                if metric_value is not None:
                    values = {
                        "id": str(uuid4()),
                        "source_id": self.source.id,
                        "node_num": node_num,
                        "metric_name": metric_name,
                        "telemetry_type": telem_type,
                        "received_at": received_at,
                        column_name: metric_value,
                    }
                    stmt = pg_insert(Telemetry).values(**values).on_conflict_do_nothing(
                        index_elements=["source_id", "node_num", "received_at", "metric_name"]
                    )
                    result = await db.execute(stmt)
                    if result.rowcount > 0:
                        inserted = True

            return inserted

    async def _collect_traceroutes(
        self, client: httpx.AsyncClient, headers: dict
    ) -> None:
        """Collect traceroutes from the API."""
        try:
            response = await client.get(
                f"{self.source.url}/api/v1/traceroutes",
                headers=headers,
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

    async def _insert_traceroute(self, db, route_data: dict) -> None:
        """Insert a traceroute."""
        from_node = route_data.get("fromNodeNum") or route_data.get("from")
        to_node = route_data.get("toNodeNum") or route_data.get("to")

        if not from_node or not to_node:
            return

        route = self._parse_array_field(route_data.get("route"))
        route_back = self._parse_array_field(route_data.get("routeBack"))
        snr_towards = self._parse_array_field(route_data.get("snrTowards"))
        snr_back = self._parse_array_field(route_data.get("snrBack"))

        traceroute = Traceroute(
            source_id=self.source.id,
            from_node_num=from_node,
            to_node_num=to_node,
            route=route or [],
            route_back=route_back,
            snr_towards=snr_towards,
            snr_back=snr_back,
        )
        db.add(traceroute)

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

        total_collected = 0
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                for batch_num in range(max_batches):
                    if not self._running:
                        logger.info(f"Historical collection stopped for {self.source.name}")
                        self.collection_status.status = "complete"
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

            logger.info(
                f"Historical data collection complete for {self.source.name}: "
                f"{total_collected} telemetry records"
            )

        except Exception as e:
            logger.error(f"Historical collection error for {self.source.name}: {e}")
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)

    async def _get_telemetry_count(
        self, client: httpx.AsyncClient, headers: dict
    ) -> int | None:
        """Get total telemetry count from the API.

        Returns the total count or None if the endpoint is not available.
        """
        try:
            response = await client.get(
                f"{self.source.url}/api/v1/telemetry/count",
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "count" in data:
                    return data["count"]
            return None
        except Exception as e:
            logger.debug(f"Could not get telemetry count: {e}")
            return None

    async def sync_all_data(
        self, batch_size: int = 500, delay_seconds: float = 5.0
    ) -> None:
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
                    self.collection_status.max_batches = (total_count + batch_size - 1) // batch_size
                    logger.info(
                        f"Sync will process ~{total_count} records in "
                        f"~{self.collection_status.max_batches} batches"
                    )

                while self._running:
                    batch_num += 1
                    self.collection_status.current_batch = batch_num

                    # Fetch batch
                    params = {"limit": batch_size, "offset": offset}
                    response = await client.get(
                        f"{self.source.url}/api/v1/telemetry",
                        headers=headers,
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
                            inserted = await self._insert_telemetry(
                                db, telem, skip_duplicates=True
                            )
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
            self.collection_status.max_batches = batch_num
            logger.info(
                f"Full sync complete for {self.source.name}: "
                f"fetched {total_fetched}, inserted {total_inserted} new records"
            )

        except Exception as e:
            logger.error(f"Sync error for {self.source.name}: {e}")
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)

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

            response = await client.get(
                f"{self.source.url}/api/v1/telemetry",
                headers=headers,
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
            encoded_node_id = quote(node_id, safe='')
            response = await client.get(
                f"{self.source.url}/api/v1/telemetry/{encoded_node_id}",
                headers=headers,
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
        cutoff_ms = int(
            (datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp() * 1000
        )

        logger.info(
            f"Collecting historical telemetry for node {node_id} "
            f"(up to {days_back} days back)"
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
                            logger.debug(
                                f"Reached cutoff date for node {node_id}"
                            )
                            break

                    logger.debug(
                        f"Node {node_id} batch {batch_num + 1}: "
                        f"collected {count} records (total: {total_collected})"
                    )

                    # Delay before next batch
                    if batch_num < max_batches - 1 and count == batch_size:
                        await asyncio.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Error collecting historical telemetry for {node_id}: {e}")

        logger.info(
            f"Historical collection for node {node_id} complete: "
            f"{total_collected} records"
        )
        return total_collected

    async def collect_all_nodes_historical_telemetry(
        self,
        days_back: int = 7,
        batch_size: int = 500,
        delay_seconds: float = 2.0,
    ) -> int:
        """Collect historical telemetry for all known nodes.

        Fetches the list of nodes from the nodes endpoint, then collects
        historical telemetry for each one using the per-node API.

        Args:
            days_back: How many days of history to fetch per node
            batch_size: Records per batch
            delay_seconds: Delay between batches

        Returns:
            Total number of records collected across all nodes
        """
        if not self.source.url:
            return 0

        logger.info(
            f"Starting historical telemetry collection for all nodes from {self.source.name}"
        )

        # Initialize collection status
        self.collection_status.status = "collecting"
        self.collection_status.current_batch = 0
        self.collection_status.max_batches = 0
        self.collection_status.total_collected = 0
        self.collection_status.last_error = None

        total_collected = 0

        try:
            nodes_url = f"{self.source.url}/api/v1/nodes"
            logger.debug(f"Fetching nodes from: {nodes_url}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = self._get_headers()

                # First, get list of nodes
                response = await client.get(
                    nodes_url,
                    headers=headers,
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

                # Set max_batches to number of nodes for progress tracking
                self.collection_status.max_batches = len(nodes)

                # Collect historical telemetry for each node
                for i, node in enumerate(nodes):
                    node_id = node.get("nodeId") or node.get("id")
                    if not node_id:
                        continue

                    # Update progress (current node being processed)
                    self.collection_status.current_batch = i + 1

                    count = await self.collect_node_historical_telemetry(
                        node_id=node_id,
                        days_back=days_back,
                        batch_size=batch_size,
                        delay_seconds=delay_seconds,
                    )
                    total_collected += count
                    self.collection_status.total_collected = total_collected

                    # Small delay between nodes to be nice to the API
                    if i < len(nodes) - 1:
                        await asyncio.sleep(1.0)

            self.collection_status.status = "complete"

        except Exception as e:
            logger.error(f"Error in all-nodes historical collection: {e}", exc_info=True)
            self.collection_status.status = "error"
            self.collection_status.last_error = str(e)

        logger.info(
            f"All-nodes historical collection complete: {total_collected} total records"
        )
        return total_collected

    async def start(self, collect_history: bool = False) -> None:
        """Start periodic collection.

        Args:
            collect_history: If True, fetch historical data in the background
                           while also starting regular polling.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Started MeshMonitor collector: {self.source.name}")

        # Start historical collection in background if requested
        if collect_history:
            self._historical_task = asyncio.create_task(self._collect_historical_background())

    async def _collect_historical_background(self) -> None:
        """Background task for historical data collection using per-node API."""
        try:
            # Wait a moment for the source to be fully committed and first poll to complete
            await asyncio.sleep(10)
            # Collect historical data for all nodes using per-node API
            await self.collect_all_nodes_historical_telemetry(
                days_back=7,
                batch_size=500,
                delay_seconds=2.0,
            )
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
        logger.info(f"Stopped MeshMonitor collector: {self.source.name}")
