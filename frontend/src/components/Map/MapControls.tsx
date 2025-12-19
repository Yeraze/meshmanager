import { useState, useRef, useEffect } from 'react'
import { getAllTilesets, getTilePreviewUrl, type TilesetId } from '../../config/tilesets'
import { useNodeRoles } from '../../hooks/useMapData'
import { getRoleName } from '../../utils/meshtastic'

interface MapControlsProps {
  tilesetId: TilesetId
  onTilesetChange: (id: TilesetId) => void
  showRoutes: boolean
  onShowRoutesChange: (show: boolean) => void
  enabledRoles: Set<string>
  onEnabledRolesChange: (roles: Set<string>) => void
  showCoverage: boolean
  onShowCoverageChange: (show: boolean) => void
  coverageEnabled: boolean
  coverageCellCount: number
  showUtilization: boolean
  onShowUtilizationChange: (show: boolean) => void
  utilizationEnabled: boolean
  utilizationCellCount: number
  showPositionHistory: boolean
  onShowPositionHistoryChange: (show: boolean) => void
  positionHistoryDays: number
  onPositionHistoryDaysChange: (days: number) => void
  positionHistoryCount: number
  showMessageActivity: boolean
  onShowMessageActivityChange: (show: boolean) => void
  messageActivityDays: number
  onMessageActivityDaysChange: (days: number) => void
  messageActivityCount: number
  showNodes: boolean
  onShowNodesChange: (show: boolean) => void
}

