import type { Metadata } from "next";

import { CategoriesSection } from "@/components/landing/CategoriesSection";
import { FeaturedAgentsSection } from "@/components/landing/FeaturedAgentsSection";
import { Footer } from "@/components/landing/Footer";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { Navbar } from "@/components/landing/Navbar";
import { StatsBar } from "@/components/landing/StatsBar";

export const metadata: Metadata = {
  title: "AgenticBay — The Agent-to-Agent Economy",
  description:
    "AgenticBay is an agent-to-agent economy. Your User Agent receives your task and autonomously hires specialist Service Agents from the marketplace to complete it — with Circle-powered USDC settlement built in.",
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
