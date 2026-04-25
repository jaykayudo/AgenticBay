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

type MarketplaceSearchResult = {
  agentSlug: string;
  agentName: string;
  description: string;
  rating: number;
  jobsCompleted: number;
  startingPriceUsdc: number;
  matchPercentage: number;
  reason: string;
  primaryAction: MarketplaceSessionCreateRequest;
  avatar: {
    label: string;
    bg: string;
    fg: string;
  };
};

type MarketplaceSearchResponse = {
  query: string;
  generatedAt: string;
  resultCount: number;
  orchestratorSuggestion: string;
  bestMatch: MarketplaceSearchResult | null;
  results: MarketplaceSearchResult[];
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

type WalletActivityTab = "transactions" | "escrow" | "earnings";

type WalletTransactionRecord = {
  id: string;
  direction: "inbound" | "outbound";
  type: "deposit" | "withdrawal" | "escrow_lock" | "escrow_release" | "earning" | "refund";
  label: string;
  amountUsdc: number;
  timestamp: string;
  status: "completed" | "pending" | "locked";
  jobId?: string;
  jobTitle?: string;
  agentName?: string;
  counterparty?: string;
};

type WalletEscrowRecord = {
  id: string;
  jobId: string;
  jobTitle: string;
  agentName: string;
  amountLockedUsdc: number;
  status: "processing" | "awaiting_payment" | "review";
  lockedAt: string;
};

type WalletEarningRecord = {
  id: string;
  agentSlug: string;
  agentName: string;
  sourceJobId: string;
  sourceJobTitle: string;
  amountUsdc: number;
  timestamp: string;
  status: "paid" | "pending";
};

type WalletActivityResponse = {
  tab: WalletActivityTab;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  items: Array<WalletTransactionRecord | WalletEscrowRecord | WalletEarningRecord>;
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

type BuyerJobHistoryStatus = "active" | "completed" | "failed";

type BuyerJobHistoryRecord = {
  sessionId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  inputSummary: string;
  status: BuyerJobHistoryStatus;
  statusLabel: "Active" | "Completed" | "Failed";
  refundStatus: "not_applicable" | "refunded" | "pending_refund";
  amountChargedUsdc: number;
  amountLockedUsdc: number;
  durationLabel: string;
  createdAt: string;
  redirectPath: string;
  mode: "hire" | "demo";
  rehirePayload: MarketplaceSessionCreateRequest;
};

type BuyerJobHistoryResponse = {
  generatedAt: string;
  jobs: BuyerJobHistoryRecord[];
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

type UserSettingsProfile = {
  username: string;
  email: string;
  role: "buyer" | "agent_owner" | "admin";
  avatarInitials: string;
  avatarColor: string;
};

type UserSettingsApiKey = {
  id: string;
  environment: "Development" | "Production";
  prefix: string;
  createdAt: string;
  lastUsedAt: string | null;
};

type UserSettingsNotification = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
};

type UserSettingsResponse = {
  profile: UserSettingsProfile;
  apiKeys: UserSettingsApiKey[];
  notifications: UserSettingsNotification[];
};

type UserSettingsProfileUpdatePayload = {
  username: string;
  email: string;
};

type UserSettingsApiKeyCreatePayload = {
  environment: UserSettingsApiKey["environment"];
};

type UserSettingsApiKeyCreateResponse = {
  key: UserSettingsApiKey;
  fullKey: string;
};

type UserSettingsNotificationUpdatePayload = {
  enabled: boolean;
};

const MOCK_SESSIONS_STORAGE_KEY = "agenticbay.mock.marketplace.sessions";
const MOCK_OWNER_ONBOARDING_DRAFT_KEY = "agenticbay.mock.owner.onboarding.draft";
const MOCK_USER_SETTINGS_STORAGE_KEY = "agenticbay.mock.user.settings";

type OwnerOnboardingAction = {
  id: string;
  name: string;
  priceUsdc: string;
};

type OwnerOnboardingPayload = {
  agentName: string;
  description: string;
  category: string;
  tags: string[];
  repositoryUrl: string;
  externalEndpointUrl: string;
  actions: OwnerOnboardingAction[];
};

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

function readOwnerOnboardingDraft(): OwnerOnboardingPayload | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(MOCK_OWNER_ONBOARDING_DRAFT_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as OwnerOnboardingPayload;
  } catch {
    window.localStorage.removeItem(MOCK_OWNER_ONBOARDING_DRAFT_KEY);
    return null;
  }
}

function buildSeedUserSettings(): UserSettingsResponse {
  return {
    profile: {
      username: "maya-buyer",
      email: "maya@agenticbay.dev",
      role: "agent_owner",
      avatarInitials: "MB",
      avatarColor: "bg-[var(--primary)]",
    },
    apiKeys: [
      {
        id: "key-live-primary",
        environment: "Production",
        prefix: "agb_live_7Hk2",
        createdAt: hoursAgoIso(24 * 18),
        lastUsedAt: hoursAgoIso(3),
      },
      {
        id: "key-dev-sandbox",
        environment: "Development",
        prefix: "agb_test_Qm91",
        createdAt: hoursAgoIso(24 * 41),
        lastUsedAt: hoursAgoIso(28),
      },
    ],
    notifications: [
      {
        id: "job_updates",
        label: "Job updates",
        description: "Status changes, completed runs, failures, and refund events.",
        enabled: true,
      },
      {
        id: "wallet_activity",
        label: "Wallet activity",
        description: "Deposits, withdrawals, escrow locks, and Circle sync alerts.",
        enabled: true,
      },
      {
        id: "agent_reviews",
        label: "Agent reviews",
        description: "New buyer reviews and quality signals for owned agents.",
        enabled: true,
      },
      {
        id: "product_digest",
        label: "Product digest",
        description: "Occasional marketplace recommendations and feature notes.",
        enabled: false,
      },
    ],
  };
}

function readUserSettings(): UserSettingsResponse {
  const seed = buildSeedUserSettings();

  if (!isBrowser()) {
    return seed;
  }

  const raw = window.localStorage.getItem(MOCK_USER_SETTINGS_STORAGE_KEY);
  if (!raw) {
    return seed;
  }

  try {
    const parsed = JSON.parse(raw) as UserSettingsResponse;
    return {
      profile: { ...seed.profile, ...parsed.profile },
      apiKeys: parsed.apiKeys ?? seed.apiKeys,
      notifications: seed.notifications.map((notification) => {
        const saved = parsed.notifications?.find((item) => item.id === notification.id);
        return saved ? { ...notification, enabled: saved.enabled } : notification;
      }),
    };
  } catch {
    window.localStorage.removeItem(MOCK_USER_SETTINGS_STORAGE_KEY);
    return seed;
  }
}

function writeUserSettings(settings: UserSettingsResponse) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(MOCK_USER_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}

function updateUserSettingsProfile(payload: UserSettingsProfileUpdatePayload): UserSettingsProfile {
  const username = payload.username.trim();
  const email = payload.email.trim().toLowerCase();
  const takenUsernames = ["admin", "agenticbay", "support", "northstar"];

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error("Enter a valid email address.");
  }

  if (!/^[a-z0-9][a-z0-9-]{2,29}$/i.test(username)) {
    throw new Error("Username must be 3-30 characters using letters, numbers, or hyphens.");
  }

  if (takenUsernames.includes(username.toLowerCase())) {
    throw new Error("That username is already taken.");
  }

  const settings = readUserSettings();
  const nextProfile = {
    ...settings.profile,
    username,
    email,
    avatarInitials: username
      .split("-")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase(),
  };

  writeUserSettings({
    ...settings,
    profile: nextProfile,
  });

  return nextProfile;
}

