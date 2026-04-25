import axios, { type AxiosInstance } from "axios";

import { attachInterceptors } from "@/lib/api/interceptors";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE_URL}/api/v1`;
const API_ROOT = `${API_BASE_URL}/api`;

export const apiClient: AxiosInstance = attachInterceptors(
  axios.create({
    baseURL: API_V1,
    withCredentials: true,
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
  })
);

export const authApiClient: AxiosInstance = attachInterceptors(
  axios.create({
    baseURL: API_ROOT,
    withCredentials: true,
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
  })
);
