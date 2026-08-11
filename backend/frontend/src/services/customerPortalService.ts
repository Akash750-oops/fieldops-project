/**
 * Customer Portal API service.
 * All API calls for the customer portal.
 */
import api from "./api";

// Profile
export const getCustomerProfile = () => api.get("/api/customer/profile");
export const createCustomerProfile = (data: any) => api.post("/api/customer/profile", data);
export const updateCustomerProfile = (data: any) => api.put("/api/customer/profile", data);
export const changeCustomerPassword = (data: any) => api.post("/api/customer/change-password", data);

// Service Requests
export const getServiceRequests = (status?: string) =>
  api.get("/api/customer/service-requests", { params: status ? { status } : {} });
export const createServiceRequest = (data: any) => api.post("/api/customer/service-requests", data);
export const getServiceRequest = (id: number) => api.get(`/api/customer/service-requests/${id}`);
export const updateServiceRequest = (id: number, data: any) =>
  api.put(`/api/customer/service-requests/${id}`, data);
export const cancelServiceRequest = (id: number) =>
  api.post(`/api/customer/service-requests/${id}/cancel`);

// Job Tracking
export const getCustomerJobs = () => api.get("/api/customer/jobs");
export const getCustomerJobDetail = (id: number) => api.get(`/api/customer/jobs/${id}`);

// Service History
export const getServiceHistory = () => api.get("/api/customer/service-history");

// Notifications
export const getCustomerNotifications = () => api.get("/api/customer/notifications");
export const markCustomerNotificationRead = (id: string) =>
  api.put(`/api/customer/notifications/${id}/read`);
export const markAllCustomerNotificationsRead = () =>
  api.put("/api/customer/notifications/read-all");

// Dashboard
export const getCustomerDashboard = () => api.get("/api/customer/dashboard");

// Planning - Declined Jobs (Admin/Dispatcher)
export const getDeclinedJobs = () => api.get("/planning/declined-jobs");
export const reassignDeclinedJob = (jobId: number, newTechnicianId: number) =>
  api.post(`/planning/declined-jobs/${jobId}/reassign?new_technician_id=${newTechnicianId}`);
