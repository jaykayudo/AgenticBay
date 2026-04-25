import { DocsPageNav } from "./DocsPageNav";

interface DocsContentProps {
  children: React.ReactNode;
  href: string;
}

export function DocsContent({ children, href }: DocsContentProps) {
  return (
    <article>
      <div className="docs-prose">{children}</div>
      <DocsPageNav currentHref={href} />
    </article>
  );
}
