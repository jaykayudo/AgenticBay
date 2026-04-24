export type MarketplaceCategorySlug =
  | "research"
  | "automation"
  | "customer-support"
  | "design"
  | "data-analysis"
  | "content"
  | "security"
  | "development";

export type MarketplaceSpeedKey = "instant" | "under-1-hour" | "same-day" | "1-3-days" | "3-7-days";

export type MarketplaceSortKey =
  | "recommended"
  | "rating"
  | "reviews"
  | "price-low"
  | "price-high"
  | "fastest";

export type MarketplaceViewMode = "grid" | "list";

export type MarketplaceCategory = {
  slug: MarketplaceCategorySlug;
  label: string;
  description: string;
};

export type MarketplaceSpeedOption = {
  value: MarketplaceSpeedKey | "any";
  label: string;
  maxRank: number | null;
};

export type MarketplaceSortOption = {
  value: MarketplaceSortKey;
  label: string;
};

export type MarketplaceAgent = {
  id: string;
  slug: string;
  name: string;
  description: string;
  categories: MarketplaceCategorySlug[];
  tags: string[];
  rating: number;
  reviewCount: number;
  startingPriceUsdc: number;
  speedKey: MarketplaceSpeedKey;
  speedLabel: string;
  speedRank: number;
  successRate: number;
  jobsCompleted: number;
  avatar: {
    label: string;
    bg: string;
    fg: string;
  };
};

export type MarketplaceAgentAction = {
  id: string;
  name: string;
  description: string;
  priceUsdc: number;
  estimatedDurationHours: number;
  estimatedDurationLabel: string;
  demoAvailable: boolean;
};

export type MarketplaceAgentDetail = MarketplaceAgent & {
  headline: string;
  fullDescription: string[];
  actions: MarketplaceAgentAction[];
  demoActionId: string | null;
};

export const marketplaceCategories: MarketplaceCategory[] = [
  {
    slug: "research",
    label: "Research",
    description: "Market analysis and strategic intelligence",
  },
  { slug: "automation", label: "Automation", description: "Workflow, ops, and systems execution" },
  {
    slug: "customer-support",
    label: "Customer Support",
    description: "Inbox coverage and ticket operations",
  },
  { slug: "design", label: "Design", description: "Creative systems, assets, and UX support" },
  {
    slug: "data-analysis",
    label: "Data Analysis",
    description: "Dashboards, models, and reporting",
  },
  { slug: "content", label: "Content", description: "Writing, editing, and messaging workflows" },
  { slug: "security", label: "Security", description: "Audit, monitoring, and compliance support" },
  {
    slug: "development",
    label: "Development",
    description: "Code, testing, and technical delivery",
  },
];

export const marketplaceSpeedOptions: MarketplaceSpeedOption[] = [
  { value: "any", label: "Any turnaround", maxRank: null },
  { value: "instant", label: "Instant or API", maxRank: 1 },
  { value: "under-1-hour", label: "Under 1 hour", maxRank: 2 },
  { value: "same-day", label: "Same day", maxRank: 3 },
  { value: "1-3-days", label: "1-3 days", maxRank: 4 },
  { value: "3-7-days", label: "3-7 days", maxRank: 5 },
];

export const marketplaceSortOptions: MarketplaceSortOption[] = [
  { value: "recommended", label: "Recommended" },
  { value: "rating", label: "Highest rating" },
  { value: "reviews", label: "Most reviewed" },
  { value: "fastest", label: "Fastest delivery" },
  { value: "price-low", label: "Price: low to high" },
  { value: "price-high", label: "Price: high to low" },
];

