import type { ChannelSummary } from '../../services/api'

interface ChannelListProps {
  channels: ChannelSummary[]
  selectedChannel: number | null
  onChannelSelect: (channelIndex: number) => void
  isLoading: boolean
  error: Error | null
}

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'No messages'

  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export default function ChannelList({
  channels,
  selectedChannel,
  onChannelSelect,
  isLoading,
  error,
}: ChannelListProps) {
  if (isLoading) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-text-muted)',
        }}
      >
        Loading channels...
      </div>
    )
  }

  if (error) {
    return (
      <div
        style={{
          flex: 1,
          padding: '1rem',
          color: 'var(--color-error)',
        }}
      >
        Error loading channels: {error.message}
      </div>
    )
  }

  if (channels.length === 0) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-text-muted)',
          padding: '1rem',
          textAlign: 'center',
        }}
      >
        No channels with messages found
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {channels.map((channel) => (
        <button
          key={channel.channel_index}
          onClick={() => onChannelSelect(channel.channel_index)}
          style={{
            width: '100%',
            padding: '0.75rem 1rem',
            border: 'none',
            background:
              selectedChannel === channel.channel_index
                ? 'var(--color-primary-transparent, rgba(137, 180, 250, 0.15))'
                : 'transparent',
            borderLeft:
              selectedChannel === channel.channel_index
                ? '3px solid var(--color-primary)'
                : '3px solid transparent',
            cursor: 'pointer',
            textAlign: 'left',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.25rem',
            transition: 'background 0.15s ease',
          }}
          onMouseEnter={(e) => {
            if (selectedChannel !== channel.channel_index) {
              e.currentTarget.style.background = 'var(--color-surface-hover, rgba(255,255,255,0.05))'
            }
          }}
          onMouseLeave={(e) => {
            if (selectedChannel !== channel.channel_index) {
              e.currentTarget.style.background = 'transparent'
            }
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span
              style={{
                fontWeight: selectedChannel === channel.channel_index ? 600 : 400,
                color: 'var(--color-text)',
                fontSize: '0.9rem',
              }}
            >
              {channel.display_name}
            </span>
            <span
              style={{
                background: 'var(--color-surface-elevated, rgba(255,255,255,0.1))',
                padding: '0.125rem 0.5rem',
                borderRadius: '10px',
                fontSize: '0.7rem',
                color: 'var(--color-text-muted)',
              }}
            >
              {channel.message_count.toLocaleString()}
            </span>
          </div>
          <span
            style={{
              fontSize: '0.7rem',
              color: 'var(--color-text-muted)',
            }}
          >
            {formatRelativeTime(channel.last_message_at)}
          </span>
        </button>
      ))}
    </div>
  )
}
