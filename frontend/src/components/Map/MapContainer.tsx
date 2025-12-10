import { useEffect, useMemo, useState, useCallback } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { useNodes } from '../../hooks/useNodes'
import { useTraceroutes } from '../../hooks/useMapData'
import { useDataContext } from '../../contexts/DataContext'
import { getTilesetById, DEFAULT_TILESET_ID, type TilesetId } from '../../config/tilesets'
import { fetchCoverageConfig, fetchCoverageCells, fetchPositionHistory } from '../../services/api'
import MapControls from './MapControls'
import CoverageImageOverlay from './CoverageImageOverlay'
import HeatmapLayer from './HeatmapLayer'
import type { Node } from '../../types/api'
import 'leaflet/dist/leaflet.css'

// LocalStorage keys
const STORAGE_KEY_TILESET = 'meshmanager_map_tileset'
const STORAGE_KEY_SHOW_ROUTES = 'meshmanager_map_show_routes'
const STORAGE_KEY_ENABLED_ROLES = 'meshmanager_map_enabled_roles'
const STORAGE_KEY_SHOW_COVERAGE = 'meshmanager_map_show_coverage'
const STORAGE_KEY_SHOW_POSITION_HISTORY = 'meshmanager_map_show_position_history'
const STORAGE_KEY_POSITION_HISTORY_DAYS = 'meshmanager_map_position_history_days'

// Coverage legend colors (matching backend)
const COVERAGE_LEGEND = [
  { color: 'rgba(65, 105, 225, 0.6)', label: '1' },
  { color: 'rgba(50, 205, 50, 0.6)', label: '2' },
  { color: 'rgba(255, 255, 0, 0.6)', label: '3' },
  { color: 'rgba(255, 165, 0, 0.7)', label: '4-5' },
  { color: 'rgba(255, 69, 0, 0.7)', label: '6-7' },
  { color: 'rgba(255, 0, 0, 0.8)', label: '8-9' },
  { color: 'rgba(139, 0, 0, 0.8)', label: '10+' },
]

// Load settings from localStorage
function loadSetting<T>(key: string, defaultValue: T, parser?: (value: string) => T): T {
  try {
    const stored = localStorage.getItem(key)
    if (stored === null) return defaultValue
    if (parser) return parser(stored)
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

function saveSetting<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore storage errors
  }
}

// Fix for default marker icons in Leaflet with Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// @ts-expect-error - Leaflet internals
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

// Custom marker icons
const createIcon = (color: string) =>
  L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 24px;
      height: 24px;
      background-color: ${color};
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  })

const onlineIcon = createIcon('#a6e3a1')
const offlineIcon = createIcon('#f38ba8')
const unknownIcon = createIcon('#7f849c')
const selectedIcon = createIcon('#89b4fa')

function getNodeStatus(node: Node, onlineHours: number): 'online' | 'offline' | 'unknown' {
  if (!node.last_heard) return 'unknown'
  const lastHeard = new Date(node.last_heard)
  const threshold = new Date(Date.now() - onlineHours * 60 * 60 * 1000)
  return lastHeard > threshold ? 'online' : 'offline'
}

function getIcon(node: Node, isSelected: boolean, onlineHours: number) {
  if (isSelected) return selectedIcon
  const status = getNodeStatus(node, onlineHours)
  if (status === 'online') return onlineIcon
  if (status === 'offline') return offlineIcon
  return unknownIcon
}

// Component to handle map center changes
function MapCenterHandler({ node }: { node: Node | null }) {
  const map = useMap()

  useEffect(() => {
    if (node?.latitude && node?.longitude) {
      map.flyTo([node.latitude, node.longitude], 14, { duration: 0.5 })
    }
  }, [node, map])

  return null
}

