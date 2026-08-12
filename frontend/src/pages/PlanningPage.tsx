import React, { useEffect, useState, useMemo } from "react";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import { Eye, Trash2, History, Search } from "lucide-react";
import EmptyState from "../components/ui/EmptyState";
import OverrideModal from "../components/notifications/OverrideModal";
import OverrideHistory from "../components/notifications/OverrideHistory";
import OverrideWarning from "../components/notifications/OverrideWarning";
import MetricsCards from "../components/dispatch/MetricsCards";
import DispatchQueueTable from "../components/dispatch/DispatchQueueTable";
import {
  getTechnicians,
  getAvailableTechnicians,
  getPendingJobs,
  getPlannedAssignments,
  assignJob,
  manualAssign,
  getOverrideHistory,
  getJobPlan,
  getAuditOverrides,
  assignJobDirect,
} from "../services/planningService";
import {
  extendSLA,
  cancelEscalatedJob,
  forceAssignEscalation,
} from "../services/escalationService";
import { CompactScorePanel } from "../components/assignment/ScoreDisplay";
import RankedTechTable from "../components/assignment/RankedTechTable";
import TopThreeHighlight, { RankedTechnician } from "../components/assignment/TopThreeHighlight";
import ReDispatchHistory from "../components/notifications/ReDispatchHistory";
import AlertBanner from "../components/notifications/AlertBanner";

const PAGE_SIZE = 8;

const normalizeStatus = (s: string) => (s || "").toLowerCase();

const getPriorityStyle = (priority: string): React.CSSProperties => {
  const p = (priority || "").toUpperCase();
  const base: React.CSSProperties = {
    fontSize: "10px",
    fontWeight: 700,
    padding: "3px 8px",
    borderRadius: "20px",
    textTransform: "uppercase",
    letterSpacing: "0.03em",
    display: "inline-block",
  };
  if (p === "CRITICAL" || p === "P1") return { ...base, background: "#FAE5E5", color: "#7A2020" };
  if (p === "HIGH" || p === "P2") return { ...base, background: "#FEF0D6", color: "#7A5120" };
  if (p === "MEDIUM" || p === "P3") return { ...base, background: "#FDFBDC", color: "#706020" };
  if (p === "LOW" || p === "P4" || p === "P5") return { ...base, background: "#DDEEE5", color: "#2F4F3E" };
  return { ...base, background: "#F0F4F2", color: "#6B7280" };
};

interface PendingJob {
  id: number;
  customer_name: string;
  location?: string;
  priority?: string;
  service_type?: string;
  issue_description?: string;
  acceptance_expired?: boolean;
  is_expired?: boolean;
  redispatched?: boolean;
  is_redispatched?: boolean;
  redispatch_count?: number;
  job_status?: string;
  status?: string;
}

interface PlannedAssignment {
  job_id: number;
  technician: string;
  skill?: string;
  customer: string;
  location?: string;
  priority?: string;
  current_jobs: number;
  max_jobs: number;
}

interface Technician {
  technician_id: number;
  technician_name: string;
  technician_skill: string;
  technician_status: string;
  current_jobs?: number;
  max_jobs?: number;
}

interface TechnicianStatus {
  technician_id: number;
  technician_name: string;
  technician_skill: string;
  status: string;
  current_jobs: number;
  max_jobs: number;
  eligible_for_assignment?: boolean;
}

interface ScoreData {
  composite_score: number;
  proximity_score: number;
  skill_score: number;
  workload_score: number;
  distance_km: number;
  active_jobs: number;
  max_capacity: number;
  is_top_3: boolean;
}

interface ForceAssignJobItem {
  id: number;
  title: string;
  location?: string;
}

interface OverrideHistoryItem {
  id: number;
  title: string;
}

