import { useAuthContext } from '../../contexts/AuthContext'

export default function UserSettings() {
  const { user, logout } = useAuthContext()

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>User Profile</h2>
      </div>

      <div className="settings-card">
        <div className="user-profile">
          <div className="user-avatar">
            {user?.display_name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="user-info">
            <div className="user-name">{user?.display_name || user?.username || 'Unknown User'}</div>
            {user?.email && <div className="user-email">{user.email}</div>}
            <div className="user-role">
              <span className={`badge ${user?.role === 'admin' ? 'badge-success' : user?.role === 'editor' ? 'badge-info' : 'badge-warning'}`}>
                {user?.role === 'admin' ? 'Administrator' : user?.role === 'editor' ? 'Editor' : 'Viewer'}
              </span>
              <span className="badge">{user?.auth_provider === 'local' ? 'Local Account' : 'OIDC'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="settings-card">
        <h3>Session</h3>
        <p className="settings-description">
          You are currently logged in. Click the button below to log out of your account.
        </p>
        <button className="btn btn-danger" onClick={logout}>
          Log Out
        </button>
      </div>
    </div>
  )
}
