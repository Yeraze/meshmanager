import { vi } from 'vitest'
import type { Node, Source, Telemetry, AuthStatus } from '../types/api'

// Mock node data
export const mockNode: Node = {
  id: 'test-node-1',
  node_id: '!abcd1234',
  node_num: 12345678,
  long_name: 'Test Node',
  short_name: 'TST1',
  latitude: 40.7128,
  longitude: -74.006,
  altitude: 10,
  last_heard: new Date().toISOString(),
  source_id: 'source-1',
  source_name: 'Test Source',
  role: 'ROUTER',
  hw_model: 'TBEAM',
}

export const mockNodes: Node[] = [
  mockNode,
  {
    ...mockNode,
    id: 'test-node-2',
    node_id: '!efgh5678',
    node_num: 87654321,
    long_name: 'Second Node',
    short_name: 'TST2',
    latitude: 40.72,
    longitude: -74.01,
    role: 'CLIENT',
  },
  {
    ...mockNode,
    id: 'test-node-3',
    node_id: '!ijkl9012',
    node_num: 11223344,
    long_name: 'Offline Node',
    short_name: 'OFF1',
    last_heard: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(), // 48 hours ago
    role: 'CLIENT_MUTE',
  },
]

// Mock source data
export const mockSource: Source = {
  id: 'source-1',
  name: 'Test MeshMonitor',
  source_type: 'meshmonitor',
  enabled: true,
  url: 'https://test.meshmonitor.example.com',
  created_at: new Date().toISOString(),
}

export const mockSources: Source[] = [
  mockSource,
  {
    id: 'source-2',
    name: 'Test MQTT',
    source_type: 'mqtt',
    enabled: true,
    mqtt_host: 'mqtt.example.com',
    mqtt_port: 1883,
    mqtt_topic: 'meshtastic/#',
    created_at: new Date().toISOString(),
  },
]

// Mock telemetry data
export const mockTelemetry: Telemetry = {
  id: 'telemetry-1',
  node_num: 12345678,
  metric_name: 'deviceMetrics',
  battery_level: 85,
  voltage: 4.1,
  channel_utilization: 25.5,
  air_util_tx: 5.2,
  received_at: new Date().toISOString(),
}

// Mock auth status
export const mockAuthStatus: AuthStatus = {
  authenticated: true,
  user: {
    id: 'user-1',
    username: 'testuser',
    email: null,
    display_name: null,
    role: 'viewer',
    auth_provider: 'local',
  },
  oidc_enabled: false,
  setup_required: false,
}

export const mockUnauthenticatedStatus: AuthStatus = {
  authenticated: false,
  user: null,
  oidc_enabled: false,
  setup_required: false,
}

export const mockAdminAuthStatus: AuthStatus = {
  authenticated: true,
  user: {
    id: 'admin-1',
    username: 'admin',
    email: null,
    display_name: null,
    role: 'admin',
    auth_provider: 'local',
  },
  oidc_enabled: false,
  setup_required: false,
}

// Mock traceroute data
export const mockTraceroutes = [
  {
    id: 'trace-1',
    source_id: 'source-1',
    from_node_num: 12345678,
    to_node_num: 87654321,
    route: [12345678, 11223344, 87654321],
    route_back: [87654321, 11223344, 12345678],
    received_at: new Date().toISOString(),
  },
  {
    id: 'trace-2',
    source_id: 'source-1',
    from_node_num: 12345678,
    to_node_num: 11223344,
    route: [12345678, 11223344],
    route_back: [11223344, 12345678],
    received_at: new Date().toISOString(),
  },
  {
    id: 'trace-3',
    source_id: 'source-1',
    from_node_num: 87654321,
    to_node_num: 11223344,
    route: [87654321, 11223344],
    route_back: null,
    received_at: new Date().toISOString(),
  },
]

// Mock API functions
export const createMockApi = () => ({
  fetchAuthStatus: vi.fn().mockResolvedValue(mockAuthStatus),
  login: vi.fn().mockResolvedValue({ success: true }),
  register: vi.fn().mockResolvedValue({ success: true }),
  logout: vi.fn().mockResolvedValue({ success: true }),
  fetchSources: vi.fn().mockResolvedValue(mockSources),
  fetchNodes: vi.fn().mockResolvedValue(mockNodes),
  fetchTraceroutes: vi.fn().mockResolvedValue(mockTraceroutes),
  fetchHealth: vi.fn().mockResolvedValue({ status: 'healthy', database: 'connected', version: '0.1.0' }),
})
