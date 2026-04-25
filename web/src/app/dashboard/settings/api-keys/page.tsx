import { ApiKeyManagementPanel } from "@/components/dashboard/ApiKeyManagementPanel";

export const metadata = {
  title: "API Keys | AgenticBay",
  description: "Create, rotate, revoke, and inspect API keys for AgenticBay integrations.",
};

export default function DashboardApiKeysPage() {
  return <ApiKeyManagementPanel />;
}
