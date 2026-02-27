import { useMemo, useRef, useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchConnections } from '../../services/api'
import { getHardwareInfo, getRoleName } from '../../utils/meshtastic'
import styles from './NodeConnections.module.css'
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d'
import EdgeDetailModal from './EdgeDetailModal'

interface GraphNode {
  id: number
  node_num?: number
  short_name?: string | null
  name?: string
  long_name?: string
  hw_model?: string
  role?: string
  last_heard?: string | null
  latitude?: number
  longitude?: number
  x?: number
  y?: number
  fx?: number
  fy?: number
}

interface GraphLink {
  source: number | GraphNode
  target: number | GraphNode
  value: number
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

interface NodeConnectionsProps {
  nodeNum?: number
  hours?: number
}

export default function NodeConnections({ nodeNum, hours = 24 }: NodeConnectionsProps) {
  const [selectedNode, setSelectedNode] = useState<number | null>(null)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null)
  const [clickedEdge, setClickedEdge] = useState<{ nodeA: number; nodeB: number } | null>(null)
  const graphRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined)
  const containerRef = useRef<HTMLDivElement>(null)
  const mousePositionRef = useRef<{ x: number; y: number } | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['connections', nodeNum, hours],
    queryFn: () => fetchConnections(hours, nodeNum),
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: false,
  })

  // Track mouse position for tooltip
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        mousePositionRef.current = {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        }
      }
    }

    const container = containerRef.current
    if (container) {
      container.addEventListener('mousemove', handleMouseMove)
      return () => {
        container.removeEventListener('mousemove', handleMouseMove)
      }
    }
  }, [])

  // Transform data for force graph
  const graphData = useMemo(() => {
    if (!data?.nodes || !data?.edges) {
      return { nodes: [], links: [] }
    }
    const nodeMap = new Map(data.nodes.map((n) => [n.id, n]))

    // Build links using node IDs (react-force-graph-2d will resolve them)
    const links = data.edges
      .filter((edge) => {
        return edge?.source !== undefined && edge?.target !== undefined && 
               nodeMap.has(edge.source) && nodeMap.has(edge.target)
      })
      .map((edge) => ({
        source: edge.source, // Use ID
        target: edge.target, // Use ID
        value: edge.usage || 1,
      }))

    // Ensure nodes have all necessary properties
    const nodes = data.nodes.map((node) => ({
      ...node,
      id: node.id ?? node.node_num,
      short_name: node.short_name || null,
      name: node.name || node.long_name || `Node ${node.id ?? node.node_num}`,
    }))
    
    return { nodes, links }
  }, [data])

  // Calculate connection counts from edges (before graphData transformation)
  const nodeConnectionCounts = useMemo(() => {
    const counts = new Map<number, number>()
    if (data?.edges) {
      data.edges.forEach((edge) => {
        if (edge.source !== undefined) {
          counts.set(edge.source, (counts.get(edge.source) || 0) + 1)
        }
        if (edge.target !== undefined) {
          counts.set(edge.target, (counts.get(edge.target) || 0) + 1)
        }
      })
    }
    return counts
  }, [data])


  // Set initial zoom level when graph loads
  useEffect(() => {
    if (graphData.nodes.length === 0) return

    const timer = setTimeout(() => {
      if (graphRef.current) {
        graphRef.current.zoom(0.5, 0) // Start zoomed out to 50%, no animation
      }
    }, 100)

    return () => clearTimeout(timer)
  }, [graphData])

  // Track if forces have been configured (reset when graphData changes)
  const forcesConfigured = useRef(false)
  
  // Configure forces when graphData changes or graph is ready
  useEffect(() => {
    if (graphData.nodes.length === 0) return

    // Reset flag when graphData changes
    forcesConfigured.current = false

    // Try to configure forces with retries
    const configureForces = () => {
      if (graphRef.current && !forcesConfigured.current) {
        // Use d3Force method directly to configure forces
        const charge = graphRef.current.d3Force('charge')
        const link = graphRef.current.d3Force('link')
        const center = graphRef.current.d3Force('center')
        const collision = graphRef.current.d3Force('collision')
        
        if (charge || link || center) {
          // Strong repulsion so all nodes push away from each other
          if (charge) {
            charge.strength(-500)
          }
          
          // Longer link distance
          if (link) {
            link.distance(100)
          }
          
          // Stronger center force to ensure graph is centered
          if (center) {
            center.strength(0.3)
          }
          
          // Small collision radius to prevent overlap
          if (collision) {
            collision.radius(10)
          }
          
          forcesConfigured.current = true
          
          // Restart simulation with higher alpha to give it energy to spread out
          graphRef.current.d3ReheatSimulation()
          return true
        }
      }
      return false
    }

    // Try immediately
    if (configureForces()) return

    // If not ready, try after a short delay
    const timeoutId = setTimeout(() => {
      if (!configureForces()) {
        // If still not ready, try one more time after a longer delay
        setTimeout(() => {
          configureForces()
        }, 500)
      }
    }, 100)

    return () => clearTimeout(timeoutId)
  }, [graphData])

  // Auto-arrange handler
  const handleAutoArrange = () => {
    if (graphRef.current) {
      // Clear fixed positions and restart simulation
      graphData.nodes.forEach((node) => {
        // fx/fy are runtime properties added by ForceGraph2D
        (node as { fx?: number; fy?: number }).fx = undefined;
        (node as { fx?: number; fy?: number }).fy = undefined
      })
      // Use d3Force method directly to configure forces (match the values above)
      graphRef.current.d3Force('charge')?.strength(-500)
      graphRef.current.d3Force('link')?.distance(100)
      graphRef.current.d3Force('center')?.strength(0.3)
      graphRef.current.d3Force('collision')?.radius(10)
      // Restart simulation
      graphRef.current.d3ReheatSimulation()
    }
  }

  const handleLinkClick = useCallback((link: GraphLink) => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source
    const targetId = typeof link.target === 'object' ? link.target.id : link.target
    if (sourceId !== undefined && targetId !== undefined) {
      setClickedEdge({ nodeA: sourceId, nodeB: targetId })
    }
  }, [])

  const handleLinkHover = useCallback((link: GraphLink | null) => {
    const container = containerRef.current
    if (container) {
      container.style.cursor = link ? 'pointer' : ''
    }
  }, [])

  // Manual edge proximity detection for clicks near nodes where the shadow canvas
  // paints the node on top of the link, preventing onLinkClick from firing.
  const findNearestLink = useCallback((screenX: number, screenY: number): GraphLink | null => {
    if (!graphRef.current || !graphData.links.length) return null

    const { x: gx, y: gy } = graphRef.current.screen2GraphCoords(screenX, screenY)
    // Compute threshold in graph coords: 15px worth of graph distance at current zoom
    const { x: gx2 } = graphRef.current.screen2GraphCoords(screenX + 15, screenY)
    const threshold = Math.abs(gx2 - gx)

    let bestDist = Infinity
    let bestLink: GraphLink | null = null

    for (const link of graphData.links) {
      const src = link.source as unknown as GraphNode
      const tgt = link.target as unknown as GraphNode
      if (!src?.x || !src?.y || !tgt?.x || !tgt?.y) continue

      // Point-to-segment distance
      const dx = tgt.x - src.x
      const dy = tgt.y - src.y
      const lenSq = dx * dx + dy * dy
      let dist: number
      if (lenSq === 0) {
        dist = Math.hypot(gx - src.x, gy - src.y)
      } else {
        const t = Math.max(0, Math.min(1, ((gx - src.x) * dx + (gy - src.y) * dy) / lenSq))
        dist = Math.hypot(gx - (src.x + t * dx), gy - (src.y + t * dy))
      }

      if (dist < bestDist) {
        bestDist = dist
        bestLink = link
      }
    }

    return bestDist <= threshold ? bestLink : null
  }, [graphData.links])

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className="loading-spinner" />
        <p>Loading connections...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        Error loading connections: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className={styles.emptyContainer}>
        No connections found for the selected time period.
      </div>
    )
  }

  const selectedNodeData = selectedNode ? data.nodes.find((n) => n.id === selectedNode) : null

  return (
    <div className={styles.connectionsContainer}>
      <div className={styles.infoPanel}>
        <div className={styles.infoTitle}>Network Graph</div>
        <div className={styles.infoStats}>
          {data.nodes.length} nodes, {data.edges.length} connections
        </div>
        <button className={styles.autoArrangeButton} onClick={handleAutoArrange}>
          Auto Arrange
        </button>
        {selectedNodeData && (
          <div className={styles.selectedNodeInfo}>
            <div className={styles.selectedNodeTitle}>Selected Node:</div>
            <div className={styles.selectedNodeDetails}>
              <div className={styles.selectedNodeName}>{selectedNodeData.name}</div>
              {selectedNodeData.short_name && (
                <div className={styles.selectedNodeSubtext}>{selectedNodeData.short_name}</div>
              )}
              {selectedNodeData.hw_model && (() => {
                const hardwareInfo = getHardwareInfo(selectedNodeData.hw_model)
                return hardwareInfo ? (
                  <div className={styles.selectedNodeSubtext}>{hardwareInfo.displayName}</div>
                ) : null
              })()}
              {selectedNodeData.role !== undefined && (
                <div className={styles.selectedNodeSubtext}>
                  Role: {getRoleName(selectedNodeData.role)}
                </div>
              )}
              <div className={styles.selectedNodeSubtext}>
                Connections: {selectedNode ? (nodeConnectionCounts.get(selectedNode) || 0) : 0}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className={styles.graphWrapper} ref={containerRef}>
        {graphData && graphData.nodes && graphData.nodes.length > 0 ? (
            <div style={{ position: 'relative', width: '100%', height: '100%' }}>
              <ForceGraph2D<GraphNode, GraphLink>
              ref={graphRef}
              graphData={graphData as GraphData}
              nodeId="id"
              nodeColor={(node: GraphNode) => {
                if (!node) return '#cdd6f4'
                if (node.id === nodeNum) return '#cba6f7' // lavender for origin node
                // Color by connection count (hop count)
                const count = nodeConnectionCounts.get(node.id) || 0
                if (count === 0) return '#6c7086' // muted for no connections
                if (count <= 2) return '#89b4fa' // blue for 1-2 connections
                if (count <= 5) return '#a6e3a1' // green for 3-5 connections
                if (count <= 10) return '#f9e2af' // yellow for 6-10 connections
                return '#f38ba8' // red for 10+ connections
              }}
                    nodeVal={(node: GraphNode) => {
                      const count = nodeConnectionCounts.get(node?.id) || 0
                      return 6 + Math.sqrt(count) * 4 // Doubled size, more noticeable differences
                    }}
              linkSource="source"
              linkTarget="target"
              linkColor={() => 'rgba(255, 255, 255, 0.9)'}
              linkWidth={2}
              linkDirectionalArrowLength={6}
              linkDirectionalArrowRelPos={1}
              linkVisibility={true}
              linkCurvature={0}
              nodeLabel={(node: GraphNode) => node?.short_name || node?.name || `Node ${node?.id || '?'}`}
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
                if (!node || !node.x || !node.y) return
                
                // Draw label below the node
                const label = node.short_name || node.name || `Node ${node.id || node.node_num || '?'}`
                if (!label) return
                
                // Calculate node radius (same as nodeVal calculation)
                const count = nodeConnectionCounts.get(node?.id) || 0
                const nodeRadius = 6 + Math.sqrt(count) * 4
                
                ctx.save()
                // Scale font size with zoom - larger when zoomed OUT (inverse)
                const scale = Math.max(0.5, Math.min(2, globalScale || 1))
                const fontSize = 16 / scale
                ctx.font = `bold ${fontSize}px Arial, sans-serif`
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                
                // Position label below the node (radius + small gap)
                const labelY = node.y + nodeRadius + 3
                
                // White text with black outline for visibility
                ctx.strokeStyle = '#000000'
                ctx.lineWidth = 3
                ctx.strokeText(label, node.x, labelY)
                ctx.fillStyle = '#ffffff'
                ctx.fillText(label, node.x, labelY)
                ctx.restore()
              }}
              onNodeClick={(node: GraphNode | null, event: MouseEvent) => {
                // Check if the click was actually closer to an edge than the node center
                const nearLink = findNearestLink(event.offsetX, event.offsetY)
                if (nearLink && graphRef.current) {
                  const { x: gx, y: gy } = graphRef.current.screen2GraphCoords(event.offsetX, event.offsetY)
                  const nodeDist = node ? Math.hypot(gx - (node.x || 0), gy - (node.y || 0)) : Infinity
                  const src = nearLink.source as GraphNode
                  const tgt = nearLink.target as GraphNode
                  if (src?.x != null && src?.y != null && tgt?.x != null && tgt?.y != null) {
                    const dx = tgt.x - src.x, dy = tgt.y - src.y
                    const lenSq = dx * dx + dy * dy
                    const t = lenSq === 0 ? 0 : Math.max(0, Math.min(1, ((gx - src.x) * dx + (gy - src.y) * dy) / lenSq))
                    const linkDist = Math.hypot(gx - (src.x + t * dx), gy - (src.y + t * dy))
                    // If click is closer to the edge line than to the node center, open edge modal
                    if (linkDist < nodeDist * 0.7) {
                      handleLinkClick(nearLink)
                      return
                    }
                  }
                }
                if (node) {
                  setSelectedNode(node.id === selectedNode ? null : node.id)
                }
              }}
              onNodeHover={(node: GraphNode | null) => {
                if (node) {
                  setHoveredNode(node)
                  if (mousePositionRef.current) {
                    setHoverPosition(mousePositionRef.current)
                  }
                } else {
                  setHoveredNode(null)
                  setHoverPosition(null)
                }
              }}
              onBackgroundClick={(event: MouseEvent) => {
                // Check if the click was near a link (shadow canvas may have missed it)
                const nearLink = findNearestLink(event.offsetX, event.offsetY)
                if (nearLink) {
                  handleLinkClick(nearLink)
                  return
                }
                setSelectedNode(null)
                setHoveredNode(null)
                setHoverPosition(null)
              }}
              backgroundColor="var(--ctp-base)"
              enableZoomInteraction={true}
              enablePanInteraction={true}
              enableNodeDrag={true}
              onNodeDragEnd={(node: GraphNode) => {
                // Fix node position without restarting simulation
                if (node) {
                  node.fx = node.x
                  node.fy = node.y
                }
              }}
              onEngineStop={() => {
                // Simulation stopped
              }}
              linkHoverPrecision={8}
              onLinkClick={handleLinkClick}
              onLinkHover={handleLinkHover}
              />
            </div>
        ) : (
          <div className={styles.emptyContainer}>No nodes to display</div>
        )}
        {hoveredNode && hoverPosition && (
          <div
            className={styles.hoverTooltip}
            style={{
              left: `${hoverPosition.x}px`,
              top: `${hoverPosition.y}px`,
            }}
          >
            <div className={styles.tooltipTitle}>{hoveredNode.name || `Node ${hoveredNode.id}`}</div>
            {hoveredNode.short_name && <div className={styles.tooltipText}>{hoveredNode.short_name}</div>}
            {hoveredNode.role !== undefined && (
              <div className={styles.tooltipText}>Role: {getRoleName(hoveredNode.role)}</div>
            )}
            <div className={styles.tooltipText}>
              Connections: {nodeConnectionCounts.get(hoveredNode.id) || 0}
            </div>
          </div>
        )}
        <div className={styles.legend}>
          <div className={styles.legendTitle}>Connections</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#cba6f7' }} /> This Node</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#6c7086' }} /> None</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#89b4fa' }} /> 1-2</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#a6e3a1' }} /> 3-5</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#f9e2af' }} /> 6-10</div>
          <div className={styles.legendItem}><span className={styles.legendDot} style={{ background: '#f38ba8' }} /> 10+</div>
        </div>
      </div>

      {clickedEdge && (
        <EdgeDetailModal
          nodeA={clickedEdge.nodeA}
          nodeB={clickedEdge.nodeB}
          hours={hours}
          onClose={() => setClickedEdge(null)}
        />
      )}
    </div>
  )
}

