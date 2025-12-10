import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

// Extend Leaflet types for heat layer
declare module 'leaflet' {
  function heatLayer(
    latlngs: Array<[number, number, number?]>,
    options?: {
      minOpacity?: number
      maxZoom?: number
      max?: number
      radius?: number
      blur?: number
      gradient?: Record<number, string>
    }
  ): L.Layer
}

interface HeatmapLayerProps {
  points: Array<{
    lat: number
    lng: number
    intensity: number
  }>
  radius?: number
  blur?: number
  maxZoom?: number
  max?: number
  minOpacity?: number
}

// Gradient matching our coverage color scale
const COVERAGE_GRADIENT = {
  0.0: 'rgba(65, 105, 225, 0.0)',   // Transparent at 0
  0.1: 'rgba(65, 105, 225, 0.6)',   // Royal Blue
  0.2: 'rgba(50, 205, 50, 0.7)',    // Lime Green
  0.3: 'rgba(255, 255, 0, 0.7)',    // Yellow
  0.5: 'rgba(255, 165, 0, 0.8)',    // Orange
  0.7: 'rgba(255, 69, 0, 0.8)',     // Red-Orange
  0.85: 'rgba(255, 0, 0, 0.9)',     // Red
  1.0: 'rgba(139, 0, 0, 0.9)',      // Dark Red
}

export default function HeatmapLayer({
  points,
  radius = 25,
  blur = 15,
  maxZoom = 18,
  max = 10,
  minOpacity = 0.4,
}: HeatmapLayerProps) {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) return

    // Convert points to heatmap format [lat, lng, intensity]
    const heatData: Array<[number, number, number]> = points.map(p => [
      p.lat,
      p.lng,
      p.intensity,
    ])

    // Create heat layer
    const heatLayer = L.heatLayer(heatData, {
      radius,
      blur,
      maxZoom,
      max,
      minOpacity,
      gradient: COVERAGE_GRADIENT,
    })

    heatLayer.addTo(map)

    // Cleanup on unmount or when points change
    return () => {
      map.removeLayer(heatLayer)
    }
  }, [map, points, radius, blur, maxZoom, max, minOpacity])

  return null
}
