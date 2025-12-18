# Nodes API

Endpoints for retrieving node information.

## List All Nodes

```http
GET /api/ui/nodes
```

Returns a summary list of all nodes across all sources.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | integer | Filter by source ID |
| `active_only` | boolean | Only return recently active nodes |
| `active_hours` | integer | Hours to consider "active" (default: 24) |

### Response

```json
[
  {
    "node_num": 1234567890,
    "node_id": "!abcd1234",
    "short_name": "TEST",
    "long_name": "Test Node",
    "hardware_model": 43,
    "hardware_name": "Heltec v3",
    "role": "ROUTER",
    "last_heard": "2024-01-15T10:30:00Z",
    "is_online": true,
    "snr": 8.5,
    "rssi": -95,
    "hops_away": 1,
    "latitude": 25.7617,
    "longitude": -80.1918
  }
]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `node_num` | integer | Numeric node identifier |
| `node_id` | string | Hexadecimal node ID (e.g., `!abcd1234`) |
| `short_name` | string | 4-character short name |
| `long_name` | string | Full node name |
| `hardware_model` | integer | Hardware model code |
| `hardware_name` | string | Human-readable hardware name |
| `role` | string | Node role (CLIENT, ROUTER, etc.) |
| `last_heard` | string | ISO 8601 timestamp |
| `is_online` | boolean | Whether node is considered online |
| `snr` | number | Signal-to-noise ratio (dB) |
| `rssi` | number | Received signal strength (dBm) |
| `hops_away` | integer | Number of hops from reporting node |
| `latitude` | number | GPS latitude (if available) |
| `longitude` | number | GPS longitude (if available) |

## Get Node by ID

```http
GET /api/ui/nodes/{node_id}
```

Returns detailed information for a specific node.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_id` | string | Hexadecimal node ID (e.g., `!abcd1234`) |

### Response

```json
{
  "node_num": 1234567890,
  "node_id": "!abcd1234",
  "short_name": "TEST",
  "long_name": "Test Node",
  "hardware_model": 43,
  "hardware_name": "Heltec v3",
  "role": "ROUTER",
  "last_heard": "2024-01-15T10:30:00Z",
  "is_online": true,
  "snr": 8.5,
  "rssi": -95,
  "hops_away": 1,
  "latitude": 25.7617,
  "longitude": -80.1918,
  "source_records": [
    {
      "source_id": 1,
      "source_name": "Home MeshMonitor",
      "last_heard": "2024-01-15T10:30:00Z"
    },
    {
      "source_id": 2,
      "source_name": "Public MQTT",
      "last_heard": "2024-01-15T09:15:00Z"
    }
  ]
}
```

## Get Node by Number

```http
GET /api/ui/nodes/by-node-num/{node_num}
```

Alternative endpoint to look up a node by its numeric ID.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_num` | integer | Numeric node identifier |

## List Node Roles

```http
GET /api/ui/nodes/roles
```

Returns a list of all node roles present in the database.

### Response

```json
["CLIENT", "ROUTER", "TRACKER", "CLIENT_MUTE"]
```

## Position History

```http
GET /api/ui/position-history
```

Returns GPS position history for nodes.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_num` | integer | Filter by specific node |
| `hours` | integer | Hours of history (default: 24) |
| `source_id` | integer | Filter by source |

### Response

```json
[
  {
    "node_num": 1234567890,
    "latitude": 25.7617,
    "longitude": -80.1918,
    "altitude": 10,
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

## Hardware Models

The `hardware_model` field maps to these common values:

| Code | Name |
|------|------|
| 1 | TLORA_V2 |
| 7 | TLORA_V1 |
| 9 | RAK4631 |
| 25 | TBEAM |
| 39 | T_DECK |
| 43 | HELTEC_V3 |
| 44 | HELTEC_WSL_V3 |
| 47 | STATION_G2 |
| 255 | UNSET |

See the MeshManager source code for the complete mapping.
