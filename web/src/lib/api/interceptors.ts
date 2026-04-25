import type { AxiosError, AxiosInstance } from "axios";

import { normalizeApiError } from "@/lib/api/errors";
import type { RetriableRequestConfig } from "@/lib/api/types";
import { tokenManager } from "@/lib/auth/tokenManager";

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function redirectToSignIn(): void {
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

function flushRefreshQueue(error: unknown, token?: string): void {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token);
    } else {
      reject(error);
    }
  });
  refreshQueue = [];
}

function requestHadBearerToken(config: RetriableRequestConfig): boolean {
  const authorization =
    typeof config.headers?.get === "function"
      ? config.headers.get("Authorization")
      : config.headers?.Authorization;

  return typeof authorization === "string" && authorization.startsWith("Bearer ");
}

export function attachInterceptors(apiClient: AxiosInstance): AxiosInstance {
  apiClient.interceptors.request.use((config) => {
    const token = tokenManager.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as RetriableRequestConfig | undefined;

      if (
        error.response?.status === 401 &&
        originalRequest &&
        !originalRequest._retry &&
        requestHadBearerToken(originalRequest)
      ) {
        originalRequest._retry = true;

        if (isRefreshing) {
          try {
            const token = await new Promise<string>((resolve, reject) => {
              refreshQueue.push({ resolve, reject });
            });

            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          } catch (refreshError) {
            return Promise.reject(normalizeApiError(refreshError));
          }
        }

        isRefreshing = true;

        try {
          const newToken = await tokenManager.refreshAccessToken();
          flushRefreshQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          flushRefreshQueue(refreshError);
          tokenManager.clearAuth();
          redirectToSignIn();
          return Promise.reject(normalizeApiError(refreshError));
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(normalizeApiError(error));
    }
  );

  return apiClient;
}
