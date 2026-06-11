import axios, { InternalAxiosRequestConfig, AxiosResponse } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Use token from localStorage (real auth) or fall back to dev token from .env
    const token =
      localStorage.getItem("token") ||
      localStorage.getItem("access_token") ||
      import.meta.env.VITE_AUTH_TOKEN;

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Backend routes require X-Tenant-ID header
    const tenantId = localStorage.getItem("tenant_id") || import.meta.env.VITE_TENANT_ID;
    if (tenantId && config.headers) {
      config.headers["X-Tenant-ID"] = tenantId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    console.error("Backend API Error:", {
      baseURL: API_BASE_URL,
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    });

    return Promise.reject(error);
  }
);

export default api;
