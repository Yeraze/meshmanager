import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../test/test-utils'
import CommunicationPage from './CommunicationPage'

// Mock the API module
vi.mock('../../services/api', () => ({
  fetchMessageChannels: vi.fn(),
  fetchMessages: vi.fn(),
  fetchMessageSources: vi.fn(),
}))

import { fetchMessageChannels, fetchMessages } from '../../services/api'

const mockedFetchChannels = vi.mocked(fetchMessageChannels)
const mockedFetchMessages = vi.mocked(fetchMessages)

const mockChannels = [
  {
    channel_key: 'gauntlet',
    display_name: 'gauntlet',
    message_count: 42,
    last_message_at: '2024-01-15T12:00:00Z',
    source_names: [
      { source_name: 'mesh', channel_name: 'gauntlet' },
      { source_name: 'wynwood', channel_name: 'gauntlet' },
    ],
  },
  {
    channel_key: '0',
    display_name: 'Channel 0',
    message_count: 100,
    last_message_at: '2024-01-15T13:00:00Z',
    source_names: [
      { source_name: 'mesh', channel_name: null },
    ],
  },
]

const mockMessages = {
  messages: [
    {
      packet_id: 'pkt-1',
      meshtastic_id: 1000,
      from_node_num: 12345678,
      to_node_num: null,
      channel_key: 'gauntlet',
      text: 'Hello world',
      emoji: null,
      reply_id: null,
      hop_limit: 3,
      hop_start: 3,
      rx_time: '2024-01-15T12:00:00Z',
      received_at: '2024-01-15T12:00:00Z',
      from_short_name: 'TST1',
      from_long_name: 'Test Node',
      source_count: 2,
    },
  ],
  has_more: false,
  next_cursor: null,
}

const mockMessagesWithReplyAndReactions = {
  messages: [
    {
      packet_id: 'pkt-original',
      meshtastic_id: 2000,
      from_node_num: 11111111,
      to_node_num: null,
      channel_key: 'gauntlet',
      text: 'Original message',
      emoji: null,
      reply_id: null,
      hop_limit: 3,
      hop_start: 3,
      rx_time: '2024-01-15T12:00:00Z',
      received_at: '2024-01-15T12:00:00Z',
      from_short_name: 'ORIG',
      from_long_name: 'Original Sender',
      source_count: 1,
    },
    {
      packet_id: 'pkt-reply',
      meshtastic_id: 2001,
      from_node_num: 22222222,
      to_node_num: null,
      channel_key: 'gauntlet',
      text: 'This is a reply',
      emoji: null,
      reply_id: 2000,
      hop_limit: 3,
      hop_start: 3,
      rx_time: '2024-01-15T12:01:00Z',
      received_at: '2024-01-15T12:01:00Z',
      from_short_name: 'RPLY',
      from_long_name: 'Reply Sender',
      source_count: 1,
    },
    {
      packet_id: 'pkt-reaction',
      meshtastic_id: 2002,
      from_node_num: 33333333,
      to_node_num: null,
      channel_key: 'gauntlet',
      text: null,
      emoji: '👍',
      reply_id: 2000,
      hop_limit: 3,
      hop_start: 3,
      rx_time: '2024-01-15T12:02:00Z',
      received_at: '2024-01-15T12:02:00Z',
      from_short_name: 'REAC',
      from_long_name: 'Reactor',
      source_count: 1,
    },
  ],
  has_more: false,
  next_cursor: null,
}

