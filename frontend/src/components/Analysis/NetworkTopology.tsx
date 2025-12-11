import { useState, useMemo, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer as LeafletMapContainer, TileLayer, Polyline, CircleMarker, Tooltip } from 'react-leaflet'
import { fetchTraceroutes, fetchNodes } from '../../services/api'
import { getTilesetById, getAllTilesets, DEFAULT_TILESET_ID, type TilesetId } from '../../config/tilesets'
import type { Traceroute } from '../../types/api'
import 'leaflet/dist/leaflet.css'

// Constants
const EARTH_RADIUS_MILES = 3959
const DEFAULT_MAP_CENTER: [number, number] = [0, 0] // World center as fallback
const BASE_CLUSTER_MARKER_RADIUS = 8
const MAX_CLUSTER_MARKER_BONUS = 10
const MAX_CLUSTER_RADIUS_MILES = 50
const DEBOUNCE_MS = 300

// Debounce hook for slider controls
function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  const firstRender = useRef(true)

  useEffect(() => {
    // Skip debounce on first render
    if (firstRender.current) {
      firstRender.current = false
      return
    }

    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(timer)
  }, [value, delay])

  return debouncedValue
}

interface EdgeData {
  from: number
  to: number
  count: number
}

interface TrunkLine {
  fromNodeNum: number
  toNodeNum: number
  fromName: string
  toName: string
  count: number
  popularity: number // percentage (0-100)
  fromPosition: [number, number] | null
  toPosition: [number, number] | null
}

interface Cluster {
  hubNodeNum: number
  hubPosition: [number, number] | null
  hubName: string | null
  connectedNodes: number[]
  connectedNodeNames: string[]
  connectionCount: number
}

// Calculate distance between two lat/lng points in miles using Haversine formula
function getDistanceMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return EARTH_RADIUS_MILES * c
}

// Count all edges from traceroutes (only interior hops, excluding source/destination edges)
function countEdges(traceroutes: Traceroute[]): Map<string, EdgeData> {
  const edgeCounts = new Map<string, EdgeData>()

  for (const trace of traceroutes) {
    if (trace.route && trace.route.length >= 2) {
      for (let i = 0; i < trace.route.length - 1; i++) {
        const from = trace.route[i]
        const to = trace.route[i + 1]
        const [a, b] = from < to ? [from, to] : [to, from]
        const key = `${a}-${b}`
        const existing = edgeCounts.get(key)
        if (existing) {
          existing.count++
        } else {
          edgeCounts.set(key, { from: a, to: b, count: 1 })
        }
      }
    }

    if (trace.route_back && trace.route_back.length >= 2) {
      for (let i = 0; i < trace.route_back.length - 1; i++) {
        const from = trace.route_back[i]
        const to = trace.route_back[i + 1]
        const [a, b] = from < to ? [from, to] : [to, from]
        const key = `${a}-${b}`
        const existing = edgeCounts.get(key)
        if (existing) {
          existing.count++
        } else {
          edgeCounts.set(key, { from: a, to: b, count: 1 })
        }
      }
    }
  }

  return edgeCounts
}

function getTrunkLines(
  edgeCounts: Map<string, EdgeData>,
  nodePositions: Map<number, [number, number]>,
  nodeNames: Map<number, string>,
  minPopularity: number,
  maxEdgeCount: number
): TrunkLine[] {
  const trunkLines: TrunkLine[] = []

  for (const [, edge] of edgeCounts) {
    const popularity = maxEdgeCount > 0 ? (edge.count / maxEdgeCount) * 100 : 0
    if (popularity >= minPopularity) {
      trunkLines.push({
        fromNodeNum: edge.from,
        toNodeNum: edge.to,
        fromName: nodeNames.get(edge.from) || `!${edge.from.toString(16)}`,
        toName: nodeNames.get(edge.to) || `!${edge.to.toString(16)}`,
        count: edge.count,
        popularity,
        fromPosition: nodePositions.get(edge.from) || null,
        toPosition: nodePositions.get(edge.to) || null,
      })
    }
  }

  return trunkLines.sort((a, b) => b.count - a.count)
}

