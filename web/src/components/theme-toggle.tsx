"use client";

import { MoonStar, SunMedium } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false
  );

  const activeTheme = mounted && resolvedTheme === "dark" ? "dark" : "light";

  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] p-1 shadow-[var(--shadow-soft)]">
      {[
        { value: "light", label: "Light", icon: SunMedium },
        { value: "dark", label: "Dark", icon: MoonStar },
      ].map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          data-active={activeTheme === value}
          aria-pressed={activeTheme === value}
          className={cn(
            "theme-chip inline-flex h-9 items-center gap-2 rounded-full px-3 text-sm font-medium transition-all",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          )}
          onClick={() => setTheme(value)}
        >
          <Icon className="h-4 w-4" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}
