# Telemetry API

Endpoints for retrieving node telemetry data.

## Get Latest Telemetry

```http
GET /api/ui/telemetry/{node_num}
```

Returns the most recent telemetry data for a node.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_num` | integer | Numeric node identifier |

### Response

```json
{
  "node_num": 1234567890,
  "battery_level": 85,
  "voltage": 4.1,
  "channel_utilization": 12.5,
  "air_util_tx": 3.2,
  "snr": 8.5,
  "rssi": -95,
  "temperature": 28.5,
  "relative_humidity": 65.0,
  "barometric_pressure": 1013.25,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Response Fields

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `battery_level` | integer | % | Battery percentage (0-100) |
| `voltage` | number | V | Battery voltage |
| `channel_utilization` | number | % | Channel airtime usage |
| `air_util_tx` | number | % | Transmit utilization |
| `snr` | number | dB | Signal-to-noise ratio |
| `rssi` | number | dBm | Received signal strength |
| `temperature` | number | °C | Device temperature |
| `relative_humidity` | number | % | Relative humidity |
| `barometric_pressure` | number | hPa | Barometric pressure |
| `timestamp` | string | | ISO 8601 timestamp |

## Get Telemetry History

```http
GET /api/ui/telemetry/{node_num}/history/{metric}
```

Returns historical values for a specific telemetry metric.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_num` | integer | Numeric node identifier |
| `metric` | string | Metric name (see below) |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours` | integer | 24 | Hours of history to return |
| `source_id` | integer | | Filter by source ID |

### Available Metrics

| Metric | Description |
|--------|-------------|
| `battery_level` | Battery percentage |
| `voltage` | Battery voltage |
| `channel_utilization` | Channel usage percentage |
| `air_util_tx` | Transmit utilization |
| `snr` | Signal-to-noise ratio |
| `rssi` | Received signal strength |
| `temperature` | Device temperature |
| `relative_humidity` | Humidity percentage |
| `barometric_pressure` | Air pressure |

### Response

```json
{
  "metric": "battery_level",
  "node_num": 1234567890,
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "value": 85
    },
    {
      "timestamp": "2024-01-15T09:00:00Z",
      "value": 87
    },
    {
      "timestamp": "2024-01-15T08:00:00Z",
      "value": 89
    }
  ]
}
```

## Time Ranges

Common time ranges for telemetry queries:

| Hours | Description |
|-------|-------------|
| 6 | Last 6 hours |
| 12 | Last 12 hours |
| 24 | Last 24 hours (default) |
| 48 | Last 2 days |
| 72 | Last 3 days |
| 168 | Last 7 days |

## Data Aggregation

When querying long time ranges, data points may be aggregated:

- **< 24 hours**: Raw data points
- **24-72 hours**: 15-minute averages
- **> 72 hours**: 1-hour averages

This ensures reasonable response sizes while maintaining data fidelity.

## Example: Fetch Battery History

```bash
curl "http://localhost:8080/api/ui/telemetry/1234567890/history/battery_level?hours=24"
```

## Example: Fetch All Metrics for a Node

```bash
# Get latest telemetry
curl "http://localhost:8080/api/ui/telemetry/1234567890"

# Get specific metric history
for metric in battery_level voltage snr rssi; do
  curl "http://localhost:8080/api/ui/telemetry/1234567890/history/${metric}?hours=24"
done
```
