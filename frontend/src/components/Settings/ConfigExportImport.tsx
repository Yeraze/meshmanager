import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { exportConfig, importConfig, type ImportResult } from '../../services/api'
import { useDataContext } from '../../contexts/DataContext'

export default function ConfigExportImport() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [mergeSources, setMergeSources] = useState(false)
  const queryClient = useQueryClient()
  const { setActiveHours, setOnlineHours } = useDataContext()

  const exportMutation = useMutation({
    mutationFn: exportConfig,
    onSuccess: (blob) => {
      // Create download link
      const url = URL.createObjectURL(blob)
      const date = new Date().toISOString().split('T')[0]
      const a = document.createElement('a')
      a.href = url
      a.download = `meshmanager-config-${date}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
    onError: (error: Error) => {
      console.error('Export failed:', error)
      alert('Failed to export configuration: ' + error.message)
    },
  })

  const importMutation = useMutation({
    mutationFn: ({ config, merge }: { config: unknown; merge: boolean }) =>
      importConfig(config, { merge_sources: merge }),
    onSuccess: (result) => {
      setImportResult(result)
      setImportError(null)

      // Apply display settings if present
      if (result.display_settings) {
        setActiveHours(result.display_settings.active_hours)
        setOnlineHours(result.display_settings.online_hours)
      }

      // Refresh sources list
      queryClient.invalidateQueries({ queryKey: ['admin-sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
    onError: (error: Error) => {
      setImportError(error.message)
      setImportResult(null)
    },
  })

  const handleExport = () => {
    exportMutation.mutate()
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Reset state
    setImportResult(null)
    setImportError(null)

    try {
      const text = await file.text()
      const config = JSON.parse(text)

      // Basic validation
      if (!config.version) {
        throw new Error('Invalid configuration file: missing version')
      }

      importMutation.mutate({ config, merge: mergeSources })
    } catch (error) {
      if (error instanceof SyntaxError) {
        setImportError('Invalid JSON file')
      } else if (error instanceof Error) {
        setImportError(error.message)
      } else {
        setImportError('Failed to read file')
      }
    }

    // Reset file input
    event.target.value = ''
  }

  const clearResults = () => {
    setImportResult(null)
    setImportError(null)
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Configuration Backup</h2>
      </div>

      <div className="settings-card">
        <h3>Export Configuration</h3>
        <p className="settings-description">
          Download your sources, display settings, and analysis configurations as a JSON file.
          Sensitive data (API tokens, passwords) are excluded for security.
        </p>

        <button
          className="btn btn-primary"
          onClick={handleExport}
          disabled={exportMutation.isPending}
        >
          {exportMutation.isPending ? 'Exporting...' : 'Export Configuration'}
        </button>
      </div>

      <div className="settings-card">
        <h3>Import Configuration</h3>
        <p className="settings-description">
          Restore configuration from a previously exported JSON file.
          Note: You will need to re-enter API tokens and passwords after import.
        </p>

        <div className="form-group">
          <label className="form-label">
            <input
              type="checkbox"
              checked={mergeSources}
              onChange={(e) => setMergeSources(e.target.checked)}
            />
            {' '}Merge with existing sources (instead of replacing)
          </label>
        </div>

        <input
          type="file"
          ref={fileInputRef}
          accept=".json"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        <button
          className="btn btn-secondary"
          onClick={handleImportClick}
          disabled={importMutation.isPending}
        >
          {importMutation.isPending ? 'Importing...' : 'Import Configuration'}
        </button>

        {importError && (
          <div className="settings-error" style={{ marginTop: '1rem' }}>
            <strong>Error:</strong> {importError}
            <button className="btn btn-sm" onClick={clearResults} style={{ marginLeft: '1rem' }}>
              Dismiss
            </button>
          </div>
        )}

        {importResult && (
          <div className="settings-success" style={{ marginTop: '1rem' }}>
            <strong>Import Complete</strong>
            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
              <li>Sources imported: {importResult.sources_imported}</li>
              {importResult.sources_skipped > 0 && (
                <li>Sources skipped: {importResult.sources_skipped}</li>
              )}
              {importResult.display_settings_imported && (
                <li>Display settings imported</li>
              )}
              {importResult.analysis_configs_imported.length > 0 && (
                <li>Analysis configs: {importResult.analysis_configs_imported.join(', ')}</li>
              )}
            </ul>
            {importResult.warnings.length > 0 && (
              <div className="settings-warnings">
                <strong>Warnings:</strong>
                <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                  {importResult.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
            <button className="btn btn-sm" onClick={clearResults}>
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