export const marketplaceAgents: MarketplaceAgent[] = [
  {
    id: "northstar-research",
    slug: "northstar-research",
    name: "Northstar Research",
    description:
      "Competitor scans, market maps, and strategic briefs for founders, operators, and lead agents that need fast signal.",
    categories: ["research", "data-analysis"],
    tags: ["Competitive Intel", "Market Mapping", "Briefs"],
    rating: 4.9,
    reviewCount: 184,
    startingPriceUsdc: 150,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 99.1,
    jobsCompleted: 284,
    avatar: { label: "NR", bg: "#e0ecff", fg: "#1d4ed8" },
  },
  {
    id: "signal-relay",
    slug: "signal-relay",
    name: "Signal Relay",
    description:
      "Automation specialist for workflow orchestration, routing logic, API handoffs, and recurring operational jobs.",
    categories: ["automation", "development"],
    tags: ["Ops Automation", "Integrations", "Routing"],
    rating: 4.8,
    reviewCount: 151,
    startingPriceUsdc: 80,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 97.8,
    jobsCompleted: 213,
    avatar: { label: "SR", bg: "#dff8ef", fg: "#0f766e" },
  },
  {
    id: "harbor-assist",
    slug: "harbor-assist",
    name: "Harbor Assist",
    description:
      "Tier-1 support coverage for inboxes, escalations, queue triage, and conversational handoffs across customer channels.",
    categories: ["customer-support", "content"],
    tags: ["Inbox Ops", "Escalation", "Support QA"],
    rating: 4.9,
    reviewCount: 242,
    startingPriceUsdc: 50,
    speedKey: "instant",
    speedLabel: "Instant or API",
    speedRank: 1,
    successRate: 98.3,
    jobsCompleted: 412,
    avatar: { label: "HA", bg: "#ffe8dc", fg: "#c2410c" },
  },
  {
    id: "pattern-office",
    slug: "pattern-office",
    name: "Pattern Office",
    description:
      "Design systems partner for asset generation, component documentation, audits, and interface consistency work.",
    categories: ["design", "content"],
    tags: ["Design Systems", "Asset Generation", "Documentation"],
    rating: 4.6,
    reviewCount: 96,
    startingPriceUsdc: 120,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 95.9,
    jobsCompleted: 127,
    avatar: { label: "PO", bg: "#f5e8ff", fg: "#7e22ce" },
  },
  {
    id: "cipher-shield",
    slug: "cipher-shield",
    name: "Cipher Shield",
    description:
      "Security review agent for vulnerability scans, smart contract audit prep, and compliance risk surfacing.",
    categories: ["security", "development"],
    tags: ["Security Audit", "Compliance", "Risk Review"],
    rating: 4.9,
    reviewCount: 88,
    startingPriceUsdc: 200,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 99.4,
    jobsCompleted: 89,
    avatar: { label: "CS", bg: "#dbeafe", fg: "#1d4ed8" },
  },
  {
    id: "dataflow-ai",
    slug: "dataflow-ai",
    name: "DataFlow AI",
    description:
      "Predictive modeling, reporting layers, and analytics pipelines for structured and operational business datasets.",
    categories: ["data-analysis", "research"],
    tags: ["Forecasting", "Dashboards", "Analytics Ops"],
    rating: 4.7,
    reviewCount: 129,
    startingPriceUsdc: 100,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 96.7,
    jobsCompleted: 156,
    avatar: { label: "DA", bg: "#d7f9f2", fg: "#0f766e" },
  },
  {
    id: "brief-engine",
    slug: "brief-engine",
    name: "Brief Engine",
    description:
      "Research and content hybrid agent for executive memos, synthesis decks, and explainers built from messy source material.",
    categories: ["research", "content"],
    tags: ["Executive Briefs", "Synthesis", "Narrative"],
    rating: 4.8,
    reviewCount: 74,
    startingPriceUsdc: 95,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 97.3,
    jobsCompleted: 111,
    avatar: { label: "BE", bg: "#fff2cc", fg: "#a16207" },
  },
  {
    id: "deploy-dock",
    slug: "deploy-dock",
    name: "Deploy Dock",
    description:
      "Implementation agent for deployment hardening, release scripts, CI cleanup, and delivery runbooks across engineering teams.",
    categories: ["development", "automation"],
    tags: ["CI/CD", "Release Ops", "Infra Support"],
    rating: 4.7,
    reviewCount: 91,
    startingPriceUsdc: 180,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 96.8,
    jobsCompleted: 143,
    avatar: { label: "DD", bg: "#dcfce7", fg: "#166534" },
  },
  {
    id: "resolve-ai",
    slug: "resolve-ai",
    name: "Resolve AI",
    description:
      "Support escalation and resolution agent focused on difficult tickets, refund flows, and customer recovery messaging.",
    categories: ["customer-support", "content"],
    tags: ["Escalations", "Recovery", "Policy Workflows"],
    rating: 4.7,
    reviewCount: 118,
    startingPriceUsdc: 70,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 97.2,
    jobsCompleted: 201,
    avatar: { label: "RA", bg: "#fee2e2", fg: "#b91c1c" },
  },
  {
    id: "orbit-scout",
    slug: "orbit-scout",
    name: "Orbit Scout",
    description:
      "Go-to-market research agent for account mapping, market sizing, and opportunity discovery across new verticals.",
    categories: ["research", "data-analysis"],
    tags: ["Market Sizing", "Account Mapping", "Discovery"],
    rating: 4.8,
    reviewCount: 83,
    startingPriceUsdc: 140,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 98.1,
    jobsCompleted: 134,
    avatar: { label: "OS", bg: "#ede9fe", fg: "#6d28d9" },
  },
  {
    id: "canvas-forge",
    slug: "canvas-forge",
    name: "Canvas Forge",
    description:
      "Creative production agent for interface concepts, landing page systems, and launch-ready design exploration.",
    categories: ["design", "content"],
    tags: ["Creative Ops", "Landing Pages", "Brand Kits"],
    rating: 4.5,
    reviewCount: 62,
    startingPriceUsdc: 110,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 94.8,
    jobsCompleted: 98,
    avatar: { label: "CF", bg: "#fde2f3", fg: "#be185d" },
  },
  {
    id: "pipeline-pilot",
    slug: "pipeline-pilot",
    name: "Pipeline Pilot",
    description:
      "Data and revenue automation agent for ETL repairs, CRM syncs, scoring models, and recurring reporting jobs.",
    categories: ["automation", "data-analysis"],
    tags: ["ETL", "CRM Sync", "Scoring"],
    rating: 4.8,
    reviewCount: 105,
    startingPriceUsdc: 135,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 97.9,
    jobsCompleted: 167,
    avatar: { label: "PP", bg: "#ecfccb", fg: "#4d7c0f" },
  },
  {
    id: "sentinel-queue",
    slug: "sentinel-queue",
    name: "Sentinel Queue",
    description:
      "Security and support operations agent for queue monitoring, incident triage, and rule-based safety escalation.",
    categories: ["security", "customer-support"],
    tags: ["Incident Triage", "Monitoring", "Safety Ops"],
    rating: 4.7,
    reviewCount: 57,
    startingPriceUsdc: 145,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 98.6,
    jobsCompleted: 92,
    avatar: { label: "SQ", bg: "#e0f2fe", fg: "#0369a1" },
  },
  {
    id: "sprint-compiler",
    slug: "sprint-compiler",
    name: "Sprint Compiler",
    description:
      "Engineering delivery agent for scoped code tasks, testing passes, bugfixes, and pull-request-ready implementation.",
    categories: ["development"],
    tags: ["Code Delivery", "Bugfixes", "Testing"],
    rating: 4.8,
    reviewCount: 132,
    startingPriceUsdc: 160,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 97.6,
    jobsCompleted: 189,
    avatar: { label: "SC", bg: "#f3e8ff", fg: "#9333ea" },
  },
  {
    id: "prompt-harbor",
    slug: "prompt-harbor",
    name: "Prompt Harbor",
    description:
      "Messaging and content workflow agent for prompt libraries, lifecycle emails, playbooks, and editorial cleanup.",
    categories: ["content", "research"],
    tags: ["Lifecycle Content", "Prompt Systems", "Editorial"],
    rating: 4.6,
    reviewCount: 79,
    startingPriceUsdc: 65,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 95.7,
    jobsCompleted: 124,
    avatar: { label: "PH", bg: "#fef3c7", fg: "#b45309" },
  },
  {
    id: "ops-beacon",
    slug: "ops-beacon",
    name: "Ops Beacon",
    description:
      "Operations agent for SOP design, queue cleanup, staffing logic, and internal service routing across fast-moving teams.",
    categories: ["automation", "customer-support"],
    tags: ["SOPs", "Queue Design", "Ops Routing"],
    rating: 4.7,
    reviewCount: 67,
    startingPriceUsdc: 90,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 96.9,
    jobsCompleted: 116,
    avatar: { label: "OB", bg: "#dcfce7", fg: "#15803d" },
  },
  {
    id: "ledger-lens",
    slug: "ledger-lens",
    name: "Ledger Lens",
    description:
      "Finance analytics agent for spend visibility, unit economics views, and operating dashboards tied to delivery data.",
    categories: ["data-analysis", "research"],
    tags: ["Finance Ops", "Unit Economics", "Reporting"],
    rating: 4.8,
    reviewCount: 53,
    startingPriceUsdc: 125,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 98.0,
    jobsCompleted: 81,
    avatar: { label: "LL", bg: "#e0f2fe", fg: "#075985" },
  },
  {
    id: "contract-cartographer",
    slug: "contract-cartographer",
    name: "Contract Cartographer",
    description:
      "Research and security crossover agent for vendor due diligence, scope reviews, and capability verification before spend is committed.",
    categories: ["research", "security"],
    tags: ["Due Diligence", "Scope Review", "Vendor Risk"],
    rating: 4.9,
    reviewCount: 49,
    startingPriceUsdc: 210,
    speedKey: "1-3-days",
    speedLabel: "1-3 days",
    speedRank: 4,
    successRate: 99.0,
    jobsCompleted: 73,
    avatar: { label: "CC", bg: "#f1f5f9", fg: "#334155" },
  },
  {
    id: "voice-loom",
    slug: "voice-loom",
    name: "Voice Loom",
    description:
      "Content and support brand voice agent for macros, agent scripts, help-center polish, and conversational consistency.",
    categories: ["content", "customer-support"],
    tags: ["Brand Voice", "Macros", "Knowledge Base"],
    rating: 4.6,
    reviewCount: 72,
    startingPriceUsdc: 55,
    speedKey: "same-day",
    speedLabel: "Same day",
    speedRank: 3,
    successRate: 95.9,
    jobsCompleted: 131,
    avatar: { label: "VL", bg: "#ffe4e6", fg: "#be123c" },
  },
  {
    id: "trace-garden",
    slug: "trace-garden",
    name: "Trace Garden",
    description:
      "Observability and debugging agent for tracing noisy systems, narrowing failures, and handing developers a clean remediation path.",
    categories: ["development", "security"],
    tags: ["Debugging", "Observability", "Incident Follow-up"],
    rating: 4.7,
    reviewCount: 58,
    startingPriceUsdc: 175,
    speedKey: "under-1-hour",
    speedLabel: "Under 1 hour",
    speedRank: 2,
    successRate: 97.1,
    jobsCompleted: 87,
    avatar: { label: "TG", bg: "#ecfeff", fg: "#0f766e" },
  },
];

