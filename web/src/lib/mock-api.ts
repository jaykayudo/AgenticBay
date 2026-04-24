import type { AxiosRequestConfig } from "axios";

import {
  getMarketplaceAgentDetail,
  marketplaceAgentDetails,
  marketplaceAgents,
} from "@/lib/marketplace-data";

type AnalyticsRange = "7d" | "30d" | "90d" | "all";

type MarketplaceStats = {
  totalAgents: number;
  totalVolume: number;
  totalJobs: number;
};

type MarketplaceAgentInsightsResponse = {
  agentSlug: string;
  agentName: string;
  generatedAt: string;
  stats: {
    successRate: number;
    totalJobs: number;
    totalEarned: number;
    avgJobValue: number;
    avgDeliveryMinutes: number;
    avgDeliveryLabel: string;
    repeatBuyerRate: number;
    onTimeRate: number;
    payoutCompletionRate: number;
    metrics: Array<{
      label: string;
      value: string;
      detail: string;
    }>;
    responseTimeDistribution: Array<{
      label: string;
      count: number;
      percentage: number;
      averageMinutes: number;
    }>;
  };
  reviews: Array<{
    id: string;
    reviewerName: string;
    company: string;
    rating: number;
    comment: string;
    jobTitle: string;
    createdAt: string;
  }>;
};

type AgentAnalyticsResponse = {
  agentId: string;
  agentName: string;
  ownerName: string;
  range: AnalyticsRange;
  generatedAt: string;
  summary: {
    totalJobs: number;
    totalEarned: number;
    successRate: number;
    avgJobValue: number;
  };
  revenueSeries: Array<{
    label: string;
    amount: number;
    jobs: number;
  }>;
  actionBreakdown: Array<{
    action: string;
    count: number;
    percentage: number;
    earned: number;
  }>;
  reviews: Array<{
    id: string;
    reviewerName: string;
    company: string;
    rating: number;
    comment: string;
    jobTitle: string;
    createdAt: string;
  }>;
  responseTimeDistribution: Array<{
    label: string;
    count: number;
    percentage: number;
    averageMinutes: number;
  }>;
};

type MarketplaceSessionStatus =
  | "queued"
  | "processing"
  | "awaiting_payment"
  | "completed"
  | "cancelled"
  | "closed";

export type MockMarketplaceSessionRecord = {
  sessionId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  priceUsdc: number;
  estimatedDurationLabel: string;
  inputSummary: string;
  amountLockedUsdc: number;
  status: MarketplaceSessionStatus;
  mode: "hire" | "demo";
  createdAt: string;
  redirectPath: string;
  sessionToken: string;
  socketUrl: string;
  resultPayload: Record<string, unknown> | null;
};

type MarketplaceSessionCreateRequest = {
  actionId: string;
  actionName: string;
  priceUsdc: number;
  estimatedDurationLabel: string;
  inputSummary: string;
  mode: "hire" | "demo";
};

type BuyerDashboardJobStatus = "done" | "running" | "failed";

type CircleWalletBalanceResponse = {
  provider: "Circle";
  walletId: string;
  walletAddress: string;
  availableBalanceUsdc: number;
  pendingBalanceUsdc: number;
  lockedInEscrowUsdc: number;
  lastUpdatedAt: string;
  syncStatus: "live";
};

type BuyerDashboardSummaryResponse = {
  generatedAt: string;
  stats: {
    totalJobs: number;
    totalSpentUsdc: number;
    savedAgentsCount: number;
  };
  recentJobs: Array<{
    sessionId: string;
    agentSlug: string;
    agentName: string;
    actionName: string;
    status: BuyerDashboardJobStatus;
    statusLabel: "Done" | "Running" | "Failed";
    amountChargedUsdc: number;
    createdAt: string;
    mode: "hire" | "demo";
  }>;
};

type BuyerRecommendedAgent = {
  id: string;
  slug: string;
  name: string;
  description: string;
  rating: number;
  reviewCount: number;
  startingPriceUsdc: number;
  speedLabel: string;
  tags: string[];
  avatar: {
    label: string;
    bg: string;
    fg: string;
  };
  reason: string;
};

const MOCK_SESSIONS_STORAGE_KEY = "agenticbay.mock.marketplace.sessions";

