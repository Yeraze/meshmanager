export interface Source {
  id: string
  name: string
  type: 'meshmonitor' | 'mqtt'
  enabled: boolean
  healthy: boolean
  // MeshMonitor fields
  url?: string
  api_token?: string
  poll_interval_seconds?: number
  historical_days_back?: number
  // MQTT fields
  mqtt_host?: string
  mqtt_port?: number
  mqtt_username?: string
  mqtt_password?: string
  mqtt_topic_pattern?: string
  mqtt_use_tls?: boolean
  // Status
  last_poll_at?: string
  last_error?: string
  remote_version?: string  // Version from remote MeshMonitor instance
}

export interface Node {
  id: string
  source_id: string
  source_name: string | null
  node_num: number
  node_id: string | null
  short_name: string | null
  long_name: string | null
  hw_model: string | null
  role: string | null
  latitude: number | null
  longitude: number | null
  snr: number | null
  rssi: number | null
  hops_away: number | null
  last_heard: string | null
}

export interface NodeDetail extends Node {
  altitude: number | null
  position_time: string | null
  position_precision_bits: number | null
  is_licensed: boolean
  first_seen: string
  updated_at: string
}

export interface AuthStatus {
  authenticated: boolean
  user: UserInfo | null
  oidc_enabled: boolean
  setup_required: boolean
  totp_required: boolean
  local_auth_disabled: boolean
  anonymous_permissions: UserPermissions | null
}

export interface TabPermission {
  read: boolean
  write: boolean
}

export interface UserPermissions {
  map: TabPermission
  nodes: TabPermission
  graphs: TabPermission
  analysis: TabPermission
  communication: TabPermission
  settings: TabPermission
}

export type UserRole = 'admin' | 'user'

export interface UserInfo {
  id: string
  username: string | null
  email: string | null
  display_name: string | null
  role: UserRole
  is_admin: boolean
  auth_provider: string
  permissions: UserPermissions
  totp_enabled: boolean
  is_anonymous: boolean
}

export interface AdminUser {
  id: string
  username: string | null
  email: string | null
  display_name: string | null
  role: UserRole
  is_admin: boolean
  auth_provider: string
  is_active: boolean
  permissions: UserPermissions
  totp_enabled: boolean
  is_anonymous: boolean
  created_at: string | null
  last_login_at: string | null
}

export interface AdminUserCreate {
  username: string
  password: string
  email?: string
  display_name?: string
  is_admin: boolean
  permissions?: UserPermissions
}

export interface AdminUserUpdate {
  email?: string
  display_name?: string
  is_admin?: boolean
  is_active?: boolean
  password?: string
  permissions?: UserPermissions
  reset_totp?: boolean
}

export interface TotpSetupResponse {
  secret: string
  qr_code_svg: string
  provisioning_uri: string
}

export interface LoginResponse {
  message: string
  user?: UserInfo
  totp_required?: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
  display_name?: string
}

export interface SourceCreate {
  name: string
  enabled?: boolean
}

export interface MeshMonitorSourceCreate extends SourceCreate {
  url: string
  api_token?: string
  poll_interval_seconds?: number
  historical_days_back?: number
}

export interface MqttSourceCreate extends SourceCreate {
  mqtt_host: string
  mqtt_port?: number
  mqtt_username?: string
  mqtt_password?: string
  mqtt_topic_pattern: string
  mqtt_use_tls?: boolean
}

export interface MeshMonitorSourceUpdate {
  name?: string
  url?: string
  api_token?: string
  poll_interval_seconds?: number
  historical_days_back?: number
  enabled?: boolean
}

export interface MqttSourceUpdate {
  name?: string
  mqtt_host?: string
  mqtt_port?: number
  mqtt_username?: string
  mqtt_password?: string
  mqtt_topic_pattern?: string
  mqtt_use_tls?: boolean
  enabled?: boolean
}

export interface Telemetry {
  id: string
  source_id: string
  source_name: string | null
  node_num: number
  telemetry_type: string
  battery_level: number | null
  voltage: number | null
  channel_utilization: number | null
  air_util_tx: number | null
  uptime_seconds: number | null
  temperature: number | null
  relative_humidity: number | null
  barometric_pressure: number | null
  current: number | null
  received_at: string
}

export interface TelemetryHistoryPoint {
  timestamp: string
  source_id: string
  source_name: string | null
  value: number | null
}

export interface TelemetryHistory {
  metric: string
  unit: string
  data: TelemetryHistoryPoint[]
}

export interface AvailableMetric {
  name: string
  label: string
  unit: string
  count: number
}

export interface AvailableMetrics {
  node_num: number
  hours: number
  metrics: Record<string, AvailableMetric[]>
}

export interface CollectionStatus {
  status: 'idle' | 'collecting' | 'complete' | 'error' | 'cancelled'
  current_batch: number
  max_batches: number
  total_collected: number
  last_error: string | null
  elapsed_seconds?: number  // Time elapsed since collection started
  estimated_seconds_remaining?: number  // Estimated time remaining (calculated by backend)
}

export interface Traceroute {
  id: string
  source_id: string
  from_node_num: number
  to_node_num: number
  route: number[]
  route_back: number[] | null
  route_positions: Record<string, { lat: number; lng: number; alt?: number }> | null
  received_at: string
}