const styles = {
  planningDashboard: {
    fontFamily: "'Inter', sans-serif",
    background: "#EEF4F1",
    minHeight: "100vh",
    padding: "14px",
    color: "#1F2933",
    display: "flex",
    flexDirection: "column",
    gap: "14px",
    boxSizing: "border-box",
  } as React.CSSProperties,

  refreshIconBtn: {
    background: "#FFFFFF",
    border: "1px solid #E3ECE7",
    color: "#2F4F3E",
    padding: "7px 14px",
    borderRadius: "8px",
    fontWeight: 600,
    fontSize: "12px",
    cursor: "pointer",
    transition: "all .2s",
    boxShadow: "0 1px 3px rgba(47, 79, 62, .06)",
  } as React.CSSProperties,

  planningTabs: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 0 10px 0",
    background: "transparent",
    borderRadius: 0,
    marginBottom: "12px",
    border: "none",
    borderBottom: "2px solid #E2E8F0",
    boxSizing: "border-box",
  } as React.CSSProperties,

  planningTab: {
    flex: "none",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 4px 12px 4px",
    border: "none",
    borderBottom: "2px solid transparent",
    borderRadius: 0,
    background: "transparent",
    color: "#64748B",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s ease",
    position: "relative",
    whiteSpace: "nowrap",
    bottom: "-2px",
  } as React.CSSProperties,

  planningTabActive: {
    background: "transparent",
    color: "#2F4F3E",
    borderBottomColor: "#2F4F3E",
    fontWeight: 700,
  } as React.CSSProperties,

  planningTabCount: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "22px",
    height: "22px",
    padding: "0 7px",
    borderRadius: "8px",
    fontSize: "11px",
    fontWeight: 800,
    lineHeight: 1,
    background: "#E2E8F0",
    color: "#64748B",
    transition: "all 0.25s ease",
  } as React.CSSProperties,

  planningTabCountActive: {
    background: "#DCFCE7",
    color: "#166534",
  } as React.CSSProperties,

  planningTabDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    transition: "transform 0.2s ease",
    flexShrink: 0,
  } as React.CSSProperties,

  dashboardSection: {
    background: "#FFFFFF",
    borderRadius: "12px",
    boxShadow: "0 1px 4px rgba(47, 79, 62, 0.07)",
    border: "1px solid #E3ECE7",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxSizing: "border-box",
  } as React.CSSProperties,

  topThreeWrapper: {
    padding: "16px 16px 0",
    boxSizing: "border-box",
  } as React.CSSProperties,

  sectionContent: {
    flex: 1,
    minHeight: "200px",
  } as React.CSSProperties,

  tableContainer: {
    overflowX: "auto",
  } as React.CSSProperties,

  dashboardTable: {
    width: "100%",
    borderCollapse: "collapse",
  } as React.CSSProperties,

  dashboardTableTh: {
    background: "#F6FAF8",
    padding: "6px 8px",
    textAlign: "left",
    fontSize: "9.5px",
    fontWeight: 700,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    borderBottom: "1px solid #E3ECE7",
  } as React.CSSProperties,

  dashboardTableTd: {
    padding: "6px 8px",
    fontSize: "11.5px",
    color: "#1F2933",
    borderBottom: "1px solid #F0F6F2",
    verticalAlign: "middle",
  } as React.CSSProperties,

  jobIdCell: {
    fontWeight: 700,
    color: "#5C9470",
  } as React.CSSProperties,

  customerCell: {
    fontWeight: 600,
    color: "#2F4F3E",
  } as React.CSSProperties,

  issueSub: {
    display: "block",
    fontSize: "11.5px",
    color: "#6B7280",
    fontWeight: 400,
    marginTop: "2px",
  } as React.CSSProperties,

  assignmentActionCell: {
    minWidth: "140px",
  } as React.CSSProperties,

  assignmentUi: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  } as React.CSSProperties,

  techSelect: {
    padding: "5px 8px",
    borderRadius: "6px",
    border: "1.5px solid #E3ECE7",
    fontSize: "12px",
    color: "#1F2933",
    outline: "none",
    background: "#FFFFFF",
    width: "100%",
    maxWidth: "170px",
    transition: "border-color .2s",
  } as React.CSSProperties,

  assignBtn: {
    padding: "5px 12px",
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "11.5px",
    fontWeight: 700,
    cursor: "pointer",
    whiteSpace: "nowrap",
    transition: "background 0.2s",
    boxShadow: "0 1px 4px rgba(122, 174, 138, .25)",
  } as React.CSSProperties,

  planningPagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 14px",
    borderTop: "1px solid #E3ECE7",
    flexWrap: "wrap",
    gap: "8px",
    background: "#FAFCFB",
    boxSizing: "border-box",
  } as React.CSSProperties,

  planningPageInfo: {
    fontSize: "10px",
    color: "#6B7280",
    fontWeight: 500,
  } as React.CSSProperties,

  planningPageControls: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  } as React.CSSProperties,

  planningPageBtn: {
    padding: "5px 12px",
    background: "#FFFFFF",
    border: "1.5px solid #E3ECE7",
    borderRadius: "7px",
    fontSize: "10px",
    fontWeight: 600,
    color: "#2F4F3E",
    cursor: "pointer",
    transition: "all .2s",
  } as React.CSSProperties,

  planningPageNumbers: {
    display: "flex",
    gap: "4px",
  } as React.CSSProperties,

  planningPageNum: {
    width: "26px",
    height: "26px",
    borderRadius: "7px",
    border: "1.5px solid #E3ECE7",
    background: "#FFFFFF",
    fontSize: "10px",
    fontWeight: 600,
    color: "#6B7280",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all .2s",
  } as React.CSSProperties,

  planningPageNumActive: {
    background: "#7AAE8A",
    borderColor: "#7AAE8A",
    color: "#fff",
  } as React.CSSProperties,

  techCell: {
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,

  skillSub: {
    display: "block",
    fontString: "11.5px",
    color: "#6B7280",
    fontWeight: 400,
    marginTop: "2px",
  } as React.CSSProperties,

  statusBadge: {
    fontSize: "10px",
    fontWeight: 700,
    padding: "3px 9px",
    borderRadius: "20px",
    textTransform: "uppercase",
    display: "inline-block",
  } as React.CSSProperties,

  statusAssigned: {
    background: "#DDEEE5",
    color: "#2F4F3E",
    border: "1px solid #C3DDC9",
  } as React.CSSProperties,

  workloadInfo: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    minWidth: "110px",
  } as React.CSSProperties,

  workloadBar: {
    flex: 1,
    height: "5px",
    background: "#E3ECE7",
    borderRadius: "3px",
    overflow: "hidden",
  } as React.CSSProperties,

  workloadFill: {
    height: "100%",
    background: "#7AAE8A",
    borderRadius: "3px",
    transition: "width 0.3s",
  } as React.CSSProperties,

  workloadText: {
    fontSize: "11px",
    fontWeight: 600,
    color: "#6B7280",
    whiteSpace: "nowrap",
  } as React.CSSProperties,

  jobItemActions: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  } as React.CSSProperties,

  iconActionBtn: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: "28px",
    height: "28px",
    border: "none",
    borderRadius: 0,
    background: "none",
    padding: 0,
    cursor: "pointer",
    outline: "none",
  } as React.CSSProperties,

  popupOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(31,41,51,.4)",
    zIndex: 2000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  } as React.CSSProperties,

  viewJobModal: {
    background: "#FFFFFF",
    borderRadius: "16px",
    padding: 0,
    maxWidth: "460px",
    width: "94%",
    boxShadow: "0 20px 50px rgba(47,79,62,.18)",
    overflow: "hidden",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewModalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "18px 22px 14px",
    borderBottom: "1px solid #E3ECE7",
    background: "#F6FAF8",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewModalHeaderH3: {
    fontSize: "15px",
    fontWeight: 700,
    color: "#2F4F3E",
    margin: 0,
  } as React.CSSProperties,

  viewModalBody: {
    padding: "18px 22px 22px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewDetailRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
  } as React.CSSProperties,

  viewLabel: {
    minWidth: "110px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: ".03em",
    paddingTop: "2px",
  } as React.CSSProperties,

  viewValue: {
    fontSize: "13px",
    color: "#1F2937",
    fontWeight: 500,
    flex: 1,
  } as React.CSSProperties,

  metricFilterBanner: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "10px",
    marginBottom: "14px",
    padding: "10px 14px",
    border: "1px solid #dbeafe",
    background: "linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%)",
    borderRadius: "12px",
    boxSizing: "border-box",
  } as React.CSSProperties,

  metricFilterLeft: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  } as React.CSSProperties,

  metricFilterIcon: {
    width: "36px",
    height: "36px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#e0f2fe",
    color: "#2563eb",
    fontSize: "16px",
    boxShadow: "0 6px 16px rgba(37, 99, 235, 0.12)",
  } as React.CSSProperties,

  metricFilterTextWrap: {
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,

  metricFilterLabel: {
    margin: 0,
    fontSize: "10px",
    color: "#64748b",
    fontWeight: 600,
  } as React.CSSProperties,

  metricFilterValue: {
    margin: "2px 0 0",
    fontSize: "16px",
    color: "#1d4ed8",
    fontWeight: 700,
    textTransform: "capitalize",
  } as React.CSSProperties,

  metricClearBtn: {
    border: "1px solid #bfdbfe",
    background: "#ffffff",
    color: "#2563eb",
    fontWeight: 600,
    borderRadius: "10px",
    padding: "8px 14px",
    fontSize: "13px",
    cursor: "pointer",
    transition: "all 0.2s ease",
  } as React.CSSProperties,

  planningHeaderSearchWrap: {
    position: "relative",
    maxWidth: "380px",
    width: "260px",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  } as React.CSSProperties,

  planningSearchIcon: {
    position: "absolute",
    left: "14px",
    top: "50%",
    transform: "translateY(-50%)",
    color: "#64748B",
    display: "flex",
    alignItems: "center",
    pointerEvents: "none",
    zIndex: 10,
    transition: "color 0.2s ease",
  } as React.CSSProperties,

  planningSearchInput: {
    width: "100%",
    padding: "10px 16px 10px 42px",
    fontSize: "13.5px",
    fontWeight: 600,
    color: "#1E293B",
    background: "#FFFFFF",
    border: "1.5px solid #CBD5E1",
    borderRadius: "12px",
    outline: "none",
    boxShadow: "0 2px 4px rgba(0, 0, 0, 0.02)",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
    boxSizing: "border-box",
  } as React.CSSProperties,

  alertError: {
    background: "#FDF2F2",
    border: "1px solid #F5C6C6",
    color: "#9B3A3A",
  } as React.CSSProperties,

  alertSuccess: {
    background: "#EDFAF1",
    border: "1px solid #B0D4BC",
    color: "#2F4F3E",
    fontWeight: 500,
  } as React.CSSProperties,
};

