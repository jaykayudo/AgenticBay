type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface ApiEndpointProps {
  method: HttpMethod;
  path: string;
  auth?: "bearer" | "api-key" | "none";
  description?: string;
}

const methodColors: Record<HttpMethod, string> = {
  GET: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  POST: "bg-green-500/10 text-green-400 border-green-500/30",
  PUT: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  PATCH: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  DELETE: "bg-red-500/10 text-red-400 border-red-500/30",
};

const authLabels: Record<string, string> = {
  bearer: "Bearer JWT",
  "api-key": "API Key",
  none: "Public",
};

export function ApiEndpoint({ method, path, auth, description }: ApiEndpointProps) {
  return (
    <div className="my-4 rounded-lg border border-border bg-muted/20 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded border px-2 py-0.5 font-mono text-xs font-bold ${methodColors[method]}`}
        >
          {method}
        </span>
        <code className="font-mono text-sm text-foreground">{path}</code>
        {auth && (
          <span className="ml-auto rounded-full border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground">
            {authLabels[auth] ?? auth}
          </span>
        )}
      </div>
      {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}
