import { useQuery } from '@tanstack/react-query'
import { fetchEdgeDetails } from '../../services/api'
import styles from './EdgeDetailModal.module.css'

interface EdgeDetailModalProps {
  nodeA: number
  nodeB: number
  hours?: number
  onClose: () => void
}

function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString()
}

function formatSnr(snr: number | null): string {
  if (snr === null) return '-'
  return `${snr.toFixed(1)} dB`
}

export default function EdgeDetailModal({ nodeA, nodeB, hours = 24, onClose }: EdgeDetailModalProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['edge-details', nodeA, nodeB, hours],
    queryFn: () => fetchEdgeDetails(nodeA, nodeB, hours),
  })

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div className={styles.overlay} onClick={handleOverlayClick}>
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <h3 className={styles.title}>Connection Details</h3>
          <button className={styles.closeButton} onClick={onClose} title="Close">
            &times;
          </button>
        </div>

        {/* Connection summary */}
        {data && (
          <div className={styles.summary}>
            <div className={styles.connectionLabel}>
              {data.node_a.name} ↔ {data.node_b.name}
            </div>
            <div className={styles.statsRow}>
              <span>Traversals: <strong>{data.usage_count}</strong></span>
              {data.snr_stats && (
                <>
                  <span>SNR Min: <strong>{data.snr_stats.min_db} dB</strong></span>
                  <span>SNR Avg: <strong>{data.snr_stats.avg_db} dB</strong></span>
                  <span>SNR Max: <strong>{data.snr_stats.max_db} dB</strong></span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        <div className={styles.content}>
          {isLoading && (
            <div className={styles.loading}>Loading edge details...</div>
          )}

          {error && (
            <div className={styles.error}>
              Error loading details: {(error as Error).message}
            </div>
          )}

          {data && data.recent_traversals.length === 0 && (
            <div className={styles.empty}>No traversal data found for this connection.</div>
          )}

          {data && data.recent_traversals.length > 0 && (
            <>
              <p className={styles.subtitle}>
                Recent traversals (showing {data.recent_traversals.length} of {data.usage_count}):
              </p>

              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Traceroute</th>
                    <th>Direction</th>
                    <th>SNR</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_traversals.map((t, index) => (
                    <tr key={index}>
                      <td className={styles.timestamp}>{formatDateTime(t.received_at)}</td>
                      <td>{t.from_node_name} → {t.to_node_name}</td>
                      <td>{t.direction}</td>
                      <td className={styles.numeric}>{formatSnr(t.snr_db)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className={styles.legend}>
                <p><strong>Traversals</strong>: Number of traceroutes that used this connection</p>
                <p><strong>SNR</strong> (Signal-to-Noise Ratio): Higher is better. Good: &gt;0 dB, Excellent: &gt;10 dB</p>
                <p><strong>Direction</strong>: &quot;towards&quot; = forward route, &quot;back&quot; = return route</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
