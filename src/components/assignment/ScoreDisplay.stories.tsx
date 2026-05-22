import type { Meta, StoryObj } from '@storybook/react';
import ScoreDisplay, { CompactScorePanel } from './ScoreDisplay';

/* ─── Meta ─────────────────────────────────────────────────────────────── */

const meta: Meta<typeof ScoreDisplay> = {
  title: 'Assignment/ScoreDisplay',
  component: ScoreDisplay,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'Displays the composite score and individual score breakdown for a ranked technician. ' +
          'Use `variant="compact"` for inline table rows, and the default `"full"` variant for modal/sidebar contexts.',
      },
    },
  },
  argTypes: {
    composite_score: { control: { type: 'range', min: 0, max: 100, step: 0.1 } },
    proximity_score: { control: { type: 'range', min: 0, max: 100, step: 0.1 } },
    skill_score:     { control: { type: 'range', min: 0, max: 100, step: 0.1 } },
    workload_score:  { control: { type: 'range', min: 0, max: 100, step: 0.1 } },
    distance_km:     { control: { type: 'number', min: 0, step: 0.1 } },
    active_jobs:     { control: { type: 'number', min: 0 } },
    max_capacity:    { control: { type: 'number', min: 1 } },
    is_top_3:        { control: 'boolean' },
    variant:         { control: 'radio', options: ['full', 'compact'] },
  },
};

export default meta;
type Story = StoryObj<typeof ScoreDisplay>;

/* ─── Stories ───────────────────────────────────────────────────────────── */

/** Excellent score — green theme, top recommended. */
export const HighScore: Story = {
  name: 'High Score (Top Recommended)',
  args: {
    composite_score: 92.5,
    proximity_score: 95.0,
    skill_score:     88.5,
    workload_score:  94.0,
    distance_km:     4.2,
    active_jobs:     1,
    max_capacity:    4,
    is_top_3:        true,
  },
};

/** Moderate score — amber/yellow theme. */
export const MediumScore: Story = {
  name: 'Medium Score',
  args: {
    composite_score: 65.2,
    proximity_score: 60.5,
    skill_score:     75.0,
    workload_score:  55.0,
    distance_km:     15.7,
    active_jobs:     3,
    max_capacity:    5,
    is_top_3:        false,
  },
};

/** Low score — red theme, high distance and near capacity. */
export const LowScore: Story = {
  name: 'Low Score',
  args: {
    composite_score: 35.8,
    proximity_score: 25.0,
    skill_score:     40.5,
    workload_score:  45.0,
    distance_km:     45.2,
    active_jobs:     6,
    max_capacity:    6,
    is_top_3:        false,
  },
};

/** Boundary: exactly 70 (medium threshold). */
export const BoundaryAt70: Story = {
  name: 'Boundary: score = 70.0 (medium)',
  args: {
    composite_score: 70.0,
    proximity_score: 70.0,
    skill_score:     70.0,
    workload_score:  70.0,
    distance_km:     10.0,
    active_jobs:     2,
    max_capacity:    5,
    is_top_3:        false,
  },
};

/** Boundary: exactly 40 (low threshold). */
export const BoundaryAt40: Story = {
  name: 'Boundary: score = 40.0 (medium/low edge)',
  args: {
    composite_score: 40.0,
    proximity_score: 40.0,
    skill_score:     40.0,
    workload_score:  40.0,
    distance_km:     25.0,
    active_jobs:     4,
    max_capacity:    5,
    is_top_3:        false,
  },
};

/** Edge: score = 0. */
export const ZeroScore: Story = {
  name: 'Edge: score = 0',
  args: {
    composite_score: 0,
    proximity_score: 0,
    skill_score:     0,
    workload_score:  0,
    distance_km:     100.0,
    active_jobs:     5,
    max_capacity:    5,
    is_top_3:        false,
  },
};

/** Edge: score = 100. */
export const PerfectScore: Story = {
  name: 'Edge: score = 100',
  args: {
    composite_score: 100,
    proximity_score: 100,
    skill_score:     100,
    workload_score:  100,
    distance_km:     0.5,
    active_jobs:     0,
    max_capacity:    5,
    is_top_3:        true,
  },
};

/** Mobile viewport — stacks gauge above breakdown. */
export const MobileLayout: Story = {
  name: 'Mobile Layout (320px)',
  args: {
    ...HighScore.args,
    is_top_3: true,
  },
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
  },
};

/** Dark mode — slate-950 background. */
export const DarkMode: Story = {
  name: 'Dark Mode',
  args: {
    ...HighScore.args,
    is_top_3: true,
  },
  decorators: [
    (Story) => (
      <div className="dark p-6 bg-slate-950 rounded-2xl">
        <Story />
      </div>
    ),
  ],
};

/** Compact inline variant for table rows. */
export const CompactVariant: Story = {
  name: 'Compact Variant (table-inline)',
  args: {
    composite_score: 78.4,
    proximity_score: 85.0,
    skill_score:     72.0,
    workload_score:  78.0,
    distance_km:     8.9,
    active_jobs:     2,
    max_capacity:    4,
    is_top_3:        true,
    variant:         'compact',
  },
  parameters: {
    layout: 'padded',
  },
};

/** Three compact panels side-by-side, ranking view. */
export const RankedList: Story = {
  name: 'Ranked List (3 Technicians)',
  render: () => (
    <div className="space-y-4 w-[560px]">
      <CompactScorePanel
        composite_score={88.5}
        proximity_score={92.0}
        skill_score={85.0}
        workload_score={88.0}
        distance_km={3.1}
        active_jobs={1}
        max_capacity={4}
        is_top_3={true}
      />
      <CompactScorePanel
        composite_score={74.2}
        proximity_score={70.0}
        skill_score={80.0}
        workload_score={73.0}
        distance_km={11.5}
        active_jobs={2}
        max_capacity={4}
        is_top_3={false}
      />
      <CompactScorePanel
        composite_score={58.0}
        proximity_score={55.0}
        skill_score={60.0}
        workload_score={60.0}
        distance_km={22.3}
        active_jobs={3}
        max_capacity={4}
        is_top_3={false}
      />
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};
