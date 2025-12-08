# MeshManager

Management and oversight application for aggregating data from multiple MeshMonitor instances and Meshtastic MQTT servers.

## Features

- Aggregate data from multiple MeshMonitor instances and MQTT brokers
- Interactive Leaflet map showing all nodes across all sources
- Prometheus-compatible metrics endpoint for monitoring
- OIDC authentication for admin access
- Configurable data retention policies
- Catppuccin-themed dark UI

## Quick Start

### Development (Single Command)

Run the entire stack with a single command:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Access the application at http://localhost:8080

This starts:
- PostgreSQL database
- FastAPI backend
- React frontend
- Nginx reverse proxy

To view logs:
```bash
docker compose -f docker-compose.dev.yml logs -f
```

To stop:
```bash
docker compose -f docker-compose.dev.yml down
```

### Production

1. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. Start the production environment:
   ```bash
   docker compose up -d
   ```

3. Access the application at http://localhost:8080

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | `meshmanager` |
| `SESSION_SECRET` | Session signing secret (required) | - |
| `OIDC_ISSUER` | OIDC provider URL | - |
| `OIDC_CLIENT_ID` | OIDC client ID | - |
| `OIDC_CLIENT_SECRET` | OIDC client secret | - |
| `OIDC_REDIRECT_URI` | OIDC callback URL | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HTTP_PORT` | HTTP port | `8080` |

### OIDC Authentication

To enable OIDC authentication:

1. Configure your OIDC provider (Keycloak, Auth0, etc.)
2. Set the OIDC environment variables
3. The first user to log in becomes an admin

Without OIDC configured, the application runs in read-only mode.

## API Endpoints

### Public

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /api/sources` - List sources (names only)
- `GET /api/nodes` - List all nodes

### Admin (requires authentication)

- `GET /api/admin/sources` - List sources with full config
- `POST /api/admin/sources/meshmonitor` - Add MeshMonitor source
- `POST /api/admin/sources/mqtt` - Add MQTT source
- `DELETE /api/admin/sources/{id}` - Remove source

## Prometheus Metrics

The `/metrics` endpoint exposes:

- `meshmanager_node_battery_level` - Node battery levels
- `meshmanager_node_voltage` - Node voltages
- `meshmanager_node_last_heard_timestamp` - Last heard timestamps
- `meshmanager_active_nodes_total` - Active nodes per source
- `meshmanager_messages_last_hour` - Messages in last hour
- `meshmanager_source_healthy` - Source health status
- `meshmanager_db_rows_total` - Database row counts

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MeshManager                                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   React     │  │   FastAPI   │  │  PostgreSQL │                  │
│  │  Frontend   │◄─┤   Backend   │◄─┤   Database  │                  │
│  └─────────────┘  └──────┬──────┘  └─────────────┘                  │
│                          │                                           │
│         ┌────────────────┼────────────────┐                         │
│         ▼                ▼                ▼                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ MeshMonitor │  │ MeshMonitor │  │    MQTT     │                  │
│  │  Collector  │  │  Collector  │  │  Collector  │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run lint
```

## License

MIT
