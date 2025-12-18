// Edit source feature added
import { useState } from 'react'
import { useAdminSources, useDeleteSource, useTestSource } from '../../hooks/useAdminSources'
import { AddSourceForm } from './AddSourceForm'
import { EditSourceForm } from './EditSourceForm'
import type { Source } from '../../types/api'
import styles from './AdminPanel.module.css'

interface AdminPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const { data: sources = [], isLoading } = useAdminSources()
  const deleteMutation = useDeleteSource()
  const testMutation = useTestSource()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})

  if (!isOpen) return null

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

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Admin Panel</h2>
          <button className={styles.closeButton} onClick={onClose}>
            &times;
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3>Sources</h3>
              <button
                className="btn btn-primary"
                onClick={() => setShowAddForm(!showAddForm)}
              >
                {showAddForm ? 'Cancel' : 'Add Source'}
              </button>
            </div>

            {showAddForm && (
              <AddSourceForm onSuccess={() => setShowAddForm(false)} />
            )}

            {editingSource && (
              <EditSourceForm
                source={editingSource}
                onSuccess={() => setEditingSource(null)}
                onCancel={() => setEditingSource(null)}
              />
            )}

            {isLoading ? (
              <div className={styles.loading}>Loading sources...</div>
            ) : sources.length === 0 ? (
              <div className={styles.empty}>
                No sources configured. Add a MeshMonitor or MQTT source to get started.
              </div>
            ) : (
              <div className={styles.sourceList}>
                {sources.map((source) => (
                  <div key={source.id} className={styles.sourceItem}>
                    <div className={styles.sourceInfo}>
                      <div className={styles.sourceName}>
                        <span className={`${styles.statusDot} ${source.healthy ? styles.healthy : styles.unhealthy}`} />
                        {source.name}
                        <span className={styles.sourceType}>{source.type}</span>
                      </div>
                      <div className={styles.sourceStatus}>
                        {source.enabled ? 'Enabled' : 'Disabled'}
                        {testResults[source.id] && (
                          <span className={testResults[source.id].success ? styles.testSuccess : styles.testFail}>
                            {testResults[source.id].message}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className={styles.sourceActions}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleTest(source.id)}
                        disabled={testMutation.isPending}
                      >
                        Test
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => {
                          setShowAddForm(false)
                          setEditingSource(source)
                        }}
                      >
                        Edit
                      </button>
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
        </div>
      </div>
    </div>
  )
}
