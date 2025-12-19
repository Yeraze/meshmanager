import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Node } from '../types/api'

export type Page = 'map' | 'nodes' | 'graphs' | 'analysis' | 'communication' | 'settings'

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
  currentPage: Page
  navigateToPage: (page: Page) => void
}

const DataContext = createContext<DataContextValue | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [enabledSourceIds, setEnabledSourceIds] = useState<Set<string>>(new Set())
  const [showActiveOnly, setShowActiveOnlyState] = useState(() => {
    const stored = localStorage.getItem('showActiveOnly')
    return stored !== null ? stored === 'true' : true // Default to true
  })
  const [activeHours, setActiveHours] = useState(24)
  const [onlineHours, setOnlineHours] = useState(1)
  const [currentPage, setCurrentPage] = useState<Page>('map')

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

  const setShowActiveOnly = (active: boolean) => {
    localStorage.setItem('showActiveOnly', String(active))
    setShowActiveOnlyState(active)
  }

  const navigateToPage = (page: Page) => {
    setCurrentPage(page)
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
    currentPage,
    navigateToPage,
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
