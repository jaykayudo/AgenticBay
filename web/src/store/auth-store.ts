"use client";

import { create } from "zustand";

type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  is_new_user: boolean;
};

type AuthSession = {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
};

type AuthState = AuthSession & {
  hydrated: boolean;
  hydrate: () => void;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
};

const AUTH_USER_KEY = "auth_user";

function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    localStorage.removeItem(AUTH_USER_KEY);
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  hydrated: false,
  hydrate: () => {
    if (typeof window === "undefined") {
      return;
    }

    set({
      accessToken: localStorage.getItem("access_token"),
      refreshToken: localStorage.getItem("refresh_token"),
      user: readStoredUser(),
      hydrated: true,
    });
  },
  setSession: ({ accessToken, refreshToken, user }) => {
    if (typeof window !== "undefined") {
      if (accessToken) {
        localStorage.setItem("access_token", accessToken);
      } else {
        localStorage.removeItem("access_token");
      }

      if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
      } else {
        localStorage.removeItem("refresh_token");
      }

      if (user) {
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
      } else {
        localStorage.removeItem(AUTH_USER_KEY);
      }
    }

    set({
      accessToken,
      refreshToken,
      user,
      hydrated: true,
    });
  },
  clearSession: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem(AUTH_USER_KEY);
    }

    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      hydrated: true,
    });
  },
}));

export type { AuthUser };
