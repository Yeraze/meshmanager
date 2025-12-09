import { useQuery } from '@tanstack/react-query'
import { fetchTraceroutes, fetchNodeRoles } from '../services/api'

export function useTraceroutes(hours?: number) {
  return useQuery({
    queryKey: ['traceroutes', hours],
    queryFn: () => fetchTraceroutes(hours),
  })
}

export function useNodeRoles() {
  return useQuery({
    queryKey: ['nodeRoles'],
    queryFn: fetchNodeRoles,
  })
}
