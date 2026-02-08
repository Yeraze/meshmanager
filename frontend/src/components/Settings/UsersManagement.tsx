import { useState } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import { useAdminUsers, useCreateUser, useUpdateUser, useDeleteUser } from '../../hooks/useAdminUsers'
import type { AdminUser, AdminUserCreate, UserRole } from '../../types/api'

function RoleBadge({ role }: { role: UserRole }) {
  const className =
    role === 'admin' ? 'badge badge-success' :
    role === 'editor' ? 'badge badge-info' :
    'badge badge-warning'
  const label = role.charAt(0).toUpperCase() + role.slice(1)
  return <span className={className}>{label}</span>
}

function AddUserForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateUser()
  const [form, setForm] = useState<AdminUserCreate>({
    username: '',
    password: '',
    email: '',
    display_name: '',
    role: 'viewer',
  })
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await createMutation.mutateAsync(form)
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
    <form onSubmit={handleSubmit} className="add-user-form">
      <h3>Add User</h3>
      {error && <div className="form-error">{error}</div>}
      <div className="form-row">
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
            minLength={3}
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={8}
          />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Display Name</label>
          <input
            type="text"
            value={form.display_name || ''}
            onChange={(e) => setForm({ ...form, display_name: e.target.value || undefined })}
          />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={form.email || ''}
            onChange={(e) => setForm({ ...form, email: e.target.value || undefined })}
          />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
          {createMutation.isPending ? 'Creating...' : 'Create User'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onSuccess}>
          Cancel
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
    role: user.role,
    is_active: user.is_active,
    password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const isSelf = currentUser?.id === user.id

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const data: Record<string, unknown> = {}
      if (form.display_name !== (user.display_name || '')) data.display_name = form.display_name || undefined
      if (form.email !== (user.email || '')) data.email = form.email || undefined
      if (form.role !== user.role) data.role = form.role
      if (form.is_active !== user.is_active) data.is_active = form.is_active
      if (form.password) data.password = form.password

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

  return (
    <form onSubmit={handleSubmit} className="edit-user-form">
      <h3>Edit User: {user.username}</h3>
      {error && <div className="form-error">{error}</div>}
      <div className="form-row">
        <div className="form-group">
          <label>Display Name</label>
          <input
            type="text"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            disabled={isSelf}
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
          {isSelf && <small>Cannot change your own role</small>}
        </div>
        <div className="form-group">
          <label>Active</label>
          <select
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
      {user.auth_provider === 'local' && (
        <div className="form-row">
          <div className="form-group">
            <label>New Password (leave blank to keep current)</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={8}
            />
          </div>
        </div>
      )}
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
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
      ) : users.length === 0 ? (
        <div className="settings-empty">No users found.</div>
      ) : (
        <div className="settings-list">
          {users.map((user) => {
            const isSelf = currentUser?.id === user.id
            return (
              <div key={user.id} className="settings-card user-card">
                <div className="user-card-header">
                  <div className="user-card-title">
                    <span className="user-card-avatar">
                      {user.display_name?.[0]?.toUpperCase() || user.username?.[0]?.toUpperCase() || '?'}
                    </span>
                    <div className="user-card-name-group">
                      <span className="user-card-name">
                        {user.display_name || user.username || 'Unknown'}
                        {isSelf && <span className="badge" style={{ marginLeft: '0.5rem' }}>You</span>}
                      </span>
                      {user.username && (
                        <span className="user-card-username">@{user.username}</span>
                      )}
                    </div>
                  </div>
                  <div className="user-card-badges">
                    <RoleBadge role={user.role} />
                    <span className={`badge ${user.is_active ? '' : 'badge-danger'}`}>
                      {user.is_active ? user.auth_provider === 'local' ? 'Local' : 'OIDC' : 'Disabled'}
                    </span>
                  </div>
                </div>
                {user.email && (
                  <div className="user-card-detail">
                    <span className="detail-value">{user.email}</span>
                  </div>
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
                    Edit
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(user)}
                    disabled={isSelf || deleteMutation.isPending}
                    title={isSelf ? 'Cannot delete your own account' : undefined}
                  >
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
