/**
 * technicianService.js
 * Centralized API service for the Technician module.
 */

import axios from "axios";

const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 8000,
});

/** Fetch all technicians */
export const getAllTechnicians = () => api.get("/technicians/");

/** Fetch available technicians with workload details */
export const getAvailableTechnicians = () => api.get("/technicians/available");

/** Update technician availability status */
export const updateTechnicianAvailability = (technicianId, technician_status) =>
  api.put(`/technicians/${technicianId}/availability`, { technician_status });

/** Get a single technician by ID */
export const getTechnicianById = (id) => api.get(`/technicians/${id}`);

/** Update technician details */
export const updateTechnician = (technicianId, technicianData) =>
  api.put(`/technicians/${technicianId}`, technicianData);

/** Delete a technician */
export const deleteTechnician = (technicianId) =>
  api.delete(`/technicians/${technicianId}`);

/** Create a technician */
export const createTechnician = (technicianData) =>
  api.post("/technicians/", technicianData);

