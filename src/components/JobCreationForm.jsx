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

function JobCreationForm() {
  const [formData, setFormData] = useState(initialFormData);
  const [jobs, setJobs] = useState([]);

  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const [isEditing, setIsEditing] = useState(false);
  const [editingJobId, setEditingJobId] = useState(null);

  const [popup, setPopup] = useState({
    show: false,
    title: "",
    message: "",
    jobId: "",
  });

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

  useEffect(() => {
    fetchJobs();
  }, []);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.customer_name.trim()) {
      newErrors.customer_name = "Customer name is required";
    }

    if (!formData.location.trim()) {
      newErrors.location = "Location is required";
    }

    if (!formData.issue_description.trim()) {
      newErrors.issue_description = "Issue description is required";
    }

    if (!formData.priority) {
      newErrors.priority = "Priority is required";
    }

    if (!formData.service_type) {
      newErrors.service_type = "Service type is required";
    }

    if (!formData.contact_number.trim()) {
      newErrors.contact_number = "Contact number is required";
    } else if (!/^[6-9]\d{9}$/.test(formData.contact_number)) {
      newErrors.contact_number = "Enter a valid 10-digit Indian mobile number";
    }

    if (!formData.preferred_service_date) {
      newErrors.preferred_service_date = "Preferred service date is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const resetForm = () => {
    setFormData(initialFormData);
    setErrors({});
    setIsEditing(false);
    setEditingJobId(null);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    setErrors((prev) => ({
      ...prev,
      [name]: "",
    }));

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
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const handleCancelEdit = () => {
    resetForm();
    setApiError("");
  };

  const closePopup = () => {
    setPopup({
      show: false,
      title: "",
      message: "",
      jobId: "",
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      if (isEditing) {
        const response = await axios.put(`${API_URL}${editingJobId}`, formData);

        setPopup({
          show: true,
          title: "Job Updated Successfully",
          message: "The job details have been updated successfully.",
          jobId: response.data?.id ? response.data.id : editingJobId,
        });
      } else {
        const response = await axios.post(API_URL, formData);

        setPopup({
          show: true,
          title: "Job Created Successfully",
          message: "Your job request has been submitted successfully.",
          jobId: response.data?.id ? response.data.id : "",
        });
      }

      resetForm();
      fetchJobs();
    } catch (error) {
      console.error(error);
      setApiError(
        error.response?.data?.detail ||
          "Unable to save job. Please check backend API."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this job?")) {
      return;
    }

    try {
      setJobsLoading(true);
      await axios.delete(`${API_URL}${id}`);
      setPopup({
        show: true,
        title: "Job Deleted",
        message: "The job has been removed successfully.",
        jobId: id,
      });
      fetchJobs();
    } catch (error) {
      console.error(error);
      setApiError("Unable to delete job. Please check backend API.");
    } finally {
      setJobsLoading(false);
    }
  };

  return (
    <div className="job-page">
      {popup.show && (
        <div className="popup-overlay">
          <div className="success-popup">
            <div className="success-icon">✓</div>

            <h3>{popup.title}</h3>

            {popup.jobId && (
              <div className="job-id-box">
                Job ID: <strong>{popup.jobId}</strong>
              </div>
            )}

            <p>{popup.message}</p>

            <button
              type="button"
              className="popup-close-btn"
              onClick={closePopup}
            >
              OK
            </button>
          </div>
        </div>
      )}

      <div className="job-container">
        <div className="job-card">
          <div className="job-header">
            <p className="badge">FieldOps Commander</p>
            <h1>{isEditing ? "Update Job Request" : "Create Job Request"}</h1>
            <p>
              {isEditing
                ? "Edit the selected job details and update the customer service request."
                : "Submit a new customer service request with priority, service type, and preferred date."}
            </p>
          </div>

          {apiError && <div className="error-message">{apiError}</div>}

          <form className="job-form" onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label>Customer Name</label>
                <input
                  type="text"
                  name="customer_name"
                  value={formData.customer_name}
                  onChange={handleChange}
                  placeholder="Enter customer name"
                  className={errors.customer_name ? "error-input" : ""}
                />
                {errors.customer_name && <small>{errors.customer_name}</small>}
              </div>

              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="Enter location"
                  className={errors.location ? "error-input" : ""}
                />
                {errors.location && <small>{errors.location}</small>}
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select
                  name="priority"
                  value={formData.priority}
                  onChange={handleChange}
                  className={errors.priority ? "error-input" : ""}
                >
                  <option value="">Select priority</option>
                  {priorities.map((priority) => (
                    <option key={priority.value} value={priority.value}>
                      {priority.label}
                    </option>
                  ))}
                </select>
                {errors.priority && <small>{errors.priority}</small>}
              </div>

              <div className="form-group">
                <label>Service Type</label>
                <select
                  name="service_type"
                  value={formData.service_type}
                  onChange={handleChange}
                  className={errors.service_type ? "error-input" : ""}
                >
                  <option value="">Select service type</option>
                  {serviceTypes.map((service) => (
                    <option key={service.value} value={service.value}>
                      {service.label}
                    </option>
                  ))}
                </select>
                {errors.service_type && <small>{errors.service_type}</small>}
              </div>

              <div className="form-group">
                <label>Contact Number</label>
                <input
                  type="text"
                  name="contact_number"
                  value={formData.contact_number}
                  onChange={handleChange}
                  placeholder="9876543210"
                  maxLength="10"
                  className={errors.contact_number ? "error-input" : ""}
                />
                {errors.contact_number && <small>{errors.contact_number}</small>}
              </div>

              <div className="form-group">
                <label>Preferred Service Date</label>
                <input
                  type="date"
                  name="preferred_service_date"
                  value={formData.preferred_service_date}
                  onChange={handleChange}
                  className={errors.preferred_service_date ? "error-input" : ""}
                />
                {errors.preferred_service_date && (
                  <small>{errors.preferred_service_date}</small>
                )}
              </div>
            </div>

            <div className="form-group full-width">
              <label>Issue Description</label>
              <textarea
                name="issue_description"
                value={formData.issue_description}
                onChange={handleChange}
                placeholder="Example: AC not cooling properly"
                rows="5"
                className={errors.issue_description ? "error-input" : ""}
              />
              {errors.issue_description && (
                <small>{errors.issue_description}</small>
              )}
            </div>

            <div className="button-row">
              <button type="submit" disabled={loading}>
                {loading
                  ? "Submitting..."
                  : isEditing
                  ? "Update Job"
                  : "Create Job"}
              </button>

              {isEditing && (
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={handleCancelEdit}
                >
                  Cancel Edit
                </button>
              )}
            </div>
          </form>
        </div>

        <div className="job-list-card">
          <div className="list-header">
            <div>
              <p className="badge">Dashboard</p>
              <h2>Job Management</h2>
            </div>

            <button type="button" className="refresh-btn" onClick={fetchJobs}>
              Refresh
            </button>
          </div>

          <div className="filters-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', marginBottom: '20px', padding: '15px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#64748b', marginBottom: '8px' }}>SEARCH</label>
              <input 
                type="text"
                placeholder="Search name, location, issue..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px' }}
              />
            </div>
            <div style={{ flex: '1 1 150px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#64748b', marginBottom: '8px' }}>STATUS</label>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px' }}
              >
                <option value="ALL">All Statuses</option>
                <option value="active">Active</option>
                <option value="in progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#64748b', marginBottom: '8px' }}>PRIORITY</label>
              <select 
                value={priorityFilter} 
                onChange={(e) => setPriorityFilter(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px' }}
              >
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          {jobsLoading ? (
            <p className="empty-text">Loading jobs...</p>
          ) : jobs.length === 0 ? (
            <p className="empty-text">No jobs available. Create your first job.</p>
          ) : (
            <div className="job-list">
              {jobs
                .filter(job => statusFilter === "ALL" || job.status === statusFilter)
                .filter(job => {
                  if (priorityFilter === "ALL") return true;
                  const jobPriority = (job.priority || "").toUpperCase();
                  const priorityMap = {
                    "P1": "CRITICAL",
                    "P2": "HIGH",
                    "P3": "MEDIUM",
                    "P4": "LOW",
                    "P5": "LOW"
                  };
                  const normalizedJobPriority = priorityMap[jobPriority] || jobPriority;
                  return normalizedJobPriority === priorityFilter;
                })
                .filter(job => {
                  const search = searchTerm.toLowerCase();
                  return (
                    (job.customer_name && job.customer_name.toLowerCase().includes(search)) ||
                    (job.location && job.location.toLowerCase().includes(search)) ||
                    (job.issue_description && job.issue_description.toLowerCase().includes(search))
                  );
                })
                .map((job) => (
                <div key={job.id} className="job-item">
                  <div className="job-info">
                    <div className="job-title-row">
                      <h3>{job.customer_name}</h3>
                      <span className={`priority-tag ${job.priority}`}>
                        {(() => {
                          const p = (job.priority || "").toUpperCase();
                          const map = { "P1": "CRITICAL", "P2": "HIGH", "P3": "MEDIUM", "P4": "LOW", "P5": "LOW" };
                          return map[p] || p;
                        })()}
                      </span>
                    </div>

                    {job.issue_description && (
                      <p className="job-desc">
                        <strong>Issue: </strong>{job.issue_description}
                      </p>
                    )}

                    <div className="job-meta">
                      {job.location && <span>📍 {job.location}</span>}
                      {job.service_type && <span>🛠 {job.service_type}</span>}
                      {job.contact_number && <span>📞 {job.contact_number}</span>}
                      {job.preferred_service_date && <span>📅 {job.preferred_service_date}</span>}
                    </div>
                  </div>

                  <div className="job-actions" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <button
                      type="button"
                      className="edit-btn"
                      onClick={() => handleEdit(job)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="delete-btn"
                      style={{ 
                        backgroundColor: '#fee2e2', 
                        color: '#b91c1c', 
                        border: '1px solid #fecaca',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                      }}
                      onClick={() => handleDelete(job.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default JobCreationForm;