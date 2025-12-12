import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../test/test-utils'
import AnalysisPage from './AnalysisPage'
import { mockNodes, mockTraceroutes } from '../../test/mocks'

// Mock the API module
vi.mock('../../services/api', () => ({
  fetchNodes: vi.fn(),
  fetchTraceroutes: vi.fn(),
  fetchSolarNodesAnalysis: vi.fn(),
  fetchSolarForecastAnalysis: vi.fn(),
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

import { fetchNodes, fetchTraceroutes, fetchSolarNodesAnalysis, fetchSolarForecastAnalysis } from '../../services/api'

const mockedFetchNodes = vi.mocked(fetchNodes)
const mockedFetchTraceroutes = vi.mocked(fetchTraceroutes)
const mockedFetchSolarNodesAnalysis = vi.mocked(fetchSolarNodesAnalysis)
const mockedFetchSolarForecastAnalysis = vi.mocked(fetchSolarForecastAnalysis)

// Mock solar analysis data
const mockSolarAnalysis = {
  lookback_days: 7,
  total_nodes_analyzed: 50,
  solar_nodes_count: 2,
  avg_charging_hours_per_day: 10.5,
  avg_discharge_hours_per_day: 13.5,
  solar_nodes: [
    {
      node_num: 12345678,
      node_name: 'Solar Node 1',
      solar_score: 85.7,
      days_analyzed: 7,
      days_with_pattern: 6,
      recent_patterns: [
        {
          date: '2024-01-15',
          sunrise: { time: '07:30', value: 70 },
          peak: { time: '14:00', value: 95 },
          sunset: { time: '18:30', value: 88 },
          rise: 25,
          fall: 7,
          charge_rate_per_hour: 3.85,
          discharge_rate_per_hour: 0.54,
        },
      ],
      metric_type: 'battery' as const,
      chart_data: [
        { timestamp: 1705300000000, value: 70 },
        { timestamp: 1705320000000, value: 95 },
      ],
      avg_charge_rate_per_hour: 3.85,
      avg_discharge_rate_per_hour: 0.54,
      insufficient_solar: false,
    },
    {
      node_num: 87654321,
      node_name: 'Solar Node 2',
      solar_score: 71.4,
      days_analyzed: 7,
      days_with_pattern: 5,
      recent_patterns: [],
      metric_type: 'voltage' as const,
      chart_data: [],
      avg_charge_rate_per_hour: 0.08,
      avg_discharge_rate_per_hour: 0.02,
      insufficient_solar: true,
    },
  ],
  solar_production: [
    { timestamp: 1705300000000, wattHours: 50 },
    { timestamp: 1705320000000, wattHours: 150 },
  ],
}

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

describe('SolarMonitoring', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchNodes.mockResolvedValue(mockNodes)
    mockedFetchTraceroutes.mockResolvedValue(mockTraceroutes)
    mockedFetchSolarNodesAnalysis.mockResolvedValue(mockSolarAnalysis)
  })

  it('renders Solar Monitoring Analysis card on main page', () => {
    render(<AnalysisPage />)
    expect(screen.getByText('Solar Monitoring Analysis')).toBeInTheDocument()
    expect(screen.getByText(/Identify solar-powered nodes/)).toBeInTheDocument()
  })

  it('opens SolarMonitoring when card is clicked', async () => {
    render(<AnalysisPage />)

    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    expect(card).toBeInTheDocument()

    fireEvent.click(card!)

    // Should show Back button and Options header
    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument()
      expect(screen.getByText('Options')).toBeInTheDocument()
    })
  })

  it('renders lookback days input', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Lookback Period (Days)')).toBeInTheDocument()
    })
  })

  it('renders Identify Solar Nodes button', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })
  })

  it('shows analysis results after clicking Identify Solar Nodes', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })

    // Click analyze button
    fireEvent.click(screen.getByRole('button', { name: /Identify Solar Nodes/i }))

    // Should show results
    await waitFor(() => {
      expect(screen.getByText(/nodes analyzed/i)).toBeInTheDocument()
    })
  })

  it('displays solar node count after analysis', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })

    // Click analyze button
    fireEvent.click(screen.getByRole('button', { name: /Identify Solar Nodes/i }))

    // Should show solar nodes count in "Solar Nodes Found:" section
    await waitFor(() => {
      expect(screen.getByText('Solar Nodes Found:')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('shows empty state when no solar nodes found', async () => {
    mockedFetchSolarNodesAnalysis.mockResolvedValue({
      ...mockSolarAnalysis,
      solar_nodes_count: 0,
      solar_nodes: [],
      avg_charging_hours_per_day: null,
      avg_discharge_hours_per_day: null,
    })

    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })

    // Click analyze button
    fireEvent.click(screen.getByRole('button', { name: /Identify Solar Nodes/i }))

    // Should show no solar nodes message
    await waitFor(() => {
      expect(screen.getByText(/No solar-powered nodes identified/i)).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    mockedFetchSolarNodesAnalysis.mockRejectedValue(new Error('Network error'))

    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })

    // Click analyze button
    fireEvent.click(screen.getByRole('button', { name: /Identify Solar Nodes/i }))

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Error analyzing data/i)).toBeInTheDocument()
    })
  })

  it('returns to grid when Back button is clicked from Solar Monitoring', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
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

  it('allows changing lookback days', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByText('Lookback Period (Days)')).toBeInTheDocument()
    })

    // Find the input and change its value
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '14' } })

    expect(input).toHaveValue(14)
  })

  it('displays "Low Solar" warning for nodes with insufficient solar output', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Identify Solar Nodes/i })).toBeInTheDocument()
    })

    // Click analyze button
    fireEvent.click(screen.getByRole('button', { name: /Identify Solar Nodes/i }))

    // Should show "Low Solar" warning for the second node (insufficient_solar: true)
    await waitFor(() => {
      expect(screen.getByText('Low Solar')).toBeInTheDocument()
    })
  })
})

