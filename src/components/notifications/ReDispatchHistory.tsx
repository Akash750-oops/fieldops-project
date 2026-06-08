import React, { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  useReactTable, 
  getCoreRowModel, 
  getFilteredRowModel, 
  getSortedRowModel, 
  flexRender, 
  createColumnHelper 
} from "@tanstack/react-table";
import { 
  X, 
  Download, 
  Filter, 
  AlertTriangle, 
  AlertOctagon, 
  Clock, 
  TrendingUp, 
  RefreshCw, 
  History,
  FileText,
  Truck,
  Layers,
  Shield,
  Info,
  ChevronDown,
  UserCheck,
  AlertCircle,
  Copy,
  Check
} from "lucide-react";
import { io, Socket } from "socket.io-client";
import "./notifications.css";

interface RedispatchAttempt {
  id: number;
  job_id: number;
  attempt_number: number;
  technician_id?: number | null;
  technician_name?: string | null;
  event_type: string; // rejection, timeout, offline, pending
  reason?: string | null;
  queue_position: number;
  next_dispatch_eta?: string | null;
  created_at: string;
}

import ForceAssignButton from "./ForceAssignButton";
import { getJob } from "../../services/planningService";
import { useToast } from "../../hooks/useToast";

interface ReDispatchHistoryProps {
  jobId: number;
  jobTitle: string;
  onClose: () => void;
  onManualAssign?: (jobId: number, techId: number) => Promise<void>;
  technicians?: Array<{ technician_id: number; technician_name: string; technician_skill: string }>;
  onForceAssignClick?: (jobId: number, jobTitle: string) => void;
  currentUserRole?: string;
}

const columnHelper = createColumnHelper<RedispatchAttempt>();

