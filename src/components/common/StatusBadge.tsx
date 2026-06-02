import React from "react";
import {
  CheckCircle,
  Clock,
  UserMinus,
  Navigation,
  MapPin,
  Coffee,
  AlertTriangle,
  Briefcase,
  LucideIcon,
} from "lucide-react";
import "./StatusBadge.css";

export interface StatusBadgeProps {
  status: "AVAILABLE" | "BUSY" | "ASSIGNED" | "OFFLINE" | "EN_ROUTE" | "ON_SITE" | "ON_BREAK" | "SUSPENDED";
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  pulse?: boolean;
  className?: string;
  "data-testid"?: string;
}

interface StatusConfigItem {
  label: string;
  icon: LucideIcon;
  description: string;
  defaultPulse?: boolean;
}

const STATUS_CONFIG: Record<StatusBadgeProps["status"], StatusConfigItem> = {
  AVAILABLE: {
    label: "Available",
    icon: CheckCircle,
    description: "Technician is available for assignment",
  },
  BUSY: {
    label: "Busy",
    icon: Clock,
    description: "Technician is currently assigned or occupied",
  },
  ASSIGNED: {
    label: "Assigned",
    icon: Briefcase,
    description: "Technician is currently assigned to a job",
  },
  OFFLINE: {
    label: "Offline",
    icon: UserMinus,
    description: "Technician is not currently online",
  },
  EN_ROUTE: {
    label: "En Route",
    icon: Navigation,
    description: "Technician is travelling to job location",
    defaultPulse: true,
  },
  ON_SITE: {
    label: "On Site",
    icon: MapPin,
    description: "Technician has reached the job location",
  },
  ON_BREAK: {
    label: "On Break",
    icon: Coffee,
    description: "Technician is temporarily unavailable",
  },
  SUSPENDED: {
    label: "Suspended",
    icon: AlertTriangle,
    description: "Technician is blocked from assignment",
  },
};

export const TECHNICIAN_STATUSES = Object.keys(STATUS_CONFIG) as StatusBadgeProps["status"][];

export default function StatusBadge({
  status,
  size = "md",
  showIcon = true,
  pulse,
  className = "",
  "data-testid": dataTestId,
}: StatusBadgeProps) {
  // Convert status to uppercase to match STATUS_CONFIG keys and gracefully handle lower/mixed-case
  const lookupStatus = (status || "").toUpperCase() as StatusBadgeProps["status"];
  const config = STATUS_CONFIG[lookupStatus] ?? STATUS_CONFIG["OFFLINE"];
  const label = config.label;
  const desc = config.description;
  const IconComponent = config.icon;

  // Pulse: use prop if explicitly provided, fall back to per-status default
  const shouldPulse = pulse !== undefined ? pulse : (config.defaultPulse ?? false);

  const classes = [
    "sb-badge",
    `sb-${size}`,
    `sb-${lookupStatus}`,
    shouldPulse ? "sb-pulse" : "",
    className,
  ].filter(Boolean).join(" ");

  const iconSize = size === "sm" ? 11 : size === "lg" ? 15 : 13;

  return (
    <span
      className={classes}
      role="status"
      aria-label={`${label} — ${desc}`}
      tabIndex={0}
      data-testid={dataTestId}
    >
      {/* Colored dot — always rendered for a11y (not color-only) */}
      <span className="sb-dot" aria-hidden="true" data-testid="status-badge-dot" />

      {/* Optional icon */}
      {showIcon && IconComponent && (
        <span className="sb-icon" aria-hidden="true" data-testid="status-badge-icon">
          <IconComponent size={iconSize} />
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
