import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAuthStatus,
  login,
  register,
  logout,
  verifyTotp,
  setupTotp,
  enableTotp,
  disableTotp,
} from '../services/api'
import type { LoginRequest, RegisterRequest } from '../types/api'

export function useAuth() {
  return useQuery({
    queryKey: ['auth'],
    queryFn: fetchAuthStatus,
    staleTime: 60000, // 1 minute
  })
}

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (credentials: LoginRequest) => login(credentials),
    onSuccess: (data) => {
      // Only invalidate auth if login was fully successful (no TOTP pending)
      if (!data.totp_required) {
        queryClient.invalidateQueries({ queryKey: ['auth'] })
      }
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: RegisterRequest) => register(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

export function useVerifyTotp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (code: string) => verifyTotp(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

export function useSetupTotp() {
  return useMutation({
    mutationFn: () => setupTotp(),
  })
}

export function useEnableTotp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (code: string) => enableTotp(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

export function useDisableTotp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (code: string) => disableTotp(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}
