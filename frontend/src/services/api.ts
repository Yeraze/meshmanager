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

// Coverage Map
export interface CoverageConfig {
  enabled: boolean
  resolution: number
  unit: 'miles' | 'kilometers'
  lookback_days: number
  bounds_south: number | null
  bounds_west: number | null
  bounds_north: number | null
  bounds_east: number | null
  last_generated: string | null
  cell_count: number
}

export interface CoverageConfigUpdate {
  enabled: boolean
  resolution: number
  unit: 'miles' | 'kilometers'
  lookback_days: number
  bounds_south: number | null
  bounds_west: number | null
  bounds_north: number | null
  bounds_east: number | null
}

export interface CoverageCell {
  south: number
  west: number
  north: number
  east: number
  count: number
  color: string
}

export interface CoverageGenerateResponse {
  success: boolean
  cell_count: number
  message: string
}

export async function fetchCoverageConfig(): Promise<CoverageConfig> {
  const response = await api.get<CoverageConfig>('/api/coverage/config')
  return response.data
}

export async function updateCoverageConfig(config: CoverageConfigUpdate): Promise<CoverageConfig> {
  const response = await api.put<CoverageConfig>('/api/coverage/config', config)
  return response.data
}

export async function generateCoverage(): Promise<CoverageGenerateResponse> {
  const response = await api.post<CoverageGenerateResponse>('/api/coverage/generate')
  return response.data
}

export async function fetchCoverageCells(): Promise<CoverageCell[]> {
  const response = await api.get<CoverageCell[]>('/api/coverage/cells')
  return response.data
}

export interface PositionPoint {
  lat: number
  lng: number
}

export interface PositionHistoryParams {
  lookback_days?: number
  bounds_south?: number
  bounds_west?: number
  bounds_north?: number
  bounds_east?: number
}

export async function fetchPositionHistory(params?: PositionHistoryParams): Promise<PositionPoint[]> {
  const response = await api.get<PositionPoint[]>('/api/coverage/positions', { params })
  return response.data
}

// Utilization Map
export type AggregationType = 'min' | 'max' | 'avg'

export interface UtilizationConfig {
  enabled: boolean
  resolution: number
  unit: 'miles' | 'kilometers'
  lookback_days: number
  aggregation: AggregationType
  bounds_south: number | null
  bounds_west: number | null
  bounds_north: number | null
  bounds_east: number | null
  last_generated: string | null
  cell_count: number
}

export interface UtilizationConfigUpdate {
  enabled: boolean
  resolution: number
  unit: 'miles' | 'kilometers'
  lookback_days: number
  aggregation: AggregationType
  bounds_south: number | null
  bounds_west: number | null
  bounds_north: number | null
  bounds_east: number | null
}

export interface UtilizationCell {
  south: number
  west: number
  north: number
  east: number
  value: number
  color: string
}

export interface UtilizationGenerateResponse {
  success: boolean
  cell_count: number
  message: string
}

export async function fetchUtilizationConfig(): Promise<UtilizationConfig> {
  const response = await api.get<UtilizationConfig>('/api/utilization/config')
  return response.data
}

export async function updateUtilizationConfig(config: UtilizationConfigUpdate): Promise<UtilizationConfig> {
  const response = await api.put<UtilizationConfig>('/api/utilization/config', config)
  return response.data
}

export async function generateUtilization(): Promise<UtilizationGenerateResponse> {
  const response = await api.post<UtilizationGenerateResponse>('/api/utilization/generate')
  return response.data
}

export async function fetchUtilizationCells(): Promise<UtilizationCell[]> {
  const response = await api.get<UtilizationCell[]>('/api/utilization/cells')
  return response.data
}

// Solar Production
export interface SolarDataPoint {
  timestamp: number
  wattHours: number
  sourceCount: number
}

export async function fetchSolarData(hours?: number): Promise<SolarDataPoint[]> {
  const params = new URLSearchParams()
  if (hours) params.append('hours', hours.toString())

  const response = await api.get<SolarDataPoint[]>(`/api/solar?${params.toString()}`)
  return response.data
}

// Solar Analysis
export interface SolarPattern {
  date: string
  sunrise: { time: string; value: number }
  peak: { time: string; value: number }
  sunset: { time: string; value: number }
  rise: number
  fall: number
}

export interface SolarChartPoint {
  timestamp: number
  value: number
}

export interface SolarNode {
  node_num: number
  node_name: string
  solar_score: number
  days_analyzed: number
  days_with_pattern: number
  recent_patterns: SolarPattern[]
  metric_type: 'battery' | 'voltage'
  chart_data: SolarChartPoint[]
}

export interface SolarProductionPoint {
  timestamp: number
  wattHours: number
}

export interface SolarNodesAnalysis {
  lookback_days: number
  total_nodes_analyzed: number
  solar_nodes_count: number
  solar_nodes: SolarNode[]
  solar_production: SolarProductionPoint[]
}

export async function fetchSolarNodesAnalysis(lookbackDays?: number): Promise<SolarNodesAnalysis> {
  const params = new URLSearchParams()
  if (lookbackDays) params.append('lookback_days', lookbackDays.toString())

  const response = await api.get<SolarNodesAnalysis>(`/api/analysis/solar-nodes?${params.toString()}`)
  return response.data
}
