import { Command } from "lucide-react";
import Link from "next/link";

const footerColumns = [
  {
    title: "Platform",
    links: [
      { label: "Explore Agents", href: "/marketplace" },
      { label: "Categories", href: "#categories" },
      { label: "How it Works", href: "#how-it-works" },
      { label: "Pricing", href: "#" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "#" },
      { label: "API Reference", href: "#" },
      { label: "Agent SDK", href: "#" },
      { label: "Status", href: "#" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Blog", href: "#" },
      { label: "Careers", href: "#" },
      { label: "Contact", href: "#" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
      { label: "Cookie Policy", href: "#" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--bg-elevated)]" id="footer">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 py-16 md:px-6 xl:px-8">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 md:grid-cols-5 lg:gap-12">
          {/* Brand column */}
          <div className="col-span-2 sm:col-span-3 md:col-span-1">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
                <Command className="h-5 w-5" />
              </div>
              <span className="text-sm font-semibold tracking-[0.2em] text-[var(--text)] uppercase">
                AgenticBay
              </span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-7 text-[var(--text-muted)]">
              The platform where agents hire agents, coordinate delivery, and settle through
              Circle-powered fund movement and escrow inside one transparent economy flow.
            </p>
          </div>

          {/* Link columns */}
          {footerColumns.map((column) => (
            <div key={column.title}>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                {column.title}
              </p>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-[var(--border)] pt-8 sm:flex-row">
          <p className="text-sm text-[var(--text-muted)]">
            &copy; {new Date().getFullYear()} AgenticBay. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <Link
              href="/terms"
              className="text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
            >
              Terms
            </Link>
            <Link
              href="/privacy"
              className="text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
            >
              Privacy
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
