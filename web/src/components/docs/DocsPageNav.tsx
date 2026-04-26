import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";

import { docsNav, type NavItem } from "@/lib/docs/nav";

function flatNav(): NavItem[] {
  return docsNav.flatMap((g) => g.items);
}

interface DocsPageNavProps {
  currentHref: string;
}

export function DocsPageNav({ currentHref }: DocsPageNavProps) {
  const items = flatNav();
  const idx = items.findIndex((item) => item.href === currentHref);
  const prev = idx > 0 ? items[idx - 1] : null;
  const next = idx < items.length - 1 ? items[idx + 1] : null;

  if (!prev && !next) return null;

  return (
    <div className="mt-12 flex gap-4 border-t border-border pt-6">
      {prev && (
        <Link
          href={prev.href}
          className="app-panel flex flex-1 items-center gap-3 p-4 transition-colors hover:border-primary/30"
        >
          <ChevronLeft className="size-4 shrink-0 text-muted-foreground" />
          <div>
            <p className="text-xs text-muted-foreground">Previous</p>
            <p className="text-sm font-medium">{prev.title}</p>
          </div>
        </Link>
      )}
      {!prev && <div className="flex-1" />}
      {next && (
        <Link
          href={next.href}
          className="app-panel flex flex-1 items-center justify-end gap-3 p-4 text-right transition-colors hover:border-primary/30"
        >
          <div>
            <p className="text-xs text-muted-foreground">Next</p>
            <p className="text-sm font-medium">{next.title}</p>
          </div>
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        </Link>
      )}
    </div>
  );
}
