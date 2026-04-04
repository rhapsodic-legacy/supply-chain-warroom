import { render, screen } from '@testing-library/react';
import { ErrorCard } from '../ErrorCard';

describe('ErrorCard', () => {
  it('renders error message', () => {
    render(<ErrorCard message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<ErrorCard message="Error" onRetry={onRetry} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('has alert role', () => {
    render(<ErrorCard message="Error" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
