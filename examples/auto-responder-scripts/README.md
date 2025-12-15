# MeshMonitor Auto-Responder Scripts

These scripts integrate with MeshMonitor's Auto-Responder feature to provide mesh network users with MeshManager data via text messages.

## Setup

1. Copy the desired scripts to your MeshMonitor container's scripts directory:
   ```bash
   docker cp solar-forecast.py meshmonitor:/data/scripts/
   ```

2. Configure the `MESHMANAGER_URL` environment variable in your MeshMonitor container to point to your MeshManager instance:
   ```yaml
   # docker-compose.yml
   services:
     meshmonitor:
       environment:
         MESHMANAGER_URL: http://meshmanager:8000
   ```

3. In MeshMonitor UI, go to **Settings > Automation > Auto Responder** and add a trigger:
   - **Trigger Pattern**: `solar`, `forecast`, `sun`
   - **Response Type**: Script
   - **Response**: `/data/scripts/solar-forecast.py`

## Available Scripts

### solar-forecast.py

Returns an abbreviated solar forecast report including:
- Today's forecasted solar production (Wh)
- Percentage compared to historical average
- Low output warning if applicable
- List of nodes at risk of low battery

**Trigger words**: `solar`, `forecast`, `sun`

**Example response**:
```
Solar: 1.2kWh (85% avg)
Risk: 2 nodes
- NodeAlpha: 23%
- NodeBeta: 41%
```

## Requirements

- MeshMonitor with Auto-Responder enabled
- MeshManager instance accessible from MeshMonitor container
- Python 3.6+ (included in MeshMonitor container)

## Script Guidelines

Scripts must:
- Output valid JSON with a `response` field
- Complete within 10 seconds
- Keep responses under 200 characters for mesh transmission
