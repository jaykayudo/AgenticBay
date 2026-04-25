import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";
import type { TokenResponse } from "@/lib/api/types";
import type { AuthUser } from "@/store/auth-store";

export type AuthResponse = TokenResponse & {
  token_type: "bearer";
  user: AuthUser;
};

export type OAuthAuthorizationURLResponse = {
  auth_url: string;
};

export type SendOtpResponse = {
  message: string;
  expires_in_minutes: number;
  email: string;
};

export type FacebookEmailRequiredResponse = {
  pending_token: string;
  email_required: true;
};

export type UserProfile = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  status?: string;
  email_verified?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type CompleteProfilePayload = {
  username: string;
  display_name: string;
  role: string;
};

export const authApi = {
  googleAuthUrl: (): Promise<AxiosResponse<OAuthAuthorizationURLResponse>> =>
    authApiClient.get("/auth/google"),

  googleCallback: (code: string, state: string): Promise<AxiosResponse<AuthResponse>> =>
    authApiClient.get("/auth/google/callback", { params: { code, state } }),

  facebookAuthUrl: (): Promise<AxiosResponse<OAuthAuthorizationURLResponse>> =>
    authApiClient.get("/auth/facebook"),

  facebookCallback: (
    code: string,
    state: string
  ): Promise<AxiosResponse<AuthResponse | FacebookEmailRequiredResponse>> =>
    authApiClient.get("/auth/facebook/callback", { params: { code, state } }),

  facebookComplete: (pendingToken: string, email: string): Promise<AxiosResponse<unknown>> =>
    authApiClient.post("/auth/facebook/complete", {
      pending_token: pendingToken,
      email,
    }),

  facebookVerifyEmail: (
    pendingToken: string,
    email: string,
    code: string
  ): Promise<AxiosResponse<AuthResponse>> =>
    authApiClient.post("/auth/facebook/verify-email", {
      pending_token: pendingToken,
      email,
      code,
    }),

  sendOtp: (email: string): Promise<AxiosResponse<SendOtpResponse>> =>
    authApiClient.post("/auth/email/send-otp", { email }),

  verifyOtp: (email: string, code: string): Promise<AxiosResponse<AuthResponse>> =>
    authApiClient.post("/auth/email/verify-otp", { email, code }),

  refresh: (refreshToken: string): Promise<AxiosResponse<TokenResponse>> =>
    authApiClient.post("/auth/refresh", { refresh_token: refreshToken }),

  logout: (refreshToken: string): Promise<AxiosResponse<void>> =>
    authApiClient.post("/auth/logout", { refresh_token: refreshToken }),

  logoutAll: (): Promise<AxiosResponse<{ revoked_sessions: number }>> =>
    authApiClient.post("/auth/logout-all"),

  me: (): Promise<AxiosResponse<UserProfile>> => authApiClient.get("/auth/me"),

  completeProfile: (data: CompleteProfilePayload): Promise<AxiosResponse<UserProfile>> =>
    authApiClient.patch("/auth/profile/complete", data),
};
