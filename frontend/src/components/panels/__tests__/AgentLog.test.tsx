import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentLog } from '../AgentLog';

const mockDecisions = [
  {
    id: 'd1',
    agent_type: 'risk_monitor',
    decision_type: 'reroute_order',
    decision_summary: 'Reroute PO-2025-0042 via Cape of Good Hope',
    confidence_score: 0.85,
    status: 'executed',
    decided_at: new Date().toISOString(),
  },
  {
    id: 'd2',
    agent_type: 'strategy',
    decision_type: 'increase_inventory',
    decision_summary: 'Increase safety stock for critical components',
    confidence_score: 0.72,
    status: 'proposed',
    decided_at: new Date().toISOString(),
  },
];

vi.mock('../../../hooks/useAgents', () => ({
  useDecisions: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

import { useDecisions } from '../../../hooks/useAgents';
const mockUseDecisions = vi.mocked(useDecisions);

describe('AgentLog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no decisions', () => {
    mockUseDecisions.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDecisions>);

    render(<AgentLog />);
    expect(screen.getByText('No agent decisions')).toBeInTheDocument();
  });

  it('renders decisions with agent type badges', () => {
    mockUseDecisions.mockReturnValue({
      data: mockDecisions,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDecisions>);

    render(<AgentLog />);
    expect(screen.getByText('Reroute PO-2025-0042 via Cape of Good Hope')).toBeInTheDocument();
    expect(screen.getByText('Increase safety stock for critical components')).toBeInTheDocument();
    expect(screen.getByText('RSK')).toBeInTheDocument();
    expect(screen.getByText('STR')).toBeInTheDocument();
  });

  it('expanding a decision shows detail', async () => {
    const user = userEvent.setup();
    mockUseDecisions.mockReturnValue({
      data: mockDecisions,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDecisions>);

    render(<AgentLog />);

    // Click on the first decision to expand it
    const firstDecision = screen.getByText('Reroute PO-2025-0042 via Cape of Good Hope');
    await user.click(firstDecision);

    // Should show the decision type detail
    expect(screen.getByText('Decision Type')).toBeInTheDocument();
    expect(screen.getByText('reroute_order')).toBeInTheDocument();
  });
});
