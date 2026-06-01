/**
 * planningService.js
 * Centralized API service for the Planning Dashboard.
 */

import axios from "axios";

const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Common error handler
const handleApiError = (error) => {
  console.error("API Error:", error?.response?.data || error.message);
  throw error;
};

/**
 * Fetch all technicians.
 */
export const getTechnicians = async () => {
  try {
    return await api.get("/technicians");
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Fetch available technicians.
 */
export const getAvailableTechnicians = async () => {
  try {
    return await api.get("/technicians/available");
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Update technician availability.
 */
export const updateTechnicianAvailability = async (
  technicianId,
  technician_status
) => {
  try {
    return await api.put(`/technicians/${technicianId}/availability`, {
      technician_status,
    });
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Fetch pending jobs.
 */
export const getPendingJobs = async () => {
  try {
    return await api.get("/jobs/pending");
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Fetch planned assignments.
 */
export const getPlannedAssignments = async () => {
  try {
    return await api.get("/planned-assignments");
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Assign technician to job.
 */
export const assignJob = async (jobId, technicianId) => {
  try {
    return await api.post("/assign-job", {
      job_id: jobId,
      technician_id: technicianId,
    });
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Fetch dashboard stats.
 */
export const getDashboardStats = async () => {
  try {
    return await api.get("/jobs/stats");
  } catch (error) {
    handleApiError(error);
  }
};

/**
 * Fetch all jobs.
 */
export const getJobs = async () => {
  try {
    return await api.get("/jobs");
  } catch (error) {
    handleApiError(error);
  }
};

export default api;