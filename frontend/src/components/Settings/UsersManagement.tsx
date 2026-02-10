import { useState } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import { useAdminUsers, useCreateUser, useUpdateUser, useDeleteUser } from '../../hooks/useAdminUsers'
import type { AdminUser, AdminUserCreate, UserPermissions, TabPermission } from '../../types/api'

const TAB_NAMES: { key: keyof UserPermissions; label: string }[] = [
  { key: 'map', label: 'Map' },
  { key: 'nodes', label: 'Node Details' },
  { key: 'graphs', label: 'Graphs' },
  { key: 'analysis', label: 'Analysis' },
  { key: 'communication', label: 'Communication' },
  { key: 'settings', label: 'Settings' },
]

const DEFAULT_PERMISSIONS: UserPermissions = {
  map: { read: true, write: false },
  nodes: { read: true, write: false },
  graphs: { read: true, write: false },
  analysis: { read: true, write: false },
  communication: { read: true, write: false },
  settings: { read: true, write: false },
}

function RoleBadge({ isAdmin }: { isAdmin: boolean }) {
  return isAdmin
    ? <span className="badge badge-success">Admin</span>
    : <span className="badge badge-info">User</span>
}

function PermissionsGrid({
  permissions,
  onChange,
  disabled,
}: {
  permissions: UserPermissions
  onChange: (perms: UserPermissions) => void
  disabled: boolean
}) {
  const handleChange = (tab: keyof UserPermissions, action: keyof TabPermission, value: boolean) => {
    const updated = { ...permissions }
    const tabPerms = { ...updated[tab] }
    tabPerms[action] = value
    // If disabling read, also disable write
    if (action === 'read' && !value) {
      tabPerms.write = false
    }
    updated[tab] = tabPerms
    onChange(updated)
  }

  return (
    <div className="permissions-grid">
      <div className="permissions-header">Tab</div>
      <div className="permissions-header">Read</div>
      <div className="permissions-header">Write</div>
      {TAB_NAMES.map(({ key, label }) => (
        <div key={key} className="permissions-row">
          <div className="permissions-tab-name">{label}</div>
          <div>
            <input
              type="checkbox"
              checked={permissions[key]?.read ?? true}
              onChange={(e) => handleChange(key, 'read', e.target.checked)}
              disabled={disabled}
            />
          </div>
          <div>
            <input
              type="checkbox"
              checked={permissions[key]?.write ?? false}
              onChange={(e) => handleChange(key, 'write', e.target.checked)}
              disabled={disabled || !(permissions[key]?.read)}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function AddUserForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateUser()
  const [form, setForm] = useState<AdminUserCreate>({
    username: '',
    password: '',
    email: '',
    display_name: '',
    is_admin: false,
    permissions: { ...DEFAULT_PERMISSIONS },
  })
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await createMutation.mutateAsync(form)
      setForm({
        username: '',
        password: '',
        email: '',
        display_name: '',
        is_admin: false,
        permissions: { ...DEFAULT_PERMISSIONS },
      })
      onSuccess()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to create user')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="user-form">
      <h3>Add User</h3>
      {error && <div className="user-form-error">{error}</div>}
      <div className="user-form-grid">
        <div className="user-form-group">
          <label htmlFor="new-username">Username</label>
          <input
            id="new-username"
            type="text"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
            minLength={3}
            placeholder="Enter username"
          />
        </div>
        <div className="user-form-group">
          <label htmlFor="new-password">Password</label>
          <input
            id="new-password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={8}
            placeholder="Minimum 8 characters"
          />
        </div>
      </div>
      <div className="user-form-grid">
        <div className="user-form-group">
          <label htmlFor="new-display-name">Display Name</label>
          <input
            id="new-display-name"
            type="text"
            value={form.display_name || ''}
            onChange={(e) => setForm({ ...form, display_name: e.target.value || undefined })}
            placeholder="Optional"
          />
        </div>
        <div className="user-form-group">
          <label htmlFor="new-email">Email</label>
          <input
            id="new-email"
            type="email"
            value={form.email || ''}
            onChange={(e) => setForm({ ...form, email: e.target.value || undefined })}
            placeholder="Optional"
          />
        </div>
      </div>
      <div className="user-form-grid">
        <div className="user-form-group">
          <label>
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
            />{' '}
            Admin
          </label>
        </div>
      </div>
      {!form.is_admin && (
        <>
          <h4 style={{ marginTop: '0.75rem', marginBottom: '0.5rem' }}>Permissions</h4>
          <PermissionsGrid
            permissions={form.permissions || DEFAULT_PERMISSIONS}
            onChange={(perms) => setForm({ ...form, permissions: perms })}
            disabled={false}
          />
        </>
      )}
      {form.is_admin && (
        <p className="settings-description" style={{ marginTop: '0.5rem' }}>
          Admins have full access to all tabs.
        </p>
      )}
      <div className="user-form-actions">
        <button type="button" className="btn btn-secondary" onClick={onSuccess}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
          {createMutation.isPending ? 'Creating...' : 'Create User'}
        </button>
      </div>
    </form>
  )
}

function EditUserForm({ user, onSuccess, onCancel }: { user: AdminUser; onSuccess: () => void; onCancel: () => void }) {
  const { user: currentUser } = useAuthContext()
  const updateMutation = useUpdateUser()
  const [form, setForm] = useState({
    display_name: user.display_name || '',
    email: user.email || '',
    is_admin: user.is_admin,
    is_active: user.is_active,
    password: '',
    permissions: user.permissions || { ...DEFAULT_PERMISSIONS },
  })
  const [error, setError] = useState<string | null>(null)
  const isSelf = currentUser?.id === user.id

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      // Anonymous user: only send permissions
      if (user.is_anonymous) {
        await updateMutation.mutateAsync({ id: user.id, data: { permissions: form.permissions } })
        onSuccess()
        return
      }

      const data: Record<string, unknown> = {}
      if (form.display_name !== (user.display_name || '')) data.display_name = form.display_name || undefined
      if (form.email !== (user.email || '')) data.email = form.email || undefined
      if (form.is_admin !== user.is_admin) data.is_admin = form.is_admin
      if (form.is_active !== user.is_active) data.is_active = form.is_active
      if (form.password) data.password = form.password
      // Always send permissions if not admin
      if (!form.is_admin) {
        data.permissions = form.permissions
      }

      await updateMutation.mutateAsync({ id: user.id, data })
      onSuccess()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to update user')
      }
    }
  }

  const handleResetTotp = async () => {
    if (!confirm(`Reset TOTP for "${user.username}"? They will need to set up a new authenticator.`)) return
    try {
      await updateMutation.mutateAsync({ id: user.id, data: { reset_totp: true } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset TOTP')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="user-form">
      <h3>{user.is_anonymous ? 'Edit Anonymous User Permissions' : `Edit User: ${user.username}`}</h3>
      {error && <div className="user-form-error">{error}</div>}
      {user.is_anonymous ? (
        <>
          <p className="settings-description" style={{ marginBottom: '0.75rem' }}>
            Configure what unauthenticated visitors can access. Changes take effect immediately.
          </p>
          <PermissionsGrid
            permissions={form.permissions}
            onChange={(perms) => setForm({ ...form, permissions: perms })}
            disabled={false}
          />
        </>
      ) : (
        <>
          <div className="user-form-grid">
            <div className="user-form-group">
              <label htmlFor="edit-display-name">Display Name</label>
              <input
                id="edit-display-name"
                type="text"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                placeholder="Optional"
              />
            </div>
            <div className="user-form-group">
              <label htmlFor="edit-email">Email</label>
              <input
                id="edit-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="user-form-grid">
            <div className="user-form-group">
              <label>
                <input
                  type="checkbox"
                  checked={form.is_admin}
                  onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
                  disabled={isSelf}
                />{' '}
                Admin
              </label>
              {isSelf && <small>Cannot change your own admin status</small>}
            </div>
            <div className="user-form-group">
              <label htmlFor="edit-active">Status</label>
              <select
                id="edit-active"
                value={form.is_active ? 'true' : 'false'}
                onChange={(e) => setForm({ ...form, is_active: e.target.value === 'true' })}
                disabled={isSelf}
              >
                <option value="true">Active</option>
                <option value="false">Disabled</option>
              </select>
              {isSelf && <small>Cannot deactivate your own account</small>}
            </div>
          </div>
          {!form.is_admin && (
            <>
              <h4 style={{ marginTop: '0.75rem', marginBottom: '0.5rem' }}>Permissions</h4>
              <PermissionsGrid
                permissions={form.permissions}
                onChange={(perms) => setForm({ ...form, permissions: perms })}
                disabled={false}
              />
            </>
          )}
          {form.is_admin && (
            <p className="settings-description" style={{ marginTop: '0.5rem' }}>
              Admins have full access to all tabs.
            </p>
          )}
          {user.auth_provider === 'local' && (
            <div className="user-form-grid">
              <div className="user-form-group">
                <label htmlFor="edit-password">New Password</label>
                <input
                  id="edit-password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  minLength={8}
                  placeholder="Leave blank to keep current"
                />
              </div>
            </div>
          )}
          {user.totp_enabled && (
            <div style={{ marginTop: '0.75rem' }}>
              <button type="button" className="btn btn-danger btn-sm" onClick={handleResetTotp}>
                Reset TOTP
              </button>
            </div>
          )}
        </>
      )}
      <div className="user-form-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}

export default function UsersManagement() {
  const { user: currentUser } = useAuthContext()
  const { data: users = [], isLoading } = useAdminUsers()
  const deleteMutation = useDeleteUser()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)

  // Sort anonymous user to top of list
  const sortedUsers = [...users].sort((a, b) => {
    if (a.is_anonymous && !b.is_anonymous) return -1
    if (!a.is_anonymous && b.is_anonymous) return 1
    return 0
  })

  const handleDelete = async (user: AdminUser) => {
    if (confirm(`Are you sure you want to delete user "${user.username}"?`)) {
      await deleteMutation.mutateAsync(user.id)
    }
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>User Management</h2>
        <button
          className="btn btn-primary"
          onClick={() => {
            setShowAddForm(!showAddForm)
            if (showAddForm) setEditingUser(null)
          }}
          disabled={!!editingUser}
        >
          {showAddForm ? 'Cancel' : 'Add User'}
        </button>
      </div>

      {showAddForm && (
        <div className="settings-card">
          <AddUserForm onSuccess={() => setShowAddForm(false)} />
        </div>
      )}

      {editingUser && (
        <div className="settings-card">
          <EditUserForm
            user={editingUser}
            onSuccess={() => setEditingUser(null)}
            onCancel={() => setEditingUser(null)}
          />
        </div>
      )}

      {isLoading ? (
        <div className="loading">
          <div className="loading-spinner" />
          Loading users...
        </div>
      ) : sortedUsers.length === 0 ? (
        <div className="settings-empty">No users found.</div>
      ) : (
        <div className="settings-list">
          {sortedUsers.map((user) => {
            const isSelf = currentUser?.id === user.id
            const canDelete = !isSelf && !user.is_anonymous
            return (
              <div key={user.id} className="settings-card user-card">
                <div className="user-card-header">
                  <div className="user-card-title">
                    <span className="user-card-avatar">
                      {user.is_anonymous ? '?' : (user.display_name?.[0]?.toUpperCase() || user.username?.[0]?.toUpperCase() || '?')}
                    </span>
                    <div className="user-card-name-group">
                      <span className="user-card-name">
                        {user.is_anonymous ? 'Anonymous' : (user.display_name || user.username || 'Unknown')}
                        {isSelf && <span className="badge">You</span>}
                      </span>
                      {user.is_anonymous ? (
                        <span className="user-card-username">Unauthenticated visitors</span>
                      ) : user.username && (
                        <span className="user-card-username">@{user.username}</span>
                      )}
                    </div>
                  </div>
                  <div className="user-card-badges">
                    {user.is_anonymous ? (
                      <span className="badge badge-warning">Anonymous</span>
                    ) : (
                      <RoleBadge isAdmin={user.is_admin} />
                    )}
                    {user.totp_enabled && <span className="badge badge-info">MFA</span>}
                    {!user.is_anonymous && (
                      <span className={`badge ${user.is_active ? '' : 'badge-danger'}`}>
                        {user.is_active ? user.auth_provider === 'local' ? 'Local' : 'OIDC' : 'Disabled'}
                      </span>
                    )}
                  </div>
                </div>
                {user.email && !user.is_anonymous && (
                  <div className="user-card-detail">{user.email}</div>
                )}
                <div className="user-card-actions">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setEditingUser(user)
                      setShowAddForm(false)
                    }}
                    disabled={!!editingUser || !!showAddForm}
                  >
                    {user.is_anonymous ? 'Edit Permissions' : 'Edit'}
                  </button>
                  {!user.is_anonymous && (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(user)}
                      disabled={!canDelete || deleteMutation.isPending}
                      title={isSelf ? 'Cannot delete your own account' : undefined}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
