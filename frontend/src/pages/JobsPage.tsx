import React, { useEffect, useState } from "react";
import api from "../services/api";
import { Eye, Pencil, Trash2 } from "lucide-react";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import EmptyState from "../components/ui/EmptyState";

const JOBS_PAGE_SIZE = 8;

interface JobFormData {
  customer_name: string;
  location: string;
  issue_description: string;
  priority: string;
  service_type: string;
  contact_number: string;
  preferred_service_date: string;
  status: string;
  required_skill?: string;
}

const initialFormData: JobFormData = {
  customer_name: "",
  location: "",
  issue_description: "",
  priority: "",
  service_type: "",
  contact_number: "",
  preferred_service_date: "",
  status: "active",
  required_skill: "",
};

interface Job {
  id: string | number;
  customer_name: string;
  location: string;
  issue_description?: string;
  priority: string;
  service_type: string;
  contact_number?: string;
  preferred_service_date?: string;
  status: string;
  required_skill?: string;
}

const priorities = [
  { label: "Critical", value: "CRITICAL" },
  { label: "High", value: "HIGH" },
  { label: "Medium", value: "MEDIUM" },
  { label: "Low", value: "LOW" },
];

const serviceTypes = [
  { label: "HVAC Repair", value: "HVAC_REPAIR" },
  { label: "Electrical Service", value: "ELECTRICAL_SERVICE" },
  { label: "Plumbing Service", value: "PLUMBING_SERVICE" },
  { label: "Network Support", value: "NETWORK_SUPPORT" },
  { label: "General Maintenance", value: "GENERAL_MAINTENANCE" },
];

const priorityMap: Record<string, string> = { P1: "CRITICAL", P2: "HIGH", P3: "MEDIUM", P4: "LOW", P5: "LOW" };

function normalizeP(p: string): string {
  const up = (p || "").toUpperCase();
  return priorityMap[up] || up;
}

const getPriorityStyle = (priority: string): React.CSSProperties => {
  const p = (priority || "").toUpperCase();
  const base = {
    fontSize: "10px",
    fontWeight: 700,
    padding: "3px 8px",
    borderRadius: "20px",
    textTransform: "uppercase",
    letterSpacing: "0.03em",
    display: "inline-block",
  } as React.CSSProperties;
  if (p === "CRITICAL" || p === "P1") return { ...base, background: "#FAE5E5", color: "#7A2020" };
  if (p === "HIGH" || p === "P2") return { ...base, background: "#FEF0D6", color: "#7A5120" };
  if (p === "MEDIUM" || p === "P3") return { ...base, background: "#FDFBDC", color: "#706020" };
  if (p === "LOW" || p === "P4" || p === "P5") return { ...base, background: "#DDEEE5", color: "#2F4F3E" };
  return { ...base, background: "#F0F4F2", color: "#6B7280" };
};

interface PopupState {
  show: boolean;
  title: string;
  message: string;
  jobId: string | number;
}

