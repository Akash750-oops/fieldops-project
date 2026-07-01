import api from './api';

export interface GPSHistoryPoint {
  id: string;
  technician_id: string;
  job_id: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  accuracy: number | null;
  altitude: number | null;
  tenant_id: string;
  created_at: string;
}

export const getGPSHistory = async (
  technicianId: string,
  params?: { job_id?: string; start_time?: string; end_time?: string }
): Promise<GPSHistoryPoint[]> => {
  const response = await api.get<GPSHistoryPoint[]>(`/api/v1/gps/history/${technicianId}`, { params });
  return response.data;
};
