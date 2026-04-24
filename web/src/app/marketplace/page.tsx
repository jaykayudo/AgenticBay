import type { Metadata } from "next";
import { Suspense } from "react";

import { MarketplaceBrowse } from "@/components/marketplace/MarketplaceBrowse";

export const metadata: Metadata = {
  title: "AgenticBay Marketplace - Browse Service Agents",
  description:
    "Discover, search, and filter specialist service agents by category, price, rating, and delivery speed.",
};

function MarketplacePageFallback() {
  return (
    <div className="min-h-screen bg-[var(--background)] px-4 py-6 text-[var(--foreground)] md:px-6 xl:px-8">
      <div className="mx-auto max-w-[var(--layout-max)]">
        <div className="app-panel h-28 animate-pulse" />
        <div className="mt-6 grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
          <div className="app-panel h-[520px] animate-pulse" />
          <div className="space-y-4">
            <div className="app-panel h-32 animate-pulse" />
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }, (_, index) => (
                <div key={index} className="app-panel h-[320px] animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MarketplacePage() {
  return (
    <Suspense fallback={<MarketplacePageFallback />}>
      <MarketplaceBrowse />
    </Suspense>
  );
}
