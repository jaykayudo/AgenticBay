"use client";

const PENDING_EMAIL_AUTH_KEY = "pending_email_auth";
const TEN_MINUTES_MS = 10 * 60 * 1000;
const RESEND_COOLDOWN_MS = 60 * 1000;

type PendingEmailAuthState = {
  email: string;
  expiresAt: number;
  resendAvailableAt: number;
};

function now() {
  return Date.now();
}

export function createPendingEmailAuth(email: string): PendingEmailAuthState {
  const timestamp = now();
  return {
    email,
    expiresAt: timestamp + TEN_MINUTES_MS,
    resendAvailableAt: timestamp + RESEND_COOLDOWN_MS,
  };
}

export function loadPendingEmailAuth(): PendingEmailAuthState | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = sessionStorage.getItem(PENDING_EMAIL_AUTH_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as PendingEmailAuthState;
  } catch {
    sessionStorage.removeItem(PENDING_EMAIL_AUTH_KEY);
    return null;
  }
}

export function savePendingEmailAuth(state: PendingEmailAuthState) {
  if (typeof window === "undefined") {
    return;
  }

  sessionStorage.setItem(PENDING_EMAIL_AUTH_KEY, JSON.stringify(state));
}

export function clearPendingEmailAuth() {
  if (typeof window === "undefined") {
    return;
  }

  sessionStorage.removeItem(PENDING_EMAIL_AUTH_KEY);
}

export type { PendingEmailAuthState };
