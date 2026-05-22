/**
 * TopThreeHighlight.test.tsx
 * Vitest + React Testing Library — comprehensive test suite.
 */
import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TopThreeHighlight, {
  RankCard,
  getRecommendationReason,
  MEDAL_CONFIG,
  type RankedTechnician,
} from './TopThreeHighlight';

/* ─── Shared fixtures ──────────────────────────────────────────────── */

const makeTech = (overrides: Partial<RankedTechnician> = {}): RankedTechnician => ({
  technician_id:    1,
  technician_name:  'Alice Green',
  technician_skill: 'Electrical',
  technician_status: 'Available',
  composite_score:  88.0,
  proximity_score:  82.0,
  skill_score:      95.0,
  workload_score:   87.0,
  distance_km:      5.3,
  active_jobs:      1,
  max_capacity:     5,
  ...overrides,
});

const GOLD_TECH   = makeTech({ technician_id: 1, technician_name: 'Alice Green',   composite_score: 92, skill_score: 95, proximity_score: 80, workload_score: 85, distance_km: 4.1  });
const SILVER_TECH = makeTech({ technician_id: 2, technician_name: 'Bob Harris',    composite_score: 78, skill_score: 60, proximity_score: 90, workload_score: 78, distance_km: 2.7  });
const BRONZE_TECH = makeTech({ technician_id: 3, technician_name: 'Carol Diaz',    composite_score: 65, skill_score: 55, proximity_score: 58, workload_score: 95, active_jobs: 0, max_capacity: 5, distance_km: 14.0 });

const THREE_TECHS = [GOLD_TECH, SILVER_TECH, BRONZE_TECH];

const defaultProps = {
  technicians: THREE_TECHS,
  jobId:       101,
  jobLabel:    'Fix HVAC Unit',
  onSelect:    vi.fn(),
  onClose:     vi.fn(),
};

/* ─── Helpers ──────────────────────────────────────────────────────── */

const renderHighlight = (props = {}) =>
  render(<TopThreeHighlight {...defaultProps} {...props} />);

/* ══════════════════════════════════════════════════════════════════════
   1. Utility — getRecommendationReason
   ══════════════════════════════════════════════════════════════════════ */

describe('getRecommendationReason', () => {
  it('returns skill match reason when skill_score is strictly highest', () => {
    const reason = getRecommendationReason(
      makeTech({ skill_score: 95, proximity_score: 70, workload_score: 72 })
    );
    expect(reason).toMatch(/Best skill match/i);
    expect(reason).toContain('95%');
  });

  it('returns proximity reason when proximity_score is strictly highest', () => {
    const reason = getRecommendationReason(
      makeTech({ skill_score: 60, proximity_score: 94, workload_score: 72, distance_km: 3.2 })
    );
    expect(reason).toMatch(/Nearest available/i);
    expect(reason).toContain('3.2km');
  });

  it('returns workload reason when workload_score is strictly highest', () => {
    const reason = getRecommendationReason(
      makeTech({ skill_score: 60, proximity_score: 62, workload_score: 97, active_jobs: 0, max_capacity: 5 })
    );
    expect(reason).toMatch(/Low workload/i);
    expect(reason).toContain('0/5');
  });

  it('falls back gracefully when all scores are equal', () => {
    const reason = getRecommendationReason(
      makeTech({ skill_score: 75, proximity_score: 75, workload_score: 75 })
    );
    // Should not throw and return a non-empty string
    expect(typeof reason).toBe('string');
    expect(reason.length).toBeGreaterThan(0);
  });

  it('formats distance_km to 1 decimal place in proximity reason', () => {
    const reason = getRecommendationReason(
      makeTech({ proximity_score: 99, skill_score: 30, workload_score: 30, distance_km: 12.3456 })
    );
    expect(reason).toContain('12.3km');
  });

  it('includes skill_score as integer percentage in skill reason', () => {
    const reason = getRecommendationReason(
      makeTech({ skill_score: 87.6, proximity_score: 40, workload_score: 40 })
    );
    expect(reason).toContain('88%'); // toFixed(0) rounds
  });
});

