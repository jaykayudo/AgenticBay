import type { Metadata } from "next";

import { OrchestratorInterfacePage } from "@/components/orchestrator/OrchestratorInterfacePage";

export const metadata: Metadata = {
  title: "Orchestrator | AgenticBay",
  description:
    "Describe a task, receive agent recommendations, review execution plans, and start marketplace jobs.",
};

export default function OrchestratorPage() {
  return <OrchestratorInterfacePage />;
}
