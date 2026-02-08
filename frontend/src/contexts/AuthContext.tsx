import { createContext, useContext, useState, type ReactNode } from 'react'
import { useAuth, useLogin, useRegister, useLogout } from '../hooks/useAuth'
import type { LoginRequest, RegisterRequest, UserInfo } from '../types/api'

interface AuthContextValue {
  isAuthenticated: boolean
  isAdmin: boolean
  isEditor: boolean
  user: UserInfo | null
  oidcEnabled: boolean
  setupRequired: boolean
  isLoading: boolean
  showLoginModal: boolean
  setShowLoginModal: (show: boolean) => void
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  loginError: string | null
  isLoggingIn: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: authStatus, isLoading } = useAuth()
  const loginMutation = useLogin()
  const registerMutation = useRegister()
  const logoutMutation = useLogout()
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  const handleLogin = async (credentials: LoginRequest) => {
    setLoginError(null)
    try {
      await loginMutation.mutateAsync(credentials)
      setShowLoginModal(false)
    } catch (error) {
      if (error instanceof Error) {
        setLoginError(error.message)
      } else {
        setLoginError('Login failed')
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
    logoutMutation.mutate()
  }

  const value: AuthContextValue = {
    isAuthenticated: authStatus?.authenticated ?? false,
    isAdmin: authStatus?.user?.role === 'admin',
    isEditor: ['admin', 'editor'].includes(authStatus?.user?.role ?? ''),
    user: authStatus?.user ?? null,
    oidcEnabled: authStatus?.oidc_enabled ?? false,
    setupRequired: authStatus?.setup_required ?? false,
    isLoading,
    showLoginModal,
    setShowLoginModal,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    loginError,
    isLoggingIn: loginMutation.isPending || registerMutation.isPending,
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