export default function MapControls({
  tilesetId,
  onTilesetChange,
  showRoutes,
  onShowRoutesChange,
  enabledRoles,
  onEnabledRolesChange,
  showCoverage,
  onShowCoverageChange,
  coverageEnabled,
  coverageCellCount,
  showUtilization,
  onShowUtilizationChange,
  utilizationEnabled,
  utilizationCellCount,
  showPositionHistory,
  onShowPositionHistoryChange,
  positionHistoryDays,
  onPositionHistoryDaysChange,
  positionHistoryCount,
  showMessageActivity,
  onShowMessageActivityChange,
  messageActivityDays,
  onMessageActivityDaysChange,
  messageActivityCount,
  showNodes,
  onShowNodesChange,
}: MapControlsProps) {
  const { data: allRoles = [] } = useNodeRoles()
  const tilesets = getAllTilesets()
  const [isTilesetOpen, setIsTilesetOpen] = useState(false)
  const [isRolesOpen, setIsRolesOpen] = useState(false)
  const tilesetRef = useRef<HTMLDivElement>(null)
  const rolesRef = useRef<HTMLDivElement>(null)

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (tilesetRef.current && !tilesetRef.current.contains(event.target as HTMLElement)) {
        setIsTilesetOpen(false)
      }
      if (rolesRef.current && !rolesRef.current.contains(event.target as HTMLElement)) {
        setIsRolesOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectedTileset = tilesets.find(t => t.id === tilesetId)

  const handleRoleToggle = (role: string) => {
    const newRoles = new Set(enabledRoles)
    if (newRoles.has(role)) {
      newRoles.delete(role)
    } else {
      newRoles.add(role)
    }
    onEnabledRolesChange(newRoles)
  }

  const handleSelectAll = () => {
    onEnabledRolesChange(new Set(allRoles))
  }

  const handleSelectNone = () => {
    onEnabledRolesChange(new Set())
  }

  return (
    <div className="map-controls">
      <div className="map-controls-row">
        {/* Tileset Selector */}
        <div className="map-control-group" ref={tilesetRef}>
          <label className="map-control-label">Map Style</label>
          <div className="map-control-dropdown">
            <button
              className="map-control-dropdown-button"
              onClick={() => setIsTilesetOpen(!isTilesetOpen)}
            >
              {selectedTileset?.name || 'Select style'}
              <span className="dropdown-arrow">{isTilesetOpen ? '\u25B2' : '\u25BC'}</span>
            </button>
            {isTilesetOpen && (
              <div className="map-control-dropdown-menu tileset-dropdown">
                {tilesets.map((tileset) => (
                  <button
                    key={tileset.id}
                    className={`tileset-option ${tilesetId === tileset.id ? 'active' : ''}`}
                    onClick={() => {
                      onTilesetChange(tileset.id)
                      setIsTilesetOpen(false)
                    }}
                  >
                    <div
                      className="tileset-option-preview"
                      style={{ backgroundImage: `url(${getTilePreviewUrl(tileset.url)})` }}
                    />
                    <span className="tileset-option-name">{tileset.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Show Routes Toggle */}
        <div className="map-control-group">
          <label className="map-control-label">Show Routes</label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={showRoutes}
              onChange={(e) => onShowRoutesChange(e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Show Nodes Toggle */}
        <div className="map-control-group">
          <label className="map-control-label">Show Nodes</label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={showNodes}
              onChange={(e) => onShowNodesChange(e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Coverage Overlay Toggle */}
        <div className="map-control-group">
          <label className="map-control-label">
            Coverage
            {coverageEnabled && coverageCellCount > 0 && (
              <span style={{ fontSize: '0.7rem', opacity: 0.7, marginLeft: '0.25rem' }}>
                ({coverageCellCount.toLocaleString()})
              </span>
            )}
          </label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={showCoverage}
              onChange={(e) => onShowCoverageChange(e.target.checked)}
              disabled={!coverageEnabled || coverageCellCount === 0}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Utilization Overlay Toggle */}
        <div className="map-control-group">
          <label className="map-control-label">
            Utilization
            {utilizationEnabled && utilizationCellCount > 0 && (
              <span style={{ fontSize: '0.7rem', opacity: 0.7, marginLeft: '0.25rem' }}>
                ({utilizationCellCount.toLocaleString()})
              </span>
            )}
          </label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={showUtilization}
              onChange={(e) => onShowUtilizationChange(e.target.checked)}
              disabled={!utilizationEnabled || utilizationCellCount === 0}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Position History Heatmap */}
        <div className="map-control-group">
          <label className="map-control-label">
            Position History
            {showPositionHistory && positionHistoryCount > 0 && (
              <span style={{ fontSize: '0.7rem', opacity: 0.7, marginLeft: '0.25rem' }}>
                ({positionHistoryCount.toLocaleString()})
              </span>
            )}
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={showPositionHistory}
                onChange={(e) => onShowPositionHistoryChange(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
            {showPositionHistory && (
              <select
                value={positionHistoryDays}
                onChange={(e) => onPositionHistoryDaysChange(Number(e.target.value))}
                style={{
                  padding: '0.25rem',
                  fontSize: '0.75rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-color, #ccc)',
                  background: 'var(--bg-secondary, #fff)',
                  color: 'var(--text-primary, #333)',
                }}
              >
                <option value={1}>1 day</option>
                <option value={3}>3 days</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            )}
          </div>
        </div>

        {/* Message Activity Heatmap */}
        <div className="map-control-group">
          <label className="map-control-label">
            Message Activity
            {showMessageActivity && messageActivityCount > 0 && (
              <span style={{ fontSize: '0.7rem', opacity: 0.7, marginLeft: '0.25rem' }}>
                ({messageActivityCount.toLocaleString()})
              </span>
            )}
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={showMessageActivity}
                onChange={(e) => onShowMessageActivityChange(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
            {showMessageActivity && (
              <select
                value={messageActivityDays}
                onChange={(e) => onMessageActivityDaysChange(Number(e.target.value))}
                style={{
                  padding: '0.25rem',
                  fontSize: '0.75rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-color, #ccc)',
                  background: 'var(--bg-secondary, #fff)',
                  color: 'var(--text-primary, #333)',
                }}
              >
                <option value={1}>1 day</option>
                <option value={3}>3 days</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            )}
          </div>
        </div>

        {/* Device Roles Filter */}
        <div className="map-control-group" ref={rolesRef}>
          <label className="map-control-label">Device Roles</label>
          <div className="map-control-dropdown">
            <button
              className="map-control-dropdown-button"
              onClick={() => setIsRolesOpen(!isRolesOpen)}
            >
              {enabledRoles.size === allRoles.length
                ? 'All roles'
                : enabledRoles.size === 0
                ? 'No roles'
                : `${enabledRoles.size} selected`}
              <span className="dropdown-arrow">{isRolesOpen ? '\u25B2' : '\u25BC'}</span>
            </button>
            {isRolesOpen && (
              <div className="map-control-dropdown-menu roles-dropdown">
                <div className="roles-dropdown-actions">
                  <button onClick={handleSelectAll}>All</button>
                  <button onClick={handleSelectNone}>None</button>
                </div>
                <div className="roles-dropdown-list">
                  {allRoles.map((role) => (
                    <label key={role} className="role-checkbox">
                      <input
                        type="checkbox"
                        checked={enabledRoles.has(role)}
                        onChange={() => handleRoleToggle(role)}
                      />
                      <span>{getRoleName(role)}</span>
                    </label>
                  ))}
                  {allRoles.length === 0 && (
                    <div className="roles-dropdown-empty">No roles found</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
