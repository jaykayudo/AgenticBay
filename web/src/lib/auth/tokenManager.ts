import axios from "axios";

import type { TokenResponse } from "@/lib/api/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_ROOT = `${API_BASE_URL}/api`;
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const AUTH_USER_KEY = "auth_user";
const REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

let accessTokenMemory: string | null = null;
let refreshTokenMemory: string | null = null;

function hasBrowserStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function setRefreshCookie(refreshToken: string): void {
  if (typeof document === "undefined") {
    return;
  }

  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${REFRESH_TOKEN_KEY}=${encodeURIComponent(
    refreshToken
  )}; Path=/; Max-Age=${REFRESH_COOKIE_MAX_AGE}; SameSite=Lax${secure}`;
}

function clearRefreshCookie(): void {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${REFRESH_TOKEN_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export const tokenManager = {
  getAccessToken(): string | null {
    if (accessTokenMemory) {
      return accessTokenMemory;
    }

    if (!hasBrowserStorage()) {
      return null;
    }

    accessTokenMemory = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    return accessTokenMemory;
  },

  getRefreshToken(): string | null {
    if (refreshTokenMemory) {
      return refreshTokenMemory;
    }

    if (!hasBrowserStorage()) {
      return null;
    }

    refreshTokenMemory = window.localStorage.getItem(REFRESH_TOKEN_KEY);
    return refreshTokenMemory;
  },

  setTokens(accessToken: string, refreshToken: string): void {
    accessTokenMemory = accessToken;
    refreshTokenMemory = refreshToken;

    if (!hasBrowserStorage()) {
      return;
    }

    setRefreshCookie(refreshToken);
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error("Refresh token is missing.");
    }

    const response = await axios.post<TokenResponse>(
      "/auth/refresh",
      { refresh_token: refreshToken },
      {
        baseURL: API_ROOT,
        withCredentials: true,
        headers: { "Content-Type": "application/json" },
        timeout: 30000,
      }
    );

    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data.access_token;
  },

  clearAuth(): void {
    accessTokenMemory = null;
    refreshTokenMemory = null;

    if (!hasBrowserStorage()) {
      return;
    }

    clearRefreshCookie();
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(AUTH_USER_KEY);
  },
};
