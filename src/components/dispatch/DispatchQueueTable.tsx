/**
 * DispatchQueueTable.tsx
 *
 * Real-time dispatch queue table with sortable columns, filter bar,
 * copy-to-clipboard Job IDs, live acceptance timers, and auto-refresh.
 * Built with @tanstack/react-table v8.
 */

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowUp,
  Copy,
  Check,
  ExternalLink,
  Eye,
  Inbox,
  Search,
  Loader2,
} from "lucide-react";

import { getDispatchQueue } from "../../services/dispatchQueueService";
import type { DispatchQueueJob } from "../../types/dispatchQueue";
import AcceptanceTimer from "./AcceptanceTimer";
import StatusBadge from "./StatusBadge";
import SLARiskBadge from "./SLARiskBadge";
import "./DispatchQueueTable.css";

/* ─── Helpers ──────────────────────────────────────────────────────────────── */

const getPriorityClass = (priority: string): string => {
  const p = (priority || "").toUpperCase();
  if (p === "CRITICAL" || p === "P1") return "dq-priority-critical";
  if (p === "HIGH" || p === "P2") return "dq-priority-high";
  if (p === "MEDIUM" || p === "P3") return "dq-priority-medium";
  if (p === "LOW" || p === "P4" || p === "P5") return "dq-priority-low";
  return "dq-priority-default";
};

const truncateId = (id: string): string => {
  if (id.length <= 8) return id;
  return `${id.slice(0, 4)}…${id.slice(-4)}`;
};

const getInitials = (name: string): string => {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
};

const googleMapsUrl = (address: string): string =>
  `https://maps.google.com/?q=${encodeURIComponent(address)}`;

/* ─── Copy Button ──────────────────────────────────────────────────────────── */

