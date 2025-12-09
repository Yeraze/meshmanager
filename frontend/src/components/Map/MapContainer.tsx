import { useEffect, useMemo, useState } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useNodes } from '../../hooks/useNodes'
import { useDataContext } from '../../contexts/DataContext'
import { getTilesetById, DEFAULT_TILESET_ID, type TilesetId } from '../../config/tilesets'
import TilesetSelector from './TilesetSelector'
import type { Node } from '../../types/api'
import 'leaflet/dist/leaflet.css'

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

function getNodeStatus(node: Node): 'online' | 'offline' | 'unknown' {
  if (!node.last_heard) return 'unknown'
  const lastHeard = new Date(node.last_heard)
  const hourAgo = new Date(Date.now() - 60 * 60 * 1000)
  return lastHeard > hourAgo ? 'online' : 'offline'
}

function getIcon(node: Node, isSelected: boolean) {
  if (isSelected) return selectedIcon
  const status = getNodeStatus(node)
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
  const { enabledSourceIds, showActiveOnly, selectedNode, setSelectedNode } = useDataContext()
  const [tilesetId, setTilesetId] = useState<TilesetId>(DEFAULT_TILESET_ID)
  const tileset = getTilesetById(tilesetId)

  const { data: allNodes = [] } = useNodes({
    activeOnly: showActiveOnly,
  })

  // Filter by enabled sources and deduplicate (same logic as Sidebar)
  const deduplicatedNodes = useMemo(() => {
    const filteredNodes = allNodes.filter((node) => enabledSourceIds.has(node.source_id))

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
  }, [allNodes, enabledSourceIds])

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

  return (
    <div className="map-container">
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

        {nodesWithPosition.map((node) => {
          const isSelected = selectedNode?.id === node.id
          const displayName = node.long_name || node.short_name || node.node_id || `Node ${node.node_num}`

          return (
            <Marker
              key={node.id}
              position={[node.latitude, node.longitude]}
              icon={getIcon(node, isSelected)}
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
      <TilesetSelector
        selectedTilesetId={tilesetId}
        onTilesetChange={setTilesetId}
      />
    </div>
  )
}
