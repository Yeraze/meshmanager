import { useState } from 'react'
import type { Node } from '../../types/api'
import { useTelemetryHistory } from '../../hooks/useTelemetry'
import { getRoleName } from '../../utils/meshtastic'
import TelemetryChart from './TelemetryChart'

interface NodeDetailsPanelProps {
  node: Node
}

const TELEMETRY_METRICS = [
  { key: 'battery_level', label: 'Battery Level' },
  { key: 'voltage', label: 'Voltage' },
  { key: 'channel_utilization', label: 'Channel Utilization' },
  { key: 'air_util_tx', label: 'Air Util TX' },
  { key: 'snr_local', label: 'SNR (Local)' },
  { key: 'snr_remote', label: 'SNR (Remote)' },
  { key: 'rssi', label: 'RSSI' },
  { key: 'temperature', label: 'Temperature' },
  { key: 'relative_humidity', label: 'Humidity' },
  { key: 'barometric_pressure', label: 'Pressure' },
]

export default function NodeDetailsPanel({ node }: NodeDetailsPanelProps) {
  const [historyHours, setHistoryHours] = useState(24)

  const displayName = node.long_name || node.short_name || node.node_id || `Node ${node.node_num}`

  // Format relative time
  const formatLastHeard = (lastHeard: string | null) => {
    if (!lastHeard) return 'Never'
    const date = new Date(lastHeard)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  // Format node ID in hex
  const formatNodeIdHex = (nodeNum: number) => {
    return `!${nodeNum.toString(16).padStart(8, '0')}`
  }

  // Get node status
  const getNodeStatus = () => {
    if (!node.last_heard) return 'unknown'
    const lastHeard = new Date(node.last_heard)
    const hourAgo = new Date(Date.now() - 60 * 60 * 1000)
    return lastHeard > hourAgo ? 'online' : 'offline'
  }

  const status = getNodeStatus()

  return (
    <div className="node-details-panel">
      {/* Header Section */}
      <div className="node-details-header-section">
        <div className="node-details-title-row">
          <h1>{displayName}</h1>
          <span className={`node-status-badge ${status}`}>
            {status === 'online' ? 'Online' : status === 'offline' ? 'Offline' : 'Unknown'}
          </span>
        </div>
        {node.short_name && node.long_name && (
          <div className="node-details-subtitle">[{node.short_name}]</div>
        )}
      </div>

      {/* Info Grid */}
      <div className="node-info-grid">
        <div className="node-info-card">
          <div className="node-info-label">Node ID</div>
          <div className="node-info-value">
            <div>{formatNodeIdHex(node.node_num)}</div>
            <div className="node-info-secondary">{node.node_num}</div>
          </div>
        </div>

        {node.hw_model && (
          <div className="node-info-card">
            <div className="node-info-label">Hardware</div>
            <div className="node-info-value">{node.hw_model}</div>
          </div>
        )}

        {node.role && (
          <div className="node-info-card">
            <div className="node-info-label">Role</div>
            <div className="node-info-value">{getRoleName(node.role)}</div>
          </div>
        )}

        <div className="node-info-card">
          <div className="node-info-label">Last Heard</div>
          <div className="node-info-value">{formatLastHeard(node.last_heard)}</div>
        </div>

        {node.snr !== null && (
          <div className="node-info-card">
            <div className="node-info-label">SNR</div>
            <div className={`node-info-value ${node.snr > 10 ? 'signal-good' : node.snr > 0 ? 'signal-medium' : 'signal-low'}`}>
              {node.snr.toFixed(1)} dB
            </div>
          </div>
        )}

        {node.rssi !== null && (
          <div className="node-info-card">
            <div className="node-info-label">RSSI</div>
            <div className="node-info-value">{node.rssi} dBm</div>
          </div>
        )}

        {node.hops_away !== null && (
          <div className="node-info-card">
            <div className="node-info-label">Hops</div>
            <div className="node-info-value">
              {node.hops_away === 0 ? 'Direct' : `${node.hops_away} hop${node.hops_away > 1 ? 's' : ''}`}
            </div>
          </div>
        )}

        {node.latitude !== null && node.longitude !== null && (
          <div className="node-info-card">
            <div className="node-info-label">Position</div>
            <div className="node-info-value">
              {node.latitude.toFixed(5)}, {node.longitude.toFixed(5)}
            </div>
          </div>
        )}

        <div className="node-info-card">
          <div className="node-info-label">Source</div>
          <div className="node-info-value">{node.source_name || 'Unknown'}</div>
        </div>
      </div>

      {/* Telemetry Charts Section */}
      <div className="telemetry-section">
        <div className="telemetry-header">
          <h2>Telemetry</h2>
          <select
            className="telemetry-hours-select"
            value={historyHours}
            onChange={(e) => setHistoryHours(Number(e.target.value))}
          >
            <option value={6}>Last 6 hours</option>
            <option value={12}>Last 12 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={48}>Last 48 hours</option>
            <option value={72}>Last 72 hours</option>
            <option value={168}>Last 7 days</option>
          </select>
        </div>

        <div className="telemetry-charts-grid">
          {TELEMETRY_METRICS.map((metric) => (
            <TelemetryChartWrapper
              key={metric.key}
              nodeNum={node.node_num}
              metricKey={metric.key}
              metricLabel={metric.label}
              hours={historyHours}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function TelemetryChartWrapper({
  nodeNum,
  metricKey,
  metricLabel,
  hours,
}: {
  nodeNum: number
  metricKey: string
  metricLabel: string
  hours: number
}) {
  const { data, isLoading, error } = useTelemetryHistory(nodeNum, metricKey, hours)

  if (isLoading) {
    return (
      <div className="telemetry-chart-card">
        <div className="telemetry-chart-title">{metricLabel}</div>
        <div className="telemetry-chart-loading">Loading...</div>
      </div>
    )
  }

  if (error || !data || data.data.length === 0) {
    return null // Don't show charts with no data
  }

  return (
    <div className="telemetry-chart-card">
      <div className="telemetry-chart-title">{data.metric} ({data.unit})</div>
      <TelemetryChart data={data} />
    </div>
  )
}
