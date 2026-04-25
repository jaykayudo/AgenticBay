"use client";

import { ArrowLeft, ExternalLink, LoaderCircle, ShieldCheck, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { useAdminGuard } from "@/hooks/useAdminAgents";
import { adminApi } from "@/lib/api/admin";

export default function AdminAgentReviewPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const router = useRouter();
  const guard = useAdminGuard();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data, isLoading, mutate } = useSWR(
    guard.isAdmin && agentId ? ["/admin/agents/review", agentId] : null,
    () => adminApi.reviewAgent(agentId).then((response) => response.data)
  );

  async function approve() {
    setIsSubmitting(true);
    try {
      await adminApi.approveAgent(agentId);
      await mutate();
      router.push("/dashboard/admin");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function reject() {
    const reason = window.prompt("Reason for rejection");
    if (!reason) {
      return;
    }

    setIsSubmitting(true);
    try {
      await adminApi.rejectAgent(agentId, reason);
      await mutate();
      router.push("/dashboard/admin");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!guard.hydrated || !guard.isAdmin) {
    return (
      <main className="app-shell grid min-h-screen place-items-center p-6">
        <section className="app-panel flex items-center gap-3 p-5 text-sm text-[var(--text-muted)]">
          <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
          Checking admin access
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell min-h-screen p-4 md:p-6">
      <div className="mx-auto max-w-[var(--layout-max)] space-y-6">
        <Link
          href="/dashboard/admin"
          className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Admin dashboard
        </Link>

        <section className="app-panel p-5 sm:p-6">
          <span className="app-status-badge" data-tone="accent">
            <ShieldCheck className="h-3.5 w-3.5" />
            Agent review
          </span>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-[var(--text)]">
                {data?.agent.name ?? "Pending agent"}
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
                {data?.agent.description ?? "Loading agent submission detail..."}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={isSubmitting || isLoading}
                onClick={() => void approve()}
                className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-60"
              >
                <ShieldCheck className="h-4 w-4" />
                Approve
              </button>
              <button
                type="button"
                disabled={isSubmitting || isLoading}
                onClick={() => void reject()}
                className="inline-flex h-11 items-center gap-2 rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)] disabled:opacity-60"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Submission</h2>
            {isLoading ? (
              <p className="mt-4 text-sm text-[var(--text-muted)]">Loading review packet...</p>
            ) : (
              <div className="mt-4 space-y-4 text-sm">
                <div>
                  <p className="text-[var(--text-muted)]">Base URL</p>
                  <p className="mt-1 break-all font-medium text-[var(--text)]">
                    {data?.agent.baseUrl ?? "--"}
                  </p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Source code</p>
                  {data?.sourceCodeUrl ? (
                    <a
                      href={data.sourceCodeUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-2 rounded-full border border-[var(--border)] px-4 py-2 font-medium text-[var(--text)]"
                    >
                      Open repository
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  ) : (
                    <p className="mt-1 text-[var(--text-muted)]">No source code URL provided.</p>
                  )}
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Review notes</p>
                  <p className="mt-1 leading-6 text-[var(--text)]">
                    {data?.reviewNotes ?? "No review notes yet."}
                  </p>
                </div>
              </div>
            )}
          </div>

          <aside className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Owner</h2>
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-[var(--text-muted)]">Email</p>
                <p className="mt-1 break-all font-medium text-[var(--text)]">
                  {data?.owner.email ?? "--"}
                </p>
              </div>
              <div>
                <p className="text-[var(--text-muted)]">Role / status</p>
                <p className="mt-1 font-medium text-[var(--text)]">
                  {data ? `${data.owner.role} / ${data.owner.status}` : "--"}
                </p>
              </div>
              <div>
                <p className="text-[var(--text-muted)]">Proxy contract</p>
                <p className="mt-1 break-all font-medium text-[var(--text)]">
                  {data?.proxyContractAddress ?? "--"}
                </p>
              </div>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