function JobCreationForm() {
  const [formData, setFormData] = useState<JobFormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof JobFormData, string>>>({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(false);

  // States for styling hover/focus effects
  const [hoveredBtn, setHoveredBtn] = useState<string | null>(null);
  const [hoveredRow, setHoveredRow] = useState<string | number | null>(null);
  const [focusedInput, setFocusedInput] = useState<string | null>(null);

  const getInputStyle = (name: string, hasError = false) => {
    let style = { ...styles.formInput };
    if (hasError) {
      style = { ...style, ...styles.inputError };
    } else if (focusedInput === name) {
      style = { ...style, ...styles.formInputFocus };
    }
    return style;
  };

  // State variables for list rendering and filtering
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [jobsPage, setJobsPage] = useState(1);

  useEffect(() => {
    setJobsPage(1);
  }, [searchTerm, statusFilter, priorityFilter, serviceFilter]);

  const getFilterServiceTypes = () => {
    const seenNormal = new Set<string>();
    const result: Array<{ value: string; label: string }> = [];
    jobs.forEach(j => {
      if (j.service_type) {
        const val = j.service_type;
        const normalized = val.toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim();
        if (!seenNormal.has(normalized)) {
          seenNormal.add(normalized);
          const predefined = serviceTypes.find(s => (s.value || "").toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim() === normalized);
          result.push({
            value: predefined ? predefined.value : val,
            label: predefined ? predefined.label : val.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
          });
        }
      }
    });
    return result;
  };

  const getFormServiceTypes = () => {
    const list = [...serviceTypes];
    const seenNormal = new Set<string>(list.map(s => (s.value || "").toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim()));

    const tryAdd = (val?: string) => {
      if (!val) return;
      const normalized = val.toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim();
      if (!seenNormal.has(normalized)) {
        seenNormal.add(normalized);
        const label = val.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        list.push({ label, value: val });
      }
    };

    jobs.forEach(j => {
      if (j.service_type) {
        tryAdd(j.service_type);
      }
    });

    if (formData.service_type) {
      tryAdd(formData.service_type);
    }

    return list;
  };

  const [isEditing, setIsEditing] = useState(false);
  const [editingJobId, setEditingJobId] = useState<string | number | null>(null);

  const [popup, setPopup] = useState<PopupState>({ show: false, title: "", message: "", jobId: "" });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [viewJob, setViewJob] = useState<Job | null>(null);

  const fetchJobs = async () => {
    try {
      setJobsLoading(true);
      const response = await api.get("/jobs");
      setJobs(response.data);
    } catch (error) {
      console.error(error);
      setApiError("Unable to fetch jobs. Please check backend API.");
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, []);

  const validateForm = () => {
    const newErrors: Partial<Record<keyof JobFormData, string>> = {};
    if (!formData.customer_name.trim()) newErrors.customer_name = "Customer name is required";
    if (!formData.location.trim()) newErrors.location = "Location is required";
    if (!formData.issue_description.trim()) newErrors.issue_description = "Issue description is required";
    if (!formData.priority) newErrors.priority = "Priority is required";
    if (!formData.service_type) newErrors.service_type = "Service type is required";
    if (!formData.contact_number.trim()) {
      newErrors.contact_number = "Contact number is required";
    } else if (!/^[6-9]\d{9}$/.test(formData.contact_number)) {
      newErrors.contact_number = "Enter a valid 10-digit Indian mobile number";
    }
    if (!formData.preferred_service_date) newErrors.preferred_service_date = "Preferred service date is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const resetForm = () => {
    setFormData(initialFormData);
    setErrors({});
    setIsEditing(false);
    setEditingJobId(null);
    setIsFormOpen(false);
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setErrors(prev => ({ ...prev, [name]: "" }));
    setApiError("");
  };

  const handleEdit = (job: Job) => {
    setIsEditing(true);
    setEditingJobId(job.id);
    setApiError("");
    let jobStatus = job.status || "active";
    const statusLower = jobStatus.toLowerCase().trim();
    if (statusLower === "inprogress") {
      jobStatus = "in progress";
    } else if (statusLower === "canceled") {
      jobStatus = "cancelled";
    }
    setFormData({
      customer_name: job.customer_name || "",
      location: job.location || "",
      issue_description: job.issue_description || "",
      priority: job.priority || "",
      service_type: job.service_type || "",
      contact_number: job.contact_number || "",
      preferred_service_date: job.preferred_service_date || "",
      status: jobStatus,
      required_skill: job.required_skill || "",
    });
    setIsFormOpen(true);
  };

  const handleCancelEdit = () => { resetForm(); setApiError(""); };
  const closePopup = () => setPopup({ show: false, title: "", message: "", jobId: "" });

  const handleCreateNew = () => {
    setFormData(initialFormData);
    setErrors({});
    setIsEditing(false);
    setEditingJobId(null);
    setApiError("");
    setIsFormOpen(true);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validateForm()) return;
    try {
      setLoading(true);
      if (isEditing && editingJobId !== null) {
        const response = await api.put(`/jobs/${editingJobId}`, formData);
        setPopup({ show: true, title: "Job Updated Successfully", message: "The job details have been updated successfully.", jobId: response.data?.id ?? editingJobId });
      } else {
        const response = await api.post("/jobs", formData);
        setPopup({ show: true, title: "Job Created Successfully", message: "Your job request has been submitted successfully.", jobId: response.data?.id ?? "" });
      }
      resetForm();
      fetchJobs();
    } catch (error: any) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to save job. Please check backend API.";
      setApiError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string | number) => {
    const job = jobs.find(j => j.id === id);
    const name = job?.customer_name || `Job #${id}`;
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      setJobsLoading(true);
      await api.delete(`/jobs/${id}`);
      setPopup({ show: true, title: "Job Deleted", message: "The job has been removed successfully.", jobId: id });
      fetchJobs();
    } catch (error) {
      console.error(error);
      setApiError("Unable to delete job. Please check backend API.");
    } finally {
      setJobsLoading(false);
    }
  };

  const filteredJobs = jobs
    .filter(j => {
      if (statusFilter === "ALL") return true;
      const jobStatus = (j.status || "active").toLowerCase().trim().replace(" ", "");
      const filterStatus = statusFilter.toLowerCase().trim().replace(" ", "");
      const normJS = jobStatus === "canceled" ? "cancelled" : jobStatus;
      const normFS = filterStatus === "canceled" ? "cancelled" : filterStatus;
      return normJS === normFS;
    })
    .filter(j => {
      if (priorityFilter === "ALL") return true;
      return normalizeP(j.priority) === priorityFilter;
    })
    .filter(j => {
      if (serviceFilter === "ALL") return true;
      const norm = (val?: string) => (val || "").toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim();
      return norm(j.service_type) === norm(serviceFilter);
    })
    .filter(j => {
      const s = searchTerm.toLowerCase();
      return (
        (j.customer_name && j.customer_name.toLowerCase().includes(s)) ||
        (j.location && j.location.toLowerCase().includes(s)) ||
        (j.issue_description && j.issue_description.toLowerCase().includes(s))
      );
    });

  const jobsTotalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PAGE_SIZE));
  const safeJobsPage = Math.min(jobsPage, jobsTotalPages);
  const paginatedJobs = filteredJobs.slice((safeJobsPage - 1) * JOBS_PAGE_SIZE, safeJobsPage * JOBS_PAGE_SIZE);

  useEffect(() => {
    const total = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PAGE_SIZE));
    if (jobsPage > total) {
      setJobsPage(total);
    }
  }, [filteredJobs.length, jobsPage]);

  const getJobsPageNums = () => {
    const nums: number[] = [];
    const delta = 2;
    for (let i = Math.max(1, safeJobsPage - delta); i <= Math.min(jobsTotalPages, safeJobsPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  const formatStatus = (status: string) => {
    const s = (status || "active").toLowerCase().trim();
    if (s === "inprogress" || s === "in progress") return "In Progress";
    if (s === "canceled" || s === "cancelled") return "Cancelled";
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  const getStatusStyle = (status: string): React.CSSProperties => {
    const s = (status || "").toLowerCase().trim();
    const base = {
      fontSize: "10px",
      fontWeight: 600,
      padding: "2px 9px",
      borderRadius: "20px",
      textTransform: "capitalize",
      display: "inline-block",
    } as React.CSSProperties;
    if (s === "inprogress" || s === "in progress") return { ...base, background: "#FEF3DC", color: "#7A5120" };
    if (s === "completed") return { ...base, background: "#E8F0FE", color: "#2F5090" };
    if (s === "canceled" || s === "cancelled") return { ...base, background: "#FAE5E5", color: "#7A2020" };
    return { ...base, background: "#DDEEE5", color: "#2F4F3E" };
  };

  return (
    <div style={styles.jobsPage}>
      {/* Success Popup */}
      {popup.show && (
        <div style={styles.popupOverlay}>
          <div style={styles.successPopup}>
            <div style={styles.successIcon}>✓</div>
            <h3>{popup.title}</h3>
            {popup.jobId && <div style={styles.jobIdBox}>Job ID: <strong>#{popup.jobId}</strong></div>}
            <p>{popup.message}</p>
            <button
              type="button"
              style={hoveredBtn === 'popupClose' ? { ...styles.popupCloseBtn, background: '#5C9470' } : styles.popupCloseBtn}
              onMouseEnter={() => setHoveredBtn('popupClose')}
              onMouseLeave={() => setHoveredBtn(null)}
              onClick={closePopup}
            >
              OK
            </button>
          </div>
        </div>
      )}


      {/* Main Content: List Only (Form moved to Sidebar) */}
      <div style={styles.mainContentRow}>
        {/* Job Management List */}
        <div style={styles.contentCard}>
          <div style={styles.cardHeader}>
            <div>
              <p style={styles.cardSubtitle}>View and manage all submitted job requests</p>
            </div>
            <div style={styles.headerActionsRow}>
              <button
                style={hoveredBtn === 'refresh' ? { ...styles.refreshIconBtn, background: "#F6FAF8", borderColor: "#7AAE8A" } : styles.refreshIconBtn}
                onMouseEnter={() => setHoveredBtn('refresh')}
                onMouseLeave={() => setHoveredBtn(null)}
                onClick={fetchJobs}
                title="Refresh"
              >
                ⟳ Refresh
              </button>
              <button
                style={hoveredBtn === 'add' ? { ...styles.addJobBtn, background: "#5C9470" } : styles.addJobBtn}
                onMouseEnter={() => setHoveredBtn('add')}
                onMouseLeave={() => setHoveredBtn(null)}
                onClick={handleCreateNew}
              >
                + Create Job
              </button>
            </div>
          </div>

          {/* Filters */}
          <div style={styles.filtersRow}>
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Search</label>
              <input
                type="text"
                placeholder="Search name, location..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                onFocus={() => setFocusedInput('search')}
                onBlur={() => setFocusedInput(null)}
                style={focusedInput === 'search' ? { ...styles.filterInput, ...styles.filterInputFocus } : styles.filterInput}
              />
            </div>
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Status</label>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                onFocus={() => setFocusedInput('statusFilter')}
                onBlur={() => setFocusedInput(null)}
                style={focusedInput === 'statusFilter' ? { ...styles.filterInput, ...styles.filterInputFocus } : styles.filterInput}
              >
                <option value="ALL">All Statuses</option>
                <option value="active">Active</option>
                <option value="in progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Priority</label>
              <select
                value={priorityFilter}
                onChange={e => setPriorityFilter(e.target.value)}
                onFocus={() => setFocusedInput('priorityFilter')}
                onBlur={() => setFocusedInput(null)}
                style={focusedInput === 'priorityFilter' ? { ...styles.filterInput, ...styles.filterInputFocus } : styles.filterInput}
              >
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Service</label>
              <select
                value={serviceFilter}
                onChange={e => setServiceFilter(e.target.value)}
                onFocus={() => setFocusedInput('serviceFilter')}
                onBlur={() => setFocusedInput(null)}
                style={focusedInput === 'serviceFilter' ? { ...styles.filterInput, ...styles.filterInputFocus } : styles.filterInput}
              >
                <option value="ALL">All Services</option>
                {getFilterServiceTypes().map(st => (
                  <option key={st.value} value={st.value}>
                    {st.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Jobs Count */}
          <p style={styles.resultsCount}>{filteredJobs.length} job{filteredJobs.length !== 1 ? "s" : ""} found</p>

          {/* Job Table */}
          <div style={styles.tableContainer}>
            {jobsLoading ? (
              <LoadingSpinner message="Loading jobs..." />
            ) : filteredJobs.length === 0 ? (
              <EmptyState
                title={
                  (searchTerm && searchTerm.trim()) ||
                  statusFilter !== "ALL" ||
                  priorityFilter !== "ALL" ||
                  serviceFilter !== "ALL"
                    ? "No jobs match your filters"
                    : "No jobs found"
                }
                description={
                  (searchTerm && searchTerm.trim()) ||
                  statusFilter !== "ALL" ||
                  priorityFilter !== "ALL" ||
                  serviceFilter !== "ALL"
                    ? "Try adjusting your search terms or filters."
                    : "Get started by creating your first job request."
                }
                action={
                  ((searchTerm && searchTerm.trim()) ||
                    statusFilter !== "ALL" ||
                    priorityFilter !== "ALL" ||
                    serviceFilter !== "ALL") ? (
                    <button
                      style={hoveredBtn === 'clearFilters' ? { ...styles.refreshIconBtn, background: '#F6FAF8', borderColor: '#7AAE8A' } : styles.refreshIconBtn}
                      onMouseEnter={() => setHoveredBtn('clearFilters')}
                      onMouseLeave={() => setHoveredBtn(null)}
                      onClick={() => {
                        setSearchTerm("");
                        setStatusFilter("ALL");
                        setPriorityFilter("ALL");
                        setServiceFilter("ALL");
                      }}
                    >
                      Clear Filters
                    </button>
                  ) : (
                    <button
                      style={hoveredBtn === 'emptyAdd' ? { ...styles.addJobBtn, background: '#5C9470' } : styles.addJobBtn}
                      onMouseEnter={() => setHoveredBtn('emptyAdd')}
                      onMouseLeave={() => setHoveredBtn(null)}
                      onClick={handleCreateNew}
                    >
                      + Create Job
                    </button>
                  )
                }
              />
            ) : (
              <table style={styles.dashboardTable}>
                <thead>
                  <tr>
                    <th style={styles.th}>Job ID</th>
                    <th style={styles.th}>Customer</th>
                    <th style={styles.th}>Location</th>
                    <th style={styles.th}>Priority</th>
                    <th style={styles.th}>Service Type</th>
                    <th style={styles.th}>Preferred Date</th>
                    <th style={styles.th}>Status</th>
                    <th style={styles.th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedJobs.map(job => (
                    <tr
                      key={job.id}
                      style={hoveredRow === job.id ? { background: "#F8FBF9" } : undefined}
                      onMouseEnter={() => setHoveredRow(job.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                    >
                      <td style={{ ...styles.td, ...styles.jobIdCell }}>#{job.id}</td>
                      <td style={{ ...styles.td, ...styles.customerCell }}>
                        <div><strong>{job.customer_name}</strong></div>
                        {job.issue_description && (
                          <div style={styles.issueSub}>{job.issue_description}</div>
                        )}
                      </td>
                      <td style={styles.td}>{job.location}</td>
                      <td style={styles.td}>
                        <span style={getPriorityStyle(job.priority)}>
                          {normalizeP(job.priority)}
                        </span>
                      </td>
                      <td style={styles.td}>{job.service_type?.replace(/_/g, " ")}</td>
                      <td style={styles.td}>{job.preferred_service_date}</td>
                      <td style={styles.td}>
                        <span style={getStatusStyle(job.status)}>{formatStatus(job.status)}</span>
                      </td>
                      <td style={styles.td}>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            style={{ ...styles.iconActionBtn, color: "#16a34a" }}
                            onClick={() => setViewJob(job)}
                            title="View job details"
                            aria-label="View job"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            style={{ ...styles.iconActionBtn, color: "#ca8a04" }}
                            onClick={() => handleEdit(job)}
                            title="Edit job"
                            aria-label="Edit job"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            style={{ ...styles.iconActionBtn, color: "#dc2626" }}
                            onClick={() => handleDelete(job.id)}
                            title="Delete job"
                            aria-label="Delete job"
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
          </div>
          {/* Pagination */}
          {!jobsLoading && (
            <div style={styles.jobsPagination}>
              <span style={styles.jobsPageInfo}>
                Page <strong style={{ color: "#2F4F3E" }}>{safeJobsPage}</strong> of <strong style={{ color: "#2F4F3E" }}>{jobsTotalPages}</strong> · {filteredJobs.length} results
              </span>
              <div style={styles.jobsPageControls}>
                <button
                  style={safeJobsPage === 1 ? { ...styles.jobsPageBtn, opacity: 0.4, cursor: "not-allowed" } : styles.jobsPageBtn}
                  type="button"
                  onClick={() => setJobsPage(1)}
                  disabled={safeJobsPage === 1}
                >
                  «
                </button>
                <button
                  style={safeJobsPage === 1 ? { ...styles.jobsPageBtn, opacity: 0.4, cursor: "not-allowed" } : styles.jobsPageBtn}
                  type="button"
                  onClick={() => setJobsPage(p => Math.max(1, p - 1))}
                  disabled={safeJobsPage === 1}
                >
                  ‹ Prev
                </button>
                <div style={styles.jobsPageNumbers}>
                  {getJobsPageNums().map(n => (
                    <button
                      key={n}
                      type="button"
                      style={
                        n === safeJobsPage
                          ? { ...styles.jobsPageNum, background: "#7AAE8A", borderColor: "#7AAE8A", color: "#fff" }
                          : styles.jobsPageNum
                      }
                      onClick={() => setJobsPage(n)}
                    >
                      {n}
                    </button>
                  ))}
                </div>
                <button
                  style={safeJobsPage === jobsTotalPages ? { ...styles.jobsPageBtn, opacity: 0.4, cursor: "not-allowed" } : styles.jobsPageBtn}
                  type="button"
                  onClick={() => setJobsPage(p => Math.min(jobsTotalPages, p + 1))}
                  disabled={safeJobsPage === jobsTotalPages}
                >
                  Next ›
                </button>
                <button
                  style={safeJobsPage === jobsTotalPages ? { ...styles.jobsPageBtn, opacity: 0.4, cursor: "not-allowed" } : styles.jobsPageBtn}
                  type="button"
                  onClick={() => setJobsPage(jobsTotalPages)}
                  disabled={safeJobsPage === jobsTotalPages}
                >
                  »
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* View Job Modal */}
      {viewJob && (
        <div style={styles.popupOverlay} onClick={() => setViewJob(null)}>
          <div style={styles.viewJobModal} onClick={e => e.stopPropagation()}>
            <div style={styles.viewModalHeader}>
              <h3 style={styles.viewModalHeaderTitle}>Job Details</h3>
              <button onClick={() => setViewJob(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div style={styles.viewModalBody}>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Job ID</span><span style={styles.viewValue}>#{viewJob.id}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Customer</span><span style={styles.viewValue}>{viewJob.customer_name}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Location</span><span style={styles.viewValue}>{viewJob.location}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Priority</span><span style={getPriorityStyle(viewJob.priority)}>{normalizeP(viewJob.priority)}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Service Type</span><span style={styles.viewValue}>{viewJob.service_type?.replace(/_/g, ' ')}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Contact</span><span style={styles.viewValue}>{viewJob.contact_number}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Preferred Date</span><span style={styles.viewValue}>{viewJob.preferred_service_date}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Status</span><span style={getStatusStyle(viewJob.status)}>{formatStatus(viewJob.status)}</span></div>
              {viewJob.issue_description && (
                <div style={{ ...styles.viewDetailRow, flexDirection: "column", gap: "4px" }}>
                  <span style={styles.viewLabel}>Issue</span>
                  <span style={styles.viewValue}>{viewJob.issue_description}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Sliding Sidebar for Job Form — rendered outside main div to avoid overflow:hidden clipping */}
      <div style={{
        ...styles.jobFormSidebar,
        right: isFormOpen ? 0 : "-420px",
      }}>
        <div style={styles.sidebarHeader}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#2F4F3E" }}>{isEditing ? "Edit Job" : "Create New Job"}</h3>
          <button style={styles.closeSidebar} onClick={() => setIsFormOpen(false)}>×</button>
        </div>
        <div style={styles.sidebarBody}>
          {apiError && <div style={styles.alertError}>{apiError}</div>}
          <form onSubmit={handleSubmit} style={styles.jobForm}>
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Customer Name <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="customer_name"
                value={formData.customer_name}
                onChange={handleChange}
                onFocus={() => setFocusedInput('customer_name')}
                onBlur={() => setFocusedInput(null)}
                placeholder="Enter customer name"
                style={getInputStyle('customer_name', !!errors.customer_name)}
              />
              {errors.customer_name && <span style={styles.fieldError}>{errors.customer_name}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Location <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="location"
                value={formData.location}
                onChange={handleChange}
                onFocus={() => setFocusedInput('location')}
                onBlur={() => setFocusedInput(null)}
                placeholder="Enter location"
                style={getInputStyle('location', !!errors.location)}
              />
              {errors.location && <span style={styles.fieldError}>{errors.location}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Priority <span style={styles.req}>*</span></label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                onFocus={() => setFocusedInput('priority')}
                onBlur={() => setFocusedInput(null)}
                style={getInputStyle('priority', !!errors.priority)}
              >
                <option value="">Select priority</option>
                {priorities.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              {errors.priority && <span style={styles.fieldError}>{errors.priority}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Service Type <span style={styles.req}>*</span></label>
              <select
                name="service_type"
                value={formData.service_type}
                onChange={handleChange}
                onFocus={() => setFocusedInput('service_type')}
                onBlur={() => setFocusedInput(null)}
                style={getInputStyle('service_type', !!errors.service_type)}
              >
                <option value="">Select service type</option>
                {getFormServiceTypes().map(st => (
                  <option key={st.value} value={st.value}>{st.label}</option>
                ))}
              </select>
              {errors.service_type && <span style={styles.fieldError}>{errors.service_type}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Contact Number <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="contact_number"
                value={formData.contact_number}
                onChange={handleChange}
                onFocus={() => setFocusedInput('contact_number')}
                onBlur={() => setFocusedInput(null)}
                placeholder="9876543210"
                maxLength={10}
                style={getInputStyle('contact_number', !!errors.contact_number)}
              />
              {errors.contact_number && <span style={styles.fieldError}>{errors.contact_number}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Preferred Service Date <span style={styles.req}>*</span></label>
              <input
                type="date"
                name="preferred_service_date"
                value={formData.preferred_service_date}
                onChange={handleChange}
                onFocus={() => setFocusedInput('preferred_service_date')}
                onBlur={() => setFocusedInput(null)}
                style={getInputStyle('preferred_service_date', !!errors.preferred_service_date)}
              />
              {errors.preferred_service_date && <span style={styles.fieldError}>{errors.preferred_service_date}</span>}
            </div>

            {isEditing && (
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Status <span style={styles.req}>*</span></label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  onFocus={() => setFocusedInput('status')}
                  onBlur={() => setFocusedInput(null)}
                  style={getInputStyle('status')}
                >
                  <option value="active">Active</option>
                  <option value="in progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            )}

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Issue Description <span style={styles.req}>*</span></label>
              <textarea
                name="issue_description"
                value={formData.issue_description}
                onChange={handleChange}
                onFocus={() => setFocusedInput('issue_description')}
                onBlur={() => setFocusedInput(null)}
                placeholder="Describe the issue in detail..."
                rows={4}
                style={getInputStyle('issue_description', !!errors.issue_description)}
              />
              {errors.issue_description && <span style={styles.fieldError}>{errors.issue_description}</span>}
            </div>

            <div style={styles.formActions}>
              <button
                type="submit"
                style={
                  loading
                    ? { ...styles.btnPrimary, background: '#A8CDB5', cursor: 'not-allowed', boxShadow: 'none' }
                    : hoveredBtn === 'submit'
                    ? { ...styles.btnPrimary, background: '#5C9470' }
                    : styles.btnPrimary
                }
                disabled={loading}
                onMouseEnter={() => setHoveredBtn('submit')}
                onMouseLeave={() => setHoveredBtn(null)}
              >
                {loading ? "Submitting..." : isEditing ? "Update Job" : "Create Job"}
              </button>
              <button
                type="button"
                style={hoveredBtn === 'cancel' ? { ...styles.btnSecondary, background: '#EAF4EE', borderColor: '#7AAE8A' } : styles.btnSecondary}
                onClick={handleCancelEdit}
                onMouseEnter={() => setHoveredBtn('cancel')}
                onMouseLeave={() => setHoveredBtn(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
      {isFormOpen && <div style={styles.sidebarOverlay} onClick={() => setIsFormOpen(false)}></div>}
    </div>
  );
}

const styles = {
  jobsPage: {
    fontFamily: "'Inter', sans-serif",
    background: "#EEF4F1",
    minHeight: "100vh",
    padding: "14px",
    color: "#1F2933",
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,
  popupOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(31, 41, 51, 0.4)",
    zIndex: 2000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  } as React.CSSProperties,
  successPopup: {
    background: "#FFFFFF",
    borderRadius: "16px",
    padding: "32px",
    maxWidth: "380px",
    width: "90%",
    textAlign: "center",
    boxShadow: "0 20px 50px rgba(47, 79, 62, 0.15)",
  } as React.CSSProperties,
  successIcon: {
    width: "52px",
    height: "52px",
    background: "#DDEEE5",
    color: "#2F4F3E",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px",
    fontWeight: 800,
    margin: "0 auto 14px",
  } as React.CSSProperties,
  jobIdBox: {
    background: "#F6FAF8",
    borderRadius: "6px",
    padding: "6px 14px",
    fontSize: "13px",
    color: "#2F4F3E",
    marginBottom: "10px",
    display: "inline-block",
    border: "1px solid #E3ECE7",
  } as React.CSSProperties,
  popupCloseBtn: {
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    padding: "10px 28px",
    borderRadius: "8px",
    fontWeight: 700,
    fontSize: "13px",
    cursor: "pointer",
    transition: "background .2s",
  } as React.CSSProperties,
  mainContentRow: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "20px",
    alignItems: "start",
  } as React.CSSProperties,
  contentCard: {
    background: "#FFFFFF",
    borderRadius: "12px",
    padding: "22px",
    boxShadow: "0 1px 4px rgba(47, 79, 62, 0.07)",
    border: "1px solid #E3ECE7",
  } as React.CSSProperties,
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "12px",
    marginBottom: "16px",
    paddingBottom: "14px",
    borderBottom: "1px solid #E3ECE7",
  } as React.CSSProperties,
  cardSubtitle: {
    fontSize: "12px",
    color: "#6B7280",
    marginTop: "3px",
  } as React.CSSProperties,
  headerActionsRow: {
    display: "flex",
    gap: "8px",
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
    boxShadow: "0 1px 3px rgba(47,79,62,.06)",
  } as React.CSSProperties,
  addJobBtn: {
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    padding: "7px 16px",
    borderRadius: "8px",
    fontWeight: 700,
    fontSize: "12px",
    cursor: "pointer",
    transition: "background .2s",
    boxShadow: "0 2px 6px rgba(122, 174, 138, 0.3)",
  } as React.CSSProperties,
  filtersRow: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr 1fr 1fr",
    gap: "10px",
    marginBottom: "14px",
  } as React.CSSProperties,
  filterGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  } as React.CSSProperties,
  filterLabel: {
    fontSize: "10px",
    fontWeight: 700,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: ".05em",
  } as React.CSSProperties,
  filterInput: {
    padding: "7px 10px",
    border: "1.5px solid #E3ECE7",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#1F2933",
    outline: "none",
    transition: "border-color .2s",
    background: "#FFFFFF",
  } as React.CSSProperties,
  filterInputFocus: {
    borderColor: "#7AAE8A",
    boxShadow: "0 0 0 2px rgba(122,174,138,.12)",
  } as React.CSSProperties,
  resultsCount: {
    fontSize: "11px",
    color: "#6B7280",
    fontWeight: 500,
    marginBottom: "10px",
  } as React.CSSProperties,
  tableContainer: {
    overflowX: "auto",
  } as React.CSSProperties,
  dashboardTable: {
    width: "100%",
    borderCollapse: "collapse",
  } as React.CSSProperties,
  th: {
    background: "#F6FAF8",
    padding: "8px 10px",
    textAlign: "left",
    fontSize: "9.5px",
    fontWeight: 700,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    borderBottom: "1px solid #E3ECE7",
  } as React.CSSProperties,
  td: {
    padding: "8px 10px",
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
  viewJobModal: {
    background: "#FFFFFF",
    borderRadius: "16px",
    padding: 0,
    maxWidth: "460px",
    width: "94%",
    boxShadow: "0 20px 50px rgba(47,79,62,.18)",
    overflow: "hidden",
  } as React.CSSProperties,
  viewModalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "18px 22px 14px",
    borderBottom: "1px solid #E3ECE7",
    background: "#F6FAF8",
  } as React.CSSProperties,
  viewModalHeaderTitle: {
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
  jobFormSidebar: {
    position: "fixed",
    top: 0,
    width: "420px",
    height: "100vh",
    background: "#FFFFFF",
    zIndex: 2000,
    boxShadow: "-4px 0 24px rgba(47,79,62,.1)",
    display: "flex",
    flexDirection: "column",
    transition: "right .3s cubic-bezier(0.4, 0, 0.2, 1)",
  } as React.CSSProperties,
  sidebarHeader: {
    padding: "20px 24px",
    borderBottom: "1px solid #E3ECE7",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#F8FBF9",
  } as React.CSSProperties,
  closeSidebar: {
    background: "none",
    border: "none",
    fontSize: "22px",
    color: "#6B7280",
    cursor: "pointer",
    width: "32px",
    height: "32px",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background .15s",
  } as React.CSSProperties,
  sidebarBody: {
    flex: 1,
    overflowY: "auto",
    padding: "24px",
  } as React.CSSProperties,
  sidebarOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(31,41,51,.35)",
    zIndex: 1999,
    backdropFilter: "blur(2px)",
  } as React.CSSProperties,
  jobForm: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  } as React.CSSProperties,
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  } as React.CSSProperties,
  formLabel: {
    fontSize: "12px",
    fontWeight: 600,
    color: "#2F4F3E",
    marginBottom: "4px",
  } as React.CSSProperties,
  req: {
    color: "#D96C6C",
  } as React.CSSProperties,
  formInput: {
    padding: "9px 12px",
    border: "1.5px solid #E3ECE7",
    borderRadius: "8px",
    fontSize: "13px",
    fontFamily: "'Inter', sans-serif",
    color: "#1F2933",
    background: "#FFFFFF",
    outline: "none",
    width: "100%",
    transition: "border-color .2s, box-shadow .2s",
  } as React.CSSProperties,
  formInputFocus: {
    borderColor: "#7AAE8A",
    boxShadow: "0 0 0 3px rgba(122, 174, 138, 0.15)",
  } as React.CSSProperties,
  inputError: {
    borderColor: "#D96C6C",
    boxShadow: "0 0 0 2px rgba(217,108,108,.1)",
  } as React.CSSProperties,
  fieldError: {
    fontSize: "11px",
    color: "#D96C6C",
    marginTop: "2px",
  } as React.CSSProperties,
  alertError: {
    background: "#FDF2F2",
    color: "#9B3A3A",
    border: "1px solid #F5C6C6",
    borderRadius: "8px",
    padding: "10px 14px",
    fontSize: "12px",
    fontWeight: 500,
    marginBottom: "14px",
  } as React.CSSProperties,
  formActions: {
    display: "flex",
    gap: "10px",
    marginTop: "10px",
  } as React.CSSProperties,
  btnPrimary: {
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    padding: "10px 20px",
    borderRadius: "8px",
    fontWeight: 700,
    fontSize: "13px",
    cursor: "pointer",
    transition: "background .2s",
    flex: 1,
    boxShadow: "0 2px 6px rgba(122,174,138,.25)",
  } as React.CSSProperties,
  btnSecondary: {
    background: "#F6FAF8",
    color: "#2F4F3E",
    border: "1.5px solid #E3ECE7",
    padding: "10px 16px",
    borderRadius: "8px",
    fontWeight: 600,
    fontSize: "13px",
    cursor: "pointer",
    transition: "all .2s",
  } as React.CSSProperties,
  jobsPagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 0 0 0",
    borderTop: "1px solid #E3ECE7",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "14px",
  } as React.CSSProperties,
  jobsPageInfo: {
    fontSize: "11px",
    color: "#6B7280",
    fontWeight: 500,
  } as React.CSSProperties,
  jobsPageControls: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  } as React.CSSProperties,
  jobsPageBtn: {
    padding: "5px 12px",
    background: "#FFFFFF",
    border: "1.5px solid #E3ECE7",
    borderRadius: "7px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#2F4F3E",
    cursor: "pointer",
    transition: "all .2s",
  } as React.CSSProperties,
  jobsPageNumbers: {
    display: "flex",
    gap: "4px",
  } as React.CSSProperties,
  jobsPageNum: {
    width: "26px",
    height: "26px",
    borderRadius: "7px",
    border: "1.5px solid #E3ECE7",
    background: "#FFFFFF",
    fontSize: "11px",
    fontWeight: 600,
    color: "#6B7280",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all .2s",
  } as React.CSSProperties,
  iconActionBtn: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: "28px",
    height: "28px",
    border: "none",
    background: "none",
    padding: 0,
    cursor: "pointer",
    transition: "transform .15s, opacity .15s",
    outline: "none",
  } as React.CSSProperties,
};

export default JobCreationForm;
