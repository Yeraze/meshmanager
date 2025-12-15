"""Collector manager for managing all data collectors."""

import asyncio
import logging

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.collectors.meshmonitor import MeshMonitorCollector
from app.collectors.mqtt import MqttCollector
from app.database import async_session_maker
from app.models import Source
from app.models.source import SourceType

logger = logging.getLogger(__name__)


class CollectorManager:
    """Manages all data collectors."""

    def __init__(self):
        self._collectors: dict[str, BaseCollector] = {}
        self._running = False

    async def start(self) -> None:
        """Start all enabled collectors."""
        if self._running:
            return

        self._running = True
        await self._load_collectors()
        logger.info(f"Started {len(self._collectors)} collectors")

    async def _load_collectors(self) -> None:
        """Load and start collectors for all enabled sources."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Source).where(Source.enabled == True)  # noqa: E712
            )
            sources = result.scalars().all()

            for source in sources:
                await self._start_collector(source)

    async def _start_collector(self, source: Source, collect_history: bool = False) -> None:
        """Start a collector for a source.

        Args:
            source: The source to start a collector for
            collect_history: If True, collect historical data in the background
        """
        if source.id in self._collectors:
            return

        if source.type == SourceType.MESHMONITOR:
            collector = MeshMonitorCollector(source)
        elif source.type == SourceType.MQTT:
            collector = MqttCollector(source)
        else:
            logger.warning(f"Unknown source type: {source.type}")
            return

        self._collectors[source.id] = collector

        # MeshMonitor supports historical collection
        if source.type == SourceType.MESHMONITOR and collect_history:
            await collector.start(collect_history=True)
        else:
            await collector.start()

    async def stop(self) -> None:
        """Stop all collectors."""
        self._running = False

        # Stop all collectors concurrently
        await asyncio.gather(
            *[collector.stop() for collector in self._collectors.values()],
            return_exceptions=True,
        )

        self._collectors.clear()
        logger.info("Stopped all collectors")

    async def add_source(self, source: Source) -> None:
        """Add and start a collector for a new source.

        For new sources, historical data collection is triggered automatically.
        """
        if source.enabled:
            # New sources should collect historical data
            await self._start_collector(source, collect_history=True)

    async def remove_source(self, source_id: str) -> None:
        """Stop and remove a collector."""
        collector = self._collectors.pop(source_id, None)
        if collector:
            await collector.stop()

    async def update_source(self, source: Source) -> None:
        """Update a collector when source config changes."""
        # Stop existing collector
        await self.remove_source(source.id)

        # Start new one if enabled
        if source.enabled:
            await self._start_collector(source)

    def get_collector(self, source_id: str) -> BaseCollector | None:
        """Get a collector by source ID."""
        return self._collectors.get(source_id)

    def get_collection_status(self, source_id: str) -> dict | None:
        """Get collection status for a source.

        Returns status dict or None if source not found or doesn't support status.
        """
        collector = self._collectors.get(source_id)
        if not collector:
            return None

        if hasattr(collector, 'collection_status'):
            return collector.collection_status.to_dict()
        return None

    def get_all_collection_statuses(self) -> dict[str, dict]:
        """Get collection status for all sources."""
        statuses = {}
        for source_id, collector in self._collectors.items():
            if hasattr(collector, 'collection_status'):
                statuses[source_id] = collector.collection_status.to_dict()
        return statuses

    async def trigger_sync(self, source_id: str) -> bool:
        """Trigger full data sync for a source using per-node historical collection.

        Returns True if sync was started, False if source not found.
        """
        collector = self._collectors.get(source_id)
        if not collector:
            return False

        # Use per-node historical collection for comprehensive sync
        if hasattr(collector, 'collect_all_nodes_historical_telemetry'):
            import asyncio
            # Use the source's configured historical_days_back value
            days_back = collector.source.historical_days_back if hasattr(collector, 'source') and collector.source else 1
            asyncio.create_task(collector.collect_all_nodes_historical_telemetry(
                days_back=days_back,  # Use source configuration
                batch_size=500,
                delay_seconds=0.3,  # Reduced delay for faster collection
                max_concurrent=10,  # Process 10 nodes in parallel
            ))
            logger.info(f"Triggered per-node historical sync for source {source_id} (days_back={days_back})")
            return True
        return False

    async def trigger_historical_collection(self, source_id: str) -> bool:
        """Trigger historical data collection for an existing source.

        Returns True if collection was started, False if source not found.
        """
        collector = self._collectors.get(source_id)
        if not collector:
            return False

        # Only MeshMonitor collectors support historical collection
        if hasattr(collector, 'collect_historical_batch'):
            import asyncio
            asyncio.create_task(collector.collect_historical_batch(
                batch_size=500,
                delay_seconds=10.0,
                max_batches=50,
            ))
            logger.info(f"Triggered historical collection for source {source_id}")
            return True
        return False

    async def trigger_historical_collection_all(self) -> int:
        """Trigger historical collection for all MeshMonitor sources.

        Returns the number of sources that started collection.
        """
        count = 0
        for source_id, collector in self._collectors.items():
            if hasattr(collector, 'collect_historical_batch'):
                import asyncio
                asyncio.create_task(collector.collect_historical_batch(
                    batch_size=500,
                    delay_seconds=10.0,
                    max_batches=50,
                ))
                logger.info(f"Triggered historical collection for source {source_id}")
                count += 1
        return count

    async def trigger_per_node_historical_collection(
        self, source_id: str, days_back: int = 7
    ) -> bool:
        """Trigger per-node historical telemetry collection for a source.

        Uses the new per-node API endpoint (if available) to fetch historical
        telemetry for all nodes.

        Returns True if collection was started, False if source not found.
        """
        collector = self._collectors.get(source_id)
        if not collector:
            return False

        # Only MeshMonitor collectors support per-node historical collection
        if hasattr(collector, 'collect_all_nodes_historical_telemetry'):
            import asyncio
            asyncio.create_task(collector.collect_all_nodes_historical_telemetry(
                days_back=days_back,
                batch_size=500,
                delay_seconds=0.3,  # Reduced delay for faster collection
                max_concurrent=10,  # Process 10 nodes in parallel
            ))
            logger.info(
                f"Triggered per-node historical collection for source {source_id} "
                f"({days_back} days back)"
            )
            return True
        return False

    async def trigger_per_node_historical_collection_all(
        self, days_back: int = 7
    ) -> int:
        """Trigger per-node historical collection for all MeshMonitor sources.

        Returns the number of sources that started collection.
        """
        count = 0
        for source_id, collector in self._collectors.items():
            if hasattr(collector, 'collect_all_nodes_historical_telemetry'):
                import asyncio
                asyncio.create_task(collector.collect_all_nodes_historical_telemetry(
                    days_back=days_back,
                    batch_size=500,
                    delay_seconds=0.3,  # Reduced delay for faster collection
                    max_concurrent=10,  # Process 10 nodes in parallel
                ))
                logger.info(
                    f"Triggered per-node historical collection for source {source_id}"
                )
                count += 1
        return count


# Global collector manager instance
collector_manager = CollectorManager()
