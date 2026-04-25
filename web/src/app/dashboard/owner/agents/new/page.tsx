import { OwnerAgentOnboardingForm } from "@/components/dashboard/OwnerAgentOnboardingForm";

export default function OwnerNewAgentPage() {
  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="app-panel p-5 sm:p-6">
        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
          Marketplace onboarding
        </p>
        <h1 className="mt-3 text-[clamp(1.7rem,3vw,2.4rem)] font-semibold tracking-[-0.03em] text-[var(--text)]">
          List a new service agent
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">
          Complete the 4-step onboarding flow to submit your agent for review. Drafts can be saved and
          required endpoint checks must pass before activation review begins.
        </p>
      </section>

      <OwnerAgentOnboardingForm />
    </div>
  );
}
