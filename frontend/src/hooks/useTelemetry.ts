import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { fetchAvailableMetrics, fetchSolarData, fetchTelemetry, fetchTelemetryHistory } from '../services/api'

export function useTelemetry(nodeNum: number | undefined, hours?: number) {
  return useQuery({
    queryKey: ['telemetry', nodeNum, hours],
    queryFn: () => fetchTelemetry(nodeNum!, hours),
    enabled: nodeNum !== undefined,
  })
}

export function useTelemetryHistory(nodeNum: number | undefined, metric: string, hours?: number) {
  return useQuery({
    queryKey: ['telemetry-history', nodeNum, metric, hours],
    queryFn: () => fetchTelemetryHistory(nodeNum!, metric, hours),
    enabled: nodeNum !== undefined,
  })
}

export function useAvailableMetrics(nodeNum: number | undefined, hours?: number) {
  return useQuery({
    queryKey: ['available-metrics', nodeNum, hours],
    queryFn: () => fetchAvailableMetrics(nodeNum!, hours),
    enabled: nodeNum !== undefined,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useSolarData(hours?: number) {
  const query = useQuery({
    queryKey: ['solar-data', hours],
    queryFn: () => fetchSolarData(hours),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Convert to Map<number, number> for efficient lookup (like MeshMonitor)
  const solarMap = useMemo(() => {
    const map = new Map<number, number>()
    if (query.data) {
      for (const point of query.data) {
        map.set(point.timestamp, point.wattHours)
      }
    }
    return map
  }, [query.data])

  return {
    ...query,
    solarMap,
  }
}
