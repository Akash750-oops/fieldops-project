import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import StatusBadge from "./StatusBadge";

/* ─── Meta ─────────────────────────────────────────────────────────────── */

const meta: Meta<typeof StatusBadge> = {
  title: "Common/StatusBadge",
  component: StatusBadge,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Displays technician status with customizable sizes, icons, tooltips, and pulse animations. Supports light and dark modes.",
      },
    },
  },
  argTypes: {
    status: {
      control: "select",
      options: ["AVAILABLE", "BUSY", "OFFLINE", "EN_ROUTE", "ON_SITE", "ON_BREAK", "SUSPENDED"],
    },
    size: {
      control: "radio",
      options: ["sm", "md", "lg"],
    },
    showIcon: { control: "boolean" },
    pulse: { control: "boolean" },
    className: { control: "text" },
  },
};

export default meta;
type Story = StoryObj<typeof StatusBadge>;

/* ─── Status Stories ────────────────────────────────────────────────────── */

export const Available: Story = {
  name: "Status: Available",
  args: {
    status: "AVAILABLE",
    size: "md",
    showIcon: true,
  },
};

export const Busy: Story = {
  name: "Status: Busy",
  args: {
    status: "BUSY",
    size: "md",
    showIcon: true,
  },
};

export const Offline: Story = {
  name: "Status: Offline",
  args: {
    status: "OFFLINE",
    size: "md",
    showIcon: true,
  },
};

export const EnRoute: Story = {
  name: "Status: En Route (Pulse)",
  args: {
    status: "EN_ROUTE",
    size: "md",
    showIcon: true,
  },
};

export const OnSite: Story = {
  name: "Status: On Site",
  args: {
    status: "ON_SITE",
    size: "md",
    showIcon: true,
  },
};

export const OnBreak: Story = {
  name: "Status: On Break",
  args: {
    status: "ON_BREAK",
    size: "md",
    showIcon: true,
  },
};

export const Suspended: Story = {
  name: "Status: Suspended",
  args: {
    status: "SUSPENDED",
    size: "md",
    showIcon: true,
  },
};

/* ─── Size Stories ──────────────────────────────────────────────────────── */

export const SmallSize: Story = {
  name: "Size: Small",
  args: {
    status: "AVAILABLE",
    size: "sm",
    showIcon: true,
  },
};

export const MediumSize: Story = {
  name: "Size: Medium (Default)",
  args: {
    status: "AVAILABLE",
    size: "md",
    showIcon: true,
  },
};

export const LargeSize: Story = {
  name: "Size: Large",
  args: {
    status: "AVAILABLE",
    size: "lg",
    showIcon: true,
  },
};

/* ─── Custom Control Stories ────────────────────────────────────────────── */

export const WithoutIcon: Story = {
  name: "Custom: Without Icon",
  args: {
    status: "AVAILABLE",
    size: "md",
    showIcon: false,
  },
};

export const CustomPulseDisabled: Story = {
  name: "Custom: En Route (Pulse Disabled)",
  args: {
    status: "EN_ROUTE",
    size: "md",
    showIcon: true,
    pulse: false,
  },
};

export const CustomPulseEnabled: Story = {
  name: "Custom: Available (Pulse Enabled)",
  args: {
    status: "AVAILABLE",
    size: "md",
    showIcon: true,
    pulse: true,
  },
};

/* ─── Layout & Theme Stories ────────────────────────────────────────────── */

export const DarkMode: Story = {
  name: "Theme: Dark Mode",
  args: {
    status: "AVAILABLE",
    size: "md",
    showIcon: true,
  },
  decorators: [
    (Story) => (
      <div className="dark p-6 bg-slate-950 rounded-2xl">
        <Story />
      </div>
    ),
  ],
};

export const AllStatusesList: Story = {
  name: "All Statuses List",
  render: () => (
    <div className="flex flex-col gap-3">
      <StatusBadge status="AVAILABLE" />
      <StatusBadge status="BUSY" />
      <StatusBadge status="OFFLINE" />
      <StatusBadge status="EN_ROUTE" />
      <StatusBadge status="ON_SITE" />
      <StatusBadge status="ON_BREAK" />
      <StatusBadge status="SUSPENDED" />
    </div>
  ),
};
