import { useState, useEffect, useCallback } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCoverageConfig, updateCoverageConfig, generateCoverage, type CoverageConfigUpdate,
  fetchUtilizationConfig, updateUtilizationConfig, generateUtilization, type UtilizationConfigUpdate, type AggregationType,
} from '../../services/api'
import { getTilesetById, DEFAULT_TILESET_ID } from '../../config/tilesets'
import 'leaflet/dist/leaflet.css'

type UnitType = 'miles' | 'kilometers'

function normalizeLng(lng: number) {
  const normalized = ((lng + 180) % 360 + 360) % 360 - 180
  return normalized
}

function normalizeBounds(bounds: { south: number; west: number; north: number; east: number }) {
  const south = Math.max(-90, Math.min(90, bounds.south))
  const north = Math.max(-90, Math.min(90, bounds.north))
  let west = normalizeLng(bounds.west)
  let east = normalizeLng(bounds.east)

  if (west > east) {
    const temp = west
    west = east
    east = temp
  }

  return { south, west, north, east }
}

// Component to track map bounds and report them
function BoundsTracker({ onBoundsChange }: { onBoundsChange: (bounds: { south: number; west: number; north: number; east: number }) => void }) {
  const map = useMapEvents({
    moveend: () => {
      const bounds = map.getBounds()
      onBoundsChange({
        ...normalizeBounds({
          south: bounds.getSouth(),
          west: bounds.getWest(),
          north: bounds.getNorth(),
          east: bounds.getEast(),
        }),
      })
    },
    zoomend: () => {
      const bounds = map.getBounds()
      onBoundsChange({
        ...normalizeBounds({
          south: bounds.getSouth(),
          west: bounds.getWest(),
          north: bounds.getNorth(),
          east: bounds.getEast(),
        }),
      })
    },
  })

  // Report initial bounds
  useEffect(() => {
    const bounds = map.getBounds()
    onBoundsChange({
      ...normalizeBounds({
        south: bounds.getSouth(),
        west: bounds.getWest(),
        north: bounds.getNorth(),
        east: bounds.getEast(),
      }),
    })
  }, [map, onBoundsChange])

  return null
}

// Component to set initial map view from saved bounds
function InitialBoundsSetter({ bounds }: { bounds: { south: number; west: number; north: number; east: number } | null }) {
  const map = useMap()

  useEffect(() => {
    if (bounds && bounds.south && bounds.west && bounds.north && bounds.east) {
      map.fitBounds([
        [bounds.south, bounds.west],
        [bounds.north, bounds.east],
      ])
    }
  }, []) // Only run once on mount

  return null
}

