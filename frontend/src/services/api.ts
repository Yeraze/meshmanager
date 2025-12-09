import axios from 'axios'
import type {
  AuthStatus,
  CollectionStatus,
  LoginRequest,
  MeshMonitorSourceCreate,
  MqttSourceCreate,
  Node,
  RegisterRequest,
  Source,
  Telemetry,
  TelemetryHistory,
  Traceroute,
  UserInfo,
} from '../types/api'

const api = axios.create({
  baseURL: '',
  withCredentials: true,
})

// Auth
export async function fetchAuthStatus(): Promise<AuthStatus> {
  const response = await api.get<AuthStatus>('/auth/status')
  return response.data
}

export async function login(credentials: LoginRequest): Promise<{ user: UserInfo }> {
  const response = await api.post<{ message: string; user: UserInfo }>('/auth/login', credentials)
  return response.data
}

export async function register(data: RegisterRequest): Promise<{ user: UserInfo }> {
  const response = await api.post<{ message: string; user: UserInfo }>('/auth/register', data)
  return response.data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

// Sources
export async function fetchSources(): Promise<Source[]> {
  const response = await api.get<Source[]>('/api/sources')
  return response.data
}

export async function fetchAdminSources(): Promise<Source[]> {
  const response = await api.get<Source[]>('/api/admin/sources')
  return response.data
}

export async function createMeshMonitorSource(data: MeshMonitorSourceCreate): Promise<Source> {
  const response = await api.post<Source>('/api/admin/sources/meshmonitor', data)
  return response.data
}

export async function createMqttSource(data: MqttSourceCreate): Promise<Source> {
  const response = await api.post<Source>('/api/admin/sources/mqtt', data)
  return response.data
}

export async function deleteSource(id: string): Promise<void> {
  await api.delete(`/api/admin/sources/${id}`)
}

export async function testSource(id: string): Promise<{ success: boolean; message: string }> {
  const response = await api.post<{ success: boolean; message: string }>(`/api/admin/sources/${id}/test`)
  return response.data
}

export async function syncSource(id: string): Promise<{ message: string; source_id: string }> {
  const response = await api.post<{ message: string; source_id: string }>(`/api/admin/sources/${id}/sync`)
  return response.data
}

// Nodes
export async function fetchNodes(options?: { sourceId?: string; activeOnly?: boolean; activeHours?: number }): Promise<Node[]> {
  const params = new URLSearchParams()
  if (options?.sourceId) params.append('source_id', options.sourceId)
  if (options?.activeOnly) params.append('active_only', 'true')
  if (options?.activeHours) params.append('active_hours', options.activeHours.toString())

  const response = await api.get<Node[]>(`/api/nodes?${params.toString()}`)
  return response.data
}

export async function fetchNode(id: string): Promise<Node> {
  const response = await api.get<Node>(`/api/nodes/${id}`)
  return response.data
}

export async function fetchNodesByNodeNum(nodeNum: number): Promise<Node[]> {
  const response = await api.get<Node[]>(`/api/nodes/by-node-num/${nodeNum}`)
  return response.data
}

// Telemetry
export async function fetchTelemetry(nodeNum: number, hours?: number): Promise<Telemetry[]> {
  const params = new URLSearchParams()
  if (hours) params.append('hours', hours.toString())

  const response = await api.get<Telemetry[]>(`/api/telemetry/${nodeNum}?${params.toString()}`)
  return response.data
}

export async function fetchTelemetryHistory(nodeNum: number, metric: string, hours?: number): Promise<TelemetryHistory> {
  const params = new URLSearchParams()
  if (hours) params.append('hours', hours.toString())

  const response = await api.get<TelemetryHistory>(`/api/telemetry/${nodeNum}/history/${metric}?${params.toString()}`)
  return response.data
}

// Health
export async function fetchHealth(): Promise<{ status: string; database: string; version: string }> {
  const response = await api.get<{ status: string; database: string; version: string }>('/health')
  return response.data
}

// Collection Status
export async function fetchCollectionStatuses(): Promise<Record<string, CollectionStatus>> {
  const response = await api.get<Record<string, CollectionStatus>>('/api/sources/collection-status')
  return response.data
}

// Traceroutes
export async function fetchTraceroutes(hours?: number): Promise<Traceroute[]> {
  const params = new URLSearchParams()
  if (hours) params.append('hours', hours.toString())

  const response = await api.get<Traceroute[]>(`/api/traceroutes?${params.toString()}`)
  return response.data
}

// Node Roles
export async function fetchNodeRoles(): Promise<string[]> {
  const response = await api.get<string[]>('/api/nodes/roles')
  return response.data
}
