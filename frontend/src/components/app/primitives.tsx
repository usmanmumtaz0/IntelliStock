import { useEffect, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, Clock, AlertTriangle, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReconStatus, ZoneHealth, SeverityTone } from "@/lib/view-models";

export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("rounded-lg border bg-surface", className)}>
      {(title || action) && (
        <header className="flex h-11 items-center justify-between border-b px-4">
          <h2 className="text-[13px] font-medium text-foreground">{title}</h2>
          {action}
        </header>
      )}
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

const dotColor: Record<string, string> = {
  healthy: "bg-healthy",
  live: "bg-healthy",
  low: "bg-warning",
  warning: "bg-warning",
  offline: "bg-critical",
  critical: "bg-critical",
  pending: "bg-pending",
  info: "bg-chart-2",
};

export function StatusDot({
  state,
  pulse,
}: {
  state: keyof typeof dotColor | string;
  pulse?: boolean;
}) {
  return (
    <span className="relative inline-flex size-2 shrink-0">
      {pulse && (
        <span className={cn("absolute inset-0 rounded-full animate-live-ping", dotColor[state])} />
      )}
      <span className={cn("relative inline-flex size-2 rounded-full", dotColor[state])} />
    </span>
  );
}

export function LiveIndicator({ label = "Live" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-healthy">
      <StatusDot state="live" pulse />
      {label}
    </span>
  );
}

export function Tag({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "healthy" | "warning" | "critical" | "primary" | "info";
  className?: string;
}) {
  const tones = {
    neutral: "bg-muted text-muted-foreground border-border",
    healthy: "bg-healthy/10 text-healthy border-healthy/30",
    warning: "bg-warning/10 text-warning border-warning/30",
    critical: "bg-critical/10 text-critical border-critical/30",
    primary: "bg-primary/10 text-primary border-primary/30",
    info: "bg-chart-2/10 text-chart-2 border-chart-2/30",
  };
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center gap-1 rounded border px-1.5 text-[11px] font-medium whitespace-nowrap",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Reconciliation status — verified = solid, pending = hatched/dashed, flagged = amber. */
export function ReconBadge({ status }: { status: ReconStatus }) {
  if (status === "verified")
    return (
      <span className="verified-solid inline-flex h-5 items-center gap-1 rounded px-1.5 text-[11px] font-medium text-verified">
        <CheckCircle2 className="size-3" /> Verified
      </span>
    );
  if (status === "pending")
    return (
      <span className="pending-hatch inline-flex h-5 items-center gap-1 rounded px-1.5 text-[11px] font-medium text-muted-foreground">
        <Clock className="size-3" /> Pending
      </span>
    );
  return (
    <span className="inline-flex h-5 items-center gap-1 rounded border border-warning/40 bg-warning/10 px-1.5 text-[11px] font-medium text-warning">
      <AlertTriangle className="size-3" /> Flagged
    </span>
  );
}

/**
 * The core visual idea: verified counts render solid & bold;
 * pending observations render hatched, dashed and provisional, next to the trusted value.
 */
export function CountDisplay({
  count,
  observed,
  low,
  size = "sm",
}: {
  count: number;
  observed?: number | null;
  low?: boolean;
  size?: "sm" | "lg";
}) {
  const big = size === "lg";
  return (
    <span className="inline-flex items-center gap-1.5 font-mono tabular-nums">
      <span
        className={cn(
          "verified-solid inline-flex items-center gap-1 rounded font-semibold",
          big ? "px-2 py-0.5 text-2xl" : "px-1.5 text-[13px]",
          low ? "text-warning" : "text-foreground",
          count === 0 && "text-critical",
        )}
        title="Verified count — committed to inventory"
      >
        {count}
      </span>
      {observed != null && observed !== count && (
        <span
          className={cn(
            "pending-hatch inline-flex items-center gap-0.5 rounded text-muted-foreground",
            big ? "px-2 py-0.5 text-base" : "px-1 text-[11px]",
          )}
          title="Observed by camera — awaiting reconciliation"
        >
          <span className="opacity-60">→</span>
          {observed}?
        </span>
      )}
    </span>
  );
}

export function ConfidenceBadge({ value }: { value: number }) {
  const tone = value >= 90 ? "healthy" : value >= 75 ? "warning" : "critical";
  return (
    <Tag tone={tone} className="font-mono tabular-nums">
      {value}%
    </Tag>
  );
}

export function healthTone(h: ZoneHealth) {
  return ({ healthy: "healthy", low: "warning", offline: "critical", pending: "neutral" } as const)[
    h
  ];
}

export function severityTone(s: SeverityTone) {
  return ({ critical: "critical", warning: "warning", info: "info" } as const)[s];
}

export function AnimatedNumber({
  value,
  suffix = "",
  className,
}: {
  value: number;
  suffix?: string;
  className?: string;
}) {
  const [display, setDisplay] = useState(value);
  const [flash, setFlash] = useState(0);
  const prev = useRef(value);
  useEffect(() => {
    if (prev.current === value) return;
    const start = prev.current;
    const t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - t0) / 500);
      setDisplay(Math.round((start + (value - start) * p) * 10) / 10);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    prev.current = value;
    setFlash((f) => f + 1);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return (
    <span
      key={flash}
      className={cn(
        "rounded px-0.5 -mx-0.5 font-mono tabular-nums",
        flash > 0 && "animate-value-flash",
        className,
      )}
    >
      {display}
      {suffix}
    </span>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
      <div className="grid size-10 place-items-center rounded-md border bg-surface-2">
        <Icon className="size-5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 max-w-sm text-[13px] text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function SkeletonRow({ className }: { className?: string }) {
  return <div className={cn("h-3 animate-pulse rounded bg-muted", className)} />;
}

export function Sparkline({ data, className }: { data: number[]; className?: string }) {
  const w = 100,
    h = 28;
  const max = Math.max(...data),
    min = Math.min(...data);
  const pts = data
    .map(
      (v, i) =>
        `${(i / (data.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * (h - 4) - 2}`,
    )
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={cn("h-7 w-full", className)}
      preserveAspectRatio="none"
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-0.5 text-[13px] text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
