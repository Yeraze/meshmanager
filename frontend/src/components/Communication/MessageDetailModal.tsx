import { useQuery } from '@tanstack/react-query'
import { fetchMessageSources, type MessageSourceDetail } from '../../services/api'
import styles from './MessageDetailModal.module.css'

interface MessageDetailModalProps {
  packetId: string
  onClose: () => void
}

function formatDateTime(dateString: string | null): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString()
}

function formatSnr(snr: number | null): string {
  if (snr === null) return '-'
  return `${snr.toFixed(1)} dB`
}

function formatRssi(rssi: number | null): string {
  if (rssi === null) return '-'
  return `${rssi} dBm`
}

function formatHops(detail: MessageSourceDetail): string {
  if (detail.hop_count !== null) {
    return `${detail.hop_count} hops`
  }
  if (detail.hop_start !== null && detail.hop_limit !== null) {
    return `${detail.hop_start - detail.hop_limit} hops (${detail.hop_start} -> ${detail.hop_limit})`
  }
  return '-'
}

export default function MessageDetailModal({ packetId, onClose }: MessageDetailModalProps) {
  const { data: sources, isLoading, error } = useQuery({
    queryKey: ['message-sources', packetId],
    queryFn: () => fetchMessageSources(packetId),
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
          <h3 className={styles.title}>Message Reception Details</h3>
          <button className={styles.closeButton} onClick={onClose} title="Close">
            &times;
          </button>
        </div>

        {/* Content */}
        <div className={styles.content}>
          {isLoading && (
            <div className={styles.loading}>Loading reception details...</div>
          )}

          {error && (
            <div className={styles.error}>
              Error loading details: {(error as Error).message}
            </div>
          )}

          {sources && sources.length === 0 && (
            <div className={styles.empty}>No reception data found for this message.</div>
          )}

          {sources && sources.length > 0 && (
            <>
              <p className={styles.subtitle}>
                This message was received by {sources.length} source{sources.length > 1 ? 's' : ''}:
              </p>

              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>SNR</th>
                    <th>RSSI</th>
                    <th>Hops</th>
                    <th>Received At</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source, index) => (
                    <tr key={`${source.source_id}-${index}`}>
                      <td className={styles.sourceName}>{source.source_name}</td>
                      <td className={styles.numeric}>{formatSnr(source.rx_snr)}</td>
                      <td className={styles.numeric}>{formatRssi(source.rx_rssi)}</td>
                      <td className={styles.numeric}>{formatHops(source)}</td>
                      <td className={styles.timestamp}>{formatDateTime(source.received_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Signal quality explanation */}
              <div className={styles.legend}>
                <p><strong>SNR</strong> (Signal-to-Noise Ratio): Higher is better. Good: &gt;0 dB, Excellent: &gt;10 dB</p>
                <p><strong>RSSI</strong> (Signal Strength): Higher (closer to 0) is better. Good: &gt;-100 dBm</p>
                <p><strong>Hops</strong>: Number of nodes the message passed through to reach this source</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
