"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { authApi, type AuthResponse } from "@/lib/api/auth";
import { tokenManager } from "@/lib/auth/tokenManager";
import { useAuthStore } from "@/store/auth-store";

export function useAuth() {
  const router = useRouter();
  const authState = useAuthStore();

  const login = useCallback(
    (data: AuthResponse) => {
      authState.setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
    },
    [authState]
  );

  const sendEmailOtp = useCallback(async (email: string) => {
    const { data } = await authApi.sendOtp(email);
    return data;
  }, []);

  const verifyEmailOtp = useCallback(
    async (email: string, code: string) => {
      const { data } = await authApi.verifyOtp(email, code);
      login(data);
      return data;
    },
    [login]
  );

  const signInWithGoogle = useCallback(async () => {
    const { data } = await authApi.googleAuthUrl();
    window.location.href = data.auth_url;
  }, []);

  const signInWithFacebook = useCallback(async () => {
    const { data } = await authApi.facebookAuthUrl();
    window.location.href = data.auth_url;
  }, []);

  const refresh = useCallback(async () => {
    const refreshToken = tokenManager.getRefreshToken();
    if (!refreshToken) {
      throw new Error("Refresh token is missing.");
    }

    const { data } = await authApi.refresh(refreshToken);
    tokenManager.setTokens(data.access_token, data.refresh_token);
    authState.setSession({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: authState.user,
    });
    return data;
  }, [authState]);

  const logout = useCallback(async () => {
    const refreshToken = tokenManager.getRefreshToken();

    try {
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } finally {
      authState.clearSession();
      router.replace("/login");
    }
  }, [authState, router]);

  const logoutAll = useCallback(async () => {
    try {
      await authApi.logoutAll();
    } finally {
      authState.clearSession();
      router.replace("/login");
    }
  }, [authState, router]);

  const loadMe = useCallback(async () => {
    const { data } = await authApi.me();
    return data;
  }, []);

  return {
    ...authState,
    login,
    sendEmailOtp,
    verifyEmailOtp,
    signInWithGoogle,
    signInWithFacebook,
    refresh,
    logout,
    logoutAll,
    loadMe,
  };
}
