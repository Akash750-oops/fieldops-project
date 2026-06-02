import React, { useEffect, useState, useMemo } from "react";
import LoadingSpinner from "./LoadingSpinner.jsx";
import { Eye, Trash2, History } from "lucide-react";
import OverrideModal from "./notifications/OverrideModal";
import OverrideHistory from "./notifications/OverrideHistory";
import OverrideWarning from "./notifications/OverrideWarning";
import {
  getTechnicians,
  getAvailableTechnicians,
  getPendingJobs,
  getPlannedAssignments,
  assignJob,
  updateTechnicianAvailability,
  manualAssign,
  getOverrideHistory,
} from "../services/planningService.js";
import { CompactScorePanel } from "./assignment/ScoreDisplay";
import RankedTechTable from "./assignment/RankedTechTable";
import ReDispatchHistory from "./notifications/ReDispatchHistory";
import AlertBanner from "./notifications/AlertBanner";
import "./PlanningDashboard.css";

const PAGE_SIZE = 8;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const normalizeStatus = (s) => (s || "").toLowerCase();

const getPriorityClass = (priority) => {
  const p = (priority || "").toUpperCase();
  if (p === "CRITICAL" || p === "P1") return "badge-critical";
  if (p === "HIGH" || p === "P2") return "badge-high";
  if (p === "MEDIUM" || p === "P3") return "badge-medium";
  if (p === "LOW" || p === "P4" || p === "P5") return "badge-low";
  return "badge-default";
};

const getStatusBadgeClass = (status) => {
  const s = normalizeStatus(status);
  if (s === "available") return "status-pill available";
  if (s === "busy") return "status-pill busy";
  if (s === "assigned") return "status-pill assigned";
  if (s === "offline") return "status-pill offline";
  return "status-pill unknown";
};

const AVAILABILITY_OPTIONS = ["Available", "Busy", "Assigned", "Offline"];

// ─── Component ────────────────────────────────────────────────────────────────

