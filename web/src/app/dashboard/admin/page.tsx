"use client";

import { ExternalLink, LoaderCircle, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  useAdminGuard,
  useAdminJobs,
  useAdminStats,
  useAdminUsers,
  usePendingAgents,
} from "@/hooks/useAdminAgents";
import { adminApi, type AgentReviewDetail } from "@/lib/api/admin";

export default function AdminDashboardPage() {
  const guard = useAdminGuard();
  const pendingAgents = usePendingAgents();
  const stats = useAdminStats();
  const users = useAdminUsers();
  const jobs = useAdminJobs();
  const [reviewDetail, setReviewDetail] = useState<AgentReviewDetail | null>(null);
  const [rejectingAgentId, setRejectingAgentId] = useState("");

  async function openReview(agentId: string) {
    const { data } = await adminApi.reviewAgent(agentId);
    setReviewDetail(data);
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
        <section className="app-panel p-5 sm:p-6">
          <span className="app-status-badge" data-tone="accent">
            <ShieldCheck className="h-3.5 w-3.5" />
            Admin only
          </span>
          <h1 className="mt-4 text-3xl font-semibold text-[var(--text)]">
            Internal review dashboard
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
            Review pending agents, manage user access, and monitor platform operating stats.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {[
            ["Users", stats.stats?.users],
            ["Agents", stats.stats?.agents],
            ["Pending", stats.stats?.pendingAgents],
            ["Jobs", stats.stats?.jobs],
            ["Active jobs", stats.stats?.activeJobs],
            ["Volume", stats.stats ? `$${stats.stats.volumeUsdc.toLocaleString()}` : undefined],
          ].map(([label, value]) => (
            <div key={label} className="app-panel p-4">
              <p className="text-sm text-[var(--text-muted)]">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text)] tabular-nums">
                {value ?? "--"}
              </p>
            </div>
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,420px)]">
          <div className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Pending agent reviews</h2>
            <div className="mt-4 space-y-3">
              {pendingAgents.isLoading ? (
                <p className="text-sm text-[var(--text-muted)]">Loading pending agents...</p>
              ) : null}
              {pendingAgents.agents.map((agent) => (
                <article
                  key={agent.id}
                  className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="font-semibold text-[var(--text)]">{agent.name}</p>
                      <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                        {agent.description}
                      </p>
                      <button
                        type="button"
                        onClick={() => void openReview(agent.id)}
                        className="mt-3 text-sm font-medium text-[var(--primary)]"
                      >
                        Load review detail
                      </button>
                      <Link
                        href={`/dashboard/admin/agents/${agent.id}/review`}
                        className="ml-4 text-sm font-medium text-[var(--primary)]"
                      >
                        Open review page
                      </Link>
                      {agent.sourceCodeUrl ? (
                        <a
                          href={agent.sourceCodeUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="ml-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--primary)]"
                        >
                          Source
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => void pendingAgents.approve(agent.id)}
                        className="inline-flex h-10 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)]"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const reason = rejectingAgentId === agent.id ? "Rejected by admin." : "";
                          setRejectingAgentId(agent.id);
                          if (reason) void pendingAgents.reject(agent.id, reason);
                        }}
                        className="inline-flex h-10 rounded-full border border-[var(--border)] px-4 text-sm font-semibold text-[var(--text)]"
                      >
                        {rejectingAgentId === agent.id ? "Confirm reject" : "Reject"}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
              {!pendingAgents.isLoading && pendingAgents.agents.length === 0 ? (
                <p className="text-sm text-[var(--text-muted)]">No pending agents.</p>
              ) : null}
            </div>
          </div>

          <aside className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Review detail</h2>
            {reviewDetail ? (
              <div className="mt-4 space-y-4 text-sm">
                <div>
                  <p className="text-[var(--text-muted)]">Agent</p>
                  <p className="font-semibold text-[var(--text)]">{reviewDetail.agent.name}</p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Owner</p>
                  <p className="font-semibold text-[var(--text)]">{reviewDetail.owner.email}</p>
                </div>
                {reviewDetail.sourceCodeUrl ? (
                  <a
                    href={reviewDetail.sourceCodeUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] px-4 py-2 font-medium text-[var(--text)]"
                  >
                    Source code
                    <ExternalLink className="h-4 w-4" />
                  </a>
                ) : (
                  <p className="text-[var(--text-muted)]">No source code URL provided.</p>
                )}
                {reviewDetail.reviewNotes ? (
                  <p className="leading-6 text-[var(--text-muted)]">{reviewDetail.reviewNotes}</p>
                ) : null}
              </div>
            ) : (
              <p className="mt-4 text-sm text-[var(--text-muted)]">
                Select a pending agent to inspect source URL and owner details.
              </p>
            )}
          </aside>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <div className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Users</h2>
            <div className="mt-4 space-y-3">
              {users.users.map((user) => (
                <div
                  key={user.id}
                  className="flex flex-col gap-3 rounded-2xl border border-[var(--border)] p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-[var(--text)]">{user.email}</p>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                      {user.role} / {user.status}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => void users.setStatus(user.id, "SUSPENDED")}
                      className="rounded-full border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--text)]"
                    >
                      Suspend
                    </button>
                    <button
                      type="button"
                      onClick={() => void users.setStatus(user.id, "BANNED")}
                      className="rounded-full border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--text)]"
                    >
                      Ban
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">All jobs</h2>
            <div className="mt-4 overflow-x-auto rounded-2xl border border-[var(--border)]">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-[var(--surface-2)] text-xs text-[var(--text-muted)] uppercase">
                  <tr>
                    <th className="px-4 py-3">Job</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.jobs.map((job) => (
                    <tr key={job.id} className="border-t border-[var(--border)]">
                      <td className="px-4 py-3 text-[var(--text)]">{job.id}</td>
                      <td className="px-4 py-3 text-[var(--text-muted)]">{"status" in job ? job.status : "--"}</td>
                      <td className="px-4 py-3 text-[var(--text-muted)]">
                        {"amountUsdc" in job && typeof job.amountUsdc === "number"
                          ? `${job.amountUsdc} USDC`
                          : "--"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
