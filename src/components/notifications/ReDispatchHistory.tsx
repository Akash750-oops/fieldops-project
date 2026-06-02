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
  AlertCircle
} from "lucide-react";
import { io, Socket } from "socket.io-client";

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

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 16 }}
        transition={{ type: "spring", duration: 0.4, bounce: 0.15 }}
        className="w-full max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-100 flex flex-col max-h-[92vh]"
        style={{ fontFamily: "'Inter', sans-serif" }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-dialog-title"
      >
        {/* ── Header ── */}
        <div className="px-7 py-5 bg-white flex justify-between items-center border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center shadow-sm shrink-0">
              <History className="w-5 h-5 text-[#2563eb]" />
            </div>
            <div className="text-left">
              <h2 id="history-dialog-title" className="text-lg font-extrabold text-slate-900 tracking-tight leading-tight">Dispatch History</h2>
              <p className="text-slate-500 text-[11px] font-medium mt-0.5">
                {jobDetail ? `${jobDetail.service_type} - ${jobDetail.customer_name}` : jobTitle} (ID: #{jobId})
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-700 flex items-center justify-center transition duration-200 shrink-0"
            aria-label="Close dialog"
          >
            <X size={15} />
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="flex-1 overflow-y-auto bg-[#f5f7fa] min-h-0">
          <div className="p-6 pb-8 space-y-5">

            {/* KPI row */}
            <div className="grid grid-cols-3 gap-4">
              {/* Attempts */}
              <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex items-center gap-3 text-left">
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <FileText size={18} className="text-emerald-600" />
                </div>
                <div className="min-w-0">
                  <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Attempts</div>
                  <div className="mt-0.5 flex items-baseline gap-1">
                    <span className="text-xl font-extrabold text-slate-900">{attemptCount}</span>
                    <span className="text-slate-400 text-[11px] font-semibold">/ 5 max</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium mt-0.5">No dispatch attempts yet</div>
                </div>
              </div>

              {/* Queue Position */}
              <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex items-center gap-3 text-left">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                  <TrendingUp size={18} className="text-blue-600" />
                </div>
                <div className="min-w-0">
                  <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Queue Position</div>
                  <div className="mt-0.5 flex items-baseline gap-1">
                    <span className="text-xl font-extrabold text-slate-900">#{currentQueuePosition}</span>
                    <span className="text-slate-400 text-[11px] font-semibold">in line</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium mt-0.5">Current queue priority</div>
                </div>
              </div>

              {/* Next Dispatch ETA */}
              <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex items-center gap-3 text-left">
                <div className="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center shrink-0">
                  <Clock size={18} className="text-violet-600" />
                </div>
                <div className="min-w-0">
                  <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Next Dispatch ETA</div>
                  <div className="mt-0.5 text-sm font-bold text-slate-800 truncate">
                    {nextDispatchETA
                      ? new Date(nextDispatchETA).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : <span className="text-slate-700">No pending search</span>}
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium mt-0.5">Estimated time unavailable</div>
                </div>
              </div>
            </div>

            {/* ── Two-column body ── */}
            <div className="grid grid-cols-5 gap-5 items-start">

              {/* Left: Event History — 3/5 */}
              <div className="col-span-3 flex flex-col gap-0 text-left">
                <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden flex flex-col" style={{ minHeight: 380 }}>

                  {/* Card header */}
                  <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between shrink-0">
                    <h3 className="text-[10px] font-extrabold text-slate-600 uppercase tracking-widest">Event History</h3>
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
                        aria-label="Export to CSV"
                      >
                        <Download size={12} className="text-slate-500" />
                        Export CSV
                      </button>
                    </div>
                  </div>

                  {/* Filter row */}
                  <div className="px-5 py-3 border-b border-slate-50 shrink-0">
                    <div className="relative inline-block">
                      <select
                        value={filterReason}
                        onChange={(e) => setFilterReason(e.target.value)}
                        className="appearance-none bg-slate-50 border border-slate-200 rounded-lg py-1.5 pl-3 pr-7 text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                        aria-label="Filter events"
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
                  <div className="flex-1 flex flex-col">
                    {loading ? (
                      <div className="flex-1 flex flex-col items-center justify-center py-16">
                        <div className="w-7 h-7 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
                        <p className="text-[11px] text-slate-400 font-semibold mt-3">Loading history…</p>
                      </div>
                    ) : filteredData.length === 0 ? (
                      <div className="flex-1 flex">
                        {/* Dotted timeline rail */}
                        <div className="w-10 shrink-0 flex flex-col items-center pt-6 pb-4">
                          <div className="w-2 h-2 rounded-full bg-slate-300 mt-1" />
                          <div className="flex-1 border-l-2 border-dashed border-slate-200 mt-2" />
                        </div>
                        {/* Empty state */}
                        <div className="flex-1 flex flex-col items-center justify-center py-10 pr-4">
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
                          <p className="text-[11px] text-slate-500 mt-1.5 max-w-[240px] text-center font-medium leading-relaxed">
                            This job is either freshly queued or was assigned without attempts.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="overflow-x-auto min-h-0">
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
                  <div className="mx-4 mb-4 mt-auto pt-3">
                    <div className="p-3 bg-blue-50/70 border border-blue-100 text-blue-700 rounded-lg text-[10px] font-semibold flex items-center gap-2 leading-relaxed">
                      <Info size={13} className="text-blue-500 shrink-0" />
                      Events will appear here once re-dispatch attempts are made.
                    </div>
                  </div>

                </div>
              </div>

              {/* Right: Stacked detail cards — 2/5 */}
              <div className="col-span-2 flex flex-col gap-3">

                {/* Card 1: Job Details */}
                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 text-left">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-md bg-emerald-50 flex items-center justify-center shrink-0">
                      <FileText size={13} className="text-emerald-600" />
                    </div>
                    <h4 className="text-[10px] font-extrabold text-slate-600 uppercase tracking-widest">Job Details</h4>
                  </div>
                  <div className="space-y-2.5 text-[11px]">
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Job</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words leading-relaxed">
                        {jobDetail ? `${jobDetail.service_type} - ${jobDetail.customer_name}` : jobTitle}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Job ID</span>
                      <span className="text-slate-800 font-semibold">#{jobId}</span>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Created</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words">
                        {jobDetail?.created_at ? new Date(jobDetail.created_at).toLocaleString([], { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : "—"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Priority</span>
                      <span className="flex items-center gap-1.5 justify-end">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${['high','critical'].includes((jobDetail?.priority || '').toLowerCase()) ? 'bg-orange-500' : 'bg-slate-400'}`} />
                        <span className="text-slate-800 font-bold">{(jobDetail?.priority || '—').toUpperCase()}</span>
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Service Line</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words">{jobDetail?.service_type || "—"}</span>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Address</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-all">{jobDetail?.location || "—"}</span>
                    </div>
                  </div>
                </div>

                {/* Card 2: Current Dispatch Status */}
                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 text-left">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-md bg-blue-50 flex items-center justify-center shrink-0">
                      <Truck size={13} className="text-blue-600" />
                    </div>
                    <h4 className="text-[10px] font-extrabold text-slate-600 uppercase tracking-widest">Current Dispatch Status</h4>
                  </div>
                  <div className="space-y-2.5 text-[11px]">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Status</span>
                      {(() => {
                        const s = (jobDetail?.status || 'queued').toLowerCase();
                        const cfg: Record<string,string> = {
                          completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
                          assigned:  'bg-blue-50 text-blue-700 border-blue-200',
                          queued:    'bg-amber-50 text-amber-700 border-amber-200',
                          failed:    'bg-rose-50 text-rose-700 border-rose-200',
                        };
                        const cls = cfg[s] || 'bg-slate-100 text-slate-700 border-slate-200';
                        return (
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wide ${cls}`}>
                            {jobDetail?.status || 'Queued'}
                          </span>
                        );
                      })()}
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Dispatch Method</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words">Automatic (PlanningAgent)</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Attempts</span>
                      <span className="text-slate-800 font-semibold">{attemptCount} of 5</span>
                    </div>
                  </div>
                </div>

                {/* Card 3: Queue Information */}
                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 text-left">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-md bg-violet-50 flex items-center justify-center shrink-0">
                      <Layers size={13} className="text-violet-600" />
                    </div>
                    <h4 className="text-[10px] font-extrabold text-slate-600 uppercase tracking-widest">Queue Information</h4>
                  </div>
                  <div className="space-y-2.5 text-[11px]">
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Queue</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words">{jobDetail?.service_type || "General"} Dispatch</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Queue Position</span>
                      <span className="text-slate-800 font-semibold">#{currentQueuePosition} in line</span>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-400 font-medium shrink-0">Next ETA</span>
                      <span className="text-slate-800 font-semibold text-right min-w-0 break-words">
                        {nextDispatchETA ? new Date(nextDispatchETA).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "No pending search"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card 4: Manual Intervention */}
                {onForceAssignClick && (
                  <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 text-left">
                    <div className="flex items-start gap-2.5 mb-3">
                      <div className="w-6 h-6 rounded-md bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
                        <Shield size={13} className="text-amber-700" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-[10px] font-extrabold text-amber-900 uppercase tracking-widest">Manual Intervention / Override</h4>
                        <p className="text-[10px] text-amber-800/80 font-medium mt-1 leading-relaxed">
                          Bypass automatic PlanningAgent rules and force-assign this job to any eligible technician with full justification.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onForceAssignClick(jobId, jobTitle)}
                      className="w-full py-2.5 bg-gradient-to-r from-orange-500 to-orange-400 hover:from-orange-600 hover:to-orange-500 text-white rounded-lg text-[11px] font-extrabold flex items-center justify-center gap-2 transition duration-200 shadow-md shadow-orange-400/20 hover:shadow-orange-500/30"
                    >
                      <Shield size={13} />
                      Force Assign Job
                    </button>
                    <div className="mt-2.5 flex items-center gap-1.5 text-[10px] text-amber-700 font-semibold">
                      <Info size={11} className="shrink-0" />
                      Manual overrides are logged and require justification.
                    </div>
                  </div>
                )}

                {/* Fallback: legacy manual assign */}
                {onManualAssign && !onForceAssignClick && (
                  <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-left space-y-3">
                    <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                      <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center">
                        <UserCheck size={13} className="text-slate-600" />
                      </div>
                      <h4 className="text-[10px] font-extrabold text-slate-600 uppercase tracking-widest">Manual Assignment</h4>
                    </div>
                    <form onSubmit={handleManualAssignSubmit} className="space-y-3">
                      <select
                        id="tech-select"
                        value={selectedTechId}
                        onChange={(e) => setSelectedTechId(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-semibold text-slate-700"
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
                        className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {assigning ? "Assigning…" : "Manual Assign"}
                      </button>
                    </form>
                  </div>
                )}

              </div>
              {/* end right col */}

            </div>
            {/* end 2-col */}

          </div>
        </div>
        {/* end scrollable body */}

      </motion.div>
    </div>
  );
}
