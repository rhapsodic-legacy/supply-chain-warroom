import { render, screen } from '@testing-library/react';
import { OrderTracker } from '../OrderTracker';

vi.mock('../../../hooks/useOrders', () => ({
  useOrderStats: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

import { useOrderStats } from '../../../hooks/useOrders';
const mockUseOrderStats = vi.mocked(useOrderStats);

describe('OrderTracker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    mockUseOrderStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useOrderStats>);

    render(<OrderTracker />);
    expect(screen.getByText('Loading orders...')).toBeInTheDocument();
  });

  it('renders order status bars with counts', () => {
    const stats = {
      pending: 5,
      confirmed: 10,
      in_production: 8,
      shipped: 3,
      in_transit: 12,
      customs: 2,
      delivered: 20,
      delayed: 4,
      cancelled: 1,
    };

    mockUseOrderStats.mockReturnValue({
      data: stats,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useOrderStats>);

    render(<OrderTracker />);

    // Check stage labels
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.getByText('In Production')).toBeInTheDocument();
    expect(screen.getByText('Shipped')).toBeInTheDocument();
    expect(screen.getByText('In Transit')).toBeInTheDocument();
    expect(screen.getByText('Customs')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();

    // Check total count (5+10+8+3+12+2+20+4+1 = 65)
    expect(screen.getByText('65')).toBeInTheDocument();

    // Check delayed indicator
    expect(screen.getByText('Delayed')).toBeInTheDocument();
  });

  it('shows empty state when no stats', () => {
    mockUseOrderStats.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useOrderStats>);

    render(<OrderTracker />);
    expect(screen.getByText('No order data available')).toBeInTheDocument();
  });
});
