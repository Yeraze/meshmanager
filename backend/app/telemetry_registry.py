"""Telemetry metric registry — single source of truth for all known Meshtastic metrics."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.telemetry import TelemetryType


@dataclass(frozen=True)
class MetricDef:
    """Definition of a single telemetry metric."""

    name: str  # snake_case canonical name (stored in metric_name)
    label: str  # Human-readable label for UI
    unit: str  # Unit of measurement
    telemetry_type: TelemetryType
    dedicated_column: str | None = None  # Legacy column name if one exists


# ---------------------------------------------------------------------------
# Build the registry
# ---------------------------------------------------------------------------

_METRICS: list[MetricDef] = [
    # ---- Device metrics ----
    MetricDef("battery_level", "Battery Level", "%", TelemetryType.DEVICE, "battery_level"),
    MetricDef("voltage", "Voltage", "V", TelemetryType.DEVICE, "voltage"),
    MetricDef("channel_utilization", "Channel Utilization", "%", TelemetryType.DEVICE, "channel_utilization"),
    MetricDef("air_util_tx", "Air Utilization TX", "%", TelemetryType.DEVICE, "air_util_tx"),
    MetricDef("uptime_seconds", "Uptime", "s", TelemetryType.DEVICE, "uptime_seconds"),
    MetricDef("snr_local", "SNR (Local)", "dB", TelemetryType.DEVICE, "snr_local"),
    MetricDef("snr_remote", "SNR (Remote)", "dB", TelemetryType.DEVICE, "snr_remote"),
    MetricDef("rssi", "RSSI", "dBm", TelemetryType.DEVICE, "rssi"),
    # ---- Paxcounter metrics ----
    MetricDef("paxcounter_wifi", "PAX WiFi", "count", TelemetryType.DEVICE),
    MetricDef("paxcounter_ble", "PAX BLE", "count", TelemetryType.DEVICE),
    MetricDef("paxcounter_uptime", "PAX Uptime", "s", TelemetryType.DEVICE),
    # ---- Device info metrics (reported by MeshMonitor) ----
    MetricDef("heap_free_bytes", "Heap Free", "bytes", TelemetryType.DEVICE),
    MetricDef("heap_total_bytes", "Heap Total", "bytes", TelemetryType.DEVICE),
    MetricDef("system_node_count", "System Nodes", "count", TelemetryType.DEVICE),
    MetricDef("system_direct_node_count", "Direct Nodes", "count", TelemetryType.DEVICE),
    # ---- Environment metrics ----
    MetricDef("temperature", "Temperature", "°C", TelemetryType.ENVIRONMENT, "temperature"),
    MetricDef("relative_humidity", "Humidity", "%", TelemetryType.ENVIRONMENT, "relative_humidity"),
    MetricDef("barometric_pressure", "Pressure", "hPa", TelemetryType.ENVIRONMENT, "barometric_pressure"),
    MetricDef("gas_resistance", "Gas Resistance", "Ω", TelemetryType.ENVIRONMENT),
    MetricDef("iaq", "Indoor Air Quality", "index", TelemetryType.ENVIRONMENT),
    MetricDef("distance", "Distance", "mm", TelemetryType.ENVIRONMENT),
    MetricDef("lux", "Illuminance", "lx", TelemetryType.ENVIRONMENT),
    MetricDef("white_lux", "White Illuminance", "lx", TelemetryType.ENVIRONMENT),
    MetricDef("ir_lux", "IR Illuminance", "lx", TelemetryType.ENVIRONMENT),
    MetricDef("uv_lux", "UV Index", "index", TelemetryType.ENVIRONMENT),
    MetricDef("wind_speed", "Wind Speed", "m/s", TelemetryType.ENVIRONMENT),
    MetricDef("wind_direction", "Wind Direction", "°", TelemetryType.ENVIRONMENT),
    MetricDef("wind_lull", "Wind Lull", "m/s", TelemetryType.ENVIRONMENT),
    MetricDef("wind_gust", "Wind Gust", "m/s", TelemetryType.ENVIRONMENT),
    MetricDef("rainfall", "Rainfall", "mm", TelemetryType.ENVIRONMENT),
    MetricDef("soil_moisture", "Soil Moisture", "%", TelemetryType.ENVIRONMENT),
    MetricDef("soil_temperature", "Soil Temperature", "°C", TelemetryType.ENVIRONMENT),
    MetricDef("weight", "Weight", "kg", TelemetryType.ENVIRONMENT),
    MetricDef("radiation", "Radiation", "μSv/h", TelemetryType.ENVIRONMENT),
    MetricDef("current", "Current", "mA", TelemetryType.ENVIRONMENT, "current"),
    # ---- Power metrics ----
    MetricDef("ch1_voltage", "Ch1 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch1_current", "Ch1 Current", "mA", TelemetryType.POWER),
    MetricDef("ch2_voltage", "Ch2 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch2_current", "Ch2 Current", "mA", TelemetryType.POWER),
    MetricDef("ch3_voltage", "Ch3 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch3_current", "Ch3 Current", "mA", TelemetryType.POWER),
    MetricDef("ch4_voltage", "Ch4 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch4_current", "Ch4 Current", "mA", TelemetryType.POWER),
    MetricDef("ch5_voltage", "Ch5 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch5_current", "Ch5 Current", "mA", TelemetryType.POWER),
    MetricDef("ch6_voltage", "Ch6 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch6_current", "Ch6 Current", "mA", TelemetryType.POWER),
    MetricDef("ch7_voltage", "Ch7 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch7_current", "Ch7 Current", "mA", TelemetryType.POWER),
    MetricDef("ch8_voltage", "Ch8 Voltage", "V", TelemetryType.POWER),
    MetricDef("ch8_current", "Ch8 Current", "mA", TelemetryType.POWER),
    # ---- Air Quality metrics ----
    MetricDef("pm10_standard", "PM1.0 (Standard)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("pm25_standard", "PM2.5 (Standard)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("pm100_standard", "PM10 (Standard)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("pm10_environmental", "PM1.0 (Env)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("pm25_environmental", "PM2.5 (Env)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("pm100_environmental", "PM10 (Env)", "μg/m³", TelemetryType.AIR_QUALITY),
    MetricDef("particles_03um", "Particles >0.3μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("particles_05um", "Particles >0.5μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("particles_10um", "Particles >1.0μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("particles_25um", "Particles >2.5μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("particles_50um", "Particles >5.0μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("particles_100um", "Particles >10μm", "/0.1L", TelemetryType.AIR_QUALITY),
    MetricDef("co2", "CO₂", "ppm", TelemetryType.AIR_QUALITY),
    MetricDef("tvoc", "TVOC", "ppb", TelemetryType.AIR_QUALITY),
    MetricDef("no2", "NO₂", "ppb", TelemetryType.AIR_QUALITY),
    MetricDef("formaldehyde", "Formaldehyde", "μg/m³", TelemetryType.AIR_QUALITY),
    # ---- Local Stats metrics ----
    MetricDef("num_online_nodes", "Online Nodes", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_total_nodes", "Total Nodes", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_packets_tx", "Packets TX", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_packets_rx", "Packets RX", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_packets_tx_relay", "Packets TX Relay", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_packets_rx_bad", "Packets RX Bad", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_packets_rx_dup", "Packets RX Dup", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_tx_cancelled", "TX Cancelled", "count", TelemetryType.LOCAL_STATS),
    MetricDef("num_tx_relay_cancelled", "TX Relay Cancelled", "count", TelemetryType.LOCAL_STATS),
    MetricDef("ls_uptime_seconds", "Uptime (Local Stats)", "s", TelemetryType.LOCAL_STATS),
    MetricDef("ls_channel_utilization", "Channel Util (Local Stats)", "%", TelemetryType.LOCAL_STATS),
    MetricDef("ls_air_util_tx", "Air Util TX (Local Stats)", "%", TelemetryType.LOCAL_STATS),
    MetricDef("noise_floor", "Noise Floor", "dBm", TelemetryType.LOCAL_STATS),
    # ---- Health metrics ----
    MetricDef("heart_bpm", "Heart Rate", "bpm", TelemetryType.HEALTH),
    MetricDef("sp_o2", "SpO₂", "%", TelemetryType.HEALTH),
    MetricDef("body_temperature", "Body Temperature", "°C", TelemetryType.HEALTH),
    # ---- Host metrics ----
    MetricDef("host_uptime_seconds", "Host Uptime", "s", TelemetryType.HOST),
    MetricDef("freemem_bytes", "Free Memory", "bytes", TelemetryType.HOST),
    MetricDef("diskfree_bytes", "Disk Free", "bytes", TelemetryType.HOST),
    MetricDef("load1", "Load (1m)", "load", TelemetryType.HOST),
    MetricDef("load5", "Load (5m)", "load", TelemetryType.HOST),
    MetricDef("load15", "Load (15m)", "load", TelemetryType.HOST),
    MetricDef("total_memory_bytes", "Total Memory", "bytes", TelemetryType.HOST),
    MetricDef("swap_free_bytes", "Swap Free", "bytes", TelemetryType.HOST),
]

METRIC_REGISTRY: dict[str, MetricDef] = {m.name: m for m in _METRICS}
"""Map from snake_case metric name to its definition."""


# ---------------------------------------------------------------------------
# camelCase → snake_case mapping (protobuf MessageToDict output)
# ---------------------------------------------------------------------------

CAMEL_TO_METRIC: dict[str, str] = {
    # Device
    "batteryLevel": "battery_level",
    "voltage": "voltage",
    "channelUtilization": "channel_utilization",
    "airUtilTx": "air_util_tx",
    "uptimeSeconds": "uptime_seconds",
    # Paxcounter
    "paxcounterWifi": "paxcounter_wifi",
    "paxcounterBle": "paxcounter_ble",
    "paxcounterUptime": "paxcounter_uptime",
    # Device info (MeshMonitor)
    "heapFreeBytes": "heap_free_bytes",
    "heapTotalBytes": "heap_total_bytes",
    "systemNodeCount": "system_node_count",
    "systemDirectNodeCount": "system_direct_node_count",
    # Environment
    "temperature": "temperature",
    "relativeHumidity": "relative_humidity",
    "humidity": "relative_humidity",  # MeshMonitor short alias
    "barometricPressure": "barometric_pressure",
    "pressure": "barometric_pressure",  # MeshMonitor short alias
    "gasResistance": "gas_resistance",
    "iaq": "iaq",
    "distance": "distance",
    "lux": "lux",
    "whiteLux": "white_lux",
    "irLux": "ir_lux",
    "uvLux": "uv_lux",
    "windSpeed": "wind_speed",
    "windDirection": "wind_direction",
    "windLull": "wind_lull",
    "windGust": "wind_gust",
    "rainfall": "rainfall",
    "soilMoisture": "soil_moisture",
    "soilTemperature": "soil_temperature",
    "weight": "weight",
    "radiation": "radiation",
    "current": "current",
    # Power
    "ch1Voltage": "ch1_voltage",
    "ch1Current": "ch1_current",
    "ch2Voltage": "ch2_voltage",
    "ch2Current": "ch2_current",
    "ch3Voltage": "ch3_voltage",
    "ch3Current": "ch3_current",
    "ch4Voltage": "ch4_voltage",
    "ch4Current": "ch4_current",
    "ch5Voltage": "ch5_voltage",
    "ch5Current": "ch5_current",
    "ch6Voltage": "ch6_voltage",
    "ch6Current": "ch6_current",
    "ch7Voltage": "ch7_voltage",
    "ch7Current": "ch7_current",
    "ch8Voltage": "ch8_voltage",
    "ch8Current": "ch8_current",
    # Air Quality
    "pm10Standard": "pm10_standard",
    "pm25Standard": "pm25_standard",
    "pm100Standard": "pm100_standard",
    "pm10Environmental": "pm10_environmental",
    "pm25Environmental": "pm25_environmental",
    "pm100Environmental": "pm100_environmental",
    "particles03um": "particles_03um",
    "particles05um": "particles_05um",
    "particles10um": "particles_10um",
    "particles25um": "particles_25um",
    "particles50um": "particles_50um",
    "particles100um": "particles_100um",
    "co2": "co2",
    "tvoc": "tvoc",
    "no2": "no2",
    "formaldehyde": "formaldehyde",
    # Local Stats
    "numOnlineNodes": "num_online_nodes",
    "numTotalNodes": "num_total_nodes",
    "numPacketsTx": "num_packets_tx",
    "numPacketsRx": "num_packets_rx",
    "numPacketsTxRelay": "num_packets_tx_relay",
    "numPacketsRxBad": "num_packets_rx_bad",
    "numPacketsRxDup": "num_packets_rx_dup",
    "numTxCancelled": "num_tx_cancelled",
    "numTxRelayCancelled": "num_tx_relay_cancelled",
    # MeshMonitor local stats aliases (slightly different naming)
    "numRxDupe": "num_packets_rx_dup",
    "numTxDropped": "num_tx_cancelled",
    "numTxRelay": "num_packets_tx_relay",
    "numTxRelayCanceled": "num_tx_relay_cancelled",  # single-l variant
    "noiseFloor": "noise_floor",
    # Health
    "heartBpm": "heart_bpm",
    "spO2": "sp_o2",
    "bodyTemperature": "body_temperature",
    # Host
    "hostUptimeSeconds": "host_uptime_seconds",
    "freememBytes": "freemem_bytes",
    "diskfreeBytes": "diskfree_bytes",
    "load1": "load1",
    "load5": "load5",
    "load15": "load15",
    "totalMemoryBytes": "total_memory_bytes",
    "swapFreeBytes": "swap_free_bytes",
}
"""Map from camelCase protobuf field names to snake_case metric names."""


# ---------------------------------------------------------------------------
# Sub-message key → TelemetryType mapping
# ---------------------------------------------------------------------------

SUBMESSAGE_TYPE_MAP: dict[str, TelemetryType] = {
    "deviceMetrics": TelemetryType.DEVICE,
    "environmentMetrics": TelemetryType.ENVIRONMENT,
    "powerMetrics": TelemetryType.POWER,
    "airQualityMetrics": TelemetryType.AIR_QUALITY,
    "localStats": TelemetryType.LOCAL_STATS,
    "healthMetrics": TelemetryType.HEALTH,
    "hostMetrics": TelemetryType.HOST,
}
"""Map from protobuf sub-message key to TelemetryType."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_metrics_by_type() -> dict[str, list[MetricDef]]:
    """Group all metrics by their telemetry type (string value)."""
    groups: dict[str, list[MetricDef]] = {}
    for m in _METRICS:
        key = m.telemetry_type.value
        if key not in groups:
            groups[key] = []
        groups[key].append(m)
    return groups