const CopyJobIdButton = ({ jobId }: { jobId: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(jobId).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <button
      className={`dq-copy-btn ${copied ? "copied" : ""}`}
      onClick={handleCopy}
      title={copied ? "Copied!" : "Copy full Job ID"}
      aria-label={`Copy Job ID ${jobId}`}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
};

/* ─── Skeleton ─────────────────────────────────────────────────────────────── */

const SkeletonRows = () => (
  <>
    {Array.from({ length: 6 }).map((_, i) => (
      <tr key={i} className="dq-skeleton-row">
        <td>
          <div className="dq-skeleton-bar w-20" />
        </td>
        <td>
          <div className="dq-skeleton-bar w-28" />
        </td>
        <td>
          <div className="dq-skeleton-bar w-36" />
        </td>
        <td>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div className="dq-skeleton-avatar" />
            <div className="dq-skeleton-bar w-20" />
          </div>
        </td>
        <td>
          <div className="dq-skeleton-bar w-16" />
        </td>
        <td>
          <div className="dq-skeleton-bar w-16" />
        </td>
        <td>
          <div className="dq-skeleton-bar w-16" />
        </td>
        <td>
          <div className="dq-skeleton-bar w-16" />
        </td>
      </tr>
    ))}
  </>
);

/* ─── Main Component ───────────────────────────────────────────────────────── */

interface DispatchQueueTableProps {
  /** Callback when a job count changes (for tab badge) */
  onCountChange?: (count: number) => void;
}

const DispatchQueueTable = ({ onCountChange }: DispatchQueueTableProps) => {
  // Data
  const [jobs, setJobs] = useState<DispatchQueueJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [searchText, setSearchText] = useState("");

  // Table
  const [sorting, setSorting] = useState<SortingState>([]);

  // Auto-refresh interval
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchQueue = useCallback(
    async (isRefresh = false) => {
      try {
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        const response = await getDispatchQueue({
          ...(statusFilter && { status: statusFilter }),
          ...(priorityFilter && { priority: priorityFilter }),
          limit: 50,
        });

        setJobs(response.data);
        onCountChange?.(response.data.length);
      } catch (err) {
        console.error("Dispatch queue fetch error:", err);
        setError("Failed to load dispatch queue. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [statusFilter, priorityFilter, onCountChange]
  );

  // Initial fetch + filter changes
  useEffect(() => {
    fetchQueue(false);
  }, [fetchQueue]);

  // Auto-refresh every 30s
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      fetchQueue(true);
    }, 30000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchQueue]);

  // ── Filtered data (client-side text search) ───────────────────────────────

  const filteredJobs = useMemo(() => {
    if (!searchText.trim()) return jobs;
    const q = searchText.toLowerCase().trim();
    return jobs.filter(
      (job) =>
        job.job_id.toLowerCase().includes(q) ||
        job.customer.toLowerCase().includes(q) ||
        job.location.toLowerCase().includes(q) ||
        job.title.toLowerCase().includes(q) ||
        (job.technician?.name || "").toLowerCase().includes(q)
    );
  }, [jobs, searchText]);

  // ── Column Definitions ────────────────────────────────────────────────────

  const columns = useMemo<ColumnDef<DispatchQueueJob>[]>(
    () => [
      {
        accessorKey: "job_id",
        header: "Job ID",
        size: 120,
        cell: ({ row }) => (
          <div className="dq-jobid-cell">
            <span className="dq-jobid-text" title={row.original.job_id}>
              {truncateId(row.original.job_id)}
            </span>
            <CopyJobIdButton jobId={row.original.job_id} />
          </div>
        ),
      },
      {
        accessorKey: "customer",
        header: "Customer",
        size: 170,
        cell: ({ row }) => (
          <div>
            <div className="dq-customer-name">{row.original.customer}</div>
            {row.original.title && (
              <div className="dq-customer-title">{row.original.title}</div>
            )}
          </div>
        ),
      },
      {
        accessorKey: "location",
        header: "Location",
        size: 200,
        cell: ({ row }) => (
          <div className="dq-location-cell">
            <span className="dq-location-text">{row.original.location}</span>
            <a
              href={googleMapsUrl(row.original.location)}
              target="_blank"
              rel="noopener noreferrer"
              className="dq-map-link"
              title="Open in Maps"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink size={12} />
            </a>
          </div>
        ),
      },
      {
        id: "technician",
        header: "Technician",
        size: 160,
        accessorFn: (row) => row.technician?.name || "",
        cell: ({ row }) => {
          const tech = row.original.technician;
          if (!tech) {
            return <span className="dq-unassigned">Unassigned</span>;
          }
          const statusClass = (tech.status || "").toLowerCase();
          return (
            <div className="dq-tech-cell">
              <div className={`dq-tech-avatar ${statusClass}`}>
                {getInitials(tech.name)}
              </div>
              <div className="dq-tech-info">
                <span className="dq-tech-name">{tech.name}</span>
                <span className="dq-tech-status-text">{tech.status}</span>
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 110,
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "priority",
        header: "Priority",
        size: 90,
        cell: ({ row }) => (
          <span
            className={`dq-priority-badge ${getPriorityClass(row.original.priority)}`}
          >
            {row.original.priority || "—"}
          </span>
        ),
      },
      {
        id: "sla",
        header: "SLA Risk",
        size: 130,
        accessorFn: (row) => row.sla.minutes_remaining ?? 999999,
        cell: ({ row }) => {
          const deadline = row.original.sla.deadline;
          if (!deadline) return <span className="dq-unassigned">—</span>;
          return (
            <SLARiskBadge
              slaDeadline={deadline}
              showMinutes={true}
              enablePulse={true}
            />
          );
        },
      },
      {
        id: "timer",
        header: "Timer",
        size: 120,
        accessorFn: (row) => {
          // Sort key: remaining seconds (lower = more urgent = top)
          if (row.status !== "ASSIGNED") return 999999;
          if (row.acceptance_expires_at) {
            return Math.max(
              0,
              (new Date(row.acceptance_expires_at).getTime() - Date.now()) /
                1000
            );
          }
          if (row.assigned_at) {
            const expires =
              new Date(row.assigned_at).getTime() + 10 * 60 * 1000;
            return Math.max(0, (expires - Date.now()) / 1000);
          }
          return 999999;
        },
        cell: ({ row }) => (
          <AcceptanceTimer
            assignedAt={row.original.assigned_at}
            expiresAt={row.original.acceptance_expires_at}
            status={row.original.status}
          />
        ),
      },
    ],
    []
  );

  // ── Table Instance ────────────────────────────────────────────────────────

  const table = useReactTable({
    data: filteredJobs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <section className="dashboard-section" aria-label="Dispatch Queue">
      {/* Filter Bar */}
      <div className="dq-filter-bar">
        <select
          className="dq-filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
          id="dq-status-filter"
        >
          <option value="">All Statuses</option>
          <option value="QUEUED">Queued</option>
          <option value="ASSIGNED">Assigned</option>
          <option value="EN_ROUTE">En Route</option>
          <option value="ON_SITE">On Site</option>
        </select>

        <select
          className="dq-filter-select"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          aria-label="Filter by priority"
          id="dq-priority-filter"
        >
          <option value="">All Priorities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        <div className="dq-filter-search-wrap">
          <Search size={13} className="dq-filter-search-icon" />
          <input
            type="text"
            className="dq-filter-search"
            placeholder="Search jobs, customers, techs..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            aria-label="Search dispatch queue"
            id="dq-search-input"
          />
        </div>

        <span className="dq-filter-count">
          <strong>{filteredJobs.length}</strong> of {jobs.length} jobs
          {refreshing && (
            <span className="dq-refresh-indicator">
              <Loader2 size={11} className="animate-spin" />
              Refreshing
            </span>
          )}
        </span>
      </div>

      {/* Table Content */}
      <div className="section-content">
        {error ? (
          <div className="dq-empty">
            <div className="dq-empty-icon">
              <Inbox size={28} />
            </div>
            <h3>Could not load queue</h3>
            <p>{error}</p>
            <button
              className="refresh-icon-btn"
              style={{ marginTop: 12 }}
              onClick={() => fetchQueue(false)}
            >
              ⟳ Retry
            </button>
          </div>
        ) : (
          <div className="dq-table-wrap">
            <table className="dq-table" role="table">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => {
                      const isSorted = header.column.getIsSorted();
                      return (
                        <th
                          key={header.id}
                          onClick={header.column.getToggleSortingHandler()}
                          style={{ width: header.getSize() }}
                          aria-sort={
                            isSorted === "asc"
                              ? "ascending"
                              : isSorted === "desc"
                                ? "descending"
                                : "none"
                          }
                        >
                          <span className="dq-th-inner">
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            <ArrowUp
                              size={11}
                              className={`dq-sort-icon ${isSorted ? "active" : ""} ${isSorted === "desc" ? "desc" : ""}`}
                            />
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {loading ? (
                  <SkeletonRows />
                ) : table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length}>
                      <div className="dq-empty">
                        <div className="dq-empty-icon">
                          <Inbox size={28} />
                        </div>
                        <h3>
                          {searchText.trim()
                            ? "No jobs match your search"
                            : "No jobs in dispatch queue"}
                        </h3>
                        <p>
                          {searchText.trim()
                            ? "Try adjusting your filters or search terms."
                            : "All jobs have been dispatched or completed."}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      title="Click to view job details"
                      style={{ cursor: "pointer" }}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};

export default DispatchQueueTable;
