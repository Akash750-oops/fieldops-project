import React, { useEffect, useState } from "react";
import axios from "axios";
import "./TechnicianList.css";

const API_BASE_URL = "http://localhost:8000/technicians";

const initialTechFormData = {
  technician_name: "",
  technician_skill: "",
  technician_location: "",
  technician_status: "Available",
};

const skills = [
  "HVAC Repair", "Electrical", "Plumbing", "Network Support", "General Maintenance"
];

function TechnicianList() {
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [techFormData, setTechFormData] = useState(initialTechFormData);
  const [formErrors, setFormErrors] = useState({});
  const [formLoading, setFormLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [message, setMessage] = useState({ text: "", type: "" });
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const fetchTechnicians = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/`);
      setTechnicians(response.data);
      setFetchError("");
    } catch (error) {
      console.error(error);
      setFetchError("Unable to fetch technicians. Please check backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTechnicians(); }, []);

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 4000);
  };

  // KPI calculations
  const total = technicians.length;
  const available = technicians.filter(t => t.technician_status === "Available" || t.technician_status === "AVAILABLE").length;
  const busy = technicians.filter(t => t.technician_status === "Busy" || t.technician_status === "BUSY").length;
  const offline = technicians.filter(t => t.technician_status === "Offline" || t.technician_status === "OFFLINE").length;

  const handleStatusChange = async (technicianId, newStatus) => {
    try {
      setUpdatingId(technicianId);
      await axios.put(`${API_BASE_URL}/${technicianId}/availability`, {
        technician_status: newStatus
      });
      showMessage("Availability updated successfully", "success");
      setTechnicians(prev => prev.map(t =>
        t.technician_id === technicianId ? { ...t, technician_status: newStatus } : t
      ));
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "Unable to update availability. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setUpdatingId(null);
    }
  };

  const validateForm = () => {
    const errors = {};
    if (!techFormData.technician_name.trim()) errors.technician_name = "Name is required";
    if (!techFormData.technician_skill.trim()) errors.technician_skill = "Skill is required";
    if (!techFormData.technician_location.trim()) errors.technician_location = "Location is required";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setTechFormData(prev => ({ ...prev, [name]: value }));
    setFormErrors(prev => ({ ...prev, [name]: "" }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    try {
      setFormLoading(true);
      await axios.post(`${API_BASE_URL}/`, techFormData);
      showMessage("Technician added successfully", "success");
      setTechFormData(initialTechFormData);
      fetchTechnicians();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "Unable to add technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setFormLoading(false);
    }
  };

  const getStatusClass = (status) => {
    const s = (status || "").toLowerCase();
    if (s === "available") return "tech-badge badge-available";
    if (s === "busy") return "tech-badge badge-busy";
    if (s === "offline") return "tech-badge badge-offline";
    return "tech-badge";
  };

  const normalizeStatus = (s) => {
    const lower = (s || "").toLowerCase();
    if (lower === "available") return "Available";
    if (lower === "busy") return "Busy";
    if (lower === "offline") return "Offline";
    return s;
  };

  const filteredTechnicians = technicians
    .filter(t => statusFilter === "ALL" || normalizeStatus(t.technician_status) === statusFilter)
    .filter(t => {
      const s = searchTerm.toLowerCase();
      return (
        (t.technician_name && t.technician_name.toLowerCase().includes(s)) ||
        (t.technician_skill && t.technician_skill.toLowerCase().includes(s)) ||
        (t.technician_location && t.technician_location.toLowerCase().includes(s))
      );
    });

  return (
    <div className="tech-page">
      {/* Toast */}
      {message.text && (
        <div className={`toast-message toast-${message.type}`}>
          {message.type === "success" ? "✓" : "✕"} {message.text}
        </div>
      )}

      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Technician Management</h1>
          <p className="page-subtitle">Manage field technicians and update their availability</p>
        </div>
        <div className="header-actions-row">
          <button className="refresh-icon-btn" onClick={fetchTechnicians}>⟳ Refresh</button>
          <button className="add-tech-btn" onClick={() => document.querySelector('.form-card').scrollIntoView({ behavior: 'smooth' })}>+ Add Technician</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-row">
        <div className="kpi-card kpi-blue">
          <div className="kpi-icon">👷</div>
          <div className="kpi-info">
            <span className="kpi-label">Total Technicians</span>
            <span className="kpi-value">{total}</span>
          </div>
        </div>
        <div className="kpi-card kpi-green">
          <div className="kpi-icon">✅</div>
          <div className="kpi-info">
            <span className="kpi-label">Available</span>
            <span className="kpi-value">{available}</span>
          </div>
        </div>
        <div className="kpi-card kpi-orange">
          <div className="kpi-icon">⚙️</div>
          <div className="kpi-info">
            <span className="kpi-label">Busy</span>
            <span className="kpi-value">{busy}</span>
          </div>
        </div>
        <div className="kpi-card kpi-red">
          <div className="kpi-icon">🔴</div>
          <div className="kpi-info">
            <span className="kpi-label">Offline</span>
            <span className="kpi-value">{offline}</span>
          </div>
        </div>
      </div>

      {/* Main Content Area: Split List Left + Form Right */}
      <div className="main-content-row split-tech-layout">
        {/* LEFT: Technicians Grid & Filters */}
        <div className="content-card grid-card">
          {/* Filters */}
          <div className="tech-filters-row">
            <div className="filter-group">
              <label>Search</label>
              <input
                type="text"
                placeholder="Name, skill, location..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="filter-input"
              />
            </div>
            <div className="filter-group">
              <label>Status</label>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="filter-select">
                <option value="ALL">All Statuses</option>
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Offline">Offline</option>
              </select>
            </div>
          </div>

          <p className="results-count">{filteredTechnicians.length} technician{filteredTechnicians.length !== 1 ? "s" : ""} found</p>

          {fetchError && <div className="alert-error">{fetchError}</div>}

          {loading ? (
            <div className="empty-state">
              <span className="empty-icon">⏳</span>
              <p>Loading technicians...</p>
            </div>
          ) : filteredTechnicians.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">👷</span>
              <p>No technicians found.</p>
            </div>
          ) : (
            <div className="tech-grid">
              {filteredTechnicians.map(tech => (
                <div key={tech.technician_id} className="tech-card">
                  <div className="tech-card-header">
                    <div className="tech-avatar">
                      {tech.technician_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="tech-name">{tech.technician_name}</h3>
                      <span className={getStatusClass(tech.technician_status)}>
                        {normalizeStatus(tech.technician_status)}
                      </span>
                    </div>
                  </div>

                  <div className="tech-details">
                    <div className="tech-detail-row">
                      <span className="detail-icon">🛠</span>
                      <span>{tech.technician_skill}</span>
                    </div>
                    <div className="tech-detail-row">
                      <span className="detail-icon">📍</span>
                      <span>{tech.technician_location}</span>
                    </div>
                    <div className="tech-detail-row">
                      <span className="detail-icon">📋</span>
                      <span>Jobs: {tech.current_jobs} / {tech.max_jobs}</span>
                    </div>
                  </div>

                  {/* Workload Bar */}
                  <div className="workload-bar-track">
                    <div
                      className="workload-bar-fill"
                      style={{
                        width: `${Math.min((tech.current_jobs / tech.max_jobs) * 100, 100)}%`,
                        background: tech.current_jobs >= tech.max_jobs ? "#ef4444" : "#3b82f6"
                      }}
                    />
                  </div>

                  {/* Availability Dropdown */}
                  <div className="availability-control">
                    <label>Availability</label>
                    <div className="select-wrapper">
                      <select
                        value={normalizeStatus(tech.technician_status)}
                        onChange={e => handleStatusChange(tech.technician_id, e.target.value)}
                        disabled={updatingId === tech.technician_id}
                        className={`status-select status-${normalizeStatus(tech.technician_status).toLowerCase()}`}
                      >
                        <option value="Available">Available</option>
                        <option value="Busy">Busy</option>
                        <option value="Offline">Offline</option>
                      </select>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="tech-card-actions">
                    <button className="btn-view" onClick={() => alert("Details feature coming soon!")}>View</button>
                    <button className="btn-edit-tech" onClick={() => alert("Edit feature coming soon!")}>Edit</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Add Technician Form */}
        <div className="content-card form-card">
          <div className="card-header">
            <div>
              <span className="section-badge">New Record</span>
              <h3 className="card-title">Add Technician</h3>
              <p className="card-subtitle">Register a new field technician</p>
            </div>
          </div>

          <form className="tech-form" onSubmit={handleFormSubmit}>
            <div className="form-group">
              <label>Full Name <span className="req">*</span></label>
              <input
                type="text"
                name="technician_name"
                value={techFormData.technician_name}
                onChange={handleFormChange}
                placeholder="e.g. Rajesh Kumar"
                className={formErrors.technician_name ? "input-error" : ""}
              />
              {formErrors.technician_name && <span className="field-error">{formErrors.technician_name}</span>}
            </div>

            <div className="form-group">
              <label>Skill <span className="req">*</span></label>
              <input
                type="text"
                name="technician_skill"
                value={techFormData.technician_skill}
                onChange={handleFormChange}
                placeholder="e.g. Electrical, HVAC"
                className={formErrors.technician_skill ? "input-error" : ""}
                list="skill-suggestions"
              />
              <datalist id="skill-suggestions">
                {skills.map(s => <option key={s} value={s} />)}
              </datalist>
              {formErrors.technician_skill && <span className="field-error">{formErrors.technician_skill}</span>}
            </div>

            <div className="form-group">
              <label>Location <span className="req">*</span></label>
              <input
                type="text"
                name="technician_location"
                value={techFormData.technician_location}
                onChange={handleFormChange}
                placeholder="e.g. Mumbai, Delhi"
                className={formErrors.technician_location ? "input-error" : ""}
              />
              {formErrors.technician_location && <span className="field-error">{formErrors.technician_location}</span>}
            </div>

            <div className="form-group">
              <label>Initial Status</label>
              <select
                name="technician_status"
                value={techFormData.technician_status}
                onChange={handleFormChange}
                className="status-select"
              >
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <button type="submit" className="btn-primary submit-full" disabled={formLoading}>
              {formLoading ? "Saving..." : "Add Technician"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default TechnicianList;