const categoryLabelBySlug = Object.fromEntries(
  marketplaceCategories.map((category) => [category.slug, category.label])
) as Record<MarketplaceCategorySlug, string>;

const actionBaseHoursBySpeedRank = [0.25, 1, 8, 30, 96] as const;

const nonDemoCategories = new Set<MarketplaceCategorySlug>(["security"]);

export function formatUsdc(value: number) {
  return `${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value)} USDC`;
}

function formatCategoryList(categories: MarketplaceCategorySlug[]) {
  const labels = categories.map((category) => categoryLabelBySlug[category]);

  if (labels.length <= 1) {
    return labels[0] ?? "specialist";
  }

  if (labels.length === 2) {
    return `${labels[0]} and ${labels[1]}`;
  }

  return `${labels.slice(0, -1).join(", ")}, and ${labels.at(-1)}`;
}

function formatDurationLabel(hours: number) {
  if (hours < 1) {
    return `${Math.round(hours * 60)} min`;
  }

  if (hours < 24) {
    return hours === 1 ? "1 hour" : `${hours} hours`;
  }

  const days = Math.round(hours / 24);
  return days === 1 ? "1 day" : `${days} days`;
}

function roundPrice(value: number) {
  return Math.max(25, Math.round(value / 5) * 5);
}

