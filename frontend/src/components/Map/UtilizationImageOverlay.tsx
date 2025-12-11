import { useEffect, useState, useRef } from 'react'
import { ImageOverlay } from 'react-leaflet'
import type { LatLngBounds } from 'leaflet'
import L from 'leaflet'

interface UtilizationCell {
  south: number
  west: number
  north: number
  east: number
  value: number
  color: string
}

interface UtilizationImageOverlayProps {
  cells: UtilizationCell[]
  blur?: number
}

// Get color for utilization value (0-100%), returns [r, g, b, a]
// <25% = Green, 25-50% = Orange, >50% = Red
function getUtilizationRGBA(value: number): [number, number, number, number] {
  if (value < 0) return [0, 0, 0, 0]           // Transparent
  if (value < 25) return [0, 128, 0, 150]      // Green (low utilization)
  if (value <= 50) return [255, 165, 0, 170]   // Orange (medium utilization)
  return [255, 0, 0, 190]                       // Red (high utilization)
}

export default function UtilizationImageOverlay({ cells, blur = 8 }: UtilizationImageOverlayProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [bounds, setBounds] = useState<LatLngBounds | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (!cells || cells.length === 0) {
      setImageUrl(null)
      setBounds(null)
      return
    }

    // Calculate grid bounds
    let minLat = Infinity, maxLat = -Infinity
    let minLng = Infinity, maxLng = -Infinity

    for (const cell of cells) {
      minLat = Math.min(minLat, cell.south)
      maxLat = Math.max(maxLat, cell.north)
      minLng = Math.min(minLng, cell.west)
      maxLng = Math.max(maxLng, cell.east)
    }

    // Calculate cell size (assuming uniform grid)
    const cellHeight = cells[0].north - cells[0].south
    const cellWidth = cells[0].east - cells[0].west

    // Calculate grid dimensions
    const numRows = Math.round((maxLat - minLat) / cellHeight)
    const numCols = Math.round((maxLng - minLng) / cellWidth)

    // Scale factor for higher resolution (pixels per cell)
    const scale = 4
    const canvasWidth = numCols * scale
    const canvasHeight = numRows * scale

    // Limit canvas size
    if (canvasWidth > 2000 || canvasHeight > 2000 || canvasWidth < 1 || canvasHeight < 1) {
      console.warn('Utilization grid too large or too small for image overlay')
      setImageUrl(null)
      return
    }

    // Create or reuse canvas
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas')
    }
    const canvas = canvasRef.current
    canvas.width = canvasWidth
    canvas.height = canvasHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas with transparency
    ctx.clearRect(0, 0, canvasWidth, canvasHeight)

    // Draw each cell
    for (const cell of cells) {
      const col = Math.round((cell.west - minLng) / cellWidth)
      const row = Math.round((maxLat - cell.north) / cellHeight) // Flip Y axis

      const [r, g, b, a] = getUtilizationRGBA(cell.value)
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a / 255})`
      ctx.fillRect(col * scale, row * scale, scale, scale)
    }

    // Apply blur filter for smoothing
    if (blur > 0) {
      ctx.filter = `blur(${blur}px)`
      ctx.drawImage(canvas, 0, 0)
      ctx.filter = 'none'
    }

    // Convert to data URL
    const dataUrl = canvas.toDataURL('image/png')
    setImageUrl(dataUrl)

    // Set bounds - shift south by half a cell to center cells on data points
    // (nodes are placed in cells based on their position, but cell extends north from there)
    const latOffset = cellHeight / 2
    setBounds(L.latLngBounds(
      [minLat - latOffset, minLng],
      [maxLat - latOffset, maxLng]
    ))

  }, [cells, blur])

  if (!imageUrl || !bounds) return null

  return (
    <ImageOverlay
      url={imageUrl}
      bounds={bounds}
      opacity={0.8}
      zIndex={100}
    />
  )
}
