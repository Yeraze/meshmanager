import { useEffect, useRef, useCallback } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { fetchMessages, type MessageResponse } from '../../services/api'

interface MessageListProps {
  channelIndex: number
  onMessageClick: (packetId: string) => void
  sourceNames?: string[]
}

function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.toDateString() === today.toDateString()) {
    return 'Today'
  } else if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday'
  } else {
    return date.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })
  }
}

function getMessageTimestamp(msg: MessageResponse): string {
  return msg.rx_time || msg.received_at
}

function getNodeDisplayName(msg: MessageResponse): string {
  if (msg.from_short_name) return msg.from_short_name
  if (msg.from_long_name) return msg.from_long_name
  return `!${msg.from_node_num.toString(16).padStart(8, '0')}`
}

export default function MessageList({ channelIndex, onMessageClick, sourceNames }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const previousChannelRef = useRef<number | null>(null)

  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['channel-messages', channelIndex, sourceNames],
    queryFn: ({ pageParam }) =>
      fetchMessages(channelIndex, 50, pageParam as string | undefined, sourceNames),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    refetchInterval: 10000, // Refresh every 10 seconds for new messages
  })

  // Scroll to bottom when channel changes or initial load
  useEffect(() => {
    if (previousChannelRef.current !== channelIndex) {
      previousChannelRef.current = channelIndex
      // Wait for render then scroll to bottom
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
      }, 100)
    }
  }, [channelIndex, data])

  // Handle scroll for infinite loading older messages
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    const { scrollTop } = containerRef.current

    // Load more when scrolled near top
    if (scrollTop < 100 && hasNextPage && !isFetchingNextPage) {
      const prevScrollHeight = containerRef.current.scrollHeight
      fetchNextPage().then(() => {
        // Maintain scroll position after loading older messages
        requestAnimationFrame(() => {
          if (containerRef.current) {
            const newScrollHeight = containerRef.current.scrollHeight
            containerRef.current.scrollTop = newScrollHeight - prevScrollHeight
          }
        })
      })
    }
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  // Combine all pages of messages
  const allMessages = data?.pages.flatMap((page) => page.messages) ?? []

  // Group messages by date
  const messagesByDate: Map<string, MessageResponse[]> = new Map()
  allMessages.forEach((msg) => {
    const dateKey = new Date(getMessageTimestamp(msg)).toDateString()
    if (!messagesByDate.has(dateKey)) {
      messagesByDate.set(dateKey, [])
    }
    messagesByDate.get(dateKey)!.push(msg)
  })

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
        Loading messages...
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
        Error loading messages: {(error as Error).message}
      </div>
    )
  }

  if (allMessages.length === 0) {
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
        No messages in this channel
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      {/* Loading older messages indicator */}
      {isFetchingNextPage && (
        <div
          style={{
            textAlign: 'center',
            padding: '0.5rem',
            color: 'var(--color-text-muted)',
            fontSize: '0.8rem',
          }}
        >
          Loading older messages...
        </div>
      )}

      {/* Messages grouped by date */}
      {Array.from(messagesByDate.entries()).map(([dateKey, messages]) => (
        <div key={dateKey}>
          {/* Date separator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              margin: '0.5rem 0',
            }}
          >
            <div
              style={{
                flex: 1,
                height: '1px',
                background: 'var(--color-border)',
              }}
            />
            <span
              style={{
                fontSize: '0.7rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
              }}
            >
              {formatDate(getMessageTimestamp(messages[0]))}
            </span>
            <div
              style={{
                flex: 1,
                height: '1px',
                background: 'var(--color-border)',
              }}
            />
          </div>

          {/* Messages */}
          {messages.map((msg) => (
            <button
              key={msg.packet_id}
              onClick={() => onMessageClick(msg.packet_id)}
              style={{
                width: '100%',
                padding: '0.75rem',
                marginBottom: '0.25rem',
                background: 'var(--color-surface-elevated, rgba(255,255,255,0.03))',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background 0.15s ease, border-color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-surface-hover, rgba(255,255,255,0.08))'
                e.currentTarget.style.borderColor = 'var(--color-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--color-surface-elevated, rgba(255,255,255,0.03))'
                e.currentTarget.style.borderColor = 'var(--color-border)'
              }}
            >
              {/* Header: Sender name and time */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '0.25rem',
                }}
              >
                <span
                  style={{
                    fontWeight: 600,
                    color: 'var(--color-primary)',
                    fontSize: '0.85rem',
                  }}
                >
                  {getNodeDisplayName(msg)}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {/* Source count badge */}
                  {msg.source_count > 1 && (
                    <span
                      style={{
                        background: 'var(--color-success, #a6e3a1)',
                        color: 'var(--color-background)',
                        padding: '0.125rem 0.375rem',
                        borderRadius: '10px',
                        fontSize: '0.65rem',
                        fontWeight: 600,
                      }}
                      title={`Received by ${msg.source_count} sources`}
                    >
                      {msg.source_count} sources
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: '0.7rem',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    {formatTime(getMessageTimestamp(msg))}
                  </span>
                </div>
              </div>

              {/* Message text */}
              <div
                style={{
                  color: 'var(--color-text)',
                  fontSize: '0.9rem',
                  lineHeight: 1.4,
                  wordBreak: 'break-word',
                }}
              >
                {msg.emoji && <span style={{ marginRight: '0.25rem' }}>{msg.emoji}</span>}
                {msg.text || <em style={{ color: 'var(--color-text-muted)' }}>(empty message)</em>}
              </div>
            </button>
          ))}
        </div>
      ))}

      {/* Scroll anchor for auto-scroll to bottom */}
      <div ref={messagesEndRef} />
    </div>
  )
}
