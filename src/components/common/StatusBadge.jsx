/**
 * StatusBadge.jsx
 * Reusable technician status badge component for FieldOps Commander.
 *
 * Props:
 *   status   — one of the 7 TECHNICIAN_STATUSES
 *   size     — 'sm' | 'md' (default) | 'lg'
 *   showIcon — boolean (default true)
 *   pulse    — boolean (default true for EN_ROUTE, false otherwise)
 *   className — extra CSS classes to merge
 *
 * Usage:
 *   <StatusBadge status="AVAILABLE" />
 *   <StatusBadge status="EN_ROUTE" size="lg" />
 *   <StatusBadge status="OFFLINE" showIcon={false} />
 *   <StatusBadge status="SUSPENDED" pulse />
 */

import React from "react";
import "./StatusBadge.css";

/* ── Status configuration map ───────────────────────────────────────────── */
const STATUS_CONFIG = {
  AVAILABLE: {
    label:       "Available",
    icon:        "",          
    description: "Technician is available for assignment",
  },
  BUSY: {
    label:       "Busy",
    icon:        "",          
    description: "Technician is currently assigned or occupied",
  },
  OFFLINE: {
    label:       "Offline",
    icon:        "",          
    description: "Technician is not currently online",
  },
  EN_ROUTE: {
    label:       "En Route",
    icon:        "",          
    description: "Technician is travelling to job location",
    defaultPulse: true,
  },
  ON_SITE: {
    label:       "On Site",
    icon:        "",          
    description: "Technician has reached the job location",
  },
  ON_BREAK: {
    label:       "On Break",
    icon:        "",          
    description: "Technician is temporarily unavailable",
  },
  SUSPENDED: {
    label:       "Suspended",
    icon:        "",          
    description: "Technician is blocked from assignment",
  },
};

/* ── Exported status list (useful for dropdowns, filters) ───────────────── */
export const TECHNICIAN_STATUSES = Object.keys(STATUS_CONFIG);

/**
 * StatusBadge
 */
export default function StatusBadge({
  status,
  size = "md",
  showIcon = true,
  pulse,          // undefined = use per-status default
  className = "",
}) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG["OFFLINE"];
  const label  = config.label;
  const desc   = config.description;

  // Pulse: use prop if explicitly provided, fall back to per-status default
  const shouldPulse = pulse !== undefined ? pulse : (config.defaultPulse ?? false);

  const classes = [
    "sb-badge",
    `sb-${size}`,
    `sb-${status}`,
    shouldPulse ? "sb-pulse" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <span
      className={classes}
      role="status"
      aria-label={`${label} — ${desc}`}
      tabIndex={0}
    >
      {/* Colored dot — always rendered for a11y (not color-only) */}
      <span className="sb-dot" aria-hidden="true" />

      {/* Optional icon */}
      {showIcon && (
        <span className="sb-icon" aria-hidden="true">
          {config.icon}
        </span>
      )}

      {/* Label text */}
      <span>{label}</span>

      {/* Tooltip */}
      <span className="sb-tooltip" role="tooltip">
        {desc}
      </span>
    </span>
  );
}