/* ══════════════════════════════════════════════════════════════════════
   2. MEDAL_CONFIG tokens
   ══════════════════════════════════════════════════════════════════════ */

describe('MEDAL_CONFIG', () => {
  it('gold has rank 1', () => expect(MEDAL_CONFIG.gold.rank).toBe(1));
  it('silver has rank 2', () => expect(MEDAL_CONFIG.silver.rank).toBe(2));
  it('bronze has rank 3', () => expect(MEDAL_CONFIG.bronze.rank).toBe(3));

  it('gold label is "Gold"', () => expect(MEDAL_CONFIG.gold.label).toBe('Gold'));
  it('silver label is "Silver"', () => expect(MEDAL_CONFIG.silver.label).toBe('Silver'));
  it('bronze label is "Bronze"', () => expect(MEDAL_CONFIG.bronze.label).toBe('Bronze'));
});

/* ══════════════════════════════════════════════════════════════════════
   3. TopThreeHighlight — Rendering
   ══════════════════════════════════════════════════════════════════════ */

describe('TopThreeHighlight rendering', () => {
  it('renders the section with correct aria-label', () => {
    renderHighlight();
    expect(
      screen.getByRole('region', { name: /Top 3 Recommended Technicians/i })
    ).toBeInTheDocument();
  });

  it('renders the data-testid "top-three-highlight"', () => {
    renderHighlight();
    expect(screen.getByTestId('top-three-highlight')).toBeInTheDocument();
  });

  it('renders all 3 rank cards', () => {
    renderHighlight();
    expect(screen.getByTestId('rank-card-1')).toBeInTheDocument();
    expect(screen.getByTestId('rank-card-2')).toBeInTheDocument();
    expect(screen.getByTestId('rank-card-3')).toBeInTheDocument();
  });

  it('renders top 3 pinned at top: role=list with 3 listitem children', () => {
    renderHighlight();
    const list = screen.getByRole('list', { name: /Ranked technician recommendations/i });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(3);
  });

  it('shows the job label in the header when provided', () => {
    renderHighlight({ jobLabel: 'Fix HVAC Unit' });
    expect(screen.getByText(/for Fix HVAC Unit/i)).toBeInTheDocument();
  });

  it('does not show job label text when not provided', () => {
    renderHighlight({ jobLabel: undefined });
    expect(screen.queryByText(/^for /i)).not.toBeInTheDocument();
  });

  it('renders the "AI Ranked" section badge', () => {
    renderHighlight();
    expect(screen.getByTestId('top-3-section-badge')).toHaveTextContent('AI Ranked');
  });

  it('renders the "Recommended" badge on rank 1 only', () => {
    renderHighlight();
    expect(screen.getByTestId('recommended-badge')).toBeInTheDocument();

    // Only one badge
    expect(screen.getAllByTestId('recommended-badge')).toHaveLength(1);
  });
});

/* ══════════════════════════════════════════════════════════════════════
   4. Medal attribution (data-medal attribute)
   ══════════════════════════════════════════════════════════════════════ */

describe('Medal attribution', () => {
  it('rank-card-1 has data-medal="gold"', () => {
    renderHighlight();
    expect(screen.getByTestId('rank-card-1')).toHaveAttribute('data-medal', 'gold');
  });

  it('rank-card-2 has data-medal="silver"', () => {
    renderHighlight();
    expect(screen.getByTestId('rank-card-2')).toHaveAttribute('data-medal', 'silver');
  });

  it('rank-card-3 has data-medal="bronze"', () => {
    renderHighlight();
    expect(screen.getByTestId('rank-card-3')).toHaveAttribute('data-medal', 'bronze');
  });

  it('renders gold medal icon for rank 1', () => {
    renderHighlight();
    expect(screen.getByTestId('medal-icon-gold')).toBeInTheDocument();
  });

  it('renders silver medal icon for rank 2', () => {
    renderHighlight();
    expect(screen.getByTestId('medal-icon-silver')).toBeInTheDocument();
  });

  it('renders bronze medal icon for rank 3', () => {
    renderHighlight();
    expect(screen.getByTestId('medal-icon-bronze')).toBeInTheDocument();
  });
});