const ownerNames = [
  "Maya Chen",
  "Jordan Hale",
  "Leah Morgan",
  "Avery Cole",
  "Sofia Martinez",
  "Noah Bennett",
  "Priya Shah",
  "Elijah Ford",
  "Anika Rose",
  "Miles Turner",
];

const reviewerNames = [
  "Ava Thompson",
  "Liam Carter",
  "Noah Brooks",
  "Mia Patel",
  "Ella Morgan",
  "Zoe Kim",
  "Nina Shah",
  "Lucas Grant",
  "Jenna Marsh",
  "Arjun Rao",
];

const companyNames = [
  "Pearl Labs",
  "Hale Commerce",
  "Sienna Cloud",
  "Rivergrid",
  "Northwind Health",
  "Brightwell",
  "Fieldline",
  "Crestline",
  "Morningside Health",
  "Northscale",
];

const commentTemplates = [
  "Clear execution around {tag} with outputs that were immediately usable.",
  "{agent} handled the delivery smoothly and reduced a lot of coordination overhead.",
  "Strong work on {tag} and the final package was easy to operationalize.",
  "Fast turnaround, practical detail, and a useful next-step recommendation.",
  "The result quality was strong and the handoff notes were especially helpful.",
];

function round(value: number, digits = 1) {
  const scale = 10 ** digits;
  return Math.round(value * scale) / scale;
}

function isBrowser() {
  return typeof window !== "undefined";
}

function readMockSessions() {
  if (!isBrowser()) {
    return inMemorySessions;
  }

  const raw = window.localStorage.getItem(MOCK_SESSIONS_STORAGE_KEY);
  if (!raw) {
    return seededMockSessions;
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, MockMarketplaceSessionRecord>;
    return {
      ...seededMockSessions,
      ...parsed,
    };
  } catch {
    window.localStorage.removeItem(MOCK_SESSIONS_STORAGE_KEY);
    return seededMockSessions;
  }
}

function writeMockSessions(sessions: Record<string, MockMarketplaceSessionRecord>) {
  const next = {
    ...seededMockSessions,
    ...sessions,
  };

  inMemorySessions = next;

  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(MOCK_SESSIONS_STORAGE_KEY, JSON.stringify(next));
}

export function patchMockMarketplaceSession(
  sessionId: string,
  updates: Partial<MockMarketplaceSessionRecord>
) {
  const sessions = readMockSessions();
  const current = sessions[sessionId];
  if (!current) {
    return null;
  }

  const next = { ...current, ...updates };
  writeMockSessions({
    ...sessions,
    [sessionId]: next,
  });
  return next;
}

function getMockMarketplaceSession(sessionId: string) {
  return readMockSessions()[sessionId] ?? null;
}

function createMockMarketplaceSession(
  agentSlug: string,
  payload: MarketplaceSessionCreateRequest
): MockMarketplaceSessionRecord {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock session could not find agent '${agentSlug}'.`);
  }

  const sessionId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `mock-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  const session: MockMarketplaceSessionRecord = {
    sessionId,
    agentSlug: agent.slug,
    agentName: agent.name,
    actionId: payload.actionId,
    actionName: payload.actionName,
    priceUsdc: payload.priceUsdc,
    estimatedDurationLabel: payload.estimatedDurationLabel,
    inputSummary: payload.inputSummary,
    amountLockedUsdc: 0,
    status: "queued",
    mode: payload.mode,
    createdAt: new Date().toISOString(),
    redirectPath: `/jobs/${sessionId}`,
    sessionToken: `mock-session-token-${sessionId}`,
    socketUrl: `mock://jobs/${sessionId}`,
    resultPayload: null,
  };

  const sessions = readMockSessions();
  writeMockSessions({
    ...sessions,
    [sessionId]: session,
  });

  return session;
}

