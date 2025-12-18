# Node Details

The Node Details page shows comprehensive information about a specific node.

## Node Information

### Identification

- **Node ID** - Hexadecimal identifier (e.g., `!abcd1234`)
- **Node Number** - Numeric identifier
- **Short Name** - 4-character name
- **Long Name** - Full descriptive name

### Hardware

- **Hardware Model** - Device type displayed as readable name
  - Examples: Heltec v3, RAK4631, T Deck, Station G2
- **Role** - Node's configured role in the mesh

### Status

- **Last Heard** - Relative time since last activity
- **Online/Offline** - Current status indicator

### Signal Quality

- **SNR** - Signal-to-Noise Ratio (dB)
  - Green: > 10 dB (good)
  - Yellow: 0-10 dB (medium)
  - Red: < 0 dB (poor)
- **RSSI** - Received Signal Strength (dBm)
- **Hops** - Number of hops from reporting node

### Position

When GPS coordinates are available:
- Latitude and longitude
- Can be clicked to open in mapping application

## Source History

When a node appears in multiple data sources, a table shows:
- Source name
- Last seen time for each source

This helps track which sources are receiving data from the node.

## Telemetry Charts

Interactive charts display historical telemetry data:

### Available Metrics

- **Battery Level** - Battery percentage (0-100%)
- **Voltage** - Battery voltage (V)
- **Channel Utilization** - Airtime usage (%)
- **Air Util TX** - Transmit utilization (%)
- **SNR** - Signal-to-noise ratio (dB)
- **RSSI** - Received signal strength (dBm)
- **Temperature** - Device temperature (°C)
- **Humidity** - Relative humidity (%)
- **Pressure** - Barometric pressure (hPa)

### Time Range

Select the time range for charts:
- Last 6 hours
- Last 12 hours
- Last 24 hours
- Last 48 hours
- Last 72 hours
- Last 7 days

### Solar Overlay

When [solar integration](/features/solar-monitoring) is configured, charts include a semi-transparent solar production overlay showing correlation between charging and solar output.
