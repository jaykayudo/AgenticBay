import Link from "next/link";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-screen">
      <aside className="flex w-64 flex-col gap-2 border-r bg-muted/40 p-4">
        <div className="mb-2 px-2 py-3">
          <span className="text-lg font-semibold">Agentic Bay</span>
        </div>
        <nav className="flex flex-col gap-1">
          <Link
            href="/dashboard"
            className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            Overview
          </Link>
          <Link
            href="/dashboard/agents"
            className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            Agents
          </Link>
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