export default function MapContainer() {
  const { enabledSourceIds, showActiveOnly, activeHours, onlineHours, selectedNode, setSelectedNode } = useDataContext()

  // Load persisted settings from localStorage
  const [tilesetId, setTilesetId] = useState<TilesetId>(() =>
    loadSetting(STORAGE_KEY_TILESET, DEFAULT_TILESET_ID)
  )
  const [showRoutes, setShowRoutes] = useState<boolean>(() =>
    loadSetting(STORAGE_KEY_SHOW_ROUTES, true)
  )
  const [enabledRoles, setEnabledRoles] = useState<Set<string>>(() => {
    const stored = loadSetting<string[] | null>(STORAGE_KEY_ENABLED_ROLES, null)
    return stored ? new Set(stored) : new Set<string>()
  })
  const [rolesInitialized, setRolesInitialized] = useState(false)
  const [showCoverage, setShowCoverage] = useState<boolean>(() =>
    loadSetting(STORAGE_KEY_SHOW_COVERAGE, false)
  )
  const [showPositionHistory, setShowPositionHistory] = useState<boolean>(() =>
    loadSetting(STORAGE_KEY_SHOW_POSITION_HISTORY, false)
  )
  const [positionHistoryDays, setPositionHistoryDays] = useState<number>(() =>
    loadSetting(STORAGE_KEY_POSITION_HISTORY_DAYS, 7)
  )

  const tileset = getTilesetById(tilesetId)

  // Coverage data queries
  const { data: coverageConfig } = useQuery({
    queryKey: ['coverage-config'],
    queryFn: fetchCoverageConfig,
  })

  const { data: coverageCells = [] } = useQuery({
    queryKey: ['coverage-cells'],
    queryFn: fetchCoverageCells,
    enabled: showCoverage && (coverageConfig?.enabled ?? false) && (coverageConfig?.cell_count ?? 0) > 0,
  })

  // Position history for heatmap
  const { data: positionHistory = [] } = useQuery({
    queryKey: ['position-history', positionHistoryDays],
    queryFn: () => fetchPositionHistory({ lookback_days: positionHistoryDays }),
    enabled: showPositionHistory,
  })

  const { data: allNodes = [] } = useNodes({
    activeOnly: showActiveOnly,
    activeHours: showActiveOnly ? activeHours : undefined,
  })

  // Use same time filtering as nodes - default to activeHours, or 24h if not filtering
  const { data: traceroutes = [] } = useTraceroutes(showActiveOnly ? activeHours : 24)

  // Initialize enabled roles when first load - if no stored value, enable all
  useEffect(() => {
    if (!rolesInitialized && allNodes.length > 0) {
      const storedRoles = localStorage.getItem(STORAGE_KEY_ENABLED_ROLES)
      if (storedRoles === null) {
        // First time - enable all unique roles
        const uniqueRoles = new Set(allNodes.map(n => n.role).filter((r): r is string => r !== null))
        setEnabledRoles(uniqueRoles)
      }
      setRolesInitialized(true)
    }
  }, [allNodes, rolesInitialized])

  // Persist settings to localStorage
  const handleTilesetChange = useCallback((id: TilesetId) => {
    setTilesetId(id)
    saveSetting(STORAGE_KEY_TILESET, id)
  }, [])

  const handleShowRoutesChange = useCallback((show: boolean) => {
    setShowRoutes(show)
    saveSetting(STORAGE_KEY_SHOW_ROUTES, show)
  }, [])

  const handleEnabledRolesChange = useCallback((roles: Set<string>) => {
    setEnabledRoles(roles)
    saveSetting(STORAGE_KEY_ENABLED_ROLES, Array.from(roles))
  }, [])

  const handleShowCoverageChange = useCallback((show: boolean) => {
    setShowCoverage(show)
    saveSetting(STORAGE_KEY_SHOW_COVERAGE, show)
  }, [])

  const handleShowPositionHistoryChange = useCallback((show: boolean) => {
    setShowPositionHistory(show)
    saveSetting(STORAGE_KEY_SHOW_POSITION_HISTORY, show)
  }, [])

  const handlePositionHistoryDaysChange = useCallback((days: number) => {
    setPositionHistoryDays(days)
    saveSetting(STORAGE_KEY_POSITION_HISTORY_DAYS, days)
  }, [])

  // Filter by enabled sources, roles, and deduplicate (same logic as Sidebar)
  const deduplicatedNodes = useMemo(() => {
    const filteredNodes = allNodes.filter((node) => {
      // Filter by source
      if (!enabledSourceIds.has(node.source_id)) return false
      // Filter by role (if no role, show if any roles are enabled)
      if (enabledRoles.size > 0 && node.role && !enabledRoles.has(node.role)) return false
      return true
    })

    const nodeMap = new Map<string, Node>()
    for (const node of filteredNodes) {
      const key = node.node_id || `num_${node.node_num}`
      const existing = nodeMap.get(key)
      if (!existing) {
        nodeMap.set(key, node)
      } else {
        const existingTime = existing.last_heard ? new Date(existing.last_heard).getTime() : 0
        const newTime = node.last_heard ? new Date(node.last_heard).getTime() : 0
        if (newTime > existingTime) {
          nodeMap.set(key, node)
        }
      }
    }

    return Array.from(nodeMap.values())
  }, [allNodes, enabledSourceIds, enabledRoles])

  // Filter nodes with positions
  const nodesWithPosition = useMemo(
    () => deduplicatedNodes.filter((n): n is Node & { latitude: number; longitude: number } =>
      n.latitude !== null && n.longitude !== null
    ),
    [deduplicatedNodes]
  )

  // Calculate map center
  const center = useMemo<[number, number]>(() => {
    if (selectedNode?.latitude && selectedNode?.longitude) {
      return [selectedNode.latitude, selectedNode.longitude]
    }
    if (nodesWithPosition.length > 0) {
      const avgLat = nodesWithPosition.reduce((sum, n) => sum + n.latitude, 0) / nodesWithPosition.length
      const avgLng = nodesWithPosition.reduce((sum, n) => sum + n.longitude, 0) / nodesWithPosition.length
      return [avgLat, avgLng]
    }
    return [39.8283, -98.5795] // Center of US
  }, [nodesWithPosition, selectedNode])

  // Build node position lookup by node_num for traceroute rendering
  // Use ALL nodes (not filtered) so traceroutes can render even if some nodes are filtered out
  const nodePositionsByNum = useMemo(() => {
    const map = new Map<number, { lat: number; lng: number }>()
    for (const node of allNodes) {
      if (node.latitude !== null && node.longitude !== null) {
        // Only add if we don't have this node_num yet, or update with most recent
        const existing = map.get(node.node_num)
        if (!existing) {
          map.set(node.node_num, { lat: node.latitude, lng: node.longitude })
        }
      }
    }
    return map
  }, [allNodes])

  // Build traceroute segments with usage weighting (like MeshMonitor)
  // Processes both forward route and route_back for complete path visualization
  const routeSegments = useMemo(() => {
    if (!showRoutes) return []

    // Track segment usage counts
    const segmentUsage = new Map<string, number>()
    const segmentPositions = new Map<string, { from: [number, number]; to: [number, number] }>()

    // Helper to add segments from a node sequence
    const addSegmentsFromSequence = (nodeNums: number[]) => {
      for (let i = 0; i < nodeNums.length - 1; i++) {
        const fromNum = nodeNums[i]
        const toNum = nodeNums[i + 1]

        // Skip broadcast address (4294967295) - it's a placeholder for unknown hops
        if (fromNum === 4294967295 || toNum === 4294967295) continue

        const fromPos = nodePositionsByNum.get(fromNum)
        const toPos = nodePositionsByNum.get(toNum)

        if (fromPos && toPos) {
          // Use sorted key so A->B and B->A are the same segment
          const segmentKey = [fromNum, toNum].sort((a, b) => a - b).join('-')
          segmentUsage.set(segmentKey, (segmentUsage.get(segmentKey) || 0) + 1)

          if (!segmentPositions.has(segmentKey)) {
            segmentPositions.set(segmentKey, {
              from: [fromPos.lat, fromPos.lng],
              to: [toPos.lat, toPos.lng],
            })
          }
        }
      }
    }

    for (const trace of traceroutes) {
      // Skip incomplete traceroutes (no route_back means no response received)
      // These are failed traceroutes that shouldn't be rendered
      if (trace.route_back === null) continue

      // Forward path: from_node_num -> route hops -> to_node_num
      // This is the path from requester to responder
      const forwardPath = [trace.from_node_num, ...trace.route, trace.to_node_num]
      addSegmentsFromSequence(forwardPath)

      // Return path: to_node_num -> route_back hops -> from_node_num
      // This is the path from responder back to requester
      if (trace.route_back.length > 0) {
        const returnPath = [trace.to_node_num, ...trace.route_back, trace.from_node_num]
        addSegmentsFromSequence(returnPath)
      }
    }

    // Convert to array with weight calculation
    return Array.from(segmentPositions.entries()).map(([key, positions]) => {
      const usage = segmentUsage.get(key) || 1
      // Weight: base 2, +0.3 per usage, max 8
      const weight = Math.min(2 + usage * 0.3, 8)
      // Opacity: more usage = more visible
      const opacity = Math.min(0.5 + usage * 0.03, 0.9)

      return {
        id: key,
        positions: [positions.from, positions.to] as [number, number][],
        weight,
        opacity,
        usage,
      }
    })
  }, [traceroutes, nodePositionsByNum, showRoutes])

  return (
    <div className="map-container">
      <MapControls
        tilesetId={tilesetId}
        onTilesetChange={handleTilesetChange}
        showRoutes={showRoutes}
        onShowRoutesChange={handleShowRoutesChange}
        enabledRoles={enabledRoles}
        onEnabledRolesChange={handleEnabledRolesChange}
        showCoverage={showCoverage}
        onShowCoverageChange={handleShowCoverageChange}
        coverageEnabled={coverageConfig?.enabled ?? false}
        coverageCellCount={coverageConfig?.cell_count ?? 0}
        showPositionHistory={showPositionHistory}
        onShowPositionHistoryChange={handleShowPositionHistoryChange}
        positionHistoryDays={positionHistoryDays}
        onPositionHistoryDaysChange={handlePositionHistoryDaysChange}
        positionHistoryCount={positionHistory.length}
      />
      <LeafletMapContainer
        center={center}
        zoom={nodesWithPosition.length > 0 ? 10 : 4}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          key={tileset.id}
          attribution={tileset.attribution}
          url={tileset.url}
          maxZoom={tileset.maxZoom}
        />
        <MapCenterHandler node={selectedNode} />

        {/* Coverage overlay - Image rendered from grid */}
        {showCoverage && coverageCells.length > 0 && (
          <CoverageImageOverlay cells={coverageCells} blur={8} />
        )}

        {/* Position history heatmap */}
        {showPositionHistory && positionHistory.length > 0 && (
          <HeatmapLayer points={positionHistory} radius={25} blur={15} />
        )}

        {/* Traceroute segments - weighted by usage */}
        {routeSegments.map((segment) => (
          <Polyline
            key={segment.id}
            positions={segment.positions}
            pathOptions={{
              color: '#cba6f7',
              weight: segment.weight,
              opacity: segment.opacity,
            }}
          />
        ))}

        {nodesWithPosition.map((node) => {
          const isSelected = selectedNode?.id === node.id
          const displayName = node.long_name || node.short_name || node.node_id || `Node ${node.node_num}`

          return (
            <Marker
              key={node.id}
              position={[node.latitude, node.longitude]}
              icon={getIcon(node, isSelected, onlineHours)}
              eventHandlers={{
                click: () => setSelectedNode(isSelected ? null : node),
              }}
            >
              <Popup>
                <div style={{ minWidth: '150px' }}>
                  <strong style={{ fontSize: '1rem' }}>{displayName}</strong>
                  {node.short_name && (
                    <span style={{ marginLeft: '0.5rem', opacity: 0.7 }}>[{node.short_name}]</span>
                  )}
                  <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', opacity: 0.8 }}>
                    <div>Source: {node.source_name}</div>
                    <div>Position: {node.latitude.toFixed(5)}, {node.longitude.toFixed(5)}</div>
                    {node.last_heard && (
                      <div>Last heard: {new Date(node.last_heard).toLocaleString()}</div>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </LeafletMapContainer>

      {/* Coverage Legend */}
      {showCoverage && coverageCells.length > 0 && (
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
            {COVERAGE_LEGEND.map(({ color, label }) => (
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
  )
}
