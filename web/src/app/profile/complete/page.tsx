"use client";

import { ArrowRight, UserRound } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";

export default function ProfileCompletionPage() {
  const hydrate = useAuthStore((state) => state.hydrate);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.94),_rgba(247,236,221,0.98)_36%,_rgba(241,227,205,1)_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <section className="rounded-[2rem] border border-stone-900/10 bg-white/90 p-8 shadow-[0_28px_80px_rgba(120,53,15,0.16)]">
          <div className="inline-flex items-center gap-2 rounded-full border border-stone-900/10 bg-stone-50 px-3 py-1.5 text-sm font-medium text-stone-700">
            <UserRound className="h-4 w-4 text-amber-700" />
            New account
          </div>
          <h1 className="mt-5 text-3xl font-semibold text-stone-950">Complete your profile</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-stone-600">
            {user?.email
              ? `${user.email} is verified and signed in.`
              : "Your email is verified and your account is active."}{" "}
            This route now exists as the post-OTP destination for first-time users.
          </p>

          <div className="mt-8 grid gap-4 rounded-[1.5rem] border border-stone-900/8 bg-stone-950/[0.03] p-5">
            <div>
              <h2 className="text-lg font-semibold text-stone-950">Suggested first fields</h2>
              <p className="mt-2 text-sm leading-6 text-stone-600">
                Display name, marketplace preferences, and anything else you want to capture before
                the first full dashboard visit.
              </p>
            </div>
            <Link
              href="/dashboard"
              className={cn(
                buttonVariants({ size: "lg" }),
                "h-12 w-fit rounded-full bg-stone-950 px-5 text-sm font-semibold text-white hover:bg-stone-800"
              )}
            >
              Continue to dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
