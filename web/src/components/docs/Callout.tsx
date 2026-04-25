import { AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";

type CalloutType = "info" | "warning" | "error" | "success";

interface CalloutProps {
  type?: CalloutType;
  title?: string;
  children: React.ReactNode;
}

const config: Record<
  CalloutType,
  { icon: React.ElementType; className: string }
> = {
  info: {
    icon: Info,
    className:
      "border-blue-500/30 bg-blue-500/5 [&_svg]:text-blue-500 [&_.callout-title]:text-blue-400",
  },
  warning: {
    icon: AlertTriangle,
    className:
      "border-yellow-500/30 bg-yellow-500/5 [&_svg]:text-yellow-500 [&_.callout-title]:text-yellow-400",
  },
  error: {
    icon: AlertCircle,
    className:
      "border-red-500/30 bg-red-500/5 [&_svg]:text-red-500 [&_.callout-title]:text-red-400",
  },
  success: {
    icon: CheckCircle,
    className:
      "border-green-500/30 bg-green-500/5 [&_svg]:text-green-500 [&_.callout-title]:text-green-400",
  },
};

export function Callout({ type = "info", title, children }: CalloutProps) {
  const { icon: Icon, className } = config[type];

  return (
    <div className={`my-6 flex gap-3 rounded-lg border p-4 ${className}`}>
      <Icon className="mt-0.5 size-4 shrink-0" />
      <div className="min-w-0 flex-1 text-sm">
        {title && (
          <p className="callout-title mb-1 font-semibold">{title}</p>
        )}
        <div className="text-foreground/80 [&>p]:m-0">{children}</div>
      </div>
    </div>
  );
}
