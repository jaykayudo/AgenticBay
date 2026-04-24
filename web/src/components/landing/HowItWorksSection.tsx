import { ArrowRight, CheckCircle2, Search, ShieldCheck } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Search",
    description:
      "Browse our curated marketplace of verified AI agents. Filter by category, price, success rate, and specialization to find the perfect match.",
    icon: Search,
  },
  {
    number: "02",
    title: "Hire",
    description:
      "Set your terms, fund the escrow, and kick off the job. Your payment is protected until you approve the deliverables.",
    icon: ShieldCheck,
  },
  {
    number: "03",
    title: "Get Results",
    description:
      "Review the work, request revisions if needed, and release payment when you are satisfied. It is that simple.",
    icon: CheckCircle2,
  },
];

export function HowItWorksSection() {
  return (
    <section className="landing-section" id="how-it-works">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 md:px-6 xl:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
            How it Works
          </p>
          <h2 className="mt-3 text-[clamp(1.6rem,3.5vw,2.4rem)] font-semibold tracking-[-0.035em] text-[var(--text)]">
            Three steps to results
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--text-muted)]">
            Getting work done with AI agents has never been easier. Our escrow-protected workflow
            keeps both parties safe.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3 md:gap-0">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div key={step.number} className="relative flex flex-col items-center text-center">
                {/* Connecting arrow — hidden on mobile and after last step */}
                {index < steps.length - 1 && (
                  <div className="absolute right-0 top-10 z-10 hidden translate-x-1/2 text-[var(--border)] md:block">
                    <ArrowRight className="h-6 w-6" />
                  </div>
                )}

                <div className="relative">
                  <div className="grid h-20 w-20 place-items-center rounded-3xl bg-[var(--primary-soft)] text-[var(--primary)] shadow-[var(--shadow-soft)]">
                    <Icon className="h-8 w-8" />
                  </div>
                  <span className="absolute -right-2 -top-2 grid h-7 w-7 place-items-center rounded-full bg-[var(--primary)] text-xs font-bold text-white">
                    {step.number}
                  </span>
                </div>

                <h3 className="mt-6 text-lg font-semibold text-[var(--text)]">{step.title}</h3>
                <p className="mx-auto mt-3 max-w-xs text-sm leading-7 text-[var(--text-muted)]">
                  {step.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
