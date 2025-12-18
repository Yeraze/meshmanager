# API Reference

MeshManager provides a REST API for programmatic access to mesh network data.

## Base URL

All API endpoints are prefixed with `/api`:

```
http://localhost:8080/api/
```

## Authentication

Currently, the API does not require authentication. Future versions may add API token support.

## Response Format

All responses are JSON. Successful responses typically return the requested data directly. Error responses include a `detail` field:

```json
{
  "detail": "Node not found"
}
```

## Endpoints Overview

### Nodes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/nodes` | List all nodes |
| GET | `/api/nodes/{id}` | Get node by ID |
| GET | `/api/nodes/by-node-num/{node_num}` | Get node by node number |
| GET | `/api/nodes/roles` | List unique node roles |

### Telemetry

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/telemetry/{node_num}` | Recent telemetry for a node |
| GET | `/api/telemetry/{node_num}/history/{metric}` | Historical data for specific metric |

### Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sources` | List all data sources |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/solar-nodes` | List identified solar nodes |
| GET | `/api/analysis/solar-forecast` | Solar forecast analysis |
| GET | `/api/solar` | Solar production data |

### Admin Endpoints

Admin endpoints require authentication when enabled:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/sources` | Create a new source |
| PUT | `/api/admin/sources/{id}` | Update a source |
| DELETE | `/api/admin/sources/{id}` | Delete a source |
| POST | `/api/admin/sources/{id}/sync` | Trigger data sync |

## Common Query Parameters

### Filtering Nodes

```
GET /api/nodes?source_id={uuid}&active_only=true&active_hours=24
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | UUID | Filter by source |
| `active_only` | boolean | Only show recently active nodes |
| `active_hours` | integer | Hours to consider "active" (1-8760) |

### Telemetry History

```
GET /api/telemetry/{node_num}/history/{metric}?hours=24
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours` | integer | Hours of history to fetch (1-168) |

### Solar Analysis

```
GET /api/analysis/solar-forecast?lookback_days=7
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `lookback_days` | integer | Days of history to analyze (1-90) |

## Detailed Endpoint Documentation

- [Nodes API](/api/nodes) - Node endpoints
- [Telemetry API](/api/telemetry) - Telemetry endpoints
- [Sources API](/api/sources) - Source management
- [Analysis API](/api/analysis) - Analysis and solar endpoints
