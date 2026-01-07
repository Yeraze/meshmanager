# Data Sources

MeshManager aggregates data from multiple sources. This page explains how to configure each source type.

## MeshMonitor Sources

[MeshMonitor](https://meshmonitor.org) is a Meshtastic monitoring tool. MeshManager can poll its API to collect node and telemetry data.

### Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Friendly identifier for this source |
| URL | Yes | Base URL of the MeshMonitor instance |
| Enabled | Yes | Whether to collect data from this source |

### Example

```
Name: Home MeshMonitor
URL: http://192.168.1.100:5000
Enabled: true
```

### Data Collected

- **Nodes** - Node information, hardware, role, last heard
- **Telemetry** - Battery, voltage, signal quality, environment sensors
- **Messages** - Text messages sent through the mesh
- **Traceroutes** - Network path information
- **Position History** - GPS coordinates over time

### Collection Behavior

1. **Initial Sync** - On first connection, collects historical data based on `CATCHUP_HOURS`
2. **Periodic Polling** - Polls every `COLLECTION_INTERVAL` seconds
3. **Per-Node History** - Can fetch detailed telemetry history for specific nodes

## MQTT Sources

Connect directly to Meshtastic MQTT brokers for real-time data.

### Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Friendly identifier for this source |
| Host | Yes | MQTT broker hostname |
| Port | Yes | MQTT port (typically 1883 or 8883 for TLS) |
| Topic | Yes | Topic pattern to subscribe (e.g., `msh/US/#`) |
| Username | No | Authentication username |
| Password | No | Authentication password |
| Use TLS | No | Enable TLS encryption |
| Enabled | Yes | Whether to collect data from this source |

### Example

```
Name: Public US MQTT
Host: mqtt.meshtastic.org
Port: 1883
Topic: msh/US/#
Enabled: true
```

### Topic Patterns

Meshtastic uses a hierarchical topic structure:

- `msh/US/#` - All US traffic
- `msh/US/BayArea/#` - Bay Area regional traffic
- `msh/2/e/#` - Encrypted channel traffic

## Managing Sources

### Adding a Source

1. Navigate to **Admin** panel
2. Click **Add Source**
3. Select source type (MeshMonitor or MQTT)
4. Fill in the configuration fields
5. Click **Save**

### Testing a Source

Before enabling a source, test the connection:

1. Click the **Test** button on the source card
2. Verify the connection succeeds
3. Check for any error messages

### Triggering Manual Sync

To immediately collect data from a source:

1. Click the **Sync** button on the source card
2. Wait for collection to complete
3. Check the **Last Poll** timestamp

### Collecting History

For MeshMonitor sources, you can fetch historical data:

1. Click **Collect History** on the source card
2. Select the time range
3. Wait for collection to complete

## Source Status

Each source displays status information:

| Indicator | Meaning |
|-----------|---------|
| **Enabled** (green) | Source is active and collecting |
| **Disabled** (gray) | Source is configured but not collecting |
| **Healthy** (green) | Last collection succeeded |
| **Unhealthy** (red) | Last collection failed |
| **Last Poll** | Timestamp of most recent collection |
| **Error** | Description of any errors |

## Troubleshooting

### MeshMonitor Connection Failed

- Verify the URL is correct and accessible
- Check if MeshMonitor is running
- Ensure no firewall blocks the connection

### MQTT Connection Failed

- Verify hostname and port
- Check credentials if authentication is required
- Ensure the topic pattern is valid
- Try enabling/disabling TLS as appropriate

### No Data Appearing

- Confirm the source is enabled
- Check the source health status
- Review application logs for errors
- Verify the MeshMonitor or MQTT broker has data

## Configuration Backup

MeshManager allows you to export and import your configuration for backup or migration purposes.

### Exporting Configuration

1. Navigate to **Settings** > **Display** tab
2. Find the **Configuration Backup** section
3. Check **Include credentials** if you want API tokens and passwords included
4. Click **Export Configuration**
5. Save the downloaded JSON file

::: warning Credentials Security
When "Include credentials" is checked, the exported file contains sensitive data (API tokens, MQTT passwords). Store this file securely and do not share it publicly.
:::

### Importing Configuration

1. Navigate to **Settings** > **Display** tab
2. Find the **Configuration Backup** section
3. Optionally check **Merge with existing sources** to keep current sources
4. Click **Import Configuration**
5. Select your previously exported JSON file

### What's Included

The export includes:
- **Sources** - All configured data sources (MeshMonitor and MQTT)
- **Display Settings** - Active hours and online thresholds
- **Analysis Config** - Coverage, utilization, and solar analysis settings

### Import Behavior

| Option | Behavior |
|--------|----------|
| **Replace** (default) | Deletes all existing sources, imports new ones |
| **Merge** | Keeps existing sources, adds new ones (skips duplicates by name) |

### Credentials Handling

| Export Option | Import Result |
|---------------|---------------|
| **With credentials** | Sources imported enabled and functional |
| **Without credentials** | Sources imported disabled; re-enter credentials manually |
