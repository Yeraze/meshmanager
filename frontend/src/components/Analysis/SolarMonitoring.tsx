import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchSolarNodesAnalysis, type SolarNode, type SolarProductionPoint } from '../../services/api'

export default function SolarMonitoring() {
  const [lookbackDays, setLookbackDays] = useState(7)
  const [runAnalysis, setRunAnalysis] = useState(false)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['solar-nodes-analysis', lookbackDays],
    queryFn: () => fetchSolarNodesAnalysis(lookbackDays),
    enabled: runAnalysis,
  })

  const handleAnalyze = () => {
    setRunAnalysis(true)
    refetch()
  }

  const labelStyle = {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase' as const,
    marginBottom: '0.25rem',
  }
  const controlGroupStyle = { marginBottom: '1rem' }

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

          {/* Analysis Button */}
          <div style={controlGroupStyle}>
            <button
              onClick={handleAnalyze}
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'var(--color-primary)',
                color: 'white',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                opacity: isLoading ? 0.7 : 1,
              }}
            >
              {isLoading ? 'Analyzing...' : 'Identify Solar Nodes'}
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
                  Nodes Analyzed: <strong>{data.total_nodes_analyzed}</strong>
                </div>
                <div>
                  Solar Nodes Found:{' '}
                  <strong style={{ color: 'var(--color-success, #22c55e)' }}>
                    {data.solar_nodes_count}
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* Average Hours Stats */}
          {data && (data.avg_charging_hours_per_day !== null || data.avg_discharge_hours_per_day !== null) && (
            <div style={controlGroupStyle}>
              <div style={labelStyle}>Average Daily Cycle</div>
              <div
                style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
              >
                {data.avg_charging_hours_per_day !== null && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Charging Hours:</span>
                    <strong style={{ color: 'var(--color-success, #22c55e)' }}>
                      {data.avg_charging_hours_per_day.toFixed(1)} hrs/day
                    </strong>
                  </div>
                )}
                {data.avg_discharge_hours_per_day !== null && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Discharge Hours:</span>
                    <strong style={{ color: 'var(--color-error, #ef4444)' }}>
                      {data.avg_discharge_hours_per_day.toFixed(1)} hrs/day
                    </strong>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right side - Results */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-background)',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Identified Solar Nodes</h3>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            Nodes showing consistent battery/voltage rise during daylight and fall at night
          </p>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
          {!runAnalysis && !data && (
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
              <span style={{ fontSize: '2rem' }}>&#9728;</span>
              <span>Click "Identify Solar Nodes" to analyze</span>
            </div>
          )}

          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--color-text-muted)',
              }}
            >
              Analyzing telemetry data...
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

          {data && data.solar_nodes.length === 0 && (
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
              <span>No solar-powered nodes identified</span>
              <span style={{ fontSize: '0.875rem' }}>
                Try increasing the lookback period or ensure nodes have sufficient telemetry data.
              </span>
            </div>
          )}

          {data && data.solar_nodes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {data.solar_nodes.map((node) => (
                <SolarNodeCard key={node.node_num} node={node} solarProduction={data.solar_production} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SolarNodeCard({ node, solarProduction }: { node: SolarNode; solarProduction: SolarProductionPoint[] }) {
  const [expanded, setExpanded] = useState(false)

  // Merge node chart data with solar production data for combined chart
  const mergedChartData = useMemo(() => {
    if (!node.chart_data || node.chart_data.length === 0) return []

    // Create a map of solar production by hour
    const solarByHour = new Map<number, number>()
    solarProduction.forEach((sp) => {
      const hourTs = Math.floor(sp.timestamp / 3600000) * 3600000
      solarByHour.set(hourTs, sp.wattHours)
    })

    // Merge solar production into node chart data
    return node.chart_data.map((point) => {
      const hourTs = Math.floor(point.timestamp / 3600000) * 3600000
      return {
        ...point,
        solarWh: solarByHour.get(hourTs) ?? null,
      }
    })
  }, [node.chart_data, solarProduction])

  const hasSolarData = solarProduction.length > 0

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
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '1rem',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{node.node_name}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
            !{node.node_num.toString(16).padStart(8, '0')}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {node.avg_charge_rate_per_hour !== null && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-success, #22c55e)' }}>
                +{node.avg_charge_rate_per_hour.toFixed(2)}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                {node.metric_type === 'battery' ? '%' : 'V'}/hr charge
              </div>
            </div>
          )}
          {node.avg_discharge_rate_per_hour !== null && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-error, #ef4444)' }}>
                -{node.avg_discharge_rate_per_hour.toFixed(2)}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                {node.metric_type === 'battery' ? '%' : 'V'}/hr drain
              </div>
            </div>
          )}
          <div style={{ textAlign: 'right' }}>
            <div
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color:
                  node.solar_score >= 80
                    ? 'var(--color-success, #22c55e)'
                    : node.solar_score >= 60
                      ? 'var(--color-warning, #f59e0b)'
                      : 'var(--color-text)',
              }}
            >
              {node.solar_score}%
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Solar Score</div>
          </div>
          <div
            style={{
              fontSize: '0.8rem',
              color: 'var(--color-text-muted)',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
            }}
          >
            &#9660;
          </div>
        </div>
      </div>

      {expanded && (
        <div
          style={{
            padding: '1rem',
            borderTop: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
          }}
        >
          <div style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
            <strong>{node.days_with_pattern}</strong> of <strong>{node.days_analyzed}</strong> days
            showed solar charging pattern
            <span style={{ marginLeft: '1rem', color: 'var(--color-text-muted)' }}>
              (Metric: {node.metric_type === 'battery' ? 'Battery %' : 'Voltage V'})
            </span>
          </div>

          {/* Telemetry Chart */}
          {mergedChartData.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  marginBottom: '0.5rem',
                }}
              >
                {node.metric_type === 'battery' ? 'Battery Level' : 'Voltage'} {hasSolarData ? '& Solar Production' : ''} Over Time
              </div>
              <div style={{ height: '200px', background: 'var(--color-background)', borderRadius: '4px', padding: '0.5rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={mergedChartData} margin={{ top: 5, right: hasSolarData ? 50 : 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(ts) => {
                        const date = new Date(ts)
                        return `${(date.getMonth() + 1)}/${date.getDate()}`
                      }}
                      stroke="var(--color-text-muted)"
                      fontSize={10}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      yAxisId="left"
                      stroke="var(--color-text-muted)"
                      fontSize={10}
                      width={40}
                      domain={node.metric_type === 'battery' ? [0, 100] : ['auto', 'auto']}
                      tickFormatter={(v) => node.metric_type === 'battery' ? `${v}%` : `${v.toFixed(1)}V`}
                    />
                    {hasSolarData && (
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#f9e2af"
                        fontSize={10}
                        width={40}
                        tickFormatter={(v) => `${v}Wh`}
                      />
                    )}
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--color-bg-secondary)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '4px',
                        color: 'var(--color-text)',
                      }}
                      labelFormatter={(ts) => new Date(ts as number).toLocaleString()}
                      formatter={(value, name) => {
                        if (name === 'solarWh') {
                          return [`${(value as number).toFixed(0)} Wh`, 'Solar']
                        }
                        return [
                          node.metric_type === 'battery' ? `${value}%` : `${(value as number).toFixed(2)}V`,
                          node.metric_type === 'battery' ? 'Battery' : 'Voltage',
                        ]
                      }}
                    />
                    {/* Solar production background area */}
                    {hasSolarData && (
                      <Area
                        yAxisId="right"
                        type="monotone"
                        dataKey="solarWh"
                        fill="#f9e2af"
                        fillOpacity={0.3}
                        stroke="#f9e2af"
                        strokeOpacity={0.5}
                        strokeWidth={1}
                        connectNulls
                        isAnimationActive={false}
                      />
                    )}
                    {/* Battery/Voltage line */}
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="value"
                      stroke="#89b4fa"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {node.recent_patterns.length > 0 && (
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  marginBottom: '0.5rem',
                }}
              >
                Recent Patterns
              </div>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.8rem',
                }}
              >
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: 600 }}>Date</th>
                    <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: 600 }}>
                      Sunrise
                    </th>
                    <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: 600 }}>Peak</th>
                    <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: 600 }}>
                      Sunset
                    </th>
                    <th style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>Rise</th>
                    <th style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>Fall</th>
                    <th style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>Charge/hr</th>
                    <th style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>Drain/hr</th>
                  </tr>
                </thead>
                <tbody>
                  {node.recent_patterns.map((pattern, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '0.5rem' }}>{pattern.date}</td>
                      <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                        <span style={{ fontWeight: 500 }}>{pattern.sunrise.time}</span>
                        <br />
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                          {pattern.sunrise.value}%
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                        <span style={{ fontWeight: 500 }}>{pattern.peak.time}</span>
                        <br />
                        <span
                          style={{
                            fontSize: '0.7rem',
                            color: 'var(--color-success, #22c55e)',
                            fontWeight: 600,
                          }}
                        >
                          {pattern.peak.value}%
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                        <span style={{ fontWeight: 500 }}>{pattern.sunset.time}</span>
                        <br />
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                          {pattern.sunset.value}%
                        </span>
                      </td>
                      <td
                        style={{
                          padding: '0.5rem',
                          textAlign: 'right',
                          color: 'var(--color-success, #22c55e)',
                        }}
                      >
                        +{pattern.rise}
                      </td>
                      <td
                        style={{
                          padding: '0.5rem',
                          textAlign: 'right',
                          color: 'var(--color-error, #ef4444)',
                        }}
                      >
                        -{pattern.fall}
                      </td>
                      <td
                        style={{
                          padding: '0.5rem',
                          textAlign: 'right',
                          color: 'var(--color-success, #22c55e)',
                          fontWeight: 500,
                        }}
                      >
                        +{pattern.charge_rate_per_hour.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: '0.5rem',
                          textAlign: 'right',
                          color: 'var(--color-error, #ef4444)',
                          fontWeight: 500,
                        }}
                      >
                        {pattern.discharge_rate_per_hour !== null
                          ? `-${pattern.discharge_rate_per_hour.toFixed(2)}`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
