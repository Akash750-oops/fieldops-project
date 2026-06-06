/**
 * dispatchMetricsService.js
 * Service for fetching dispatch KPI metrics from the backend.
 * Falls back to realistic mock data when the API is unavailable.
 */

import axios from "axios";

const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
    Authorization: "Bearer mock-token",
    "X-Tenant-ID": "tenant-1",
  },
  timeout: 8000,
});

const mockDispatchMetrics = {
  jobs_dispatched: 45,
  jobs_pending: 20,
  jobs_expired: 3,
  jobs_redispatched: 8,
  trends: {
    dispatched: { yesterday: 40, change_pct: 12.5 },
    pending: { yesterday: 15, change_pct: 33.3 },
    expired: { yesterday: 0, change_pct: null },
    redispatched: { yesterday: 5, change_pct: 60.0 },
  },
  sparklines: {
    dispatched: [
      2, 4, 6, 8, 5, 7, 9, 12, 15, 18, 20, 22,
      25, 28, 30, 35, 38, 40, 42, 45, 45, 45, 45, 45,
    ],
    pending: [
      10, 12, 15, 14, 16, 18, 20, 19, 21, 20, 18, 19,
      20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    ],
    expired: [
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 3, 3,
    ],
    redispatched: [
      1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 6,
      6, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8,
    ],
  },
};

export const getDispatchMetrics = async (timeRange = "today") => {
  try {
    const response = await api.get(`/dispatch/metrics`, {
      params: { time_range: timeRange },
    });
    return response.data;
  } catch (error) {
    console.warn(
      "Dispatch metrics API failed. Using mock data temporarily.",
      error
    );

    return mockDispatchMetrics;
  }
};