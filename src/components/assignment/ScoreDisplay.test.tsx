import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ScoreDisplay, {
  CompactScorePanel,
  ScoreBadge,
  getScoreLevel,
  formatScore,
} from './ScoreDisplay';

/* ── Shared props ─────────────────────────────────────────────────────────── */
const defaultProps = {
  composite_score: 85.5,
  proximity_score: 90.0,
  skill_score:     80.0,
  workload_score:  86.5,
  distance_km:     12.3,
  active_jobs:     2,
  max_capacity:    5,
};

/* ═══════════════════════════════════════════════════════════════════════════
   Utility helpers
   ═══════════════════════════════════════════════════════════════════════════ */

describe('Score utilities', () => {
  describe('getScoreLevel', () => {
    it('returns "high" for score > 70', () => {
      expect(getScoreLevel(71)).toBe('high');
      expect(getScoreLevel(100)).toBe('high');
      expect(getScoreLevel(70.1)).toBe('high');
    });

    it('returns "medium" for score === 70 (boundary)', () => {
      expect(getScoreLevel(70)).toBe('medium');
    });

    it('returns "medium" for score in [40, 70]', () => {
      expect(getScoreLevel(40)).toBe('medium');
      expect(getScoreLevel(55)).toBe('medium');
      expect(getScoreLevel(69.9)).toBe('medium');
    });

    it('returns "low" for score < 40', () => {
      expect(getScoreLevel(39.9)).toBe('low');
      expect(getScoreLevel(0)).toBe('low');
    });
  });

  describe('formatScore', () => {
    it('formats to exactly 1 decimal place', () => {
      expect(formatScore(85)).toBe('85.0');
      expect(formatScore(85.55)).toBe('85.6');   // rounds up
      expect(formatScore(0)).toBe('0.0');
      expect(formatScore(100)).toBe('100.0');
    });
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   ScoreDisplay — full variant
   ═══════════════════════════════════════════════════════════════════════════ */

describe('ScoreDisplay', () => {
  it('renders all score values correctly and formatted to 1 decimal place', () => {
    render(<ScoreDisplay {...defaultProps} />);

    // Composite score element must exist and contain the formatted value
    const compositeEl = screen.getByTestId('composite-score');
    expect(compositeEl).toHaveTextContent('85.5');

    // ARIA labels on score bar groups
    expect(screen.getByLabelText(/Composite score: 85.5 out of 100/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Proximity: 90.0 out of 100/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Skill Match: 80.0 out of 100/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Workload: 86.5 out of 100/i)).toBeInTheDocument();
  });

  it('displays Top 3 badge only when is_top_3 is true', () => {
    const { rerender } = render(<ScoreDisplay {...defaultProps} />);
    expect(screen.queryByTestId('top-3-badge')).not.toBeInTheDocument();

    rerender(<ScoreDisplay {...defaultProps} is_top_3={true} />);
    expect(screen.getByTestId('top-3-badge')).toBeInTheDocument();
  });

  it('displays distance badge with correct kilometers', () => {
    render(<ScoreDisplay {...defaultProps} />);
    expect(screen.getByTestId('distance-badge')).toHaveTextContent('12.3 km');
  });

  it('displays workload badge with active jobs and max capacity', () => {
    render(<ScoreDisplay {...defaultProps} />);
    expect(screen.getByTestId('workload-badge')).toHaveTextContent('2 / 5');
  });

  it('has correct ARIA labels present for accessibility', () => {
    render(<ScoreDisplay {...defaultProps} />);

    // Top-level region
    expect(
      screen.getByRole('region', { name: /Technician Assignment Score/i })
    ).toBeInTheDocument();

    // Progress bars (3 score bars)
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars.length).toBeGreaterThanOrEqual(3);

    expect(screen.getByLabelText(/Proximity progress/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Skill Match progress/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Workload progress/i)).toBeInTheDocument();
  });

  it('supports score update rendering', async () => {
    const { rerender } = render(<ScoreDisplay {...defaultProps} />);

    // Initial value must be visible immediately
    expect(screen.getByTestId('composite-score')).toHaveTextContent('85.5');

    rerender(<ScoreDisplay {...defaultProps} composite_score={95.1} />);

    // The span is seeded with the new value synchronously via the data-value
    // attribute; wait for the textContent to reflect the new seed value.
    await waitFor(
      () => {
        expect(screen.getByTestId('composite-score')).toHaveTextContent('95.1');
      },
      { timeout: 2000 }
    );
  });

  describe('Color coding logic', () => {
    it('applies high score (green) styling for scores > 70', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={71} />);
      expect(screen.getByTestId('score-display')).toHaveAttribute(
        'data-score-level',
        'high'
      );
    });

    it('applies medium score (yellow/amber) styling for scores between 40 and 70', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={70} />);
      expect(screen.getByTestId('score-display')).toHaveAttribute(
        'data-score-level',
        'medium'
      );
    });

    it('applies low score (red) styling for scores < 40', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={39.9} />);
      expect(screen.getByTestId('score-display')).toHaveAttribute(
        'data-score-level',
        'low'
      );
    });

    it('correctly classifies boundary score of 40 as medium', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={40} />);
      expect(screen.getByTestId('score-display')).toHaveAttribute(
        'data-score-level',
        'medium'
      );
    });
  });

  describe('Edge cases', () => {
    it('renders a score of 0 without crashing', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={0} />);
      expect(screen.getByTestId('composite-score')).toHaveTextContent('0.0');
    });

    it('renders a score of 100 without crashing', () => {
      render(<ScoreDisplay {...defaultProps} composite_score={100} />);
      expect(screen.getByTestId('composite-score')).toHaveTextContent('100.0');
    });
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   CompactScorePanel
   ═══════════════════════════════════════════════════════════════════════════ */