function getClusters(
  edgeCounts: Map<string, EdgeData>,
  nodePositions: Map<number, [number, number]>,
  nodeNames: Map<number, string>,
  minPopularity: number,
  maxEdgeCount: number,
  minClusterConnections: number,
  clusterRadiusMiles: number
): Cluster[] {
  const connections = new Map<number, Set<number>>()

  // Build connection map from non-trunk edges
  for (const [, edge] of edgeCounts) {
    const popularity = maxEdgeCount > 0 ? (edge.count / maxEdgeCount) * 100 : 0
    if (popularity < minPopularity) {
      const from = edge.from
      const to = edge.to

      if (!connections.has(from)) connections.set(from, new Set())
      if (!connections.has(to)) connections.set(to, new Set())
      connections.get(from)!.add(to)
      connections.get(to)!.add(from)
    }
  }

  const clusters: Cluster[] = []

  // For each potential hub, check if connected nodes form a geographic cluster
  for (const [hubNodeNum, connectedSet] of connections) {
    if (connectedSet.size < minClusterConnections) continue

    const hubPosition = nodePositions.get(hubNodeNum)
    if (!hubPosition) continue // Hub must have a position

    // Filter connected nodes to only those within the radius of the hub
    const nodesWithinRadius: number[] = []
    for (const connectedNode of connectedSet) {
      const connectedPos = nodePositions.get(connectedNode)
      if (connectedPos) {
        const distance = getDistanceMiles(
          hubPosition[0], hubPosition[1],
          connectedPos[0], connectedPos[1]
        )
        if (distance <= clusterRadiusMiles) {
          nodesWithinRadius.push(connectedNode)
        }
      }
    }

    // Only count as a cluster if enough nodes are within radius
    if (nodesWithinRadius.length >= minClusterConnections) {
      clusters.push({
        hubNodeNum,
        hubPosition,
        hubName: nodeNames.get(hubNodeNum) || null,
        connectedNodes: nodesWithinRadius,
        connectedNodeNames: nodesWithinRadius.map(n => nodeNames.get(n) || `!${n.toString(16)}`),
        connectionCount: nodesWithinRadius.length,
      })
    }
  }

  return clusters.sort((a, b) => b.connectionCount - a.connectionCount)
}

function getTrunkLineColor(count: number, maxCount: number): string {
  const intensity = Math.min(count / maxCount, 1)
  const r = 255
  const g = Math.round(140 * (1 - intensity))
  const b = 0
  return `rgb(${r}, ${g}, ${b})`
}

function getTrunkLineWidth(count: number, maxCount: number): number {
  const intensity = Math.min(count / maxCount, 1)
  return 2 + intensity * 6
}

