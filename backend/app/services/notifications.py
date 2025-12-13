"""Notification service using Apprise."""

import logging

import apprise

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications via Apprise."""

    async def send(self, urls: list[str], title: str, body: str) -> dict:
        """Send notification to multiple Apprise URLs.

        Args:
            urls: List of Apprise notification URLs
            title: Notification title
            body: Notification body text

        Returns:
            Dict with success status and count of URLs
        """
        if not urls:
            logger.warning("No Apprise URLs provided, skipping notification")
            return {"success": False, "urls_count": 0, "error": "No URLs provided"}

        apobj = apprise.Apprise()
        for url in urls:
            apobj.add(url)

        try:
            success = apobj.notify(title=title, body=body)
            logger.info(f"Notification sent to {len(urls)} URLs, success={success}")
            return {"success": success, "urls_count": len(urls)}
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {"success": False, "urls_count": len(urls), "error": str(e)}

    def format_solar_summary(
        self, analysis: dict, forecast: dict | None = None
    ) -> tuple[str, str]:
        """Format solar analysis results as a notification summary.

        Uses markdown formatting for better readability on Discord/Slack/etc.

        Args:
            analysis: Solar nodes analysis results
            forecast: Optional solar forecast analysis results

        Returns:
            Tuple of (title, body) for the notification
        """
        title = "Solar Analysis Report"

        # Get values with correct field names from API response
        lookback_days = analysis.get("lookback_days", 7)
        total_analyzed = analysis.get("total_nodes_analyzed", 0)
        solar_nodes = analysis.get("solar_nodes", [])
        solar_count = analysis.get("solar_nodes_count", len(solar_nodes))

        lines = [
            f"**Period:** {lookback_days} days",
            f"**Nodes analyzed:** {total_analyzed}",
            f"**Solar nodes found:** {solar_count}",
        ]

        # Add charge/discharge averages if available
        avg_charge = analysis.get("avg_charging_hours_per_day")
        avg_discharge = analysis.get("avg_discharge_hours_per_day")
        if avg_charge is not None or avg_discharge is not None:
            lines.append("")
            lines.append("**Charging Stats**")
            if avg_charge is not None:
                lines.append(f"  Avg charging: {avg_charge:.1f} hrs/day")
            if avg_discharge is not None:
                lines.append(f"  Avg discharge: {avg_discharge:.1f} hrs/day")

        # Check for insufficient solar warnings (Low Solar nodes)
        insufficient_nodes = [
            node for node in solar_nodes if node.get("insufficient_solar")
        ]
        if insufficient_nodes:
            lines.append("")
            lines.append(f"**Low Solar Warning:** {len(insufficient_nodes)} nodes")
            for node in insufficient_nodes[:5]:
                node_name = node.get("node_name", "Unknown")
                lines.append(f"  - {node_name}")
            if len(insufficient_nodes) > 5:
                lines.append(f"  _...and {len(insufficient_nodes) - 5} more_")

        # Add forecast information if available
        if forecast:
            lines.append("")
            lines.append("---")  # Horizontal rule

            if forecast.get("low_output_warning"):
                lines.append("**WARNING: Low solar output forecast!**")
                lines.append("")

            hist_avg = forecast.get("avg_historical_daily_wh")
            if hist_avg is not None:
                lines.append(f"**Historical avg:** {hist_avg:.0f} Wh/day")

            nodes_at_risk = forecast.get("nodes_at_risk", [])
            if nodes_at_risk:
                lines.append("")
                lines.append(f"**Nodes at risk:** {len(nodes_at_risk)}")
                for node in nodes_at_risk[:5]:  # Limit to first 5
                    # Use correct field names from API response
                    node_name = node.get("node_name", "Unknown")
                    min_battery = node.get("min_simulated_battery", 0)
                    # Color-code by severity
                    if min_battery <= 10:
                        indicator = "🔴"
                    elif min_battery <= 30:
                        indicator = "🟡"
                    else:
                        indicator = "🟢"
                    lines.append(f"  {indicator} **{node_name}** — min {min_battery:.0f}%")
                if len(nodes_at_risk) > 5:
                    lines.append(f"  _...and {len(nodes_at_risk) - 5} more_")

        return title, "\n".join(lines)


# Global notification service instance
notification_service = NotificationService()
