import type { Metadata } from "next";
import { Suspense } from "react";

import { MarketplaceSearchResultsPage } from "@/components/marketplace/MarketplaceSearchResultsPage";

export const metadata: Metadata = {
  title: "AgenticBay Marketplace Search - Agent Results",
  description:
    "Natural language marketplace search results with orchestrator-ranked agent matches.",
};

function MarketplaceSearchFallback() {
  return (
    <div className="min-h-screen bg-[var(--background)] px-4 py-6 text-[var(--foreground)] md:px-6 xl:px-8">
      <div className="mx-auto max-w-[var(--layout-max)] space-y-4">
        <div className="app-panel h-20 animate-pulse" />
        <div className="app-panel h-36 animate-pulse" />
        <div className="app-panel h-40 animate-pulse" />
        <div className="app-panel h-64 animate-pulse" />
      </div>
    </div>
  );
}

export default function MarketplaceSearchPage() {
  return (
    <Suspense fallback={<MarketplaceSearchFallback />}>
      <MarketplaceSearchResultsPage />
    </Suspense>
  );
}