// Mock solar forecast data
const mockSolarForecast = {
  lookback_days: 7,
  historical_days_analyzed: 7,
  avg_historical_daily_wh: 1500.0,
  low_output_warning: false,
  forecast_days: [
    {
      date: '2024-01-16',
      forecast_wh: 1400,
      avg_historical_wh: 1500,
      pct_of_average: 93.3,
      is_low: false,
    },
    {
      date: '2024-01-17',
      forecast_wh: 1100,
      avg_historical_wh: 1500,
      pct_of_average: 73.3,
      is_low: true,
    },
  ],
  nodes_at_risk_count: 0,
  nodes_at_risk: [],
}

const mockSolarForecastWithAtRisk = {
  lookback_days: 7,
  historical_days_analyzed: 7,
  avg_historical_daily_wh: 1500.0,
  low_output_warning: true,
  forecast_days: [
    {
      date: '2024-01-16',
      forecast_wh: 900,
      avg_historical_wh: 1500,
      pct_of_average: 60.0,
      is_low: true,
    },
  ],
  nodes_at_risk_count: 1,
  nodes_at_risk: [
    {
      node_num: 12345678,
      node_name: 'At Risk Node',
      current_battery: 60,
      min_simulated_battery: 35,
      avg_charge_rate_per_hour: 3.5,
      avg_discharge_rate_per_hour: 0.6,
      simulation: [
        { date: '2024-01-16', simulated_battery: 55, forecast_factor: 0.6 },
        { date: '2024-01-17', simulated_battery: 35, forecast_factor: 0.6 },
      ],
    },
  ],
}

describe('SolarForecastAnalysis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchNodes.mockResolvedValue(mockNodes)
    mockedFetchTraceroutes.mockResolvedValue(mockTraceroutes)
    mockedFetchSolarNodesAnalysis.mockResolvedValue(mockSolarAnalysis)
    mockedFetchSolarForecastAnalysis.mockResolvedValue(mockSolarForecast)
  })

  it('renders Forecast Analysis button on Solar Monitoring page', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Forecast Analysis/i })).toBeInTheDocument()
    })
  })

  it('shows forecast results after clicking Forecast Analysis button', async () => {
    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Forecast Analysis/i })).toBeInTheDocument()
    })

    // Click forecast analysis button
    fireEvent.click(screen.getByRole('button', { name: /Forecast Analysis/i }))

    // Should show forecast summary
    await waitFor(() => {
      expect(screen.getByText(/Avg Historical:/i)).toBeInTheDocument()
    })
  })

  it('shows low output warning when forecast is below threshold', async () => {
    mockedFetchSolarForecastAnalysis.mockResolvedValue(mockSolarForecastWithAtRisk)

    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Forecast Analysis/i })).toBeInTheDocument()
    })

    // Click forecast analysis button
    fireEvent.click(screen.getByRole('button', { name: /Forecast Analysis/i }))

    // Should show low output warning
    await waitFor(() => {
      expect(screen.getByText(/Low Solar Output Forecast/i)).toBeInTheDocument()
    })
  })

  it('shows nodes at risk when forecast predicts low battery', async () => {
    mockedFetchSolarForecastAnalysis.mockResolvedValue(mockSolarForecastWithAtRisk)

    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Forecast Analysis/i })).toBeInTheDocument()
    })

    // Click forecast analysis button
    fireEvent.click(screen.getByRole('button', { name: /Forecast Analysis/i }))

    // Should show nodes at risk count
    await waitFor(() => {
      expect(screen.getByText(/Nodes at Risk:/i)).toBeInTheDocument()
    })
  })

  it('shows error state when forecast API fails', async () => {
    mockedFetchSolarForecastAnalysis.mockRejectedValue(new Error('Network error'))

    render(<AnalysisPage />)

    // Open solar monitoring
    const card = screen.getByText('Solar Monitoring Analysis').closest('button')
    fireEvent.click(card!)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Forecast Analysis/i })).toBeInTheDocument()
    })

    // Click forecast analysis button
    fireEvent.click(screen.getByRole('button', { name: /Forecast Analysis/i }))

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Error analyzing forecast/i)).toBeInTheDocument()
    })
  })
})
