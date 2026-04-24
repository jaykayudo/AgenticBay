import axios, { type AxiosError, type AxiosRequestConfig } from "axios";

import { mockApiFetch, supportsMockApi } from "@/lib/mock-api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE_URL}/api/v1`;
const API_ROOT = `${API_BASE_URL}/api`;
const USE_MOCK_MARKETPLACE_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA !== "false";

export const apiClient = axios.create({
  baseURL: API_V1,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

export const authApiClient = axios.create({
  baseURL: API_ROOT,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("auth_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export async function apiFetch<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
  const canMock = USE_MOCK_MARKETPLACE_DATA && supportsMockApi(path);

  if (canMock) {
    return mockApiFetch<T>(path, config);
  }

  try {
    const response = await apiClient.request<T>({ url: path, ...config });
    return response.data;
  } catch (error) {
    if (supportsMockApi(path)) {
      return mockApiFetch<T>(path, config);
    }
    throw error;
  }
}

export async function authApiFetch<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await authApiClient.request<T>({ url: path, ...config });
  return response.data;
}
