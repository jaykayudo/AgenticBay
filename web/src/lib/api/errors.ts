import axios, { type AxiosError } from "axios";

import type { ApiErrorCode, ApiErrorShape } from "@/lib/api/types";

function getResponseMessage(data: unknown): string | null {
  if (!data || typeof data !== "object") {
    return null;
  }

  const detail = "detail" in data ? data.detail : undefined;
  if (typeof detail === "string") {
    return detail;
  }

  const message = "message" in data ? data.message : undefined;
  return typeof message === "string" ? message : null;
}

function getErrorCode(status?: number): ApiErrorCode {
  if (status === 401) {
    return "AUTH_REQUIRED";
  }

  if (status && status >= 500) {
    return "SERVER_ERROR";
  }

  if (status) {
    return "REQUEST_ERROR";
  }

  return "NETWORK_ERROR";
}

export function normalizeApiError(error: unknown): ApiErrorShape {
  if (axios.isCancel(error) || (axios.isAxiosError(error) && error.code === "ERR_CANCELED")) {
    return {
      message: "Request was cancelled.",
      code: "CANCELLED",
      isApiError: true,
    };
  }

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    const details = axiosError.response?.data;

    return {
      message:
        getResponseMessage(details) ??
        axiosError.message ??
        (status ? `Request failed with status ${status}.` : "Network request failed."),
      code: getErrorCode(status),
      status,
      details,
      isApiError: true,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      code: "UNKNOWN_ERROR",
      isApiError: true,
    };
  }

  return {
    message: "An unknown error occurred.",
    code: "UNKNOWN_ERROR",
    details: error,
    isApiError: true,
  };
}

export function isApiError(error: unknown): error is ApiErrorShape {
  return Boolean(error && typeof error === "object" && "isApiError" in error);
}