describe('CommunicationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchChannels.mockResolvedValue(mockChannels)
    mockedFetchMessages.mockResolvedValue(mockMessages)
  })

  it('renders channel list with channel_key-based names', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
      expect(screen.getByText('Channel 0')).toBeInTheDocument()
    })
  })

  it('shows placeholder when no channel is selected', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('Select a channel to view messages')).toBeInTheDocument()
    })
  })

  it('selects a channel and shows messages', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    await waitFor(() => {
      expect(mockedFetchMessages).toHaveBeenCalledWith(
        'gauntlet',
        50,
        undefined,
        undefined,
      )
    })
  })

  it('shows source filter buttons when channel is selected', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    await waitFor(() => {
      expect(screen.getByTitle('Click to hide messages from mesh')).toBeInTheDocument()
      expect(screen.getByTitle('Click to hide messages from wynwood')).toBeInTheDocument()
    })
  })

  it('toggles source filter on button click', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    await waitFor(() => {
      expect(screen.getByTitle('Click to hide messages from mesh')).toBeInTheDocument()
    })

    // Click to disable "mesh" source
    fireEvent.click(screen.getByTitle('Click to hide messages from mesh'))

    // After disabling mesh, should re-fetch with only wynwood
    await waitFor(() => {
      expect(mockedFetchMessages).toHaveBeenCalledWith(
        'gauntlet',
        50,
        undefined,
        ['wynwood'],
      )
    })
  })

  it('re-enables source on second click', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    await waitFor(() => {
      expect(screen.getByTitle('Click to hide messages from mesh')).toBeInTheDocument()
    })

    // Click to disable
    fireEvent.click(screen.getByTitle('Click to hide messages from mesh'))

    await waitFor(() => {
      expect(screen.getByTitle('Click to show messages from mesh')).toBeInTheDocument()
    })

    // Click again to re-enable
    fireEvent.click(screen.getByTitle('Click to show messages from mesh'))

    // Should go back to unfiltered (undefined sourceNames)
    await waitFor(() => {
      // The most recent call should have undefined sourceNames (no filtering)
      const lastCall = mockedFetchMessages.mock.calls[mockedFetchMessages.mock.calls.length - 1]
      expect(lastCall[3]).toBeUndefined()
    })
  })

  it('resets source filters when switching channels', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    // Select gauntlet and disable a source
    fireEvent.click(screen.getByText('gauntlet'))
    await waitFor(() => {
      expect(screen.getByTitle('Click to hide messages from mesh')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByTitle('Click to hide messages from mesh'))

    // Switch to Channel 0
    fireEvent.click(screen.getByText('Channel 0'))

    // Should fetch without source filtering (filters reset)
    await waitFor(() => {
      expect(mockedFetchMessages).toHaveBeenCalledWith(
        '0',
        50,
        undefined,
        undefined,
      )
    })
  })

  it('passes undefined when all sources disabled (not empty array)', async () => {
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    await waitFor(() => {
      expect(screen.getByTitle('Click to hide messages from mesh')).toBeInTheDocument()
    })

    // Disable both sources
    fireEvent.click(screen.getByTitle('Click to hide messages from mesh'))
    fireEvent.click(screen.getByTitle('Click to hide messages from wynwood'))

    // Should pass undefined, NOT an empty array
    await waitFor(() => {
      const lastCall = mockedFetchMessages.mock.calls[mockedFetchMessages.mock.calls.length - 1]
      expect(lastCall[3]).toBeUndefined()
    })
  })

  it('filters reaction messages from the main message list', async () => {
    mockedFetchMessages.mockResolvedValue(mockMessagesWithReplyAndReactions)
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    // The original message and reply should be visible
    // "Original message" appears in both message body and reply preview, so use getAllByText
    await waitFor(() => {
      expect(screen.getAllByText('Original message').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('This is a reply')).toBeInTheDocument()
    })

    // The reaction sender name should NOT appear as a standalone message sender
    // (REAC only exists as a reaction badge sender, not as a message header)
    const reacElements = screen.queryAllByText('REAC')
    // If REAC appears, it should only be inside reaction badges, not as a message sender header
    for (const el of reacElements) {
      const badge = el.closest('[data-testid="reaction-badges"]')
      expect(badge).not.toBeNull()
    }
  })

  it('shows reply indicator for messages with reply_id', async () => {
    mockedFetchMessages.mockResolvedValue(mockMessagesWithReplyAndReactions)
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    // The reply message should show a reply indicator with the original sender's name
    await waitFor(() => {
      const replyIndicators = screen.getAllByTestId('reply-indicator')
      expect(replyIndicators.length).toBeGreaterThanOrEqual(1)
      // The reply indicator should reference the original sender
      expect(replyIndicators[0]).toHaveTextContent('ORIG')
    })
  })

  it('renders reaction badges below target messages', async () => {
    mockedFetchMessages.mockResolvedValue(mockMessagesWithReplyAndReactions)
    render(<CommunicationPage />)

    await waitFor(() => {
      expect(screen.getByText('gauntlet')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('gauntlet'))

    // The original message should have a reaction badge
    await waitFor(() => {
      const reactionBadges = screen.getAllByTestId('reaction-badges')
      expect(reactionBadges.length).toBeGreaterThanOrEqual(1)
      // Should contain the emoji and sender name
      expect(reactionBadges[0]).toHaveTextContent('👍')
      expect(reactionBadges[0]).toHaveTextContent('REAC')
    })
  })
})
