import { useState, useMemo } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import { type Page } from '../../contexts/DataContext'

interface NavSidebarProps {
  currentPage: Page
  onPageChange: (page: Page) => void
}

export default function NavSidebar({ currentPage, onPageChange }: NavSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const { isAuthenticated } = useAuthContext()

  const navItems = useMemo(() => {
    const items: { id: Page; label: string; icon: string }[] = [
      { id: 'map', label: 'Map', icon: '🗺️' },
      { id: 'nodes', label: 'Node Details', icon: '📡' },
      { id: 'graphs', label: 'Graphs', icon: '📊' },
      { id: 'analysis', label: 'Analysis', icon: '🔬' },
    ]

    if (isAuthenticated) {
      items.push({ id: 'settings', label: 'Settings', icon: '⚙️' })
    }

    return items
  }, [isAuthenticated])

  return (
    <nav className={`nav-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="nav-header">
        <img src="/logo-32.png" alt="MeshManager" className="nav-logo" />
        {!isCollapsed && <span className="nav-title">MeshManager</span>}
        <button
          className="nav-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand' : 'Collapse'}
        >
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>

      <div className="nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
            onClick={() => onPageChange(item.id)}
            title={isCollapsed ? item.label : undefined}
          >
            <span className="nav-icon">{item.icon}</span>
            {!isCollapsed && <span className="nav-label">{item.label}</span>}
          </button>
        ))}
      </div>
    </nav>
  )
}