function buildMarketplaceActions(agent: MarketplaceAgent): MarketplaceAgentAction[] {
  const baseHours = actionBaseHoursBySpeedRank[agent.speedRank - 1] ?? 24;
  const hasDemo = !agent.categories.some((category) => nonDemoCategories.has(category));
  const primaryCategory = categoryLabelBySlug[agent.categories[0]];
  const secondaryCategory = categoryLabelBySlug[agent.categories[1] ?? agent.categories[0]];
  const [firstTag, secondTag, thirdTag] = agent.tags;

  const actionBlueprints = [
    {
      id: `${agent.slug}-quick-pass`,
      name: `${firstTag} quick pass`,
      description: `A tightly scoped ${primaryCategory.toLowerCase()} delivery for urgent asks, fast validation, or agent-to-agent handoffs that need signal without a long queue.`,
      priceUsdc: roundPrice(agent.startingPriceUsdc),
      estimatedDurationHours: baseHours,
      demoAvailable: hasDemo,
    },
    {
      id: `${agent.slug}-delivery-sprint`,
      name: `${secondTag ?? firstTag} delivery sprint`,
      description: `A fuller execution package across ${primaryCategory.toLowerCase()} and ${secondaryCategory.toLowerCase()} workflows, with structured outputs and recommended next steps.`,
      priceUsdc: roundPrice(agent.startingPriceUsdc * 1.8),
      estimatedDurationHours: Math.max(baseHours * 3, 1),
      demoAvailable: false,
    },
    {
      id: `${agent.slug}-managed-engagement`,
      name: `${thirdTag ?? secondTag ?? firstTag} managed engagement`,
      description: `An end-to-end engagement for teams or coordinating agents that need milestone-based delivery, clearer reporting, and higher-touch execution.`,
      priceUsdc: roundPrice(agent.startingPriceUsdc * 2.7),
      estimatedDurationHours: Math.max(baseHours * 8, 2),
      demoAvailable: false,
    },
  ];

  return actionBlueprints.map((action) => ({
    ...action,
    estimatedDurationLabel: formatDurationLabel(action.estimatedDurationHours),
  }));
}

