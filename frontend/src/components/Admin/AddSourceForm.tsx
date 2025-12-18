import { useState } from 'react'
import { useCreateMeshMonitorSource, useCreateMqttSource } from '../../hooks/useAdminSources'
import styles from './AdminPanel.module.css'

interface AddSourceFormProps {
  onSuccess: () => void
}

export function AddSourceForm({ onSuccess }: AddSourceFormProps) {
  const [sourceType, setSourceType] = useState<'meshmonitor' | 'mqtt'>('meshmonitor')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  // MeshMonitor fields
  const [url, setUrl] = useState('')
  const [apiToken, setApiToken] = useState('')
  const [pollInterval, setPollInterval] = useState(60)
  const [historicalDaysBack, setHistoricalDaysBack] = useState(1)

  // MQTT fields
  const [mqttHost, setMqttHost] = useState('')
  const [mqttPort, setMqttPort] = useState(1883)
  const [mqttUsername, setMqttUsername] = useState('')
  const [mqttPassword, setMqttPassword] = useState('')
  const [mqttTopic, setMqttTopic] = useState('msh/+/2/json/#')
  const [mqttUseTls, setMqttUseTls] = useState(false)

  const createMeshMonitor = useCreateMeshMonitorSource()
  const createMqtt = useCreateMqttSource()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (sourceType === 'meshmonitor') {
        await createMeshMonitor.mutateAsync({
          name,
          url,
          api_token: apiToken || undefined,
          poll_interval_seconds: pollInterval,
          historical_days_back: historicalDaysBack,
        })
      } else {
        await createMqtt.mutateAsync({
          name,
          mqtt_host: mqttHost,
          mqtt_port: mqttPort,
          mqtt_username: mqttUsername || undefined,
          mqtt_password: mqttPassword || undefined,
          mqtt_topic_pattern: mqttTopic,
          mqtt_use_tls: mqttUseTls,
        })
      }
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create source')
    }
  }

  const isPending = createMeshMonitor.isPending || createMqtt.isPending

  return (
    <form onSubmit={handleSubmit} className={styles.addForm}>
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.formRow}>
        <label>Source Type</label>
        <div className={styles.radioGroup}>
          <label>
            <input
              type="radio"
              name="sourceType"
              value="meshmonitor"
              checked={sourceType === 'meshmonitor'}
              onChange={() => setSourceType('meshmonitor')}
            />
            MeshMonitor
          </label>
          <label>
            <input
              type="radio"
              name="sourceType"
              value="mqtt"
              checked={sourceType === 'mqtt'}
              onChange={() => setSourceType('mqtt')}
            />
            MQTT
          </label>
        </div>
      </div>

      <div className={styles.formRow}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="My MeshMonitor"
        />
      </div>

      {sourceType === 'meshmonitor' ? (
        <>
          <div className={styles.formRow}>
            <label htmlFor="url">URL</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://meshmonitor.example.com"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="apiToken">API Token (optional)</label>
            <input
              id="apiToken"
              type="password"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              placeholder="Bearer token if required"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="pollInterval">Poll Interval (seconds)</label>
            <input
              id="pollInterval"
              type="number"
              value={pollInterval}
              onChange={(e) => setPollInterval(parseInt(e.target.value) || 60)}
              min={10}
              max={3600}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="historicalDaysBack">Historical Data (days)</label>
            <select
              id="historicalDaysBack"
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
            <label htmlFor="mqttHost">MQTT Host</label>
            <input
              id="mqttHost"
              type="text"
              value={mqttHost}
              onChange={(e) => setMqttHost(e.target.value)}
              required
              placeholder="mqtt.example.com"
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="mqttPort">MQTT Port</label>
            <input
              id="mqttPort"
              type="number"
              value={mqttPort}
              onChange={(e) => setMqttPort(parseInt(e.target.value) || 1883)}
              min={1}
              max={65535}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="mqttUsername">Username (optional)</label>
            <input
              id="mqttUsername"
              type="text"
              value={mqttUsername}
              onChange={(e) => setMqttUsername(e.target.value)}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="mqttPassword">Password (optional)</label>
            <input
              id="mqttPassword"
              type="password"
              value={mqttPassword}
              onChange={(e) => setMqttPassword(e.target.value)}
            />
          </div>

          <div className={styles.formRow}>
            <label htmlFor="mqttTopic">Topic Pattern</label>
            <input
              id="mqttTopic"
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
        <button type="submit" className="btn btn-primary" disabled={isPending}>
          {isPending ? 'Creating...' : 'Create Source'}
        </button>
      </div>
    </form>
  )
}
