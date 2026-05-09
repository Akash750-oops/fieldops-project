import React, { useState } from "react";
import axios from "axios";
import "./JobCreationForm.css";

const API_URL = "http://localhost:8000/jobs";

const priorities = [
  { label: "Critical", value: "P1" },
  { label: "High", value: "P2" },
  { label: "Medium", value: "P3" },
  { label: "Low", value: "P4" },
  { label: "Planned", value: "P5" },
];

const serviceTypes = [
  { label: "HVAC Repair", value: "HVAC_REPAIR" },
  { label: "Electrical Service", value: "ELECTRICAL_SERVICE" },
  { label: "Plumbing Service", value: "PLUMBING_SERVICE" },
  { label: "Network Support", value: "NETWORK_SUPPORT" },
  { label: "General Maintenance", value: "GENERAL_MAINTENANCE" },
];

function JobCreationForm() {
  const [formData, setFormData] = useState({
    customer_name: "",
    location: "",
    issue_description: "",
    priority: "",
    service_type: "",
    contact_number: "",
    preferred_service_date: "",
  });

  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState("");
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

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

    setSuccessMessage("");
    setApiError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      const response = await axios.post(API_URL, formData);

      setSuccessMessage(
        response.data?.id
          ? `Job created successfully. Job ID: ${response.data.id}`
          : "Job created successfully."
      );

      setFormData({
        customer_name: "",
        location: "",
        issue_description: "",
        priority: "",
        service_type: "",
        contact_number: "",
        preferred_service_date: "",
      });
    } catch (error) {
      setApiError(
        error.response?.data?.detail ||
          "Unable to create job. Please check backend API."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="job-page">
      <div className="job-card">
        <div className="job-header">
          <p className="badge">FieldOps Commander</p>
          <h1>Create Job Request</h1>
          <p>
            Submit a new customer service request with priority, service type,
            and preferred date.
          </p>
        </div>

        {successMessage && <div className="success-message">{successMessage}</div>}
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
            {errors.issue_description && <small>{errors.issue_description}</small>}
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Submitting..." : "Create Job"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default JobCreationForm;