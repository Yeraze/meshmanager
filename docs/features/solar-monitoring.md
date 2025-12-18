# Solar Monitoring

MeshManager includes powerful features for monitoring solar-powered Meshtastic nodes and predicting potential issues before they occur.

## Solar Node Identification

MeshManager automatically identifies solar-powered nodes by analyzing their charging patterns:

- Looks for daily charge/discharge cycles
- Detects sunrise charging increases
- Tracks typical charge and discharge rates
- Requires 2+ days of telemetry data

Nodes are classified as solar when they show consistent patterns of charging during daylight hours and discharging overnight.

## Forecast.Solar Integration

MeshManager integrates with [Forecast.Solar](https://forecast.solar) to get solar production predictions for your location.

### Configuration

1. Go to **Settings > Solar Schedule**
2. Enter your location coordinates (latitude/longitude)
3. Configure your solar panel setup:
   - Panel wattage (kWp)
   - Panel orientation (azimuth)
   - Panel tilt (declination)

### How It Works

1. MeshManager fetches hourly production forecasts from Forecast.Solar
2. Historical production is averaged to establish baselines
3. Forecasts are compared against historical averages
4. Warnings are generated when forecast is below 75% of average

## Nodes at Risk

The system simulates battery levels for each solar node based on:

- Current battery level
- Average charge rate (during daylight)
- Average discharge rate (overnight)
- Forecasted solar production

Nodes are flagged as "at risk" when simulated battery drops below 50%.

### Risk Calculation

For each forecast day, MeshManager simulates:
1. **Sunrise** - Battery level after overnight discharge
2. **Peak** - Battery level at maximum charge (adjusted by forecast factor)
3. **Sunset** - Battery level at end of day

If any simulated point drops below 50%, the node is added to the at-risk list.

## Scheduled Reports

Configure automated solar analysis reports:

1. Go to **Settings > Solar Schedule**
2. Enable scheduled notifications
3. Set notification times (e.g., "07:00" for morning report)
4. Configure Apprise notification URLs

### Report Contents

Each report includes:
- Solar production forecast for the day
- Comparison to historical average
- Low output warning (if applicable)
- List of nodes at risk with minimum predicted battery
- Chart image showing production and node simulations

### Example Report

```
☀️ Solar Analysis (7-day lookback)

📊 Forecast vs Historical:
• Today: 4,123Wh (88% of avg) ⚠️

⚠️ Low Output Warning
Forecast output is below 75% of your 7-day average.

🔋 Nodes at Risk (4):
• AlephNull: Current 65% → Min 6% 🔴
• Lana Truck: Current 72% → Min 16% 🔴
• Trash Panda: Current 78% → Min 20% 🟡
• Wynwood Solar: Current 82% → Min 25% 🟡
```

## Chart Visualization

The Solar Monitoring page displays:

### Production Chart
- Bar chart showing daily production
- Actual (blue) vs Forecast (cyan) comparison
- Average line and 75% warning threshold
- Historical data plus forecast days

### Node Simulation Charts
- Individual charts for each at-risk node
- Historical battery data (solid line)
- Simulated forecast (dashed line, color-coded by severity)
- Solar production background (semi-transparent)
- Reference lines at 50% and 25% battery

## Best Practices

1. **Allow time for data collection** - Solar identification needs at least 2 days of telemetry
2. **Verify your coordinates** - Incorrect location will produce inaccurate forecasts
3. **Adjust panel configuration** - Match your actual installation for better predictions
4. **Set conservative thresholds** - Consider increasing warning thresholds for critical nodes
