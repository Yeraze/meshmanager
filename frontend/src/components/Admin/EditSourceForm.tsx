import { useState, useEffect } from 'react'
import { useUpdateMeshMonitorSource, useUpdateMqttSource } from '../../hooks/useAdminSources'
import type { Source } from '../../types/api'
import styles from './AdminPanel.module.css'

interface EditSourceFormProps {
  source: Source
  onSuccess: () => void
  onCancel: () => void
}

export function EditSourceForm({ source, onSuccess, onCancel }: EditSourceFormProps) {
  const [error, setError] = useState<string | null>(null)

  // Common fields
  const [name, setName] = useState(source.name)
  const [enabled, setEnabled] = useState(source.enabled)

  // MeshMonitor fields
  const [url, setUrl] = useState(source.url || '')
  const [apiToken, setApiToken] = useState('') // Don't pre-fill for security
  const [pollInterval, setPollInterval] = useState(source.poll_interval_seconds || 300)
  const [historicalDaysBack, setHistoricalDaysBack] = useState(source.historical_days_back || 1)

  // MQTT fields
  const [mqttHost, setMqttHost] = useState(source.mqtt_host || '')
  const [mqttPort, setMqttPort] = useState(source.mqtt_port || 1883)
  const [mqttUsername, setMqttUsername] = useState(source.mqtt_username || '')
  const [mqttPassword, setMqttPassword] = useState('') // Don't pre-fill for security
  const [mqttTopic, setMqttTopic] = useState(source.mqtt_topic_pattern || '')
  const [mqttUseTls, setMqttUseTls] = useState(source.mqtt_use_tls || false)

  const updateMeshMonitor = useUpdateMeshMonitorSource()
  const updateMqtt = useUpdateMqttSource()

  // Update form when source changes
  useEffect(() => {
    setName(source.name)
    setUrl(source.url || '')
    setPollInterval(source.poll_interval_seconds || 300)
    setHistoricalDaysBack(source.historical_days_back || 1)
    setEnabled(source.enabled)
    setMqttHost(source.mqtt_host || '')
    setMqttPort(source.mqtt_port || 1883)
    setMqttUsername(source.mqtt_username || '')
    setMqttTopic(source.mqtt_topic_pattern || '')
    setMqttUseTls(source.mqtt_use_tls || false)
    // Don't reset password/token fields - let user change if needed
  }, [source])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (source.type === 'meshmonitor') {
        const updateData: Partial<{
          name: string
          url: string
          api_token?: string
          poll_interval_seconds: number
          historical_days_back: number
          enabled: boolean
        }> = {
          name,
          url,
          poll_interval_seconds: pollInterval,
          historical_days_back: historicalDaysBack,
          enabled,
        }
        // Only include api_token if it was changed (not empty)
        if (apiToken) {
          updateData.api_token = apiToken
        }
        await updateMeshMonitor.mutateAsync({ id: source.id, data: updateData })
      } else {
        const updateData: Partial<{
          name: string
          mqtt_host: string
          mqtt_port: number
          mqtt_username?: string
          mqtt_password?: string
          mqtt_topic_pattern: string
          mqtt_use_tls: boolean
          enabled: boolean
        }> = {
          name,
          mqtt_host: mqttHost,
          mqtt_port: mqttPort,
          mqtt_topic_pattern: mqttTopic,
          mqtt_use_tls: mqttUseTls,
          enabled,
        }
        // Only include username/password if they were changed
        if (mqttUsername !== (source.mqtt_username || '')) {
          updateData.mqtt_username = mqttUsername || undefined
        }
        if (mqttPassword) {
          updateData.mqtt_password = mqttPassword
        }
        await updateMqtt.mutateAsync({ id: source.id, data: updateData })
      }
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update source')
    }
  }

  const isPending = updateMeshMonitor.isPending || updateMqtt.isPending

  return (
    <form onSubmit={handleSubmit} className={styles.addForm}>
      <h4>Edit {source.type === 'meshmonitor' ? 'MeshMonitor' : 'MQTT'} Source</h4>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.formRow}>
        <label htmlFor="edit-name">Name</label>
        <input
          id="edit-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="My MeshMonitor"
        />
      </div>

      <div className={styles.formRow}>
        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enabled
        </label>
      </div>

      {source.type === 'meshmonitor' ? (
        <>
          <div className={styles.formRow}>
            <label htmlFor="edit-url">URL</label>
            <input
              id="edit-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://meshmonitor.example.com"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-apiToken">API Token (leave blank to keep current)</label>
            <input
              id="edit-apiToken"
              type="password"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              placeholder="Enter new token or leave blank"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-pollInterval">Poll Interval (seconds)</label>
            <input
              id="edit-pollInterval"
              type="number"
              value={pollInterval}
              onChange={(e) => setPollInterval(parseInt(e.target.value) || 300)}
              min={60}
              max={86400}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-historicalDaysBack">Historical Data (days)</label>
            <select
              id="edit-historicalDaysBack"
              value={historicalDaysBack}
              onChange={(e) => setHistoricalDaysBack(parseInt(e.target.value))}
            >
              <option value={1}>1 day (fastest)</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days (slowest)</option>
            </select>
            <small style={{ display: 'block', marginTop: '4px', color: '#666' }}>
              Days of historical data to sync on initial collection
            </small>
          </div>
        </>
      ) : (
        <>
          <div className={styles.formRow}>
            <label htmlFor="edit-mqttHost">MQTT Host</label>
            <input
              id="edit-mqttHost"
              type="text"
              value={mqttHost}
              onChange={(e) => setMqttHost(e.target.value)}
              required
              placeholder="mqtt.example.com"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-mqttPort">MQTT Port</label>
            <input
              id="edit-mqttPort"
              type="number"
              value={mqttPort}
              onChange={(e) => setMqttPort(parseInt(e.target.value) || 1883)}
              min={1}
              max={65535}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-mqttUsername">Username (leave blank to keep current)</label>
            <input
              id="edit-mqttUsername"
              type="text"
              value={mqttUsername}
              onChange={(e) => setMqttUsername(e.target.value)}
              placeholder="Enter new username or leave blank"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-mqttPassword">Password (leave blank to keep current)</label>
            <input
              id="edit-mqttPassword"
              type="password"
              value={mqttPassword}
              onChange={(e) => setMqttPassword(e.target.value)}
              placeholder="Enter new password or leave blank"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="edit-mqttTopic">Topic Pattern</label>
            <input
              id="edit-mqttTopic"
              type="text"
              value={mqttTopic}
              onChange={(e) => setMqttTopic(e.target.value)}
              required
              placeholder="msh/+/2/json/#"
            />
          </div>

          <div className={styles.formRow}>
            <label className={styles.checkbox}>
              <input
                type="checkbox"
                checked={mqttUseTls}
                onChange={(e) => setMqttUseTls(e.target.checked)}
              />
              Use TLS
            </label>
          </div>
        </>
      )}

      <div className={styles.formActions}>
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={isPending}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={isPending}>
          {isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}
