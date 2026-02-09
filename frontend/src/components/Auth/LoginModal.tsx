import { useState, useEffect } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import styles from './LoginModal.module.css'

export function LoginModal() {
  const {
    showLoginModal,
    setShowLoginModal,
    login,
    register,
    loginError,
    isLoggingIn,
    oidcEnabled,
    setupRequired,
    isAdmin,
    totpRequired,
    verifyTotp,
  } = useAuthContext()

  const [mode, setMode] = useState<'login' | 'register' | 'totp'>('login')

  // Update mode when setupRequired changes (e.g., after auth status loads)
  useEffect(() => {
    if (setupRequired) {
      setMode('register')
    }
  }, [setupRequired])

  // Switch to TOTP mode when required
  useEffect(() => {
    if (totpRequired) {
      setMode('totp')
    }
  }, [totpRequired])

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  if (!showLoginModal) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (mode === 'totp') {
      try {
        await verifyTotp(totpCode)
        setTotpCode('')
      } catch {
        // Error is handled by AuthContext
      }
    } else if (mode === 'register') {
      if (password !== confirmPassword) {
        setLocalError('Passwords do not match')
        return
      }
      if (password.length < 8) {
        setLocalError('Password must be at least 8 characters')
        return
      }
      try {
        await register({
          username,
          password,
          email: email || undefined,
          display_name: displayName || undefined,
        })
      } catch {
        // Error is handled by AuthContext
      }
    } else {
      try {
        await login({ username, password })
      } catch {
        // Error is handled by AuthContext
      }
    }
  }

  const handleClose = () => {
    if (!setupRequired && !totpRequired) {
      setShowLoginModal(false)
      setLocalError(null)
      setUsername('')
      setPassword('')
      setConfirmPassword('')
      setEmail('')
      setDisplayName('')
      setTotpCode('')
      setMode('login')
    }
  }

  const handleOidcLogin = () => {
    window.location.href = '/auth/oidc/login'
  }

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    setLocalError(null)
  }

  const error = localError || loginError
  const showRegisterOption = isAdmin || setupRequired

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>
            {mode === 'totp'
              ? 'Two-Factor Authentication'
              : setupRequired
                ? 'Create Admin Account'
                : mode === 'login'
                  ? 'Sign In'
                  : 'Create User'}
          </h2>
          {!setupRequired && !totpRequired && (
            <button className={styles.closeButton} onClick={handleClose}>
              ×
            </button>
          )}
        </div>

        {setupRequired && mode !== 'totp' && (
          <p className={styles.setupMessage}>
            Welcome! Create the first admin account to get started.
          </p>
        )}

        {mode === 'totp' && (
          <p className={styles.setupMessage}>
            Enter the 6-digit code from your authenticator app.
          </p>
        )}

        {error && <div className={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit} className={styles.form}>
          {mode === 'totp' ? (
            <div className={styles.field}>
              <label htmlFor="totpCode">Verification Code</label>
              <input
                id="totpCode"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={totpCode}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, '').slice(0, 6)
                  setTotpCode(val)
                }}
                required
                minLength={6}
                maxLength={6}
                placeholder="000000"
                autoFocus
                style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5em' }}
              />
            </div>
          ) : (
            <>
              <div className={styles.field}>
                <label htmlFor="username">Username</label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  minLength={3}
                  autoComplete="username"
                  autoFocus
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={mode === 'register' ? 8 : 1}
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                />
              </div>

              {mode === 'register' && (
                <>
                  <div className={styles.field}>
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      autoComplete="new-password"
                    />
                  </div>

                  <div className={styles.field}>
                    <label htmlFor="email">Email (optional)</label>
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                    />
                  </div>

                  <div className={styles.field}>
                    <label htmlFor="displayName">Display Name (optional)</label>
                    <input
                      id="displayName"
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      autoComplete="name"
                    />
                  </div>
                </>
              )}
            </>
          )}

          <button type="submit" className={styles.submitButton} disabled={isLoggingIn}>
            {isLoggingIn
              ? 'Please wait...'
              : mode === 'totp'
                ? 'Verify'
                : mode === 'register'
                  ? 'Create Account'
                  : 'Sign In'}
          </button>
        </form>

        {oidcEnabled && mode === 'login' && !setupRequired && (
          <>
            <div className={styles.divider}>
              <span>or</span>
            </div>
            <button className={styles.oidcButton} onClick={handleOidcLogin}>
              Sign in with SSO
            </button>
          </>
        )}

        {showRegisterOption && !setupRequired && mode !== 'totp' && (
          <div className={styles.switchMode}>
            {mode === 'login' ? (
              <button onClick={switchMode}>Create a new user</button>
            ) : (
              <button onClick={switchMode}>Back to sign in</button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
