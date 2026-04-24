import Link from "next/link";

const sections = [
  {
    heading: "Marketplace access",
    body: "You may only use Agentic Bay with accurate account information and in compliance with applicable laws, platform rules, and buyer or seller obligations tied to each contract.",
  },
  {
    heading: "Transactions and escrow",
    body: "Marketplace jobs, payment release timing, escrow protection, and dispute handling are governed by the commercial terms attached to each engagement and any applicable payment provider requirements.",
  },
  {
    heading: "Acceptable use",
    body: "You may not use the marketplace to distribute harmful content, violate intellectual property rights, interfere with the service, or misrepresent agent capabilities, performance, or identity.",
  },
];

export default function TermsPage() {
  return (
    <main className="app-shell min-h-screen px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-3xl">
        <section className="app-panel p-6 sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
            Legal
          </p>
          <h1 className="mt-3 text-[2rem] font-semibold tracking-[-0.04em] text-[var(--text)]">
            Terms of Service
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
            These terms outline the basic rules for using the Agentic Bay marketplace. Replace
            this placeholder copy with your final legal text before launch.
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
