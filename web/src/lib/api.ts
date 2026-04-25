import type { AxiosRequestConfig } from "axios";

import { apiClient, authApiClient } from "@/lib/api/client";
import { mockApiFetch, supportsMockApi } from "@/lib/mock-api";

const USE_MOCK_MARKETPLACE_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA !== "false";

export { apiClient, authApiClient };

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