/* ══════════════════════════════════════════════════════════════════════
   5. ARIA labels for accessibility
   ══════════════════════════════════════════════════════════════════════ */

describe('ARIA labels', () => {
  it('rank-card-1 has aria-label containing rank number and name', () => {
    renderHighlight();
    const card = screen.getByTestId('rank-card-1');
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Rank 1'));
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Alice Green'));
  });

  it('rank-card-2 has aria-label containing rank number and name', () => {
    renderHighlight();
    const card = screen.getByTestId('rank-card-2');
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Rank 2'));
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Bob Harris'));
  });

  it('rank-card-3 has aria-label containing rank number and name', () => {
    renderHighlight();
    const card = screen.getByTestId('rank-card-3');
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Rank 3'));
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Carol Diaz'));
  });

  it('"Select Other" button has correct aria-label', () => {
    renderHighlight();
    expect(
      screen.getByRole('button', { name: /Select other technician/i })
    ).toBeInTheDocument();
  });

  it('close button has aria-label', () => {
    renderHighlight();
    expect(
      screen.getByRole('button', { name: /Close recommendations panel/i })
    ).toBeInTheDocument();
  });

  it('each Select button has aria-label with technician name', () => {
    renderHighlight();
    expect(
      screen.getByRole('button', { name: /Select Alice Green for this job/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Select Bob Harris for this job/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Select Carol Diaz for this job/i })
    ).toBeInTheDocument();
  });
});

/* ══════════════════════════════════════════════════════════════════════
   6. Recommendation reasons
   ══════════════════════════════════════════════════════════════════════ */

describe('Recommendation reasons', () => {
  it('renders a reason chip for each rank card', () => {
    renderHighlight();
    expect(screen.getByTestId('reason-chip-1')).toBeInTheDocument();
    expect(screen.getByTestId('reason-chip-2')).toBeInTheDocument();
    expect(screen.getByTestId('reason-chip-3')).toBeInTheDocument();
  });

  it('rank 1 reason mentions skill match (skill_score is highest for GOLD_TECH)', () => {
    renderHighlight();
    expect(screen.getByTestId('reason-text-1').textContent).toMatch(/Best skill match/i);
  });

  it('rank 2 reason mentions proximity (proximity_score is highest for SILVER_TECH)', () => {
    renderHighlight();
    expect(screen.getByTestId('reason-text-2').textContent).toMatch(/Nearest available/i);
  });

  it('rank 3 reason mentions workload (workload_score is highest for BRONZE_TECH)', () => {
    renderHighlight();
    expect(screen.getByTestId('reason-text-3').textContent).toMatch(/Low workload/i);
  });
});

/* ══════════════════════════════════════════════════════════════════════
   7. Pin-to-top: rendering order
   ══════════════════════════════════════════════════════════════════════ */

describe('Ranking order', () => {
  it('sorts technicians by composite_score descending regardless of input order', () => {
    // Pass in reverse order — component must sort
    const reversed = [BRONZE_TECH, SILVER_TECH, GOLD_TECH];
    render(<TopThreeHighlight {...defaultProps} technicians={reversed} />);

    const card1 = screen.getByTestId('rank-card-1');
    expect(card1).toHaveAttribute('aria-label', expect.stringContaining('Alice Green')); // highest
  });

  it('rank-card-1 always has the highest composite_score', () => {
    renderHighlight();
    // gold has 92, silver 78, bronze 65
    const card1 = screen.getByTestId('rank-card-1');
    expect(within(card1).getByLabelText(/Score: 92.0 out of 100/i)).toBeInTheDocument();
  });

  it('caps rendering at 3 cards even if more technicians are passed', () => {
    const extra = makeTech({ technician_id: 4, technician_name: 'Dave Extra', composite_score: 50 });
    const moreTechs = [...THREE_TECHS, extra];
    render(<TopThreeHighlight {...defaultProps} technicians={moreTechs} />);

    expect(screen.queryByTestId('rank-card-4')).not.toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });
});

