import { useState, useMemo, useCallback } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, Rectangle, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { fetchNodes, fetchPositionHistory } from '../../services/api'
import { getTilesetById, DEFAULT_TILESET_ID } from '../../config/tilesets'
import 'leaflet/dist/leaflet.css'

interface CoverageMapModalProps {
  isOpen: boolean
  onClose: () => void
}

interface GridCell {
  bounds: L.LatLngBoundsLiteral
  count: number
  color: string
}

interface PositionPoint {
  latitude: number
  longitude: number
}

type UnitType = 'miles' | 'kilometers'

// Constants for coordinate conversion
const KM_PER_DEGREE_LAT = 111.0 // km per degree of latitude (roughly constant)
const MILES_TO_KM = 1.60934

// Color scale for heatmap (from cool to hot)
const COLORS = [
  'rgba(65, 105, 225, 0.4)',   // 1 - Royal Blue
  'rgba(50, 205, 50, 0.5)',    // 2 - Lime Green
  'rgba(255, 255, 0, 0.5)',    // 3 - Yellow
  'rgba(255, 165, 0, 0.6)',    // 4-5 - Orange
  'rgba(255, 69, 0, 0.6)',     // 6-7 - Red-Orange
  'rgba(255, 0, 0, 0.7)',      // 8-9 - Red
  'rgba(139, 0, 0, 0.8)',      // 10+ - Dark Red
]

function getColorForCount(count: number): string {
  if (count <= 0) return 'transparent'
  if (count === 1) return COLORS[0]
  if (count === 2) return COLORS[1]
  if (count === 3) return COLORS[2]
  if (count <= 5) return COLORS[3]
  if (count <= 7) return COLORS[4]
  if (count <= 9) return COLORS[5]
  return COLORS[6]
}

// Component to fit map bounds to positions
function MapBoundsFitter({ positions }: { positions: PositionPoint[] }) {
  const map = useMap()

  useMemo(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(
        positions.map(p => [p.latitude, p.longitude])
      )
      // Add some padding
      map.fitBounds(bounds.pad(0.1))
    }
  }, [positions, map])

  return null
}

