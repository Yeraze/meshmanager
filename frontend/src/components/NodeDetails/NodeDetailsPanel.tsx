import { useState } from 'react'
import type { Node } from '../../types/api'
import { useAvailableMetrics, useSolarData, useTelemetryHistory } from '../../hooks/useTelemetry'
import { useNodesByNodeNum } from '../../hooks/useNodes'
import { useDataContext } from '../../contexts/DataContext'
import { getRoleName, getHardwareInfo } from '../../utils/meshtastic'
import TelemetryChart from './TelemetryChart'
import NodeConnections from './NodeConnections'

interface NodeDetailsPanelProps {
  node: Node
}

const TYPE_ORDER = ['device', 'environment', 'power', 'air_quality', 'local_stats', 'health', 'host'] as const
const TYPE_LABELS: Record<string, string> = {
  device: 'Device',
  environment: 'Environment',
  power: 'Power',
  air_quality: 'Air Quality',
  local_stats: 'Local Stats',
  health: 'Health',
  host: 'Host',
}

const STORAGE_KEY_HISTORY_HOURS = 'meshmanager_node_details_history_hours'

export default function NodeDetailsPanel({ node }: NodeDetailsPanelProps) {
  const { onlineHours } = useDataContext()
  const [historyHours, setHistoryHoursState] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY_HISTORY_HOURS)
    return stored ? Number(stored) : 24
  })

  const setHistoryHours = (hours: number) => {
    localStorage.setItem(STORAGE_KEY_HISTORY_HOURS, String(hours))
    setHistoryHoursState(hours)
  }

  // Fetch available metrics for this node
  const { data: availableMetrics } = useAvailableMetrics(node.node_num, historyHours)

  // Fetch solar data for background on charts
  const { solarMap } = useSolarData(historyHours)

  // Fetch all source records for this node
  const { data: sourceRecords = [] } = useNodesByNodeNum(node.node_num)

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
    const threshold = new Date(Date.now() - onlineHours * 60 * 60 * 1000)
    return lastHeard > threshold ? 'online' : 'offline'
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

        {node.hw_model && (() => {
          const hardwareInfo = getHardwareInfo(node.hw_model)
          return (
            <div className="node-info-card">
              <div className="node-info-label">Hardware</div>
              <div className="node-info-value" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {hardwareInfo.imageUrl && (
                  <img
                    src={hardwareInfo.imageUrl}
                    alt={hardwareInfo.name}
                    style={{
                      width: '48px',
                      height: '48px',
                      objectFit: 'contain',
                      backgroundColor: 'var(--ctp-surface0)',
                      borderRadius: '4px',
                      padding: '4px',
                    }}
                    onError={(e) => {
                      // Hide image if it fails to load
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                )}
                <span>{hardwareInfo.displayName}</span>
              </div>
            </div>
          )
        })()}

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

      {/* Node Connections Section */}
      <div className="telemetry-section">
        <div className="telemetry-header">
          <h2>Network Connections</h2>
        </div>
        <NodeConnections nodeNum={node.node_num} hours={historyHours} />
      </div>

      {/* Source Last Seen Table */}
      {sourceRecords.length > 1 && (
        <div className="source-history-section">
          <h2>Source History</h2>
          <table className="source-history-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {sourceRecords.map((record) => (
                <tr key={record.id}>
                  <td>{record.source_name || 'Unknown'}</td>
                  <td>{formatLastHeard(record.last_heard)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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

        {availableMetrics ? (
          TYPE_ORDER.map(typeKey => {
            const metrics = availableMetrics.metrics[typeKey]
            if (!metrics?.length) return null
            return (
              <div key={typeKey} className="telemetry-type-group">
                <h3 className="telemetry-type-heading">{TYPE_LABELS[typeKey]}</h3>
                <div className="telemetry-charts-grid">
                  {metrics.map(m => (
                    <TelemetryChartWrapper
                      key={m.name}
                      nodeNum={node.node_num}
                      metricKey={m.name}
                      metricLabel={m.label}
                      hours={historyHours}
                      solarData={solarMap}
                    />
                  ))}
                </div>
              </div>
            )
          })
        ) : (
          <div className="telemetry-charts-grid">
            <div className="telemetry-chart-loading">Loading metrics...</div>
          </div>
        )}
      </div>
    </div>
  )
}

function TelemetryChartWrapper({
  nodeNum,
  metricKey,
  metricLabel,
  hours,
  solarData,
}: {
  nodeNum: number
  metricKey: string
  metricLabel: string
  hours: number
  solarData?: Map<number, number>
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
      <TelemetryChart data={data} solarData={solarData} />
    </div>
  )
}