function createSeedMarketplaceSession({
  agentSlug,
  actionIndex = 0,
  sessionId,
  status,
  mode,
  hoursAgo,
  amountLockedUsdc,
}: {
  agentSlug: string;
  actionIndex?: number;
  sessionId: string;
  status: MarketplaceSessionStatus;
  mode: "hire" | "demo";
  hoursAgo: number;
  amountLockedUsdc?: number;
}) {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock seed session could not find agent '${agentSlug}'.`);
  }

  const action = agent.actions[actionIndex] ?? agent.actions[0];
  const createdAt = new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();
  const lockedAmount =
    amountLockedUsdc ??
    (status === "processing" || status === "completed" || status === "cancelled"
      ? action.priceUsdc
      : 0);

  const session: MockMarketplaceSessionRecord = {
    sessionId,
    agentSlug: agent.slug,
    agentName: agent.name,
    actionId: action.id,
    actionName: action.name,
    priceUsdc: mode === "demo" ? 0 : action.priceUsdc,
    estimatedDurationLabel: action.estimatedDurationLabel,
    inputSummary: `${agent.name} will execute ${action.name} for the buyer dashboard demo workspace.`,
    amountLockedUsdc: mode === "demo" ? 0 : lockedAmount,
    status,
    mode,
    createdAt,
    redirectPath: `/jobs/${sessionId}`,
    sessionToken: `mock-session-token-${sessionId}`,
    socketUrl: `mock://jobs/${sessionId}`,
    resultPayload: null,
  };

  if (status === "completed") {
    session.resultPayload = buildMockJobResultPayload(session);
  }

  return session;
}

function buildSeedMockSessions() {
  const sessions = [
    createSeedMarketplaceSession({
      agentSlug: "northstar-research",
      actionIndex: 0,
      sessionId: "seed-northstar-brief",
      status: "completed",
      mode: "hire",
      hoursAgo: 3,
    }),
    createSeedMarketplaceSession({
      agentSlug: "signal-relay",
      actionIndex: 1,
      sessionId: "seed-signal-relay-routing",
      status: "processing",
      mode: "hire",
      hoursAgo: 6,
    }),
    createSeedMarketplaceSession({
      agentSlug: "harbor-assist",
      actionIndex: 0,
      sessionId: "seed-harbor-support",
      status: "cancelled",
      mode: "hire",
      hoursAgo: 12,
    }),
    createSeedMarketplaceSession({
      agentSlug: "dataflow-ai",
      actionIndex: 2,
      sessionId: "seed-dataflow-model",
      status: "completed",
      mode: "hire",
      hoursAgo: 20,
    }),
    createSeedMarketplaceSession({
      agentSlug: "pattern-office",
      actionIndex: 0,
      sessionId: "seed-pattern-ops",
      status: "completed",
      mode: "hire",
      hoursAgo: 28,
    }),
    createSeedMarketplaceSession({
      agentSlug: "cipher-shield",
      actionIndex: 1,
      sessionId: "seed-cipher-audit",
      status: "processing",
      mode: "hire",
      hoursAgo: 32,
    }),
    createSeedMarketplaceSession({
      agentSlug: "pipeline-pilot",
      actionIndex: 1,
      sessionId: "seed-pipeline-pilot-sync",
      status: "completed",
      mode: "hire",
      hoursAgo: 46,
    }),
    createSeedMarketplaceSession({
      agentSlug: "ledger-lens",
      actionIndex: 1,
      sessionId: "seed-ledger-lens-forecast",
      status: "completed",
      mode: "hire",
      hoursAgo: 58,
    }),
    createSeedMarketplaceSession({
      agentSlug: "brief-engine",
      actionIndex: 0,
      sessionId: "seed-brief-engine-demo",
      status: "completed",
      mode: "demo",
      hoursAgo: 71,
    }),
    createSeedMarketplaceSession({
      agentSlug: "deploy-dock",
      actionIndex: 0,
      sessionId: "seed-deploy-dock-release",
      status: "cancelled",
      mode: "hire",
      hoursAgo: 90,
    }),
    createSeedMarketplaceSession({
      agentSlug: "ops-beacon",
      actionIndex: 1,
      sessionId: "seed-ops-beacon-routing",
      status: "completed",
      mode: "hire",
      hoursAgo: 108,
    }),
    createSeedMarketplaceSession({
      agentSlug: "orbit-scout",
      actionIndex: 0,
      sessionId: "seed-orbit-scout-expansion",
      status: "completed",
      mode: "hire",
      hoursAgo: 132,
    }),
  ];

  return Object.fromEntries(sessions.map((session) => [session.sessionId, session]));
}

const seededMockSessions = buildSeedMockSessions();
let inMemorySessions: Record<string, MockMarketplaceSessionRecord> = seededMockSessions;

function sumCharCodes(value: string) {
  return Array.from(value).reduce((total, char) => total + char.charCodeAt(0), 0);
}

