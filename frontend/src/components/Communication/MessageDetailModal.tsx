import { useQuery } from '@tanstack/react-query'
import { fetchMessageSources, fetchNodesByNodeNum, type MessageSourceDetail } from '../../services/api'
import { useDataContext } from '../../contexts/DataContext'
import styles from './MessageDetailModal.module.css'

interface MessageDetailModalProps {
  packetId: string
  onClose: () => void
  senderName?: string
  messageText?: string | null
  timestamp?: string
}

function formatDateTime(dateString: string | null): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString()
}

function getSourceTimestamp(source: MessageSourceDetail): string | null {
  return source.rx_time || source.received_at
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

function formatRelayText(detail: MessageSourceDetail): string {
  if (detail.relay_node_name) return detail.relay_node_name
  if (detail.relay_node) return `0x${(detail.relay_node & 0xFF).toString(16).padStart(2, '0').toUpperCase()}`
  return '-'
}

function formatGatewayText(detail: MessageSourceDetail): string {
  if (detail.gateway_node_name) return detail.gateway_node_name
  if (detail.gateway_node_num) return `!${detail.gateway_node_num.toString(16).padStart(8, '0')}`
  return '-'
}

export default function MessageDetailModal({ packetId, onClose, senderName, messageText, timestamp }: MessageDetailModalProps) {
  const { setSelectedNode, navigateToPage } = useDataContext()
  const { data: sources, isLoading, error } = useQuery({
    queryKey: ['message-sources', packetId],
    queryFn: () => fetchMessageSources(packetId),
  })

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const handleNodeClick = async (nodeNum: number) => {
    try {
      const nodes = await fetchNodesByNodeNum(nodeNum)
      if (nodes.length > 0) {
        setSelectedNode(nodes[0])
        navigateToPage('nodes')
        onClose()
      }
    } catch {
      // Node not found or API error — ignore
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

        {/* Message summary */}
        {(senderName || messageText !== undefined || timestamp) && (
          <div className={styles.messageSummary}>
            <div className={styles.messageMeta}>
              {senderName && <span className={styles.messageSender}>{senderName}</span>}
              {timestamp && <span className={styles.messageTimestamp}>{formatDateTime(timestamp)}</span>}
            </div>
            <div className={styles.messageText}>
              {messageText || <em>(empty message)</em>}
            </div>
          </div>
        )}

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
                    <th>Gateway</th>
                    <th>SNR</th>
                    <th>RSSI</th>
                    <th>Hops</th>
                    <th>Relay</th>
                    <th>Received At</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source, index) => (
                    <tr key={`${source.source_id}-${index}`}>
                      <td className={styles.sourceName}>{source.source_name}</td>
                      <td>
                        {source.gateway_node_num ? (
                          <button
                            className={styles.nodeLink}
                            onClick={() => handleNodeClick(source.gateway_node_num!)}
                            title="View node details"
                          >
                            {formatGatewayText(source)}
                          </button>
                        ) : '-'}
                      </td>
                      <td className={styles.numeric}>{formatSnr(source.rx_snr)}</td>
                      <td className={styles.numeric}>{formatRssi(source.rx_rssi)}</td>
                      <td className={styles.numeric}>{formatHops(source)}</td>
                      <td>{formatRelayText(source)}</td>
                      <td className={styles.timestamp}>{formatDateTime(getSourceTimestamp(source))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Signal quality explanation */}
              <div className={styles.legend}>
                <p><strong>SNR</strong> (Signal-to-Noise Ratio): Higher is better. Good: &gt;0 dB, Excellent: &gt;10 dB</p>
                <p><strong>RSSI</strong> (Signal Strength): Higher (closer to 0) is better. Good: &gt;-100 dBm</p>
                <p><strong>Hops</strong>: Number of nodes the message passed through to reach this source</p>
                <p><strong>Relay</strong>: The node that relayed/forwarded this packet</p>
                <p><strong>Gateway</strong>: The node that uploaded this packet to MQTT</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
