import { useCallback, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  fetchMessageUtilizationAnalysis,
  type MessageUtilizationAnalysis,
} from '../../services/api'

// Catppuccin Mocha colors for message types
const TYPE_COLORS: Record<string, string> = {
  text: '#89b4fa',      // Blue - text messages
  device: '#a6e3a1',    // Green - device telemetry
  environment: '#fab387', // Peach - environment
  power: '#f9e2af',     // Yellow - power
  position: '#cba6f7',  // Mauve - position
  air_quality: '#94e2d5', // Teal - air quality
  traceroute: '#f5c2e7', // Pink - traceroutes
  nodeinfo: '#74c7ec',  // Sapphire - node info
  encrypted: '#f38ba8', // Red - encrypted
  unknown: '#9399b2',   // Overlay1 - unknown
}

const TYPE_LABELS: Record<string, string> = {
  text: 'Text Messages',
  device: 'Device Telemetry',
  environment: 'Environment',
  power: 'Power',
  position: 'Position',
  air_quality: 'Air Quality',
  traceroute: 'Traceroutes',
  nodeinfo: 'Node Info',
  encrypted: 'Encrypted',
  unknown: 'Unknown',
}

export default function MessageUtilization() {
  const [lookbackDays, setLookbackDays] = useState(7)

  // Filter states
  const [includeText, setIncludeText] = useState(true)
  const [includeDevice, setIncludeDevice] = useState(true)
  const [includeEnvironment, setIncludeEnvironment] = useState(true)
  const [includePower, setIncludePower] = useState(true)
  const [includePosition, setIncludePosition] = useState(true)
  const [includeAirQuality, setIncludeAirQuality] = useState(true)
  const [includeTraceroute, setIncludeTraceroute] = useState(true)
  const [includeNodeinfo, setIncludeNodeinfo] = useState(true)
  const [includeEncrypted, setIncludeEncrypted] = useState(true)
  const [includeUnknown, setIncludeUnknown] = useState(true)
  const [excludeLocalNodes, setExcludeLocalNodes] = useState(false)

  // Ref captures current filter values at click time so queryFn uses a stable snapshot
  const paramsRef = useRef({
    lookback_days: lookbackDays,
    include_text: includeText,
    include_device: includeDevice,
    include_environment: includeEnvironment,
    include_power: includePower,
    include_position: includePosition,
    include_air_quality: includeAirQuality,
    include_traceroute: includeTraceroute,
    include_nodeinfo: includeNodeinfo,
    include_encrypted: includeEncrypted,
    include_unknown: includeUnknown,
    exclude_local_nodes: excludeLocalNodes,
  })

  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ['message-utilization'],
    queryFn: () => fetchMessageUtilizationAnalysis(paramsRef.current),
    enabled: false,
  })

  const handleAnalyze = useCallback(() => {
    paramsRef.current = {
      lookback_days: lookbackDays,
      include_text: includeText,
      include_device: includeDevice,
      include_environment: includeEnvironment,
      include_power: includePower,
      include_position: includePosition,
      include_air_quality: includeAirQuality,
      include_traceroute: includeTraceroute,
      include_nodeinfo: includeNodeinfo,
      include_encrypted: includeEncrypted,
      include_unknown: includeUnknown,
      exclude_local_nodes: excludeLocalNodes,
    }
    refetch()
  }, [lookbackDays, includeText, includeDevice, includeEnvironment, includePower, includePosition, includeAirQuality, includeTraceroute, includeNodeinfo, includeEncrypted, includeUnknown, excludeLocalNodes, refetch])

  const labelStyle = {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase' as const,
    marginBottom: '0.25rem',
  }
  const controlGroupStyle = { marginBottom: '1rem' }

  const checkboxStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.5rem',
    cursor: 'pointer',
  }

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        background: 'var(--color-surface)',
        borderRadius: '8px',
        border: '1px solid var(--color-border)',
        overflow: 'hidden',
      }}
    >
      {/* Left Sidebar - Controls */}
      <div
        style={{
          width: '280px',
          flexShrink: 0,
          borderRight: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Options</h3>
        </div>

        <div style={{ padding: '1rem', overflowY: 'auto', flex: 1 }}>
          {/* Lookback Period */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Lookback Period (Days)</div>
            <input
              type="number"
              min="1"
              max="90"
              value={lookbackDays}
              onChange={(e) => setLookbackDays(parseInt(e.target.value) || 7)}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-background)',
                color: 'var(--color-text)',
              }}
            />
          </div>

          {/* Message Type Filters */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Message Types</div>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeText}
                onChange={(e) => setIncludeText(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.text, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Text Messages</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeDevice}
                onChange={(e) => setIncludeDevice(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.device, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Device Telemetry</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeEnvironment}
                onChange={(e) => setIncludeEnvironment(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.environment, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Environment</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includePower}
                onChange={(e) => setIncludePower(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.power, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Power</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includePosition}
                onChange={(e) => setIncludePosition(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.position, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Position</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeAirQuality}
                onChange={(e) => setIncludeAirQuality(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.air_quality, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Air Quality</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeTraceroute}
                onChange={(e) => setIncludeTraceroute(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.traceroute, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Traceroutes</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeNodeinfo}
                onChange={(e) => setIncludeNodeinfo(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.nodeinfo, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Node Info</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeEncrypted}
                onChange={(e) => setIncludeEncrypted(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.encrypted, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Encrypted</span>
            </label>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={includeUnknown}
                onChange={(e) => setIncludeUnknown(e.target.checked)}
              />
              <span style={{ display: 'inline-block', width: 12, height: 12, background: TYPE_COLORS.unknown, borderRadius: 2, marginRight: 4 }} />
              <span style={{ fontSize: '0.85rem' }}>Unknown</span>
            </label>
          </div>

          {/* Exclusions */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Exclusions</div>
            <label style={checkboxStyle}>
              <input
                type="checkbox"
                checked={excludeLocalNodes}
                onChange={(e) => setExcludeLocalNodes(e.target.checked)}
              />
              <span style={{ fontSize: '0.85rem' }}>Exclude Local Nodes</span>
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: '0.25rem 0 0 1.5rem' }}>
              Exclude telemetry from nodes directly connected to sources (via IP/MQTT), as they don't impact mesh traffic.
            </p>
          </div>

          {/* Analyze Button */}
          <div style={controlGroupStyle}>
            <button
              onClick={handleAnalyze}
              disabled={isFetching}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'var(--color-primary)',
                color: 'white',
                cursor: isFetching ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                opacity: isFetching ? 0.7 : 1,
              }}
            >
              {isFetching ? 'Analyzing...' : 'Analyze Messages'}
            </button>
          </div>

          {/* Results Summary */}
          {data && (
            <div style={controlGroupStyle}>
              <div style={labelStyle}>Results Summary</div>
              <div
                style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}
              >
                <div>
                  Period: <strong>{data.lookback_days} days</strong>
                </div>
                <div>
                  Total Messages: <strong>{data.total_messages.toLocaleString()}</strong>
                </div>
                <div>
                  Active Nodes: <strong>{data.total_nodes}</strong>
                </div>
                {data.local_nodes_excluded > 0 && (
                  <div style={{ color: 'var(--color-text-muted)' }}>
                    Local Nodes Excluded: <strong>{data.local_nodes_excluded}</strong>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Type Breakdown */}
          {data && Object.keys(data.type_breakdown).length > 0 && (
            <div style={controlGroupStyle}>
              <div style={labelStyle}>By Type</div>
              <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {Object.entries(data.type_breakdown).map(([type, count]) => (
                  <div key={type} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ display: 'inline-block', width: 10, height: 10, background: TYPE_COLORS[type] || '#888', borderRadius: 2 }} />
                      {TYPE_LABELS[type] || type}
                    </span>
                    <strong>{count.toLocaleString()}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right side - Charts */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-background)',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Message Activity Analysis</h3>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            Top senders and hourly activity distribution
          </p>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
          {!isFetching && !data && !error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--color-text-muted)',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <span style={{ fontSize: '2rem' }}>&#128172;</span>
              <span>Click "Analyze Messages" to begin</span>
            </div>
          )}

          {isFetching && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--color-text-muted)',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  border: '3px solid var(--color-border)',
                  borderTopColor: 'var(--color-primary)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <span>Analyzing message data...</span>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--color-error, #ef4444)',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <span>Error analyzing data</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                {(error as Error).message}
              </span>
            </div>
          )}

          {data && !isFetching && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Top 10 Chattiest Nodes Chart */}
              <ChattiesNodesChart data={data} />

              {/* Hourly Histogram */}
              <HourlyHistogramChart data={data} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ChattiesNodesChart({ data }: { data: MessageUtilizationAnalysis }) {
  if (data.top_nodes.length === 0) {
    return (
      <div
        style={{
          background: 'var(--color-background)',
          border: '1px solid var(--color-border)',
          borderRadius: '8px',
          padding: '2rem',
          textAlign: 'center',
          color: 'var(--color-text-muted)',
        }}
      >
        No message data found for the selected filters.
      </div>
    )
  }

  // Prepare chart data - show short node names
  const chartData = data.top_nodes.map((node) => ({
    name: node.node_name.length > 12 ? node.node_name.substring(0, 10) + '...' : node.node_name,
    fullName: node.node_name,
    total: node.total,
    ...node.breakdown,
  }))

  // Get all message types present in the data
  const messageTypes = Object.keys(data.type_breakdown)

  return (
    <div
      style={{
        background: 'var(--color-background)',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '1rem',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <h4 style={{ margin: 0, fontSize: '0.9rem' }}>Top 10 Chattiest Nodes</h4>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Nodes with the most messages over the lookback period
        </p>
      </div>
      <div style={{ padding: '1rem' }}>
        <div style={{ height: '300px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis type="number" stroke="var(--color-text-muted)" fontSize={10} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="var(--color-text-muted)"
                fontSize={10}
                width={75}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  color: 'var(--color-text)',
                }}
                formatter={(value, name) => [
                  value.toLocaleString(),
                  TYPE_LABELS[name as string] || name,
                ]}
                labelFormatter={(label, payload) => {
                  const item = payload?.[0]?.payload
                  return item?.fullName || label
                }}
              />
              {messageTypes.map((type) => (
                <Bar
                  key={type}
                  dataKey={type}
                  stackId="a"
                  fill={TYPE_COLORS[type] || '#888'}
                  name={type}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function HourlyHistogramChart({ data }: { data: MessageUtilizationAnalysis }) {
  // Prepare chart data
  const chartData = data.hourly_histogram.map((hour) => ({
    hour: `${hour.hour.toString().padStart(2, '0')}:00`,
    total: hour.total,
    ...hour.breakdown,
  }))

  // Get all message types present in the data
  const messageTypes = Object.keys(data.type_breakdown)

  // Find peak hour
  const peakHour = data.hourly_histogram.reduce((max, curr) =>
    curr.total > max.total ? curr : max
  , data.hourly_histogram[0])

  return (
    <div
      style={{
        background: 'var(--color-background)',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '1rem',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <h4 style={{ margin: 0, fontSize: '0.9rem' }}>Message Activity by Hour of Day</h4>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Distribution of messages across 24 hours (UTC)
          {peakHour && peakHour.total > 0 && (
            <span style={{ marginLeft: '1rem' }}>
              Peak: <strong>{peakHour.hour.toString().padStart(2, '0')}:00</strong> ({peakHour.total.toLocaleString()} messages)
            </span>
          )}
        </p>
      </div>
      <div style={{ padding: '1rem' }}>
        <div style={{ height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="hour"
                stroke="var(--color-text-muted)"
                fontSize={10}
                interval={2}
              />
              <YAxis stroke="var(--color-text-muted)" fontSize={10} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  color: 'var(--color-text)',
                }}
                formatter={(value, name) => [
                  (value as number).toLocaleString(),
                  TYPE_LABELS[name as string] || name,
                ]}
              />
              {messageTypes.map((type) => (
                <Bar
                  key={type}
                  dataKey={type}
                  stackId="a"
                  fill={TYPE_COLORS[type] || '#888'}
                  name={type}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