export default function ReDispatchHistory({
  jobId,
  jobTitle,
  onClose,
  onManualAssign,
  technicians = [],
  onForceAssignClick,
  currentUserRole = "dispatcher"
}: ReDispatchHistoryProps) {
  const [history, setHistory] = useState<RedispatchAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterReason, setFilterReason] = useState<string>("all");
  const [selectedTechId, setSelectedTechId] = useState<string>("");
  const [assigning, setAssigning] = useState(false);
  const [jobDetail, setJobDetail] = useState<any>(null);
  const [isJobDetailsExpanded, setIsJobDetailsExpanded] = useState(true);
  const [isDispatchStatusExpanded, setIsDispatchStatusExpanded] = useState(true);
  const [isQueueInfoExpanded, setIsQueueInfoExpanded] = useState(true);
  const [copiedJobId, setCopiedJobId] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    const fetchJobDetail = async () => {
      try {
        const res = await getJob(jobId);
        if (res && res.data) {
          setJobDetail(res.data);
        }
      } catch (err) {
        console.warn("Failed to fetch job details in ReDispatchHistory", err);
      }
    };
    fetchJobDetail();
  }, [jobId]);

  // Fetch history from backend
  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`http://localhost:8000/jobs/${jobId}/redispatch-history`);
      if (!response.ok) throw new Error("Failed to load re-dispatch history");
      const data = await response.json();
      setHistory(data);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();

    // Setup Socket.IO listener for real-time updates
    const socket: Socket = io("http://localhost:8000", {
      transports: ["websocket", "polling"]
    });

    socket.on("redispatch:alert", (data: any) => {
      if (data.job_id === jobId) {
        // Play subtle beep sound when new attempt is registered
        try {
          const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          const oscillator = audioCtx.createOscillator();
          const gainNode = audioCtx.createGain();
          oscillator.connect(gainNode);
          gainNode.connect(audioCtx.destination);
          oscillator.type = "sine";
          oscillator.frequency.setValueAtTime(440, audioCtx.currentTime); // A4
          gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
          oscillator.start();
          gainNode.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.3);
          oscillator.stop(audioCtx.currentTime + 0.3);
        } catch (e) {
          console.warn("Failed to play audio notification", e);
        }

        // Fetch fresh history from server
        fetchHistory();
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [jobId]);

  // Derived stats from timeline
  const attemptCount = history.length;
  const currentQueuePosition = history.length > 0 ? history[history.length - 1].queue_position : 1;
  const nextDispatchETA = history.length > 0 ? history[history.length - 1].next_dispatch_eta : null;

  // Filter history by reason type
  const filteredData = useMemo(() => {
    if (filterReason === "all") return history;
    return history.filter(item => item.event_type.toLowerCase() === filterReason.toLowerCase());
  }, [history, filterReason]);

  // Column definitions for TanStack Table
  const columns = useMemo(() => [
    columnHelper.accessor("attempt_number", {
      header: "Attempt",
      cell: info => <span className="font-semibold text-slate-800">#{info.getValue()}</span>
    }),
    columnHelper.accessor("event_type", {
      header: "Type",
      cell: info => {
        const type = info.getValue().toLowerCase();
        let bg = "bg-gray-100 text-gray-700";
        if (type === "rejection") bg = "bg-rose-100 text-rose-700 border border-rose-200";
        if (type === "timeout") bg = "bg-amber-100 text-amber-700 border border-amber-200";
        if (type === "offline") bg = "bg-slate-100 text-slate-700 border border-slate-200";
        return (
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${bg}`}>
            {info.getValue()}
          </span>
        );
      }
    }),
    columnHelper.accessor("technician_name", {
      header: "Technician",
      cell: info => info.getValue() || <span className="text-slate-400 italic">Searching...</span>
    }),
    columnHelper.accessor("reason", {
      header: "Reason",
      cell: info => <span className="text-slate-600 font-medium">{info.getValue() || "-"}</span>
    }),
    columnHelper.accessor("created_at", {
      header: "Time",
      cell: info => new Date(info.getValue()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    })
  ], []);

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel()
  });

  // CSV Export Utility
  const handleExportCSV = () => {
    if (history.length === 0) return;
    const headers = ["Attempt", "Event Type", "Technician Name", "Reason", "Queue Position", "ETA", "Timestamp"];
    const rows = history.map(item => [
      item.attempt_number,
      item.event_type,
      item.technician_name || "",
      item.reason || "",
      item.queue_position,
      item.next_dispatch_eta || "",
      item.created_at
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(e => e.map(val => `"${val}"`).join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `job_${jobId}_redispatch_history.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleManualAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTechId || !onManualAssign) return;
    try {
      setAssigning(true);
      setError("");
      await onManualAssign(jobId, parseInt(selectedTechId));
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to manually assign job");
    } finally {
      setAssigning(false);
    }
  };

  const isCompleted = jobDetail?.status?.toLowerCase() === "completed";
  const attemptsSubtitle = attemptCount === 0 
    ? "No dispatch attempts yet" 
    : `${attemptCount} of 5 attempts made`;
  
  const queueSubtitle = isCompleted
    ? "Job completed"
    : currentQueuePosition === 1
      ? "Top priority in queue"
      : `Position #${currentQueuePosition} in queue`;

  const etaSubtitle = isCompleted
    ? "Job is completed"
    : nextDispatchETA
      ? "Automatic search scheduled"
      : "No automatic search active";

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 16 }}
        transition={{ type: "spring", duration: 0.4, bounce: 0.15 }}
        className="rdh-modal-container"
        style={{ fontFamily: "'Inter', sans-serif" }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-dialog-title"
      >
        {/* ── Header ── */}
        <div className="rdh-header">
          <div className="flex items-center gap-4">
            <div className="rdh-header-icon-box">
              <History className="w-5 h-5 text-[#2563eb]" />
            </div>
            <div className="text-left">
              <h2 id="history-dialog-title" className="rdh-header-title">Dispatch History</h2>
              <p className="rdh-header-subtitle">
                {jobDetail ? `${jobDetail.service_type} - ${jobDetail.customer_name}` : jobTitle} (ID: #{jobId})
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="rdh-header-close-btn"
            aria-label="Close dialog"
          >
            <X size={15} />
          </button>
        </div>

        {/* ── Modal Body (No vertical scroll on wrapper itself) ── */}
        <div className="rdh-body">
          <div className="rdh-body-inner">

            {/* KPI row */}
            <div className="rdh-summary-row">
              {/* Attempts */}
              <div className="rdh-summary-card">
                <div className="rdh-summary-icon-box bg-emerald-50 text-emerald-600">
                  <FileText size={18} className="text-emerald-600" />
                </div>
                <div className="min-w-0">
                  <div className="rdh-summary-label">Attempts</div>
                  <div className="rdh-summary-value flex items-baseline gap-1">
                    <span className="text-xl font-extrabold text-slate-900">{attemptCount}</span>
                    <span className="text-slate-400 text-[11px] font-semibold">/ 5 max</span>
                  </div>
                  <div className="rdh-summary-subtitle">{attemptsSubtitle}</div>
                </div>
              </div>

              {/* Queue Position */}
              <div className="rdh-summary-card">
                <div className="rdh-summary-icon-box bg-blue-50 text-blue-600">
                  <TrendingUp size={18} className="text-blue-600" />
                </div>
                <div className="min-w-0">
                  <div className="rdh-summary-label">Queue Position</div>
                  <div className="rdh-summary-value flex items-baseline gap-1">
                    <span className="text-xl font-extrabold text-slate-900">#{currentQueuePosition}</span>
                    <span className="text-slate-400 text-[11px] font-semibold">in line</span>
                  </div>
                  <div className="rdh-summary-subtitle">{queueSubtitle}</div>
                </div>
              </div>

              {/* Next Dispatch ETA */}
              <div className="rdh-summary-card">
                <div className="rdh-summary-icon-box bg-violet-50 text-violet-600">
                  <Clock size={18} className="text-violet-600" />
                </div>
                <div className="min-w-0">
                  <div className="rdh-summary-label">Next Dispatch ETA</div>
                  <div className="rdh-summary-value text-sm font-bold text-slate-800 truncate">
                    {nextDispatchETA
                      ? new Date(nextDispatchETA).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : <span className="text-slate-700">No pending search</span>}
                  </div>
                  <div className="rdh-summary-subtitle">{etaSubtitle}</div>
                </div>
              </div>
            </div>

            {/* ── Two-column body ── */}
            <div className="rdh-main-layout">
              {/* Left Column: Event History */}
              <div className="rdh-left-column text-left">
                <div className="rdh-event-history-card">
                  {/* Card header */}
                  <div className="rdh-event-history-header">
                    <h3 className="rdh-event-history-title">Event History</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={fetchHistory}
                        className="p-1.5 border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition duration-150"
                        title="Refresh"
                        aria-label="Refresh history"
                      >
                        <RefreshCw size={13} />
                      </button>
                      <button
                        onClick={handleExportCSV}
                        disabled={history.length === 0}
                        className="flex items-center gap-1.5 py-1.5 px-3 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-[11px] font-bold transition duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
                        aria-label="Export history to CSV"
                      >
                        <Download size={12} className="text-slate-500" />
                        Export CSV
                      </button>
                    </div>
                  </div>

                  {/* Filter row */}
                  <div className="rdh-event-history-filter-bar">
                    <div className="relative inline-block">
                      <select
                        value={filterReason}
                        onChange={(e) => setFilterReason(e.target.value)}
                        className="appearance-none bg-slate-50 border border-slate-200 rounded-lg py-1.5 pl-3 pr-7 text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                        aria-label="Filter events by type"
                      >
                        <option value="all">All Events</option>
                        <option value="rejection">Rejections Only</option>
                        <option value="timeout">Timeouts Only</option>
                        <option value="offline">Offline Only</option>
                      </select>
                      <ChevronDown size={11} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    </div>
                  </div>

                  {/* Error */}
                  {error && (
                    <div className="mx-5 mt-4 p-3 bg-rose-50 text-rose-700 rounded-lg border border-rose-100 flex items-start gap-2 text-xs font-semibold">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* Content */}
                  <div className="flex-1 flex flex-col min-h-0">
                    {loading ? (
                      <div className="flex-1 flex flex-col items-center justify-center py-16">
                        <div className="w-7 h-7 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
                        <p className="text-[11px] text-slate-400 font-semibold mt-3">Loading history…</p>
                      </div>
                    ) : filteredData.length === 0 ? (
                      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                        <div className="w-24 h-24 bg-blue-50/60 rounded-full flex items-center justify-center mb-5">
                          <svg width="52" height="52" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M19 3H5C3.896 3 3 3.896 3 5V19C3 20.104 3.896 21 5 21H19C20.104 21 21 20.104 21 19V5C21 3.896 20.104 3 19 3Z" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M9 7H15" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round"/>
                            <path d="M9 11H13" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round"/>
                            <path d="M9 15H11" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round"/>
                            <circle cx="16" cy="16" r="4" fill="white" stroke="#3b82f6" strokeWidth="2"/>
                            <path d="M19 19L22 22" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round"/>
                          </svg>
                        </div>
                        <p className="text-sm text-slate-700 font-extrabold">No re-dispatch history logged</p>
                        <p className="text-[11px] text-slate-500 mt-1.5 max-w-[280px] text-center font-medium leading-relaxed">
                          {jobDetail
                            ? isCompleted
                              ? "This job was completed successfully without any re-dispatch attempts."
                              : "This job is currently not completed and has no failed dispatch attempts."
                            : "This job is either freshly queued or was assigned without attempts."
                          }
                        </p>
                      </div>
                    ) : (
                      <div className="rdh-table-container scrollbar-thin">
                        <table className="min-w-full divide-y divide-slate-100 text-left text-xs">
                          <thead className="bg-slate-50 uppercase tracking-wider sticky top-0 z-10">
                            {table.getHeaderGroups().map(headerGroup => (
                              <tr key={headerGroup.id}>
                                {headerGroup.headers.map(header => (
                                  <th key={header.id} className="px-4 py-3 text-[10px] font-extrabold text-slate-400">
                                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                                  </th>
                                ))}
                              </tr>
                            ))}
                          </thead>
                          <tbody className="divide-y divide-slate-50 text-slate-700 font-semibold">
                            {table.getRowModel().rows.map(row => (
                              <tr key={row.id} className="hover:bg-slate-50/60 transition duration-100">
                                {row.getVisibleCells().map(cell => (
                                  <td key={cell.id} className="px-4 py-3">
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Bottom info banner */}
                  <div className="rdh-bottom-info">
                    <Info size={13} className="text-blue-500 shrink-0" />
                    <span>
                      {isCompleted
                        ? "This job is completed. Re-dispatch events are closed."
                        : "Events will appear here once re-dispatch attempts are made."
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Detail Cards */}
              <div className="rdh-right-column scrollbar-thin">
                {/* Card 1: Job Details */}
                <div className="rdh-details-card">
                  <div className="rdh-details-card-header" onClick={() => setIsJobDetailsExpanded(!isJobDetailsExpanded)}>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-emerald-50 flex items-center justify-center shrink-0">
                        <FileText size={13} className="text-emerald-600" />
                      </div>
                      <h4 className="rdh-details-card-title">Job Details</h4>
                    </div>
                    <button className="text-slate-400 hover:text-slate-600 transition-colors" type="button" aria-label="Toggle details">
                      <ChevronDown size={14} className={`transform transition-transform duration-200 ${isJobDetailsExpanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                  {isJobDetailsExpanded && (
                    <div className="rdh-detail-grid">
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Job</span>
                        <span className="rdh-detail-value">
                          {jobDetail ? `${jobDetail.service_type} - ${jobDetail.customer_name}` : jobTitle}
                        </span>
                      </div>
                      <div className="rdh-detail-row items-center">
                        <span className="rdh-detail-label">Job ID</span>
                        <div className="rdh-detail-value flex items-center gap-1.5">
                          <span>#{jobId}</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(String(jobId));
                              setCopiedJobId(true);
                              setTimeout(() => setCopiedJobId(false), 1500);
                              addToast({
                                type: "success",
                                title: "Copied!",
                                message: `Job ID #${jobId} copied to your clipboard`,
                                autoDismiss: 4000,
                                priority: "normal",
                              });
                            }}
                            className="p-1 hover:bg-slate-100 rounded transition-colors text-slate-400 hover:text-slate-600 cursor-pointer"
                            title={copiedJobId ? "Copied!" : "Copy Job ID"}
                            aria-label={`Copy Job ID ${jobId}`}
                          >
                            {copiedJobId ? <Check size={11} className="text-emerald-600" /> : <Copy size={11} />}
                          </button>
                        </div>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Created</span>
                        <span className="rdh-detail-value">
                          {jobDetail?.created_at ? new Date(jobDetail.created_at).toLocaleString([], { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : "—"}
                        </span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Priority</span>
                        <span className="rdh-detail-value flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${['high','critical'].includes((jobDetail?.priority || '').toLowerCase()) ? 'bg-orange-500' : 'bg-slate-400'}`} />
                          <span>{(jobDetail?.priority || '—').toUpperCase()}</span>
                        </span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Service Line</span>
                        <span className="rdh-detail-value">{jobDetail?.service_type || "—"}</span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Address</span>
                        <span className="rdh-detail-value">{jobDetail?.location || "—"}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card 2: Current Dispatch Status */}
                <div className="rdh-details-card">
                  <div className="rdh-details-card-header" onClick={() => setIsDispatchStatusExpanded(!isDispatchStatusExpanded)}>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-blue-50 flex items-center justify-center shrink-0">
                        <Truck size={13} className="text-blue-600" />
                      </div>
                      <h4 className="rdh-details-card-title">Current Dispatch Status</h4>
                    </div>
                    <button className="text-slate-400 hover:text-slate-600 transition-colors" type="button" aria-label="Toggle status">
                      <ChevronDown size={14} className={`transform transition-transform duration-200 ${isDispatchStatusExpanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                  {isDispatchStatusExpanded && (
                    <div className="rdh-detail-grid">
                      <div className="rdh-detail-row items-center">
                        <span className="rdh-detail-label">Status</span>
                        <div className="rdh-detail-value">
                          {(() => {
                            const s = (jobDetail?.status || 'queued').toLowerCase();
                            const cfg: Record<string,string> = {
                              completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
                              assigned:  'bg-blue-50 text-blue-700 border-blue-200',
                              queued:    'bg-amber-50 text-amber-700 border-amber-200',
                              active:    'bg-amber-50 text-amber-700 border-amber-200',
                              pending:   'bg-amber-50 text-amber-700 border-amber-200',
                              'in progress': 'bg-sky-50 text-sky-700 border-sky-200',
                              en_route:  'bg-sky-50 text-sky-700 border-sky-200',
                              on_site:   'bg-sky-50 text-sky-700 border-sky-200',
                              failed:    'bg-rose-50 text-rose-700 border-rose-200',
                              expired:   'bg-rose-50 text-rose-700 border-rose-200',
                            };
                            const cls = cfg[s] || 'bg-slate-100 text-slate-700 border-slate-200';
                            return (
                              <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wide ${cls}`}>
                                {jobDetail?.status || 'Queued'}
                              </span>
                            );
                          })()}
                        </div>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Dispatch Method</span>
                        <span className="rdh-detail-value">Automatic (PlanningAgent)</span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Attempts</span>
                        <span className="rdh-detail-value">{attemptCount} of 5</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card 3: Queue Information */}
                <div className="rdh-details-card">
                  <div className="rdh-details-card-header" onClick={() => setIsQueueInfoExpanded(!isQueueInfoExpanded)}>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-violet-50 flex items-center justify-center shrink-0">
                        <Layers size={13} className="text-violet-600" />
                      </div>
                      <h4 className="rdh-details-card-title">Queue Information</h4>
                    </div>
                    <button className="text-slate-400 hover:text-slate-600 transition-colors" type="button" aria-label="Toggle queue info">
                      <ChevronDown size={14} className={`transform transition-transform duration-200 ${isQueueInfoExpanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                  {isQueueInfoExpanded && (
                    <div className="rdh-detail-grid">
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Queue</span>
                        <span className="rdh-detail-value">{jobDetail?.service_type || "General"} Dispatch</span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Queue Position</span>
                        <span className="rdh-detail-value">#{currentQueuePosition} in line</span>
                      </div>
                      <div className="rdh-detail-row">
                        <span className="rdh-detail-label">Next ETA</span>
                        <span className="rdh-detail-value">
                          {nextDispatchETA ? new Date(nextDispatchETA).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "No pending search"}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card 4: Manual Intervention */}
                {onForceAssignClick && (
                  <div className="rdh-manual-card">
                    <div className="flex items-start gap-2.5 mb-3">
                      <div className="w-6 h-6 rounded-md bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
                        <Shield size={13} className="text-amber-700" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="rdh-manual-title">Manual Intervention / Override</h4>
                        <p className="rdh-manual-text">
                          Bypass automatic PlanningAgent rules and force-assign this job to any eligible technician with full justification.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onForceAssignClick(jobId, jobTitle)}
                      className="rdh-manual-btn"
                    >
                      <Shield size={13} />
                      Force Assign Job
                    </button>
                    <div className="mt-2.5 flex items-center gap-1.5 text-[10px] text-amber-700 font-semibold text-left">
                      <Info size={11} className="shrink-0" />
                      Manual overrides are logged and require justification.
                    </div>
                  </div>
                )}

                {/* Fallback: legacy manual assign */}
                {onManualAssign && !onForceAssignClick && (
                  <div className="rdh-details-card">
                    <div className="flex items-center gap-2 pb-2 border-b border-slate-100 mb-3">
                      <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center">
                        <UserCheck size={13} className="text-slate-600" />
                      </div>
                      <h4 className="rdh-details-card-title">Manual Assignment</h4>
                    </div>
                    <form onSubmit={handleManualAssignSubmit} className="space-y-3">
                      <select
                        id="tech-select"
                        value={selectedTechId}
                        onChange={(e) => setSelectedTechId(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-semibold text-slate-700"
                        aria-label="Select Technician to Force-Assign"
                        required
                      >
                        <option value="">-- Choose a Technician --</option>
                        {technicians.map(t => (
                          <option key={t.technician_id} value={t.technician_id}>
                            {t.technician_name} ({t.technician_skill})
                          </option>
                        ))}
                      </select>
                      <button
                        type="submit"
                        disabled={assigning || !selectedTechId}
                        className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {assigning ? "Assigning…" : "Manual Assign"}
                      </button>
                    </form>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* end scrollable body */}

      </motion.div>
    </div>
  );
}
