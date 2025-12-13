import { useState } from 'react'
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
  const [apiToken, setApiToken] = useState('')
  const [pollInterval, setPollInterval] = useState(source.poll_interval_seconds || 60)

  // MQTT fields
  const [mqttHost, setMqttHost] = useState(source.mqtt_host || '')
  const [mqttPort, setMqttPort] = useState(source.mqtt_port || 1883)
  const [mqttUsername, setMqttUsername] = useState('')
  const [mqttPassword, setMqttPassword] = useState('')
  const [mqttTopic, setMqttTopic] = useState(source.mqtt_topic_pattern || '')
  const [mqttUseTls, setMqttUseTls] = useState(source.mqtt_use_tls || false)

  const updateMeshMonitor = useUpdateMeshMonitorSource()
  const updateMqtt = useUpdateMqttSource()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (source.type === 'meshmonitor') {
        await updateMeshMonitor.mutateAsync({
          id: source.id,
          data: {
            name,
            url,
            api_token: apiToken || undefined,
            poll_interval_seconds: pollInterval,
            enabled,
          },
        })
      } else {
        await updateMqtt.mutateAsync({
          id: source.id,
          data: {
            name,
            mqtt_host: mqttHost,
            mqtt_port: mqttPort,
            mqtt_username: mqttUsername || undefined,
            mqtt_password: mqttPassword || undefined,
            mqtt_topic_pattern: mqttTopic,
            mqtt_use_tls: mqttUseTls,
            enabled,
          },
        })
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
              onChange={(e) => setPollInterval(parseInt(e.target.value) || 60)}
              min={10}
              max={3600}
            />
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
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={isPending}>
          {isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}
