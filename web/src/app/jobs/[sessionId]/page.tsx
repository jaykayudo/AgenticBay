import type { Metadata } from "next";

import { JobSessionPage } from "@/components/marketplace/JobSessionPage";

type JobSessionPageProps = {
  params: Promise<{
    sessionId: string;
  }>;
};

export const metadata: Metadata = {
  title: "Job Session - AgenticBay",
  description: "Review the marketplace job session created when you hired an agent.",
};

export default async function MarketplaceJobSessionPage({
  params,
}: JobSessionPageProps) {
  const { sessionId } = await params;

  return <JobSessionPage sessionId={decodeURIComponent(sessionId)} />;
}
