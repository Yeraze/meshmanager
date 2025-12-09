import { useMemo, useEffect, useState, useRef } from 'react'
import { useNodes } from '../../hooks/useNodes'
import { useSources } from '../../hooks/useSources'
import { useDataContext } from '../../contexts/DataContext'
import NodeList from '../NodeList/NodeList'
import type { Node } from '../../types/api'

export default function Sidebar() {
  const { enabledSourceIds, toggleSource, enableAllSources, showActiveOnly, setShowActiveOnly } = useDataContext()
  const [showSourceDropdown, setShowSourceDropdown] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: sources = [], isLoading: sourcesLoading } = useSources()
  const { data: allNodes = [], isLoading: nodesLoading } = useNodes({
    activeOnly: showActiveOnly,
  })

  // Initialize enabled sources when sources load
  useEffect(() => {
    if (sources.length > 0 && enabledSourceIds.size === 0) {
      enableAllSources(sources.map((s) => s.id))
    }
  }, [sources, enabledSourceIds.size, enableAllSources])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as globalThis.Node)) {
        setShowSourceDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter nodes by enabled sources and deduplicate by node_id
  const deduplicatedNodes = useMemo(() => {
    // Filter by enabled sources
    const filteredNodes = allNodes.filter((node) => enabledSourceIds.has(node.source_id))

    // Group by node identifier (prefer node_id, fallback to node_num)
    const nodeMap = new Map<string, Node>()

    for (const node of filteredNodes) {
      const key = node.node_id || `num_${node.node_num}`

      const existing = nodeMap.get(key)
      if (!existing) {
        nodeMap.set(key, node)
      } else {
        // Keep the one with more recent last_heard
        const existingTime = existing.last_heard ? new Date(existing.last_heard).getTime() : 0
        const newTime = node.last_heard ? new Date(node.last_heard).getTime() : 0

        if (newTime > existingTime) {
          nodeMap.set(key, node)
        }
      }
    }

    // Convert to array and sort by last_heard (most recent first)
    return Array.from(nodeMap.values()).sort((a, b) => {
      const aTime = a.last_heard ? new Date(a.last_heard).getTime() : 0
      const bTime = b.last_heard ? new Date(b.last_heard).getTime() : 0
      return bTime - aTime
    })
  }, [allNodes, enabledSourceIds])

  // Apply search filter
  const filteredNodes = useMemo(() => {
    if (!searchFilter.trim()) return deduplicatedNodes

    const search = searchFilter.toLowerCase().trim()
    return deduplicatedNodes.filter((node) => {
      const longName = node.long_name?.toLowerCase() || ''
      const shortName = node.short_name?.toLowerCase() || ''
      const nodeId = node.node_id?.toLowerCase() || ''
      return longName.includes(search) || shortName.includes(search) || nodeId.includes(search)
    })
  }, [deduplicatedNodes, searchFilter])

  const isLoading = sourcesLoading || nodesLoading
  const enabledCount = enabledSourceIds.size
  const totalSources = sources.length

  return (
    <aside className="sidebar">
      <div className="node-list-header">
        <h2>Nodes ({filteredNodes.length}{searchFilter && ` / ${deduplicatedNodes.length}`})</h2>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={showActiveOnly}
            onChange={(e) => setShowActiveOnly(e.target.checked)}
          />
          Active only
        </label>
      </div>

      {/* Search filter */}
      <div className="node-search">
        <input
          type="text"
          className="node-search-input"
          placeholder="Search nodes..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
        />
        {searchFilter && (
          <button
            className="node-search-clear"
            onClick={() => setSearchFilter('')}
            title="Clear search"
          >
            ×
          </button>
        )}
      </div>

      {/* Source filter dropdown */}
      <div className="source-filter" ref={dropdownRef}>
        <button
          className="source-filter-button"
          onClick={() => setShowSourceDropdown(!showSourceDropdown)}
        >
          <span>Sources ({enabledCount}/{totalSources})</span>
          <span className="source-filter-chevron">{showSourceDropdown ? '▲' : '▼'}</span>
        </button>

        {showSourceDropdown && (
          <div className="source-filter-dropdown">
            <div className="source-filter-actions">
              <button
                className="btn btn-sm btn-ghost"
                onClick={() => enableAllSources(sources.map((s) => s.id))}
              >
                All
              </button>
              <button
                className="btn btn-sm btn-ghost"
                onClick={() => enableAllSources([])}
              >
                None
              </button>
            </div>
            {sources.map((source) => (
              <label key={source.id} className="source-filter-item">
                <input
                  type="checkbox"
                  checked={enabledSourceIds.has(source.id)}
                  onChange={() => toggleSource(source.id)}
                />
                <span className={`source-status ${source.healthy ? 'healthy' : 'unhealthy'}`} />
                <span className="source-filter-name">{source.name}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="loading">
          <div className="loading-spinner" />
          Loading...
        </div>
      ) : deduplicatedNodes.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📡</div>
          <p>No nodes found</p>
          <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
            {sources.length === 0
              ? 'Add a source in Settings to get started'
              : enabledCount === 0
                ? 'Enable at least one source above'
                : 'No nodes match current filters'}
          </p>
        </div>
      ) : filteredNodes.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <p>No matching nodes</p>
          <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
            No nodes match "{searchFilter}"
          </p>
        </div>
      ) : (
        <div className="node-list">
          <NodeList nodes={filteredNodes} />
        </div>
      )}
    </aside>
  )
}
