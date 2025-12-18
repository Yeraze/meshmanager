# Getting Started

This guide will help you get MeshManager up and running quickly.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- At least one data source:
  - A running [MeshMonitor](https://meshmonitor.org) instance, or
  - Access to a Meshtastic MQTT broker

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yeraze/meshmanager.git
cd meshmanager
```

### 2. Start the Services

For development:
```bash
docker compose -f docker-compose.dev.yml up -d
```

For production:
```bash
docker compose up -d
```

### 3. Access the Application

Open your browser to [http://localhost:8080](http://localhost:8080)

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
