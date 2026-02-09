import { useState, useMemo } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import { type Page } from '../../contexts/DataContext'

interface NavSidebarProps {
  currentPage: Page
  onPageChange: (page: Page) => void
}

export default function NavSidebar({ currentPage, onPageChange }: NavSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const { isAuthenticated, hasPermission } = useAuthContext()

  const navItems = useMemo(() => {
    const allItems: { id: Page; label: string; icon: string }[] = [
      { id: 'map', label: 'Map', icon: '\u{1F5FA}\uFE0F' },
      { id: 'nodes', label: 'Node Details', icon: '\u{1F4E1}' },
      { id: 'graphs', label: 'Graphs', icon: '\u{1F4CA}' },
      { id: 'analysis', label: 'Analysis', icon: '\u{1F52C}' },
      { id: 'communication', label: 'Communication', icon: '\u{1F4AC}' },
    ]

    // Filter by read permission for authenticated users
    const items = isAuthenticated
      ? allItems.filter((item) => hasPermission(item.id, 'read'))
      : allItems

    // Settings tab: only show when authenticated and has settings read permission
    if (isAuthenticated && hasPermission('settings', 'read')) {
      items.push({ id: 'settings', label: 'Settings', icon: '\u2699\uFE0F' })
    }

    return items
  }, [isAuthenticated, hasPermission])

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
          {isCollapsed ? '\u25B6' : '\u25C0'}
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
