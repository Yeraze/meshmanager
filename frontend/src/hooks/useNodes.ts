import { useQuery } from '@tanstack/react-query'
import { fetchNodes, fetchNodesByNodeNum } from '../services/api'

export function useNodes(options?: { sourceId?: string; activeOnly?: boolean; activeHours?: number }) {
  return useQuery({
    queryKey: ['nodes', options],
    queryFn: () => fetchNodes(options),
  })
}

export function useNodesByNodeNum(nodeNum: number) {
  return useQuery({
    queryKey: ['nodes', 'by-node-num', nodeNum],
    queryFn: () => fetchNodesByNodeNum(nodeNum),
    enabled: !!nodeNum,
  })
}