/* ══════════════════════════════════════════════════════════════════════
   8. Interactions — Select & Override
   ══════════════════════════════════════════════════════════════════════ */

describe('Interactions', () => {
  it('calls onSelect with correct technician_id when Select button is clicked (rank 1)', () => {
    const onSelect = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('select-btn-1'));
    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith(GOLD_TECH.technician_id);
  });

  it('calls onSelect with correct technician_id when Select button is clicked (rank 2)', () => {
    const onSelect = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('select-btn-2'));
    expect(onSelect).toHaveBeenCalledWith(SILVER_TECH.technician_id);
  });

  it('calls onSelect with correct technician_id when Select button is clicked (rank 3)', () => {
    const onSelect = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('select-btn-3'));
    expect(onSelect).toHaveBeenCalledWith(BRONZE_TECH.technician_id);
  });

  it('"Select Other" button calls onClose', () => {
    const onClose = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('select-other-btn'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('Close (X) button also calls onClose', () => {
    const onClose = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('close-btn'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('onSelect is NOT called when override buttons are clicked', () => {
    const onSelect = vi.fn();
    render(<TopThreeHighlight {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('select-other-btn'));
    fireEvent.click(screen.getByTestId('close-btn'));
    expect(onSelect).not.toHaveBeenCalled();
  });
});

/* ══════════════════════════════════════════════════════════════════════
   9. Status pills
   ══════════════════════════════════════════════════════════════════════ */

describe('Status pills', () => {
  it('renders Available status pill for an available technician', () => {
    renderHighlight();
    // GOLD_TECH is Available — at least one should exist
    expect(screen.getAllByTestId('status-pill-available').length).toBeGreaterThanOrEqual(1);
  });

  it('renders Busy status pill when technician status is Busy', () => {
    const busyTech = makeTech({ technician_id: 99, technician_name: 'Busy Bob', composite_score: 70, technician_status: 'Busy' });
    render(
      <TopThreeHighlight
        {...defaultProps}
        technicians={[GOLD_TECH, busyTech, BRONZE_TECH]}
      />
    );
    expect(screen.getByTestId('status-pill-busy')).toBeInTheDocument();
  });
});

/* ══════════════════════════════════════════════════════════════════════
   10. RankCard standalone
   ══════════════════════════════════════════════════════════════════════ */

describe('RankCard standalone', () => {
  const baseProps = {
    rank: 1 as const,
    medal: 'gold' as const,
    tech: GOLD_TECH,
    reason: 'Best skill match (95%)',
    onSelect: vi.fn(),
  };

  it('renders technician name', () => {
    render(<RankCard {...baseProps} />);
    expect(screen.getByText('Alice Green')).toBeInTheDocument();
  });

  it('renders technician skill', () => {
    render(<RankCard {...baseProps} />);
    expect(screen.getByText('Electrical')).toBeInTheDocument();
  });

  it('renders reason text prop', () => {
    render(<RankCard {...baseProps} reason="Nearest available (4.1km)" />);
    expect(screen.getByTestId('reason-text-1')).toHaveTextContent('Nearest available (4.1km)');
  });

  it('renders gold medal icon', () => {
    render(<RankCard {...baseProps} />);
    expect(screen.getByTestId('medal-icon-gold')).toBeInTheDocument();
  });

  it('calls onSelect with technician_id when Select clicked', () => {
    const onSelect = vi.fn();
    render(<RankCard {...baseProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('select-btn-1'));
    expect(onSelect).toHaveBeenCalledWith(GOLD_TECH.technician_id);
  });
});
