import { render, screen } from '@testing-library/react';
import { Card } from '../Card';

describe('Card', () => {
  it('renders title', () => {
    render(<Card title="Test Title">content</Card>);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('renders children', () => {
    render(<Card><p>Child content</p></Card>);
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('applies className', () => {
    const { container } = render(<Card className="custom-class">content</Card>);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('renders badge when provided', () => {
    render(<Card title="Title" badge={<span data-testid="badge">Active</span>}>content</Card>);
    expect(screen.getByTestId('badge')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });
});
