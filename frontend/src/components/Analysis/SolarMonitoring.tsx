import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  fetchSolarNodesAnalysis,
  fetchSolarForecastAnalysis,
  getSolarScheduleSettings,
  updateSolarScheduleSettings,
  testSolarNotification,
  type SolarNode,
  type SolarProductionPoint,
  type SolarForecastAnalysis,
  type SolarScheduleSettings,
} from '../../services/api'

export default function SolarMonitoring() {
  const [lookbackDays, setLookbackDays] = useState(7)
  const [runAnalysis, setRunAnalysis] = useState(false)
  const [runForecast, setRunForecast] = useState(false)
  const [scheduleExpanded, setScheduleExpanded] = useState(false)
  const [testStatus, setTestStatus] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['solar-nodes-analysis', lookbackDays],
    queryFn: () => fetchSolarNodesAnalysis(lookbackDays),
    enabled: runAnalysis,
  })

  const {
    data: forecastData,
    isLoading: isForecastLoading,
    error: forecastError,
    refetch: refetchForecast,
  } = useQuery({
    queryKey: ['solar-forecast-analysis', lookbackDays],
    queryFn: () => fetchSolarForecastAnalysis(lookbackDays),
    enabled: runForecast,
  })

  // Schedule settings query
  const { data: scheduleSettings } = useQuery({
    queryKey: ['solar-schedule-settings'],
    queryFn: getSolarScheduleSettings,
  })

  // Schedule settings mutation
  const updateScheduleMutation = useMutation({
    mutationFn: updateSolarScheduleSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['solar-schedule-settings'] })
    },
  })

  // Test notification mutation
  const testNotificationMutation = useMutation({
    mutationFn: testSolarNotification,
    onSuccess: () => {
      setTestStatus('Notification sent successfully!')
      setTimeout(() => setTestStatus(null), 3000)
    },
    onError: (error: Error) => {
      setTestStatus(`Failed: ${error.message}`)
      setTimeout(() => setTestStatus(null), 5000)
    },
  })

  const handleAnalyze = () => {
    setRunAnalysis(true)
    refetch()
  }

  const handleForecast = () => {
    setRunForecast(true)
    refetchForecast()
  }

  // Helper functions for schedule settings
  const updateSettings = (updates: Partial<SolarScheduleSettings>) => {
    if (!scheduleSettings) return
    updateScheduleMutation.mutate({ ...scheduleSettings, ...updates })
  }

  const addScheduleTime = () => {
    if (!scheduleSettings) return
    updateSettings({ schedules: [...scheduleSettings.schedules, '08:00'] })
  }

  const removeScheduleTime = (index: number) => {
    if (!scheduleSettings) return
    const newSchedules = scheduleSettings.schedules.filter((_, i) => i !== index)
    updateSettings({ schedules: newSchedules })
  }

  const updateScheduleTime = (index: number, value: string) => {
    if (!scheduleSettings) return
    const newSchedules = [...scheduleSettings.schedules]
    newSchedules[index] = value
    updateSettings({ schedules: newSchedules })
  }

  const addAppriseUrl = () => {
    if (!scheduleSettings) return
    // Add a placeholder that user will edit - backend filters empty strings
    updateSettings({ apprise_urls: [...scheduleSettings.apprise_urls, 'apprise://new'] })
  }

  const removeAppriseUrl = (index: number) => {
    if (!scheduleSettings) return
    const newUrls = scheduleSettings.apprise_urls.filter((_, i) => i !== index)
    updateSettings({ apprise_urls: newUrls })
  }

  const updateAppriseUrl = (index: number, value: string) => {
    if (!scheduleSettings) return
    const newUrls = [...scheduleSettings.apprise_urls]
    newUrls[index] = value
    updateSettings({ apprise_urls: newUrls })
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

          {/* Analysis Buttons */}
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
                marginBottom: '0.5rem',
              }}
            >
              {isLoading ? 'Analyzing...' : 'Identify Solar Nodes'}
            </button>
            <button
              onClick={handleForecast}
              disabled={isForecastLoading}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'var(--color-warning, #f59e0b)',
                color: '#000',
                cursor: isForecastLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                opacity: isForecastLoading ? 0.7 : 1,
              }}
            >
              {isForecastLoading ? 'Analyzing...' : 'Forecast Analysis'}
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

          {/* Forecast Summary */}
          {forecastData && (
            <div style={controlGroupStyle}>
              <div style={labelStyle}>Forecast Summary</div>
              <div
                style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
              >
                {forecastData.low_output_warning && (
                  <div
                    style={{
                      background: 'var(--color-error, #ef4444)',
                      color: 'white',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      fontWeight: 600,
                      textAlign: 'center',
                      marginBottom: '0.5rem',
                    }}
                  >
                    Low Solar Output Forecast
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Avg Historical:</span>
                  <strong>{forecastData.avg_historical_daily_wh.toLocaleString()} Wh/day</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Forecast Days:</span>
                  <strong>{forecastData.forecast_days.length}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Nodes at Risk:</span>
                  <strong
                    style={{
                      color:
                        forecastData.nodes_at_risk_count > 0
                          ? 'var(--color-error, #ef4444)'
                          : 'var(--color-success, #22c55e)',
                    }}
                  >
                    {forecastData.nodes_at_risk_count}
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* Scheduled Analysis Section */}
          <div
            style={{
              borderTop: '1px solid var(--color-border)',
              paddingTop: '1rem',
              marginTop: '1rem',
            }}
          >
            <div
              style={{
                ...labelStyle,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                userSelect: 'none',
              }}
              onClick={() => setScheduleExpanded(!scheduleExpanded)}
            >
              <span style={{ marginRight: '0.5rem', fontSize: '0.7rem' }}>
                {scheduleExpanded ? '▼' : '▶'}
              </span>
              SCHEDULED ANALYSIS
            </div>

            {scheduleExpanded && scheduleSettings && (
              <div style={{ marginTop: '0.75rem' }}>
                {/* Enable toggle */}
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    marginBottom: '1rem',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={scheduleSettings.enabled}
                    onChange={(e) => updateSettings({ enabled: e.target.checked })}
                    style={{ marginRight: '0.5rem' }}
                  />
                  <span style={{ fontSize: '0.85rem' }}>Enable scheduled analysis</span>
                </label>

                {/* Lookback days for schedule */}
                <div style={controlGroupStyle}>
                  <div style={labelStyle}>Analysis Lookback (Days)</div>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    value={scheduleSettings.lookback_days}
                    onChange={(e) =>
                      updateSettings({ lookback_days: parseInt(e.target.value) || 7 })
                    }
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

                {/* Schedule times */}
                <div style={controlGroupStyle}>
                  <div style={labelStyle}>Schedule Times</div>
                  {scheduleSettings.schedules.map((time, i) => (
                    <div
                      key={i}
                      style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}
                    >
                      <input
                        type="time"
                        value={time}
                        onChange={(e) => updateScheduleTime(i, e.target.value)}
                        style={{
                          flex: 1,
                          padding: '0.4rem',
                          borderRadius: '4px',
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-background)',
                          color: 'var(--color-text)',
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => removeScheduleTime(i)}
                        style={{
                          padding: '0.4rem 0.6rem',
                          borderRadius: '4px',
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-background)',
                          color: 'var(--color-text)',
                          cursor: 'pointer',
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={addScheduleTime}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px dashed var(--color-border)',
                      background: 'transparent',
                      color: 'var(--color-text-muted)',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                    }}
                  >
                    + Add Time
                  </button>
                </div>

                {/* Apprise URLs */}
                <div style={controlGroupStyle}>
                  <div style={labelStyle}>Notification URLs (Apprise)</div>
                  {scheduleSettings.apprise_urls.map((url, i) => (
                    <div
                      key={i}
                      style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}
                    >
                      <input
                        type="text"
                        value={url}
                        placeholder="discord://... or slack://..."
                        onChange={(e) => updateAppriseUrl(i, e.target.value)}
                        style={{
                          flex: 1,
                          padding: '0.4rem',
                          borderRadius: '4px',
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-background)',
                          color: 'var(--color-text)',
                          fontSize: '0.8rem',
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => removeAppriseUrl(i)}
                        style={{
                          padding: '0.4rem 0.6rem',
                          borderRadius: '4px',
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-background)',
                          color: 'var(--color-text)',
                          cursor: 'pointer',
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={addAppriseUrl}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px dashed var(--color-border)',
                      background: 'transparent',
                      color: 'var(--color-text-muted)',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                    }}
                  >
                    + Add URL
                  </button>
                </div>

                {/* Test button */}
                <button
                  onClick={() => testNotificationMutation.mutate()}
                  disabled={
                    testNotificationMutation.isPending ||
                    scheduleSettings.apprise_urls.length === 0
                  }
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: 'none',
                    background: 'var(--color-primary)',
                    color: 'white',
                    cursor:
                      testNotificationMutation.isPending ||
                      scheduleSettings.apprise_urls.length === 0
                        ? 'not-allowed'
                        : 'pointer',
                    opacity:
                      testNotificationMutation.isPending ||
                      scheduleSettings.apprise_urls.length === 0
                        ? 0.6
                        : 1,
                    fontSize: '0.85rem',
                  }}
                >
                  {testNotificationMutation.isPending
                    ? 'Sending...'
                    : 'Test Notification'}
                </button>

                {/* Test status message */}
                {testStatus && (
                  <div
                    style={{
                      marginTop: '0.5rem',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      background: testStatus.startsWith('Failed')
                        ? 'var(--color-error, #ef4444)'
                        : 'var(--color-success, #22c55e)',
                      color: 'white',
                      textAlign: 'center',
                    }}
                  >
                    {testStatus}
                  </div>
                )}
              </div>
            )}
          </div>
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

          {/* Forecast Analysis Results - shown at top */}
          {isForecastLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem',
                color: 'var(--color-text-muted)',
              }}
            >
              Analyzing solar forecast...
            </div>
          )}

          {forecastError && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem',
                color: 'var(--color-error, #ef4444)',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <span>Error analyzing forecast</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                {(forecastError as Error).message}
              </span>
            </div>
          )}

          {forecastData && data && (
            <ForecastResults data={forecastData} solarProduction={data.solar_production} />
          )}

          {data && data.solar_nodes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {data.solar_nodes.map((node) => (
                <SolarNodeCard
                  key={node.node_num}
                  node={node}
                  solarProduction={data.solar_production}
                  forecastData={forecastData}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SolarNodeCard({
  node,
  solarProduction,
  forecastData,
}: {
  node: SolarNode
  solarProduction: SolarProductionPoint[]
  forecastData?: SolarForecastAnalysis
}) {
  const [expanded, setExpanded] = useState(false)

  // Find forecast simulation for this node (from solar_simulations, which includes all solar nodes)
  const nodeForecast = forecastData?.solar_simulations?.find((n) => n.node_num === node.node_num)

  // Check if this node is at risk (min simulated battery drops below 50%)
  const isAtRisk = forecastData?.nodes_at_risk?.some((n) => n.node_num === node.node_num)
  const atRiskData = forecastData?.nodes_at_risk?.find((n) => n.node_num === node.node_num)

  // Merge node chart data with solar production and forecast simulation data
  const mergedChartData = useMemo(() => {
    if (!node.chart_data || node.chart_data.length === 0) return []

    // Create a map of solar production by hour
    const solarByHour = new Map<number, number>()
    solarProduction.forEach((sp) => {
      const hourTs = Math.floor(sp.timestamp / 3600000) * 3600000
      solarByHour.set(hourTs, sp.wattHours)
    })

    // Note: We now use the actual hourly solar data from solarByHour for forecast points
    // instead of the daily forecast totals. The solarProduction data from the API
    // includes both historical and future forecast data from MeshMonitor/Forecast.Solar.

    // Merge solar production into node chart data (historical data only, no forecast here)
    const chartData = node.chart_data.map((point) => {
      const hourTs = Math.floor(point.timestamp / 3600000) * 3600000
      return {
        ...point,
        solarWh: solarByHour.get(hourTs) ?? null,
        forecastBattery: null as number | null,
        forecastSolarWh: null as number | null,
      }
    })

    // Get the first and last timestamps to determine the chart range
    const firstTimestamp = chartData.length > 0 ? chartData[0].timestamp : 0
    const lastTimestamp = chartData.length > 0 ? chartData[chartData.length - 1].timestamp : 0
    const lastValue = chartData.length > 0 ? chartData[chartData.length - 1].value : 0

    // Add ALL hourly solar data points that aren't already in the chart
    // This ensures we show the complete solar curve even when telemetry has gaps
    const telemetryHours = new Set(chartData.map(p => Math.floor(p.timestamp / 3600000) * 3600000))
    solarByHour.forEach((wh, hourTs) => {
      // Add historical solar points that don't have corresponding telemetry
      if (!telemetryHours.has(hourTs) && hourTs >= firstTimestamp && hourTs <= lastTimestamp) {
        chartData.push({
          timestamp: hourTs,
          value: null as unknown as number,
          solarWh: wh,
          forecastBattery: null,
          forecastSolarWh: null,
        })
      }
    })

    // Get the last point info for adding forecast/future data
    if (chartData.length > 0) {
      // Add forecast simulation as FUTURE points extending from the end of the chart
      if (nodeForecast?.simulation && nodeForecast.simulation.length > 0) {
        // Add a bridge point at the last actual value to connect forecast to historical data
        // This creates continuity between the actual battery line and forecast line
        chartData.push({
          timestamp: lastTimestamp + 1, // Just after last actual point
          value: null as unknown as number,
          solarWh: null,
          forecastBattery: lastValue, // Start forecast from last known value
          forecastSolarWh: null,
        })

        // Add forecast points - now includes sunrise/peak/sunset cycle points per day
        // Only include points AFTER the last historical data point
        nodeForecast.simulation.forEach((sim) => {
          // Parse the timestamp directly (format: "YYYY-MM-DDTHH:MM:SSZ")
          const forecastTimestamp = new Date(sim.timestamp).getTime()

          // Only add forecast points that are after the last historical data
          if (forecastTimestamp > lastTimestamp) {
            // Get the hourly solar forecast from solarByHour (which includes future forecast data)
            const hourTs = Math.floor(forecastTimestamp / 3600000) * 3600000
            const forecastSolar = solarByHour.get(hourTs) ?? null

            chartData.push({
              timestamp: forecastTimestamp,
              value: null as unknown as number,
              solarWh: null,
              forecastBattery: sim.simulated_battery,
              forecastSolarWh: forecastSolar,
            })
          }
        })
      }

      // Always add future hourly solar forecast points (independent of battery forecast)
      // This shows the solar curve even when battery simulation isn't available
      const addedTimestamps = new Set(chartData.map(p => Math.floor(p.timestamp / 3600000) * 3600000))
      solarByHour.forEach((wh, hourTs) => {
        // Only add future hours that aren't already in the chart
        if (hourTs > lastTimestamp && !addedTimestamps.has(hourTs)) {
          chartData.push({
            timestamp: hourTs,
            value: null as unknown as number,
            solarWh: null,
            forecastBattery: null,
            forecastSolarWh: wh,
          })
        }
      })
    }

    // Sort by timestamp to ensure proper chart rendering
    chartData.sort((a, b) => a.timestamp - b.timestamp)

    return chartData
  }, [node.chart_data, solarProduction, nodeForecast])

  const hasSolarData = solarProduction.length > 0
  const hasForecastData = nodeForecast?.simulation && nodeForecast.simulation.length > 0

  return (
    <div
      style={{
        background: 'var(--color-background)',
        border: isAtRisk ? '2px solid var(--color-error, #ef4444)' : '1px solid var(--color-border)',
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
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {node.node_name}
            {isAtRisk && (
              <span
                title={`Forecast shows battery dropping to ${atRiskData?.min_simulated_battery}%`}
                style={{
                  background: 'var(--color-error, #ef4444)',
                  color: 'white',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.4rem',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                }}
              >
                At Risk
              </span>
            )}
            {node.insufficient_solar && (
              <span
                title="Insufficient solar output: charge rate does not sufficiently exceed discharge rate"
                style={{
                  background: 'var(--color-warning, #f59e0b)',
                  color: '#000',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.4rem',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                }}
              >
                Low Solar
              </span>
            )}
          </div>
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
                {node.metric_type === 'battery' ? 'Battery Level' : 'Voltage'}{hasSolarData ? ' & Solar Production' : ''}{hasForecastData ? ' & Forecast' : ''} Over Time
              </div>
              <div style={{ height: '200px', background: 'var(--color-background)', borderRadius: '4px', padding: '0.5rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={mergedChartData} margin={{ top: 5, right: hasSolarData ? 50 : 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="timestamp"
                      type="number"
                      scale="time"
                      domain={['dataMin', 'dataMax']}
                      tickFormatter={(ts) => {
                        const date = new Date(ts)
                        return `${(date.getMonth() + 1)}/${date.getDate()}`
                      }}
                      stroke="var(--color-text-muted)"
                      fontSize={10}
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
                        if (name === 'forecastSolarWh') {
                          return [`${(value as number).toFixed(0)} Wh`, 'Forecast Solar']
                        }
                        if (name === 'forecastBattery') {
                          return [
                            node.metric_type === 'battery' ? `${value}%` : `${(value as number).toFixed(2)}V`,
                            node.metric_type === 'battery' ? 'Forecast Battery' : 'Forecast Voltage',
                          ]
                        }
                        if (name === 'value') {
                          return [
                            node.metric_type === 'battery' ? `${value}%` : `${(value as number).toFixed(2)}V`,
                            node.metric_type === 'battery' ? 'Battery' : 'Voltage',
                          ]
                        }
                        return [value, name]
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
                    {/* Forecast solar production - dashed yellow area */}
                    {hasForecastData && hasSolarData && (
                      <Area
                        yAxisId="right"
                        type="monotone"
                        dataKey="forecastSolarWh"
                        fill="#f9e2af"
                        fillOpacity={0.15}
                        stroke="#f9e2af"
                        strokeOpacity={0.8}
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        connectNulls
                        isAnimationActive={false}
                      />
                    )}
                    {/* Forecast battery line - dashed orange for visibility */}
                    {/* Only show for battery nodes - voltage/INA forecasts use battery % which doesn't match chart scale */}
                    {hasForecastData && node.metric_type === 'battery' && (
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="forecastBattery"
                        stroke="#f97316"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={{ fill: '#f97316', r: 3 }}
                        connectNulls
                        isAnimationActive={false}
                      />
                    )}
                    {/* Warning line at risk threshold (40% for battery) */}
                    {hasForecastData && node.metric_type === 'battery' && (
                      <ReferenceLine
                        yAxisId="left"
                        y={40}
                        stroke="#ef4444"
                        strokeDasharray="3 3"
                      />
                    )}
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

function ForecastResults({ data, solarProduction }: { data: SolarForecastAnalysis; solarProduction: SolarProductionPoint[] }) {
  // Aggregate hourly solar production into daily totals
  const chartData = useMemo(() => {
    // Get today's date string for comparison (in local timezone)
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    // Group hourly data by date (YYYY-MM-DD)
    const dailyTotals = new Map<string, number>()

    solarProduction.forEach((point) => {
      const date = new Date(point.timestamp)
      const dateStr = date.toISOString().split('T')[0]
      dailyTotals.set(dateStr, (dailyTotals.get(dateStr) || 0) + point.wattHours)
    })

    // Create forecast map for quick lookup
    const forecastByDate = new Map(data.forecast_days.map((d) => [d.date, d.forecast_wh]))

    // Build combined chart data: actual (past) + forecast (future)
    // For today, show both actual and forecast
    const combined: Array<{
      date: string
      historical_wh: number | null
      forecast_wh: number | null
      avg_historical_wh: number
    }> = []

    // Collect all unique dates from both sources
    const allDates = new Set([
      ...Array.from(dailyTotals.keys()),
      ...data.forecast_days.map((d) => d.date),
    ])

    // Add data for each date
    // - Past dates: only show actual (historical_wh)
    // - Future dates: only show forecast (forecast_wh)
    // - Today: show both if available
    Array.from(allDates)
      .sort()
      .forEach((date) => {
        const rawTotal = dailyTotals.get(date)
        const forecastWh = forecastByDate.get(date)
        const isFuture = date > todayStr
        const isToday = date === todayStr

        combined.push({
          date,
          // Only show actual data for today and past dates
          historical_wh: (!isFuture && rawTotal !== undefined) ? Math.round(rawTotal) : null,
          // Only show forecast for today and future dates
          forecast_wh: ((isToday || isFuture) && forecastWh !== undefined) ? forecastWh : null,
          avg_historical_wh: data.avg_historical_daily_wh,
        })
      })

    // Sort by date
    combined.sort((a, b) => a.date.localeCompare(b.date))

    return combined
  }, [solarProduction, data.forecast_days, data.avg_historical_daily_wh])

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      {/* Section Header */}
      <div
        style={{
          padding: '1rem',
          background: 'var(--color-background)',
          borderRadius: '8px 8px 0 0',
          border: '1px solid var(--color-border)',
          borderBottom: 'none',
        }}
      >
        <h4 style={{ margin: 0, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Forecast Analysis
          {data.low_output_warning && (
            <span
              style={{
                background: 'var(--color-error, #ef4444)',
                color: 'white',
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.15rem 0.4rem',
                borderRadius: '4px',
                textTransform: 'uppercase',
              }}
            >
              Low Output Warning
            </span>
          )}
          {data.nodes_at_risk_count > 0 && (
            <span
              style={{
                background: 'var(--color-error, #ef4444)',
                color: 'white',
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.15rem 0.4rem',
                borderRadius: '4px',
                textTransform: 'uppercase',
              }}
            >
              {data.nodes_at_risk_count} Node{data.nodes_at_risk_count > 1 ? 's' : ''} at Risk
            </span>
          )}
        </h4>
        <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          {data.historical_days_analyzed} days of historical data (avg {data.avg_historical_daily_wh.toLocaleString()} Wh/day)
          {data.forecast_days.length > 0 && ` + ${data.forecast_days.length} day forecast`}
        </p>
      </div>

      {/* Combined Historical + Forecast Chart */}
      {chartData.length > 0 && (
        <div
          style={{
            padding: '1rem',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: data.nodes_at_risk.length === 0 && data.forecast_days.length === 0 ? '0 0 8px 8px' : undefined,
          }}
        >
          <div
            style={{
              fontSize: '0.75rem',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              marginBottom: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
            }}
          >
            <span>Daily Solar Production</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: 12, height: 12, background: '#89b4fa', borderRadius: 2 }} />
              Actual
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: 12, height: 12, background: '#f9e2af', borderRadius: 2 }} />
              Forecast
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: 12, height: 2, background: '#a6adc8', borderRadius: 1 }} />
              Average
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: 12, height: 2, background: '#ef4444', borderRadius: 1 }} />
              75% Warning
            </span>
          </div>
          <div style={{ height: '200px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(date) => {
                    // Parse YYYY-MM-DD directly to avoid timezone issues
                    const parts = (date as string).split('-')
                    return `${parseInt(parts[1])}/${parseInt(parts[2])}`
                  }}
                  stroke="var(--color-text-muted)"
                  fontSize={10}
                  interval="preserveStartEnd"
                />
                <YAxis stroke="var(--color-text-muted)" fontSize={10} width={60} tickFormatter={(v) => `${v.toLocaleString()}`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-bg-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '4px',
                    color: 'var(--color-text)',
                  }}
                  labelFormatter={(date) => {
                    // Parse YYYY-MM-DD directly to avoid timezone issues
                    const parts = (date as string).split('-')
                    return `${parseInt(parts[1])}/${parseInt(parts[2])}/${parts[0]}`
                  }}
                  formatter={(value, name) => {
                    if (name === 'historical_wh') return [`${(value as number).toLocaleString()} Wh`, 'Actual']
                    if (name === 'forecast_wh') return [`${(value as number).toLocaleString()} Wh`, 'Forecast']
                    if (name === 'avg_historical_wh') return [`${(value as number).toLocaleString()} Wh`, 'Average']
                    return [value, name]
                  }}
                />
                {/* 75% warning line */}
                <ReferenceLine y={data.avg_historical_daily_wh * 0.75} stroke="#ef4444" strokeDasharray="5 5" label={{ value: '75%', fill: '#ef4444', fontSize: 10 }} />
                {/* Historical bars (blue) */}
                <Bar dataKey="historical_wh" fill="#89b4fa" name="Actual" />
                {/* Forecast bars (yellow) */}
                <Bar dataKey="forecast_wh" fill="#f9e2af" name="Forecast" />
                {/* Average line */}
                <Line type="monotone" dataKey="avg_historical_wh" stroke="#a6adc8" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Average" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {chartData.length === 0 && (
        <div
          style={{
            padding: '2rem',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            textAlign: 'center',
            color: 'var(--color-text-muted)',
            borderRadius: '0 0 8px 8px',
          }}
        >
          No solar production data available.
        </div>
      )}

      {/* Nodes at Risk Summary */}
      {data.nodes_at_risk.length > 0 && (
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
          }}
        >
          <span style={{ color: 'var(--color-error, #ef4444)', fontWeight: 600 }}>
            {data.nodes_at_risk.length} node{data.nodes_at_risk.length > 1 ? 's' : ''} predicted to drop below 50% battery:
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>
            {data.nodes_at_risk.map((n) => n.node_name).join(', ')}
          </span>
        </div>
      )}

      {data.nodes_at_risk.length === 0 && data.forecast_days.length > 0 && (
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            textAlign: 'center',
          }}
        >
          <span style={{ color: 'var(--color-success, #22c55e)', fontWeight: 600 }}>
            No nodes predicted to drop below 50% battery during forecast period
          </span>
        </div>
      )}
    </div>
  )
}
