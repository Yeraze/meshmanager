import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Node } from '../types/api'

interface DataContextValue {
  selectedNode: Node | null
  setSelectedNode: (node: Node | null) => void
  enabledSourceIds: Set<string>
  toggleSource: (sourceId: string) => void
  enableAllSources: (sourceIds: string[]) => void
  showActiveOnly: boolean
  setShowActiveOnly: (active: boolean) => void
  activeHours: number
  setActiveHours: (hours: number) => void
  onlineHours: number
  setOnlineHours: (hours: number) => void
}

const DataContext = createContext<DataContextValue | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [enabledSourceIds, setEnabledSourceIds] = useState<Set<string>>(new Set())
  const [showActiveOnly, setShowActiveOnly] = useState(false)
  const [activeHours, setActiveHours] = useState(24)
  const [onlineHours, setOnlineHours] = useState(1)

  const toggleSource = (sourceId: string) => {
    setEnabledSourceIds((prev) => {
      const next = new Set(prev)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }

  const enableAllSources = (sourceIds: string[]) => {
    setEnabledSourceIds(new Set(sourceIds))
  }

  const value: DataContextValue = {
    selectedNode,
    setSelectedNode,
    enabledSourceIds,
    toggleSource,
    enableAllSources,
    showActiveOnly,
    setShowActiveOnly,
    activeHours,
    setActiveHours,
    onlineHours,
    setOnlineHours,
  }

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useDataContext() {
  const context = useContext(DataContext)
  if (!context) {
    throw new Error('useDataContext must be used within a DataProvider')
  }
  return context
}
