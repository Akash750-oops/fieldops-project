import React, { useEffect, useState } from "react";
import LoadingSpinner from "./LoadingSpinner.jsx";
import {
  getTechnicians,
  getAvailableTechnicians,
  getPendingJobs,
  getPlannedAssignments,
  assignJob,
  updateTechnicianAvailability,
} from "../services/planningService.js";
import { CompactScorePanel } from "./assignment/ScoreDisplay";
import RankedTechTable from "./assignment/RankedTechTable";
import "./PlanningDashboard.css";

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
  if (s === "offline") return "status-pill offline";
  return "status-pill unknown";
};

const AVAILABILITY_OPTIONS = ["Available", "Busy", "Offline"];

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
    if (tech && normalizeStatus(tech.technician_status) !== "available") {
      setError(
        `Cannot assign: ${tech.technician_name} is currently ${tech.technician_status}. Please select an Available technician.`
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
      showSuccess("Job assigned successfully!");
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
                newStatus === "Available" && t.current_jobs < t.max_jobs,
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

  const isGlobalLoading = jobsLoading || assignmentsLoading || techStatusLoading;

  const availableCount = allTechsStatus.filter(
    (t) => normalizeStatus(t.status) === "available"
  ).length;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="planning-dashboard">
      {/* Page Header styled as Card Header */}
      <div className="content-card header-card" style={{ marginBottom: '4px' }}>
        <div className="card-header" style={{ borderBottom: 'none', paddingBottom: 0, marginBottom: 0 }}>
          <div>
            <span className="section-badge">Planning</span>
            <p className="card-subtitle">Optimize resource allocation and assign jobs in real-time</p>
          </div>
          <div className="header-actions-row">
            <button
              className="refresh-icon-btn"
              onClick={fetchAllData}
              disabled={isGlobalLoading}
            >
              {isGlobalLoading ? "Refreshing..." : "⟳ Refresh"}
            </button>
          </div>
        </div>
      </div>

      {/* Global messages */}
      {error && <div className="alert-error">{error}</div>}
      {successMsg && <div className="alert-success">{successMsg}</div>}

      {/* ── Top Grid: Pending Jobs + Technician Status ── */}
      <div className="dashboard-grid">

        {/* SECTION 1 – Pending Jobs */}
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

          <div className="section-header">
            <h2 className="section-title">Pending Jobs</h2>
            <span className="count-badge">{pendingJobs.length} unassigned</span>
            {selectedJobForRanking && (
              <span
                className="count-badge"
                style={{ background: '#FEF3C7', color: '#92400E', marginLeft: 'auto' }}
              >
                ★ Ranking Job #{selectedJobForRanking.id}
              </span>
            )}
          </div>
          <div className="section-content">
            {jobsLoading ? (
              <LoadingSpinner message="Loading pending jobs..." />
            ) : pendingJobs.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon"></span>
                <h3>No pending jobs</h3>
                <p>All jobs are either assigned or completed.</p>
              </div>
            ) : (
              <div className="table-container">
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
                    {pendingJobs.map((job) => (
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
                              <option value="" disabled>Select Technician</option>
                              {allTechsList.map((tech) => {
                                const unavail =
                                  normalizeStatus(tech.technician_status) !== "available";
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
                              onClick={() => handleAssignJob(job.id)}
                              disabled={!selectedTechs[job.id] || assigningJobId === job.id}
                            >
                              {assigningJobId === job.id ? "Assigning…" : "Assign"}
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
              </div>
            )}
          </div>
        </section>

        {/* SECTION 2 – Technician Status Panel */}
        <section className="dashboard-section">
          <div className="section-header">
            <h2 className="section-title">Technician Status</h2>
            <span className="count-badge">{availableCount} available</span>
          </div>
          <div className="section-content">
            {techStatusLoading ? (
              <LoadingSpinner message="Loading technicians..." />
            ) : allTechsStatus.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon"></span>
                <h3>No technicians found</h3>
                <p>No technicians are registered in the system.</p>
              </div>
            ) : (
              <div className="tech-available-list">
                {allTechsStatus.map((tech) => (
                  <div key={tech.technician_id} className="tech-status-card">
                    <div className="tech-avatar">
                      {(tech.technician || "?").charAt(0).toUpperCase()}
                    </div>
                    <div className="tech-status-info">
                      <span className="tech-status-name">{tech.technician}</span>
                      <span className="tech-skill-label">{tech.skill}</span>
                      <span className="tech-location-label">{tech.location}</span>
                      <div className="tech-status-tags">
                        <span className={getStatusBadgeClass(tech.status)}>
                          {tech.status || "Unknown"}
                        </span>
                        {tech.eligible_for_assignment && (
                          <span className="eligible-tag">Ready</span>
                        )}
                        <span className="workload-mini">
                          {tech.current_jobs}/{tech.max_jobs} jobs
                        </span>
                      </div>
                    </div>
                    {/* Inline availability update */}
                    <select
                      className="avail-select"
                      value={tech.status}
                      onChange={(e) =>
                        handleAvailabilityChange(tech.technician_id, e.target.value)
                      }
                      disabled={updatingTechId === tech.technician_id}
                      title="Update availability"
                    >
                      {AVAILABILITY_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ── Full-Width: Planned Assignments ── */}
      <section className="dashboard-section planned-section">
        <div className="section-header">
          <h2 className="section-title">Planned Assignments</h2>
          <span className="count-badge">{plannedAssignments.length} active</span>
        </div>
        <div className="section-content">
          {assignmentsLoading ? (
            <LoadingSpinner message="Loading assignments..." />
          ) : plannedAssignments.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon"></span>
              <h3>No planned assignments</h3>
              <p>No jobs have been assigned to technicians yet.</p>
            </div>
          ) : (
            <div className="table-container">
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
                  </tr>
                </thead>
                <tbody>
                  {plannedAssignments.map((item) => (
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Score Detail Modal — opens full card on demand from header button */}
      {/* (Inline compact panels render directly in the table rows above) */}
    </div>
  );
}

export default PlanningDashboard;
