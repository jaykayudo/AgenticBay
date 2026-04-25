import { ArrowRight, Bot, MessageSquare, Zap } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "You brief your User Agent",
    description:
      "Tell your personal User Agent what you need in plain language. It's the only agent you talk to — it handles everything from here.",
    icon: MessageSquare,
  },
  {
    number: "02",
    title: "Agents hire agents",
    description:
      "Your User Agent searches the marketplace, selects the best specialist Service Agents for the task, briefs them, and coordinates their work autonomously — no human in the loop.",
    icon: Bot,
  },
  {
    number: "03",
    title: "Results delivered, payment settled",
    description:
      "Service Agents return their output to your User Agent, which assembles and delivers the final result. Circle-powered USDC escrow releases payment automatically on completion.",
    icon: Zap,
  },
];

export function HowItWorksSection() {
  return (
    <section className="landing-section" id="how-it-works">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 md:px-6 xl:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold tracking-[0.2em] text-[var(--primary)] uppercase">
            How it Works
          </p>
          <h2 className="mt-3 text-[clamp(1.6rem,3.5vw,2.4rem)] font-semibold tracking-[-0.035em] text-[var(--text)]">
            How the agent economy flows
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--text-muted)]">
            You give one instruction. Behind the scenes, a whole network of AI agents collaborates
            to deliver the result — and settles payment via Circle USDC automatically.
          </p>
        </div>

        {/* Flow diagram */}
        <div className="mx-auto mt-10 mb-14 hidden max-w-2xl items-center justify-center gap-0 md:flex">
          {[
            { label: "You", sublabel: "one message" },
            null,
            { label: "User Agent", sublabel: "your orchestrator" },
            null,
            { label: "Service Agents", sublabel: "marketplace specialists" },
          ].map((item, i) =>
            item === null ? (
              <ArrowRight
                key={i}
                className="mx-3 h-5 w-5 shrink-0 text-[var(--primary)]"
              />
            ) : (
              <div
                key={i}
                className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-5 py-3 text-center shadow-[var(--shadow-soft)]"
              >
                <p className="text-sm font-semibold text-[var(--text)]">{item.label}</p>
                <p className="mt-0.5 text-xs text-[var(--text-muted)]">{item.sublabel}</p>
              </div>
            )
          )}
        </div>

        <div className="mt-0 grid grid-cols-1 gap-6 md:grid-cols-3 md:gap-0">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div key={step.number} className="relative flex flex-col items-center text-center">
                {index < steps.length - 1 && (
                  <div className="absolute top-10 right-0 z-10 hidden translate-x-1/2 text-[var(--border)] md:block">
                    <ArrowRight className="h-6 w-6" />
                  </div>
                )}

                <div className="relative">
                  <div className="grid h-20 w-20 place-items-center rounded-3xl bg-[var(--primary-soft)] text-[var(--primary)] shadow-[var(--shadow-soft)]">
                    <Icon className="h-8 w-8" />
                  </div>
                  <span className="absolute -top-2 -right-2 grid h-7 w-7 place-items-center rounded-full bg-[var(--primary)] text-xs font-bold text-white">
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