const localCss = `
  .planning-tab-style {
    transition: all 0.2s ease !important;
  }
  .planning-tab-style:hover:not(.active-tab-style) {
    color: #1E293B !important;
  }
  .planning-tab-style:hover .planning-tab-dot-style {
    transform: scale(1.25) !important;
  }
  .planning-page-btn-style:hover:not(:disabled) {
    background-color: #EAF4EE !important;
    border-color: #7AAE8A !important;
  }
  .planning-page-num-style:hover {
    border-color: #7AAE8A !important;
    color: #2F4F3E !important;
  }
  .planning-refresh-btn-style:hover:not(:disabled) {
    background-color: #F6FAF8 !important;
    border-color: #7AAE8A !important;
  }
  .planning-header-search-wrap-style:focus-within {
    width: 380px !important;
    max-width: 420px !important;
  }
  .planning-header-search-wrap-style:focus-within .planning-search-icon-style {
    color: #2F4F3E !important;
  }
  .planning-search-input-style:focus {
    border-color: #2F4F3E !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 4px 12px rgba(47, 79, 62, 0.08), 0 0 0 3px rgba(47, 79, 62, 0.12) !important;
  }
  .planning-search-input-style:hover:not(:focus) {
    border-color: #94A3B8 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
  }
  .tech-select-style:focus {
    border-color: #7AAE8A !important;
    box-shadow: 0 0 0 2px rgba(122, 174, 138, .12) !important;
  }
  .assign-btn-style:hover:not(:disabled) {
    background-color: #5C9470 !important;
  }
  .icon-action-btn-style {
    transition: transform .15s, opacity .15s !important;
  }
  .icon-action-btn-style:hover {
    transform: scale(1.2) !important;
    opacity: .8 !important;
  }
  .icon-action-btn-style:active {
    transform: scale(0.9) !important;
  }
  .metric-clear-btn-style:hover {
    background-color: #eff6ff !important;
    transform: translateY(-1px) !important;
  }
  .dashboard-table-row:hover td {
    background-color: #F8FBF9 !important;
  }
  .dashboard-table-row.selected-row-style td {
    background-color: #FFF8E7 !important;
    border-left: 3px solid #F59E0B !important;
  }
  .dashboard-table-row.selected-row-style:hover td {
    background-color: #FFF3D0 !important;
  }

  .alert-style-base {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1000;
    max-width: 380px;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
    animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  
  .alert-close-btn-style {
    background: none;
    border: none;
    color: currentColor;
    font-size: 20px;
    line-height: 1;
    padding: 0 4px;
    cursor: pointer;
    opacity: 0.65;
    transition: opacity 0.2s ease;
    flex-shrink: 0;
  }
  .alert-close-btn-style:hover {
    opacity: 1;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(16px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 768px) {
    .planning-header-responsive {
      flex-direction: column !important;
      align-items: flex-start !important;
      gap: 12px !important;
    }
    .planning-header-controls-responsive {
      width: 100% !important;
      justify-content: space-between !important;
    }
    .metric-filter-banner-responsive {
      flex-direction: column !important;
      align-items: flex-start !important;
    }
    .metric-clear-btn-style {
      width: 100% !important;
    }
    .planning-tabs-responsive {
      flex-direction: column !important;
      align-items: flex-start !important;
      gap: 12px !important;
    }
    .planning-tab-btn-group {
      width: 100% !important;
      justify-content: space-between !important;
    }
    .alert-style-base {
      right: 16px !important;
      left: 16px !important;
      bottom: 74px !important;
      max-width: none !important;
    }
  }
  @media (max-width: 640px) {
    .planning-tabs-responsive {
      gap: 16px !important;
      padding: 0 0 8px 0 !important;
    }
    .planning-tab-btn-style {
      padding: 6px 2px 10px 2px !important;
      font-size: 13px !important;
      gap: 6px !important;
    }
  }
`;

