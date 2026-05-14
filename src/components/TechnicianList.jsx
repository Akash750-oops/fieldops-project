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

function TechnicianList() {
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [techFormData, setTechFormData] = useState(initialTechFormData);
  const [formErrors, setFormErrors] = useState({});
  const [formLoading, setFormLoading] = useState(false);
  
  // Status update states
  const [updatingId, setUpdatingId] = useState(null);
  
  // Global message states
  const [message, setMessage] = useState({ text: "", type: "" }); // type: 'success' | 'error'

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

  useEffect(() => {
    fetchTechnicians();
  }, []);

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 5000);
  };

  const handleStatusChange = async (technicianId, newStatus) => {
    try {
      setUpdatingId(technicianId);
      
      await axios.put(`${API_BASE_URL}/${technicianId}/availability`, {
        technician_status: newStatus
      });
      
      showMessage("Technician availability updated successfully", "success");
      
      // Update local state to avoid full refetch
      setTechnicians(prev => prev.map(tech => 
        tech.technician_id === technicianId 
          ? { ...tech, technician_status: newStatus } 
          : tech
      ));
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "Unable to update technician availability. Please try again.";
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
      setIsSidebarOpen(false);
      fetchTechnicians();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "Unable to add technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setFormLoading(false);
    }
  };

  return (
    <div className="tech-page">
      {message.text && (
        <div className={`toast-message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="tech-container">
        <div className="tech-header">
          <div>
            <p className="badge">Planning System</p>
            <h2>Technicians Dashboard</h2>
          </div>
          <button 
            className="add-tech-btn" 
            onClick={() => setIsSidebarOpen(true)}
          >
            + Add Technician
          </button>
        </div>

        {fetchError && <div className="error-message">{fetchError}</div>}

        {loading ? (
          <p className="loading-text">Loading technicians...</p>
        ) : technicians.length === 0 ? (
          <p className="empty-text">No technicians found.</p>
        ) : (
          <div className="tech-grid">
            {technicians.map((tech) => (
              <div key={tech.technician_id} className="tech-card">
                <div className="tech-info">
                  <h3>{tech.technician_name}</h3>
                  <p className="tech-skill">🛠 {tech.technician_skill}</p>
                  <p className="tech-location">📍 {tech.technician_location}</p>
                  <p className="tech-jobs">
                    Jobs: {tech.current_jobs} / {tech.max_jobs}
                  </p>
                </div>
                
                <div className="tech-status-control">
                  <label>Availability:</label>
                  <select
                    value={tech.technician_status}
                    onChange={(e) => handleStatusChange(tech.technician_id, e.target.value)}
                    disabled={updatingId === tech.technician_id}
                    className={`status-select ${tech.technician_status.toLowerCase()}`}
                  >
                    <option value="Available">Available</option>
                    <option value="Busy">Busy</option>
                    <option value="Offline">Offline</option>
                  </select>
                  {updatingId === tech.technician_id && <span className="updating-spinner">↻</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Sidebar for Adding Technician */}
      <div className={`sidebar-overlay ${isSidebarOpen ? "open" : ""}`} onClick={() => setIsSidebarOpen(false)}>
        <div className="sidebar" onClick={(e) => e.stopPropagation()}>
          <div className="sidebar-header">
            <h3>Add New Technician</h3>
            <button className="close-btn" onClick={() => setIsSidebarOpen(false)}>✕</button>
          </div>
          
          <form className="sidebar-form" onSubmit={handleFormSubmit}>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                name="technician_name"
                value={techFormData.technician_name}
                onChange={handleFormChange}
                placeholder="Enter full name"
                className={formErrors.technician_name ? "error-input" : ""}
              />
              {formErrors.technician_name && <small>{formErrors.technician_name}</small>}
            </div>

            <div className="form-group">
              <label>Skill</label>
              <input
                type="text"
                name="technician_skill"
                value={techFormData.technician_skill}
                onChange={handleFormChange}
                placeholder="e.g. Electrical, HVAC"
                className={formErrors.technician_skill ? "error-input" : ""}
              />
              {formErrors.technician_skill && <small>{formErrors.technician_skill}</small>}
            </div>

            <div className="form-group">
              <label>Location</label>
              <input
                type="text"
                name="technician_location"
                value={techFormData.technician_location}
                onChange={handleFormChange}
                placeholder="e.g. Mumbai, New Delhi"
                className={formErrors.technician_location ? "error-input" : ""}
              />
              {formErrors.technician_location && <small>{formErrors.technician_location}</small>}
            </div>

            <div className="form-group">
              <label>Initial Status</label>
              <select
                name="technician_status"
                value={techFormData.technician_status}
                onChange={handleFormChange}
              >
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <button type="submit" className="submit-btn" disabled={formLoading}>
              {formLoading ? "Saving..." : "Add Technician"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default TechnicianList;