function formatDurationLabel(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  if (minutes < 24 * 60) {
    const hours = Math.round(minutes / 60);
    return hours === 1 ? "1 hour" : `${hours} hours`;
  }

  const days = Math.round(minutes / (24 * 60));
  return days === 1 ? "1 day" : `${days} days`;
}

function buildResponseTimeDistribution(agentSlug: string) {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock response distribution could not find agent '${agentSlug}'.`);
  }

  const jobs = Math.max(agent.jobsCompleted, 1);
  const patterns: Record<number, number[]> = {
    1: [0.46, 0.28, 0.14, 0.08, 0.04],
    2: [0.28, 0.32, 0.2, 0.12, 0.08],
    3: [0.14, 0.24, 0.3, 0.2, 0.12],
    4: [0.06, 0.12, 0.22, 0.33, 0.27],
    5: [0.02, 0.08, 0.15, 0.32, 0.43],
  };
  const averages = [11, 24, 46, 88, 180];
  const labels = ["Under 15 min", "15-30 min", "31-60 min", "1-2 hours", "Over 2 hours"];
  const fractions = patterns[agent.speedRank] ?? patterns[3];

  const rawCounts = fractions.map((fraction) => Math.floor(jobs * fraction));
  rawCounts[rawCounts.length - 1] += jobs - rawCounts.reduce((total, count) => total + count, 0);

  let runningPercentage = 0;

  return labels.map((label, index) => {
    const count = rawCounts[index];
    const percentage =
      index === labels.length - 1
        ? round(Math.max(0, 100 - runningPercentage))
        : round((count / jobs) * 100);

    runningPercentage += index === labels.length - 1 ? 0 : percentage;

    return {
      label,
      count,
      percentage,
      averageMinutes: Math.round(averages[index] * (0.92 + (agent.speedRank - 1) * 0.16)),
    };
  });
}

function buildMockReviews(agentSlug: string, count = 10) {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock reviews could not find agent '${agentSlug}'.`);
  }

  const seed = sumCharCodes(agent.slug);

  return Array.from({ length: count }, (_, index) => {
    const tag = agent.tags[index % agent.tags.length].toLowerCase();
    const reviewerName = reviewerNames[(seed + index) % reviewerNames.length];
    const company = companyNames[(seed * 2 + index) % companyNames.length];
    const rating = (seed + index) % 6 === 0 && agent.rating < 4.9 ? 4 : 5;

    return {
      id: `${agent.slug}-review-${index + 1}`,
      reviewerName,
      company,
      rating,
      comment: commentTemplates[index % commentTemplates.length]
        .replace("{tag}", tag)
        .replace("{agent}", agent.name),
      jobTitle: `${agent.tags[index % agent.tags.length]} delivery sprint`,
      createdAt: new Date(Date.now() - (index + 1) * 1000 * 60 * 60 * 24 * 7).toISOString(),
    };
  });
}

function buildMockMarketplaceStats(): MarketplaceStats {
  return {
    totalAgents: marketplaceAgents.length,
    totalVolume: marketplaceAgents.reduce(
      (total, agent) => total + Math.round(agent.startingPriceUsdc * agent.jobsCompleted * 1.8),
      0
    ),
    totalJobs: marketplaceAgents.reduce((total, agent) => total + agent.jobsCompleted, 0),
  };
}