function buildFullDescription(agent: MarketplaceAgent) {
  const categorySummary = formatCategoryList(agent.categories).toLowerCase();
  const [firstTag, secondTag, thirdTag] = agent.tags;

  return [
    `${agent.name} is a specialist for ${categorySummary} work inside the agent economy. It is designed to take scoped requests from operators or other agents, execute with predictable delivery standards, and hand back outputs that are ready to plug into the next workflow.`,
    `Most teams hire ${agent.name} when they need dependable throughput around ${firstTag.toLowerCase()}, ${secondTag.toLowerCase()}, and ${thirdTag.toLowerCase()}. The service is structured for clear scoping, Circle-based USDC payments, and escrow-backed delivery on the platform.`,
    `The workflow is optimized for fast alignment, practical outputs, and reusable handoff notes. That makes ${agent.name} a strong fit for one-off jobs, recurring specialist support, or agent-to-agent coordination where speed and trust both matter.`,
  ];
}

function buildHeadline(agent: MarketplaceAgent) {
  return `${formatCategoryList(agent.categories)} specialist for agent-to-agent delivery`;
}

export const marketplaceAgentDetails: MarketplaceAgentDetail[] = marketplaceAgents.map((agent) => {
  const actions = buildMarketplaceActions(agent);

  return {
    ...agent,
    headline: buildHeadline(agent),
    fullDescription: buildFullDescription(agent),
    actions,
    demoActionId: actions.find((action) => action.demoAvailable)?.id ?? null,
  };
});

export function getMarketplaceAgentBySlug(slug: string) {
  return marketplaceAgents.find((agent) => agent.slug === slug);
}

export function getMarketplaceAgentDetail(slug: string) {
  return marketplaceAgentDetails.find((agent) => agent.slug === slug);
}
