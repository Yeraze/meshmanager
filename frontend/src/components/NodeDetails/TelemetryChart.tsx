import { useMemo } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TelemetryHistory } from '../../types/api'

// Catppuccin Mocha colors for the chart lines
const SOURCE_COLORS = [
  '#89b4fa', // Blue
  '#a6e3a1', // Green
  '#fab387', // Peach (skip yellow - used for solar)
  '#cba6f7', // Mauve
  '#f38ba8', // Red
  '#94e2d5', // Teal
  '#f5c2e7', // Pink
]

// Solar background color (Catppuccin Yellow)
const SOLAR_COLOR = '#f9e2af'

interface TelemetryChartProps {
  data: TelemetryHistory
  solarData?: Map<number, number>
}

export default function TelemetryChart({ data, solarData }: TelemetryChartProps) {
  // Transform data for recharts - group by timestamp and source
  const { chartData, sources, hasSolar } = useMemo(() => {
    // Get unique sources
    const sourceSet = new Set<string>()
    data.data.forEach((point) => {
      sourceSet.add(point.source_name || point.source_id)
    })
    const sources = Array.from(sourceSet)

    // Find the time range from telemetry data
    let minTime = Infinity
    let maxTime = -Infinity
    data.data.forEach((point) => {
      const timestamp = new Date(point.timestamp).getTime()
      minTime = Math.min(minTime, timestamp)
      maxTime = Math.max(maxTime, timestamp)
    })

    // Create hourly buckets for solar data (independent of telemetry gaps)
    const hasSolar = solarData && solarData.size > 0
    const timeMap = new Map<number, Record<string, number | null>>()

    if (hasSolar && minTime !== Infinity) {
      // Round to hour boundaries
      const startHour = Math.floor(minTime / 3600000) * 3600000
      const endHour = Math.ceil(maxTime / 3600000) * 3600000

      // Create hourly entries for solar
      for (let hour = startHour; hour <= endHour; hour += 3600000) {
        const solarValue = solarData.get(hour) ?? 0
        timeMap.set(hour, { timestamp: hour, solarEstimate: solarValue })
      }
    }

    // Add telemetry data on top of solar buckets
    data.data.forEach((point) => {
      const timestamp = new Date(point.timestamp).getTime()
      // Round to nearest minute for grouping
      const roundedTime = Math.round(timestamp / 60000) * 60000

      if (!timeMap.has(roundedTime)) {
        // No existing entry - create one with solar if available
        const hourTs = Math.round(roundedTime / 3600000) * 3600000
        const entry: Record<string, number | null> = { timestamp: roundedTime }
        if (hasSolar) {
          entry.solarEstimate = solarData.get(hourTs) ?? 0
        }
        timeMap.set(roundedTime, entry)
      }

      const entry = timeMap.get(roundedTime)!
      const sourceKey = point.source_name || point.source_id
      entry[sourceKey] = point.value
    })

    // Convert to array and sort by timestamp
    const chartData = Array.from(timeMap.values()).sort(
      (a, b) => (a.timestamp as number) - (b.timestamp as number)
    )

    return { chartData, sources, hasSolar }
  }, [data, solarData])

  if (chartData.length === 0) {
    return <div className="telemetry-chart-empty">No data available</div>
  }

  // Format timestamp for X axis
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Format tooltip value
  const formatValue = (value: number | null) => {
    if (value === null) return 'N/A'
    return value.toFixed(2)
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={chartData} margin={{ top: 5, right: hasSolar ? 50 : 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTime}
          stroke="var(--color-text-muted)"
          fontSize={10}
          interval="preserveStartEnd"
        />
        <YAxis
          yAxisId="left"
          stroke="var(--color-text-muted)"
          fontSize={10}
          width={40}
          tickFormatter={(v) => v.toFixed(1)}
        />
        {hasSolar && (
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke={SOLAR_COLOR}
            fontSize={10}
            width={40}
            tickFormatter={(v) => `${v}Wh`}
          />
        )}
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--color-bg-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-text)',
          }}
          labelFormatter={(timestamp) =>
            new Date(timestamp as number).toLocaleString()
          }
          formatter={(value, name) => {
            if (name === 'solarEstimate') {
              return [`${(value as number).toFixed(0)} Wh`, 'Solar']
            }
            return [formatValue(value as number | null), '']
          }}
        />
        {sources.length > 1 && (
          <Legend
            wrapperStyle={{ fontSize: '10px' }}
            iconSize={8}
          />
        )}
        {/* Solar background area - rendered first so it's behind the lines */}
        {hasSolar && (
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="solarEstimate"
            fill={SOLAR_COLOR}
            fillOpacity={0.3}
            stroke={SOLAR_COLOR}
            strokeOpacity={0.5}
            strokeWidth={1}
            connectNulls
            isAnimationActive={false}
          />
        )}
        {sources.map((source, index) => (
          <Line
            key={source}
            yAxisId="left"
            type="monotone"
            dataKey={source}
            name={source}
            stroke={SOURCE_COLORS[index % SOURCE_COLORS.length]}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
