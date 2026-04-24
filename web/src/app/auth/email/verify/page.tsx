"use client";

import axios, { type AxiosError } from "axios";
import { ArrowLeft, CheckCircle2, Clock3, Mail, RefreshCcw, ShieldAlert } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, startTransition, useEffect, useEffectEvent, useRef, useState } from "react";
import type { ClipboardEvent, KeyboardEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { authApiFetch } from "@/lib/api";
import {
  clearPendingEmailAuth,
  createPendingEmailAuth,
  loadPendingEmailAuth,
  savePendingEmailAuth,
} from "@/lib/pending-email-auth";
import { cn } from "@/lib/utils";
import { useAuthStore, type AuthUser } from "@/store/auth-store";

const DIGIT_COUNT = 6;
const RESEND_SECONDS = 60;
const TEN_MINUTES_MS = 10 * 60 * 1000;
const ONE_MINUTE_MS = 60 * 1000;

type VerifyResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

type SendOtpResponse = {
  message: string;
  expires_in_minutes: number;
  email: string;
};

type ApiErrorPayload = {
  detail?: string;
  retry_after?: number;
};

function formatClock(totalSeconds: number, padMinutes = true) {
  const clamped = Math.max(0, totalSeconds);
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  const minuteLabel = padMinutes ? String(minutes).padStart(2, "0") : String(minutes);
  return `${minuteLabel}:${String(seconds).padStart(2, "0")}`;
}

function parseAttemptsRemaining(detail: string | undefined) {
  const match = detail?.match(/(\d+)\s+attempts?\s+remaining/i);
  return match ? Number(match[1]) : null;
}

function sanitizeDigits(value: string) {
  return value.replace(/\D/g, "");
}

function getInitialEmailState(emailFromQuery: string) {
  if (typeof window === "undefined") {
    const fallbackNow = Date.now();
    return {
      email: emailFromQuery,
      expiresAt: fallbackNow + TEN_MINUTES_MS,
      resendAvailableAt: fallbackNow + ONE_MINUTE_MS,
      initialError: emailFromQuery
        ? null
        : "We couldn't find the email for this sign-in attempt. Please start again.",
    };
  }

  const stored = loadPendingEmailAuth();
  const nextEmail = emailFromQuery || stored?.email || "";
  const fallbackNow = Date.now();

  if (!nextEmail) {
    return {
      email: "",
      expiresAt: fallbackNow + TEN_MINUTES_MS,
      resendAvailableAt: fallbackNow + ONE_MINUTE_MS,
      initialError: "We couldn't find the email for this sign-in attempt. Please start again.",
    };
  }

  const nextState =
    stored && stored.email === nextEmail ? stored : createPendingEmailAuth(nextEmail);

  return {
    email: nextEmail,
    expiresAt: nextState.expiresAt,
    resendAvailableAt: nextState.resendAvailableAt,
    initialError: null,
  };
}

function EmailOtpVerificationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailFromQuery = searchParams.get("email")?.trim().toLowerCase() ?? "";
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const autoSubmitLockRef = useRef(false);
  const initialEmailState = getInitialEmailState(emailFromQuery);

  const hydrate = useAuthStore((state) => state.hydrate);
  const setSession = useAuthStore((state) => state.setSession);

  const [email, setEmail] = useState(initialEmailState.email);
  const [digits, setDigits] = useState<string[]>(() =>
    Array.from({ length: DIGIT_COUNT }, () => "")
  );
  const [expiresAt, setExpiresAt] = useState<number>(initialEmailState.expiresAt);
  const [resendAvailableAt, setResendAvailableAt] = useState<number>(
    initialEmailState.resendAvailableAt
  );
  const [now, setNow] = useState(() => Date.now());
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [isInvalidated, setIsInvalidated] = useState(false);
  const [isShaking, setIsShaking] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(initialEmailState.initialError);
  const [resendError, setResendError] = useState<string | null>(null);

  const joinedCode = digits.join("");
  const expirySeconds = Math.max(0, Math.ceil((expiresAt - now) / 1000));
  const resendSeconds = Math.max(0, Math.ceil((resendAvailableAt - now) / 1000));
  const hasCompleteCode = joinedCode.length === DIGIT_COUNT && digits.every(Boolean);
  const verifyDisabled =
    isSubmitting ||
    isResending ||
    expirySeconds === 0 ||
    isInvalidated ||
    !hasCompleteCode ||
    !email;
  const resendDisabled = isSubmitting || isResending || resendSeconds > 0;
  const friendlyEmail = email || "you@example.com";
  const effectiveStatusMessage =
    statusMessage ||
    (!isInvalidated && expirySeconds === 0 ? "Code expired. Request a new one to continue." : null);

  const tick = useEffectEvent(() => {
    setNow(Date.now());
  });
  const triggerAutoSubmit = useEffectEvent((code: string) => {
    void handleVerify(code);
  });

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!email) {
      return;
    }

    persistTiming(email, expiresAt, resendAvailableAt);
  }, [email, expiresAt, resendAvailableAt]);

  useEffect(() => {
    const intervalId = window.setInterval(() => tick(), 1000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!isShaking) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setIsShaking(false);
    }, 360);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isShaking]);

  useEffect(() => {
    if (!hasCompleteCode || verifyDisabled || autoSubmitLockRef.current) {
      return;
    }

    autoSubmitLockRef.current = true;
    triggerAutoSubmit(joinedCode);
  }, [hasCompleteCode, joinedCode, verifyDisabled]);

  const focusIndex = (index: number) => {
    const nextInput = inputRefs.current[index];
    nextInput?.focus();
    nextInput?.select();
  };

  const resetCode = (nextError?: string | null, nextStatus?: string | null) => {
    setDigits(Array.from({ length: DIGIT_COUNT }, () => ""));
    setIsShaking(true);
    setErrorMessage(nextError ?? null);
    setStatusMessage(nextStatus ?? null);
    autoSubmitLockRef.current = false;
    window.requestAnimationFrame(() => focusIndex(0));
  };

  const persistTiming = (
    nextEmail: string,
    nextExpiresAt: number,
    nextResendAvailableAt: number
  ) => {
    savePendingEmailAuth({
      email: nextEmail,
      expiresAt: nextExpiresAt,
      resendAvailableAt: nextResendAvailableAt,
    });
  };

  async function handleVerify(code: string) {
    autoSubmitLockRef.current = true;

    if (!email || expirySeconds === 0 || isInvalidated) {
      autoSubmitLockRef.current = false;
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setResendError(null);

    try {
      const response = await authApiFetch<VerifyResponse>("/auth/email/verify-otp", {
        method: "post",
        data: { email, code },
      });

      setSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        user: response.user,
      });
      clearPendingEmailAuth();
      toast.success("Code verified. Welcome back.");

      startTransition(() => {
        if (response.user.is_new_user) {
          router.push("/profile/complete");
        } else {
          router.push("/dashboard");
        }
      });
    } catch (error) {
      const apiError = error as AxiosError<ApiErrorPayload>;
      const detail =
        axios.isAxiosError(apiError) && apiError.response?.data?.detail
          ? apiError.response.data.detail
          : "We couldn't verify that code. Please try again.";

      const nextAttemptsRemaining = parseAttemptsRemaining(detail);
      if (detail.toLowerCase().includes("expired")) {
        setExpiresAt(Date.now());
        resetCode(detail, "Code expired. Request a new one to continue.");
      } else if (detail.toLowerCase().includes("too many invalid attempts")) {
        setIsInvalidated(true);
        setAttemptsRemaining(0);
        resetCode(
          "Code invalidated after too many attempts.",
          "Code invalidated. Request a fresh code to keep going."
        );
      } else {
        setAttemptsRemaining(nextAttemptsRemaining);
        resetCode(detail);
      }
    } finally {
      setIsSubmitting(false);
      window.setTimeout(() => {
        autoSubmitLockRef.current = false;
      }, 0);
    }
  }

  const handleDigitChange = (index: number, value: string) => {
    const nextValue = sanitizeDigits(value).slice(-1);
    if (!nextValue && value !== "") {
      return;
    }

    setDigits((current) => {
      const nextDigits = [...current];
      nextDigits[index] = nextValue;
      return nextDigits;
    });

    setErrorMessage(null);
    setStatusMessage(null);

    if (nextValue && index < DIGIT_COUNT - 1) {
      window.requestAnimationFrame(() => focusIndex(index + 1));
    }
  };

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace") {
      event.preventDefault();
      setDigits((current) => {
        const nextDigits = [...current];
        if (nextDigits[index]) {
          nextDigits[index] = "";
          return nextDigits;
        }

        const previousIndex = Math.max(0, index - 1);
        nextDigits[previousIndex] = "";
        window.requestAnimationFrame(() => focusIndex(previousIndex));
        return nextDigits;
      });
      autoSubmitLockRef.current = false;
      return;
    }

    if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      focusIndex(index - 1);
    }

    if (event.key === "ArrowRight" && index < DIGIT_COUNT - 1) {
      event.preventDefault();
      focusIndex(index + 1);
    }
  };

  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    event.preventDefault();
    const pasted = sanitizeDigits(event.clipboardData.getData("text")).slice(0, DIGIT_COUNT);
    if (pasted.length !== DIGIT_COUNT) {
      return;
    }

    setDigits(pasted.split(""));
    setErrorMessage(null);
    setStatusMessage(null);
    autoSubmitLockRef.current = false;
    window.requestAnimationFrame(() => focusIndex(DIGIT_COUNT - 1));
  };

  const handleResend = async () => {
    if (!email || resendDisabled) {
      return;
    }

    setIsResending(true);
    setResendError(null);
    setErrorMessage(null);
    setStatusMessage(null);

    try {
      const response = await authApiFetch<SendOtpResponse>("/auth/email/send-otp", {
        method: "post",
        data: { email },
      });
      const nextState = createPendingEmailAuth(response.email);
      setEmail(response.email);
      setDigits(Array.from({ length: DIGIT_COUNT }, () => ""));
      setExpiresAt(nextState.expiresAt);
      setResendAvailableAt(nextState.resendAvailableAt);
      setNow(Date.now());
      setAttemptsRemaining(null);
      setIsInvalidated(false);
      setStatusMessage("A fresh code is on its way.");
      autoSubmitLockRef.current = false;
      toast.success("New code sent.");
      window.requestAnimationFrame(() => focusIndex(0));
    } catch (error) {
      const apiError = error as AxiosError<ApiErrorPayload>;
      const retryAfter =
        axios.isAxiosError(apiError) && apiError.response?.data?.retry_after
          ? apiError.response.data.retry_after
          : RESEND_SECONDS;
      const detail =
        axios.isAxiosError(apiError) && apiError.response?.data?.detail
          ? apiError.response.data.detail
          : "We couldn't resend the code right now.";

      const nextAvailableAt = Date.now() + retryAfter * 1000;
      setResendAvailableAt(nextAvailableAt);
      setResendError(detail);
      persistTiming(email, expiresAt, nextAvailableAt);
    } finally {
      setIsResending(false);
    }
  };

  const attemptLabel =
    attemptsRemaining === null
      ? "Enter the code exactly as it appears in your inbox."
      : attemptsRemaining > 0
        ? `${attemptsRemaining} attempts remaining`
        : "No attempts remaining";
  const hasAlertError = Boolean(isInvalidated || errorMessage || resendError);

  return (
    <main className="relative flex min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.92),_rgba(247,236,221,0.98)_35%,_rgba(243,227,205,1)_100%)] px-4 py-6 text-stone-950 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 h-64 bg-[linear-gradient(180deg,rgba(120,53,15,0.18),rgba(120,53,15,0))]" />
        <div className="absolute -top-24 right-[-5rem] h-80 w-80 rounded-full bg-amber-300/30 blur-3xl" />
        <div className="absolute bottom-[-8rem] left-[-4rem] h-72 w-72 rounded-full bg-orange-400/18 blur-3xl" />
      </div>

      <section className="relative mx-auto flex w-full max-w-5xl flex-1 items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="hidden min-h-[44rem] rounded-[2rem] border border-stone-900/10 bg-stone-950 p-10 text-stone-50 shadow-[0_30px_120px_rgba(28,25,23,0.24)] lg:flex lg:flex-col lg:justify-between">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2">
                <div className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-amber-300 to-orange-500 text-stone-950">
                  AB
                </div>
                <div>
                  <p className="font-semibold tracking-[0.18em] text-amber-200/90 uppercase">
                    Agentic Bay
                  </p>
                  <p className="text-sm text-stone-400">Secure marketplace access</p>
                </div>
              </div>

              <div className="space-y-5">
                <p className="inline-flex items-center gap-2 rounded-full bg-white/8 px-3 py-1 text-xs font-medium tracking-[0.2em] text-amber-200/80 uppercase">
                  <Mail className="h-3.5 w-3.5" />
                  Passwordless sign-in
                </p>
                <h1 className="max-w-lg text-4xl leading-tight font-semibold">
                  One clean checkpoint before the dashboard opens.
                </h1>
                <p className="max-w-lg text-base leading-7 text-stone-300">
                  Enter the six-digit code from your inbox and we&apos;ll finish the sign-in flow
                  without ever asking for a password.
                </p>
              </div>
            </div>

            <div className="grid gap-4 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
              <div className="flex items-start gap-4">
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-amber-300/15 text-amber-200">
                  <ShieldAlert className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-stone-100">One-time code only</p>
                  <p className="mt-1 text-sm leading-6 text-stone-400">
                    Wrong entries count against the active code. After five misses you&apos;ll need
                    a fresh send.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-amber-300/15 text-amber-200">
                  <Clock3 className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-stone-100">Short expiry window</p>
                  <p className="mt-1 text-sm leading-6 text-stone-400">
                    The code stays valid for 10 minutes, then the form locks until you resend.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex min-h-[44rem] flex-col justify-center rounded-[2rem] border border-stone-900/10 bg-white/88 p-5 shadow-[0_28px_80px_rgba(120,53,15,0.18)] backdrop-blur md:p-8">
            <div className="flex h-full flex-col rounded-[1.6rem] border border-stone-900/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(250,245,237,0.9))] p-5 sm:p-7">
              <button
                type="button"
                onClick={() => router.back()}
                className="inline-flex w-fit items-center gap-2 text-sm font-medium text-stone-600 transition hover:text-stone-950"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>

              <div className="mt-8 flex-1">
                <div className="mb-8 space-y-4">
                  <div className="inline-flex items-center gap-3 rounded-full border border-amber-950/10 bg-amber-100/70 px-4 py-2 text-sm font-medium text-amber-950 lg:hidden">
                    <div className="grid h-8 w-8 place-items-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-xs font-semibold text-stone-950">
                      AB
                    </div>
                    Agentic Bay
                  </div>

                  <div className="space-y-3">
                    <h2 className="text-3xl leading-tight font-semibold text-stone-950">
                      Check your email
                    </h2>
                    <p className="max-w-md text-base leading-7 text-stone-600">
                      We sent a six-digit code to{" "}
                      <span className="font-semibold text-stone-950">{friendlyEmail}</span>.
                    </p>
                  </div>
                </div>

                <div className="rounded-[1.4rem] border border-stone-900/8 bg-white/92 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] sm:p-5">
                  <div onPaste={handlePaste} className={cn("space-y-5", isShaking && "otp-shake")}>
                    <div className="grid grid-cols-6 gap-2 sm:gap-3">
                      {digits.map((digit, index) => (
                        <input
                          key={index}
                          ref={(node) => {
                            inputRefs.current[index] = node;
                          }}
                          value={digit}
                          inputMode="numeric"
                          autoComplete={index === 0 ? "one-time-code" : "off"}
                          aria-label={`Digit ${index + 1}`}
                          maxLength={1}
                          disabled={isSubmitting || expirySeconds === 0 || isInvalidated}
                          onChange={(event) => handleDigitChange(index, event.target.value)}
                          onKeyDown={(event) => handleKeyDown(index, event)}
                          className={cn(
                            "aspect-square w-full rounded-[1.15rem] border bg-stone-50 text-center text-2xl font-semibold text-stone-950 transition duration-200 outline-none sm:text-3xl",
                            "focus:border-amber-500 focus:bg-white focus:shadow-[0_0_0_4px_rgba(245,158,11,0.15)]",
                            errorMessage || isInvalidated
                              ? "border-rose-400 bg-rose-50"
                              : "border-stone-300/80"
                          )}
                        />
                      ))}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-sm text-stone-600">
                      <span className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-1.5 font-medium text-stone-700">
                        <Clock3 className="h-4 w-4" />
                        {expirySeconds === 0
                          ? "Code expired"
                          : `Expires in ${formatClock(expirySeconds)}`}
                      </span>
                      {effectiveStatusMessage ? (
                        <span className="text-sm leading-6 text-stone-600">
                          {effectiveStatusMessage}
                        </span>
                      ) : null}
                    </div>

                    <Button
                      className="h-14 w-full rounded-[1.2rem] bg-stone-950 text-base font-semibold text-white transition hover:bg-stone-800"
                      disabled={verifyDisabled}
                      onClick={() => void handleVerify(joinedCode)}
                    >
                      {isSubmitting ? "Verifying..." : "Verify Code"}
                    </Button>
                  </div>
                </div>

                <div className="mt-6 space-y-4 rounded-[1.4rem] border border-stone-900/8 bg-stone-950/[0.03] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-stone-800">Didn&apos;t receive it?</p>
                      <p className="text-sm text-stone-600">
                        Resend becomes available after a short cooldown.
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        className="h-11 rounded-full border-stone-300 bg-white px-4 text-sm font-semibold text-stone-900 hover:bg-stone-100"
                        disabled={resendDisabled}
                        onClick={() => void handleResend()}
                      >
                        <RefreshCcw className="h-4 w-4" />
                        {isResending ? "Sending..." : "Resend Code"}
                      </Button>
                      <span className="min-w-28 text-right text-sm text-stone-500">
                        {resendSeconds > 0
                          ? `(available in ${formatClock(resendSeconds, false)})`
                          : "ready now"}
                      </span>
                    </div>
                  </div>

                  <div
                    className={cn(
                      "rounded-2xl border px-4 py-3 text-sm leading-6",
                      hasAlertError
                        ? "border-rose-200 bg-rose-50 text-rose-700"
                        : "border-amber-200 bg-amber-50 text-amber-900"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {hasAlertError ? (
                        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                      ) : (
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                      )}
                      <div className="space-y-1">
                        <p className="font-medium">
                          {isInvalidated
                            ? "Code invalidated"
                            : resendError
                              ? "Resend locked"
                              : attemptsRemaining !== null
                                ? attemptLabel
                                : "Security reminder"}
                        </p>
                        <p>
                          {isInvalidated
                            ? "Request a fresh code to continue signing in."
                            : errorMessage || resendError || attemptLabel}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function EmailOtpVerificationFallback() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.92),_rgba(247,236,221,0.98)_35%,_rgba(243,227,205,1)_100%)] px-4 py-6">
      <div className="w-full max-w-lg rounded-[2rem] border border-stone-900/10 bg-white/90 p-8 text-center shadow-[0_28px_80px_rgba(120,53,15,0.18)]">
        <p className="text-sm font-medium tracking-[0.18em] text-amber-800/80 uppercase">
          Loading verification
        </p>
        <h1 className="mt-4 text-3xl font-semibold text-stone-950">Preparing your code screen</h1>
        <p className="mt-3 text-base leading-7 text-stone-600">
          We&apos;re restoring the latest email sign-in state.
        </p>
      </div>
    </main>
  );
}

export default function EmailOtpVerificationPage() {
  return (
    <Suspense fallback={<EmailOtpVerificationFallback />}>
      <EmailOtpVerificationContent />
    </Suspense>
  );
}
