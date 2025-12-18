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

The Docker Compose setup includes:

| Service | Image | Purpose |
|---------|-------|---------|
| `frontend` | meshmanager-frontend | React SPA served by Nginx |
| `backend` | meshmanager-backend | FastAPI Python application |
| `postgres` | postgres:16-alpine | PostgreSQL database |
| `nginx` | nginx:alpine | Reverse proxy |

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

By default, services communicate on an internal Docker network. Only the Nginx proxy is exposed to the host.

### Port Configuration

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | nginx | HTTP access |
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

Both frontend and backend services include health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
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

# Specific service
docker compose logs -f backend
```

### Restart Services

```bash
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
