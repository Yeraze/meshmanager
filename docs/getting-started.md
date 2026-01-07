# Getting Started

This guide will help you get MeshManager up and running quickly.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- At least one data source:
  - A running [MeshMonitor](https://meshmonitor.org) instance, or
  - Access to a Meshtastic MQTT broker

## Quick Start with Docker Compose

::: tip Docker Configurator
Need OIDC authentication or custom settings? Use the [Docker Configurator](/configuration/configurator) to generate a customized compose file.
:::

### 1. Create a `docker-compose.yml` file

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: meshmanager-db
    environment:
      POSTGRES_DB: meshmanager
      POSTGRES_USER: meshmanager
      POSTGRES_PASSWORD: meshmanager  # Change in production
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U meshmanager"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  meshmanager:
    image: ghcr.io/yeraze/meshmanager:latest
    container_name: meshmanager
    ports:
      - "8080:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://meshmanager:meshmanager@postgres/meshmanager
      SESSION_SECRET: change-me-to-random-string  # Required: generate with `openssl rand -hex 32`
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
```

::: warning Required Configuration
You **must** change `SESSION_SECRET` to a random string. Generate one with:
```bash
openssl rand -hex 32
```
:::

### 2. Start the services

```bash
docker compose up -d
```

### 3. Access the application

Open your browser to [http://localhost:8080](http://localhost:8080)

That's it! No complex configuration needed for basic usage.

::: tip Version Pinning
To use a specific version instead of `latest`, change the image tag:
```yaml
image: ghcr.io/yeraze/meshmanager:0.5.0
```
:::

## Building from Source

For development or customization, you can build locally:

```bash
git clone https://github.com/yeraze/meshmanager.git
cd meshmanager
docker compose -f docker-compose.dev.yml up -d
```

## Initial Configuration

### Adding Your First Data Source

1. Click **Admin** in the navigation (if authentication is enabled, log in first)
2. Click **Add Source**
3. Choose your source type:
   - **MeshMonitor**: Enter the URL of your MeshMonitor instance
   - **MQTT**: Enter your MQTT broker connection details

### MeshMonitor Source

To connect to a MeshMonitor instance:

| Field | Description | Example |
|-------|-------------|---------|
| Name | Friendly name for this source | `Home MeshMonitor` |
| URL | Base URL of MeshMonitor | `http://192.168.1.100:5000` |

MeshManager will poll the MeshMonitor API for:
- Node information
- Telemetry data
- Messages
- Traceroutes

### MQTT Source

To connect to a Meshtastic MQTT broker:

| Field | Description | Example |
|-------|-------------|---------|
| Name | Friendly name for this source | `Public MQTT` |
| Host | MQTT broker hostname | `mqtt.meshtastic.org` |
| Port | MQTT port | `1883` |
| Topic | Root topic to subscribe | `msh/US/#` |
| Username | Optional authentication | |
| Password | Optional authentication | |

## Solar Integration

MeshManager can integrate with [Forecast.Solar](https://forecast.solar) to:
- Compare actual vs predicted solar production
- Identify nodes at risk of low battery
- Generate automated reports

See [Solar Configuration](/configuration/solar) for setup details.

## Next Steps

- [Configure Notifications](/configuration/notifications) - Set up automated alerts
- [Explore Features](/features/) - Learn about all MeshManager capabilities
- [API Reference](/api/) - Integrate with MeshManager programmatically
