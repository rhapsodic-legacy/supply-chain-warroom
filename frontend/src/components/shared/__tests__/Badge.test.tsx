import { render, screen } from '@testing-library/react';
import { Badge } from '../Badge';

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge severity="info">Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it.each(['critical', 'high', 'medium', 'low', 'info'] as const)(
    'applies badge-%s class for severity "%s"',
    (severity) => {
      const { container } = render(<Badge severity={severity}>Label</Badge>);
      expect(container.firstChild).toHaveClass(`badge-${severity}`);
    }
  );

  it('shows pulse dot when dot prop is true', () => {
    const { container } = render(<Badge severity="critical" dot>Alert</Badge>);
    const dot = container.querySelector('.pulse-dot');
    expect(dot).toBeInTheDocument();
  });

  it('does not show pulse dot when dot prop is absent', () => {
    const { container } = render(<Badge severity="critical">Alert</Badge>);
    const dot = container.querySelector('.pulse-dot');
    expect(dot).not.toBeInTheDocument();
  });
});
