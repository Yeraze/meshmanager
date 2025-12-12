import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock axios before importing the API module
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  }
})

// Import after mocking
import {
  fetchAuthStatus,
  login,
  register,
  logout,
  fetchSources,
  fetchNodes,
  fetchNode,
  fetchTelemetry,
  fetchHealth,
  fetchTraceroutes,
  fetchNodeRoles,
  fetchCoverageConfig,
  fetchUtilizationConfig,
  deleteSource,
  testSource,
  syncSource,
  fetchSolarNodesAnalysis,
} from './api'

describe('API Service', () => {
  // Get the mocked axios instance
  const mockAxiosInstance = (axios.create as ReturnType<typeof vi.fn>)()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Auth endpoints', () => {
    it('fetchAuthStatus should call GET /auth/status', async () => {
      const mockStatus = {
        authenticated: true,
        user: { id: '1', username: 'test', is_admin: false, auth_method: 'local' },
        oidc_enabled: false,
        setup_required: false,
      }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockStatus })

      const result = await fetchAuthStatus()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/status')
      expect(result).toEqual(mockStatus)
    })

    it('login should call POST /auth/login with credentials', async () => {
      const credentials = { username: 'test', password: 'password123' }
      const mockResponse = { message: 'Success', user: { id: '1', username: 'test', is_admin: false, auth_method: 'local' } }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse })

      const result = await login(credentials)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/login', credentials)
      expect(result).toEqual(mockResponse)
    })

    it('register should call POST /auth/register with user data', async () => {
      const userData = { username: 'newuser', password: 'password123', password_confirm: 'password123' }
      const mockResponse = { message: 'Success', user: { id: '1', username: 'newuser', is_admin: true, auth_method: 'local' } }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse })

      const result = await register(userData)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', userData)
      expect(result).toEqual(mockResponse)
    })

    it('logout should call POST /auth/logout', async () => {
      mockAxiosInstance.post.mockResolvedValueOnce({ data: {} })

      await logout()

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/logout')
    })
  })

  describe('Sources endpoints', () => {
    it('fetchSources should call GET /api/sources', async () => {
      const mockSources = [
        { id: '1', name: 'Source 1', source_type: 'meshmonitor', enabled: true },
      ]
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockSources })

      const result = await fetchSources()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/sources')
      expect(result).toEqual(mockSources)
    })

    it('deleteSource should call DELETE /api/admin/sources/:id', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ data: {} })

      await deleteSource('source-123')

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/api/admin/sources/source-123')
    })

    it('testSource should call POST /api/admin/sources/:id/test', async () => {
      const mockResponse = { success: true, message: 'Connection successful' }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse })

      const result = await testSource('source-123')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/admin/sources/source-123/test')
      expect(result).toEqual(mockResponse)
    })

    it('syncSource should call POST /api/admin/sources/:id/sync', async () => {
      const mockResponse = { message: 'Sync started', source_id: 'source-123' }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse })

      const result = await syncSource('source-123')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/admin/sources/source-123/sync')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('Nodes endpoints', () => {
    it('fetchNodes should call GET /api/nodes with no params', async () => {
      const mockNodes = [{ id: '1', node_num: 12345, long_name: 'Test Node' }]
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockNodes })

      const result = await fetchNodes()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/nodes?')
      expect(result).toEqual(mockNodes)
    })

    it('fetchNodes should include sourceId param when provided', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({ data: [] })

      await fetchNodes({ sourceId: 'source-123' })

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        expect.stringContaining('source_id=source-123')
      )
    })

    it('fetchNodes should include activeOnly and activeHours params', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({ data: [] })

      await fetchNodes({ activeOnly: true, activeHours: 24 })

      const call = mockAxiosInstance.get.mock.calls[0][0]
      expect(call).toContain('active_only=true')
      expect(call).toContain('active_hours=24')
    })

    it('fetchNode should call GET /api/nodes/:id', async () => {
      const mockNode = { id: 'node-1', node_num: 12345 }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockNode })

      const result = await fetchNode('node-1')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/nodes/node-1')
      expect(result).toEqual(mockNode)
    })
  })

  describe('Telemetry endpoints', () => {
    it('fetchTelemetry should call GET /api/telemetry/:nodeNum', async () => {
      const mockTelemetry = [{ id: '1', node_num: 12345, battery_level: 85 }]
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockTelemetry })

      const result = await fetchTelemetry(12345)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/telemetry/12345?')
      expect(result).toEqual(mockTelemetry)
    })

    it('fetchTelemetry should include hours param when provided', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({ data: [] })

      await fetchTelemetry(12345, 48)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        expect.stringContaining('hours=48')
      )
    })
  })

  describe('Health endpoint', () => {
    it('fetchHealth should call GET /health', async () => {
      const mockHealth = { status: 'healthy', database: 'connected', version: '0.1.0' }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockHealth })

      const result = await fetchHealth()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health')
      expect(result).toEqual(mockHealth)
    })
  })

  describe('Traceroutes endpoint', () => {
    it('fetchTraceroutes should call GET /api/traceroutes', async () => {
      const mockTraceroutes = [{ id: '1', from_node_num: 12345, to_node_num: 67890 }]
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockTraceroutes })

      const result = await fetchTraceroutes()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/traceroutes?')
      expect(result).toEqual(mockTraceroutes)
    })

    it('fetchTraceroutes should include hours param when provided', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({ data: [] })

      await fetchTraceroutes(24)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        expect.stringContaining('hours=24')
      )
    })
  })

  describe('Node Roles endpoint', () => {
    it('fetchNodeRoles should call GET /api/nodes/roles', async () => {
      const mockRoles = ['0', '2', '5']
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockRoles })

      const result = await fetchNodeRoles()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/nodes/roles')
      expect(result).toEqual(mockRoles)
    })
  })

  describe('Coverage endpoints', () => {
    it('fetchCoverageConfig should call GET /api/coverage/config', async () => {
      const mockConfig = {
        enabled: true,
        resolution: 1.0,
        unit: 'miles',
        lookback_days: 7,
        cell_count: 100,
      }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockConfig })

      const result = await fetchCoverageConfig()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/coverage/config')
      expect(result).toEqual(mockConfig)
    })
  })

  describe('Utilization endpoints', () => {
    it('fetchUtilizationConfig should call GET /api/utilization/config', async () => {
      const mockConfig = {
        enabled: true,
        resolution: 1.0,
        unit: 'miles',
        lookback_days: 7,
        aggregation: 'avg',
        cell_count: 50,
      }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockConfig })

      const result = await fetchUtilizationConfig()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/utilization/config')
      expect(result).toEqual(mockConfig)
    })
  })

  describe('Solar Analysis endpoints', () => {
    it('fetchSolarNodesAnalysis should call GET /api/analysis/solar-nodes', async () => {
      const mockAnalysis = {
        lookback_days: 7,
        total_nodes_analyzed: 50,
        solar_nodes_count: 5,
        avg_charging_hours_per_day: 10.5,
        avg_discharge_hours_per_day: 13.5,
        solar_nodes: [
          {
            node_num: 12345678,
            node_name: 'Solar Node',
            solar_score: 85.7,
            days_analyzed: 7,
            days_with_pattern: 6,
            recent_patterns: [],
            metric_type: 'battery',
            chart_data: [],
            avg_charge_rate_per_hour: 3.85,
            avg_discharge_rate_per_hour: 0.54,
          },
        ],
        solar_production: [],
      }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockAnalysis })

      const result = await fetchSolarNodesAnalysis()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/analysis/solar-nodes?')
      expect(result).toEqual(mockAnalysis)
    })

    it('fetchSolarNodesAnalysis should include lookback_days param when provided', async () => {
      const mockAnalysis = {
        lookback_days: 14,
        total_nodes_analyzed: 50,
        solar_nodes_count: 5,
        avg_charging_hours_per_day: 10.5,
        avg_discharge_hours_per_day: 13.5,
        solar_nodes: [],
        solar_production: [],
      }
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockAnalysis })

      await fetchSolarNodesAnalysis(14)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        expect.stringContaining('lookback_days=14')
      )
    })
  })
})
