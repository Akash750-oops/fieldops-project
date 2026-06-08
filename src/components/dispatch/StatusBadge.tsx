/**
 * StatusBadge.tsx
 * Color-coded status badge for dispatch queue rows.
 *
 * QUEUED   → gray
 * ASSIGNED → blue (subtle pulse)
 * EN_ROUTE → yellow
 * ON_SITE  → orange
 */

interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<
  string,
  { label: string; className: string }
> = {
  QUEUED: { label: "Queued", className: "dq-status-queued" },
  ASSIGNED: { label: "Assigned", className: "dq-status-assigned" },
  EN_ROUTE: { label: "En Route", className: "dq-status-enroute" },
  ON_SITE: { label: "On Site", className: "dq-status-onsite" },
};

const StatusBadge = ({ status }: StatusBadgeProps) => {
  const config = statusConfig[status] || {
    label: status,
    className: "dq-status-queued",
  };

  return (
    <span className={`dq-status-badge ${config.className}`}>
      <span className="dq-status-dot" />
      {config.label}
    </span>
  );
};

export default StatusBadge;
