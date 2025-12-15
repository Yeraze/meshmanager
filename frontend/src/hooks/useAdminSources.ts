import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAdminSources,
  fetchCollectionStatuses,
  createMeshMonitorSource,
  createMqttSource,
  updateMeshMonitorSource,
  updateMqttSource,
  deleteSource,
  testSource,
  syncSource,
} from '../services/api'
import type { MeshMonitorSourceCreate, MqttSourceCreate } from '../types/api'

export function useAdminSources() {
  return useQuery({
    queryKey: ['admin', 'sources'],
    queryFn: fetchAdminSources,
  })
}

export function useCreateMeshMonitorSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MeshMonitorSourceCreate) => createMeshMonitorSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useCreateMqttSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MqttSourceCreate) => createMqttSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useUpdateMeshMonitorSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MeshMonitorSourceCreate> }) =>
      updateMeshMonitorSource(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useUpdateMqttSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MqttSourceCreate> }) =>
      updateMqttSource(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useDeleteSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: ['nodes'] })
    },
  })
}

export function useTestSource() {
  return useMutation({
    mutationFn: (id: string) => testSource(id),
  })
}

export function useSyncSource() {
  return useMutation({
    mutationFn: (id: string) => syncSource(id),
  })
}

export function useCollectionStatuses() {
  return useQuery({
    queryKey: ['collection-statuses'],
    queryFn: fetchCollectionStatuses,
    refetchInterval: 5000, // Refetch every 5 seconds while collecting
  })
}
