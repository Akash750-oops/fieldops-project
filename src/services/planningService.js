/**
 * planningService.js
 * Centralized API service for the Planning Dashboard.
 * All Planning Dashboard API calls should go through this file.
 */

import axios from "axios";

const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

/**
 * Fetch all technicians (all statuses) for the assignment dropdown.
 */
export const getTechnicians = () => api.get("/technicians/");

/**
 * Fetch all technicians with availability/workload details for the status panel.
 * Returns all technicians but marks which ones are eligible for assignment.
 */
export const getAvailableTechnicians = () => api.get("/technicians/available");

/**
 * Update a technician's availability status.
 * @param {number} technicianId
 * @param {string} technician_status - "Available" | "Busy" | "Offline"
 */
export const updateTechnicianAvailability = (technicianId, technician_status) =>
  api.put(`/technicians/${technicianId}/availability`, { technician_status });

/**
 * Fetch all pending / unassigned jobs for planning.
 */
export const getPendingJobs = () => api.get("/jobs/pending");

/**
 * Fetch all planned (assigned) job-technician assignments.
 */
export const getPlannedAssignments = () => api.get("/planned-assignments");

/**
 * Assign a technician to a job.
 * Backend will block if the technician is Busy or Offline.
 * @param {number} jobId
 * @param {number} technicianId
 */
export const assignJob = (jobId, technicianId) =>
  api.post("/assign-job", { job_id: jobId, technician_id: technicianId });