export default function GraphsPage() {
  const queryClient = useQueryClient()
  const tileset = getTilesetById(DEFAULT_TILESET_ID)

  // Coverage form state
  const [enabled, setEnabled] = useState(false)
  const [resolution, setResolution] = useState(1)
  const [unit, setUnit] = useState<UnitType>('miles')
  const [lookbackDays, setLookbackDays] = useState(7)
  const [currentBounds, setCurrentBounds] = useState<{ south: number; west: number; north: number; east: number } | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Utilization form state
  const [utilEnabled, setUtilEnabled] = useState(false)
  const [utilResolution, setUtilResolution] = useState(1)
  const [utilUnit, setUtilUnit] = useState<UnitType>('miles')
  const [utilLookbackDays, setUtilLookbackDays] = useState(7)
  const [utilAggregation, setUtilAggregation] = useState<AggregationType>('avg')
  const [utilBounds, setUtilBounds] = useState<{ south: number; west: number; north: number; east: number } | null>(null)
  const [utilHasUnsavedChanges, setUtilHasUnsavedChanges] = useState(false)

  // Fetch current config
  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['coverage-config'],
    queryFn: fetchCoverageConfig,
  })

  // Initialize form from config
  useEffect(() => {
    if (config) {
      setEnabled(config.enabled)
      setResolution(config.resolution)
      setUnit(config.unit as UnitType)
      setLookbackDays(config.lookback_days)
      if (config.bounds_south && config.bounds_west && config.bounds_north && config.bounds_east) {
        setCurrentBounds(normalizeBounds({
          south: config.bounds_south,
          west: config.bounds_west,
          north: config.bounds_north,
          east: config.bounds_east,
        }))
      }
    }
  }, [config])

  // Update config mutation
  const updateMutation = useMutation({
    mutationFn: (data: CoverageConfigUpdate) => updateCoverageConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coverage-config'] })
      setHasUnsavedChanges(false)
    },
  })

  // Generate coverage mutation
  const generateMutation = useMutation({
    mutationFn: generateCoverage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coverage-config'] })
      queryClient.invalidateQueries({ queryKey: ['coverage-cells'] })
    },
  })

  // Fetch utilization config
  const { data: utilConfig, isLoading: utilConfigLoading } = useQuery({
    queryKey: ['utilization-config'],
    queryFn: fetchUtilizationConfig,
  })

  // Initialize utilization form from config
  useEffect(() => {
    if (utilConfig) {
      setUtilEnabled(utilConfig.enabled)
      setUtilResolution(utilConfig.resolution)
      setUtilUnit(utilConfig.unit as UnitType)
      setUtilLookbackDays(utilConfig.lookback_days)
      setUtilAggregation(utilConfig.aggregation as AggregationType)
      if (utilConfig.bounds_south && utilConfig.bounds_west && utilConfig.bounds_north && utilConfig.bounds_east) {
        setUtilBounds({
          south: utilConfig.bounds_south,
          west: utilConfig.bounds_west,
          north: utilConfig.bounds_north,
          east: utilConfig.bounds_east,
        })
      }
    }
  }, [utilConfig])

  // Update utilization config mutation
  const utilUpdateMutation = useMutation({
    mutationFn: (data: UtilizationConfigUpdate) => updateUtilizationConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['utilization-config'] })
      setUtilHasUnsavedChanges(false)
    },
  })

  // Generate utilization mutation
  const utilGenerateMutation = useMutation({
    mutationFn: generateUtilization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['utilization-config'] })
      queryClient.invalidateQueries({ queryKey: ['utilization-cells'] })
    },
  })

  const handleBoundsChange = useCallback((bounds: { south: number; west: number; north: number; east: number }) => {
    setCurrentBounds(bounds)
    setHasUnsavedChanges(true)
  }, [])

  const handleSave = () => {
    updateMutation.mutate({
      enabled,
      resolution,
      unit,
      lookback_days: lookbackDays,
      bounds_south: currentBounds?.south ?? null,
      bounds_west: currentBounds?.west ?? null,
      bounds_north: currentBounds?.north ?? null,
      bounds_east: currentBounds?.east ?? null,
    })
  }

  const handleGenerate = () => {
    // Save first, then generate
    updateMutation.mutate({
      enabled,
      resolution,
      unit,
      lookback_days: lookbackDays,
      bounds_south: currentBounds?.south ?? null,
      bounds_west: currentBounds?.west ?? null,
      bounds_north: currentBounds?.north ?? null,
      bounds_east: currentBounds?.east ?? null,
    }, {
      onSuccess: () => {
        generateMutation.mutate()
      },
    })
  }

  const handleCancel = () => {
    // Reset form to config values
    if (config) {
      setEnabled(config.enabled)
      setResolution(config.resolution)
      setUnit(config.unit as UnitType)
      setLookbackDays(config.lookback_days)
      if (config.bounds_south && config.bounds_west && config.bounds_north && config.bounds_east) {
        setCurrentBounds({
          south: config.bounds_south,
          west: config.bounds_west,
          north: config.bounds_north,
          east: config.bounds_east,
        })
      }
    }
    setHasUnsavedChanges(false)
  }

  // Utilization handlers
  const handleUtilBoundsChange = useCallback((bounds: { south: number; west: number; north: number; east: number }) => {
    setUtilBounds(bounds)
    setUtilHasUnsavedChanges(true)
  }, [])

  const handleUtilSave = () => {
    utilUpdateMutation.mutate({
      enabled: utilEnabled,
      resolution: utilResolution,
      unit: utilUnit,
      lookback_days: utilLookbackDays,
      aggregation: utilAggregation,
      bounds_south: utilBounds?.south ?? null,
      bounds_west: utilBounds?.west ?? null,
      bounds_north: utilBounds?.north ?? null,
      bounds_east: utilBounds?.east ?? null,
    })
  }

  const handleUtilGenerate = () => {
    // Save first, then generate
    utilUpdateMutation.mutate({
      enabled: utilEnabled,
      resolution: utilResolution,
      unit: utilUnit,
      lookback_days: utilLookbackDays,
      aggregation: utilAggregation,
      bounds_south: utilBounds?.south ?? null,
      bounds_west: utilBounds?.west ?? null,
      bounds_north: utilBounds?.north ?? null,
      bounds_east: utilBounds?.east ?? null,
    }, {
      onSuccess: () => {
        utilGenerateMutation.mutate()
      },
    })
  }

  const handleUtilCancel = () => {
    // Reset form to config values
    if (utilConfig) {
      setUtilEnabled(utilConfig.enabled)
      setUtilResolution(utilConfig.resolution)
      setUtilUnit(utilConfig.unit as UnitType)
      setUtilLookbackDays(utilConfig.lookback_days)
      setUtilAggregation(utilConfig.aggregation as AggregationType)
      if (utilConfig.bounds_south && utilConfig.bounds_west && utilConfig.bounds_north && utilConfig.bounds_east) {
        setUtilBounds({
          south: utilConfig.bounds_south,
          west: utilConfig.bounds_west,
          north: utilConfig.bounds_north,
          east: utilConfig.bounds_east,
        })
      }
    }
    setUtilHasUnsavedChanges(false)
  }

  // Default center (US)
  const defaultCenter: [number, number] = [39.8283, -98.5795]

  // Initial bounds from config (for map initialization)
  const initialBounds = config?.bounds_south && config?.bounds_west && config?.bounds_north && config?.bounds_east
    ? { south: config.bounds_south, west: config.bounds_west, north: config.bounds_north, east: config.bounds_east }
    : null

  // Initial utilization bounds from config
  const utilInitialBounds = utilConfig?.bounds_south && utilConfig?.bounds_west && utilConfig?.bounds_north && utilConfig?.bounds_east
    ? { south: utilConfig.bounds_south, west: utilConfig.bounds_west, north: utilConfig.bounds_north, east: utilConfig.bounds_east }
    : null

  if (configLoading || utilConfigLoading) {
    return (
      <div className="graphs-page">
        <div className="settings-header">
          <h1>Graphs</h1>
        </div>
        <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
      </div>
    )
  }

  return (
    <div className="graphs-page">
      <div className="settings-header">
        <h1>Graphs</h1>
      </div>

      <div style={{ padding: '1rem' }}>
        {/* Coverage Map Configuration */}
        <div style={{
          background: 'var(--color-surface)',
          borderRadius: '8px',
          border: '1px solid var(--color-border)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Coverage Map</h2>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                Configure the position report heatmap overlay. When enabled, coverage data is regenerated every 24 hours.
              </p>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={e => {
                  setEnabled(e.target.checked)
                  setHasUnsavedChanges(true)
                }}
                style={{ width: '18px', height: '18px' }}
              />
              <span>Enable</span>
            </label>
          </div>

          {/* Configuration Controls */}
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            gap: '2rem',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Resolution
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={resolution}
                  onChange={e => {
                    setResolution(parseFloat(e.target.value) || 1)
                    setHasUnsavedChanges(true)
                  }}
                  style={{
                    width: '80px',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                />
                <select
                  value={unit}
                  onChange={e => {
                    setUnit(e.target.value as UnitType)
                    setHasUnsavedChanges(true)
                  }}
                  style={{
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="miles">Miles</option>
                  <option value="kilometers">Kilometers</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Lookback Period
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={lookbackDays}
                  onChange={e => {
                    setLookbackDays(parseInt(e.target.value) || 7)
                    setHasUnsavedChanges(true)
                  }}
                  style={{
                    width: '60px',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                />
                <span style={{ color: 'var(--color-text-muted)' }}>days</span>
              </div>
            </div>

            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={handleCancel}
                disabled={!hasUnsavedChanges}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
                  cursor: hasUnsavedChanges ? 'pointer' : 'default',
                  opacity: hasUnsavedChanges ? 1 : 0.5,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending || !hasUnsavedChanges}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid var(--color-border)',
                  background: hasUnsavedChanges ? 'var(--color-primary)' : 'var(--color-surface)',
                  color: hasUnsavedChanges ? 'white' : 'var(--color-text)',
                  cursor: hasUnsavedChanges ? 'pointer' : 'default',
                  opacity: hasUnsavedChanges ? 1 : 0.5,
                }}
              >
                {updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending || updateMutation.isPending}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: 'none',
                  background: 'var(--color-success)',
                  color: 'white',
                  cursor: 'pointer',
                }}
              >
                {generateMutation.isPending ? 'Generating...' : 'Generate Now'}
              </button>
            </div>
          </div>

          {/* Status Info */}
          {config && (
            <div style={{
              padding: '0.75rem 1.5rem',
              borderBottom: '1px solid var(--color-border)',
              background: 'var(--color-background)',
              fontSize: '0.875rem',
              display: 'flex',
              gap: '2rem',
              flexWrap: 'wrap',
              alignItems: 'center',
            }}>
              <span>
                <strong>Cells:</strong> {config.cell_count.toLocaleString()}
              </span>
              {config.last_generated && (
                <span>
                  <strong>Last Generated:</strong> {new Date(config.last_generated).toLocaleString()}
                </span>
              )}
              {generateMutation.isSuccess && generateMutation.data && (
                <span style={{ color: 'var(--color-success)' }}>
                  {generateMutation.data.message}
                </span>
              )}
              {generateMutation.isError && (
                <span style={{ color: 'var(--color-error)' }}>
                  Generation failed
                </span>
              )}
              {config.cell_count > 0 && (
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ color: 'var(--color-text-muted)', marginRight: '0.25rem' }}>Export Grid:</span>
                  <a
                    href="/api/coverage/export/kml"
                    download="coverage.kml"
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      textDecoration: 'none',
                      fontSize: '0.75rem',
                    }}
                  >
                    KML
                  </a>
                  <a
                    href="/api/coverage/export/geotiff"
                    download="coverage.tif"
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      textDecoration: 'none',
                      fontSize: '0.75rem',
                    }}
                  >
                    GeoTIFF
                  </a>
                  <span style={{ color: 'var(--color-text-muted)', marginLeft: '0.5rem', marginRight: '0.25rem' }}>Points:</span>
                  <a
                    href={`/api/coverage/export/csv?lookback_days=${lookbackDays}`}
                    download="positions.csv"
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      textDecoration: 'none',
                      fontSize: '0.75rem',
                    }}
                  >
                    CSV
                  </a>
                  <a
                    href={`/api/coverage/export/shapefile?lookback_days=${lookbackDays}`}
                    download="positions.zip"
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      textDecoration: 'none',
                      fontSize: '0.75rem',
                    }}
                  >
                    Shapefile
                  </a>
                  <a
                    href={`/api/coverage/export/geopackage?lookback_days=${lookbackDays}`}
                    download="positions.gpkg"
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      textDecoration: 'none',
                      fontSize: '0.75rem',
                    }}
                  >
                    GeoPackage
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Boundary Selection Map */}
          <div style={{ padding: '1rem 1.5rem' }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Pan and zoom the map to set the coverage calculation bounds. Only positions within these bounds will be included.
            </div>
            {currentBounds && (
              <div style={{ marginBottom: '0.5rem', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                Bounds: {currentBounds.south.toFixed(4)}N to {currentBounds.north.toFixed(4)}N, {currentBounds.west.toFixed(4)}W to {currentBounds.east.toFixed(4)}E
              </div>
            )}
            <div style={{
              height: '400px',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
            }}>
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
                <BoundsTracker onBoundsChange={handleBoundsChange} />
                {initialBounds && <InitialBoundsSetter bounds={initialBounds} />}
              </LeafletMapContainer>
            </div>
          </div>
        </div>

        {/* Utilization Overlay Configuration */}
        <div style={{
          background: 'var(--color-surface)',
          borderRadius: '8px',
          border: '1px solid var(--color-border)',
          overflow: 'hidden',
          marginTop: '1.5rem',
        }}>
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Utilization Overlay</h2>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                Configure the channel utilization heatmap overlay. Shows network congestion based on node telemetry.
              </p>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={utilEnabled}
                onChange={e => {
                  setUtilEnabled(e.target.checked)
                  setUtilHasUnsavedChanges(true)
                }}
                style={{ width: '18px', height: '18px' }}
              />
              <span>Enable</span>
            </label>
          </div>

          {/* Configuration Controls */}
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            gap: '2rem',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Resolution
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={utilResolution}
                  onChange={e => {
                    setUtilResolution(parseFloat(e.target.value) || 1)
                    setUtilHasUnsavedChanges(true)
                  }}
                  style={{
                    width: '80px',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                />
                <select
                  value={utilUnit}
                  onChange={e => {
                    setUtilUnit(e.target.value as UnitType)
                    setUtilHasUnsavedChanges(true)
                  }}
                  style={{
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="miles">Miles</option>
                  <option value="kilometers">Kilometers</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Lookback Period
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={utilLookbackDays}
                  onChange={e => {
                    setUtilLookbackDays(parseInt(e.target.value) || 7)
                    setUtilHasUnsavedChanges(true)
                  }}
                  style={{
                    width: '60px',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-background)',
                    color: 'var(--color-text)',
                  }}
                />
                <span style={{ color: 'var(--color-text-muted)' }}>days</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Aggregation
              </label>
              <select
                value={utilAggregation}
                onChange={e => {
                  setUtilAggregation(e.target.value as AggregationType)
                  setUtilHasUnsavedChanges(true)
                }}
                style={{
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-background)',
                  color: 'var(--color-text)',
                }}
              >
                <option value="min">Minimum</option>
                <option value="max">Maximum</option>
                <option value="avg">Average</option>
              </select>
            </div>

            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={handleUtilCancel}
                disabled={!utilHasUnsavedChanges}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
                  cursor: utilHasUnsavedChanges ? 'pointer' : 'default',
                  opacity: utilHasUnsavedChanges ? 1 : 0.5,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleUtilSave}
                disabled={utilUpdateMutation.isPending || !utilHasUnsavedChanges}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid var(--color-border)',
                  background: utilHasUnsavedChanges ? 'var(--color-primary)' : 'var(--color-surface)',
                  color: utilHasUnsavedChanges ? 'white' : 'var(--color-text)',
                  cursor: utilHasUnsavedChanges ? 'pointer' : 'default',
                  opacity: utilHasUnsavedChanges ? 1 : 0.5,
                }}
              >
                {utilUpdateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleUtilGenerate}
                disabled={utilGenerateMutation.isPending || utilUpdateMutation.isPending}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: 'none',
                  background: 'var(--color-success)',
                  color: 'white',
                  cursor: 'pointer',
                }}
              >
                {utilGenerateMutation.isPending ? 'Generating...' : 'Generate Now'}
              </button>
            </div>
          </div>

          {/* Status Info */}
          {utilConfig && (
            <div style={{
              padding: '0.75rem 1.5rem',
              borderBottom: '1px solid var(--color-border)',
              background: 'var(--color-background)',
              fontSize: '0.875rem',
              display: 'flex',
              gap: '2rem',
              flexWrap: 'wrap',
              alignItems: 'center',
            }}>
              <span>
                <strong>Cells:</strong> {utilConfig.cell_count.toLocaleString()}
              </span>
              {utilConfig.last_generated && (
                <span>
                  <strong>Last Generated:</strong> {new Date(utilConfig.last_generated).toLocaleString()}
                </span>
              )}
              {utilGenerateMutation.isSuccess && utilGenerateMutation.data && (
                <span style={{ color: 'var(--color-success)' }}>
                  {utilGenerateMutation.data.message}
                </span>
              )}
              {utilGenerateMutation.isError && (
                <span style={{ color: 'var(--color-error)' }}>
                  Generation failed
                </span>
              )}
            </div>
          )}

          {/* Boundary Selection Map */}
          <div style={{ padding: '1rem 1.5rem' }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Pan and zoom the map to set the utilization calculation bounds. Only telemetry within these bounds will be included.
            </div>
            {utilBounds && (
              <div style={{ marginBottom: '0.5rem', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                Bounds: {utilBounds.south.toFixed(4)}N to {utilBounds.north.toFixed(4)}N, {utilBounds.west.toFixed(4)}W to {utilBounds.east.toFixed(4)}E
              </div>
            )}
            <div style={{
              height: '400px',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
            }}>
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
                <BoundsTracker onBoundsChange={handleUtilBoundsChange} />
                {utilInitialBounds && <InitialBoundsSetter bounds={utilInitialBounds} />}
              </LeafletMapContainer>
            </div>
          </div>
        </div>

        {/* Placeholder cards for future graphs */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '1rem',
          marginTop: '1.5rem',
        }}>
          <div
            className="graph-card"
            style={{
              background: 'var(--color-surface)',
              borderRadius: '8px',
              padding: '1.5rem',
              border: '1px solid var(--color-border)',
              opacity: 0.6,
            }}
          >
            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>📈</div>
            <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Signal Strength</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Coming soon: Track signal strength over time.
            </p>
          </div>

          <div
            className="graph-card"
            style={{
              background: 'var(--color-surface)',
              borderRadius: '8px',
              padding: '1.5rem',
              border: '1px solid var(--color-border)',
              opacity: 0.6,
            }}
          >
            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔗</div>
            <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Node Connections</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Coming soon: Visualize network topology.
            </p>
          </div>

          <div
            className="graph-card"
            style={{
              background: 'var(--color-surface)',
              borderRadius: '8px',
              padding: '1.5rem',
              border: '1px solid var(--color-border)',
              opacity: 0.6,
            }}
          >
            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>💬</div>
            <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Message Activity</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Coming soon: View message traffic patterns.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
