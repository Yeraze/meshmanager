import { useEffect, useRef, useCallback, useMemo } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { fetchMessages, type MessageResponse } from '../../services/api'

interface MessageListProps {
  channelKey: string
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

/** Returns true if a string consists entirely of emoji characters */
function isEmojiOnly(str: string): boolean {
  // Remove zero-width joiners and variation selectors, then check remaining chars
  const stripped = str.replace(/\u200d|\ufe0f|\u20e3/g, '')
  if (stripped.length === 0) return false
  // Use spread to iterate codepoints (handles surrogate pairs correctly)
  return [...stripped].every(
    (ch) => /\p{Emoji_Presentation}/u.test(ch) || /\p{Extended_Pictographic}/u.test(ch),
  )
}

/** Returns true if the message is a tapback/reaction (emoji + reply_id, no meaningful text) */
function isReaction(msg: MessageResponse): boolean {
  if (msg.reply_id == null) return false
  // Has emoji and no text -> reaction
  if (msg.emoji != null && (msg.text == null || msg.text.trim() === '')) return true
  // Text is pure emoji and has reply_id -> reaction
  if (msg.text != null && isEmojiOnly(msg.text.trim()) && msg.emoji == null) return true
  return false
}

export default function MessageList({ channelKey, onMessageClick, sourceNames }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const previousChannelRef = useRef<string | null>(null)

  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['channel-messages', channelKey, sourceNames],
    queryFn: ({ pageParam }) =>
      fetchMessages(channelKey, 50, pageParam as string | undefined, sourceNames),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    refetchInterval: 10000, // Refresh every 10 seconds for new messages
  })

  // Scroll to bottom when channel changes or initial load
  useEffect(() => {
    if (previousChannelRef.current !== channelKey) {
      previousChannelRef.current = channelKey
      // Wait for render then scroll to bottom
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
      }, 100)
    }
  }, [channelKey, data])

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

  // Build lookup maps and filter reactions
  const { meshtasticIdMap, reactionsMap, displayMessages } = useMemo(() => {
    // Map meshtastic_id -> message for reply resolution
    const idMap = new Map<number, MessageResponse>()
    for (const msg of allMessages) {
      if (msg.meshtastic_id != null) {
        idMap.set(msg.meshtastic_id, msg)
      }
    }

    // Group reactions by reply_id
    const reactions = new Map<number, Array<{ emoji: string; senderName: string }>>()
    const display: MessageResponse[] = []

    for (const msg of allMessages) {
      if (isReaction(msg)) {
        const replyId = msg.reply_id!
        if (!reactions.has(replyId)) {
          reactions.set(replyId, [])
        }
        const emoji = msg.emoji || msg.text?.trim() || ''
        reactions.get(replyId)!.push({
          emoji,
          senderName: getNodeDisplayName(msg),
        })
      } else {
        display.push(msg)
      }
    }

    return { meshtasticIdMap: idMap, reactionsMap: reactions, displayMessages: display }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  // Group messages by date (using filtered display messages)
  const messagesByDate: Map<string, MessageResponse[]> = new Map()
  displayMessages.forEach((msg) => {
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

  if (displayMessages.length === 0) {
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
          {messages.map((msg) => {
            const repliedTo = msg.reply_id != null ? meshtasticIdMap.get(msg.reply_id) : undefined
            const msgReactions = msg.meshtastic_id != null ? reactionsMap.get(msg.meshtastic_id) : undefined

            return (
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
                {/* Reply indicator */}
                {msg.reply_id != null && (
                  <div
                    data-testid="reply-indicator"
                    style={{
                      borderLeft: '3px solid var(--color-primary)',
                      paddingLeft: '0.5rem',
                      marginBottom: '0.375rem',
                      fontSize: '0.75rem',
                      color: 'var(--color-text-muted)',
                      lineHeight: 1.3,
                    }}
                  >
                    {repliedTo ? (
                      <>
                        <span style={{ marginRight: '0.25rem' }}>↳</span>
                        <span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>
                          {getNodeDisplayName(repliedTo)}
                        </span>
                        {repliedTo.text && (
                          <span style={{ marginLeft: '0.25rem' }}>
                            {repliedTo.text.length > 50
                              ? repliedTo.text.slice(0, 50) + '...'
                              : repliedTo.text}
                          </span>
                        )}
                      </>
                    ) : (
                      <span>↳ Reply</span>
                    )}
                  </div>
                )}

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

                {/* Reaction badges */}
                {msgReactions && msgReactions.length > 0 && (
                  <div
                    data-testid="reaction-badges"
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '0.25rem',
                      marginTop: '0.375rem',
                    }}
                  >
                    {msgReactions.map((reaction, idx) => (
                      <span
                        key={idx}
                        title={reaction.senderName}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          background: 'var(--color-surface-hover, rgba(255,255,255,0.08))',
                          border: '1px solid var(--color-border)',
                          borderRadius: '12px',
                          padding: '0.125rem 0.5rem',
                          fontSize: '0.75rem',
                        }}
                      >
                        <span>{reaction.emoji}</span>
                        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.65rem' }}>
                          {reaction.senderName}
                        </span>
                      </span>
                    ))}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      ))}

      {/* Scroll anchor for auto-scroll to bottom */}
      <div ref={messagesEndRef} />
    </div>
  )
}
