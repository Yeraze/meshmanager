import { useState } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import { useSetupTotp, useEnableTotp, useDisableTotp } from '../../hooks/useAuth'
import type { TotpSetupResponse } from '../../types/api'

export default function UserSettings() {
  const { user, logout } = useAuthContext()
  const setupTotpMutation = useSetupTotp()
  const enableTotpMutation = useEnableTotp()
  const disableTotpMutation = useDisableTotp()

  const [totpSetup, setTotpSetup] = useState<TotpSetupResponse | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [totpError, setTotpError] = useState<string | null>(null)

  const isLocalUser = user?.auth_provider === 'local'

  const handleSetupTotp = async () => {
    setTotpError(null)
    try {
      const result = await setupTotpMutation.mutateAsync()
      setTotpSetup(result)
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : 'Failed to setup TOTP')
    }
  }

  const handleEnableTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setTotpError(null)
    try {
      await enableTotpMutation.mutateAsync(totpCode)
      setTotpSetup(null)
      setTotpCode('')
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : 'Invalid code')
    }
  }

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setTotpError(null)
    try {
      await disableTotpMutation.mutateAsync(disableCode)
      setDisableCode('')
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : 'Invalid code')
    }
  }

  const handleCancelSetup = () => {
    setTotpSetup(null)
    setTotpCode('')
    setTotpError(null)
  }

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
              <span className={`badge ${user?.is_admin ? 'badge-success' : 'badge-info'}`}>
                {user?.is_admin ? 'Administrator' : 'User'}
              </span>
              <span className="badge">{user?.auth_provider === 'local' ? 'Local Account' : 'OIDC'}</span>
            </div>
          </div>
        </div>
      </div>

      {isLocalUser && (
        <div className="settings-card">
          <h3>Two-Factor Authentication (TOTP)</h3>

          {totpError && <div className="user-form-error">{totpError}</div>}

          {user?.totp_enabled ? (
            <>
              <p className="settings-description">
                <span className="badge badge-success">Enabled</span>{' '}
                Two-factor authentication is active on your account.
              </p>
              <form onSubmit={handleDisableTotp}>
                <div className="user-form-grid">
                  <div className="user-form-group">
                    <label htmlFor="disable-totp-code">Enter code to disable</label>
                    <input
                      id="disable-totp-code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={disableCode}
                      onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      maxLength={6}
                      required
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={disableTotpMutation.isPending || disableCode.length !== 6}
                >
                  {disableTotpMutation.isPending ? 'Disabling...' : 'Disable TOTP'}
                </button>
              </form>
            </>
          ) : totpSetup ? (
            <>
              <p className="settings-description">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
              </p>
              <div className="totp-qr" dangerouslySetInnerHTML={{ __html: totpSetup.qr_code_svg }} />
              <p className="settings-description" style={{ marginTop: '1rem' }}>
                Or enter this secret manually: <code>{totpSetup.secret}</code>
              </p>
              <form onSubmit={handleEnableTotp}>
                <div className="user-form-grid">
                  <div className="user-form-group">
                    <label htmlFor="enable-totp-code">Enter the 6-digit code to verify</label>
                    <input
                      id="enable-totp-code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      maxLength={6}
                      required
                      autoFocus
                    />
                  </div>
                </div>
                <div className="user-form-actions">
                  <button type="button" className="btn btn-secondary" onClick={handleCancelSetup}>
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={enableTotpMutation.isPending || totpCode.length !== 6}
                  >
                    {enableTotpMutation.isPending ? 'Verifying...' : 'Confirm & Enable'}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <p className="settings-description">
                Add an extra layer of security to your account by enabling two-factor authentication
                with a TOTP authenticator app.
              </p>
              <button
                className="btn btn-primary"
                onClick={handleSetupTotp}
                disabled={setupTotpMutation.isPending}
              >
                {setupTotpMutation.isPending ? 'Setting up...' : 'Enable TOTP'}
              </button>
            </>
          )}
        </div>
      )}

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
