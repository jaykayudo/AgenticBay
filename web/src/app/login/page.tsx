"use client";

import axios, { type AxiosError } from "axios";
import { Command, LoaderCircle, LockKeyhole, Mail } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, startTransition, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApiFetch } from "@/lib/api";
import { createPendingEmailAuth, savePendingEmailAuth } from "@/lib/pending-email-auth";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";

const MARKETPLACE_NAME = process.env.NEXT_PUBLIC_MARKETPLACE_NAME ?? "Agentic Bay";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type AuthMethod = "google" | "facebook" | "email" | null;
type OAuthProvider = Exclude<AuthMethod, "email" | null>;

type OAuthAuthorizationURLResponse = {
  auth_url: string;
};

type SendOtpResponse = {
  message: string;
  expires_in_minutes: number;
  email: string;
};

type UserProfileResponse = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  email_verified: boolean;
  auth_provider: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type ApiErrorPayload = {
  detail?: string;
};

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.49 12.27c0-.79-.07-1.55-.2-2.27H12v4.3h6.45a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.1 3.56-5.18 3.56-8.65Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.07 7.93-2.91l-3.88-3c-1.08.72-2.45 1.14-4.05 1.14-3.11 0-5.74-2.1-6.68-4.92H1.32v3.1A12 12 0 0 0 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.32 14.31A7.2 7.2 0 0 1 4.95 12c0-.8.14-1.57.37-2.31v-3.1H1.32A12 12 0 0 0 0 12c0 1.93.46 3.75 1.32 5.41l4-3.1Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.34.6 4.59 1.78l3.44-3.45C17.94 1.17 15.23 0 12 0A12 12 0 0 0 1.32 6.59l4 3.1C6.26 6.87 8.89 4.77 12 4.77Z"
      />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path
        fill="#1877F2"
        d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07c0 6.03 4.39 11.03 10.13 11.93v-8.43H7.08v-3.5h3.05V9.41c0-3.03 1.79-4.7 4.54-4.7 1.31 0 2.68.24 2.68.24v2.98h-1.51c-1.49 0-1.95.93-1.95 1.88v2.26h3.32l-.53 3.5h-2.79V24C19.61 23.1 24 18.1 24 12.07Z"
      />
    </svg>
  );
}

function BrandMark() {
  return (
    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-[1.2rem] bg-[var(--primary)] text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]">
      <Command className="h-6 w-6" />
    </div>
  );
}

function AuthShell({
  children,
  subtitle,
}: {
  children: ReactNode;
  subtitle?: string;
}) {
  return (
    <main className="app-shell flex min-h-screen px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex w-full max-w-[28rem] items-center justify-center">
        <section className="app-panel w-full p-5 sm:p-8">
          <div className="text-center">
            <BrandMark />
            <p className="mt-5 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
              {MARKETPLACE_NAME}
            </p>
            <h1 className="mt-3 text-[1.95rem] font-semibold tracking-[-0.04em] text-[var(--text)]">
              Welcome to {MARKETPLACE_NAME}
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
              {subtitle ?? "Sign in to access the agent economy."}
            </p>
          </div>

          {children}
        </section>
      </div>
    </main>
  );
}

function ProviderButton({
  provider,
  label,
  activeMethod,
  disabled,
  onClick,
}: {
  provider: OAuthProvider;
  label: string;
  activeMethod: AuthMethod;
  disabled: boolean;
  onClick: () => void;
}) {
  const isLoading = activeMethod === provider;
  const Icon = provider === "google" ? GoogleIcon : FacebookIcon;

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "h-13 w-full justify-center rounded-[1rem] border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-semibold text-[var(--text)] shadow-[var(--shadow-soft)] hover:bg-[var(--surface-2)]",
        "disabled:border-[var(--border)] disabled:bg-[var(--surface)] disabled:text-[var(--text-muted)]"
      )}
    >
      <span className="mr-3 flex h-8 w-8 items-center justify-center rounded-full bg-[var(--surface-2)]">
        {isLoading ? <LoaderCircle className="h-4.5 w-4.5 animate-spin" /> : <Icon />}
      </span>
      {isLoading ? `Connecting to ${label}...` : `Continue with ${label}`}
    </Button>
  );
}