function PlanningDashboard() {
  const [pendingJobs, setPendingJobs] = useState<PendingJob[]>([]);
  const [plannedAssignments, setPlannedAssignments] = useState<PlannedAssignment[]>([]);
  const [allTechsStatus, setAllTechsStatus] = useState<TechnicianStatus[]>([]);
  const [allTechsList, setAllTechsList] = useState<Technician[]>([]);

  const [jobsLoading, setJobsLoading] = useState(false);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [techStatusLoading, setTechStatusLoading] = useState(false);

  const [selectedTechs, setSelectedTechs] = useState<Record<number, string>>({});
  const [assigningJobId, setAssigningJobId] = useState<number | null>(null);
  
  const [expandedScores, setExpandedScores] = useState<Record<number, boolean>>({});
  const [scoreDataMap, setScoreDataMap] = useState<Record<number, ScoreData>>({});

  const [selectedJobForRanking, setSelectedJobForRanking] = useState<PendingJob | null>(null);
  const [rankedCandidates, setRankedCandidates] = useState<RankedTechnician[]>([]);
  const [showFullCandidatePool, setShowFullCandidatePool] = useState(false);

  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [assignSuccessMsg, setAssignSuccessMsg] = useState("");

  const [showHistoryJobId, setShowHistoryJobId] = useState<number | null>(null);
  const [showHistoryJobTitle, setShowHistoryJobTitle] = useState("");
  const [forceAssignJob, setForceAssignJob] = useState<ForceAssignJobItem | null>(null);
  const [showOverrideHistoryForJob, setShowOverrideHistoryForJob] = useState<OverrideHistoryItem | null>(null);
  const [viewAssignmentOverride, setViewAssignmentOverride] = useState<any>(null);
  const [showOverrideHistoryForView, setShowOverrideHistoryForView] = useState(false);

  const handleManualAssign = async (jobId: number, techId: number) => {
    try {
      await manualAssign(jobId, techId);
      showAssignSuccess("Job assigned manually successfully!");
      fetchAllData();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to manually assign job.";
      setError(msg);
    }
  };

  const [activeTab, setActiveTab] = useState("pending");

  const [pendingPage, setPendingPage] = useState(1);
  const [plannedPage, setPlannedPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewAssignment, setViewAssignment] = useState<PlannedAssignment | null>(null);

  const [activeMetricFilter, setActiveMetricFilter] = useState("all");
  const [dispatchQueueCount, setDispatchQueueCount] = useState(0);

  const handleMetricFilterChange = (filter: string, metricKey: string) => {
    console.log("Metric card clicked:", metricKey, filter);
    setActiveMetricFilter(metricKey);
    setActiveTab("pending");
    setPendingPage(1);
  };

  const getMetricEmptyTitle = () => {
    if (activeMetricFilter === "expired") {
      return "No expired jobs found";
    }
    if (activeMetricFilter === "redispatched") {
      return "No re-dispatched jobs found";
    }
    if (activeMetricFilter === "pending") {
      return "No pending jobs found";
    }
    return searchQuery.trim() ? "No jobs match your search" : "No pending jobs";
  };

  const getMetricEmptyDescription = () => {
    if (activeMetricFilter === "expired") {
      return "There are no jobs with expired acceptance timer in the current queue.";
    }
    if (activeMetricFilter === "redispatched") {
      return "There are no re-dispatched jobs in the current queue.";
    }
    if (activeMetricFilter === "pending") {
      return "There are no queued, assigned, or pending jobs available right now.";
    }
    return searchQuery.trim()
      ? "Try adjusting your search terms."
      : "All jobs are either assigned or completed.";
  };

  const fetchPendingJobs = async () => {
    try {
      setJobsLoading(true);
      const res = await getPendingJobs();
      setPendingJobs(res.data);
    } catch {
      setError("Failed to load pending jobs. Please try again.");
    } finally {
      setJobsLoading(false);
    }
  };

  const fetchPlannedAssignments = async () => {
    try {
      setAssignmentsLoading(true);
      const res = await getPlannedAssignments();
      setPlannedAssignments(res.data);
    } catch {
      setError("Failed to load planned assignments. Please try again.");
    } finally {
      setAssignmentsLoading(false);
    }
  };

  const fetchTechnicianStatus = async () => {
    try {
      setTechStatusLoading(true);
      const res = await getAvailableTechnicians();
      setAllTechsStatus(res.data);
    } catch {
      setError("Failed to load technician status. Please try again.");
    } finally {
      setTechStatusLoading(false);
    }
  };

  const fetchTechniciansList = async () => {
    try {
      const res = await getTechnicians();
      setAllTechsList(res.data);
    } catch {
      console.error("Could not fetch technicians list for dropdown.");
    }
  };

  const fetchAllData = () => {
    setError("");
    setSuccessMsg("");
    fetchPendingJobs();
    fetchPlannedAssignments();
    fetchTechnicianStatus();
    fetchTechniciansList();
  };

  useEffect(() => { fetchAllData(); }, []);

  useEffect(() => {
    if (viewAssignment) {
      getOverrideHistory(viewAssignment.job_id)
        .then(res => {
          if (res && res.data && res.data.length > 0) {
            setViewAssignmentOverride(res.data[0]);
          } else {
            setViewAssignmentOverride(null);
          }
        })
        .catch(err => {
          console.warn("Failed to fetch override history for view modal", err);
          setViewAssignmentOverride(null);
        });
    } else {
      setViewAssignmentOverride(null);
    }
  }, [viewAssignment]);

  const generateRankedCandidates = (job: PendingJob): RankedTechnician[] => {
    if (!allTechsList || allTechsList.length === 0) return [];
    return allTechsList
      .map((t) => {
        const seed = t.technician_id * 13 + (job?.id || 1) * 7;
        const pseudo = (n: number) => ((seed * n * 31 + 17) % 45) + 50;
        const composite = pseudo(1);
        return {
          technician_id:    t.technician_id,
          technician_name:  t.technician_name,
          technician_skill: t.technician_skill,
          technician_status: t.technician_status,
          composite_score:  composite,
          proximity_score:  Math.min(100, pseudo(2)),
          skill_score:      Math.min(100, pseudo(3)),
          workload_score:   Math.min(100, pseudo(4)),
          distance_km:      parseFloat(((seed % 200) / 10).toFixed(1)),
          active_jobs:      t.current_jobs ?? Math.floor(seed % 3),
          max_capacity:     t.max_jobs ?? 5,
        };
      })
      .sort((a, b) => b.composite_score - a.composite_score);
  };

  const handleJobRowClick = async (job: PendingJob) => {
    if (selectedJobForRanking?.id === job.id) {
      setSelectedJobForRanking(null);
      setRankedCandidates([]);
      return;
    }
    setSelectedJobForRanking(job);
    setShowFullCandidatePool(false);
    try {
      const res = await getJobPlan(job.id);
      if (res && res.ranked_technicians) {
        const mapped: RankedTechnician[] = res.ranked_technicians.map((rt: any) => ({
          technician_id: parseInt(String(rt.tech_id).replace(/\D/g, ''), 10) || 1,
          technician_name: rt.name,
          technician_skill: rt.skill || 'HVAC',
          technician_status: rt.status || 'Available',
          composite_score: rt.composite_score || 0,
          proximity_score: rt.proximity_score || 0,
          skill_score: rt.skill_score || 0,
          workload_score: rt.workload_score || 0,
          distance_km: rt.distance_km || 0,
          active_jobs: rt.active_jobs || 0,
          max_capacity: rt.max_capacity || 3
        }));
        setRankedCandidates(mapped);
      } else {
        setRankedCandidates(generateRankedCandidates(job));
      }
    } catch (err) {
      console.warn("Failed to fetch AI plan from backend, falling back to mock ranking", err);
      setRankedCandidates(generateRankedCandidates(job));
    }
  };

  const handleTopThreeClose = () => {
    setSelectedJobForRanking(null);
    setRankedCandidates([]);
  };

  const handleTechSelect = (jobId: number, techId: string) => {
    setSelectedTechs((prev) => ({ ...prev, [jobId]: techId }));
    if (techId) {
      const job = pendingJobs.find((j) => j.id === jobId);
      if (job) {
        const candidatesList = generateRankedCandidates(job);
        const candidate = candidatesList.find((c) => c.technician_id === parseInt(techId, 10));
        if (candidate) {
          setScoreDataMap((prev) => ({
            ...prev,
            [jobId]: {
              composite_score: candidate.composite_score,
              proximity_score: candidate.proximity_score,
              skill_score:     candidate.skill_score,
              workload_score:  candidate.workload_score,
              distance_km:     candidate.distance_km,
              active_jobs:     candidate.active_jobs,
              max_capacity:    candidate.max_capacity,
              is_top_3:        candidatesList.slice(0, 3).some((c) => c.technician_id === candidate.technician_id),
            },
          }));
        } else {
          const composite = Math.floor(Math.random() * 45) + 50;
          setScoreDataMap((prev) => ({
            ...prev,
            [jobId]: {
              composite_score: composite,
              proximity_score: Math.min(100, composite + Math.floor(Math.random() * 12) - 4),
              skill_score:     Math.min(100, composite + Math.floor(Math.random() * 15)),
              workload_score:  Math.min(100, composite + Math.floor(Math.random() * 10) - 5),
              distance_km:     parseFloat((Math.random() * 22).toFixed(1)),
              active_jobs:     Math.floor(Math.random() * 3),
              max_capacity:    5,
              is_top_3:        composite >= 80,
            },
          }));
        }
      }
      setExpandedScores((prev) => ({ ...prev, [jobId]: true }));
    } else {
      setExpandedScores((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  const toggleScorePanel = (jobId: number) => {
    setExpandedScores((prev) => ({ ...prev, [jobId]: !prev[jobId] }));
  };

  const handleAssignJob = async (jobId: number, techIdOverride?: string) => {
    const techId = techIdOverride || selectedTechs[jobId];
    if (!techId) return;
    const tech = allTechsList.find(
      (t) => t.technician_id === parseInt(techId, 10)
    );
    if (tech && normalizeStatus(tech.technician_status) !== "available" && normalizeStatus(tech.technician_status) !== "assigned") {
      setError(
        `Cannot assign: ${tech.technician_name} is currently ${tech.technician_status}. Please select an Available or Assigned technician.`
      );
      return;
    }
    try {
      setAssigningJobId(jobId);
      setError("");
      await assignJob(jobId, parseInt(techId, 10));
      setSelectedTechs((prev) => {
        const next = { ...prev };
        delete next[jobId];
        return next;
      });
      if (selectedJobForRanking?.id === jobId) {
        setSelectedJobForRanking(null);
        setRankedCandidates([]);
      }
      const techName = tech ? tech.technician_name : "Technician";
      showAssignSuccess(`${techName} has been assigned to this work.`);
      fetchAllData();
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        "Failed to assign technician.";
      setError(msg);
    } finally {
      setAssigningJobId(null);
    }
  };

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(""), 3500);
  };

  const showAssignSuccess = (msg: string) => {
    setAssignSuccessMsg(msg);
    setTimeout(() => setAssignSuccessMsg(""), 4500);
  };

  const isGlobalLoading = jobsLoading || assignmentsLoading || techStatusLoading;

  const escalatedJobs = useMemo(() => {
    return pendingJobs.filter(job => {
      const status = String(job.status || job.job_status || "").toUpperCase();
      return status === "ESCALATED" || status === "ESCALATED_TO_CTO";
    });
  }, [pendingJobs]);

  const normalPendingJobs = useMemo(() => {
    return pendingJobs.filter(job => {
      const status = String(job.status || job.job_status || "").toUpperCase();
      return status !== "ESCALATED" && status !== "ESCALATED_TO_CTO";
    });
  }, [pendingJobs]);

  const filteredPendingJobs = useMemo(() => {
    if (!searchQuery.trim()) return normalPendingJobs;
    const q = searchQuery.toLowerCase().trim();
    return normalPendingJobs.filter(
      (job) =>
        String(job.id).includes(q) ||
        (job.customer_name && job.customer_name.toLowerCase().includes(q)) ||
        (job.location && job.location.toLowerCase().includes(q)) ||
        (job.issue_description && job.issue_description.toLowerCase().includes(q)) ||
        (job.priority && job.priority.toLowerCase().includes(q))
    );
  }, [normalPendingJobs, searchQuery]);

  const metricFilteredPendingJobs = useMemo(() => {
    if (!filteredPendingJobs || filteredPendingJobs.length === 0) return [];
    if (activeMetricFilter === "all" || activeMetricFilter === "dispatched") {
      return filteredPendingJobs;
    }
    if (activeMetricFilter === "pending") {
      return filteredPendingJobs.filter((job) => {
        const status = String(job.status || job.job_status || "").toLowerCase();
        return (
          status === "queued" ||
          status === "assigned" ||
          status === "pending" ||
          !status
        );
      });
    }
    if (activeMetricFilter === "expired") {
      return filteredPendingJobs.filter((job) => {
        const status = String(job.status || job.job_status || "").toLowerCase();
        return (
          status === "expired" ||
          job.acceptance_expired === true ||
          job.is_expired === true
        );
      });
    }
    if (activeMetricFilter === "redispatched") {
      return filteredPendingJobs.filter((job) => {
        return (
          job.redispatched === true ||
          job.is_redispatched === true ||
          Number(job.redispatch_count || 0) > 0
        );
      });
    }
    return filteredPendingJobs;
  }, [filteredPendingJobs, activeMetricFilter]);

  const filteredPlannedAssignments = useMemo(() => {
    if (!searchQuery.trim()) return plannedAssignments;
    const q = searchQuery.toLowerCase().trim();
    return plannedAssignments.filter(
      (item) =>
        String(item.job_id).includes(q) ||
        (item.technician && item.technician.toLowerCase().includes(q)) ||
        (item.skill && item.skill.toLowerCase().includes(q)) ||
        (item.customer && item.customer.toLowerCase().includes(q)) ||
        (item.location && item.location.toLowerCase().includes(q)) ||
        (item.priority && item.priority.toLowerCase().includes(q))
    );
  }, [plannedAssignments, searchQuery]);

  useEffect(() => {
    setPendingPage(1);
    setPlannedPage(1);
  }, [searchQuery, activeMetricFilter]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(metricFilteredPendingJobs.length / PAGE_SIZE));
    if (pendingPage > totalPages) {
      setPendingPage(totalPages);
    }
  }, [metricFilteredPendingJobs.length, pendingPage]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredPlannedAssignments.length / PAGE_SIZE));
    if (plannedPage > totalPages) {
      setPlannedPage(totalPages);
    }
  }, [filteredPlannedAssignments.length, plannedPage]);

  const pendingTotalPages = Math.max(1, Math.ceil(metricFilteredPendingJobs.length / PAGE_SIZE));
  const safePendingPage = Math.min(pendingPage, pendingTotalPages);
  const paginatedPendingJobs = metricFilteredPendingJobs.slice(
    (safePendingPage - 1) * PAGE_SIZE,
    safePendingPage * PAGE_SIZE
  );

  const plannedTotalPages = Math.max(1, Math.ceil(filteredPlannedAssignments.length / PAGE_SIZE));
  const safePlannedPage = Math.min(plannedPage, plannedTotalPages);
  const paginatedPlannedAssignments = filteredPlannedAssignments.slice((safePlannedPage - 1) * PAGE_SIZE, safePlannedPage * PAGE_SIZE);

  const getPageNums = (currentPage: number, totalPages: number) => {
    const nums: number[] = [];
    const delta = 2;
    for (let i = Math.max(1, currentPage - delta); i <= Math.min(totalPages, currentPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  return (
    <div style={styles.planningDashboard}>
      <style>{localCss}</style>
      <div style={{ marginBottom: "24px" }}>
        <MetricsCards onFilterChange={handleMetricFilterChange} />
      </div>
      <AlertBanner
        onViewHistory={(jobId: number, jobTitle: string) => {
          setShowHistoryJobId(jobId);
          setShowHistoryJobTitle(jobTitle);
        }}
        onManualAssignClick={(jobId: number, jobTitle: string) => {
          setForceAssignJob({ id: jobId, title: jobTitle });
        }}
        currentUserRole="dispatcher"
      />

      {/* Global messages */}
      {error && (
        <div className="alert-style-base" style={styles.alertError}>
          <span>{error}</span>
          <button
            onClick={() => setError("")}
            className="alert-close-btn-style"
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}
      {successMsg && (
        <div className="alert-style-base" style={styles.alertSuccess}>
          <span>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg("")}
            className="alert-close-btn-style"
            aria-label="Dismiss success message"
          >
            &times;
          </button>
        </div>
      )}
      {assignSuccessMsg && (
        <div className="alert-style-base" style={{ ...styles.alertSuccess, right: "auto", left: "24px" }}>
          <span>{assignSuccessMsg}</span>
          <button
            onClick={() => setAssignSuccessMsg("")}
            className="alert-close-btn-style"
            aria-label="Dismiss success message"
          >
            &times;
          </button>
        </div>
      )}

      {/* ── Tab Navigation ── */}
      <div className="planning-tabs-responsive" style={styles.planningTabs}>
        <div className="planning-tab-btn-group" style={{ display: "flex", gap: "24px" }}>
          <button
            className={`planning-tab-style ${activeTab === 'pending' ? 'active-tab-style' : ''}`}
            style={{
              ...styles.planningTab,
              ...(activeTab === 'pending' ? styles.planningTabActive : {})
            }}
            onClick={() => setActiveTab('pending')}
          >
            <span className="planning-tab-dot-style" style={{ ...styles.planningTabDot, backgroundColor: "#EF4444" }}></span>
            <span>Pending Jobs</span>
            <span style={{
              ...styles.planningTabCount,
              ...(activeTab === 'pending' ? styles.planningTabCountActive : {})
            }}>{normalPendingJobs.length}</span>
          </button>
          <button
            className={`planning-tab-style ${activeTab === 'planned' ? 'active-tab-style' : ''}`}
            style={{
              ...styles.planningTab,
              ...(activeTab === 'planned' ? styles.planningTabActive : {})
            }}
            onClick={() => setActiveTab('planned')}
          >
            <span className="planning-tab-dot-style" style={{ ...styles.planningTabDot, backgroundColor: "#10B981" }}></span>
            <span>Planned Assignments</span>
            <span style={{
              ...styles.planningTabCount,
              ...(activeTab === 'planned' ? styles.planningTabCountActive : {})
            }}>{plannedAssignments.length}</span>
          </button>
          <button
            className={`planning-tab-style ${activeTab === 'dispatch' ? 'active-tab-style' : ''}`}
            style={{
              ...styles.planningTab,
              ...(activeTab === 'dispatch' ? styles.planningTabActive : {})
            }}
            onClick={() => setActiveTab('dispatch')}
          >
            <span className="planning-tab-dot-style" style={{ ...styles.planningTabDot, backgroundColor: '#3B82F6' }}></span>
            <span>Dispatch Queue</span>
            <span style={{
              ...styles.planningTabCount,
              ...(activeTab === 'dispatch' ? styles.planningTabCountActive : {})
            }}>{dispatchQueueCount}</span>
          </button>
          <button
            className={`planning-tab-style ${activeTab === 'escalated' ? 'active-tab-style' : ''}`}
            style={{
              ...styles.planningTab,
              ...(activeTab === 'escalated' ? styles.planningTabActive : {})
            }}
            onClick={() => setActiveTab('escalated')}
          >
            <span className="planning-tab-dot-style" style={{ ...styles.planningTabDot, backgroundColor: '#F59E0B' }}></span>
            <span>SLA Escalations</span>
            <span style={{
              ...styles.planningTabCount,
              ...(activeTab === 'escalated' ? styles.planningTabCountActive : {})
            }}>{escalatedJobs.length}</span>
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <div className="planning-header-search-wrap-style" style={styles.planningHeaderSearchWrap}>
            <span className="planning-search-icon-style" style={styles.planningSearchIcon}>
              <Search size={18} />
            </span>
            <input
              type="text"
              placeholder="Search jobs, customers, locations..."
              className="planning-search-input-style"
              style={styles.planningSearchInput}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button
            className="planning-refresh-btn-style"
            style={{ ...styles.refreshIconBtn, marginBottom: 0 }}
            onClick={fetchAllData}
            disabled={isGlobalLoading}
          >
            {isGlobalLoading ? "Refreshing..." : "⟳ Refresh"}
          </button>
        </div>
      </div>

      {/* ── Tab Content ── */}

      {/* PENDING JOBS TAB */}
      {activeTab === 'pending' && (
        <section style={styles.dashboardSection}>
          {/* Ranked Technician Selection Panel */}
          {selectedJobForRanking && rankedCandidates.length > 0 && (
            <div style={styles.topThreeWrapper}>
              {!showFullCandidatePool ? (
                <TopThreeHighlight
                  technicians={rankedCandidates}
                  jobId={selectedJobForRanking.id}
                  jobLabel={`Job #${selectedJobForRanking.id} (${selectedJobForRanking.customer_name})`}
                  onSelect={(techId) => handleAssignJob(selectedJobForRanking.id, String(techId))}
                  onSelectOther={() => setShowFullCandidatePool(true)}
                  onClose={handleTopThreeClose}
                />
              ) : (
                <RankedTechTable
                  job={{
                    id: selectedJobForRanking.id,
                    customer_name: selectedJobForRanking.customer_name,
                    priority: selectedJobForRanking.priority,
                    location: selectedJobForRanking.location,
                    issue_description: selectedJobForRanking.issue_description,
                  }}
                  candidates={rankedCandidates}
                  selectedTechId={selectedTechs[selectedJobForRanking.id] ? parseInt(selectedTechs[selectedJobForRanking.id], 10) : undefined}
                  onSelect={(techId) => handleTechSelect(selectedJobForRanking.id, String(techId))}
                  onAssign={(techId) => handleAssignJob(selectedJobForRanking.id, String(techId))}
                  onClose={handleTopThreeClose}
                />
              )}
            </div>
          )}

          <div style={styles.sectionContent}>
            {activeMetricFilter !== "all" && (
              <div className="metric-filter-banner-responsive" style={styles.metricFilterBanner}>
                <div style={styles.metricFilterLeft}>
                  <div style={styles.metricFilterIcon} aria-hidden="true">
                    🔎
                  </div>
                  <div style={styles.metricFilterTextWrap}>
                    <p style={styles.metricFilterLabel}>Active metric filter</p>
                    <h4 style={styles.metricFilterValue}>{activeMetricFilter}</h4>
                  </div>
                </div>
                <button
                  type="button"
                  className="metric-clear-btn-style"
                  style={styles.metricClearBtn}
                  onClick={() => {
                    setActiveMetricFilter("all");
                    setPendingPage(1);
                  }}
                >
                  ✕ Clear Filter
                </button>
              </div>
            )}

            {jobsLoading ? (
              <LoadingSpinner message="Loading pending jobs..." />
            ) : (
              <div style={styles.tableContainer}>
                {metricFilteredPendingJobs.length === 0 ? (
                  <EmptyState
                    title={getMetricEmptyTitle()}
                    description={getMetricEmptyDescription()}
                    action={
                      searchQuery.trim() || activeMetricFilter !== "all" ? (
                        <button
                          className="planning-refresh-btn-style"
                          style={styles.refreshIconBtn}
                          onClick={() => {
                            setSearchQuery("");
                            setActiveMetricFilter("all");
                          }}
                        >
                          Clear Filters
                        </button>
                      ) : undefined
                    }
                  />
                ) : (
                  <table style={styles.dashboardTable}>
                    <thead>
                      <tr>
                        <th style={styles.dashboardTableTh}>ID</th>
                        <th style={styles.dashboardTableTh}>Customer</th>
                        <th style={styles.dashboardTableTh}>Location</th>
                        <th style={styles.dashboardTableTh}>Priority</th>
                        <th style={styles.dashboardTableTh}>Assign Technician</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPendingJobs.map((job) => (
                        <tr
                          key={job.id}
                          onClick={() => handleJobRowClick(job)}
                          className={`dashboard-table-row ${selectedJobForRanking?.id === job.id ? 'selected-row-style' : ''}`}
                          style={{ cursor: 'pointer' }}
                          title="Click to see top recommended technicians"
                        >
                          <td style={{ ...styles.dashboardTableTd, ...styles.jobIdCell }}>#{job.id}</td>
                          <td style={{ ...styles.dashboardTableTd, ...styles.customerCell }}>
                            <div>{job.customer_name}</div>
                            {job.issue_description && (
                              <div style={styles.issueSub}>{job.issue_description}</div>
                            )}
                          </td>
                          <td style={styles.dashboardTableTd}>{job.location}</td>
                          <td style={styles.dashboardTableTd}>
                            <span style={getPriorityStyle(job.priority || "")}>
                              {job.priority || "UNKNOWN"}
                            </span>
                          </td>
                          <td style={{ ...styles.dashboardTableTd, ...styles.assignmentActionCell }}>
                            <div style={styles.assignmentUi}>
                              <select
                                className="tech-select-style"
                                style={styles.techSelect}
                                value={selectedTechs[job.id] || ""}
                                onChange={(e) => handleTechSelect(job.id, e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                disabled={assigningJobId === job.id}
                              >
                                <option value="" disabled>
                                  {techStatusLoading ? "Loading technicians..." : "Select Technician"}
                                </option>
                                {allTechsList.map((tech) => {
                                  const unavail =
                                    normalizeStatus(tech.technician_status) !== "available" &&
                                    normalizeStatus(tech.technician_status) !== "assigned";
                                  return (
                                    <option
                                      key={tech.technician_id}
                                      value={tech.technician_id}
                                      disabled={unavail}
                                    >
                                      {tech.technician_name} – {tech.technician_skill}
                                      {unavail ? ` (Unavailable – ${tech.technician_status})` : ""}
                                    </option>
                                  );
                                })}
                              </select>
                              <button
                                className="assign-btn-style"
                                style={styles.assignBtn}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAssignJob(job.id);
                                }}
                                disabled={!selectedTechs[job.id] || assigningJobId === job.id}
                              >
                                {assigningJobId === job.id ? "Assigning…" : "Assign"}
                              </button>
                              <button
                                className="assign-btn-style"
                                style={{
                                  ...styles.assignBtn,
                                  backgroundColor: '#475569',
                                  minWidth: 40,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  padding: '0 8px'
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowHistoryJobId(job.id);
                                  setShowHistoryJobTitle(`${job.service_type || "Job"} - ${job.location || ""}`);
                                }}
                                title="View Re-Dispatch History"
                              >
                                <History size={16} />
                              </button>
                              <button
                                className="assign-btn-style"
                                style={{
                                  ...styles.assignBtn,
                                  backgroundColor: selectedJobForRanking?.id === job.id ? '#1c1917' : '#0284c7',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  padding: '0 8px',
                                  fontWeight: 'bold',
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleJobRowClick(job);
                                }}
                                title="Get AI Plan / Candidates"
                              >
                                AI Plan
                              </button>
                              {selectedTechs[job.id] && scoreDataMap[job.id] && (
                                <button
                                  className="assign-btn-style"
                                  style={{
                                    ...styles.assignBtn,
                                    backgroundColor: expandedScores[job.id] ? '#6b7280' : '#10b981',
                                    minWidth: 90,
                                  }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleScorePanel(job.id);
                                  }}
                                >
                                  {expandedScores[job.id] ? 'Hide Score' : '★ Score'}
                                </button>
                              )}
                            </div>
                            {/* Inline compact score panel */}
                            {expandedScores[job.id] && scoreDataMap[job.id] && (
                              <div onClick={(e) => e.stopPropagation()} style={{ marginTop: "8px" }}>
                                <CompactScorePanel
                                  composite_score={scoreDataMap[job.id].composite_score}
                                  proximity_score={scoreDataMap[job.id].proximity_score}
                                  skill_score={scoreDataMap[job.id].skill_score}
                                  workload_score={scoreDataMap[job.id].workload_score}
                                  distance_km={scoreDataMap[job.id].distance_km}
                                  active_jobs={scoreDataMap[job.id].active_jobs}
                                  max_capacity={scoreDataMap[job.id].max_capacity}
                                  is_top_3={scoreDataMap[job.id].is_top_3}
                                />
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {/* Pagination */}
                <div style={styles.planningPagination}>
                  <span style={styles.planningPageInfo}>
                    Page <strong>{safePendingPage}</strong> of <strong>{pendingTotalPages}</strong> · {metricFilteredPendingJobs.length} results
                  </span>
                  <div style={styles.planningPageControls}>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPendingPage(1)} disabled={safePendingPage === 1}>«</button>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPendingPage(p => Math.max(1, p - 1))} disabled={safePendingPage === 1}>‹ Prev</button>
                    <div style={styles.planningPageNumbers}>
                      {getPageNums(safePendingPage, pendingTotalPages).map(n => (
                        <button
                          key={n}
                          className={`planning-page-num-style ${n === safePendingPage ? "active" : ""}`}
                          style={{
                            ...styles.planningPageNum,
                            ...(n === safePendingPage ? styles.planningPageNumActive : {})
                          }}
                          onClick={() => setPendingPage(n)}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPendingPage(p => Math.min(pendingTotalPages, p + 1))} disabled={safePendingPage === pendingTotalPages}>Next ›</button>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPendingPage(pendingTotalPages)} disabled={safePendingPage === pendingTotalPages}>»</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* SLA ESCALATIONS TAB */}
      {activeTab === 'escalated' && (
        <section style={{ ...styles.dashboardSection, marginBottom: "8px" }}>
          <div style={styles.sectionContent}>
            {jobsLoading ? (
              <LoadingSpinner message="Loading escalations..." />
            ) : escalatedJobs.length === 0 ? (
              <EmptyState
                title="No active SLA escalations"
                description="Hooray! No jobs are currently in SLA risk state or escalated."
              />
            ) : (
              <div style={styles.tableContainer}>
                <table style={styles.dashboardTable}>
                  <thead>
                    <tr>
                      <th style={styles.dashboardTableTh}>Job ID</th>
                      <th style={styles.dashboardTableTh}>Customer & Description</th>
                      <th style={styles.dashboardTableTh}>Location</th>
                      <th style={styles.dashboardTableTh}>Priority</th>
                      <th style={styles.dashboardTableTh}>Escalation Level</th>
                      <th style={styles.dashboardTableTh}>Escalation Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {escalatedJobs.map((job) => {
                      const isCTO = String(job.status || job.job_status || "").toUpperCase() === "ESCALATED_TO_CTO";
                      return (
                        <tr key={job.id} className="dashboard-table-row">
                          <td style={{ ...styles.dashboardTableTd, ...styles.jobIdCell }}>#{job.id}</td>
                          <td style={{ ...styles.dashboardTableTd, ...styles.customerCell }}>
                            <div>{job.customer_name}</div>
                            {job.issue_description && (
                              <div style={styles.issueSub}>{job.issue_description}</div>
                            )}
                          </td>
                          <td style={styles.dashboardTableTd}>{job.location}</td>
                          <td style={styles.dashboardTableTd}>
                            <span style={getPriorityStyle(job.priority || "")}>
                              {job.priority || "UNKNOWN"}
                            </span>
                          </td>
                          <td style={styles.dashboardTableTd}>
                            <span style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "3px 9px",
                              borderRadius: "20px",
                              backgroundColor: isCTO ? "#fee2e2" : "#fef3c7",
                              color: isCTO ? "#991b1b" : "#92400e",
                              border: `1px solid ${isCTO ? '#fca5a5' : '#fde047'}`
                            }}>
                              {isCTO ? "CTO ESCALATED" : "MANAGER ESCALATED"}
                            </span>
                          </td>
                          <td style={{ ...styles.dashboardTableTd, minWidth: "320px" }}>
                            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                              <button
                                className="assign-btn-style"
                                style={{
                                  ...styles.assignBtn,
                                  backgroundColor: "#10B981"
                                }}
                                onClick={async () => {
                                  const minsStr = prompt("Enter SLA extension time in minutes:", "30");
                                  if (!minsStr) return;
                                  const mins = parseInt(minsStr, 10);
                                  if (isNaN(mins) || mins <= 0) {
                                    alert("Please enter a valid positive number.");
                                    return;
                                  }
                                  try {
                                    await extendSLA(job.id, mins);
                                    showSuccess(`SLA deadline extended by ${mins} minutes.`);
                                    fetchAllData();
                                  } catch (err: any) {
                                    alert(err.response?.data?.detail || "Failed to extend SLA");
                                  }
                                }}
                              >
                                Extend SLA
                              </button>
                              <button
                                className="assign-btn-style"
                                style={{
                                  ...styles.assignBtn,
                                  backgroundColor: "#EF4444"
                                }}
                                onClick={async () => {
                                  const reason = prompt("Enter cancellation reason:", "SLA breach - cancel job");
                                  if (!reason) return;
                                  try {
                                    await cancelEscalatedJob(job.id, reason);
                                    showSuccess(`Job #${job.id} cancelled successfully.`);
                                    fetchAllData();
                                  } catch (err: any) {
                                    alert(err.response?.data?.detail || "Failed to cancel job");
                                  }
                                }}
                              >
                                Cancel Job
                              </button>
                              
                              <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
                                <select
                                  className="tech-select-style"
                                  style={{ ...styles.techSelect, margin: 0, padding: "4px 8px" }}
                                  value={selectedTechs[job.id] || ""}
                                  onChange={(e) => setSelectedTechs(prev => ({ ...prev, [job.id]: e.target.value }))}
                                >
                                  <option value="" disabled>Select Tech</option>
                                  {allTechsList.map(t => (
                                    <option key={t.technician_id} value={t.technician_id}>
                                      {t.technician_name}
                                    </option>
                                  ))}
                                </select>
                                <button
                                  className="assign-btn-style"
                                  style={{
                                    ...styles.assignBtn,
                                    backgroundColor: "#f59e0b",
                                    opacity: selectedTechs[job.id] ? 1 : 0.6
                                  }}
                                  disabled={!selectedTechs[job.id]}
                                  onClick={async () => {
                                    const reason = prompt("Enter force-assignment justification:", "Manager escalation override");
                                    if (!reason) return;
                                    const techId = selectedTechs[job.id];
                                    const tech = allTechsList.find(t => String(t.technician_id) === String(techId));
                                    try {
                                      await forceAssignEscalation(job.id, String(tech?.technician_id || techId), reason);
                                      showSuccess(`Job #${job.id} force-assigned to ${tech?.technician_name || techId}.`);
                                      setSelectedTechs(prev => {
                                        const next = { ...prev };
                                        delete next[job.id];
                                        return next;
                                      });
                                      fetchAllData();
                                    } catch (err: any) {
                                      alert(err.response?.data?.detail || "Failed to force assign job");
                                    }
                                  }}
                                >
                                  Force Assign
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {/* DISPATCH QUEUE TAB */}
      {activeTab === 'dispatch' && (
        <DispatchQueueTable onCountChange={setDispatchQueueCount} />
      )}

      {/* PLANNED ASSIGNMENTS TAB */}
      {activeTab === 'planned' && (
        <section style={{ ...styles.dashboardSection, marginBottom: "8px" }}>
          <div style={styles.sectionContent}>
            {assignmentsLoading ? (
              <LoadingSpinner message="Loading assignments..." />
            ) : (
              <div style={styles.tableContainer}>
                {filteredPlannedAssignments.length === 0 ? (
                  <EmptyState
                    title={searchQuery.trim() ? "No assignments match your search" : "No planned assignments"}
                    description={searchQuery.trim() ? "Try adjusting your search terms." : "No jobs have been assigned to technicians yet."}
                    action={
                      searchQuery.trim() ? (
                        <button
                          className="planning-refresh-btn-style"
                          style={styles.refreshIconBtn}
                          onClick={() => setSearchQuery("")}
                        >
                          Clear Search
                        </button>
                      ) : undefined
                    }
                  />
                ) : (
                  <table style={styles.dashboardTable}>
                    <thead>
                      <tr>
                        <th style={styles.dashboardTableTh}>Job ID</th>
                        <th style={styles.dashboardTableTh}>Technician</th>
                        <th style={styles.dashboardTableTh}>Customer</th>
                        <th style={styles.dashboardTableTh}>Location</th>
                        <th style={styles.dashboardTableTh}>Priority</th>
                        <th style={styles.dashboardTableTh}>Status</th>
                        <th style={styles.dashboardTableTh}>Workload</th>
                        <th style={styles.dashboardTableTh}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPlannedAssignments.map((item) => (
                        <tr key={item.job_id} className="dashboard-table-row">
                          <td style={{ ...styles.dashboardTableTd, ...styles.jobIdCell }}>#{item.job_id}</td>
                          <td style={{ ...styles.dashboardTableTd, ...styles.techCell }}>
                            <strong>{item.technician}</strong>
                            <span style={styles.skillSub}>{item.skill}</span>
                          </td>
                          <td style={{ ...styles.dashboardTableTd, ...styles.customerCell }}>{item.customer}</td>
                          <td style={styles.dashboardTableTd}>{item.location}</td>
                          <td style={styles.dashboardTableTd}>
                            <span style={getPriorityStyle(item.priority || "")}>
                              {item.priority || "UNKNOWN"}
                            </span>
                          </td>
                          <td style={styles.dashboardTableTd}>
                            <span style={{ ...styles.statusBadge, ...styles.statusAssigned }}>ASSIGNED</span>
                          </td>
                          <td style={styles.dashboardTableTd}>
                            <div style={styles.workloadInfo}>
                              <div style={styles.workloadBar}>
                                <div
                                  style={{
                                    ...styles.workloadFill,
                                    width: `${Math.min(
                                      (item.current_jobs / (item.max_jobs || 5)) * 100,
                                      100
                                    )}%`,
                                  }}
                                />
                              </div>
                              <span style={styles.workloadText}>
                                {item.current_jobs}/{item.max_jobs}
                              </span>
                            </div>
                          </td>
                          <td style={styles.dashboardTableTd}>
                            <div style={styles.jobItemActions}>
                              <button
                                className="icon-action-btn-style"
                                style={{ ...styles.iconActionBtn, color: '#16a34a' }}
                                onClick={() => setViewAssignment(item)}
                                title="View assignment"
                                aria-label="View assignment"
                              >
                                <Eye size={15} />
                              </button>
                              <button
                                className="icon-action-btn-style"
                                style={{ ...styles.iconActionBtn, color: '#475569' }}
                                onClick={() => {
                                  setShowOverrideHistoryForJob({ id: item.job_id, title: `${item.customer}'s Job` });
                                }}
                                title="View Override History"
                                aria-label="View Override History"
                              >
                                <History size={15} />
                              </button>
                              <button
                                className="icon-action-btn-style"
                                style={{ ...styles.iconActionBtn, color: '#dc2626' }}
                                onClick={() => {
                                  if (window.confirm(`Are you sure you want to delete assignment for "${item.technician}" → "${item.customer}" (Job #${item.job_id})?`)) {
                                    showSuccess(`Assignment for Job #${item.job_id} removed (connect API for persistence).`);
                                  }
                                }}
                                title="Delete assignment"
                                aria-label="Delete assignment"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {/* Pagination */}
                <div style={styles.planningPagination}>
                  <span style={styles.planningPageInfo}>
                    Page <strong>{safePlannedPage}</strong> of <strong>{plannedTotalPages}</strong> · {filteredPlannedAssignments.length} results
                  </span>
                  <div style={styles.planningPageControls}>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPlannedPage(1)} disabled={safePlannedPage === 1}>«</button>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPlannedPage(p => Math.max(1, p - 1))} disabled={safePlannedPage === 1}>‹ Prev</button>
                    <div style={styles.planningPageNumbers}>
                      {getPageNums(safePlannedPage, plannedTotalPages).map(n => (
                        <button
                          key={n}
                          className={`planning-page-num-style ${n === safePlannedPage ? "active" : ""}`}
                          style={{
                            ...styles.planningPageNum,
                            ...(n === safePlannedPage ? styles.planningPageNumActive : {})
                          }}
                          onClick={() => setPlannedPage(n)}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPlannedPage(p => Math.min(plannedTotalPages, p + 1))} disabled={safePlannedPage === plannedTotalPages}>Next ›</button>
                    <button className="planning-page-btn-style" style={styles.planningPageBtn} onClick={() => setPlannedPage(plannedTotalPages)} disabled={safePlannedPage === plannedTotalPages}>»</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* View Assignment Modal */}
      {viewAssignment && (
        <div style={styles.popupOverlay} onClick={() => setViewAssignment(null)}>
          <div style={styles.viewJobModal} onClick={e => e.stopPropagation()}>
            <div style={styles.viewModalHeader}>
              <h3 style={styles.viewModalHeaderH3}>Assignment Details</h3>
              <button onClick={() => setViewAssignment(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div style={styles.viewModalBody}>
              {viewAssignmentOverride && (
                <div style={{ marginBottom: "16px" }}>
                  <OverrideWarning
                    actorName={viewAssignmentOverride.actor_name}
                    actorRole={viewAssignmentOverride.actor_role}
                    assignedAt={viewAssignmentOverride.created_at}
                    reason={viewAssignmentOverride.justification}
                    onViewHistory={() => setShowOverrideHistoryForView(true)}
                  />
                </div>
              )}
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Job ID</span><span style={styles.viewValue}>#{viewAssignment.job_id}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Technician</span><span style={styles.viewValue}>{viewAssignment.technician}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Skill</span><span style={styles.viewValue}>{viewAssignment.skill}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Customer</span><span style={styles.viewValue}>{viewAssignment.customer}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Location</span><span style={styles.viewValue}>{viewAssignment.location}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Priority</span><span style={getPriorityStyle(viewAssignment.priority || "")}>{viewAssignment.priority || 'UNKNOWN'}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Status</span><span style={{ ...styles.statusBadge, ...styles.statusAssigned }}>ASSIGNED</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Workload</span><span style={styles.viewValue}>{viewAssignment.current_jobs}/{viewAssignment.max_jobs}</span></div>
            </div>
          </div>
        </div>
      )}

      {showHistoryJobId && (
        <ReDispatchHistory
          jobId={showHistoryJobId}
          jobTitle={showHistoryJobTitle}
          onClose={() => {
            setShowHistoryJobId(null);
            setShowHistoryJobTitle("");
          }}
          onManualAssign={handleManualAssign}
          technicians={allTechsList}
          onForceAssignClick={(jobId, jobTitle) => {
            setForceAssignJob({ id: jobId, title: jobTitle });
          }}
          currentUserRole="dispatcher"
        />
      )}

      {forceAssignJob && (
        <OverrideModal
          jobId={forceAssignJob.id}
          jobTitle={forceAssignJob.title}
          initialJobLocation={forceAssignJob.location}
          currentUserRole="dispatcher"
          onClose={() => setForceAssignJob(null)}
          onSuccess={() => {
            setSuccessMsg(`Job #${forceAssignJob.id} has been force-assigned successfully!`);
            setTimeout(() => setSuccessMsg(""), 4000);
            fetchAllData();
            setShowHistoryJobId(null);
            setShowHistoryJobTitle("");
          }}
        />
      )}

      {showOverrideHistoryForJob && (
        <OverrideHistory
          jobId={showOverrideHistoryForJob.id}
          jobTitle={showOverrideHistoryForJob.title}
          onClose={() => setShowOverrideHistoryForJob(null)}
        />
      )}

      {showOverrideHistoryForView && viewAssignment && (
        <OverrideHistory
          jobId={viewAssignment.job_id}
          jobTitle={`${viewAssignment.customer}'s Job`}
          onClose={() => setShowOverrideHistoryForView(false)}
        />
      )}
    </div>
  );
}

export default PlanningDashboard;
