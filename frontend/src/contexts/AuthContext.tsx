import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { useAuth, useLogin, useRegister, useLogout, useVerifyTotp } from '../hooks/useAuth'
import type { LoginRequest, RegisterRequest, UserInfo } from '../types/api'

interface AuthContextValue {
  isAuthenticated: boolean
  isAdmin: boolean
  hasPermission: (tab: string, action: 'read' | 'write') => boolean
  user: UserInfo | null
  oidcEnabled: boolean
  setupRequired: boolean
  localAuthDisabled: boolean
  isLoading: boolean
  showLoginModal: boolean
  setShowLoginModal: (show: boolean) => void
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  loginError: string | null
  isLoggingIn: boolean
  totpRequired: boolean
  verifyTotp: (code: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: authStatus, isLoading } = useAuth()
  const loginMutation = useLogin()
  const registerMutation = useRegister()
  const logoutMutation = useLogout()
  const verifyTotpMutation = useVerifyTotp()
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [totpRequired, setTotpRequired] = useState(false)

  const handleLogin = async (credentials: LoginRequest) => {
    setLoginError(null)
    try {
      const result = await loginMutation.mutateAsync(credentials)
      if (result.totp_required) {
        setTotpRequired(true)
        // Don't close modal — show TOTP step
      } else {
        setTotpRequired(false)
        setShowLoginModal(false)
      }
    } catch (error) {
      if (error instanceof Error) {
        setLoginError(error.message)
      } else {
        setLoginError('Login failed')
      }
      throw error
    }
  }

  const handleVerifyTotp = async (code: string) => {
    setLoginError(null)
    try {
      await verifyTotpMutation.mutateAsync(code)
      setTotpRequired(false)
      setShowLoginModal(false)
    } catch (error) {
      if (error instanceof Error) {
        setLoginError(error.message)
      } else {
        setLoginError('TOTP verification failed')
      }
      throw error
    }
  }

  const handleRegister = async (data: RegisterRequest) => {
    setLoginError(null)
    try {
      await registerMutation.mutateAsync(data)
      setShowLoginModal(false)
    } catch (error) {
      if (error instanceof Error) {
        setLoginError(error.message)
      } else {
        setLoginError('Registration failed')
      }
      throw error
    }
  }

  const handleLogout = () => {
    setTotpRequired(false)
    logoutMutation.mutate()
  }

  const hasPermission = useCallback(
    (tab: string, action: 'read' | 'write'): boolean => {
      if (!authStatus?.authenticated || !authStatus.user) return false
      if (authStatus.user.is_admin) return true
      const perms = authStatus.user.permissions
      if (!perms) return false
      const tabPerms = perms[tab as keyof typeof perms]
      if (!tabPerms) return false
      return tabPerms[action] ?? false
    },
    [authStatus],
  )

  const value: AuthContextValue = {
    isAuthenticated: authStatus?.authenticated ?? false,
    isAdmin: authStatus?.user?.is_admin ?? false,
    hasPermission,
    user: authStatus?.user ?? null,
    oidcEnabled: authStatus?.oidc_enabled ?? false,
    setupRequired: authStatus?.setup_required ?? false,
    localAuthDisabled: authStatus?.local_auth_disabled ?? false,
    isLoading,
    showLoginModal,
    setShowLoginModal,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    loginError,
    isLoggingIn:
      loginMutation.isPending ||
      registerMutation.isPending ||
      verifyTotpMutation.isPending,
    totpRequired: totpRequired || (authStatus?.totp_required ?? false),
    verifyTotp: handleVerifyTotp,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}
