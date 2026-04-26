"use client";

import { Search, X } from "lucide-react";
import Link from "next/link";
import { useState, useEffect, useRef, useCallback } from "react";

import { docsNav } from "@/lib/docs/nav";

const allItems = docsNav.flatMap((g) => g.items);

export function DocsSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const results = query
    ? allItems.filter((item) => item.title.toLowerCase().includes(query.toLowerCase()))
    : [];

  const openSearch = useCallback(() => {
    setOpen(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        openSearch();
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [openSearch]);

  return (
    <>
      <button
        onClick={openSearch}
        className="flex w-full items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-border/80 hover:bg-muted/50"
      >
        <Search className="size-3.5" />
        <span className="flex-1 text-left">Search docs…</span>
        <kbd className="hidden rounded border border-border px-1 py-0.5 font-mono text-[10px] sm:inline">
          ⌘K
        </kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[20vh] backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="app-panel w-full max-w-lg overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-border px-3 py-3">
              <Search className="size-4 shrink-0 text-muted-foreground" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search documentation…"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              {query && (
                <button onClick={() => setQuery("")}>
                  <X className="size-4 text-muted-foreground" />
                </button>
              )}
            </div>

            {results.length > 0 && (
              <ul className="max-h-64 overflow-y-auto py-2">
                {results.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted/50"
                    >
                      <Search className="size-3.5 shrink-0 text-muted-foreground" />
                      {item.title}
                    </Link>
                  </li>
                ))}
              </ul>
            )}

            {query && results.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                No results for &quot;{query}&quot;
              </p>
            )}

            {!query && (
              <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                Type to search the docs
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
