import { render, screen } from '@testing-library/react';
import { EmptyState } from '../EmptyState';

describe('EmptyState', () => {
  it('renders default message', () => {
    render(<EmptyState />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders custom message', () => {
    render(<EmptyState message="Nothing to see here" />);
    expect(screen.getByText('Nothing to see here')).toBeInTheDocument();
  });
});
