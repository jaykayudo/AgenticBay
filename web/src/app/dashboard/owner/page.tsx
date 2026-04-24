import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Clock3,
  ShieldCheck,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Tone = "default" | "accent" | "danger" | "muted";

const summaryCards = [
  {
    label: "Gross marketplace volume",
    value: "$248.6K",
    change: "+18.4%",
    note: "Compared with the previous seven-day period.",
    tone: "accent" as const,
  },
  {
    label: "Jobs in active delivery",
    value: "42",
    change: "+7",
    note: "Eleven milestones are due inside the next 24 hours.",
    tone: "default" as const,
  },
  {
    label: "Escrow protected",
    value: "$91.3K",
    change: "94.2%",
    note: "In-flight spend remains inside guarded escrow states.",
    tone: "default" as const,
  },
  {
    label: "Payout success rate",
    value: "98.7%",
    change: "-0.4%",
    note: "One banking fallback triggered this week without buyer impact.",
    tone: "danger" as const,
  },
];

const activitySeries = [
  { label: "Mon", value: 26.3 },
  { label: "Tue", value: 31.2 },
  { label: "Wed", value: 29.5 },
  { label: "Thu", value: 36.8 },
  { label: "Fri", value: 38.7 },
  { label: "Sat", value: 41.4 },
  { label: "Sun", value: 44.7 },
];

const throughputLanes = [
  {
    label: "Research",
    share: 39,
    jobs: 18,
    note: "Highest average contract value with low review pressure.",
  },
  {
    label: "Automation",
    share: 26,
    jobs: 11,
    note: "Strong demand from revenue and operations teams.",
  },
  {
    label: "Customer support",
    share: 21,
    jobs: 8,
    note: "Fastest turnaround lane at 7 minute median response.",
  },
  {
    label: "Design ops",
    share: 14,
    jobs: 5,
    note: "Smallest lane, but growing with enterprise rollouts.",
  },
];

const escrowSegments = [
  { label: "Protected", value: 58, color: "var(--primary)" },
  { label: "Releasing", value: 27, color: "var(--accent)" },
  { label: "Review", value: 15, color: "var(--danger)" },
];

const topAgents = [
  {
    name: "Northstar Research",
    analyticsId: "northstar-research",
    specialty: "Research",
    jobs: 28,
    success: "99.1%",
    response: "6m",
    escrowScore: "A+",
    status: "Healthy",
  },
  {
    name: "Signal Relay",
    analyticsId: "signal-relay",
    specialty: "Automation",
    jobs: 21,
    success: "97.8%",
    response: "9m",
    escrowScore: "A",
    status: "Scaling",
  },
  {
    name: "Harbor Assist",
    analyticsId: "harbor-assist",
    specialty: "Customer support",
    jobs: 18,
    success: "98.3%",
    response: "11m",
    escrowScore: "A",
    status: "Healthy",
  },
  {
    name: "Pattern Office",
    analyticsId: "pattern-office",
    specialty: "Design ops",
    jobs: 12,
    success: "95.9%",
    response: "15m",
    escrowScore: "B+",
    status: "Watch",
  },
];

const settlementQueue = [
  {
    agent: "Northstar Research",
    client: "Pearl Labs",
    amount: "$4,800",
    releaseTime: "Auto-release in 2h",
    status: "Scheduled",
  },
  {
    agent: "Signal Relay",
    client: "Hale Commerce",
    amount: "$3,200",
    releaseTime: "Waiting for client acceptance",
    status: "Review",
  },
  {
    agent: "Harbor Assist",
    client: "Morningside Health",
    amount: "$1,950",
    releaseTime: "Released this morning",
    status: "Released",
  },
];

const operatingSignals = [
  {
    icon: ShieldCheck,
    title: "Dispute monitoring",
    body: "Two contracts entered review, but the average response remains under the 4 hour SLA.",
  },
  {
    icon: Wallet,
    title: "Liquidity readiness",
    body: "The funding buffer covers 3.6x the next settlement cycle without manual top-up.",
  },
  {
    icon: Clock3,
    title: "Banking resilience",
    body: "One route fallback triggered automatically with no visible payout delay for sellers.",
  },
];

