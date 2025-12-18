# Multi-Source Support

MeshManager is designed to aggregate data from multiple sources, giving you a unified view of your entire mesh network infrastructure.

## Supported Source Types

### MeshMonitor

Connect to any [MeshMonitor](https://meshmonitor.org) instance to pull:
- Node information
- Telemetry data
- Messages
- Traceroutes

MeshManager polls MeshMonitor's API periodically and supports:
- Historical data backfill on first connection
- Catchup collection after restarts
- Per-node historical telemetry sync

### MQTT

Connect directly to Meshtastic MQTT brokers:
- Subscribe to topic patterns (e.g., `msh/US/#`)
- Supports authentication
- Real-time data ingestion

## Data Deduplication

When the same node appears in multiple sources:

1. **Node List** - Shows the record with the most recent `last_heard` timestamp
2. **Node Details** - Displays source history table showing all sources
3. **Telemetry** - Aggregates data from all sources for charting

## Managing Sources

### Adding a Source

1. Go to **Admin** panel
2. Click **Add Source**
3. Select source type (MeshMonitor or MQTT)
4. Enter connection details
5. Save

### Source Status

Each source shows:
- **Enabled/Disabled** status
- **Healthy/Unhealthy** indicator
- **Last Poll** timestamp
- **Error** message (if any)

### Source Actions

- **Edit** - Modify source configuration
- **Sync** - Trigger immediate data collection
- **Delete** - Remove source and optionally its data

## Filtering by Source

Throughout the application, you can filter views by source:

- Dashboard node list
- Telemetry charts
- Analysis reports

This helps when troubleshooting or when you want to focus on a specific part of your network.

## Best Practices

1. **Name sources descriptively** - Include location or purpose
2. **Monitor source health** - Check for connection errors
3. **Stagger collection** - Avoid overwhelming a single MeshMonitor
4. **Use MQTT for real-time** - MeshMonitor polling has latency