describe('CompactScorePanel', () => {
  it('renders with role region and label', () => {
    render(<CompactScorePanel {...defaultProps} />);
    expect(
      screen.getByRole('region', { name: /Assignment Score Summary/i })
    ).toBeInTheDocument();
  });

  it('shows composite score formatted to 1 decimal', () => {
    render(<CompactScorePanel {...defaultProps} composite_score={74.6} />);
    expect(screen.getByRole('region')).toHaveTextContent('74.6');
  });

  it('shows distance in km', () => {
    render(<CompactScorePanel {...defaultProps} distance_km={9.7} />);
    expect(screen.getByRole('region')).toHaveTextContent('9.7 km');
  });

  it('shows workload as active/max', () => {
    render(<CompactScorePanel {...defaultProps} active_jobs={3} max_capacity={5} />);
    expect(screen.getByRole('region')).toHaveTextContent('3/5');
  });

  it('shows Top Pick label when is_top_3=true', () => {
    render(<CompactScorePanel {...defaultProps} is_top_3={true} />);
    expect(screen.getByRole('region')).toHaveTextContent('Top Pick');
  });

  it('does not show Top Pick label when is_top_3=false', () => {
    render(<CompactScorePanel {...defaultProps} is_top_3={false} />);
    expect(screen.queryByText('Top Pick')).not.toBeInTheDocument();
  });

  it('renders 3 mini progress bars for breakdown scores', () => {
    render(<CompactScorePanel {...defaultProps} />);
    const bars = screen.getAllByRole('progressbar');
    expect(bars.length).toBeGreaterThanOrEqual(3);
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   ScoreBadge
   ═══════════════════════════════════════════════════════════════════════════ */

describe('ScoreBadge', () => {
  it('renders with formatted score text', () => {
    render(<ScoreBadge score={82.5} label="Composite" />);
    expect(screen.getByText('82.5')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<ScoreBadge score={82.5} label="Composite" />);
    expect(
      screen.getByLabelText(/Composite: 82.5 out of 100/i)
    ).toBeInTheDocument();
  });

  it('renders data-testid matching label', () => {
    render(<ScoreBadge score={70} label="Skill Match" />);
    expect(screen.getByTestId('score-badge-skill-match')).toBeInTheDocument();
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   ScoreDisplay — compact variant prop
   ═══════════════════════════════════════════════════════════════════════════ */

describe('ScoreDisplay variant="compact"', () => {
  it('renders CompactScorePanel when variant is compact', () => {
    render(<ScoreDisplay {...defaultProps} variant="compact" />);
    expect(screen.getByTestId('compact-score-panel')).toBeInTheDocument();
  });

  it('does NOT render the full score-display testid when variant is compact', () => {
    render(<ScoreDisplay {...defaultProps} variant="compact" />);
    expect(screen.queryByTestId('score-display')).not.toBeInTheDocument();
  });
});
