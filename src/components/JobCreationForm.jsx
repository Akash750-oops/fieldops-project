import React, { useEffect, useState } from "react";
import axios from "axios";
import { Eye, Pencil, Trash2 } from "lucide-react";
import LoadingSpinner from "./LoadingSpinner.jsx";
import "./JobCreationForm.css";

const API_URL = "http://localhost:8000/jobs";
const JOBS_PAGE_SIZE = 8;

const initialFormData = {
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

const priorityColors = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
  P1: "#ef4444",
};

const priorityMap = { P1: "CRITICAL", P2: "HIGH", P3: "MEDIUM", P4: "LOW", P5: "LOW" };

function normalizeP(p) {
  const up = (p || "").toUpperCase();
  return priorityMap[up] || up;
}

const getPriorityClass = (priority) => {
  const p = (priority || "").toUpperCase();
  if (p === "CRITICAL" || p === "P1") return "badge-critical";
  if (p === "HIGH" || p === "P2") return "badge-high";
  if (p === "MEDIUM" || p === "P3") return "badge-medium";
  if (p === "LOW" || p === "P4" || p === "P5") return "badge-low";
  return "badge-default";
};

function JobCreationForm() {
  const [formData, setFormData] = useState(initialFormData);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(false);

  // Missing state variables for list rendering and filtering
  const [jobs, setJobs] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [jobsPage, setJobsPage] = useState(1);

  useEffect(() => {
    setJobsPage(1);
  }, [searchTerm, statusFilter, priorityFilter, serviceFilter]);

  const getFilterServiceTypes = () => {
    const seenNormal = new Set();
    const result = [];
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
    const seenNormal = new Set(list.map(s => (s.value || "").toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim()));

    const tryAdd = (val) => {
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
  const [editingJobId, setEditingJobId] = useState(null);

  const [popup, setPopup] = useState({ show: false, title: "", message: "", jobId: "" });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [viewJob, setViewJob] = useState(null);

  const fetchJobs = async () => {
    try {
      setJobsLoading(true);
      const response = await axios.get(API_URL);
      setJobs(response.data);
    } catch (error) {
      console.error(error);
      setApiError("Unable to fetch jobs. Please check backend API.");
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, []);

  // KPI calculations
  const totalJobs = jobs.length;
  const activeJobs = jobs.filter(j => (j.status || "").toLowerCase().trim() === "active").length;
  const inProgressJobs = jobs.filter(j => {
    const s = (j.status || "").toLowerCase().trim().replace(" ", "");
    return s === "inprogress" || s === "in-progress";
  }).length;
  const completedJobs = jobs.filter(j => (j.status || "").toLowerCase().trim() === "completed").length;

  const validateForm = () => {
    const newErrors = {};
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

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setErrors(prev => ({ ...prev, [name]: "" }));
    setApiError("");
  };

  const handleEdit = (job) => {
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

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validateForm()) return;
    try {
      setLoading(true);
      if (isEditing) {
        const response = await axios.put(`${API_URL}/${editingJobId}`, formData);
        setPopup({ show: true, title: "Job Updated Successfully", message: "The job details have been updated successfully.", jobId: response.data?.id ?? editingJobId });
      } else {
        const response = await axios.post(API_URL, formData);
        setPopup({ show: true, title: "Job Created Successfully", message: "Your job request has been submitted successfully.", jobId: response.data?.id ?? "" });
      }
      resetForm();
      fetchJobs();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to save job. Please check backend API.";
      setApiError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    const job = jobs.find(j => j.id === id);
    const name = job?.customer_name || `Job #${id}`;
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      setJobsLoading(true);
      await axios.delete(`${API_URL}/${id}`);
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
      const norm = (val) => (val || "").toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim();
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
    const nums = [];
    const delta = 2;
    for (let i = Math.max(1, safeJobsPage - delta); i <= Math.min(jobsTotalPages, safeJobsPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  const formatStatus = (status) => {
    const s = (status || "active").toLowerCase().trim();
    if (s === "inprogress" || s === "in progress") return "In Progress";
    if (s === "canceled" || s === "cancelled") return "Cancelled";
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  const getStatusClass = (status) => {
    let s = (status || "").toLowerCase().trim();
    if (s === "inprogress") s = "in-progress";
    else if (s === "canceled") s = "cancelled";
    else s = s.replace(" ", "-");
    return `status-badge status-${s}`;
  };

  return (
    <div className="jobs-page">
      {/* Success Popup */}
      {popup.show && (
        <div className="popup-overlay">
          <div className="success-popup">
            <div className="success-icon">✓</div>
            <h3>{popup.title}</h3>
            {popup.jobId && <div className="job-id-box">Job ID: <strong>#{popup.jobId}</strong></div>}
            <p>{popup.message}</p>
            <button type="button" className="popup-close-btn" onClick={closePopup}>OK</button>
          </div>
        </div>
      )}


      {/* Main Content: List Only (Form moved to Sidebar) */}
      <div className="main-content-row full-list-layout">
        {/* Job Management List */}
        <div className="content-card list-card">
          <div className="card-header">
            <div>
              <p className="card-subtitle">View and manage all submitted job requests</p>
            </div>
            <div className="header-actions-row">
              <button className="refresh-icon-btn" onClick={fetchJobs} title="Refresh">⟳ Refresh</button>
              <button className="add-job-btn" onClick={handleCreateNew}>+ Create Job</button>
            </div>
          </div>

          {/* Filters */}
          <div className="filters-row">
            <div className="filter-group">
              <label>Search</label>
              <input
                type="text"
                placeholder="Search name, location..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="filter-input"
              />
            </div>
            <div className="filter-group">
              <label>Status</label>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="filter-select">
                <option value="ALL">All Statuses</option>
                <option value="active">Active</option>
                <option value="in progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Priority</label>
              <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="filter-select">
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Service</label>
              <select value={serviceFilter} onChange={e => setServiceFilter(e.target.value)} className="filter-select">
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
          <p className="results-count">{filteredJobs.length} job{filteredJobs.length !== 1 ? "s" : ""} found</p>

          {/* Job Table */}
          <div className="table-container">
            {jobsLoading ? (
              <LoadingSpinner message="Loading jobs..." />
            ) : filteredJobs.length === 0 ? (
              <div className="empty-state">
                <p>No jobs found. Create your first job.</p>
              </div>
            ) : (
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Customer</th>
                    <th>Location</th>
                    <th>Priority</th>
                    <th>Service Type</th>
                    <th>Preferred Date</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedJobs.map(job => (
                    <tr key={job.id}>
                      <td className="job-id-cell">#{job.id}</td>
                      <td className="customer-cell">
                        <div><strong>{job.customer_name}</strong></div>
                        {job.issue_description && (
                          <div className="issue-sub">{job.issue_description}</div>
                        )}
                      </td>
                      <td>{job.location}</td>
                      <td>
                        <span className={`priority-badge ${getPriorityClass(job.priority)}`}>
                          {normalizeP(job.priority)}
                        </span>
                      </td>
                      <td>{job.service_type?.replace(/_/g, " ")}</td>
                      <td>{job.preferred_service_date}</td>
                      <td>
                        <span className={getStatusClass(job.status)}>{formatStatus(job.status)}</span>
                      </td>
                      <td>
                        <div className="job-item-actions" style={{ border: "none", padding: 0, margin: 0 }}>
                          <button
                            className="icon-action-btn icon-view"
                            onClick={() => setViewJob(job)}
                            title="View job details"
                            aria-label="View job"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            className="icon-action-btn icon-edit"
                            onClick={() => handleEdit(job)}
                            title="Edit job"
                            aria-label="Edit job"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            className="icon-action-btn icon-delete"
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
            <div className="jobs-pagination">
              <span className="jobs-page-info">
                Page <strong>{safeJobsPage}</strong> of <strong>{jobsTotalPages}</strong> · {filteredJobs.length} results
              </span>
              <div className="jobs-page-controls">
                <button className="jobs-page-btn" type="button" onClick={() => setJobsPage(1)} disabled={safeJobsPage === 1}>«</button>
                <button className="jobs-page-btn" type="button" onClick={() => setJobsPage(p => Math.max(1, p - 1))} disabled={safeJobsPage === 1}>‹ Prev</button>
                <div className="jobs-page-numbers">
                  {getJobsPageNums().map(n => (
                    <button
                      key={n}
                      type="button"
                      className={`jobs-page-num${n === safeJobsPage ? " active" : ""}`}
                      onClick={() => setJobsPage(n)}
                    >
                      {n}
                    </button>
                  ))}
                </div>
                <button className="jobs-page-btn" type="button" onClick={() => setJobsPage(p => Math.min(jobsTotalPages, p + 1))} disabled={safeJobsPage === jobsTotalPages}>Next ›</button>
                <button className="jobs-page-btn" type="button" onClick={() => setJobsPage(jobsTotalPages)} disabled={safeJobsPage === jobsTotalPages}>»</button>
              </div>
            </div>
          )}
           </div>
        </div>

      {/* View Job Modal */}
      {viewJob && (
        <div className="popup-overlay" onClick={() => setViewJob(null)}>
          <div className="view-job-modal" onClick={e => e.stopPropagation()}>
            <div className="view-modal-header">
              <h3>Job Details</h3>
              <button onClick={() => setViewJob(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div className="view-modal-body">
              <div className="view-detail-row"><span className="view-label">Job ID</span><span className="view-value">#{viewJob.id}</span></div>
              <div className="view-detail-row"><span className="view-label">Customer</span><span className="view-value">{viewJob.customer_name}</span></div>
              <div className="view-detail-row"><span className="view-label">Location</span><span className="view-value">{viewJob.location}</span></div>
              <div className="view-detail-row"><span className="view-label">Priority</span><span className={`priority-badge ${getPriorityClass(viewJob.priority)}`}>{normalizeP(viewJob.priority)}</span></div>
              <div className="view-detail-row"><span className="view-label">Service Type</span><span className="view-value">{viewJob.service_type?.replace(/_/g, ' ')}</span></div>
              <div className="view-detail-row"><span className="view-label">Contact</span><span className="view-value">{viewJob.contact_number}</span></div>
              <div className="view-detail-row"><span className="view-label">Preferred Date</span><span className="view-value">{viewJob.preferred_service_date}</span></div>
              <div className="view-detail-row"><span className="view-label">Status</span><span className={getStatusClass(viewJob.status)}>{formatStatus(viewJob.status)}</span></div>
              {viewJob.issue_description && <div className="view-detail-row col"><span className="view-label">Issue</span><span className="view-value">{viewJob.issue_description}</span></div>}
            </div>
          </div>
        </div>
      )}

      {/* Sliding Sidebar for Job Form — rendered outside main div to avoid overflow:hidden clipping */}
      <div className={`job-form-sidebar ${isFormOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>{isEditing ? "Edit Job" : "Create New Job"}</h3>
          <button className="close-sidebar" onClick={() => setIsFormOpen(false)}>×</button>
        </div>
        <div className="sidebar-body">
          {apiError && <div className="alert-error">{apiError}</div>}
          <form onSubmit={handleSubmit} className="job-form">
            <div className="form-group">
              <label>Customer Name <span className="req">*</span></label>
              <input
                type="text"
                name="customer_name"
                value={formData.customer_name}
                onChange={handleChange}
                placeholder="Enter customer name"
                className={errors.customer_name ? "input-error" : ""}
              />
              {errors.customer_name && <span className="field-error">{errors.customer_name}</span>}
            </div>

            <div className="form-group">
              <label>Location <span className="req">*</span></label>
              <input
                type="text"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="Enter location"
                className={errors.location ? "input-error" : ""}
              />
              {errors.location && <span className="field-error">{errors.location}</span>}
            </div>

            <div className="form-group">
              <label>Priority <span className="req">*</span></label>
              <select name="priority" value={formData.priority} onChange={handleChange} className={errors.priority ? "input-error" : ""}>
                <option value="">Select priority</option>
                {priorities.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              {errors.priority && <span className="field-error">{errors.priority}</span>}
            </div>

            <div className="form-group">
              <label>Service Type <span className="req">*</span></label>
              <select name="service_type" value={formData.service_type} onChange={handleChange} className={errors.service_type ? "input-error" : ""}>
                <option value="">Select service type</option>
                {getFormServiceTypes().map(st => (
                  <option key={st.value} value={st.value}>{st.label}</option>
                ))}
              </select>
              {errors.service_type && <span className="field-error">{errors.service_type}</span>}
            </div>

            <div className="form-group">
              <label>Contact Number <span className="req">*</span></label>
              <input
                type="text"
                name="contact_number"
                value={formData.contact_number}
                onChange={handleChange}
                placeholder="9876543210"
                maxLength="10"
                className={errors.contact_number ? "input-error" : ""}
              />
              {errors.contact_number && <span className="field-error">{errors.contact_number}</span>}
            </div>

            <div className="form-group">
              <label>Preferred Service Date <span className="req">*</span></label>
              <input
                type="date"
                name="preferred_service_date"
                value={formData.preferred_service_date}
                onChange={handleChange}
                className={errors.preferred_service_date ? "input-error" : ""}
              />
              {errors.preferred_service_date && <span className="field-error">{errors.preferred_service_date}</span>}
            </div>

            {isEditing && (
              <div className="form-group">
                <label>Status <span className="req">*</span></label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                >
                  <option value="active">Active</option>
                  <option value="in progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            )}

            <div className="form-group">
              <label>Issue Description <span className="req">*</span></label>
              <textarea
                name="issue_description"
                value={formData.issue_description}
                onChange={handleChange}
                placeholder="Describe the issue in detail..."
                rows="4"
                className={errors.issue_description ? "input-error" : ""}
              />
              {errors.issue_description && <span className="field-error">{errors.issue_description}</span>}
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? "Submitting..." : isEditing ? "Update Job" : "Create Job"}
              </button>
              <button type="button" className="btn-secondary" onClick={handleCancelEdit}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
      {isFormOpen && <div className="sidebar-overlay" onClick={() => setIsFormOpen(false)}></div>}
    </div>
  );
}

export default JobCreationForm;