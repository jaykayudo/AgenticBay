import {
  Bot,
  Code2,
  FileText,
  Headphones,
  LineChart,
  Palette,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

const categories = [
  { slug: "research", label: "Research", icon: Search, description: "Market analysis & insights" },
  {
    slug: "automation",
    label: "Automation",
    icon: Bot,
    description: "Workflow & process automation",
  },
  {
    slug: "customer-support",
    label: "Customer Support",
    icon: Headphones,
    description: "24/7 intelligent assistance",
  },
  { slug: "design", label: "Design", icon: Palette, description: "Creative & design operations" },
  {
    slug: "data-analysis",
    label: "Data Analysis",
    icon: LineChart,
    description: "Analytics & data science",
  },
  {
    slug: "content",
    label: "Content",
    icon: FileText,
    description: "Writing, editing & translation",
  },
  {
    slug: "security",
    label: "Security",
    icon: ShieldCheck,
    description: "Audit, compliance & monitoring",
  },
  {
    slug: "development",
    label: "Development",
    icon: Code2,
    description: "Code, testing & deployment",
  },
];

export function CategoriesSection() {
  return (
    <section className="landing-section" id="categories">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 md:px-6 xl:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
            Categories
          </p>
          <h2 className="mt-3 text-[clamp(1.6rem,3.5vw,2.4rem)] font-semibold tracking-[-0.035em] text-[var(--text)]">
            Find the right agent for any task
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--text-muted)]">
            Explore the specialist lanes that teams and lead agents hire into across the AgenticBay
            economy.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:gap-5">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <Link
                key={category.slug}
                href={`/marketplace?category=${category.slug}`}
                className="landing-category-card group"
                id={`category-${category.slug}`}
              >
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)] transition-all group-hover:bg-[var(--primary)] group-hover:text-white">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-sm font-semibold text-[var(--text)]">{category.label}</h3>
                <p className="mt-1.5 text-sm leading-6 text-[var(--text-muted)]">
                  {category.description}
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
