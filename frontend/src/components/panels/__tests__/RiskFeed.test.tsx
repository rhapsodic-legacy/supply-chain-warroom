import { render, screen } from '@testing-library/react';
import { RiskFeed } from '../RiskFeed';

const mockRiskEvents = [
  {
    id: 'r1',
    event_type: 'geopolitical',
    title: 'Suez Canal Disruption',
    description: 'Major disruption in Suez Canal shipping routes.',
    severity: 'critical',
    severity_score: 0.95,
    affected_region: 'Middle East',
    started_at: new Date().toISOString(),
    expected_end: null,
    actual_end: null,
    is_active: true,
    created_at: new Date().toISOString(),
    impacts: [
      {
        id: 'i1',
        risk_event_id: 'r1',
        entity_type: 'supplier',
        entity_id: 's1',
        entity_name: 'Acme Corp',
        impact_multiplier: 1.5,
        created_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 'r2',
    event_type: 'weather',
    title: 'Typhoon Warning',
    description: 'Typhoon approaching East Asia.',
    severity: 'high',
    severity_score: 0.7,
    affected_region: 'East Asia',
    started_at: new Date().toISOString(),
    expected_end: null,
    actual_end: null,
    is_active: true,
    created_at: new Date().toISOString(),
    impacts: [],
  },
];

vi.mock('../../../hooks/useRiskEvents', () => ({
  useRiskEvents: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

import { useRiskEvents } from '../../../hooks/useRiskEvents';
const mockUseRiskEvents = vi.mocked(useRiskEvents);

describe('RiskFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner when loading', () => {
    mockUseRiskEvents.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useRiskEvents>);

    render(<RiskFeed />);
    expect(screen.getByText('Scanning threats...')).toBeInTheDocument();
  });

  it('shows error card on error', () => {
    mockUseRiskEvents.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    } as unknown as ReturnType<typeof useRiskEvents>);

    render(<RiskFeed />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('shows empty state when no events', () => {
    mockUseRiskEvents.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useRiskEvents>);

    render(<RiskFeed />);
    expect(screen.getByText('No active risk events')).toBeInTheDocument();
  });

  it('renders risk events with severity badges', () => {
    mockUseRiskEvents.mockReturnValue({
      data: mockRiskEvents,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useRiskEvents>);

    render(<RiskFeed />);
    expect(screen.getByText('Suez Canal Disruption')).toBeInTheDocument();
    expect(screen.getByText('Typhoon Warning')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
  });
});
