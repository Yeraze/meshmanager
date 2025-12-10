import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

interface HeatmapLayerProps {
  points: Array<{ lat: number; lng: number }>
  radius?: number
  blur?: number
  maxZoom?: number
  max?: number
  minOpacity?: number
}

// Extend L to include heatLayer
declare module 'leaflet' {
  function heatLayer(
    latlngs: Array<[number, number] | [number, number, number]>,
    options?: {
      radius?: number
      blur?: number
      maxZoom?: number
      max?: number
      minOpacity?: number
      gradient?: Record<number, string>
    }
  ): L.Layer
}

export default function HeatmapLayer({
  points,
  radius = 25,
  blur = 15,
  maxZoom = 18,
  max = 1.0,
  minOpacity = 0.4,
}: HeatmapLayerProps) {
  const map = useMap()
  const heatLayerRef = useRef<L.Layer | null>(null)

  useEffect(() => {
    if (!points || points.length === 0) {
      // Remove existing layer if no points
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current)
        heatLayerRef.current = null
      }
      return
    }

    // Convert points to format expected by leaflet.heat
    // Each point is [lat, lng, intensity] - intensity defaults to 1
    const heatData: Array<[number, number, number]> = points.map(p => [p.lat, p.lng, 1])

    // Remove existing layer
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current)
    }

    // Create new heat layer with density-based gradient
    const heatLayer = L.heatLayer(heatData, {
      radius,
      blur,
      maxZoom,
      max,
      minOpacity,
      // Classic density heatmap gradient (blue -> green -> yellow -> red)
      gradient: {
        0.0: 'blue',
        0.25: 'cyan',
        0.5: 'lime',
        0.75: 'yellow',
        1.0: 'red',
      },
    })

    heatLayer.addTo(map)
    heatLayerRef.current = heatLayer

    // Cleanup
    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current)
        heatLayerRef.current = null
      }
    }
  }, [points, map, radius, blur, maxZoom, max, minOpacity])

  return null
}
