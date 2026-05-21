import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RankedTechTable, { RankedTechTableProps } from './RankedTechTable';
import { RankedTechnician } from './TopThreeHighlight';

const makeTech = (overrides: Partial<RankedTechnician> = {}): RankedTechnician => ({
  technician_id: 1,
  technician_name: 'Tech One',
  technician_skill: 'Plumbing',
  technician_status: 'Available',
  composite_score: 85,
  proximity_score: 80,
  skill_score: 90,
  workload_score: 85,
  distance_km: 4.5,
  active_jobs: 1,
  max_capacity: 5,
  ...overrides,
});

const mockCandidates: RankedTechnician[] = [
  makeTech({ technician_id: 1, technician_name: 'Alice Gold', composite_score: 95, distance_km: 1.2, technician_skill: 'Plumbing' }),
  makeTech({ technician_id: 2, technician_name: 'Bob Silver', composite_score: 85, distance_km: 5.6, technician_skill: 'Electrical' }),
  makeTech({ technician_id: 3, technician_name: 'Charlie Bronze', composite_score: 75, distance_km: 2.3, technician_skill: 'Plumbing' }),
  makeTech({ technician_id: 4, technician_name: 'Dave Dave', composite_score: 65, distance_km: 10.4, technician_status: 'Busy', technician_skill: 'Electrical' }),
  makeTech({ technician_id: 5, technician_name: 'Eve Eve', composite_score: 55, distance_km: 15.0, technician_status: 'Offline', technician_skill: 'Network Support' }),
];

const defaultProps: RankedTechTableProps = {
  job: {
    id: 101,
    customer_name: 'Acme Corp',
    location: 'Downtown',
  },
  candidates: mockCandidates,
  selectedTechId: undefined,
  onSelect: vi.fn(),
  onAssign: vi.fn(),
  onClose: vi.fn(),
};

describe('RankedTechTable', () => {
  it('renders the component and title details correctly', () => {
    render(<RankedTechTable {...defaultProps} />);
    expect(screen.getByTestId('ranked-tech-selection-panel')).toBeInTheDocument();
    expect(screen.getByText('Job #101')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
  });

  it('renders the TopThreeHighlight component at the top', () => {
    render(<RankedTechTable {...defaultProps} />);
    // TopThreeHighlight renders cards
    expect(screen.getByTestId('rank-card-1')).toBeInTheDocument();
    expect(screen.getByTestId('rank-card-2')).toBeInTheDocument();
    expect(screen.getByTestId('rank-card-3')).toBeInTheDocument();
  });

  it('pins the top 3 recommendations at the top of the table', () => {
    render(<RankedTechTable {...defaultProps} />);
    expect(screen.getByTestId('table-pinned-row-1')).toHaveTextContent('Alice Gold');
    expect(screen.getByTestId('table-pinned-row-2')).toHaveTextContent('Bob Silver');
    expect(screen.getByTestId('table-pinned-row-3')).toHaveTextContent('Charlie Bronze');
  });

  it('renders remaining candidates (Rank 4+) in the "Other Candidates" section', () => {
    render(<RankedTechTable {...defaultProps} />);
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Dave Dave');
    expect(screen.getByTestId('table-other-row-1')).toHaveTextContent('Eve Eve');
  });

  it('allows filtering by status in the other candidates list', () => {
    render(<RankedTechTable {...defaultProps} />);
    const statusFilter = screen.getByTestId('toolbar-status-filter');

    // Filter by Busy status
    fireEvent.change(statusFilter, { target: { value: 'Busy' } });

    // Pinned rows remain visible
    expect(screen.getByTestId('table-pinned-row-1')).toBeInTheDocument();

    // Dave is Busy, Eve is Offline (Eve should be filtered out)
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Dave Dave');
    expect(screen.queryByTestId('table-other-row-1')).not.toBeInTheDocument();
  });

  it('allows filtering by skill in the other candidates list', () => {
    render(<RankedTechTable {...defaultProps} />);
    const skillFilter = screen.getByTestId('toolbar-skill-filter');

    // Filter by Network Support
    fireEvent.change(skillFilter, { target: { value: 'Network Support' } });

    // Eve Eve is Network Support, Dave Dave is Electrical (Dave should be filtered out)
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Eve Eve');
    expect(screen.queryByText('Dave Dave')).not.toBeInTheDocument();
  });

  it('allows searching by technician name', () => {
    render(<RankedTechTable {...defaultProps} />);
    const searchInput = screen.getByTestId('toolbar-search-input');

    // Search for "Eve"
    fireEvent.change(searchInput, { target: { value: 'Eve' } });

    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Eve Eve');
    expect(screen.queryByText('Dave Dave')).not.toBeInTheDocument();
  });

  it('allows sorting the other candidates list by headers', () => {
    render(<RankedTechTable {...defaultProps} />);

    // Default sort is Score desc: Dave (#4, composite_score 65) then Eve (#5, composite_score 55)
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Dave Dave');
    expect(screen.getByTestId('table-other-row-1')).toHaveTextContent('Eve Eve');

    // Sort by Distance (header: Distance). Click Distance header
    const distanceHeader = screen.getByRole('columnheader', { name: /Distance/i });
    fireEvent.click(distanceHeader); // sorts Distance asc
    
    // Dave has 10.4 km, Eve has 15.0 km. Under asc, Dave is still first
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Dave Dave');
    
    // Click Distance header again to sort desc (Eve 15.0 km then Dave 10.4 km)
    fireEvent.click(distanceHeader);
    expect(screen.getByTestId('table-other-row-0')).toHaveTextContent('Eve Eve');
    expect(screen.getByTestId('table-other-row-1')).toHaveTextContent('Dave Dave');
  });

  it('triggers onSelect callback when Select button is clicked', () => {
    const onSelect = vi.fn();
    render(<RankedTechTable {...defaultProps} onSelect={onSelect} />);

    // Click select on Alice Gold (pinned row 1)
    fireEvent.click(screen.getByTestId('table-pinned-select-1'));
    expect(onSelect).toHaveBeenCalledWith(1);

    // Click select on Dave Dave (other row 0)
    fireEvent.click(screen.getByTestId('table-other-select-0'));
    expect(onSelect).toHaveBeenCalledWith(4);
  });

  it('triggers onAssign callback when Assign button is clicked', () => {
    const onAssign = vi.fn();
    render(<RankedTechTable {...defaultProps} onAssign={onAssign} />);

    // Click assign on Bob Silver (pinned row 2)
    fireEvent.click(screen.getByTestId('table-pinned-assign-2'));
    expect(onAssign).toHaveBeenCalledWith(2);

    // Click assign on Eve Eve (other row 1)
    fireEvent.click(screen.getByTestId('table-other-assign-1'));
    expect(onAssign).toHaveBeenCalledWith(5);
  });

  it('triggers onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<RankedTechTable {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('panel-close-btn'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('is accessible with correct ARIA roles and labels', () => {
    render(<RankedTechTable {...defaultProps} />);
    
    // Table has correct role and label
    const table = screen.getByRole('table', { name: /Technician candidate pool/i });
    expect(table).toBeInTheDocument();

    // Headers have sortable attributes
    const scoreHeader = screen.getByRole('columnheader', { name: /Score/i });
    expect(scoreHeader).toHaveAttribute('aria-sort');

    // Select buttons have labels
    expect(screen.getByRole('button', { name: /Select Alice Gold for Job 101/i })).toBeInTheDocument();
  });
});