function formatCallbackError(error: string | null, description: string | null) {
  if (!error) {
    return null;
  }

  if (description) {
    return description.replace(/\+/g, " ");
  }

  const errorMessages: Record<string, string> = {
    oauth_failed: "We couldn't complete that social sign-in. Please try again.",
    access_denied: "Access was denied by the provider. Please try another sign-in method.",
    oauth_cancelled: "That sign-in was cancelled before it could be completed.",
  };

  return errorMessages[error] ?? "Something interrupted authentication. Please try again.";
}

function getApiErrorMessage(error: unknown, fallback: string) {
  const apiError = error as AxiosError<ApiErrorPayload>;

  if (axios.isAxiosError(apiError) && apiError.response?.data?.detail) {
    return apiError.response.data.detail;
  }

  return fallback;
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hydrate = useAuthStore((state) => state.hydrate);
  const hydrated = useAuthStore((state) => state.hydrated);
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearSession = useAuthStore((state) => state.clearSession);
  const user = useAuthStore((state) => state.user);

  const [email, setEmail] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [activeMethod, setActiveMethod] = useState<AuthMethod>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [dismissedCallbackError, setDismissedCallbackError] = useState(false);
  const [sessionCheckState, setSessionCheckState] = useState<"checking" | "guest" | "authenticated">(
    "checking"
  );

  const normalizedEmail = email.trim().toLowerCase();
  const emailIsValid = EMAIL_PATTERN.test(normalizedEmail);
  const emailHasValue = email.trim().length > 0;
  const showEmailValidation = emailTouched && emailHasValue && !emailIsValid;
  const callbackError = useMemo(
    () =>
      formatCallbackError(
        searchParams.get("error"),
        searchParams.get("error_description")
      ),
    [searchParams]
  );
  const displayedError =
    submissionError ?? (dismissedCallbackError ? null : callbackError);
  const authInProgress = activeMethod !== null;
  const authenticated = sessionCheckState === "authenticated";

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    let cancelled = false;

    const validateSession = async () => {
      if (!accessToken) {
        if (user) {
          clearSession();
        }

        if (!cancelled) {
          setSessionCheckState("guest");
        }
        return;
      }

      try {
        await authApiFetch<UserProfileResponse>("/auth/me", {
          method: "get",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (cancelled) {
          return;
        }

        setSessionCheckState("authenticated");
        startTransition(() => {
          router.replace("/dashboard");
        });
      } catch {
        if (cancelled) {
          return;
        }

        clearSession();
        setSessionCheckState("guest");
      }
    };

    void validateSession();

    return () => {
      cancelled = true;
    };
  }, [accessToken, clearSession, hydrated, router, user]);

  const dismissErrors = () => {
    setSubmissionError(null);
    setDismissedCallbackError(true);
  };

  const handleOAuth = async (provider: OAuthProvider) => {
    dismissErrors();
    setActiveMethod(provider);

    try {
      const response = await authApiFetch<OAuthAuthorizationURLResponse>(`/auth/${provider}`, {
        method: "get",
      });

      if (!response.auth_url) {
        throw new Error("Missing auth URL.");
      }

      window.location.assign(response.auth_url);
    } catch (error) {
      setSubmissionError(
        getApiErrorMessage(error, `We couldn't start ${provider} sign-in. Please try again.`)
      );
      setActiveMethod(null);
    }
  };

  const handleEmailSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setEmailTouched(true);

    if (!emailIsValid || authInProgress) {
      return;
    }

    dismissErrors();
    setActiveMethod("email");

    try {
      const response = await authApiFetch<SendOtpResponse>("/auth/email/send-otp", {
        method: "post",
        data: { email: normalizedEmail },
      });
      const pendingState = createPendingEmailAuth(response.email);
      savePendingEmailAuth(pendingState);

      startTransition(() => {
        router.push(`/auth/email/verify?email=${encodeURIComponent(response.email)}`);
      });
    } catch (error) {
      setSubmissionError(
        getApiErrorMessage(error, "We couldn't send a sign-in code right now. Please try again.")
      );
      setActiveMethod(null);
    }
  };

  if (!hydrated || sessionCheckState === "checking" || authenticated) {
    return (
      <AuthShell subtitle="Preparing your sign-in experience.">
        <div className="mt-10 flex flex-col items-center justify-center gap-4 rounded-[1.35rem] border border-[var(--border)] bg-[var(--surface-2)] px-5 py-10 text-center">
          <LoaderCircle className="h-6 w-6 animate-spin text-[var(--primary)]" />
          <p className="text-sm text-[var(--text-muted)]">
            {authenticated ? "Redirecting to your dashboard..." : "Checking your session..."}
          </p>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell subtitle="Sign in to access the agent economy.">
      <div className="mt-10 space-y-4">
        <ProviderButton
          provider="google"
          label="Google"
          activeMethod={activeMethod}
          disabled={authInProgress}
          onClick={() => void handleOAuth("google")}
        />

        <ProviderButton
          provider="facebook"
          label="Facebook"
          activeMethod={activeMethod}
          disabled={authInProgress}
          onClick={() => void handleOAuth("facebook")}
        />
      </div>

      <div className="my-7 flex items-center gap-4">
        <div className="h-px flex-1 bg-[var(--border)]" />
        <span className="text-sm text-[var(--text-muted)]">or</span>
        <div className="h-px flex-1 bg-[var(--border)]" />
      </div>

      <form className="space-y-4" onSubmit={(event) => void handleEmailSubmit(event)}>
        <div className="space-y-2">
          <label
            htmlFor="email"
            className="text-sm font-medium text-[var(--text)]"
          >
            Email address
          </label>

          <div className="relative">
            <Mail className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-[var(--text-muted)]" />
            <Input
              id="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              value={email}
              aria-invalid={showEmailValidation}
              disabled={authInProgress}
              placeholder="you@example.com"
              onChange={(event) => {
                dismissErrors();
                setEmail(event.target.value);
              }}
              onBlur={() => setEmailTouched(true)}
              className={cn(
                "h-13 rounded-[1rem] border-[var(--border)] bg-[var(--surface)] pl-11 pr-4 text-sm text-[var(--text)] shadow-[var(--shadow-soft)] placeholder:text-[var(--text-muted)]",
                "focus-visible:border-[var(--ring)] focus-visible:ring-4 focus-visible:ring-[var(--ring)]/60",
                showEmailValidation && "border-[var(--danger)]"
              )}
            />
          </div>

          {showEmailValidation ? (
            <p className="text-sm text-[var(--danger)]">
              Enter a valid email address to continue.
            </p>
          ) : null}
        </div>

        <Button
          type="submit"
          disabled={authInProgress || !emailIsValid}
          className="h-13 w-full rounded-[1rem] bg-[var(--primary)] text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] hover:opacity-95"
        >
          {activeMethod === "email" ? (
            <>
              <LoaderCircle className="h-4.5 w-4.5 animate-spin" />
              Continue with Email
            </>
          ) : (
            <>
              <LockKeyhole className="h-4.5 w-4.5" />
              Continue with Email
            </>
          )}
        </Button>
      </form>

      {displayedError ? (
        <div className="mt-5 rounded-[1rem] border border-[var(--danger-soft)] bg-[var(--danger-soft)] px-4 py-3 text-sm leading-6 text-[var(--danger)]">
          {displayedError}
        </div>
      ) : null}

      <p className="mt-7 text-center text-sm leading-6 text-[var(--text-muted)]">
        By signing in you agree to our{" "}
        <Link href="/terms" className="font-medium text-[var(--text)] transition hover:text-[var(--primary)]">
          Terms of Service
        </Link>{" "}
        and{" "}
        <Link
          href="/privacy"
          className="font-medium text-[var(--text)] transition hover:text-[var(--primary)]"
        >
          Privacy Policy
        </Link>
        .
      </p>
    </AuthShell>
  );
}

function LoginPageFallback() {
  return (
    <AuthShell subtitle="Preparing your sign-in experience.">
      <div className="mt-10 flex flex-col items-center justify-center gap-4 rounded-[1.35rem] border border-[var(--border)] bg-[var(--surface-2)] px-5 py-10 text-center">
        <LoaderCircle className="h-6 w-6 animate-spin text-[var(--primary)]" />
        <p className="text-sm text-[var(--text-muted)]">Loading sign-in options...</p>
      </div>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageFallback />}>
      <LoginContent />
    </Suspense>
  );
}