function buildMockMarketplaceInsights(agentSlug: string): MarketplaceAgentInsightsResponse {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock insights could not find agent '${agentSlug}'.`);
  }

  const totalEarned = Math.round(agent.startingPriceUsdc * agent.jobsCompleted * 1.86);
  const avgJobValue = round(totalEarned / Math.max(agent.jobsCompleted, 1), 2);
  const distribution = buildResponseTimeDistribution(agent.slug);
  const avgDeliveryMinutes = Math.round(
    distribution.reduce((total, item) => total + item.count * item.averageMinutes, 0) /
      Math.max(
        distribution.reduce((total, item) => total + item.count, 0),
        1
      )
  );
  const repeatBuyerRate = round(Math.min(92, 54 + agent.reviewCount * 0.14));
  const onTimeRate = round(Math.min(99.5, agent.successRate + 0.7));
  const payoutCompletionRate = round(Math.min(99.8, 97 + (agent.successRate - 95) * 0.5));

  return {
    agentSlug: agent.slug,
    agentName: agent.name,
    generatedAt: new Date().toISOString(),
    stats: {
      successRate: agent.successRate,
      totalJobs: agent.jobsCompleted,
      totalEarned,
      avgJobValue,
      avgDeliveryMinutes,
      avgDeliveryLabel: formatDurationLabel(avgDeliveryMinutes),
      repeatBuyerRate,
      onTimeRate,
      payoutCompletionRate,
      metrics: [
        {
          label: "On-time delivery",
          value: `${onTimeRate.toFixed(1)}%`,
          detail: "Completed inside the quoted delivery window.",
        },
        {
          label: "Repeat buyers",
          value: `${repeatBuyerRate.toFixed(1)}%`,
          detail: "Returning buyers and coordinating agents using this specialist again.",
        },
        {
          label: "Avg contract value",
          value: `$${avgJobValue.toLocaleString("en-US", { maximumFractionDigits: 0 })}`,
          detail: "Average settled spend across recent marketplace jobs.",
        },
        {
          label: "Payout completion",
          value: `${payoutCompletionRate.toFixed(1)}%`,
          detail: "Successful escrow-to-settlement completion for delivered jobs.",
        },
      ],
      responseTimeDistribution: distribution,
    },
    reviews: buildMockReviews(agent.slug, 10),
  };
}

function buildRevenueSeries(
  agentSlug: string,
  range: AnalyticsRange,
  totalEarned: number,
  totalJobs: number
) {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock revenue series could not find agent '${agentSlug}'.`);
  }

  const base = sumCharCodes(agent.slug);

  if (range === "7d") {
    const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const shares = [0.09, 0.13, 0.11, 0.15, 0.18, 0.16, 0.18];
    return labels.map((label, index) => ({
      label,
      amount: Math.round(totalEarned * shares[index]),
      jobs: Math.max(1, Math.round(totalJobs * shares[index])),
    }));
  }

  if (range === "30d") {
    const labels = ["Jan 1-5", "Jan 6-10", "Jan 11-15", "Jan 16-20", "Jan 21-25", "Jan 26-30"];
    const shares = [0.11, 0.15, 0.17, 0.14, 0.2, 0.23];
    return labels.map((label, index) => ({
      label,
      amount: Math.round(totalEarned * shares[index]),
      jobs: Math.max(1, Math.round(totalJobs * shares[index])),
    }));
  }

  if (range === "90d") {
    const labels = ["Week 1-2", "Week 3-4", "Week 5-6", "Week 7-8", "Week 9-10", "Week 11-12"];
    const shares = [0.1, 0.12, 0.16, 0.18, 0.2, 0.24];
    return labels.map((label, index) => ({
      label,
      amount: Math.round(totalEarned * shares[index]),
      jobs: Math.max(1, Math.round(totalJobs * shares[index])),
    }));
  }

  return ["Jan", "Feb", "Mar", "Apr", "May", "Jun"].map((label, index) => {
    const share = 0.1 + (((base + index * 7) % 9) / 100 + index * 0.03);
    return {
      label,
      amount: Math.round(totalEarned * Math.min(share, 0.24)),
      jobs: Math.max(1, Math.round(totalJobs * Math.min(share, 0.24))),
    };
  });
}

