# Solar Integration

MeshManager integrates with [Forecast.Solar](https://forecast.solar) to predict solar production and identify nodes at risk of low battery.

## Overview

The solar integration provides:

- **Production Forecasting** - Predicted solar output based on your panel configuration
- **Historical Comparison** - Compare actual production to forecasts
- **Battery Simulation** - Predict which nodes may run low on battery
- **Automated Alerts** - Notifications for nodes at risk

## Configuration

### Prerequisites

1. **Solar Panels** - Know your panel specifications:
   - Latitude and longitude
   - Declination (tilt angle)
   - Azimuth (compass direction)
   - Peak power (kWp)

2. **Nodes with Solar** - Identify which mesh nodes have solar charging

### Setting Up Solar Monitoring

1. Navigate to **Settings > Solar Schedule**
2. Configure your solar panel parameters:

| Field | Description | Example |
|-------|-------------|---------|
| Latitude | Panel location latitude | `25.7617` |
| Longitude | Panel location longitude | `-80.1918` |
| Declination | Panel tilt in degrees | `25` |
| Azimuth | Panel direction (0=North, 180=South) | `180` |
| Peak Power | Panel capacity in kWp | `0.5` |

3. Click **Save**

### Selecting Solar Nodes

Mark nodes that have solar charging:

1. Go to the **Solar Analysis** page
2. Select nodes with solar panels
3. The system will track their battery levels against solar production

## Solar Analysis

### Production Chart

The main chart shows:

- **Blue Line** - Actual production (from Forecast.Solar estimate based on weather)
- **Dashed Line** - Forecasted production (ideal conditions)
- **Yellow Overlay** - Daylight hours

### Battery Simulation

For each solar-powered node:

1. Takes current battery level
2. Simulates drain based on historical consumption
3. Applies solar charging based on forecast
4. Predicts minimum battery level

### Risk Assessment

Nodes are flagged based on simulated minimum battery:

| Level | Criteria | Indicator |
|-------|----------|-----------|
| Critical | Below 20% | 🔴 Red |
| Warning | Below 50% | 🟡 Yellow |
| OK | Above 50% | ✅ Green |

## Scheduled Notifications

Configure automated solar reports:

1. Navigate to **Settings > Solar Schedule**
2. Enable **Scheduled Notifications**
3. Add notification times (24-hour format, e.g., `07:00`)
4. Configure Apprise notification URLs

### Notification Content

Scheduled notifications include:

- Today's forecast vs historical average
- List of nodes at risk with battery predictions
- Chart attachment showing production and node simulations

See [Notifications](/configuration/notifications) for Apprise URL configuration.

## Lookback Period

The analysis uses a configurable lookback period:

- **7 days** (default) - Balance of recent data and trend analysis
- **3 days** - More responsive to recent changes
- **14 days** - Smoother averages, less noise

Adjust in the Solar Analysis settings based on your needs.

## API Endpoints

For programmatic access:

- `GET /api/ui/analysis/solar-forecast` - Get forecast and analysis data
- `GET /api/ui/solar` - Get solar configuration
- `PUT /api/ui/settings/solar-schedule` - Update solar settings

See [API Reference](/api/analysis) for details.

## Troubleshooting

### No Forecast Data

- Verify latitude/longitude are correct
- Check that Forecast.Solar is accessible
- Ensure peak power is set (required for calculations)

### Inaccurate Predictions

- Verify panel orientation (declination/azimuth)
- Check for obstructions affecting actual production
- Adjust lookback period for your climate

### Missing Node Simulations

- Ensure nodes are marked as solar-powered
- Verify nodes have recent telemetry data
- Check that battery level data is being collected
