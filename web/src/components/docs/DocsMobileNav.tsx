"use client";

import { Menu, X, BookOpen } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { docsNav } from "@/lib/docs/nav";

export function DocsMobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-md p-2 text-muted-foreground hover:text-foreground lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="size-5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 overflow-y-auto bg-background p-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <Link href="/docs" className="flex items-center gap-2 font-semibold">
                <BookOpen className="size-4 text-primary" />
                Documentation
              </Link>
              <button onClick={() => setOpen(false)}>
                <X className="size-5 text-muted-foreground" />
              </button>
            </div>
            <nav>
              {docsNav.map((group) => (
                <div key={group.title} className="mb-6">
                  <p className="mb-1 px-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                    {group.title}
                  </p>
                  <ul className="space-y-0.5">
                    {group.items.map((item) => (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={() => setOpen(false)}
                          className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
                            pathname === item.href
                              ? "bg-primary/10 font-medium text-primary"
                              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                          }`}
                        >
                          {item.title}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