function buildMockAgentAnalytics(agentSlug: string, range: AnalyticsRange): AgentAnalyticsResponse {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock analytics could not find agent '${agentSlug}'.`);
  }

  const rangeShare = {
    "7d": 0.18,
    "30d": 0.42,
    "90d": 0.74,
    all: 1,
  }[range];

  const totalJobs = Math.max(1, Math.round(agent.jobsCompleted * rangeShare));
  const totalEarned = Math.round(totalJobs * agent.startingPriceUsdc * 1.92);
  const reviews = buildMockReviews(agent.slug, 5);
  const ownerName = ownerNames[sumCharCodes(agent.slug) % ownerNames.length];
  const counts = agent.actions.map((action, index) =>
    Math.max(1, totalJobs - index * Math.ceil(totalJobs / 4))
  );
  const countSum = counts.reduce((total, count) => total + count, 0);

  const actionBreakdown = agent.actions.map((action, index) => {
    const count = counts[index];
    const percentage = round((count / countSum) * 100);
    return {
      action: action.name,
      count,
      percentage,
      earned: Math.round(totalEarned * (percentage / 100)),
    };
  });

  return {
    agentId: agent.slug,
    agentName: agent.name,
    ownerName,
    range,
    generatedAt: new Date().toISOString(),
    summary: {
      totalJobs,
      totalEarned,
      successRate: agent.successRate,
      avgJobValue: round(totalEarned / totalJobs, 2),
    },
    revenueSeries: buildRevenueSeries(agent.slug, range, totalEarned, totalJobs),
    actionBreakdown,
    reviews,
    responseTimeDistribution: buildResponseTimeDistribution(agent.slug),
  };
}

function parsePositiveInteger(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function toBuyerDashboardStatus(status: MarketplaceSessionStatus): {
  status: BuyerDashboardJobStatus;
  statusLabel: "Done" | "Running" | "Failed";
} {
  if (status === "completed") {
    return {
      status: "done",
      statusLabel: "Done",
    };
  }

  if (status === "cancelled" || status === "closed") {
    return {
      status: "failed",
      statusLabel: "Failed",
    };
  }

  return {
    status: "running",
    statusLabel: "Running",
  };
}

function listRecentBuyerSessions(limit = 10) {
  return Object.values(readMockSessions())
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime())
    .slice(0, limit);
}

function buildMockBuyerDashboardSummary(limit = 10): BuyerDashboardSummaryResponse {
  const sessions = Object.values(readMockSessions());
  const recentJobs = listRecentBuyerSessions(limit).map((session) => {
    const { status, statusLabel } = toBuyerDashboardStatus(session.status);

    return {
      sessionId: session.sessionId,
      agentSlug: session.agentSlug,
      agentName: session.agentName,
      actionName: session.actionName,
      status,
      statusLabel,
      amountChargedUsdc: session.priceUsdc,
      createdAt: session.createdAt,
      mode: session.mode,
    };
  });

  const totalSpentUsdc = sessions
    .filter((session) => session.mode === "hire")
    .reduce((total, session) => total + session.priceUsdc, 0);

  return {
    generatedAt: new Date().toISOString(),
    stats: {
      totalJobs: sessions.length,
      totalSpentUsdc,
      savedAgentsCount: 8,
    },
    recentJobs,
  };
}

function buildMockCircleWalletBalance(): CircleWalletBalanceResponse {
  const sessions = Object.values(readMockSessions());
  const pendingBalanceUsdc = sessions
    .filter((session) => session.status === "awaiting_payment")
    .reduce((total, session) => total + session.priceUsdc, 0);
  const lockedInEscrowUsdc = sessions
    .filter((session) => session.status === "processing")
    .reduce((total, session) => total + Math.max(session.amountLockedUsdc, session.priceUsdc), 0);
  const baseAvailable = 18420;
  const activityOffset = (Math.floor(Date.now() / 15000) % 5) * 18;
  const spentOffset = sessions
    .filter((session) => session.mode === "hire")
    .reduce((total, session) => total + session.priceUsdc * 0.14, 0);

  return {
    provider: "Circle",
    walletId: "circle-wallet-demo-primary",
    walletAddress: "0xB0YER0000000000000000000000000000ABCD",
    availableBalanceUsdc: round(Math.max(6200, baseAvailable - spentOffset + activityOffset), 2),
    pendingBalanceUsdc,
    lockedInEscrowUsdc,
    lastUpdatedAt: new Date().toISOString(),
    syncStatus: "live",
  };
}

function buildMockBuyerRecommendedAgents(limit = 6): BuyerRecommendedAgent[] {
  const reasons = [
    "Strong fit for buyers who keep hiring across research and strategy workflows.",
    "Fastest handoff for automation-heavy jobs that need immediate orchestration support.",
    "High repeat-buyer rate for support coverage and ongoing operating tasks.",
    "Useful when jobs require analytics output plus an executive-ready narrative.",
    "Trusted for security-sensitive work before larger spend gets committed.",
    "Reliable for finance and reporting workloads that need USDC-aware delivery context.",
  ];

  const recommendedSlugs = [
    "northstar-research",
    "signal-relay",
    "harbor-assist",
    "dataflow-ai",
    "cipher-shield",
    "ledger-lens",
  ];

  return recommendedSlugs
    .map((slug, index) => {
      const agent = marketplaceAgents.find((item) => item.slug === slug);
      if (!agent) {
        return null;
      }

      return {
        id: agent.id,
        slug: agent.slug,
        name: agent.name,
        description: agent.description,
        rating: agent.rating,
        reviewCount: agent.reviewCount,
        startingPriceUsdc: agent.startingPriceUsdc,
        speedLabel: agent.speedLabel,
        tags: agent.tags,
        avatar: agent.avatar,
        reason: reasons[index] ?? reasons[reasons.length - 1],
      };
    })
    .filter((agent): agent is BuyerRecommendedAgent => Boolean(agent))
    .slice(0, limit);
}

function parsePath(path: string) {
  return new URL(path, "http://mock.local");
}

export function supportsMockApi(path: string) {
  const pathname = parsePath(path).pathname;

  return (
    pathname === "/circle/wallets/primary/balance" ||
    pathname === "/buyer/dashboard/summary" ||
    pathname === "/buyer/recommended-agents" ||
    pathname === "/marketplace/stats" ||
    /^\/marketplace\/agents\/[^/]+\/insights$/.test(pathname) ||
    /^\/marketplace\/agents\/[^/]+\/sessions$/.test(pathname) ||
    /^\/marketplace\/sessions\/[^/]+$/.test(pathname) ||
    /^\/agents\/[^/]+\/analytics$/.test(pathname)
  );
}

export async function mockApiFetch<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
  const url = parsePath(path);
  const pathname = url.pathname;
  const method = (config?.method ?? "get").toLowerCase();

  if (pathname === "/circle/wallets/primary/balance" && method === "get") {
    return buildMockCircleWalletBalance() as T;
  }

  if (pathname === "/buyer/dashboard/summary" && method === "get") {
    const limit = parsePositiveInteger(url.searchParams.get("limit"), 10);
    return buildMockBuyerDashboardSummary(limit) as T;
  }

  if (pathname === "/buyer/recommended-agents" && method === "get") {
    const limit = parsePositiveInteger(url.searchParams.get("limit"), 6);
    return buildMockBuyerRecommendedAgents(limit) as T;
  }

  if (pathname === "/marketplace/stats" && method === "get") {
    return buildMockMarketplaceStats() as T;
  }

  const insightsMatch = pathname.match(/^\/marketplace\/agents\/([^/]+)\/insights$/);
  if (insightsMatch && method === "get") {
    return buildMockMarketplaceInsights(decodeURIComponent(insightsMatch[1])) as T;
  }

  const createSessionMatch = pathname.match(/^\/marketplace\/agents\/([^/]+)\/sessions$/);
  if (createSessionMatch && method === "post") {
    return createMockMarketplaceSession(
      decodeURIComponent(createSessionMatch[1]),
      config?.data as MarketplaceSessionCreateRequest
    ) as T;
  }

  const getSessionMatch = pathname.match(/^\/marketplace\/sessions\/([^/]+)$/);
  if (getSessionMatch && method === "get") {
    const session = getMockMarketplaceSession(decodeURIComponent(getSessionMatch[1]));
    if (!session) {
      throw new Error(`Mock session '${getSessionMatch[1]}' was not found.`);
    }
    return session as T;
  }

  const analyticsMatch = pathname.match(/^\/agents\/([^/]+)\/analytics$/);
  if (analyticsMatch && method === "get") {
    const rangeParam = url.searchParams.get("range");
    const range: AnalyticsRange =
      rangeParam === "7d" || rangeParam === "30d" || rangeParam === "90d" || rangeParam === "all"
        ? rangeParam
        : "30d";

    return buildMockAgentAnalytics(decodeURIComponent(analyticsMatch[1]), range) as T;
  }

  throw new Error(`No mock API route matched '${method.toUpperCase()} ${path}'.`);
}

export function buildMockJobResultPayload(session: MockMarketplaceSessionRecord) {
  return {
    action: session.actionName,
    agentName: session.agentName,
    inputSummary: session.inputSummary,
    escrowLockedUsdc: session.amountLockedUsdc,
    deliverables: [
      {
        label: "Execution summary",
        content: `${session.agentName} completed ${session.actionName} and returned a structured package for the next workflow step.`,
      },
      {
        label: "Recommended next step",
        content: "Review the output, trigger downstream execution, or close the session.",
      },
    ],
    resultText: `${session.actionName} completed successfully for ${session.agentName}.`,
    completedAt: new Date().toISOString(),
  };
}

export function listMockMarketplaceAgents() {
  return marketplaceAgentDetails;
}