function PlanningDashboard() {
  // Data state
  const [pendingJobs, setPendingJobs] = useState([]);
  const [plannedAssignments, setPlannedAssignments] = useState([]);
  const [allTechsStatus, setAllTechsStatus] = useState([]); // for status panel
  const [allTechsList, setAllTechsList] = useState([]); // for dropdown

  // Loading states (per section)
  const [jobsLoading, setJobsLoading] = useState(false);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [techStatusLoading, setTechStatusLoading] = useState(false);

  // Assignment UI
  const [selectedTechs, setSelectedTechs] = useState({});
  const [assigningJobId, setAssigningJobId] = useState(null);
  
  // Score Display state — keyed by job id so each row is independent
  const [expandedScores, setExpandedScores] = useState({});
  const [scoreDataMap, setScoreDataMap] = useState({});

  // Ranked candidate panel
  const [selectedJobForRanking, setSelectedJobForRanking] = useState(null); // job object
  const [rankedCandidates, setRankedCandidates] = useState([]);

  // Availability update
  const [updatingTechId, setUpdatingTechId] = useState(null);

  // Messages
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [assignSuccessMsg, setAssignSuccessMsg] = useState("");

  // Re-dispatch & Override states
  const [showHistoryJobId, setShowHistoryJobId] = useState(null);
  const [showHistoryJobTitle, setShowHistoryJobTitle] = useState("");
  const [forceAssignJob, setForceAssignJob] = useState(null);
  const [showOverrideHistoryForJob, setShowOverrideHistoryForJob] = useState(null);
  const [viewAssignmentOverride, setViewAssignmentOverride] = useState(null);
  const [showOverrideHistoryForView, setShowOverrideHistoryForView] = useState(false);

  const handleManualAssign = async (jobId, techId) => {
    try {
      await manualAssign(jobId, techId);
      showAssignSuccess("Job assigned manually successfully!");
      fetchAllData();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to manually assign job.";
      setError(msg);
    }
  };

  // Tab navigation
  const [activeTab, setActiveTab] = useState("pending");

  // Pagination states
  const [pendingPage, setPendingPage] = useState(1);
  const [plannedPage, setPlannedPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewAssignment, setViewAssignment] = useState(null);

  // ── Fetchers ────────────────────────────────────────────────────────────────

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
      // getAvailableTechnicians returns all techs with full details
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
      // Silent — dropdown falls back to empty
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

  useEffect(() => { fetchAllData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  // ── Ranked Candidate Selection ───────────────────────────────────────────────

  /** Build a sorted ranked list from all technicians for the given job. */
  const generateRankedCandidates = (job) => {
    if (!allTechsList || allTechsList.length === 0) return [];

    // Score each technician (mock algorithm — return scores for all technicians)
    return allTechsList
      .map((t) => {
        const seed = t.technician_id * 13 + (job?.id || 1) * 7;
        const pseudo = (n) => ((seed * n * 31 + 17) % 45) + 50; // deterministic 50-95
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

  const handleJobRowClick = (job) => {
    if (selectedJobForRanking?.id === job.id) {
      // Toggle off
      setSelectedJobForRanking(null);
      setRankedCandidates([]);
      return;
    }
    setSelectedJobForRanking(job);
    setRankedCandidates(generateRankedCandidates(job));
  };

  const handleTopThreeClose = () => {
    setSelectedJobForRanking(null);
    setRankedCandidates([]);
  };

  // ── Assignment ───────────────────────────────────────────────────────────────

  const handleTechSelect = (jobId, techId) => {
    setSelectedTechs((prev) => ({ ...prev, [jobId]: techId }));

    if (techId) {
      // Look up candidate score from deterministic generation
      const job = pendingJobs.find((j) => j.id === jobId);
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
        // Fallback to random generator if not found
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
      // Auto-expand inline score panel for this job
      setExpandedScores((prev) => ({ ...prev, [jobId]: true }));
    } else {
      setExpandedScores((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  const toggleScorePanel = (jobId) => {
    setExpandedScores((prev) => ({ ...prev, [jobId]: !prev[jobId] }));
  };

  const handleAssignJob = async (jobId, techIdOverride) => {
    const techId = techIdOverride || selectedTechs[jobId];
    if (!techId) return;

    // Client-side guard (case-insensitive)
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
      // Clear panel if assigning currently selected ranking job
      if (selectedJobForRanking?.id === jobId) {
        setSelectedJobForRanking(null);
        setRankedCandidates([]);
      }
      const techName = tech ? tech.technician_name : "Technician";
      showAssignSuccess(`${techName} has been assigned to this work.`);
      fetchAllData();
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        "Failed to assign technician.";
      setError(msg);
    } finally {
      setAssigningJobId(null);
    }
  };

  // ── Availability Update ──────────────────────────────────────────────────────

  const handleAvailabilityChange = async (techId, newStatus) => {
    try {
      setUpdatingTechId(techId);
      setError("");
      await updateTechnicianAvailability(techId, newStatus);
      // Update local status panel state immediately (optimistic)
      setAllTechsStatus((prev) =>
        prev.map((t) =>
          t.technician_id === techId
            ? {
              ...t,
              status: newStatus,
              eligible_for_assignment:
                (newStatus === "Available" || newStatus === "Assigned") && t.current_jobs < t.max_jobs,
            }
            : t
        )
      );
      // Also update dropdown list
      setAllTechsList((prev) =>
        prev.map((t) =>
          t.technician_id === techId ? { ...t, technician_status: newStatus } : t
        )
      );
      showSuccess(`${newStatus} status set successfully.`);
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        "Failed to update availability.";
      setError(msg);
    } finally {
      setUpdatingTechId(null);
    }
  };

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(""), 3500);
  };

  const showAssignSuccess = (msg) => {
    setAssignSuccessMsg(msg);
    setTimeout(() => setAssignSuccessMsg(""), 4500);
  };

  const isGlobalLoading = jobsLoading || assignmentsLoading || techStatusLoading;

  const availableCount = allTechsStatus.filter(
    (t) => normalizeStatus(t.status) === "available"
  ).length;

  // Filtered lists for search
  const filteredPendingJobs = useMemo(() => {
    if (!searchQuery.trim()) return pendingJobs;
    const q = searchQuery.toLowerCase().trim();
    return pendingJobs.filter(
      (job) =>
        String(job.id).includes(q) ||
        (job.customer_name && job.customer_name.toLowerCase().includes(q)) ||
        (job.location && job.location.toLowerCase().includes(q)) ||
        (job.issue_description && job.issue_description.toLowerCase().includes(q)) ||
        (job.priority && job.priority.toLowerCase().includes(q))
    );
  }, [pendingJobs, searchQuery]);

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

  // Reset page when search query changes
  useEffect(() => {
    setPendingPage(1);
    setPlannedPage(1);
  }, [searchQuery]);

  // Clamp page to total pages when data changes to prevent empty page views
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredPendingJobs.length / PAGE_SIZE));
    if (pendingPage > totalPages) {
      setPendingPage(totalPages);
    }
  }, [filteredPendingJobs.length, pendingPage]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredPlannedAssignments.length / PAGE_SIZE));
    if (plannedPage > totalPages) {
      setPlannedPage(totalPages);
    }
  }, [filteredPlannedAssignments.length, plannedPage]);

  // Pagination logic
  const pendingTotalPages = Math.max(1, Math.ceil(filteredPendingJobs.length / PAGE_SIZE));
  const safePendingPage = Math.min(pendingPage, pendingTotalPages);
  const paginatedPendingJobs = filteredPendingJobs.slice((safePendingPage - 1) * PAGE_SIZE, safePendingPage * PAGE_SIZE);

  const plannedTotalPages = Math.max(1, Math.ceil(filteredPlannedAssignments.length / PAGE_SIZE));
  const safePlannedPage = Math.min(plannedPage, plannedTotalPages);
  const paginatedPlannedAssignments = filteredPlannedAssignments.slice((safePlannedPage - 1) * PAGE_SIZE, safePlannedPage * PAGE_SIZE);

  const getPageNums = (currentPage, totalPages) => {
    const nums = [];
    const delta = 2;
    for (let i = Math.max(1, currentPage - delta); i <= Math.min(totalPages, currentPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="planning-dashboard">
      <AlertBanner
        onViewHistory={(jobId, jobTitle) => {
          setShowHistoryJobId(jobId);
          setShowHistoryJobTitle(jobTitle);
        }}
        onManualAssignClick={(jobId, jobTitle) => {
          setForceAssignJob({ id: jobId, title: jobTitle });
        }}
        currentUserRole="dispatcher"
      />
      {/* Global messages */}
      {error && (
        <div className="alert-error">
          <span>{error}</span>
          <button
            onClick={() => setError("")}
            className="alert-close-btn"
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}
      {successMsg && (
        <div className="alert-success">
          <span>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg("")}
            className="alert-close-btn"
            aria-label="Dismiss success message"
          >
            &times;
          </button>
        </div>
      )}
      {assignSuccessMsg && (
        <div className="alert-success alert-left-bottom">
          <span>{assignSuccessMsg}</span>
          <button
            onClick={() => setAssignSuccessMsg("")}
            className="alert-close-btn"
            aria-label="Dismiss success message"
          >
            &times;
          </button>
        </div>
      )}

      {/* ── Tab Navigation ── */}
      <div className="planning-tabs">
        <div style={{ display: "flex", gap: "24px" }}>
          <button
            className={`planning-tab ${activeTab === 'pending' ? 'planning-tab-active' : ''}`}
            onClick={() => setActiveTab('pending')}
          >
            <span className="planning-tab-dot pending-dot"></span>
            <span>Pending Jobs</span>
            <span className="planning-tab-count">{pendingJobs.length}</span>
          </button>
          <button
            className={`planning-tab ${activeTab === 'planned' ? 'planning-tab-active' : ''}`}
            onClick={() => setActiveTab('planned')}
          >
            <span className="planning-tab-dot planned-dot"></span>
            <span>Planned Assignments</span>
            <span className="planning-tab-count">{plannedAssignments.length}</span>
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <div className="planning-header-search-wrap">
            <span className="planning-search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search jobs, customers, locations..."
              className="planning-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button
            className="refresh-icon-btn"
            onClick={fetchAllData}
            disabled={isGlobalLoading}
            style={{ marginBottom: 0 }}
          >
            {isGlobalLoading ? "Refreshing..." : "⟳ Refresh"}
          </button>
        </div>
      </div>

      {/* ── Tab Content ── */}

      {/* PENDING JOBS TAB */}
      {activeTab === 'pending' && (
        <section className="dashboard-section">

          {/* ── Ranked Technician Selection Panel (above table, pinned) ── */}
          {selectedJobForRanking && rankedCandidates.length > 0 && (
            <div className="top-three-wrapper">
              <RankedTechTable
                job={selectedJobForRanking}
                candidates={rankedCandidates}
                selectedTechId={selectedTechs[selectedJobForRanking.id] ? parseInt(selectedTechs[selectedJobForRanking.id], 10) : undefined}
                onSelect={(techId) => handleTechSelect(selectedJobForRanking.id, String(techId))}
                onAssign={(techId) => handleAssignJob(selectedJobForRanking.id, String(techId))}
                onClose={handleTopThreeClose}
              />
            </div>
          )}

          <div className="section-content">
            {jobsLoading ? (
              <LoadingSpinner message="Loading pending jobs..." />
            ) : (
              <div className="table-container">
                {filteredPendingJobs.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon"></span>
                    <h3>{searchQuery.trim() ? "No jobs match your search" : "No pending jobs"}</h3>
                    <p>{searchQuery.trim() ? "Try adjusting your search terms." : "All jobs are either assigned or completed."}</p>
                  </div>
                ) : (
                  <table className="dashboard-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Customer</th>
                        <th>Location</th>
                        <th>Priority</th>
                        <th>Assign Technician</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPendingJobs.map((job) => (
                        <tr
                          key={job.id}
                          onClick={() => handleJobRowClick(job)}
                          className={selectedJobForRanking?.id === job.id ? 'selected-job-row' : ''}
                          style={{ cursor: 'pointer' }}
                          title="Click to see top recommended technicians"
                        >
                          <td className="job-id-cell">#{job.id}</td>
                          <td className="customer-cell">
                            <div>{job.customer_name}</div>
                            {job.issue_description && (
                              <div className="issue-sub">{job.issue_description}</div>
                            )}
                          </td>
                          <td>{job.location}</td>
                          <td>
                            <span className={`priority-badge ${getPriorityClass(job.priority)}`}>
                              {job.priority || "UNKNOWN"}
                            </span>
                          </td>
                          <td className="assignment-action-cell">
                            <div className="assignment-ui">
                              <select
                                className="tech-select"
                                value={selectedTechs[job.id] || ""}
                                onChange={(e) => handleTechSelect(job.id, e.target.value)}
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
                                className="assign-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAssignJob(job.id);
                                }}
                                disabled={!selectedTechs[job.id] || assigningJobId === job.id}
                              >
                                {assigningJobId === job.id ? "Assigning…" : "Assign"}
                              </button>
                              <button
                                className="assign-btn"
                                style={{
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
                                  setShowHistoryJobTitle(`${job.service_type} - ${job.location}`);
                                }}
                                title="View Re-Dispatch History"
                              >
                                <History size={16} />
                              </button>
                              {selectedTechs[job.id] && scoreDataMap[job.id] && (
                                <button
                                  className="assign-btn"
                                  style={{
                                    backgroundColor: expandedScores[job.id] ? '#6b7280' : '#10b981',
                                    minWidth: 90,
                                  }}
                                  onClick={() => toggleScorePanel(job.id)}
                                >
                                  {expandedScores[job.id] ? 'Hide Score' : '★ Score'}
                                </button>
                              )}
                            </div>
                            {/* Inline compact score panel */}
                            {expandedScores[job.id] && scoreDataMap[job.id] && (
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
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {/* Pagination */}
                <div className="planning-pagination">
                  <span className="planning-page-info">
                    Page <strong>{safePendingPage}</strong> of <strong>{pendingTotalPages}</strong> · {filteredPendingJobs.length} results
                  </span>
                  <div className="planning-page-controls">
                    <button className="planning-page-btn" onClick={() => setPendingPage(1)} disabled={safePendingPage === 1}>«</button>
                    <button className="planning-page-btn" onClick={() => setPendingPage(p => Math.max(1, p - 1))} disabled={safePendingPage === 1}>‹ Prev</button>
                    <div className="planning-page-numbers">
                      {getPageNums(safePendingPage, pendingTotalPages).map(n => (
                        <button
                          key={n}
                          className={`planning-page-num${n === safePendingPage ? " active" : ""}`}
                          onClick={() => setPendingPage(n)}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                    <button className="planning-page-btn" onClick={() => setPendingPage(p => Math.min(pendingTotalPages, p + 1))} disabled={safePendingPage === pendingTotalPages}>Next ›</button>
                    <button className="planning-page-btn" onClick={() => setPendingPage(pendingTotalPages)} disabled={safePendingPage === pendingTotalPages}>»</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* PLANNED ASSIGNMENTS TAB */}
      {activeTab === 'planned' && (
      <section className="dashboard-section planned-section">
        <div className="section-content">
          {assignmentsLoading ? (
            <LoadingSpinner message="Loading assignments..." />
          ) : (
            <div className="table-container">
              {filteredPlannedAssignments.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon"></span>
                  <h3>{searchQuery.trim() ? "No assignments match your search" : "No planned assignments"}</h3>
                  <p>{searchQuery.trim() ? "Try adjusting your search terms." : "No jobs have been assigned to technicians yet."}</p>
                </div>
              ) : (
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Job ID</th>
                      <th>Technician</th>
                      <th>Customer</th>
                      <th>Location</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Workload</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedPlannedAssignments.map((item) => (
                      <tr key={item.job_id}>
                        <td className="job-id-cell">#{item.job_id}</td>
                        <td className="tech-cell">
                          <div className="tech-info">
                            <strong>{item.technician}</strong>
                            <span className="skill-sub">{item.skill}</span>
                          </div>
                        </td>
                        <td className="customer-cell">{item.customer}</td>
                        <td>{item.location}</td>
                        <td>
                          <span className={`priority-badge ${getPriorityClass(item.priority)}`}>
                            {item.priority || "UNKNOWN"}
                          </span>
                        </td>
                        <td>
                          <span className="status-badge status-assigned">ASSIGNED</span>
                        </td>
                        <td>
                          <div className="workload-info">
                            <div className="workload-bar">
                              <div
                                className="workload-fill"
                                style={{
                                  width: `${Math.min(
                                    (item.current_jobs / (item.max_jobs || 5)) * 100,
                                    100
                                  )}%`,
                                }}
                              />
                            </div>
                            <span className="workload-text">
                              {item.current_jobs}/{item.max_jobs}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="job-item-actions" style={{ border: 'none', padding: 0, margin: 0 }}>
                            <button
                              className="icon-action-btn icon-view"
                              onClick={() => setViewAssignment(item)}
                              title="View assignment"
                              aria-label="View assignment"
                            >
                              <Eye size={15} />
                            </button>
                            <button
                              className="icon-action-btn"
                              style={{ color: '#475569' }}
                              onClick={() => {
                                setShowOverrideHistoryForJob({ id: item.job_id, title: `${item.customer}'s Job` });
                              }}
                              title="View Override History"
                              aria-label="View Override History"
                            >
                              <History size={15} />
                            </button>
                            <button
                              className="icon-action-btn icon-delete"
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
              <div className="planning-pagination">
                <span className="planning-page-info">
                  Page <strong>{safePlannedPage}</strong> of <strong>{plannedTotalPages}</strong> · {filteredPlannedAssignments.length} results
                </span>
                <div className="planning-page-controls">
                  <button className="planning-page-btn" onClick={() => setPlannedPage(1)} disabled={safePlannedPage === 1}>«</button>
                  <button className="planning-page-btn" onClick={() => setPlannedPage(p => Math.max(1, p - 1))} disabled={safePlannedPage === 1}>‹ Prev</button>
                  <div className="planning-page-numbers">
                    {getPageNums(safePlannedPage, plannedTotalPages).map(n => (
                      <button
                        key={n}
                        className={`planning-page-num${n === safePlannedPage ? " active" : ""}`}
                        onClick={() => setPlannedPage(n)}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                  <button className="planning-page-btn" onClick={() => setPlannedPage(p => Math.min(plannedTotalPages, p + 1))} disabled={safePlannedPage === plannedTotalPages}>Next ›</button>
                  <button className="planning-page-btn" onClick={() => setPlannedPage(plannedTotalPages)} disabled={safePlannedPage === plannedTotalPages}>»</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
      )}

      {/* View Assignment Modal */}
      {viewAssignment && (
        <div className="popup-overlay" onClick={() => setViewAssignment(null)}>
          <div className="view-job-modal" onClick={e => e.stopPropagation()}>
            <div className="view-modal-header">
              <h3>Assignment Details</h3>
              <button onClick={() => setViewAssignment(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div className="view-modal-body">
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
              <div className="view-detail-row"><span className="view-label">Job ID</span><span className="view-value">#{viewAssignment.job_id}</span></div>
              <div className="view-detail-row"><span className="view-label">Technician</span><span className="view-value">{viewAssignment.technician}</span></div>
              <div className="view-detail-row"><span className="view-label">Skill</span><span className="view-value">{viewAssignment.skill}</span></div>
              <div className="view-detail-row"><span className="view-label">Customer</span><span className="view-value">{viewAssignment.customer}</span></div>
              <div className="view-detail-row"><span className="view-label">Location</span><span className="view-value">{viewAssignment.location}</span></div>
              <div className="view-detail-row"><span className="view-label">Priority</span><span className={`priority-badge ${getPriorityClass(viewAssignment.priority)}`}>{viewAssignment.priority || 'UNKNOWN'}</span></div>
              <div className="view-detail-row"><span className="view-label">Status</span><span className="status-badge status-assigned">ASSIGNED</span></div>
              <div className="view-detail-row"><span className="view-label">Workload</span><span className="view-value">{viewAssignment.current_jobs}/{viewAssignment.max_jobs}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Score Detail Modal — opens full card on demand from header button */}
      {/* (Inline compact panels render directly in the table rows above) */}

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
