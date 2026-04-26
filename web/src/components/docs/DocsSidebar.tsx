"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { docsNav, type NavGroup } from "@/lib/docs/nav";

function SidebarGroup({ group }: { group: NavGroup }) {
  const pathname = usePathname();

  return (
    <div className="mb-6">
      <p className="mb-1 px-3 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        {group.title}
      </p>
      <ul className="space-y-0.5">
        {group.items.map((item) => {
          const active = pathname === item.href;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                {item.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function DocsSidebar() {
  return (
    <nav className="py-6 pr-4">
      {docsNav.map((group) => (
        <SidebarGroup key={group.title} group={group} />
      ))}
    </nav>
  );
}
