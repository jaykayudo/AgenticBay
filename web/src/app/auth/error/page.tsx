import { AlertTriangle } from "lucide-react";
import Link from "next/link";

const ERROR_MESSAGES: Record<string, string> = {
  oauth_invalid: "The provider returned an incomplete sign-in response.",
  oauth_failed: "We could not complete that social sign-in.",
  oauth_email_required: "Facebook needs a verified email before this sign-in can continue.",
};

type AuthErrorPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AuthErrorPage({ searchParams }: AuthErrorPageProps) {
  const params = await searchParams;
  const errorType =
    typeof params.error_type === "string" ? params.error_type : "oauth_failed";
  const message =
    ERROR_MESSAGES[errorType] ??
    (errorType.startsWith("oauth_")
      ? "The OAuth provider could not complete sign-in."
      : "Authentication could not be completed.");

  return (
    <main className="app-shell grid min-h-screen place-items-center px-4 py-8">
      <section className="app-panel w-full max-w-lg p-6 text-center sm:p-8">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[var(--danger-soft)] text-[var(--danger)]">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <p className="mt-5 text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
          {errorType}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-[var(--text)]">Sign-in interrupted</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{message}</p>
        <Link
          href="/login"
          className="mt-7 inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)]"
        >
          Try again
        </Link>
      </section>
    </main>
  );
}
