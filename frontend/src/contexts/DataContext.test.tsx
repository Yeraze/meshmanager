import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { DataProvider, useDataContext } from './DataContext'
import type { ReactNode } from 'react'

const wrapper = ({ children }: { children: ReactNode }) => (
  <DataProvider>{children}</DataProvider>
)

describe('DataContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  describe('useDataContext', () => {
    it('should throw error when used outside DataProvider', () => {
      expect(() => {
        renderHook(() => useDataContext())
      }).toThrow('useDataContext must be used within a DataProvider')
    })

    it('should return default values', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      expect(result.current.selectedNode).toBeNull()
      expect(result.current.enabledSourceIds.size).toBe(0)
      expect(result.current.showActiveOnly).toBe(true) // Default is true
      expect(result.current.activeHours).toBe(24)
      expect(result.current.onlineHours).toBe(1)
    })
  })

  describe('selectedNode', () => {
    it('should update selectedNode when setSelectedNode is called', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      const mockNode = {
        id: 'node-1',
        node_id: '!abc123',
        node_num: 12345,
        long_name: 'Test Node',
        short_name: 'TST1',
        latitude: 40.7128,
        longitude: -74.006,
        altitude: null,
        last_heard: new Date().toISOString(),
        source_id: 'source-1',
        source_name: 'Test Source',
        role: '2',
        hw_model: 'TBEAM',
      }

      act(() => {
        result.current.setSelectedNode(mockNode)
      })

      expect(result.current.selectedNode).toEqual(mockNode)
    })

    it('should clear selectedNode when setSelectedNode is called with null', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      const mockNode = {
        id: 'node-1',
        node_id: '!abc123',
        node_num: 12345,
        long_name: 'Test Node',
        short_name: null,
        latitude: null,
        longitude: null,
        altitude: null,
        last_heard: null,
        source_id: 'source-1',
        source_name: 'Test Source',
        role: null,
        hw_model: null,
      }

      act(() => {
        result.current.setSelectedNode(mockNode)
      })

      expect(result.current.selectedNode).not.toBeNull()

      act(() => {
        result.current.setSelectedNode(null)
      })

      expect(result.current.selectedNode).toBeNull()
    })
  })

  describe('enabledSourceIds', () => {
    it('should add source when toggleSource is called with new id', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      act(() => {
        result.current.toggleSource('source-1')
      })

      expect(result.current.enabledSourceIds.has('source-1')).toBe(true)
      expect(result.current.enabledSourceIds.size).toBe(1)
    })

    it('should remove source when toggleSource is called with existing id', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      act(() => {
        result.current.toggleSource('source-1')
      })

      expect(result.current.enabledSourceIds.has('source-1')).toBe(true)

      act(() => {
        result.current.toggleSource('source-1')
      })

      expect(result.current.enabledSourceIds.has('source-1')).toBe(false)
      expect(result.current.enabledSourceIds.size).toBe(0)
    })

    it('should toggle multiple sources independently', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      act(() => {
        result.current.toggleSource('source-1')
        result.current.toggleSource('source-2')
        result.current.toggleSource('source-3')
      })

      expect(result.current.enabledSourceIds.size).toBe(3)

      act(() => {
        result.current.toggleSource('source-2')
      })

      expect(result.current.enabledSourceIds.has('source-1')).toBe(true)
      expect(result.current.enabledSourceIds.has('source-2')).toBe(false)
      expect(result.current.enabledSourceIds.has('source-3')).toBe(true)
      expect(result.current.enabledSourceIds.size).toBe(2)
    })

    it('should replace all sources when enableAllSources is called', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      act(() => {
        result.current.toggleSource('old-source')
      })

      expect(result.current.enabledSourceIds.has('old-source')).toBe(true)

      act(() => {
        result.current.enableAllSources(['source-1', 'source-2', 'source-3'])
      })

      expect(result.current.enabledSourceIds.has('old-source')).toBe(false)
      expect(result.current.enabledSourceIds.has('source-1')).toBe(true)
      expect(result.current.enabledSourceIds.has('source-2')).toBe(true)
      expect(result.current.enabledSourceIds.has('source-3')).toBe(true)
      expect(result.current.enabledSourceIds.size).toBe(3)
    })

    it('should clear all sources when enableAllSources is called with empty array', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      act(() => {
        result.current.enableAllSources(['source-1', 'source-2'])
      })

      expect(result.current.enabledSourceIds.size).toBe(2)

      act(() => {
        result.current.enableAllSources([])
      })

      expect(result.current.enabledSourceIds.size).toBe(0)
    })
  })

  describe('showActiveOnly', () => {
    it('should default to true when no localStorage value', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })
      expect(result.current.showActiveOnly).toBe(true)
    })

    it('should read initial value from localStorage', () => {
      localStorage.setItem('showActiveOnly', 'false')
      const { result } = renderHook(() => useDataContext(), { wrapper })
      expect(result.current.showActiveOnly).toBe(false)
    })

    it('should update showActiveOnly and persist to localStorage', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      expect(result.current.showActiveOnly).toBe(true)

      act(() => {
        result.current.setShowActiveOnly(false)
      })

      expect(result.current.showActiveOnly).toBe(false)
      expect(localStorage.getItem('showActiveOnly')).toBe('false')

      act(() => {
        result.current.setShowActiveOnly(true)
      })

      expect(result.current.showActiveOnly).toBe(true)
      expect(localStorage.getItem('showActiveOnly')).toBe('true')
    })
  })

  describe('activeHours', () => {
    it('should update activeHours when setActiveHours is called', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      expect(result.current.activeHours).toBe(24)

      act(() => {
        result.current.setActiveHours(48)
      })

      expect(result.current.activeHours).toBe(48)

      act(() => {
        result.current.setActiveHours(1)
      })

      expect(result.current.activeHours).toBe(1)
    })
  })

  describe('onlineHours', () => {
    it('should update onlineHours when setOnlineHours is called', () => {
      const { result } = renderHook(() => useDataContext(), { wrapper })

      expect(result.current.onlineHours).toBe(1)

      act(() => {
        result.current.setOnlineHours(4)
      })

      expect(result.current.onlineHours).toBe(4)

      act(() => {
        result.current.setOnlineHours(24)
      })

      expect(result.current.onlineHours).toBe(24)
    })
  })
})
