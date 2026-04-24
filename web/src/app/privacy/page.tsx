import Link from "next/link";

const sections = [
  {
    heading: "Account data",
    body: "We collect the information required to create and secure your marketplace account, including email address, session metadata, and basic profile details needed to operate the service.",
  },
  {
    heading: "Operational data",
    body: "We process job activity, payment status, escrow events, and marketplace analytics so teams can manage supply, trust, and fulfillment across the platform.",
  },
  {
    heading: "Security and compliance",
    body: "We use authentication logs, one-time passcode events, and other security signals to protect accounts, prevent abuse, and satisfy legal or payment-provider obligations.",
  },
];

export default function PrivacyPage() {
  return (
    <main className="app-shell min-h-screen px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-3xl">
        <section className="app-panel p-6 sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
            Legal
          </p>
          <h1 className="mt-3 text-[2rem] font-semibold tracking-[-0.04em] text-[var(--text)]">
            Privacy Policy
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
            This summary explains the kinds of data the platform uses and why. Replace this
            placeholder copy with your final privacy policy before production launch.
          </p>

          <div className="mt-8 space-y-6">
            {sections.map((section) => (
              <section key={section.heading} className="app-subtle p-5">
                <h2 className="text-lg font-semibold text-[var(--text)]">{section.heading}</h2>
                <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{section.body}</p>
              </section>
            ))}
          </div>

          <div className="mt-8">
            <Link
              href="/login"
              className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-4 py-2 text-sm font-medium text-[var(--text)] transition hover:border-[var(--primary)] hover:text-[var(--primary)]"
            >
              Back to sign in
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
