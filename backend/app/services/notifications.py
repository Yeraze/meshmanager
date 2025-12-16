"""Notification service using Apprise."""

import logging
import tempfile
from datetime import datetime

import apprise
import matplotlib
import matplotlib.pyplot as plt

# Use non-interactive backend for server-side rendering
matplotlib.use("Agg")

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications via Apprise."""

    async def send(
        self, urls: list[str], title: str, body: str, image_path: str | None = None
    ) -> dict:
        """Send notification to multiple Apprise URLs.

        Args:
            urls: List of Apprise notification URLs
            title: Notification title
            body: Notification body text
            image_path: Optional path to image file to attach

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
            # Prepare attachment if image provided
            attach = None
            if image_path:
                attach = apprise.AppriseAttachment()
                attach.add(image_path)
                logger.info(f"Attaching image: {image_path}")

            success = apobj.notify(title=title, body=body, attach=attach)
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

    def generate_solar_chart(
        self,
        analysis: dict,
        forecast: dict,
        solar_production: list[dict],
    ) -> str | None:
        """Generate a solar production chart image with nodes at risk.

        Args:
            analysis: Solar nodes analysis data
            forecast: Solar forecast analysis data
            solar_production: Hourly solar production data points

        Returns:
            Path to generated image file, or None if generation fails
        """
        try:
            # Get today's date for determining actual vs forecast
            today = datetime.now().strftime("%Y-%m-%d")

            # Aggregate hourly solar production into daily totals
            daily_totals: dict[str, float] = {}
            for point in solar_production:
                # Convert timestamp (milliseconds) to date string
                ts = point.get("timestamp", 0)
                if ts:
                    date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    daily_totals[date] = daily_totals.get(date, 0) + point.get("wattHours", 0)

            # Get forecast data by date
            forecast_by_date = {
                d["date"]: d["forecast_wh"] for d in forecast.get("forecast_days", [])
            }

            # Collect all dates
            all_dates = sorted(set(daily_totals.keys()) | set(forecast_by_date.keys()))

            # Prepare chart data
            dates = []
            actual_values = []
            forecast_values = []

            for date in all_dates:
                dates.append(date)
                is_future = date > today

                # Actual: only for today and past
                if not is_future and date in daily_totals:
                    actual_values.append(daily_totals[date])
                else:
                    actual_values.append(0)

                # Forecast: only for today and future
                if (date >= today) and date in forecast_by_date:
                    forecast_values.append(forecast_by_date[date])
                else:
                    forecast_values.append(0)

            if not dates:
                logger.warning("No data available for solar chart")
                return None

            # Get average for reference line
            avg_historical = forecast.get("avg_historical_daily_wh", 0)
            warning_threshold = avg_historical * 0.75

            # Get nodes at risk for subplots
            nodes_at_risk = forecast.get("nodes_at_risk", [])
            num_risk_nodes = len(nodes_at_risk)

            # Calculate figure layout
            # Main chart on top, then 2-column grid for risk nodes below
            num_risk_rows = (num_risk_nodes + 1) // 2  # Ceiling division for 2 columns
            total_rows = 1 + num_risk_rows if num_risk_nodes > 0 else 1

            # Create figure with subplots
            if num_risk_nodes > 0:
                # Use GridSpec for flexible layout
                fig = plt.figure(figsize=(10, 4 + num_risk_rows * 2.5), layout="constrained")
                gs = fig.add_gridspec(
                    total_rows, 2,
                    height_ratios=[2] + [1] * num_risk_rows if num_risk_rows > 0 else [1],
                    hspace=0.1,
                    wspace=0.1
                )
                ax_main = fig.add_subplot(gs[0, :])  # Main chart spans both columns
            else:
                fig, ax_main = plt.subplots(figsize=(10, 5), layout="constrained")

            # Set dark theme for figure
            fig.patch.set_facecolor("#1e1e2e")

            # === Main Solar Production Chart ===
            ax_main.set_facecolor("#1e1e2e")

            x = range(len(dates))
            bar_width = 0.35

            # Plot bars
            ax_main.bar(
                [i - bar_width / 2 for i in x],
                actual_values,
                bar_width,
                label="Actual",
                color="#89b4fa",
            )
            ax_main.bar(
                [i + bar_width / 2 for i in x],
                forecast_values,
                bar_width,
                label="Forecast",
                color="#f9e2af",
            )

            # Add reference lines
            if avg_historical > 0:
                ax_main.axhline(
                    y=avg_historical,
                    color="#a6adc8",
                    linestyle="--",
                    linewidth=2,
                    label=f"Average ({avg_historical:.0f} Wh)",
                )
                ax_main.axhline(
                    y=warning_threshold,
                    color="#ef4444",
                    linestyle="--",
                    linewidth=2,
                    label=f"75% Warning ({warning_threshold:.0f} Wh)",
                )

            # Format x-axis labels (show month/day)
            date_labels = [f"{d[5:7]}/{d[8:10]}" for d in dates]
            ax_main.set_xticks(list(x))
            ax_main.set_xticklabels(date_labels, color="#cdd6f4")

            # Style main chart
            ax_main.set_ylabel("Watt Hours", color="#cdd6f4")
            ax_main.set_title(
                "Daily Solar Production", color="#cdd6f4", fontsize=14, fontweight="bold"
            )
            ax_main.tick_params(colors="#cdd6f4")
            for spine in ax_main.spines.values():
                spine.set_color("#45475a")

            # Legend
            ax_main.legend(
                loc="upper left", facecolor="#313244", edgecolor="#45475a", labelcolor="#cdd6f4"
            )

            # Grid
            ax_main.yaxis.grid(True, color="#45475a", linestyle="--", alpha=0.5)
            ax_main.set_axisbelow(True)

            # === Nodes at Risk Subplots ===
            # Build lookup for solar_nodes by node_num for historical chart_data
            solar_nodes_by_num = {
                n.get("node_num"): n for n in analysis.get("solar_nodes", [])
            }

            # Build hourly solar production lookup (timestamp in ms -> wattHours)
            solar_by_hour: dict[int, float] = {}
            for sp in solar_production:
                ts = sp.get("timestamp", 0)
                if ts:
                    hour_ts = (ts // 3600000) * 3600000  # Round to hour
                    solar_by_hour[hour_ts] = sp.get("wattHours", 0)

            # Find max solar wattHours for scaling the background
            max_solar_wh = max(solar_by_hour.values()) if solar_by_hour else 1

            for idx, node in enumerate(nodes_at_risk):
                row = 1 + idx // 2  # Start from row 1 (row 0 is main chart)
                col = idx % 2

                ax = fig.add_subplot(gs[row, col])
                ax.set_facecolor("#1e1e2e")

                node_num = node.get("node_num")
                min_battery = node.get("min_simulated_battery", 0)

                # Get historical chart_data from solar_nodes analysis
                solar_node = solar_nodes_by_num.get(node_num, {})
                chart_data = solar_node.get("chart_data", [])

                # Get forecast simulation data
                simulation = node.get("simulation", [])

                # Collect all data points: historical + forecast
                hist_times = []
                hist_batteries = []
                forecast_times = []
                forecast_batteries = []

                # Parse historical data (convert to naive datetime for consistency)
                for point in chart_data:
                    ts = point.get("timestamp", 0)
                    value = point.get("value")
                    if ts and value is not None:
                        hist_times.append(datetime.fromtimestamp(ts / 1000))
                        hist_batteries.append(value)

                # Parse forecast simulation (convert to naive datetime for consistency)
                for sim_point in simulation:
                    ts_str = sim_point.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            # Convert to naive datetime by removing timezone
                            ts = ts.replace(tzinfo=None)
                            forecast_times.append(ts)
                            forecast_batteries.append(sim_point.get("simulated_battery", 0))
                        except ValueError:
                            continue

                # Need at least some data to plot
                if not hist_times and not forecast_times:
                    continue

                # Determine time range for solar background
                all_times = hist_times + forecast_times
                if not all_times:
                    continue

                min_time = min(all_times)
                max_time = max(all_times)

                # Create secondary y-axis for solar production
                ax2 = ax.twinx()

                # Plot solar production as semi-transparent background area
                solar_times = []
                solar_values = []
                for hour_ts, wh in sorted(solar_by_hour.items()):
                    dt = datetime.fromtimestamp(hour_ts / 1000)
                    # Only include solar data within the chart time range (with some padding)
                    if min_time <= dt <= max_time:
                        solar_times.append(dt)
                        solar_values.append(wh)

                if solar_times:
                    ax2.fill_between(
                        solar_times, 0, solar_values,
                        color="#f9e2af", alpha=0.15, label="Solar"
                    )
                    ax2.set_ylim(0, max_solar_wh * 1.1)
                    ax2.tick_params(colors="#f9e2af", labelsize=6)
                    ax2.set_ylabel("Wh", color="#f9e2af", fontsize=7)
                    for spine in ax2.spines.values():
                        spine.set_color("#45475a")

                # Color based on severity
                if min_battery <= 10:
                    line_color = "#f38ba8"  # Red
                elif min_battery <= 30:
                    line_color = "#f9e2af"  # Yellow
                else:
                    line_color = "#a6e3a1"  # Green

                # Plot historical battery data (solid line)
                if hist_times:
                    ax.plot(
                        hist_times, hist_batteries,
                        color="#89b4fa", linewidth=1.5, label="Actual"
                    )

                # Plot forecast battery data (dashed line, different color)
                if forecast_times:
                    # Add bridge point to connect historical to forecast
                    if hist_times and hist_batteries:
                        bridge_times = [hist_times[-1]] + forecast_times
                        bridge_batteries = [hist_batteries[-1]] + forecast_batteries
                    else:
                        bridge_times = forecast_times
                        bridge_batteries = forecast_batteries

                    ax.plot(
                        bridge_times, bridge_batteries,
                        color=line_color, linewidth=2, linestyle="--",
                        marker="o", markersize=3, label="Forecast"
                    )

                # Add warning threshold lines
                ax.axhline(y=50, color="#f9e2af", linestyle=":", linewidth=1, alpha=0.5)
                ax.axhline(y=25, color="#f38ba8", linestyle=":", linewidth=1, alpha=0.5)

                # Style subplot
                node_name = node.get("node_name", "Unknown")
                # Truncate long names
                if len(node_name) > 20:
                    node_name = node_name[:17] + "..."
                ax.set_title(
                    f"{node_name} (min: {min_battery:.0f}%)",
                    color="#cdd6f4", fontsize=10, fontweight="bold"
                )
                ax.set_ylabel("Battery %", color="#cdd6f4", fontsize=8)
                ax.set_ylim(0, 110)
                ax.tick_params(colors="#cdd6f4", labelsize=7)
                for spine in ax.spines.values():
                    spine.set_color("#45475a")

                # Format x-axis with readable time labels
                ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%m/%d"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)

                # Grid
                ax.yaxis.grid(True, color="#45475a", linestyle="--", alpha=0.5)
                ax.set_axisbelow(True)

            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="solar_chart_"
            )
            plt.savefig(temp_file.name, dpi=150, facecolor=fig.get_facecolor())
            plt.close(fig)

            logger.info(f"Generated solar chart: {temp_file.name}")
            return temp_file.name

        except Exception as e:
            logger.error(f"Failed to generate solar chart: {e}")
            return None


# Global notification service instance
notification_service = NotificationService()
