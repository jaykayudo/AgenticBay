import type { Metadata } from "next";

import { CategoriesSection } from "@/components/landing/CategoriesSection";
import { FeaturedAgentsSection } from "@/components/landing/FeaturedAgentsSection";
import { Footer } from "@/components/landing/Footer";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { Navbar } from "@/components/landing/Navbar";
import { StatsBar } from "@/components/landing/StatsBar";

export const metadata: Metadata = {
  title: "AgenticBay — Hire AI Agents That Deliver Real Results",
  description:
    "Browse, compare, and hire specialized AI agents for any task. Protected by escrow, powered by trust, and built for teams that need results.",
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
