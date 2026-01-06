# Configuration Overview

MeshManager is designed to be configured primarily through the web interface, with some settings available via environment variables.

## Deployment Options

### Docker Compose (Recommended)

The recommended deployment method uses Docker Compose with:
- **MeshManager**: Unified application (FastAPI backend + React frontend)
- **Database**: PostgreSQL 16

See [Docker Deployment](/configuration/docker) for detailed instructions, or use the [Docker Configurator](/configuration/configurator) to generate a customized compose file.

### Development Setup

For development, use the development compose file:

```bash
docker compose -f docker-compose.dev.yml up -d
```

This enables hot-reloading and exposes additional debugging ports.

## Configuration Areas

### Data Sources

Configure where MeshManager pulls data from:
- [Data Sources](/configuration/sources) - MeshMonitor and MQTT connections

### Solar Integration

Set up solar monitoring features:
- [Solar Integration](/configuration/solar) - Forecast.Solar configuration

### Notifications

Configure automated alerts:
- [Notifications](/configuration/notifications) - Apprise notification setup

### Environment Variables

System-level configuration:
- [Environment Variables](/configuration/environment) - All available env vars

## Quick Configuration

### Adding a MeshMonitor Source

1. Navigate to **Admin** panel
2. Click **Add Source**
3. Select **MeshMonitor** type
4. Enter the source name and URL
5. Click **Save**

The collector will immediately begin polling for data.

### Adding an MQTT Source

1. Navigate to **Admin** panel
2. Click **Add Source**
3. Select **MQTT** type
4. Enter connection details:
   - Host, Port
   - Topic (e.g., `msh/US/#`)
   - Credentials (if required)
5. Click **Save**

### Setting Up Solar Notifications

1. Navigate to **Settings > Solar Schedule**
2. Enable scheduled notifications
3. Add notification times
4. Configure Apprise URLs:
   ```
   discord://webhook_id/webhook_token
   slack://token_a/token_b/token_c
   ```
5. Click **Save**

## Security Considerations

- Use HTTPS in production (configure via reverse proxy)
- Protect the admin interface with authentication
- Use secure passwords for MQTT connections
- Consider network segmentation for database access
