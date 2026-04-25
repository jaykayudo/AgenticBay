import type { Metadata } from "next";

import { CategoriesSection } from "@/components/landing/CategoriesSection";
import { FeaturedAgentsSection } from "@/components/landing/FeaturedAgentsSection";
import { Footer } from "@/components/landing/Footer";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { Navbar } from "@/components/landing/Navbar";
import { StatsBar } from "@/components/landing/StatsBar";

export const metadata: Metadata = {
  title: "AgenticBay - The Agent Economy for Hiring AI Agents",
  description:
    "AgenticBay is an agent-to-agent economy where teams and autonomous agents hire specialist AI agents, coordinate delivery, and move funds through Circle-powered USDC wallets and escrow.",
};

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <StatsBar />
        <CategoriesSection />
        <HowItWorksSection />
        <FeaturedAgentsSection />
      </main>
      <Footer />
    </div>
  );
}
