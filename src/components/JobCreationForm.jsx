import React, { useEffect, useState } from "react";
import axios from "axios";
import "./JobCreationForm.css";

const API_URL = "http://localhost:8000/jobs/";

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

  const [isEditing, setIsEditing] = useState(false);
  const [editingJobId, setEditingJobId] = useState(null);

  const [popup, setPopup] = useState({ show: false, title: "", message: "", jobId: "" });
  const [isFormOpen, setIsFormOpen] = useState(false);

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
  const activeJobs = jobs.filter(j => (j.status || "").toLowerCase() === "active").length;
  const inProgressJobs = jobs.filter(j => (j.status || "").toLowerCase() === "in progress").length;
  const completedJobs = jobs.filter(j => (j.status || "").toLowerCase() === "completed").length;

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
    setFormData({
      customer_name: job.customer_name || "",
      location: job.location || "",
      issue_description: job.issue_description || "",
      priority: job.priority || "",
      service_type: job.service_type || "",
      contact_number: job.contact_number || "",
      preferred_service_date: job.preferred_service_date || "",
      status: job.status || "active",
      required_skill: job.required_skill || "",
    });
    setIsFormOpen(true);
  };

  const handleCancelEdit = () => { resetForm(); setApiError(""); };
  const closePopup = () => setPopup({ show: false, title: "", message: "", jobId: "" });

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validateForm()) return;
    try {
      setLoading(true);
      if (isEditing) {
        const response = await axios.put(`${API_URL}${editingJobId}`, formData);
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
    if (!window.confirm("Are you sure you want to delete this job?")) return;
    try {
      setJobsLoading(true);
      await axios.delete(`${API_URL}${id}`);
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
    .filter(j => statusFilter === "ALL" || (j.status || "").toLowerCase() === statusFilter.toLowerCase())
    .filter(j => {
      if (priorityFilter === "ALL") return true;
      return normalizeP(j.priority) === priorityFilter;
    })
    .filter(j => serviceFilter === "ALL" || j.service_type === serviceFilter)
    .filter(j => {
      const s = searchTerm.toLowerCase();
      return (
        (j.customer_name && j.customer_name.toLowerCase().includes(s)) ||
        (j.location && j.location.toLowerCase().includes(s)) ||
        (j.issue_description && j.issue_description.toLowerCase().includes(s))
      );
    });

  const getStatusClass = (status) => {
    const s = (status || "").toLowerCase().replace(" ", "-");
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

      {/* Page Header */}
      <div className="page-header">
        <div>
          <p className="page-subtitle">Create and manage field service job requests</p>
        </div>
        <div className="header-actions-row">
          <button className="refresh-icon-btn" onClick={fetchJobs} title="Refresh">⟳ Refresh</button>
          <button className="add-job-btn" onClick={() => setIsFormOpen(true)}>+ Create Job</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-row">
        <div className="kpi-card kpi-blue">
          <div className="kpi-icon">📋</div>
          <div className="kpi-info">
            <span className="kpi-label">Total Jobs</span>
            <span className="kpi-value">{totalJobs}</span>
          </div>
        </div>
        <div className="kpi-card kpi-green">
          <div className="kpi-icon">✅</div>
          <div className="kpi-info">
            <span className="kpi-label">Active Jobs</span>
            <span className="kpi-value">{activeJobs}</span>
          </div>
        </div>
        <div className="kpi-card kpi-orange">
          <div className="kpi-icon">⚙️</div>
          <div className="kpi-info">
            <span className="kpi-label">In Progress</span>
            <span className="kpi-value">{inProgressJobs}</span>
          </div>
        </div>
        <div className="kpi-card kpi-purple">
          <div className="kpi-icon">🏁</div>
          <div className="kpi-info">
            <span className="kpi-label">Completed</span>
            <span className="kpi-value">{completedJobs}</span>
          </div>
        </div>
      </div>

      {/* Main Content: List Only (Form moved to Sidebar) */}
      <div className="main-content-row full-list-layout">
        {/* Job Management List */}
        <div className="content-card list-card">
          <div className="card-header">
            <div>
              <span className="section-badge">Dashboard</span>
              <p className="card-subtitle">View and manage all submitted job requests</p>
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
                {serviceTypes.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          {/* Jobs Count */}
          <p className="results-count">{filteredJobs.length} job{filteredJobs.length !== 1 ? "s" : ""} found</p>

          {/* Job List */}
          <div className="job-list-scroll">
            {jobsLoading ? (
              <div className="empty-state">
                <span className="empty-icon">⏳</span>
                <p>Loading jobs...</p>
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">📭</span>
                <p>No jobs found. Create your first job.</p>
              </div>
            ) : (
              filteredJobs.map(job => (
                <div key={job.id} className="job-item-card">
                  <div className="job-item-header">
                    <div className="job-item-title">
                      <h4>{job.customer_name}</h4>
                      <span className={getStatusClass(job.status)}>{job.status || "active"}</span>
                    </div>
                    <span
                      className="priority-dot"
                      style={{ background: priorityColors[normalizeP(job.priority)] || "#94a3b8" }}
                      title={normalizeP(job.priority)}
                    >
                      {normalizeP(job.priority)}
                    </span>
                  </div>

                  <p className="job-item-desc">{job.issue_description}</p>

                  <div className="job-item-meta">
                    {job.location && <span>📍 {job.location}</span>}
                    {job.service_type && <span>🛠 {job.service_type.replace(/_/g, " ")}</span>}
                    {job.contact_number && <span>📞 {job.contact_number}</span>}
                    {job.preferred_service_date && <span>📅 {job.preferred_service_date}</span>}
                  </div>

                  <div className="job-item-actions">
                    <button className="btn-edit" onClick={() => handleEdit(job)}>Edit</button>
                    <button className="btn-delete" onClick={() => handleDelete(job.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Sliding Sidebar for Job Form */}
      <div className={`job-form-sidebar ${isFormOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>{isEditing ? "Edit Job" : "Create New Job"}</h3>
          <button className="close-sidebar" onClick={() => setIsFormOpen(false)}>×</button>
        </div>
        <div className="sidebar-content">
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
                {serviceTypes.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
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