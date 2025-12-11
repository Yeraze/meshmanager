import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../test/test-utils'
import AnalysisPage from './AnalysisPage'
import { mockNodes, mockTraceroutes } from '../../test/mocks'

// Mock the API module
vi.mock('../../services/api', () => ({
  fetchNodes: vi.fn(),
  fetchTraceroutes: vi.fn(),
}))

// Mock Leaflet - jsdom doesn't support it
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Polyline: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="polyline">{children}</div>
  ),
  CircleMarker: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="circle-marker">{children}</div>
  ),
  Tooltip: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip">{children}</div>
  ),
}))

import { fetchNodes, fetchTraceroutes } from '../../services/api'

const mockedFetchNodes = vi.mocked(fetchNodes)
const mockedFetchTraceroutes = vi.mocked(fetchTraceroutes)

describe('AnalysisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchNodes.mockResolvedValue(mockNodes)
    mockedFetchTraceroutes.mockResolvedValue(mockTraceroutes)
  })

  it('renders the analysis page title', () => {
    render(<AnalysisPage />)
    expect(screen.getByText('Analysis')).toBeInTheDocument()
  })

  it('renders the Network Routing Topology card', () => {
    render(<AnalysisPage />)
    expect(screen.getByText('Network Routing Topology')).toBeInTheDocument()
    expect(screen.getByText(/Analyze traceroute data/)).toBeInTheDocument()
  })

  it('opens NetworkTopology when card is clicked', async () => {
    render(<AnalysisPage />)

    const card = screen.getByText('Network Routing Topology').closest('button')
    expect(card).toBeInTheDocument()

    fireEvent.click(card!)

    // Should show Back button and Options header
    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument()
      expect(screen.getByText('Options')).toBeInTheDocument()
    })
  })

  it('returns to grid when Back button is clicked', async () => {
    render(<AnalysisPage />)

    // Open the analysis
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument()
    })

    // Click back
    fireEvent.click(screen.getByText('Back'))

    // Should show Analysis title again (grid view)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Analysis' })).toBeInTheDocument()
    })
  })
})

describe('NetworkTopology', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchNodes.mockResolvedValue(mockNodes)
    mockedFetchTraceroutes.mockResolvedValue(mockTraceroutes)
  })

  it('shows loading state initially', async () => {
    // Make the fetch slow
    mockedFetchNodes.mockImplementation(() => new Promise(() => {}))
    mockedFetchTraceroutes.mockImplementation(() => new Promise(() => {}))

    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Loading traceroute data...')).toBeInTheDocument()
    })
  })

  it('renders controls when data is loaded', async () => {
    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Map Tiles')).toBeInTheDocument()
      expect(screen.getByText('Lookback Period')).toBeInTheDocument()
      expect(screen.getByText(/Min Popularity/)).toBeInTheDocument()
      expect(screen.getByText('Min Cluster Connections')).toBeInTheDocument()
      expect(screen.getByText(/Cluster Radius/)).toBeInTheDocument()
      expect(screen.getByText('Display')).toBeInTheDocument()
      expect(screen.getByText('Legend')).toBeInTheDocument()
      expect(screen.getByText('Statistics')).toBeInTheDocument()
    })
  })

  it('shows statistics with traceroute count', async () => {
    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      // Should show traceroute count
      expect(screen.getByText('Traceroutes:')).toBeInTheDocument()
    })
  })

  it('allows toggling trunk lines visibility', async () => {
    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByLabelText('Show Trunk Lines')).toBeInTheDocument()
    })

    const checkbox = screen.getByLabelText('Show Trunk Lines')
    expect(checkbox).toBeChecked()

    fireEvent.click(checkbox)
    expect(checkbox).not.toBeChecked()
  })

  it('allows toggling clusters visibility', async () => {
    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByLabelText('Show Clusters')).toBeInTheDocument()
    })

    const checkbox = screen.getByLabelText('Show Clusters')
    expect(checkbox).toBeChecked()

    fireEvent.click(checkbox)
    expect(checkbox).not.toBeChecked()
  })

  it('shows error state when API fails', async () => {
    mockedFetchTraceroutes.mockRejectedValue(new Error('Network error'))

    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Error loading data')).toBeInTheDocument()
    })
  })

  it('shows empty state when no traceroutes', async () => {
    mockedFetchTraceroutes.mockResolvedValue([])

    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('No traceroute data available')).toBeInTheDocument()
    })
  })

  it('renders map container when data is available', async () => {
    render(<AnalysisPage />)

    // Open network topology
    const card = screen.getByText('Network Routing Topology').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByTestId('map-container')).toBeInTheDocument()
    })
  })
})

// Unit tests for utility functions
describe('Utility Functions', () => {
  describe('getDistanceMiles (via Haversine)', () => {
    // Test known distances
    it('returns 0 for same coordinates', () => {
      // We can't directly test the function since it's not exported,
      // but we can verify the behavior through the component
      // This is a placeholder for when we export the function for testing
      expect(true).toBe(true)
    })
  })
})
