import { useState, useRef, useEffect } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'

export default function Header() {
  const { isAuthenticated, user, logout, setShowLoginModal } = useAuthContext()
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const displayName = user?.display_name || user?.username || user?.email || 'User'

  return (
    <header className="header">
      <h1>MeshManager</h1>
      <div className="header-actions">
        {isAuthenticated ? (
          <div className="user-menu" ref={dropdownRef}>
            <button
              className="user-menu-button"
              onClick={() => setShowDropdown(!showDropdown)}
            >
              <span className="user-menu-avatar">
                {displayName[0].toUpperCase()}
              </span>
              <span className="user-menu-name">{displayName}</span>
              {user?.is_admin && <span className="badge badge-success">Admin</span>}
              <span className="user-menu-chevron">{showDropdown ? '\u25B2' : '\u25BC'}</span>
            </button>

            {showDropdown && (
              <div className="user-dropdown">
                <div className="user-dropdown-header">
                  <div className="user-dropdown-name">{displayName}</div>
                  {user?.email && <div className="user-dropdown-email">{user.email}</div>}
                </div>
                <div className="user-dropdown-divider" />
                <button className="user-dropdown-item" onClick={() => { logout(); setShowDropdown(false); }}>
                  Logout
                </button>
              </div>
            )}
          </div>
        ) : (
          <button className="btn btn-primary" onClick={() => setShowLoginModal(true)}>
            Login
          </button>
        )}
      </div>
    </header>
  )
}