export default function NetworkTopology() {
  const [tilesetId, setTilesetId] = useState<TilesetId>(DEFAULT_TILESET_ID)
  const tileset = getTilesetById(tilesetId)
  const allTilesets = getAllTilesets()

  const [lookbackHours, setLookbackHours] = useState(168)
  const [minPopularity, setMinPopularity] = useState(25)
  const [minClusterConnections, setMinClusterConnections] = useState(3)
  const [clusterRadius, setClusterRadius] = useState(5) // miles
  const [showTrunkLines, setShowTrunkLines] = useState(true)
  const [showClusters, setShowClusters] = useState(true)

  // Debounce slider values to prevent lag during adjustment
  const debouncedMinPopularity = useDebouncedValue(minPopularity, DEBOUNCE_MS)
  const debouncedClusterRadius = useDebouncedValue(clusterRadius, DEBOUNCE_MS)

  const { data: traceroutes, isLoading: traceroutesLoading, error: traceroutesError } = useQuery({
    queryKey: ['traceroutes', lookbackHours],
    queryFn: () => fetchTraceroutes(lookbackHours),
  })

  const { data: nodes, isLoading: nodesLoading, error: nodesError } = useQuery({
    queryKey: ['nodes'],
    queryFn: () => fetchNodes(),
  })

  const { trunkLines, clusters, mapCenter, maxTrunkCount, maxEdgeCount, totalEdges } = useMemo(() => {
    if (!traceroutes || !nodes) {
      return { trunkLines: [], clusters: [], mapCenter: DEFAULT_MAP_CENTER, maxTrunkCount: 1, maxEdgeCount: 0, totalEdges: 0 }
    }

    const nodePositions = new Map<number, [number, number]>()
    const nodeNames = new Map<number, string>()
    for (const node of nodes) {
      if (node.latitude && node.longitude) {
        nodePositions.set(node.node_num, [node.latitude, node.longitude])
      }
      const longName = node.long_name || ''
      const shortName = node.short_name || ''
      let displayName: string
      if (longName && shortName) {
        displayName = `${longName} [${shortName}]`
      } else if (longName) {
        displayName = longName
      } else if (shortName) {
        displayName = shortName
      } else {
        displayName = `!${node.node_num.toString(16)}`
      }
      nodeNames.set(node.node_num, displayName)
    }

    const edgeCounts = countEdges(traceroutes)

    let maxCount = 0
    for (const [, edge] of edgeCounts) {
      if (edge.count > maxCount) maxCount = edge.count
    }

    const trunks = getTrunkLines(edgeCounts, nodePositions, nodeNames, debouncedMinPopularity, maxCount)
    const clusterData = getClusters(edgeCounts, nodePositions, nodeNames, debouncedMinPopularity, maxCount, minClusterConnections, debouncedClusterRadius)

    const nodesWithPositions = nodes.filter(n => n.latitude && n.longitude)
    let center: [number, number] = DEFAULT_MAP_CENTER
    if (nodesWithPositions.length > 0) {
      const avgLat = nodesWithPositions.reduce((sum, n) => sum + (n.latitude || 0), 0) / nodesWithPositions.length
      const avgLng = nodesWithPositions.reduce((sum, n) => sum + (n.longitude || 0), 0) / nodesWithPositions.length
      center = [avgLat, avgLng]
    }

    const maxTrunkCountValue = trunks.length > 0 ? Math.max(...trunks.map(t => t.count)) : 1

    return {
      trunkLines: trunks,
      clusters: clusterData,
      mapCenter: center,
      maxTrunkCount: maxTrunkCountValue,
      maxEdgeCount: maxCount,
      totalEdges: edgeCounts.size,
    }
  }, [traceroutes, nodes, debouncedMinPopularity, minClusterConnections, debouncedClusterRadius])

  const visibleTrunkLines = trunkLines.filter(t => t.fromPosition && t.toPosition)
  const visibleClusters = clusters.filter(c => c.hubPosition)

  const isLoading = traceroutesLoading || nodesLoading
  const hasError = traceroutesError || nodesError
  const errorMessage = traceroutesError?.message || nodesError?.message || 'An error occurred'
  const hasNoData = !isLoading && !hasError && traceroutes?.length === 0

  const labelStyle = { fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' as const, marginBottom: '0.25rem' }
  const controlGroupStyle = { marginBottom: '1rem' }

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      background: 'var(--color-surface)',
      borderRadius: '8px',
      border: '1px solid var(--color-border)',
      overflow: 'hidden',
    }}>
      {/* Left Sidebar - Controls */}
      <div style={{
        width: '280px',
        flexShrink: 0,
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Options</h3>
        </div>

        <div style={{ padding: '1rem', overflowY: 'auto', flex: 1 }}>
          {/* Map Tiles */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Map Tiles</div>
            <select
              value={tilesetId}
              onChange={e => setTilesetId(e.target.value as TilesetId)}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-background)',
                color: 'var(--color-text)',
              }}
            >
              {allTilesets.map(ts => (
                <option key={ts.id} value={ts.id}>{ts.name}</option>
              ))}
            </select>
          </div>

          {/* Lookback Period */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Lookback Period</div>
            <select
              value={lookbackHours}
              onChange={e => setLookbackHours(parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-background)',
                color: 'var(--color-text)',
              }}
            >
              <option value={24}>24 hours</option>
              <option value={72}>3 days</option>
              <option value={168}>7 days</option>
              <option value={336}>14 days</option>
              <option value={720}>30 days</option>
            </select>
          </div>

          {/* Min Popularity */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Min Popularity: {minPopularity}%</div>
            <input
              type="range"
              min="0"
              max="100"
              value={minPopularity}
              onChange={e => setMinPopularity(parseInt(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          {/* Min Cluster Connections */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Min Cluster Connections</div>
            <input
              type="number"
              min="2"
              max="50"
              value={minClusterConnections}
              onChange={e => setMinClusterConnections(parseInt(e.target.value) || 2)}
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

          {/* Cluster Radius */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Cluster Radius: {clusterRadius} mi</div>
            <input
              type="range"
              min="1"
              max={MAX_CLUSTER_RADIUS_MILES}
              value={clusterRadius}
              onChange={e => setClusterRadius(parseInt(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          {/* Show/Hide toggles */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Display</div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
              <input
                type="checkbox"
                checked={showTrunkLines}
                onChange={e => setShowTrunkLines(e.target.checked)}
              />
              <span style={{ fontSize: '0.875rem' }}>Show Trunk Lines</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showClusters}
                onChange={e => setShowClusters(e.target.checked)}
              />
              <span style={{ fontSize: '0.875rem' }}>Show Clusters</span>
            </label>
          </div>

          {/* Legend */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Legend</div>
            <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '30px', height: '3px', background: 'linear-gradient(to right, rgb(255,140,0), rgb(255,0,0))', borderRadius: '2px' }} />
                <span>Trunk Line</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', background: '#8b5cf6', borderRadius: '50%', opacity: 0.6 }} />
                <span>Cluster Hub</span>
              </div>
            </div>
          </div>

          {/* Statistics */}
          <div style={controlGroupStyle}>
            <div style={labelStyle}>Statistics</div>
            <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div>Traceroutes: <strong>{traceroutes?.length ?? 0}</strong></div>
              <div>Total Edges: <strong>{totalEdges}</strong></div>
              <div>Trunk Lines: <strong>{trunkLines.length}</strong> ({visibleTrunkLines.length} visible)</div>
              <div>Clusters: <strong>{clusters.length}</strong> ({visibleClusters.length} visible)</div>
              {maxEdgeCount > 0 && <div>Max Uses: <strong>{maxEdgeCount}</strong></div>}
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Map and tables */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Map */}
        <div style={{ flex: 1, minHeight: 0 }}>
          {isLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)' }}>
              Loading traceroute data...
            </div>
          ) : hasError ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-error, #ef4444)', flexDirection: 'column', gap: '0.5rem' }}>
              <span>Error loading data</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>{errorMessage}</span>
            </div>
          ) : hasNoData ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)', flexDirection: 'column', gap: '0.5rem' }}>
              <span>No traceroute data available</span>
              <span style={{ fontSize: '0.875rem' }}>Traceroute data will appear as the network collects routing information.</span>
            </div>
          ) : (
            <LeafletMapContainer
              center={mapCenter}
              zoom={6}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution={tileset.attribution}
                url={tileset.url}
                maxZoom={tileset.maxZoom}
              />

              {showTrunkLines && visibleTrunkLines.map((trunk, idx) => (
                <Polyline
                  key={`trunk-${idx}`}
                  positions={[trunk.fromPosition!, trunk.toPosition!]}
                  pathOptions={{
                    color: getTrunkLineColor(trunk.count, maxTrunkCount),
                    weight: getTrunkLineWidth(trunk.count, maxTrunkCount),
                    opacity: 0.8,
                  }}
                >
                  <Tooltip sticky>
                    <div>
                      <strong>Trunk Line</strong><br />
                      Uses: {trunk.count} ({trunk.popularity.toFixed(0)}%)<br />
                      From: {trunk.fromName}<br />
                      To: {trunk.toName}
                    </div>
                  </Tooltip>
                </Polyline>
              ))}

              {showClusters && visibleClusters.map((cluster, idx) => (
                <CircleMarker
                  key={`cluster-${idx}`}
                  center={cluster.hubPosition!}
                  radius={BASE_CLUSTER_MARKER_RADIUS + Math.min(cluster.connectionCount, MAX_CLUSTER_MARKER_BONUS)}
                  pathOptions={{
                    color: '#8b5cf6',
                    fillColor: '#8b5cf6',
                    fillOpacity: 0.6,
                    weight: 2,
                  }}
                >
                  <Tooltip>
                    <div>
                      <strong>Geographic Cluster</strong><br />
                      <span style={{ color: '#8b5cf6' }}>Hub: {cluster.hubName}</span><br />
                      Nodes within {clusterRadius} mi: {cluster.connectionCount}<br />
                      <br />
                      <em>Connected Nodes:</em><br />
                      {cluster.connectedNodeNames.slice(0, 10).map((name, i) => (
                        <span key={i}>&nbsp;&nbsp;{name}<br /></span>
                      ))}
                      {cluster.connectedNodeNames.length > 10 && (
                        <span>&nbsp;&nbsp;... and {cluster.connectedNodeNames.length - 10} more</span>
                      )}
                    </div>
                  </Tooltip>
                </CircleMarker>
              ))}
            </LeafletMapContainer>
          )}
        </div>

        {/* Tables below map */}
        <div style={{
          maxHeight: '250px',
          overflowY: 'auto',
          borderTop: '1px solid var(--color-border)',
          background: 'var(--color-background)',
        }}>
          {/* Top Trunk Lines Table */}
          {trunkLines.length > 0 && (
            <div style={{ padding: '0.75rem 1rem' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem' }}>Top Trunk Lines</h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem', fontWeight: 600 }}>From</th>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem', fontWeight: 600 }}>To</th>
                    <th style={{ textAlign: 'right', padding: '0.25rem 0.5rem', fontWeight: 600 }}>Uses</th>
                    <th style={{ textAlign: 'right', padding: '0.25rem 0.5rem', fontWeight: 600 }}>Pop.</th>
                  </tr>
                </thead>
                <tbody>
                  {trunkLines.slice(0, 5).map((trunk, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '0.25rem 0.5rem' }}>{trunk.fromName}</td>
                      <td style={{ padding: '0.25rem 0.5rem' }}>{trunk.toName}</td>
                      <td style={{ padding: '0.25rem 0.5rem', textAlign: 'right' }}>{trunk.count}</td>
                      <td style={{ padding: '0.25rem 0.5rem', textAlign: 'right' }}>{trunk.popularity.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Clusters Table */}
          {clusters.length > 0 && (
            <div style={{ padding: '0.75rem 1rem', borderTop: trunkLines.length > 0 ? '1px solid var(--color-border)' : 'none' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem' }}>Top Clusters</h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem', fontWeight: 600 }}>Hub</th>
                    <th style={{ textAlign: 'right', padding: '0.25rem 0.5rem', fontWeight: 600 }}>Connections</th>
                  </tr>
                </thead>
                <tbody>
                  {clusters.slice(0, 5).map((cluster, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '0.25rem 0.5rem' }}>{cluster.hubName || `!${cluster.hubNodeNum.toString(16)}`}</td>
                      <td style={{ padding: '0.25rem 0.5rem', textAlign: 'right' }}>{cluster.connectionCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