function createUserSettingsApiKey(
  payload: UserSettingsApiKeyCreatePayload
): UserSettingsApiKeyCreateResponse {
  const settings = readUserSettings();
  const isProduction = payload.environment === "Production";
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}${Math.random().toString(36).slice(2)}`;
  const prefix = `${isProduction ? "agb_live" : "agb_test"}_${random.slice(0, 4)}`;
  const key: UserSettingsApiKey = {
    id: `key-${random.slice(0, 12)}`,
    environment: payload.environment,
    prefix,
    createdAt: new Date().toISOString(),
    lastUsedAt: null,
  };

  writeUserSettings({
    ...settings,
    apiKeys: [key, ...settings.apiKeys],
  });

  return {
    key,
    fullKey: `${prefix}_${random.slice(4)}${random}`,
  };
}

function revokeUserSettingsApiKey(keyId: string) {
  const settings = readUserSettings();
  const apiKeys = settings.apiKeys.filter((key) => key.id !== keyId);

  writeUserSettings({
    ...settings,
    apiKeys,
  });

  return {
    revoked: settings.apiKeys.length !== apiKeys.length,
  };
}

function updateUserSettingsNotification(
  notificationId: string,
  payload: UserSettingsNotificationUpdatePayload
) {
  const settings = readUserSettings();
  const notifications = settings.notifications.map((notification) =>
    notification.id === notificationId
      ? { ...notification, enabled: payload.enabled }
      : notification
  );

  writeUserSettings({
    ...settings,
    notifications,
  });

  return notifications.find((notification) => notification.id === notificationId) ?? null;
}

function writeOwnerOnboardingDraft(payload: OwnerOnboardingPayload) {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(MOCK_OWNER_ONBOARDING_DRAFT_KEY, JSON.stringify(payload));
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

function buildResponseTimeDistribution(agentSlug: string, totalJobsOverride?: number) {
  const agent = getMarketplaceAgentDetail(agentSlug);
  if (!agent) {
    throw new Error(`Mock response distribution could not find agent '${agentSlug}'.`);
  }

  const jobs = Math.max(totalJobsOverride ?? agent.jobsCompleted, 1);
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

function tokenizeSearchQuery(query: string) {
  const aliases: Record<string, string[]> = {
    scrape: ["research", "data", "development", "automation"],
    scraping: ["research", "data", "development", "automation"],
    website: ["content", "development", "research"],
    web: ["content", "development", "research"],
    dashboard: ["data", "analytics", "reporting"],
    automate: ["automation", "workflow", "ops"],
    support: ["support", "inbox", "customer"],
    design: ["design", "creative", "component"],
    audit: ["security", "review", "compliance"],
    code: ["development", "testing", "bugfix"],
  };

  return query
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
    .flatMap((token) => [token, ...(aliases[token] ?? [])]);
}

function scoreSearchAgent(agentSlug: string, query: string) {
  const detail = getMarketplaceAgentDetail(agentSlug);
  if (!detail) {
    return null;
  }

  const tokens = tokenizeSearchQuery(query);
  const haystack = [
    detail.name,
    detail.description,
    detail.headline,
    detail.tags.join(" "),
    detail.categories.join(" "),
    detail.actions.map((action) => `${action.name} ${action.description}`).join(" "),
  ]
    .join(" ")
    .toLowerCase();

  const hits = tokens.filter((token) => haystack.includes(token));
  const uniqueHits = new Set(hits);
  const lexicalScore = uniqueHits.size / Math.max(new Set(tokens).size, 1);
  const qualityScore = detail.rating / 5;
  const completionScore = Math.min(detail.jobsCompleted / 420, 1);
  const speedScore = (6 - detail.speedRank) / 5;
  const rawScore = lexicalScore * 62 + qualityScore * 16 + completionScore * 12 + speedScore * 10;
  const matchPercentage = Math.min(99, Math.max(0, Math.round(rawScore)));

  return {
    detail,
    matchPercentage,
    hitCount: uniqueHits.size,
  };
}

function buildMarketplaceSearchResult(
  agentSlug: string,
  query: string
): MarketplaceSearchResult | null {
  const scored = scoreSearchAgent(agentSlug, query);
  if (!scored || scored.matchPercentage < 28) {
    return null;
  }

  const { detail, matchPercentage } = scored;
  const primaryAction = detail.actions[0];

  return {
    agentSlug: detail.slug,
    agentName: detail.name,
    description: detail.description,
    rating: detail.rating,
    jobsCompleted: detail.jobsCompleted,
    startingPriceUsdc: detail.startingPriceUsdc,
    matchPercentage,
    reason: `${detail.name} matches this request through ${detail.tags.slice(0, 2).join(" and ").toLowerCase()} with ${detail.speedLabel.toLowerCase()} delivery.`,
    primaryAction: {
      actionId: primaryAction.id,
      actionName: primaryAction.name,
      priceUsdc: primaryAction.priceUsdc,
      estimatedDurationLabel: primaryAction.estimatedDurationLabel,
      inputSummary: `${detail.name} will execute ${primaryAction.name} for: ${query}`,
      mode: "hire",
    },
    avatar: detail.avatar,
  };
}

function buildMockMarketplaceSearch(query: string): MarketplaceSearchResponse {
  const normalizedQuery = query.trim();
  const results = marketplaceAgents
    .map((agent) => buildMarketplaceSearchResult(agent.slug, normalizedQuery))
    .filter((result): result is MarketplaceSearchResult => Boolean(result))
    .sort(
      (left, right) =>
        right.matchPercentage - left.matchPercentage ||
        right.rating - left.rating ||
        right.jobsCompleted - left.jobsCompleted
    )
    .slice(0, 12);

  const bestMatch = results[0] ?? null;
  const orchestratorSuggestion = bestMatch
    ? `I would start with ${bestMatch.agentName}. It is the strongest match for "${normalizedQuery}" at ${bestMatch.matchPercentage}% because its capabilities overlap the request and it has ${bestMatch.jobsCompleted.toLocaleString("en-US")} completed jobs with a ${bestMatch.rating.toFixed(1)} rating.`
    : `I could not find a strong specialist match for "${normalizedQuery}". Try a more specific service request, such as "research competitors", "automate CRM routing", or "audit smart contract".`;

  return {
    query: normalizedQuery,
    generatedAt: new Date().toISOString(),
    resultCount: results.length,
    orchestratorSuggestion,
    bestMatch,
    results,
  };
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
  let runningPercentage = 0;

  const actionBreakdown = agent.actions.map((action, index) => {
    const count = counts[index];
    const percentage =
      index === agent.actions.length - 1
        ? round(100 - runningPercentage)
        : round((count / countSum) * 100);
    runningPercentage += index === agent.actions.length - 1 ? 0 : percentage;

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
    responseTimeDistribution: buildResponseTimeDistribution(agent.slug, totalJobs),
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

function toBuyerJobHistoryStatus(status: MarketplaceSessionStatus): {
  status: BuyerJobHistoryStatus;
  statusLabel: "Active" | "Completed" | "Failed";
  refundStatus: "not_applicable" | "refunded" | "pending_refund";
} {
  if (status === "completed") {
    return {
      status: "completed",
      statusLabel: "Completed",
      refundStatus: "not_applicable",
    };
  }

  if (status === "cancelled" || status === "closed") {
    return {
      status: "failed",
      statusLabel: "Failed",
      refundStatus: status === "cancelled" ? "refunded" : "pending_refund",
    };
  }

  return {
    status: "active",
    statusLabel: "Active",
    refundStatus: "not_applicable",
  };
}

function buildMockBuyerJobHistory(): BuyerJobHistoryResponse {
  const jobs = Object.values(readMockSessions())
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime())
    .map((session) => {
      const status = toBuyerJobHistoryStatus(session.status);

      return {
        sessionId: session.sessionId,
        agentSlug: session.agentSlug,
        agentName: session.agentName,
        actionId: session.actionId,
        actionName: session.actionName,
        inputSummary: session.inputSummary,
        ...status,
        amountChargedUsdc: session.priceUsdc,
        amountLockedUsdc: session.amountLockedUsdc,
        durationLabel: session.estimatedDurationLabel,
        createdAt: session.createdAt,
        redirectPath: session.redirectPath,
        mode: session.mode,
        rehirePayload: {
          actionId: session.actionId,
          actionName: session.actionName,
          priceUsdc: session.priceUsdc,
          estimatedDurationLabel: session.estimatedDurationLabel,
          inputSummary: session.inputSummary,
          mode: session.mode,
        },
      };
    });

  return {
    generatedAt: new Date().toISOString(),
    jobs,
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

function paginateWalletItems<T>(items: T[], page: number, pageSize: number) {
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const currentPage = Math.min(Math.max(page, 1), totalPages);

  return {
    page: currentPage,
    pageSize,
    totalItems,
    totalPages,
    items: items.slice((currentPage - 1) * pageSize, currentPage * pageSize),
  };
}

function hoursAgoIso(hours: number) {
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
}

function buildMockWalletTransactions(): WalletTransactionRecord[] {
  const sessionTransactions = Object.values(readMockSessions()).flatMap((session) => {
    if (session.mode === "demo" || session.priceUsdc <= 0) {
      return [];
    }

    const locked =
      session.status === "processing" ||
      session.status === "completed" ||
      session.status === "cancelled";
    const completed = session.status === "completed";
    const cancelled = session.status === "cancelled";

    return [
      ...(locked
        ? [
            {
              id: `${session.sessionId}-lock`,
              direction: "outbound" as const,
              type: "escrow_lock" as const,
              label: `Escrow locked for ${session.actionName}`,
              amountUsdc: session.priceUsdc,
              timestamp: session.createdAt,
              status: "locked" as const,
              jobId: session.sessionId,
              jobTitle: session.actionName,
              agentName: session.agentName,
            },
          ]
        : []),
      ...(completed
        ? [
            {
              id: `${session.sessionId}-release`,
              direction: "outbound" as const,
              type: "escrow_release" as const,
              label: `Escrow released to ${session.agentName}`,
              amountUsdc: session.priceUsdc,
              timestamp: hoursAgoIso(
                Math.max(
                  1,
                  Math.floor((Date.now() - new Date(session.createdAt).getTime()) / 36e5) - 1
                )
              ),
              status: "completed" as const,
              jobId: session.sessionId,
              jobTitle: session.actionName,
              agentName: session.agentName,
            },
          ]
        : []),
      ...(cancelled
        ? [
            {
              id: `${session.sessionId}-refund`,
              direction: "inbound" as const,
              type: "refund" as const,
              label: `Escrow refund from ${session.agentName}`,
              amountUsdc: session.priceUsdc,
              timestamp: hoursAgoIso(
                Math.max(
                  1,
                  Math.floor((Date.now() - new Date(session.createdAt).getTime()) / 36e5) - 2
                )
              ),
              status: "completed" as const,
              jobId: session.sessionId,
              jobTitle: session.actionName,
              agentName: session.agentName,
            },
          ]
        : []),
    ];
  });

  const manualTransactions: WalletTransactionRecord[] = [
    {
      id: "wallet-deposit-seed-01",
      direction: "inbound",
      type: "deposit",
      label: "Circle USDC deposit",
      amountUsdc: 8500,
      timestamp: hoursAgoIso(2),
      status: "completed",
      counterparty: "Circle wallet rail",
    },
    {
      id: "wallet-withdraw-seed-01",
      direction: "outbound",
      type: "withdrawal",
      label: "Withdrawal to external wallet",
      amountUsdc: 1250,
      timestamp: hoursAgoIso(18),
      status: "completed",
      counterparty: "0x71C4...A901",
    },
    {
      id: "wallet-deposit-seed-02",
      direction: "inbound",
      type: "deposit",
      label: "Circle USDC deposit",
      amountUsdc: 4200,
      timestamp: hoursAgoIso(76),
      status: "completed",
      counterparty: "Circle wallet rail",
    },
  ];

  return [...manualTransactions, ...sessionTransactions].sort(
    (left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime()
  );
}

function buildMockWalletEscrow(): WalletEscrowRecord[] {
  return Object.values(readMockSessions())
    .filter(
      (session) =>
        session.mode === "hire" &&
        (session.status === "processing" || session.status === "awaiting_payment") &&
        Math.max(session.amountLockedUsdc, session.priceUsdc) > 0
    )
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime())
    .map((session) => ({
      id: `${session.sessionId}-escrow`,
      jobId: session.sessionId,
      jobTitle: session.actionName,
      agentName: session.agentName,
      amountLockedUsdc: Math.max(session.amountLockedUsdc, session.priceUsdc),
      status: session.status === "awaiting_payment" ? "awaiting_payment" : "processing",
      lockedAt: session.createdAt,
    }));
}

function buildMockWalletEarnings(): WalletEarningRecord[] {
  return Object.values(readMockSessions())
    .filter((session) => session.mode === "hire" && session.status === "completed")
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime())
    .map((session, index) => ({
      id: `${session.sessionId}-earning`,
      agentSlug: session.agentSlug,
      agentName: session.agentName,
      sourceJobId: session.sessionId,
      sourceJobTitle: session.actionName,
      amountUsdc: round(session.priceUsdc * 0.86, 2),
      timestamp: hoursAgoIso(
        Math.max(1, Math.floor((Date.now() - new Date(session.createdAt).getTime()) / 36e5) - 1)
      ),
      status: index % 4 === 0 ? "pending" : "paid",
    }));
}

function buildMockWalletActivity(
  tab: WalletActivityTab,
  page: number,
  pageSize: number
): WalletActivityResponse {
  const source: WalletActivityResponse["items"] =
    tab === "escrow"
      ? buildMockWalletEscrow()
      : tab === "earnings"
        ? buildMockWalletEarnings()
        : buildMockWalletTransactions();
  const paginated = paginateWalletItems(source, page, pageSize);

  return {
    tab,
    ...paginated,
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
    pathname === "/owner/agents/onboarding/draft" ||
    pathname === "/owner/agents/onboarding/check-endpoints" ||
    pathname === "/owner/agents/onboarding/submit" ||
    pathname === "/circle/wallets/primary/balance" ||
    pathname === "/circle/wallets/primary/activity" ||
    pathname === "/buyer/dashboard/summary" ||
    pathname === "/buyer/jobs/history" ||
    pathname === "/buyer/recommended-agents" ||
    pathname === "/user/settings" ||
    pathname === "/user/settings/profile" ||
    pathname === "/user/settings/api-keys" ||
    /^\/user\/settings\/api-keys\/[^/]+$/.test(pathname) ||
    /^\/user\/settings\/notifications\/[^/]+$/.test(pathname) ||
    pathname === "/marketplace/search" ||
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

  if (pathname === "/owner/agents/onboarding/draft") {
    if (method === "get") {
      return {
        draft: readOwnerOnboardingDraft(),
      } as T;
    }
    if (method === "post" || method === "put" || method === "patch") {
      const payload = config?.data as OwnerOnboardingPayload;
      writeOwnerOnboardingDraft(payload);
      return {
        savedAt: new Date().toISOString(),
      } as T;
    }
  }

  if (pathname === "/owner/agents/onboarding/check-endpoints" && method === "post") {
    const payload = config?.data as OwnerOnboardingPayload;
    const endpoint = payload.externalEndpointUrl.trim();
    const hasEndpoint = endpoint.length > 0;
    const failingEndpoint = hasEndpoint && endpoint.includes("fail");
    const invalidScheme = hasEndpoint && !/^https?:\/\//i.test(endpoint);

    const results = [
      {
        path: "GET /capabilities",
        ok: !invalidScheme && !failingEndpoint,
        message: invalidScheme
          ? "invalid endpoint URL"
          : failingEndpoint
            ? "request returned 500"
            : "ok",
      },
      {
        path: "POST /connect",
        ok: !invalidScheme && !failingEndpoint,
        message: invalidScheme
          ? "invalid endpoint URL"
          : failingEndpoint
            ? "request timeout"
            : "ok",
      },
      {
        path: "WS /ws/service/{session_id}",
        ok: !invalidScheme && !failingEndpoint,
        message: invalidScheme
          ? "invalid endpoint URL"
          : failingEndpoint
            ? "websocket handshake failed"
            : "ok",
      },
    ];

    return { results } as T;
  }

  if (pathname === "/owner/agents/onboarding/submit" && method === "post") {
    const payload = config?.data as OwnerOnboardingPayload;
    writeOwnerOnboardingDraft(payload);
    return {
      status: "pending_review",
      notice:
        "Submission received. Your listing is now pending manual source review and endpoint verification.",
    } as T;
  }

  if (pathname === "/circle/wallets/primary/balance" && method === "get") {
    return buildMockCircleWalletBalance() as T;
  }

  if (pathname === "/circle/wallets/primary/activity" && method === "get") {
    const rawTab = url.searchParams.get("tab");
    const tab: WalletActivityTab =
      rawTab === "escrow" || rawTab === "earnings" ? rawTab : "transactions";
    const page = parsePositiveInteger(url.searchParams.get("page"), 1);
    const pageSize = parsePositiveInteger(url.searchParams.get("limit"), 8);
    return buildMockWalletActivity(tab, page, pageSize) as T;
  }

  if (pathname === "/buyer/dashboard/summary" && method === "get") {
    const limit = parsePositiveInteger(url.searchParams.get("limit"), 10);
    return buildMockBuyerDashboardSummary(limit) as T;
  }

  if (pathname === "/buyer/jobs/history" && method === "get") {
    return buildMockBuyerJobHistory() as T;
  }

  if (pathname === "/buyer/recommended-agents" && method === "get") {
    const limit = parsePositiveInteger(url.searchParams.get("limit"), 6);
    return buildMockBuyerRecommendedAgents(limit) as T;
  }

  if (pathname === "/user/settings" && method === "get") {
    return readUserSettings() as T;
  }

  if (pathname === "/user/settings/profile" && method === "patch") {
    return updateUserSettingsProfile(config?.data as UserSettingsProfileUpdatePayload) as T;
  }

  if (pathname === "/user/settings/api-keys" && method === "post") {
    return createUserSettingsApiKey(config?.data as UserSettingsApiKeyCreatePayload) as T;
  }

  const revokeApiKeyMatch = pathname.match(/^\/user\/settings\/api-keys\/([^/]+)$/);
  if (revokeApiKeyMatch && method === "delete") {
    return revokeUserSettingsApiKey(decodeURIComponent(revokeApiKeyMatch[1])) as T;
  }

  const notificationMatch = pathname.match(/^\/user\/settings\/notifications\/([^/]+)$/);
  if (notificationMatch && method === "patch") {
    return updateUserSettingsNotification(
      decodeURIComponent(notificationMatch[1]),
      config?.data as UserSettingsNotificationUpdatePayload
    ) as T;
  }

  if (pathname === "/marketplace/search" && method === "get") {
    return buildMockMarketplaceSearch(url.searchParams.get("q") ?? "") as T;
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
