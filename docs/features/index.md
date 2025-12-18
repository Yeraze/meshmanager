# Features Overview

MeshManager provides comprehensive tools for monitoring and managing your Meshtastic mesh network.

## Core Features

### Multi-Source Aggregation

Connect to multiple data sources simultaneously:
- **MeshMonitor Instances** - Poll data from any number of MeshMonitor deployments
- **MQTT Brokers** - Subscribe directly to Meshtastic MQTT topics

All data is aggregated and deduplicated, giving you a unified view of your entire network.

### Node Management

- View all nodes across all sources
- Filter by source, activity status, or role
- Detailed node information including hardware model and firmware
- Track when each node was last seen on each source

### Telemetry Visualization

Interactive charts for all telemetry metrics:
- Battery level and voltage
- Channel utilization and air time
- Temperature, humidity, and pressure
- Signal quality (SNR/RSSI)

Charts include solar production overlay when solar integration is configured.

### Solar Monitoring

Specialized features for solar-powered nodes:
- Automatic solar node identification based on charging patterns
- Integration with Forecast.Solar for production predictions
- Battery simulation to identify at-risk nodes
- Daily production charts (actual vs forecast)

### Scheduled Notifications

Automated reports delivered on schedule:
- Solar analysis summaries
- Nodes at risk alerts
- Chart image attachments
- Supports Discord, Slack, and 90+ notification services via Apprise

### Network Analysis

- Traceroute visualization
- Network topology graphs
- Node relationship mapping
- Signal quality analysis

## Feature Pages

- [Dashboard](/features/dashboard) - Main overview page
- [Node Details](/features/node-details) - Individual node information
- [Solar Monitoring](/features/solar-monitoring) - Solar-specific features
- [Notifications](/features/notifications) - Alert configuration
- [Multi-Source Support](/features/multi-source) - Working with multiple data sources
