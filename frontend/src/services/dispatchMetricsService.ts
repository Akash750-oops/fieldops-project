/**
 * dispatchMetricsService.ts
 * Service for fetching dispatch KPI metrics from the backend.
 */

import api from "./api";

export const getDispatchMetrics = async (timeRange: string = "today"): Promise<any> => {
  const response = await api.get(`/dispatch/metrics`, {
    params: { time_range: timeRange },
  });
  return response.data;
};
