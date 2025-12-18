# Sources API

Endpoints for managing data sources.

## List Sources

```http
GET /api/sources
```

Returns all configured data sources.

### Response

```json
[
  {
    "id": 1,
    "name": "Home MeshMonitor",
    "source_type": "meshmonitor",
    "enabled": true,
    "healthy": true,
    "last_poll": "2024-01-15T10:30:00Z",
    "last_error": null,
    "url": "http://192.168.1.100:5000"
  },
  {
    "id": 2,
    "name": "Public MQTT",
    "source_type": "mqtt",
    "enabled": true,
    "healthy": true,
    "last_poll": "2024-01-15T10:30:00Z",
    "last_error": null,
    "host": "mqtt.meshtastic.org",
    "port": 1883,
    "topic": "msh/US/#"
  }
]
```

## Get Source

```http
GET /api/sources/{source_id}
```

Returns details for a specific source.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | integer | Source ID |

## Create MeshMonitor Source

```http
POST /api/sources/meshmonitor
```

Creates a new MeshMonitor data source.

### Request Body

```json
{
  "name": "Home MeshMonitor",
  "url": "http://192.168.1.100:5000",
  "enabled": true
}
```

### Response

Returns the created source with its assigned ID.

## Create MQTT Source

```http
POST /api/sources/mqtt
```

Creates a new MQTT data source.

### Request Body

```json
{
  "name": "Public MQTT",
  "host": "mqtt.meshtastic.org",
  "port": 1883,
  "topic": "msh/US/#",
  "username": null,
  "password": null,
  "use_tls": false,
  "enabled": true
}
```

## Update MeshMonitor Source

```http
PUT /api/sources/meshmonitor/{source_id}
```

Updates an existing MeshMonitor source.

### Request Body

```json
{
  "name": "Updated Name",
  "url": "http://192.168.1.101:5000",
  "enabled": true
}
```

## Update MQTT Source

```http
PUT /api/sources/mqtt/{source_id}
```

Updates an existing MQTT source.

### Request Body

```json
{
  "name": "Updated Name",
  "host": "mqtt.example.com",
  "port": 8883,
  "topic": "msh/#",
  "username": "user",
  "password": "pass",
  "use_tls": true,
  "enabled": true
}
```

## Delete Source

```http
DELETE /api/sources/{source_id}
```

Deletes a data source.

### Response

Returns `204 No Content` on success.

## Test Source Connection

```http
POST /api/sources/{source_id}/test
```

Tests the connection to a data source without collecting data.

### Response

```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "nodes_available": 150,
    "version": "1.0.0"
  }
}
```

Or on failure:

```json
{
  "success": false,
  "message": "Connection failed",
  "error": "Connection refused"
}
```

## Trigger Sync

```http
POST /api/sources/{source_id}/sync
```

Triggers an immediate data collection from the source.

### Response

```json
{
  "success": true,
  "message": "Sync started"
}
```

## Collect History

```http
POST /api/sources/{source_id}/collect-history
```

Triggers historical data collection from a MeshMonitor source.

### Request Body

```json
{
  "hours": 24
}
```

### Response

```json
{
  "success": true,
  "message": "History collection started",
  "hours": 24
}
```

## Collect Node History

```http
POST /api/sources/{source_id}/collect-node-history
```

Collects detailed telemetry history for specific nodes.

### Request Body

```json
{
  "node_nums": [1234567890, 9876543210],
  "hours": 168
}
```

## Collection Status

```http
GET /api/ui/sources/collection-status
```

Returns the status of all data collection tasks.

### Response

```json
{
  "sources": [
    {
      "id": 1,
      "name": "Home MeshMonitor",
      "collecting": false,
      "last_poll": "2024-01-15T10:30:00Z",
      "next_poll": "2024-01-15T10:35:00Z"
    }
  ]
}
```
