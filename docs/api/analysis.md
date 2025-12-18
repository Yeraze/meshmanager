# Analysis API

Endpoints for solar analysis and forecasting.

## Solar Forecast

```http
GET /api/ui/analysis/solar-forecast
```

Returns solar production forecast and node battery analysis.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | integer | 7 | Days of historical data for comparison |

### Response

```json
{
  "forecast": {
    "date": "2024-01-15",
    "watt_hours_today": 4123,
    "watt_hours_period": 28750,
    "average_daily": 4107,
    "percentage_of_average": 100.4
  },
  "hourly_forecast": [
    {
      "hour": 6,
      "watts": 0
    },
    {
      "hour": 7,
      "watts": 125
    },
    {
      "hour": 8,
      "watts": 340
    }
  ],
  "nodes_at_risk": [
    {
      "node_num": 1234567890,
      "long_name": "AlephNull",
      "current_battery": 65,
      "min_simulated": 6,
      "critical": true
    }
  ],
  "config": {
    "latitude": 25.7617,
    "longitude": -80.1918,
    "declination": 25,
    "azimuth": 180,
    "kwp": 0.5
  }
}
```

### Response Fields

#### forecast

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Forecast date |
| `watt_hours_today` | integer | Predicted production today (Wh) |
| `watt_hours_period` | integer | Total production over lookback period |
| `average_daily` | integer | Average daily production (Wh) |
| `percentage_of_average` | number | Today vs average (%) |

#### hourly_forecast

Array of hourly predictions:

| Field | Type | Description |
|-------|------|-------------|
| `hour` | integer | Hour of day (0-23) |
| `watts` | integer | Predicted watts for that hour |

#### nodes_at_risk

Nodes predicted to have battery issues:

| Field | Type | Description |
|-------|------|-------------|
| `node_num` | integer | Node numeric ID |
| `long_name` | string | Node name |
| `current_battery` | integer | Current battery level (%) |
| `min_simulated` | integer | Minimum predicted battery (%) |
| `critical` | boolean | Whether below critical threshold |

## Solar Nodes

```http
GET /api/ui/analysis/solar-nodes
```

Returns nodes configured for solar monitoring.

### Response

```json
{
  "nodes": [
    {
      "node_num": 1234567890,
      "long_name": "AlephNull",
      "enabled": true,
      "battery_level": 65
    }
  ]
}
```

## Solar Configuration

```http
GET /api/ui/solar
```

Returns solar panel configuration.

### Response

```json
{
  "latitude": 25.7617,
  "longitude": -80.1918,
  "declination": 25,
  "azimuth": 180,
  "kwp": 0.5
}
```

## Solar Schedule Settings

### Get Settings

```http
GET /api/ui/settings/solar-schedule
```

Returns notification schedule configuration.

### Response

```json
{
  "enabled": true,
  "times": ["07:00", "18:00"],
  "apprise_urls": ["discord://webhook_id/token"],
  "lookback_days": 7,
  "solar_nodes": [1234567890, 9876543210]
}
```

### Update Settings

```http
PUT /api/ui/settings/solar-schedule
```

Updates notification schedule configuration.

### Request Body

```json
{
  "enabled": true,
  "times": ["07:00", "18:00"],
  "apprise_urls": ["discord://webhook_id/token"],
  "lookback_days": 7,
  "solar_nodes": [1234567890, 9876543210]
}
```

### Test Notification

```http
POST /api/ui/settings/solar-schedule/test
```

Sends a test notification using current configuration.

### Response

```json
{
  "success": true,
  "message": "Test notification sent"
}
```

Or on failure:

```json
{
  "success": false,
  "message": "Failed to send notification",
  "error": "Invalid Apprise URL"
}
```

## Traceroutes

```http
GET /api/ui/traceroutes
```

Returns traceroute data showing mesh network paths.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours` | integer | 24 | Hours of history |
| `source_id` | integer | | Filter by source |

### Response

```json
[
  {
    "id": 1,
    "from_node": 1234567890,
    "to_node": 9876543210,
    "route": [1234567890, 5555555555, 9876543210],
    "snr": [8.5, 6.2],
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

## Example: Generate Daily Report

```bash
# Get solar forecast
forecast=$(curl -s "http://localhost:8080/api/ui/analysis/solar-forecast?lookback_days=7")

# Extract key metrics
today_wh=$(echo $forecast | jq '.forecast.watt_hours_today')
avg_wh=$(echo $forecast | jq '.forecast.average_daily')
at_risk=$(echo $forecast | jq '.nodes_at_risk | length')

echo "Today: ${today_wh}Wh (avg: ${avg_wh}Wh)"
echo "Nodes at risk: ${at_risk}"
```