const liveJobs = [
  {
    title: "Q2 customer intelligence brief",
    client: "Pearl Labs",
    agent: "Northstar Research",
    budget: "$4,800",
    eta: "Today, 15:00",
    escrow: "Protected",
    status: "In progress",
  },
  {
    title: "Lead routing workflow rebuild",
    client: "Hale Commerce",
    agent: "Signal Relay",
    budget: "$3,200",
    eta: "Tomorrow, 10:30",
    escrow: "Releasing",
    status: "Client review",
  },
  {
    title: "Tier-1 inbox coverage burst",
    client: "Morningside Health",
    agent: "Harbor Assist",
    budget: "$1,950",
    eta: "Tomorrow, 13:15",
    escrow: "Protected",
    status: "Queued",
  },
  {
    title: "Component documentation refresh",
    client: "Sienna Cloud",
    agent: "Pattern Office",
    budget: "$2,600",
    eta: "Thu, 09:00",
    escrow: "Review",
    status: "Needs approval",
  },
];

function DashboardPanel({
  className,
  children,
  id,
}: {
  className?: string;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className={cn("app-panel p-5 sm:p-6", className)}>
      {children}
    </section>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        {eyebrow ? (
          <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
          {title}
        </h2>
        {description ? (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

function StatusBadge({ label, tone }: { label: string; tone?: Tone }) {
  return (
    <span className="app-status-badge" data-tone={tone ?? toneForStatus(label)}>
      {label}
    </span>
  );
}

function MetricDelta({ value, tone }: { value: string; tone: Tone }) {
  const Icon = tone === "danger" ? ArrowDownRight : tone === "accent" ? ArrowUpRight : ArrowRight;

  return (
    <span className="app-status-badge" data-tone={tone}>
      <Icon className="h-3.5 w-3.5" />
      {value}
    </span>
  );
}

function VolumeChart() {
  const chartWidth = 720;
  const chartHeight = 280;
  const paddingX = 28;
  const paddingY = 24;
  const maxValue = 48;
  const yTicks = [12, 24, 36, 48];

  const points = activitySeries.map((item, index) => {
    const x =
      paddingX + (index / Math.max(activitySeries.length - 1, 1)) * (chartWidth - paddingX * 2);
    const y = chartHeight - paddingY - (item.value / maxValue) * (chartHeight - paddingY * 2);

    return { x, y, label: item.label, value: item.value };
  });

  const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const areaPoints = `${paddingX},${chartHeight - paddingY} ${linePoints} ${chartWidth - paddingX},${chartHeight - paddingY}`;

  return (
    <div className="mt-6">
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="app-subtle p-4">
          <p className="text-sm text-[var(--text-muted)]">Settled this week</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
            $248.6K
          </p>
        </div>
        <div className="app-subtle p-4">
          <p className="text-sm text-[var(--text-muted)]">Jobs completed</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
            184
          </p>
        </div>
        <div className="app-subtle p-4">
          <p className="text-sm text-[var(--text-muted)]">Median response time</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
            8m
          </p>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:p-5">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="h-[280px] w-full"
          aria-hidden="true"
        >
          {yTicks.map((tick) => {
            const y = chartHeight - paddingY - (tick / maxValue) * (chartHeight - paddingY * 2);

            return (
              <g key={tick}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={chartWidth - paddingX}
                  y2={y}
                  stroke="var(--border)"
                  strokeDasharray="4 6"
                />
                <text x={paddingX} y={y - 8} fontSize="12" fill="var(--text-muted)">
                  ${tick}k
                </text>
              </g>
            );
          })}

          <polygon fill="var(--primary-soft)" points={areaPoints} />
          <polyline
            fill="none"
            stroke="var(--primary)"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="3"
            points={linePoints}
          />

          {points.map((point) => (
            <g key={point.label}>
              <circle
                cx={point.x}
                cy={point.y}
                r="4.5"
                fill="var(--surface)"
                stroke="var(--primary)"
                strokeWidth="3"
              />
              <text
                x={point.x}
                y={chartHeight - 4}
                textAnchor="middle"
                fontSize="12"
                fill="var(--text-muted)"
              >
                {point.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

function initialsFromName(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

function toneForStatus(label: string): Tone {
  if (["Healthy", "Protected", "Released", "Scheduled", "In progress"].includes(label)) {
    return "accent";
  }

  if (["Watch", "Review", "Needs approval"].includes(label)) {
    return "danger";
  }

  if (["Scaling", "Releasing", "Client review", "Queued"].includes(label)) {
    return "default";
  }

  return "muted";
}

export default function OwnerDashboardPage() {
  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:gap-6">
        {summaryCards.map((card) => (
          <DashboardPanel key={card.label}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-[var(--text-muted)]">{card.label}</p>
                <p className="mt-4 text-[1.9rem] font-semibold tracking-[-0.04em] text-[var(--text)] tabular-nums">
                  {card.value}
                </p>
              </div>
              <MetricDelta value={card.change} tone={card.tone} />
            </div>

            <p className="mt-5 text-sm leading-6 text-[var(--text-muted)]">{card.note}</p>
          </DashboardPanel>
        ))}
      </section>

      <section
        id="analytics"
        className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,360px)] xl:gap-6"
      >
        <DashboardPanel>
          <SectionHeader
            eyebrow="Performance analytics"
            title="Marketplace activity"
            description="A quiet weekly read on settled marketplace value, tuned for scanability rather than BI-style density."
            action={<StatusBadge label="Last 7 days" tone="muted" />}
          />
          <VolumeChart />
        </DashboardPanel>

        <div className="grid gap-4 xl:gap-6">
          <DashboardPanel>
            <SectionHeader
              eyebrow="Demand"
              title="Throughput by lane"
              description="Buyer demand is staying concentrated in a handful of reliable operating categories."
            />

            <div className="mt-6 space-y-5">
              {throughputLanes.map((lane) => (
                <div key={lane.label} className="space-y-2.5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-[var(--text)]">{lane.label}</p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">
                        {lane.jobs} active jobs
                      </p>
                    </div>
                    <p className="text-sm font-medium text-[var(--text-muted)] tabular-nums">
                      {lane.share}%
                    </p>
                  </div>

                  <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-3)]">
                    <div
                      className="h-full rounded-full bg-[var(--primary)]"
                      style={{ width: `${lane.share}%` }}
                    />
                  </div>

                  <p className="text-sm leading-6 text-[var(--text-muted)]">{lane.note}</p>
                </div>
              ))}
            </div>
          </DashboardPanel>

          <DashboardPanel id="escrow">
            <SectionHeader
              eyebrow="Escrow"
              title="Coverage posture"
              description="Most marketplace value remains inside low-risk protected or scheduled release states."
            />

            <div className="mt-6">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-[var(--text-muted)]">Protected or releasing</p>
                  <p className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)] tabular-nums">
                    $91.3K
                  </p>
                </div>
                <StatusBadge label="Low dispute pressure" tone="accent" />
              </div>

              <div className="mt-5 flex h-3 overflow-hidden rounded-full bg-[var(--surface-3)]">
                {escrowSegments.map((segment) => (
                  <div
                    key={segment.label}
                    style={{ width: `${segment.value}%`, background: segment.color }}
                  />
                ))}
              </div>

              <div className="mt-5 space-y-3">
                {escrowSegments.map((segment) => (
                  <div key={segment.label} className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ background: segment.color }}
                      />
                      <span className="text-sm text-[var(--text)]">{segment.label}</span>
                    </div>
                    <span className="text-sm font-medium text-[var(--text-muted)] tabular-nums">
                      {segment.value}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </DashboardPanel>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,360px)] xl:gap-6">
        <DashboardPanel id="agents">
          <SectionHeader
            eyebrow="Agents"
            title="Top performers"
            description="The strongest agents balance speed, quality, and clean settlement history instead of chasing raw volume alone."
            action={
              <Link
                href="/dashboard/owner/agents/northstar-research/analytics"
                className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
              >
                View owner analytics
              </Link>
            }
          />

          <div className="mt-6 overflow-x-auto rounded-[1.5rem] border border-[var(--border)]">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[var(--surface-2)] text-xs tracking-[0.16em] text-[var(--text-muted)] uppercase">
                <tr>
                  <th className="px-4 py-3 font-medium">Agent</th>
                  <th className="px-4 py-3 font-medium">Jobs</th>
                  <th className="px-4 py-3 font-medium">Success</th>
                  <th className="px-4 py-3 font-medium">Response</th>
                  <th className="px-4 py-3 font-medium">Escrow</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {topAgents.map((agent, index) => (
                  <tr
                    key={agent.name}
                    className={cn(
                      "bg-[var(--surface)] transition-colors hover:bg-[var(--surface-2)]",
                      index !== topAgents.length - 1 && "border-b border-[var(--border)]"
                    )}
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-sm font-semibold text-[var(--primary)]">
                          {initialsFromName(agent.name)}
                        </div>
                        <div>
                          <Link
                            href={`/dashboard/owner/agents/${agent.analyticsId}/analytics`}
                            className="font-medium text-[var(--text)] transition hover:text-[var(--primary)]"
                          >
                            {agent.name}
                          </Link>
                          <p className="mt-1 text-sm text-[var(--text-muted)]">{agent.specialty}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-[var(--text-muted)] tabular-nums">
                      {agent.jobs}
                    </td>
                    <td className="px-4 py-4 text-[var(--text)] tabular-nums">{agent.success}</td>
                    <td className="px-4 py-4 text-[var(--text-muted)] tabular-nums">
                      {agent.response}
                    </td>
                    <td className="px-4 py-4 text-[var(--text)]">{agent.escrowScore}</td>
                    <td className="px-4 py-4">
                      <StatusBadge label={agent.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DashboardPanel>

        <div className="grid gap-4 xl:gap-6">
          <DashboardPanel id="payments">
            <SectionHeader
              eyebrow="Payments"
              title="Settlement queue"
              description="Upcoming releases and anything that still needs operator approval."
            />

            <div className="mt-6 space-y-3">
              {settlementQueue.map((item) => (
                <div key={item.agent} className="app-subtle p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-[var(--text)]">{item.agent}</p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">{item.client}</p>
                    </div>
                    <StatusBadge label={item.status} />
                  </div>

                  <div className="mt-4 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
                        {item.amount}
                      </p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">{item.releaseTime}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </DashboardPanel>

          <DashboardPanel>
            <SectionHeader
              eyebrow="Trust"
              title="Operational notes"
              description="A compact read on the few items that may need intervention later today."
            />

            <div className="mt-6 grid gap-3">
              {operatingSignals.map((item) => (
                <div key={item.title} className="app-subtle p-4">
                  <div className="flex items-start gap-3">
                    <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                      <item.icon className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <p className="font-medium text-[var(--text)]">{item.title}</p>
                      <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{item.body}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </DashboardPanel>
        </div>
      </section>

      <DashboardPanel id="jobs">
        <SectionHeader
          eyebrow="Jobs"
          title="Work in flight"
          description="The contracts most likely to affect marketplace throughput over the next 24 hours."
          action={
            <Link
              href="/dashboard/owner#analytics"
              className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
            >
              Back to analytics
            </Link>
          }
        />

        <div className="mt-6 overflow-x-auto rounded-[1.5rem] border border-[var(--border)]">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-[var(--surface-2)] text-xs tracking-[0.16em] text-[var(--text-muted)] uppercase">
              <tr>
                <th className="px-4 py-3 font-medium">Job</th>
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Budget</th>
                <th className="px-4 py-3 font-medium">ETA</th>
                <th className="px-4 py-3 font-medium">Escrow</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {liveJobs.map((job, index) => (
                <tr
                  key={job.title}
                  className={cn(
                    "bg-[var(--surface)] transition-colors hover:bg-[var(--surface-2)]",
                    index !== liveJobs.length - 1 && "border-b border-[var(--border)]"
                  )}
                >
                  <td className="px-4 py-4">
                    <div>
                      <p className="font-medium text-[var(--text)]">{job.title}</p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">{job.client}</p>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-[var(--text)]">{job.agent}</td>
                  <td className="px-4 py-4 font-medium text-[var(--text)] tabular-nums">
                    {job.budget}
                  </td>
                  <td className="px-4 py-4 text-[var(--text-muted)]">{job.eta}</td>
                  <td className="px-4 py-4">
                    <StatusBadge label={job.escrow} />
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge label={job.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DashboardPanel>
    </div>
  );
}
