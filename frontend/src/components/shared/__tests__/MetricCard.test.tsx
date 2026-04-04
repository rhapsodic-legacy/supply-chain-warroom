import { render, screen } from '@testing-library/react';
import { MetricCard } from '../MetricCard';

describe('MetricCard', () => {
  it('renders label and value', () => {
    render(<MetricCard label="Total Orders" value={42} />);
    expect(screen.getByText('Total Orders')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('shows up arrow for positive trend', () => {
    render(<MetricCard label="Revenue" value="$1M" trend="up" trendValue="+5%" />);
    expect(screen.getByText(/\u2191/)).toBeInTheDocument();
    expect(screen.getByText(/\+5%/)).toBeInTheDocument();
  });

  it('shows down arrow for negative trend', () => {
    render(<MetricCard label="Fill Rate" value="87%" trend="down" trendValue="-3%" />);
    expect(screen.getByText(/\u2193/)).toBeInTheDocument();
    expect(screen.getByText(/-3%/)).toBeInTheDocument();
  });

  it('shows flat arrow for zero trend', () => {
    render(<MetricCard label="Supply" value={100} trend="flat" trendValue="0%" />);
    expect(screen.getByText(/\u2192/)).toBeInTheDocument();
  });
});
