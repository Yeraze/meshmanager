import { useState } from 'react'
import { useAdminSources, useDeleteSource, useTestSource, useSyncSource, useCollectionStatuses } from '../../hooks/useAdminSources'
import { AddSourceForm } from '../Admin/AddSourceForm'
import { EditSourceForm } from '../Admin/EditSourceForm'
import type { CollectionStatus, Source } from '../../types/api'

function formatEta(seconds: number): string {
  if (seconds <= 0) return ''
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  }
  return `${secs}s`
}

function CollectionStatusIndicator({ status }: { status: CollectionStatus | undefined }) {
  if (!status) {
    return null
  }

  if (status.status === 'collecting') {
    const progress = status.max_batches > 0
      ? Math.round((status.current_batch / status.max_batches) * 100)
      : 0
    
    // Use backend-provided ETA if available (more accurate, based on actual progress)
    // Fall back to simple calculation if backend hasn't provided it yet
    let etaSeconds = status.estimated_seconds_remaining
    if (etaSeconds === undefined && status.max_batches > 0 && status.current_batch > 0) {
      // Fallback: estimate based on progress so far
      const remainingNodes = status.max_batches - status.current_batch
      const elapsed = status.elapsed_seconds || 0
      if (elapsed > 0 && status.current_batch > 0) {
        // Calculate average time per node based on actual progress
        const avgTimePerNode = elapsed / status.current_batch
        // Account for parallel processing (10 nodes in parallel)
        const maxConcurrent = 10
        etaSeconds = Math.ceil((remainingNodes / maxConcurrent) * avgTimePerNode)
      }
    }
    
    const etaText = etaSeconds !== undefined && etaSeconds > 0 ? formatEta(etaSeconds) : ''
    const elapsedText = status.elapsed_seconds !== undefined && status.elapsed_seconds > 0 
      ? formatEta(status.elapsed_seconds) 
      : ''
    
    return (
      <div className="collection-status collecting">
        <div className="collection-progress-bar">
          <div className="collection-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <span className="collection-status-text">
          Collecting... {status.current_batch}/{status.max_batches} ({status.total_collected} records)
          {elapsedText && <span className="collection-elapsed"> • Elapsed: {elapsedText}</span>}
          {etaText && <span className="collection-eta"> • Remaining: {etaText}</span>}
        </span>
      </div>
    )
  }

  if (status.status === 'complete') {
    return (
      <div className="collection-status complete">
        <span className="collection-check">✓</span>
        <span className="collection-status-text">Up to date</span>
      </div>
    )
  }

  if (status.status === 'error') {
    return (
      <div className="collection-status error">
        <span className="collection-error">✕</span>
        <span className="collection-status-text" title={status.last_error || 'Unknown error'}>
          Collection error
        </span>
      </div>
    )
  }

  if (status.status === 'cancelled') {
    return (
      <div className="collection-status error">
        <span className="collection-error">⚠</span>
        <span className="collection-status-text">
          Collection cancelled
        </span>
      </div>
    )
  }

  // idle status - don't show anything
  return null
}

export default function SourcesSettings() {
  const { data: sources = [], isLoading } = useAdminSources()
  const { data: collectionStatuses = {} } = useCollectionStatuses()
  const deleteMutation = useDeleteSource()
  const testMutation = useTestSource()
  const syncMutation = useSyncSource()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; nodes_found?: number }>>({})

  const handleDelete = async (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"? This will also delete all associated nodes and data.`)) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleTest = async (id: string) => {
    try {
      const result = await testMutation.mutateAsync(id)
      setTestResults((prev) => ({ ...prev, [id]: result }))
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, message: error instanceof Error ? error.message : 'Test failed' },
      }))
    }
  }

  const handleSync = async (id: string) => {
    try {
      await syncMutation.mutateAsync(id)
    } catch (error) {
      console.error('Sync failed:', error)
    }
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Data Sources</h2>
        <button
          className="btn btn-primary"
          onClick={() => {
            setShowAddForm(!showAddForm)
            if (showAddForm) {
              setEditingSource(null)
            }
          }}
          disabled={!!editingSource}
        >
          {showAddForm ? 'Cancel' : 'Add Source'}
        </button>
      </div>

      {showAddForm && (
        <div className="settings-card">
          <AddSourceForm onSuccess={() => setShowAddForm(false)} />
        </div>
      )}

      {editingSource && (
        <div className="settings-card">
          <EditSourceForm
            source={editingSource}
            onSuccess={() => setEditingSource(null)}
            onCancel={() => setEditingSource(null)}
          />
        </div>
      )}

      {isLoading ? (
        <div className="loading">
          <div className="loading-spinner" />
          Loading sources...
        </div>
      ) : sources.length === 0 ? (
        <div className="settings-empty">
          No sources configured. Add a MeshMonitor or MQTT source to get started.
        </div>
      ) : (
        <div className="settings-list">
          {sources.map((source) => (
            <div key={source.id} className="settings-card source-card">
              <div className="source-card-header">
                <div className="source-card-title">
                  <span className={`source-status ${source.healthy ? 'healthy' : 'unhealthy'}`} />
                  <span className="source-name">{source.name}</span>
                  <span className="badge">{source.type}</span>
                  {source.remote_version && (
                    <span className="badge badge-info">v{source.remote_version}</span>
                  )}
                </div>
                <div className="source-card-status">
                  <span className={`badge ${source.enabled ? 'badge-success' : 'badge-warning'}`}>
                    {source.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>

              {source.url && (
                <div className="source-card-detail">
                  <span className="detail-label">URL:</span>
                  <span className="detail-value">{source.url}</span>
                </div>
              )}

              {source.mqtt_host && (
                <div className="source-card-detail">
                  <span className="detail-label">MQTT Host:</span>
                  <span className="detail-value">{source.mqtt_host}:{source.mqtt_port}</span>
                </div>
              )}

              <CollectionStatusIndicator status={collectionStatuses[source.id]} />

              {testResults[source.id] && (
                <div className={`source-test-result ${testResults[source.id].success ? 'success' : 'error'}`}>
                  {testResults[source.id].message}
                  {testResults[source.id].success && testResults[source.id].nodes_found !== undefined && (
                    <span> ({testResults[source.id].nodes_found} nodes found)</span>
                  )}
                </div>
              )}

              <div className="source-card-actions">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setEditingSource(source)
                    setShowAddForm(false)
                  }}
                  disabled={!!editingSource || !!showAddForm}
                >
                  Edit
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleTest(source.id)}
                  disabled={testMutation.isPending}
                >
                  {testMutation.isPending ? 'Testing...' : 'Test Connection'}
                </button>
                {source.type === 'meshmonitor' && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleSync(source.id)}
                    disabled={syncMutation.isPending || collectionStatuses[source.id]?.status === 'collecting'}
                  >
                    {collectionStatuses[source.id]?.status === 'collecting' ? 'Syncing...' : 'Sync Data'}
                  </button>
                )}
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(source.id, source.name)}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
