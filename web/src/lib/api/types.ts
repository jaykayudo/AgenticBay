import type { AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";

export type ApiErrorCode =
  | "AUTH_REQUIRED"
  | "CANCELLED"
  | "NETWORK_ERROR"
  | "REQUEST_ERROR"
  | "SERVER_ERROR"
  | "UNKNOWN_ERROR";

export type ApiErrorShape = {
  message: string;
  code: ApiErrorCode;
  status?: number;
  details?: unknown;
  isApiError: true;
};

export type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export type ApiRequestConfig = AxiosRequestConfig & {
  signal?: AbortSignal;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};
