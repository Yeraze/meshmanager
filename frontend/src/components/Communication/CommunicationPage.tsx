import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMessageChannels } from '../../services/api'
import ChannelList from './ChannelList'
import MessageList from './MessageList'
import MessageDetailModal from './MessageDetailModal'

export default function CommunicationPage() {
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null)
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null)
  const [disabledSources, setDisabledSources] = useState<Set<string>>(new Set())

  const {
    data: channels,
    isLoading: channelsLoading,
    error: channelsError,
  } = useQuery({
    queryKey: ['message-channels'],
    queryFn: fetchMessageChannels,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const handleChannelSelect = (channelIndex: number) => {
    setSelectedChannel(channelIndex)
    setDisabledSources(new Set())
  }

  const handleSourceToggle = useCallback((sourceName: string) => {
    setDisabledSources((prev) => {
      const next = new Set(prev)
      if (next.has(sourceName)) {
        next.delete(sourceName)
      } else {
        next.add(sourceName)
      }
      return next
    })
  }, [])

  const handleMessageClick = (packetId: string) => {
    setSelectedMessageId(packetId)
  }

  const handleCloseModal = () => {
    setSelectedMessageId(null)
  }

  // Get the selected channel info
  const selectedChannelInfo = channels?.find((c) => c.channel_index === selectedChannel)

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        background: 'var(--color-surface)',
        borderRadius: '8px',
        border: '1px solid var(--color-border)',
        overflow: 'hidden',
      }}
    >
      {/* Left Sidebar - Channel List */}
      <div
        style={{
          width: '280px',
          flexShrink: 0,
          borderRight: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Channels</h3>
        </div>

        <ChannelList
          channels={channels || []}
          selectedChannel={selectedChannel}
          onChannelSelect={handleChannelSelect}
          isLoading={channelsLoading}
          error={channelsError}
        />
      </div>

      {/* Right Content - Message List */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {selectedChannel !== null ? (
          <>
            <div
              style={{
                padding: '1rem',
                borderBottom: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '1rem' }}>
                {selectedChannelInfo?.display_name || `Channel ${selectedChannel}`}
              </h3>
              <p
                style={{
                  margin: '0.25rem 0 0 0',
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                }}
              >
                {selectedChannelInfo?.message_count.toLocaleString()} messages
              </p>
              {/* Source filter buttons */}
              {selectedChannelInfo?.source_names && selectedChannelInfo.source_names.length > 0 && (
                <div
                  style={{
                    marginTop: '0.5rem',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  {selectedChannelInfo.source_names.map((sn, idx) => {
                    const isActive = !disabledSources.has(sn.source_name)
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSourceToggle(sn.source_name)}
                        style={{
                          fontSize: '0.7rem',
                          padding: '0.25rem 0.5rem',
                          background: isActive
                            ? 'var(--color-primary, #89b4fa)'
                            : 'var(--color-surface-elevated, rgba(255,255,255,0.05))',
                          borderRadius: '4px',
                          color: isActive
                            ? 'var(--color-background, #1e1e2e)'
                            : 'var(--color-text-muted)',
                          border: '1px solid',
                          borderColor: isActive
                            ? 'var(--color-primary, #89b4fa)'
                            : 'var(--color-border)',
                          cursor: 'pointer',
                          opacity: isActive ? 1 : 0.5,
                          transition: 'all 0.15s ease',
                          fontFamily: 'inherit',
                        }}
                        title={
                          isActive
                            ? `Click to hide messages from ${sn.source_name}`
                            : `Click to show messages from ${sn.source_name}`
                        }
                      >
                        <strong>{sn.source_name}:</strong> {sn.channel_name || '(unnamed)'}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
            <MessageList
              channelIndex={selectedChannel}
              onMessageClick={handleMessageClick}
              sourceNames={
                selectedChannelInfo?.source_names &&
                disabledSources.size > 0
                  ? selectedChannelInfo.source_names
                      .map((sn) => sn.source_name)
                      .filter((name) => !disabledSources.has(name))
                  : undefined
              }
            />
          </>
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-muted)',
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💬</div>
              <p>Select a channel to view messages</p>
            </div>
          </div>
        )}
      </div>

      {/* Message Detail Modal */}
      {selectedMessageId && (
        <MessageDetailModal packetId={selectedMessageId} onClose={handleCloseModal} />
      )}
    </div>
  )
}
