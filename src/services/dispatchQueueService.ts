/**
 * dispatchQueueService.ts
 * API service for fetching dispatch queue data.
 */

import axios from "axios";
import type { DispatchQueueResponse } from "../types/dispatchQueue";

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

export interface DispatchQueueParams {
  status?: string;
  priority?: string;
  zone?: string;
  cursor?: string;
  limit?: number;
}

/**
 * Fetch dispatch queue jobs with optional filters and cursor pagination.
 */
export const getDispatchQueue = async (
  params: DispatchQueueParams = {}
): Promise<DispatchQueueResponse> => {
  try {
    const response = await api.get<DispatchQueueResponse>("/dispatch/queue", {
      params: {
        ...(params.status && { status: params.status }),
        ...(params.priority && { priority: params.priority }),
        ...(params.zone && { zone: params.zone }),
        ...(params.cursor && { cursor: params.cursor }),
        ...(params.limit && { limit: params.limit }),
      },
    });
    return response.data;
  } catch (error) {
    console.error("Failed to fetch dispatch queue:", error);
    throw error;
  }
};
