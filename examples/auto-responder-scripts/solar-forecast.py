#!/usr/bin/env python3
"""
Solar Forecast Auto-Responder Script for MeshMonitor

This script queries the MeshManager API for solar forecast analysis
and returns an abbreviated summary suitable for mesh network transmission.

Environment variables available from MeshMonitor:
- MESSAGE: Full message text
- FROM_NODE: Sender node number
- MESHMANAGER_URL: MeshManager API base URL (configure in MeshMonitor)

Setup:
1. Copy this script to your MeshMonitor scripts directory
2. Set MESHMANAGER_URL environment variable in your MeshMonitor container
   (e.g., MESHMANAGER_URL=http://meshmanager:8000)
3. Configure trigger in MeshMonitor UI:
   - Trigger Pattern: solar, forecast, sun
   - Response Type: Script
   - Response: /data/scripts/solar-forecast.py

Usage:
- "solar" - Get abbreviated solar forecast report
- "forecast" - Alias for solar
- "sun" - Alias for solar

Response format (abbreviated for mesh):
  Solar Forecast for 12/15
  4.1kWh (85% avg)
  Risk: 2 nodes
  - NodeA: min 23%
  - NodeB: min 41%
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime


def fetch_solar_forecast(base_url: str, lookback_days: int = 7) -> dict:
    """Fetch solar forecast data from MeshManager API."""
    url = f"{base_url}/api/analysis/solar-forecast?lookback_days={lookback_days}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        raise Exception(f"API request failed: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response: {e}")


def format_response(forecast: dict) -> str:
    """Format forecast data into abbreviated mesh-friendly response."""
    lines = []

    # Get forecast for today/tomorrow
    forecast_days = forecast.get("forecast_days", [])

    if forecast_days:
        today = forecast_days[0]
        date_str = today.get("date", "")
        wh = today.get("forecast_wh", 0)
        pct = today.get("pct_of_average", 100)

        # Format date as MM/DD
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = dt.strftime("%m/%d")
            except ValueError:
                formatted_date = date_str
        else:
            formatted_date = datetime.now().strftime("%m/%d")

        # Header line with date
        lines.append(f"Solar Forecast for {formatted_date}")

        # Solar output line
        if wh >= 1000:
            wh_str = f"{wh/1000:.1f}kWh"
        else:
            wh_str = f"{wh:.0f}Wh"

        status = ""
        if forecast.get("low_output_warning"):
            status = " LOW!"
        lines.append(f"{wh_str} ({pct:.0f}% avg){status}")
    else:
        lines.append("Solar: No forecast data")

    # Nodes at risk
    nodes_at_risk = forecast.get("nodes_at_risk", [])
    risk_count = len(nodes_at_risk)

    if risk_count > 0:
        lines.append(f"Risk: {risk_count} node{'s' if risk_count != 1 else ''}")

        # Show up to 3 nodes at risk (abbreviated)
        for node in nodes_at_risk[:3]:
            name = node.get("node_name", "?")
            # Truncate long names
            if len(name) > 12:
                name = name[:10] + ".."
            min_bat = node.get("min_simulated_battery", 0)
            lines.append(f"- {name}: {min_bat:.0f}%")

        if risk_count > 3:
            lines.append(f"+ {risk_count - 3} more")
    else:
        lines.append("Risk: None")

    return "\n".join(lines)


def main():
    """Main function to fetch and format solar forecast."""
    try:
        # Get MeshManager URL from environment
        base_url = os.environ.get("MESHMANAGER_URL", "http://localhost:8000")

        # Remove trailing slash if present
        base_url = base_url.rstrip("/")

        # Fetch forecast data
        forecast = fetch_solar_forecast(base_url)

        # Format response
        response_text = format_response(forecast)

        # Ensure response fits in mesh message (200 char limit)
        if len(response_text) > 200:
            response_text = response_text[:197] + "..."

        output = {"response": response_text}
        print(json.dumps(output))

    except Exception as e:
        error_msg = f"Solar forecast error: {str(e)}"
        if len(error_msg) > 195:
            error_msg = error_msg[:192] + "..."
        output = {"response": error_msg}
        print(json.dumps(output))
        print(f"Script error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
