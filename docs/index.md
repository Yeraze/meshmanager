---
layout: home

hero:
  name: "MeshManager"
  text: "Multi-Source Mesh Network Management"
  tagline: Aggregate, analyze, and monitor your Meshtastic mesh network across multiple MeshMonitor instances
  image:
    src: /images/logo.png
    alt: MeshManager
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/yeraze/meshmanager

features:
  - icon: 🔗
    title: Multi-Source Aggregation
    details: Connect to multiple MeshMonitor instances and MQTT brokers to aggregate data from your entire mesh network into a single view.
  - icon: ☀️
    title: Solar Monitoring
    details: Track solar-powered nodes with forecast integration from Forecast.Solar. Identify nodes at risk of low battery before problems occur.
  - icon: 📊
    title: Telemetry Analysis
    details: View detailed telemetry charts for each node including battery, voltage, channel utilization, temperature, and signal metrics.
  - icon: 🔔
    title: Scheduled Notifications
    details: Configure automated solar analysis reports delivered via Discord, Slack, or any Apprise-compatible notification service.
  - icon: 🗺️
    title: Network Topology
    details: Visualize your mesh network topology with traceroute data showing node connections and signal quality.
  - icon: 🐳
    title: Docker Ready
    details: Deploy easily with Docker Compose. Just two containers - MeshManager and PostgreSQL - for simple production deployments.
---

## What is MeshManager?

MeshManager is a management and oversight application designed to aggregate data from multiple [MeshMonitor](https://meshmonitor.org) instances and Meshtastic MQTT brokers. It provides a unified view of your mesh network with advanced analytics and monitoring capabilities.

### Key Features

- **Multi-Source Data Collection** - Connect to multiple MeshMonitor instances and MQTT brokers
- **Solar Node Tracking** - Identify solar-powered nodes and predict battery issues using Forecast.Solar
- **Detailed Telemetry** - Historical charts for all node metrics with solar overlay
- **Automated Reports** - Scheduled notifications with analysis charts
- **Network Visualization** - Topology graphs showing node relationships

### Quick Start

Create a `docker-compose.yml` with MeshManager and PostgreSQL, then:

```bash
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

See the [Getting Started](/getting-started) guide for the complete compose file and setup instructions.
