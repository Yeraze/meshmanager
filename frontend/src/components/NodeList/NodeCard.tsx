import { useMemo } from 'react'
import { useDataContext } from '../../contexts/DataContext'
import { getRoleName } from '../../utils/meshtastic'
import type { Node } from '../../types/api'

interface NodeCardProps {
  node: Node
}

export default function NodeCard({ node }: NodeCardProps) {
  const { selectedNode, setSelectedNode } = useDataContext()
  const isSelected = selectedNode?.id === node.id

  const status = useMemo(() => {
    if (!node.last_heard) return 'unknown'
    const lastHeard = new Date(node.last_heard)
    const hourAgo = new Date(Date.now() - 60 * 60 * 1000)
    return lastHeard > hourAgo ? 'online' : 'offline'
  }, [node.last_heard])

  const lastHeardText = useMemo(() => {
    if (!node.last_heard) return 'Never'
    const lastHeard = new Date(node.last_heard)
    const now = new Date()
    const diffMs = now.getTime() - lastHeard.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }, [node.last_heard])

  const roleName = node.role ? getRoleName(node.role) : null

  const displayName = node.long_name || node.short_name || node.node_id || `Node ${node.node_num}`

  return (
    <div
      className={`node-card ${isSelected ? 'selected' : ''}`}
      onClick={() => setSelectedNode(isSelected ? null : node)}
    >
      <div className="node-card-header">
        <span className={`node-status ${status}`} />
        <span className="node-name">{displayName}</span>
        {node.short_name && (
          <span className="node-short-name">{node.short_name}</span>
        )}
      </div>
      <div className="node-details">
        <span className="node-info">
          {roleName && <span className="node-role">{roleName}</span>}
          {node.snr !== null && (
            <span className="node-signal" title="SNR">
              {node.snr > 0 ? '+' : ''}{node.snr.toFixed(1)} dB
            </span>
          )}
          {node.hops_away !== null && node.hops_away > 0 && (
            <span className="node-hops" title="Hops away">
              {node.hops_away} hop{node.hops_away !== 1 ? 's' : ''}
            </span>
          )}
        </span>
        <span className="node-time">{lastHeardText}</span>
      </div>
    </div>
  )
}
