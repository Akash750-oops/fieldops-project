/**
 * StatusBadge.test.jsx
 * Vitest + React Testing Library unit tests for the StatusBadge component.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBadge, { TECHNICIAN_STATUSES } from './StatusBadge';

describe('StatusBadge', () => {
  // ── 1. Renders all statuses ──────────────────────────────────────────────
  it('renders all 7 technician statuses without crashing', () => {
    const { container } = render(
      <div>
        {TECHNICIAN_STATUSES.map((s) => (
          <StatusBadge key={s} status={s} />
        ))}
      </div>
    );
    const badges = container.querySelectorAll('.sb-badge');
    expect(badges).toHaveLength(7);
  });

  // ── 2. Label text ─────────────────────────────────────────────────────────
  it('shows readable label text for EN_ROUTE', () => {
    render(<StatusBadge status="EN_ROUTE" />);
    expect(screen.getByText('En Route')).toBeInTheDocument();
  });

  it('shows readable label text for AVAILABLE', () => {
    render(<StatusBadge status="AVAILABLE" />);
    expect(screen.getByText('Available')).toBeInTheDocument();
  });

  // ── 3. Color/status CSS classes ───────────────────────────────────────────
  it('applies status-specific CSS class sb-AVAILABLE', () => {
    const { container } = render(<StatusBadge status="AVAILABLE" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-AVAILABLE');
  });

  it('applies status-specific CSS class sb-ON_SITE', () => {
    const { container } = render(<StatusBadge status="ON_SITE" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-ON_SITE');
  });

  // ── 4. Size variants ──────────────────────────────────────────────────────
  it('applies sb-sm class for size="sm"', () => {
    const { container } = render(<StatusBadge status="BUSY" size="sm" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-sm');
  });

  it('applies sb-md class for size="md" (default)', () => {
    const { container } = render(<StatusBadge status="BUSY" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-md');
  });

  it('applies sb-lg class for size="lg"', () => {
    const { container } = render(<StatusBadge status="BUSY" size="lg" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-lg');
  });

  // ── 5. Icon rendering ─────────────────────────────────────────────────────
  it('shows icon when showIcon=true (default)', () => {
    const { container } = render(<StatusBadge status="BUSY" />);
    expect(container.querySelector('.sb-icon')).toBeInTheDocument();
  });

  it('hides icon when showIcon=false', () => {
    const { container } = render(<StatusBadge status="BUSY" showIcon={false} />);
    expect(container.querySelector('.sb-icon')).not.toBeInTheDocument();
  });

  // ── 6. Pulse animation ────────────────────────────────────────────────────
  it('adds sb-pulse class for EN_ROUTE by default', () => {
    const { container } = render(<StatusBadge status="EN_ROUTE" />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-pulse');
  });

  it('does not add sb-pulse for AVAILABLE by default', () => {
    const { container } = render(<StatusBadge status="AVAILABLE" />);
    expect(container.querySelector('.sb-badge')).not.toHaveClass('sb-pulse');
  });

  it('overrides EN_ROUTE pulse to false when pulse={false}', () => {
    const { container } = render(<StatusBadge status="EN_ROUTE" pulse={false} />);
    expect(container.querySelector('.sb-badge')).not.toHaveClass('sb-pulse');
  });

  it('overrides AVAILABLE pulse to true when pulse={true}', () => {
    const { container } = render(<StatusBadge status="AVAILABLE" pulse={true} />);
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-pulse');
  });

  // ── 7. ARIA accessibility ─────────────────────────────────────────────────
  it('renders with role="status"', () => {
    render(<StatusBadge status="AVAILABLE" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-label containing the status label', () => {
    render(<StatusBadge status="AVAILABLE" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('aria-label', expect.stringContaining('Available'));
  });

  it('has aria-label containing the status description', () => {
    render(<StatusBadge status="BUSY" />);
    const badge = screen.getByRole('status');
    expect(badge.getAttribute('aria-label')).toMatch(/currently assigned/i);
  });

  // ── 8. Custom className ───────────────────────────────────────────────────
  it('applies custom className alongside default classes', () => {
    const { container } = render(
      <StatusBadge status="BUSY" className="my-test-class" />
    );
    expect(container.querySelector('.sb-badge')).toHaveClass('my-test-class');
    expect(container.querySelector('.sb-badge')).toHaveClass('sb-badge');
  });

  // ── 9. Fallback for unknown status ────────────────────────────────────────
  it('falls back to Offline config for unknown status', () => {
    render(<StatusBadge status="UNKNOWN_STATUS" />);
    // Should not throw — offline is the fallback
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });

  // ── 10. Tooltip renders ───────────────────────────────────────────────────
  it('renders a tooltip element with the description', () => {
    const { container } = render(<StatusBadge status="AVAILABLE" />);
    const tooltip = container.querySelector('.sb-tooltip');
    expect(tooltip).toBeInTheDocument();
    expect(tooltip?.textContent).toMatch(/available for assignment/i);
  });
});