export default function CoverageMapModal({ isOpen, onClose }: CoverageMapModalProps) {
  const [unit, setUnit] = useState<UnitType>('miles')
  const [resolution, setResolution] = useState(1)
  const [lookbackDays, setLookbackDays] = useState(7)
  const [showGrid, setShowGrid] = useState(false)

  const tileset = getTilesetById(DEFAULT_TILESET_ID)

  // Fetch position history
  const { data: positionHistory = [], isLoading: loadingHistory } = useQuery({
    queryKey: ['position-history', lookbackDays],
    queryFn: () => fetchPositionHistory(lookbackDays),
    enabled: showGrid && isOpen,
  })

  // Fallback: fetch nodes with current positions
  const { data: nodes = [], isLoading: loadingNodes } = useQuery({
    queryKey: ['nodes', 'coverage', lookbackDays],
    queryFn: () => fetchNodes({ activeOnly: true, activeHours: lookbackDays * 24 }),
    enabled: showGrid && isOpen,
  })

  const isLoading = loadingHistory || loadingNodes

  // Combine position history with current node positions
  const allPositions = useMemo((): PositionPoint[] => {
    const positions: PositionPoint[] = []

    // Add historical positions
    for (const pos of positionHistory) {
      if (pos.latitude != null && pos.longitude != null) {
        positions.push({ latitude: pos.latitude, longitude: pos.longitude })
      }
    }

    // Add current node positions (only if we don't have historical data)
    // Or always include current positions as additional data points
    for (const node of nodes) {
      if (node.latitude != null && node.longitude != null) {
        positions.push({ latitude: node.latitude, longitude: node.longitude })
      }
    }

    return positions
  }, [positionHistory, nodes])

  // Calculate the grid
  const gridCells = useMemo((): GridCell[] => {
    if (!showGrid || allPositions.length === 0) return []

    // Calculate cell size in degrees
    const cellSizeKm = unit === 'miles' ? resolution * MILES_TO_KM : resolution
    const cellSizeLat = cellSizeKm / KM_PER_DEGREE_LAT

    // Find bounds
    const lats = allPositions.map(p => p.latitude)
    const lngs = allPositions.map(p => p.longitude)
    const minLat = Math.min(...lats)
    const maxLat = Math.max(...lats)
    const minLng = Math.min(...lngs)
    const maxLng = Math.max(...lngs)

    // Calculate center latitude for longitude conversion
    const centerLat = (minLat + maxLat) / 2
    const kmPerDegreeLng = KM_PER_DEGREE_LAT * Math.cos(centerLat * Math.PI / 180)
    const cellSizeLng = cellSizeKm / kmPerDegreeLng

    // Expand bounds to full grid cells
    const gridMinLat = Math.floor(minLat / cellSizeLat) * cellSizeLat
    const gridMaxLat = Math.ceil(maxLat / cellSizeLat) * cellSizeLat
    const gridMinLng = Math.floor(minLng / cellSizeLng) * cellSizeLng
    const gridMaxLng = Math.ceil(maxLng / cellSizeLng) * cellSizeLng

    // Count positions in each cell
    const cellCounts = new Map<string, number>()

    for (const pos of allPositions) {
      const cellRow = Math.floor((pos.latitude - gridMinLat) / cellSizeLat)
      const cellCol = Math.floor((pos.longitude - gridMinLng) / cellSizeLng)
      const key = `${cellRow},${cellCol}`
      cellCounts.set(key, (cellCounts.get(key) || 0) + 1)
    }

    // Create grid cells
    const cells: GridCell[] = []
    const numRows = Math.ceil((gridMaxLat - gridMinLat) / cellSizeLat)
    const numCols = Math.ceil((gridMaxLng - gridMinLng) / cellSizeLng)

    // Limit grid size to prevent performance issues
    if (numRows * numCols > 10000) {
      console.warn('Grid too large, skipping rendering')
      return []
    }

    for (let row = 0; row < numRows; row++) {
      for (let col = 0; col < numCols; col++) {
        const key = `${row},${col}`
        const count = Math.min(cellCounts.get(key) || 0, 10) // Cap at 10

        if (count > 0) {
          const south = gridMinLat + row * cellSizeLat
          const north = south + cellSizeLat
          const west = gridMinLng + col * cellSizeLng
          const east = west + cellSizeLng

          cells.push({
            bounds: [[south, west], [north, east]],
            count,
            color: getColorForCount(count),
          })
        }
      }
    }

    return cells
  }, [allPositions, showGrid, unit, resolution])

  const handleGenerate = useCallback(() => {
    setShowGrid(true)
  }, [])

  const handleReset = useCallback(() => {
    setShowGrid(false)
  }, [])

  if (!isOpen) return null

  // Calculate default center
  const defaultCenter: [number, number] = [39.8283, -98.5795] // Center of US

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content coverage-modal"
        onClick={e => e.stopPropagation()}
        style={{ width: '90vw', maxWidth: '1200px', height: '80vh' }}
      >
        <div className="modal-header">
          <h2>Coverage Map</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>

        <div className="coverage-controls" style={{
          display: 'flex',
          gap: '1rem',
          padding: '1rem',
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <div className="control-group" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <label>Resolution:</label>
            <input
              type="number"
              min="0.1"
              max="100"
              step="0.1"
              value={resolution}
              onChange={e => setResolution(parseFloat(e.target.value) || 1)}
              style={{ width: '80px' }}
              disabled={showGrid}
            />
            <select
              value={unit}
              onChange={e => setUnit(e.target.value as UnitType)}
              disabled={showGrid}
            >
              <option value="miles">Miles</option>
              <option value="kilometers">Kilometers</option>
            </select>
          </div>

          <div className="control-group" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <label>Lookback:</label>
            <input
              type="number"
              min="1"
              max="365"
              value={lookbackDays}
              onChange={e => setLookbackDays(parseInt(e.target.value) || 7)}
              style={{ width: '60px' }}
              disabled={showGrid}
            />
            <span>days</span>
          </div>

          {!showGrid ? (
            <button
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : 'Generate'}
            </button>
          ) : (
            <button
              className="btn btn-secondary"
              onClick={handleReset}
            >
              Reset
            </button>
          )}

          {showGrid && (
            <div style={{ marginLeft: 'auto', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              {positionHistory.length} historical + {nodes.filter(n => n.latitude != null).length} current positions | {gridCells.length} cells
            </div>
          )}
        </div>

        <div style={{ flex: 1, position: 'relative' }}>
          <LeafletMapContainer
            center={defaultCenter}
            zoom={4}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution={tileset.attribution}
              url={tileset.url}
              maxZoom={tileset.maxZoom}
            />

            {showGrid && <MapBoundsFitter positions={allPositions} />}

            {gridCells.map((cell, index) => (
              <Rectangle
                key={index}
                bounds={cell.bounds}
                pathOptions={{
                  color: cell.color,
                  fillColor: cell.color,
                  fillOpacity: 0.7,
                  weight: 1,
                  opacity: 0.3,
                }}
              />
            ))}
          </LeafletMapContainer>

          {/* Legend */}
          {showGrid && (
            <div style={{
              position: 'absolute',
              bottom: '20px',
              right: '20px',
              background: 'var(--color-surface)',
              padding: '0.75rem',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              zIndex: 1000,
              fontSize: '0.75rem',
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Position Reports</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {[
                  { color: COLORS[0], label: '1' },
                  { color: COLORS[1], label: '2' },
                  { color: COLORS[2], label: '3' },
                  { color: COLORS[3], label: '4-5' },
                  { color: COLORS[4], label: '6-7' },
                  { color: COLORS[5], label: '8-9' },
                  { color: COLORS[6], label: '10+' },
                ].map(({ color, label }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                      width: '16px',
                      height: '16px',
                      background: color,
                      border: '1px solid rgba(255,255,255,0.3)',
                    }} />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
