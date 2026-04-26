import type { MDXComponents } from "mdx/types";

import { ApiEndpoint } from "@/components/docs/ApiEndpoint";
import { Callout } from "@/components/docs/Callout";
import { DocsTabs, DocsTabItem } from "@/components/docs/DocsTabs";

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    Callout,
    Tabs: DocsTabs,
    Tab: DocsTabItem,
    ApiEndpoint,
    ...components,
  };
}
