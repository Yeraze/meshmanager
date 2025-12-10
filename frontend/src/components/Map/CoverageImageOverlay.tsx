import { useEffect, useState, useRef } from 'react'
import { ImageOverlay } from 'react-leaflet'
import type { LatLngBounds } from 'leaflet'
import L from 'leaflet'

interface CoverageCell {
  south: number
  west: number
  north: number
  east: number
  count: number
}

interface CoverageImageOverlayProps {
  cells: CoverageCell[]
  blur?: number
}

// Get color for coverage count (returns [r, g, b, a])
function getCoverageRGBA(count: number): [number, number, number, number] {
  if (count <= 1) return [65, 105, 225, 180]    // Blue
  if (count <= 2) return [50, 205, 50, 180]     // Green
  if (count <= 3) return [255, 255, 0, 180]     // Yellow
  if (count <= 5) return [255, 165, 0, 200]     // Orange
  if (count <= 7) return [255, 69, 0, 200]      // Red-Orange
  if (count <= 9) return [255, 0, 0, 210]       // Red
  return [139, 0, 0, 210]                        // Dark Red
}

export default function CoverageImageOverlay({ cells, blur = 8 }: CoverageImageOverlayProps) {
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
      console.warn('Coverage grid too large or too small for image overlay')
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

      const [r, g, b, a] = getCoverageRGBA(cell.count)
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

    // Set bounds with small padding
    const latPadding = cellHeight * 0.5
    const lngPadding = cellWidth * 0.5
    setBounds(L.latLngBounds(
      [minLat - latPadding, minLng - lngPadding],
      [maxLat + latPadding, maxLng + lngPadding]
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
