export interface NavItem {
  title: string;
  href: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const docsNav: NavGroup[] = [
  {
    title: "Getting Started",
    items: [
      { title: "Introduction", href: "/docs/getting-started/introduction" },
      { title: "Quickstart", href: "/docs/getting-started/quickstart" },
      { title: "Architecture", href: "/docs/getting-started/architecture" },
    ],
  },
  {
    title: "Service Agents",
    items: [
      { title: "Overview", href: "/docs/service-agents/overview" },
      { title: "Health Endpoint", href: "/docs/service-agents/health-endpoint" },
      {
        title: "Capabilities Endpoint",
        href: "/docs/service-agents/capabilities-endpoint",
      },
      { title: "Invoke Endpoint", href: "/docs/service-agents/invoke-endpoint" },
      { title: "Authentication", href: "/docs/service-agents/authentication" },
    ],
  },
  {
    title: "User Agents",
    items: [
      { title: "Overview", href: "/docs/user-agents/overview" },
      {
        title: "WebSocket Protocol",
        href: "/docs/user-agents/websocket-protocol",
      },
      { title: "Session Lifecycle", href: "/docs/user-agents/session-lifecycle" },
      { title: "Message Types", href: "/docs/user-agents/message-types" },
    ],
  },
  {
    title: "API Reference",
    items: [
      { title: "Authentication", href: "/docs/api-reference/authentication" },
      { title: "Agents", href: "/docs/api-reference/agents" },
      { title: "Sessions", href: "/docs/api-reference/sessions" },
      { title: "Marketplace", href: "/docs/api-reference/marketplace" },
    ],
  },
  {
    title: "Tutorials",
    items: [
      {
        title: "Build Your First Agent",
        href: "/docs/tutorials/build-your-first-agent",
      },
      {
        title: "Integrate with Marketplace",
        href: "/docs/tutorials/integrate-with-marketplace",
      },
    ],
  },
];
