# Dashboard

The MeshManager dashboard provides an overview of your mesh network.

## Node List

The main view displays all nodes across all configured sources:

- **Name** - Long name or short name of the node
- **Hardware** - Device hardware model (e.g., Heltec v3, RAK4631)
- **Role** - Node role (Client, Router, Tracker, etc.)
- **Last Heard** - Time since last activity
- **SNR/RSSI** - Signal quality metrics

### Filtering

Use the sidebar controls to filter the node list:
- **Source** - Show nodes from a specific data source
- **Active Only** - Hide nodes that haven't been heard recently
- **Active Hours** - Define what "recently" means (1-8760 hours)

### Search

Type in the search box to filter nodes by name or ID.

## Status Indicators

- **Online** (green) - Node heard within the configured active hours
- **Offline** (gray) - Node not heard recently

## Selecting a Node

Click on any node in the list to view its [detailed information](/features/node-details).
