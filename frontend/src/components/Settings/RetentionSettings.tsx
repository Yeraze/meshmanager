import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRetentionSettings, updateRetentionSettings, RetentionSettings as RetentionSettingsType } from '../../services/api'

export default function RetentionSettings() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<RetentionSettingsType>({ messages: 30, telemetry: 7, traceroutes: 30 })
  const [hasChanges, setHasChanges] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['retention-settings'],
    queryFn: getRetentionSettings,
  })

  useEffect(() => {
    if (data) {
      setForm(data)
      setHasChanges(false)
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: updateRetentionSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retention-settings'] })
      setSuccessMsg('Retention settings saved successfully.')
      setHasChanges(false)
      setTimeout(() => setSuccessMsg(null), 3000)
    },
    onError: () => {
      setErrorMsg('Failed to save retention settings.')
      setTimeout(() => setErrorMsg(null), 5000)
    },
  })

  const handleChange = (key: keyof RetentionSettingsType, value: string) => {
    const num = parseInt(value, 10)
    if (!isNaN(num) && num >= 1 && num <= 365) {
      setForm((prev) => ({ ...prev, [key]: num }))
      setHasChanges(true)
      setSuccessMsg(null)
      setErrorMsg(null)
    }
  }

  const handleSave = () => {
    mutation.mutate(form)
  }

  if (isLoading) return null

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Data Retention</h2>
      </div>

      <div className="settings-card">
        <p className="settings-description">
          Configure how long data is kept before automatic cleanup. The cleanup service runs every 24 hours.
        </p>

        <div className="form-group">
          <label className="form-label">Messages</label>
          <p className="settings-hint">Text messages, replies, and reactions.</p>
          <div className="custom-hours-input">
            <input
              type="number"
              className="form-input"
              min={1}
              max={365}
              value={form.messages}
              onChange={(e) => handleChange('messages', e.target.value)}
            />
            <span className="hours-label">days</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Telemetry</label>
          <p className="settings-hint">Device, environment, power, air quality, position, local stats, health, and host metrics.</p>
          <div className="custom-hours-input">
            <input
              type="number"
              className="form-input"
              min={1}
              max={365}
              value={form.telemetry}
              onChange={(e) => handleChange('telemetry', e.target.value)}
            />
            <span className="hours-label">days</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Traceroutes</label>
          <p className="settings-hint">Route paths, SNR data, and node positions at time of trace.</p>
          <div className="custom-hours-input">
            <input
              type="number"
              className="form-input"
              min={1}
              max={365}
              value={form.traceroutes}
              onChange={(e) => handleChange('traceroutes', e.target.value)}
            />
            <span className="hours-label">days</span>
          </div>
        </div>

        {successMsg && <p className="settings-hint" style={{ color: 'var(--ctp-green)' }}>{successMsg}</p>}
        {errorMsg && <p className="settings-hint" style={{ color: 'var(--ctp-red)' }}>{errorMsg}</p>}

        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={!hasChanges || mutation.isPending}
        >
          {mutation.isPending ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  )
}
