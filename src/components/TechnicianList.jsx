import React, { useEffect, useState } from "react";
import axios from "axios";
import { Eye, Pencil, Trash2 } from "lucide-react";
import LoadingSpinner from "./LoadingSpinner.jsx";
import StatusBadge from "./common/StatusBadge";
import "./TechnicianList.css";

const API_BASE_URL = "http://localhost:8000/technicians";
const TECH_PAGE_SIZE = 8;

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
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [techPage, setTechPage] = useState(1);
  const [isEditing, setIsEditing] = useState(false);
  const [editingTechId, setEditingTechId] = useState(null);
  const [viewTech, setViewTech] = useState(null);

  useEffect(() => {
    setTechPage(1);
  }, [searchTerm, statusFilter]);

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
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to update availability. Please try again.";
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

  const resetForm = () => {
    setTechFormData(initialTechFormData);
    setFormErrors({});
    setIsEditing(false);
    setEditingTechId(null);
    setIsFormOpen(false);
  };

  const handleEdit = (tech) => {
    setIsEditing(true);
    setEditingTechId(tech.technician_id);
    setTechFormData({
      technician_name: tech.technician_name || "",
      technician_skill: tech.technician_skill || "",
      technician_location: tech.technician_location || "",
      technician_status: normalizeStatus(tech.technician_status) || "Available",
    });
    setIsFormOpen(true);
  };

  const handleDelete = async (id) => {
    const tech = technicians.find(t => t.technician_id === id);
    const name = tech?.technician_name || `Technician #${id}`;
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/${id}`);
      showMessage("Technician deleted successfully", "success");
      fetchTechnicians();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to delete technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    try {
      setFormLoading(true);
      if (isEditing) {
        await axios.put(`${API_BASE_URL}/${editingTechId}`, techFormData);
        showMessage("Technician updated successfully", "success");
      } else {
        await axios.post(`${API_BASE_URL}/`, techFormData);
        showMessage("Technician added successfully", "success");
      }
      resetForm();
      fetchTechnicians();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to save technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setFormLoading(false);
    }
  };

  const getStatusClass = (status) => {
    const s = (status || "").toLowerCase();
    if (s === "available") return "tech-badge badge-available";
    if (s === "busy") return "tech-badge badge-busy";
    if (s === "assigned") return "tech-badge badge-assigned";
    if (s === "offline") return "tech-badge badge-offline";
    return "tech-badge";
  };

  const normalizeStatus = (s) => {
    const lower = (s || "").toLowerCase();
    if (lower === "available") return "Available";
    if (lower === "busy") return "Busy";
    if (lower === "assigned") return "Assigned";
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

  const techTotalPages = Math.max(1, Math.ceil(filteredTechnicians.length / TECH_PAGE_SIZE));
  const safeTechPage = Math.min(techPage, techTotalPages);
  const paginatedTechnicians = filteredTechnicians.slice((safeTechPage - 1) * TECH_PAGE_SIZE, safeTechPage * TECH_PAGE_SIZE);

  useEffect(() => {
    const total = Math.max(1, Math.ceil(filteredTechnicians.length / TECH_PAGE_SIZE));
    if (techPage > total) {
      setTechPage(total);
    }
  }, [filteredTechnicians.length, techPage]);

  const getTechPageNums = () => {
    const nums = [];
    const delta = 2;
    for (let i = Math.max(1, safeTechPage - delta); i <= Math.min(techTotalPages, safeTechPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  return (
    <div className="tech-page">
      {/* Toast */}
      {message.text && (
        <div className={`toast-message toast-${message.type}`}>
          {message.type === "success" ? "✓" : "✕"} {message.text}
        </div>
      )}

      {/* Main Content Area: Grid Only */}
      <div className="main-content-row full-grid-layout">
        {/* Technicians Grid & Filters */}
        <div className="content-card grid-card">
          <div className="card-header">
            <div>
              <span className="section-badge">Registry</span>
              <p className="card-subtitle">Manage field technicians and update their availability</p>
            </div>
            <div className="header-actions-row">
              <button className="refresh-icon-btn" onClick={fetchTechnicians} title="Refresh">⟳ Refresh</button>
              <button className="add-tech-btn" onClick={() => { resetForm(); setIsFormOpen(true); }}>+ Add Technician</button>
            </div>
          </div>

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
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
            </div>
          </div>

          <p className="results-count">{filteredTechnicians.length} technician{filteredTechnicians.length !== 1 ? "s" : ""} found</p>

          {fetchError && <div className="alert-error">{fetchError}</div>}

          {loading ? (
            <LoadingSpinner message="Loading technicians..." />
          ) : filteredTechnicians.length === 0 ? (
            <div className="empty-state">
              <p>No technicians found.</p>
            </div>
          ) : (
          <div className="table-container">
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>Technician</th>
                  <th>Skill</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Workload</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedTechnicians.map(tech => {
                  const pct = tech.max_jobs > 0 ? Math.min((tech.current_jobs / tech.max_jobs) * 100, 100) : 0;
                  return (
                    <tr key={tech.technician_id}>
                      <td>
                        <div className="tech-info" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div className="tech-avatar" style={{ margin: 0, width: "30px", height: "30px", fontSize: "11px" }}>
                            {tech.technician_name.charAt(0).toUpperCase()}
                          </div>
                          <strong>{tech.technician_name}</strong>
                        </div>
                      </td>
                      <td>{tech.technician_skill}</td>
                      <td>{tech.technician_location}</td>
                      <td>
                        <div className="availability-control" style={{ margin: 0, padding: 0 }}>
                          <div className="select-wrapper">
                            <select
                              value={normalizeStatus(tech.technician_status)}
                              onChange={e => handleStatusChange(tech.technician_id, e.target.value)}
                              disabled={updatingId === tech.technician_id}
                              className={`status-select status-${normalizeStatus(tech.technician_status).toLowerCase()}`}
                              style={{ padding: "4px 8px", fontSize: "11px" }}
                            >
                              <option value="Available">Available</option>
                              <option value="Busy">Busy</option>
                              <option value="Assigned">Assigned</option>
                              <option value="Offline">Offline</option>
                            </select>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="workload-info" style={{ display: "flex", flexDirection: "column", gap: "4px", width: "120px" }}>
                          <div className="workload-bar" style={{ background: "#E3ECE7", height: "6px", borderRadius: "3px", overflow: "hidden" }}>
                            <div
                              className="workload-fill"
                              style={{
                                width: `${pct}%`,
                                height: "100%",
                                background: tech.current_jobs >= tech.max_jobs ? "#D96C6C" : "#7AAE8A"
                              }}
                            />
                          </div>
                          <span className="workload-text" style={{ fontSize: "10px", color: "#6B7280" }}>
                            {tech.current_jobs}/{tech.max_jobs} jobs
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="tech-card-actions" style={{ display: "flex", gap: "6px", border: "none", padding: 0, background: "none", margin: 0 }}>
                          <button
                            className="icon-action-btn icon-view"
                            onClick={() => setViewTech(tech)}
                            title="View technician details"
                            aria-label="View technician"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            className="icon-action-btn icon-edit"
                            onClick={() => handleEdit(tech)}
                            title="Edit technician"
                            aria-label="Edit technician"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            className="icon-action-btn icon-delete"
                            onClick={() => handleDelete(tech.technician_id)}
                            title="Delete technician"
                            aria-label="Delete technician"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {/* Pagination */}
        {!loading && (
          <div className="tech-pagination">
            <span className="tech-page-info">
              Page <strong>{safeTechPage}</strong> of <strong>{techTotalPages}</strong> · {filteredTechnicians.length} results
            </span>
            <div className="tech-page-controls">
              <button className="tech-page-btn" type="button" onClick={() => setTechPage(1)} disabled={safeTechPage === 1}>«</button>
              <button className="tech-page-btn" type="button" onClick={() => setTechPage(p => Math.max(1, p - 1))} disabled={safeTechPage === 1}>‹ Prev</button>
              <div className="tech-page-numbers">
                {getTechPageNums().map(n => (
                  <button
                    key={n}
                    type="button"
                    className={`tech-page-num${n === safeTechPage ? " active" : ""}`}
                    onClick={() => setTechPage(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <button className="tech-page-btn" type="button" onClick={() => setTechPage(p => Math.min(techTotalPages, p + 1))} disabled={safeTechPage === techTotalPages}>Next ›</button>
              <button className="tech-page-btn" type="button" onClick={() => setTechPage(techTotalPages)} disabled={safeTechPage === techTotalPages}>»</button>
            </div>
          </div>
        )}
      </div>
    </div>

      {/* View Technician Modal */}
      {viewTech && (
        <div className="popup-overlay" onClick={() => setViewTech(null)}>
          <div className="view-job-modal" onClick={e => e.stopPropagation()}>
            <div className="view-modal-header">
              <h3>Technician Details</h3>
              <button onClick={() => setViewTech(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div className="view-modal-body">
              <div className="view-detail-row"><span className="view-label">Technician ID</span><span className="view-value">#{viewTech.technician_id}</span></div>
              <div className="view-detail-row"><span className="view-label">Name</span><span className="view-value">{viewTech.technician_name}</span></div>
              <div className="view-detail-row"><span className="view-label">Skill</span><span className="view-value">{viewTech.technician_skill}</span></div>
              <div className="view-detail-row"><span className="view-label">Location / Zone</span><span className="view-value">{viewTech.technician_location}</span></div>
              <div className="view-detail-row"><span className="view-label">Status</span><StatusBadge status={viewTech.technician_status} size="md" /></div>
              <div className="view-detail-row"><span className="view-label">Active Jobs</span><span className="view-value">{viewTech.current_jobs} / {viewTech.max_jobs}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Sliding Sidebar for Technician Form */}
      <div className={`tech-form-sidebar ${isFormOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>{isEditing ? "Edit Technician" : "Add New Technician"}</h3>
          <button className="close-sidebar" onClick={resetForm}>×</button>
        </div>
        <div className="sidebar-content">
          <form className="tech-form" onSubmit={(e) => {
            handleFormSubmit(e);
            if (validateForm()) setIsFormOpen(false);
          }}>
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
              <label>{isEditing ? "Status" : "Initial Status"}</label>
              <select
                name="technician_status"
                value={techFormData.technician_status}
                onChange={handleFormChange}
                className="status-select"
              >
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={formLoading}>
                {formLoading ? "Saving..." : isEditing ? "Update Technician" : "Add Technician"}
              </button>
              <button type="button" className="btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
      {isFormOpen && <div className="sidebar-overlay" onClick={resetForm}></div>}
    </div>
  );
}

export default TechnicianList;
