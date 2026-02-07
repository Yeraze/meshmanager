import axios from 'axios'
import type {
  AuthStatus,
  CollectionStatus,
  LoginRequest,
  MeshMonitorSourceCreate,
  MeshMonitorSourceUpdate,
  MqttSourceCreate,
  MqttSourceUpdate,
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

export async function updateMeshMonitorSource(id: string, data: MeshMonitorSourceUpdate): Promise<Source> {
  const response = await api.put<Source>(`/api/admin/sources/meshmonitor/${id}`, data)
  return response.data
}

export async function updateMqttSource(id: string, data: MqttSourceUpdate): Promise<Source> {
  const response = await api.put<Source>(`/api/admin/sources/mqtt/${id}`, data)
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

// Node Connections Graph
export interface ConnectionNode {
  id: number
  node_num: number
  name: string
  short_name?: string
  long_name?: string
  latitude: number
  longitude: number
  role?: string
  hw_model?: string
  last_heard?: string
}

export interface ConnectionEdge {
  source: number
  target: number
  usage: number
}

export interface ConnectionsGraph {
  nodes: ConnectionNode[]
  edges: ConnectionEdge[]
}

export async function fetchConnections(hours?: number, nodeNum?: number): Promise<ConnectionsGraph> {
  const params = new URLSearchParams()
  if (hours) params.append('hours', hours.toString())
  if (nodeNum !== undefined) params.append('node_num', nodeNum.toString())

  const response = await api.get<ConnectionsGraph>(`/api/connections?${params.toString()}`)
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

// Message Activity
export interface MessageActivityPoint {
  lat: number
  lng: number
  count: number
}

export interface MessageActivityParams {
  lookback_days?: number
  bounds_south?: number
  bounds_west?: number
  bounds_north?: number
  bounds_east?: number
}

export async function fetchMessageActivity(params?: MessageActivityParams): Promise<MessageActivityPoint[]> {
  const response = await api.get<MessageActivityPoint[]>('/api/coverage/message-activity', { params })
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
  charge_rate_per_hour: number
  discharge_rate_per_hour: number | null
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
  avg_charge_rate_per_hour: number | null
  avg_discharge_rate_per_hour: number | null
  insufficient_solar: boolean | null
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
  avg_charging_hours_per_day: number | null
  avg_discharge_hours_per_day: number | null
}

export async function fetchSolarNodesAnalysis(lookbackDays?: number): Promise<SolarNodesAnalysis> {
  const params = new URLSearchParams()
  if (lookbackDays) params.append('lookback_days', lookbackDays.toString())

  const response = await api.get<SolarNodesAnalysis>(`/api/analysis/solar-nodes?${params.toString()}`)
  return response.data
}

// Solar Forecast Analysis
export interface ForecastDay {
  date: string
  forecast_wh: number
  avg_historical_wh: number
  pct_of_average: number
  is_low: boolean
}

export interface ForecastSimulationDay {
  timestamp: string
  simulated_battery: number
  phase: 'sunrise' | 'peak' | 'sunset'
  forecast_factor: number
}

export interface NodeAtRisk {
  node_num: number
  node_name: string
  current_battery: number
  min_simulated_battery: number
  avg_charge_rate_per_hour: number
  avg_discharge_rate_per_hour: number
  simulation: ForecastSimulationDay[]
}

export interface SolarForecastAnalysis {
  lookback_days: number
  historical_days_analyzed: number
  avg_historical_daily_wh: number
  low_output_warning: boolean
  forecast_days: ForecastDay[]
  nodes_at_risk_count: number
  nodes_at_risk: NodeAtRisk[]
  solar_simulations: NodeAtRisk[]
}

export async function fetchSolarForecastAnalysis(lookbackDays?: number): Promise<SolarForecastAnalysis> {
  const params = new URLSearchParams()
  if (lookbackDays) params.append('lookback_days', lookbackDays.toString())

  const response = await api.get<SolarForecastAnalysis>(`/api/analysis/solar-forecast?${params.toString()}`)
  return response.data
}

// Solar Schedule Settings
export interface SolarScheduleSettings {
  enabled: boolean
  schedules: string[]  // Array of "HH:MM" time strings
  apprise_urls: string[]
  lookback_days: number
}

export async function getSolarScheduleSettings(): Promise<SolarScheduleSettings> {
  const response = await api.get<SolarScheduleSettings>('/api/settings/solar-schedule')
  return response.data
}

export async function updateSolarScheduleSettings(settings: SolarScheduleSettings): Promise<SolarScheduleSettings> {
  const response = await api.put<SolarScheduleSettings>('/api/settings/solar-schedule', settings)
  return response.data
}

export async function testSolarNotification(): Promise<{ success: boolean; message: string }> {
  const response = await api.post<{ success: boolean; message: string }>('/api/settings/solar-schedule/test')
  return response.data
}

// Message Utilization Analysis
export interface MessageUtilizationNode {
  node_num: number
  node_name: string
  total: number
  breakdown: Record<string, number>
}

export interface MessageUtilizationHour {
  hour: number
  total: number
  breakdown: Record<string, number>
}

export interface MessageUtilizationFilters {
  text: boolean
  device: boolean
  environment: boolean
  power: boolean
  position: boolean
  air_quality: boolean
  exclude_local_nodes: boolean
}

export interface MessageUtilizationAnalysis {
  lookback_days: number
  total_messages: number
  total_nodes: number
  type_breakdown: Record<string, number>
  top_nodes: MessageUtilizationNode[]
  hourly_histogram: MessageUtilizationHour[]
  filters: MessageUtilizationFilters
  local_nodes_excluded: number
}

export interface MessageUtilizationParams {
  lookback_days?: number
  include_text?: boolean
  include_device?: boolean
  include_environment?: boolean
  include_power?: boolean
  include_position?: boolean
  include_air_quality?: boolean
  exclude_local_nodes?: boolean
}

export async function fetchMessageUtilizationAnalysis(
  params?: MessageUtilizationParams
): Promise<MessageUtilizationAnalysis> {
  const queryParams = new URLSearchParams()
  if (params?.lookback_days) queryParams.append('lookback_days', params.lookback_days.toString())
  if (params?.include_text !== undefined) queryParams.append('include_text', params.include_text.toString())
  if (params?.include_device !== undefined) queryParams.append('include_device', params.include_device.toString())
  if (params?.include_environment !== undefined) queryParams.append('include_environment', params.include_environment.toString())
  if (params?.include_power !== undefined) queryParams.append('include_power', params.include_power.toString())
  if (params?.include_position !== undefined) queryParams.append('include_position', params.include_position.toString())
  if (params?.include_air_quality !== undefined) queryParams.append('include_air_quality', params.include_air_quality.toString())
  if (params?.exclude_local_nodes !== undefined) queryParams.append('exclude_local_nodes', params.exclude_local_nodes.toString())

  const response = await api.get<MessageUtilizationAnalysis>(`/api/analysis/message-utilization?${queryParams.toString()}`)
  return response.data
}

// Message Channels (Communication Page)
export interface ChannelSourceName {
  source_name: string
  channel_name: string | null
}

export interface ChannelSummary {
  channel_index: number
  display_name: string
  message_count: number
  last_message_at: string | null
  source_names: ChannelSourceName[]
}

export interface MessageResponse {
  packet_id: string
  from_node_num: number
  to_node_num: number | null
  channel: number
  text: string | null
  emoji: string | null
  reply_id: number | null
  hop_limit: number | null
  hop_start: number | null
  rx_time: string | null
  received_at: string
  from_short_name: string | null
  from_long_name: string | null
  source_count: number
}

export interface MessagesListResponse {
  messages: MessageResponse[]
  has_more: boolean
  next_cursor: string | null
}

export interface MessageSourceDetail {
  source_id: string
  source_name: string
  rx_snr: number | null
  rx_rssi: number | null
  hop_limit: number | null
  hop_start: number | null
  hop_count: number | null
  rx_time: string | null
  received_at: string
}

export async function fetchMessageChannels(): Promise<ChannelSummary[]> {
  const response = await api.get<ChannelSummary[]>('/api/messages/channels')
  return response.data
}

export async function fetchMessages(
  channel: number,
  limit?: number,
  before?: string,
  sourceNames?: string[]
): Promise<MessagesListResponse> {
  const params = new URLSearchParams()
  params.append('channel', channel.toString())
  if (limit) params.append('limit', limit.toString())
  if (before) params.append('before', before)
  if (sourceNames) {
    sourceNames.forEach((name) => params.append('source_names', name))
  }

  const response = await api.get<MessagesListResponse>(`/api/messages?${params.toString()}`)
  return response.data
}

export async function fetchMessageSources(packetId: string): Promise<MessageSourceDetail[]> {
  const response = await api.get<MessageSourceDetail[]>(
    `/api/messages/${encodeURIComponent(packetId)}/sources`
  )
  return response.data
}

// Configuration Export/Import
export interface DisplaySettingsConfig {
  active_hours: number
  online_hours: number
}

export interface ImportResult {
  success: boolean
  sources_imported: number
  sources_skipped: number
  display_settings_imported: boolean
  analysis_configs_imported: string[]
  warnings: string[]
  display_settings: DisplaySettingsConfig | null
}

export async function exportConfig(options?: {
  include_credentials?: boolean
}): Promise<Blob> {
  const params = new URLSearchParams()
  if (options?.include_credentials !== undefined) {
    params.append('include_credentials', String(options.include_credentials))
  }
  const queryString = params.toString()
  const url = queryString
    ? `/api/admin/config/export?${queryString}`
    : '/api/admin/config/export'
  const response = await api.get(url, {
    responseType: 'blob',
  })
  return response.data
}

export async function importConfig(
  config: unknown,
  options?: { merge_sources?: boolean }
): Promise<ImportResult> {
  const params = new URLSearchParams()
  if (options?.merge_sources !== undefined) {
    params.append('merge_sources', String(options.merge_sources))
  }

  const response = await api.post<ImportResult>(
    `/api/admin/config/import?${params.toString()}`,
    config
  )
  return response.data
}
