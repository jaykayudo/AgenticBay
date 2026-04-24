import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MarketplaceAgentDetail } from "@/components/marketplace/MarketplaceAgentDetail";
import { getMarketplaceAgentDetail } from "@/lib/marketplace-data";

type MarketplaceAgentPageProps = {
  params: Promise<{
    agentSlug: string;
  }>;
};

export async function generateMetadata({
  params,
}: MarketplaceAgentPageProps): Promise<Metadata> {
  const { agentSlug } = await params;
  const agent = getMarketplaceAgentDetail(decodeURIComponent(agentSlug));

  if (!agent) {
    return {
      title: "Agent not found - AgenticBay",
    };
  }

  return {
    title: `${agent.name} - Hire on AgenticBay`,
    description: `${agent.headline}. Review actions, pricing, delivery metrics, and buyer feedback before hiring.`,
  };
}

export default async function MarketplaceAgentPage({
  params,
}: MarketplaceAgentPageProps) {
  const { agentSlug } = await params;
  const decodedSlug = decodeURIComponent(agentSlug);
  const agent = getMarketplaceAgentDetail(decodedSlug);

  if (!agent) {
    notFound();
  }

  return <MarketplaceAgentDetail agentSlug={decodedSlug} />;
}
