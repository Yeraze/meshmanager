<p align="center">
  <img src="docs/public/images/logo.png" alt="MeshManager Logo" width="200">
</p>

# MeshManager

[![Tests](https://github.com/Yeraze/meshmanager/actions/workflows/tests.yml/badge.svg)](https://github.com/Yeraze/meshmanager/actions/workflows/tests.yml)
[![Release](https://github.com/Yeraze/meshmanager/actions/workflows/release.yml/badge.svg)](https://github.com/Yeraze/meshmanager/actions/workflows/release.yml)
[![Backend Docker](https://img.shields.io/badge/docker-backend-blue?logo=docker)](https://ghcr.io/yeraze/meshmanager-backend)
[![Frontend Docker](https://img.shields.io/badge/docker-frontend-blue?logo=docker)](https://ghcr.io/yeraze/meshmanager-frontend)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

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

### Production (Pre-built Images)

The easiest way to deploy MeshManager is using pre-built Docker images:

1. Download the required files:
   ```bash
   mkdir meshmanager && cd meshmanager
   curl -O https://raw.githubusercontent.com/Yeraze/meshmanager/main/docker-compose.prebuilt.yml
   curl -O https://raw.githubusercontent.com/Yeraze/meshmanager/main/docker/nginx.conf
   curl -O https://raw.githubusercontent.com/Yeraze/meshmanager/main/.env.example
   ```

2. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (SESSION_SECRET is required)
   ```

3. Start the stack:
   ```bash
   docker compose -f docker-compose.prebuilt.yml up -d
   ```

4. Access the application at http://localhost:8080

To use a specific version instead of `latest`:
```bash
MESHMANAGER_VERSION=0.1.0 docker compose -f docker-compose.prebuilt.yml up -d
```

### Production (Build from Source)

If you prefer to build the images yourself:

1. Clone the repository and configure:
   ```bash
   git clone https://github.com/Yeraze/meshmanager.git
   cd meshmanager
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
| `MESHMANAGER_VERSION` | Docker image version (prebuilt only) | `latest` |
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

### Source Metrics
- `meshmanager_source_healthy` - Source collection status (1=healthy, 0=error)
- `meshmanager_source_last_collection_timestamp` - Last successful collection timestamp

### Node Metrics
- `meshmanager_node_battery_level` - Node battery level (0-100)
- `meshmanager_node_voltage` - Node voltage
- `meshmanager_node_last_heard_timestamp` - Node last heard timestamp (Unix seconds)
- `meshmanager_node_channel_utilization` - Node channel utilization (0-100)

### Network Metrics
- `meshmanager_active_nodes_total` - Active nodes per source (heard in last hour)
- `meshmanager_nodes_total` - Total nodes ever seen per source
- `meshmanager_messages_last_hour` - Messages received in last hour

### Database Metrics
- `meshmanager_db_rows_total` - Database row counts by table (nodes, messages, telemetry, traceroutes)

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

BSD-3-Clause
