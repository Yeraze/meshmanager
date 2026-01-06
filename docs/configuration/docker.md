# Docker Deployment

MeshManager is designed to run in Docker containers using Docker Compose.

## Quick Start

```bash
git clone https://github.com/yeraze/meshmanager.git
cd meshmanager
docker compose up -d
```

Access the application at [http://localhost:8080](http://localhost:8080).

## Architecture

### Production (Pre-built Images)

Using pre-built images, the stack consists of just two containers:

| Service | Image | Purpose |
|---------|-------|---------|
| `meshmanager` | ghcr.io/yeraze/meshmanager | Unified app (FastAPI + React SPA) |
| `postgres` | postgres:16-alpine | PostgreSQL database |

### Development (Build from Source)

When building from source, the stack uses separate containers:

| Service | Purpose |
|---------|---------|
| `frontend` | React SPA with hot reloading |
| `backend` | FastAPI Python application |
| `postgres` | PostgreSQL database |
| `nginx` | Reverse proxy |

## Compose Files

### Production (docker-compose.yml)

Standard production deployment:

```yaml
docker compose up -d
```

### Development (docker-compose.dev.yml)

Development mode with hot reloading:

```yaml
docker compose -f docker-compose.dev.yml up -d
```

## Environment Variables

Configure via environment variables or `.env` file:

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `POSTGRES_USER` | `meshmanager` | Database user |
| `POSTGRES_PASSWORD` | `meshmanager` | Database password |
| `POSTGRES_DB` | `meshmanager` | Database name |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Volumes

### Database Persistence

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

Ensure the `postgres_data` volume is backed up regularly.

## Networking

By default, services communicate on an internal Docker network. Only the MeshManager application is exposed to the host.

### Port Configuration

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | meshmanager | HTTP access (maps to internal port 8000) |
| 5432 | postgres | Database (internal only by default) |

### Exposing Database

To access PostgreSQL from outside Docker:

```yaml
services:
  postgres:
    ports:
      - "5432:5432"
```

## Health Checks

The MeshManager container includes a health check:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Building Images

To rebuild images after code changes:

```bash
docker compose build
docker compose up -d
```

## Updating

```bash
git pull
docker compose build
docker compose up -d
```

## Troubleshooting

### View Logs

```bash
# All services
docker compose logs -f

# Specific service (production)
docker compose logs -f meshmanager

# Specific service (development)
docker compose logs -f backend
```

### Restart Services

```bash
# Production
docker compose restart meshmanager

# Development
docker compose restart backend
```

### Database Access

```bash
docker compose exec postgres psql -U meshmanager -d meshmanager
```

### Reset Everything

```bash
docker compose down -v  # Removes volumes too!
docker compose up -d
```

::: warning
Using `-v` will delete all data. Use with caution.
:::
