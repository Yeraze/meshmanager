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
})
