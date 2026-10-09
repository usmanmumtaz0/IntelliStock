import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PackageMinus, CameraOff, Activity, Check, BellOff, X, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { api, type AlertDto } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";
import { ago, alertSeverityTone, minutesAgo } from "@/lib/view-models";
import {
  PageHeader,
  Tag,
  severityTone,
  EmptyState,
  SkeletonRow,
} from "@/components/app/primitives";

export const Route = createFileRoute("/_console/alerts")({
  head: () => ({ meta: [{ title: "Alerts — IntelliStock" }] }),
  component: Alerts,
});

function alertIcon(type: string) {
  if (type.includes("STOCK")) return PackageMinus;
  if (type.includes("CAMERA")) return CameraOff;
  return Activity;
}

function Alerts() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<"active" | "all">("active");
  const [typeFilter, setTypeFilter] = useState("all");
  const alerts = useQuery({
    queryKey: [...queryKeys.alerts, "all"],
    queryFn: () => api.alerts(),
    refetchInterval: 20_000,
  });
  const zones = useQuery({ queryKey: queryKeys.zones, queryFn: api.zones, staleTime: 30_000 });
  const inventory = useQuery({
    queryKey: queryKeys.inventory,
    queryFn: () => api.inventory(),
    staleTime: 30_000,
  });
  const canMutate = user?.role === "admin" || user?.role === "manager";

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
      queryClient.invalidateQueries({ queryKey: queryKeys.alertStats }),
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard }),
    ]);
  };
  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "acknowledge" | "resolve" | "dismiss" }) =>
      action === "acknowledge"
        ? api.acknowledgeAlert(id)
        : action === "resolve"
          ? api.resolveAlert(id)
          : api.dismissAlert(id),
    onSuccess: async (result) => {
      toast.success(result.message);
      await refresh();
    },
    onError: (error) => toast.error(error.message),
  });
  const acknowledgeAll = useMutation({
    mutationFn: api.acknowledgeAllAlerts,
    onSuccess: async (result) => {
      toast.success(result.message);
      await refresh();
    },
    onError: (error) => toast.error(error.message),
  });

  const zoneNames = new Map(zones.data?.map((zone) => [zone.id, zone.name]));
  const productNames = new Map(
    inventory.data?.map((item) => [item.product_id, { name: item.name, sku: item.sku }]),
  );
  const all = alerts.data?.data ?? [];
  const openCount = all.filter((alert) => alert.status === "OPEN").length;
  const activeStatuses = new Set(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "ESCALATED"]);
  const activeCount = all.filter((alert) => activeStatuses.has(alert.status)).length;
  const types = [...new Set(all.map((alert) => alert.alert_type))].sort();
  const list = all.filter(
    (alert) =>
      (statusFilter === "all" || activeStatuses.has(alert.status)) &&
      (typeFilter === "all" || alert.alert_type === typeFilter),
  );

  return (
    <>
      <PageHeader
        title="Alerts"
        description={`${openCount} open · ${activeCount} active · persistent alert lifecycle`}
        actions={
          canMutate && openCount > 0 ? (
            <button
              disabled={acknowledgeAll.isPending}
              onClick={() => acknowledgeAll.mutate()}
              className="h-8 rounded-md border px-3 text-[12px] hover:bg-accent disabled:opacity-50"
            >
              Acknowledge all
            </button>
          ) : undefined
        }
      />
      {alerts.error && (
        <p
          role="alert"
          className="mb-4 rounded-md border border-critical/40 bg-critical/10 p-3 text-[12px] text-critical"
        >
          {alerts.error.message}
        </p>
      )}
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="flex rounded-md border p-0.5 text-[12px]">
          {(["active", "all"] as const).map((value) => (
            <button
              key={value}
              onClick={() => setStatusFilter(value)}
              className={cn(
                "h-7 rounded px-2.5",
                statusFilter === value ? "bg-secondary font-medium" : "text-muted-foreground",
              )}
            >
              {value === "active" ? "Active" : "All"}
            </button>
          ))}
        </div>
        <select
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value)}
          className="h-8 rounded-md border bg-surface px-2 text-[12px]"
        >
          <option value="all">All types</option>
          {types.map((type) => (
            <option key={type} value={type}>
              {type.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {alerts.isLoading ? (
        <div className="space-y-3 rounded-lg border p-4">
          {Array.from({ length: 7 }).map((_, index) => (
            <SkeletonRow key={index} />
          ))}
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon={BellOff}
          title="No matching alerts"
          description="New persistent alerts will appear when verified state crosses a configured rule."
        />
      ) : (
        <div className="space-y-3">
          {list.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              zone={zoneNames.get(alert.zone_id) ?? alert.zone_id}
              product={productNames.get(alert.product_id)}
              canMutate={canMutate}
              pending={mutation.isPending}
              onAction={(action) => mutation.mutate({ id: alert.id, action })}
            />
          ))}
        </div>
      )}
    </>
  );
}

function AlertCard({
  alert,
  zone,
  product,
  canMutate,
  pending,
  onAction,
}: {
  alert: AlertDto;
  zone: string;
  product: { name: string | null; sku: string | null } | undefined;
  canMutate: boolean;
  pending: boolean;
  onAction: (action: "acknowledge" | "resolve" | "dismiss") => void;
}) {
  const tone = alertSeverityTone(alert.severity);
  const Icon = alertIcon(alert.alert_type);
  const closed =
    alert.status === "RESOLVED" || alert.status === "DISMISSED" || alert.status === "EXPIRED";
  return (
    <article
      className={cn(
        "flex items-start gap-3 rounded-lg border border-l-2 bg-surface p-3.5",
        tone === "critical"
          ? "border-l-critical"
          : tone === "warning"
            ? "border-l-warning"
            : "border-l-chart-2",
        closed && "opacity-65",
      )}
    >
      <div
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-md border",
          tone === "critical"
            ? "border-critical/40 bg-critical/10 text-critical"
            : tone === "warning"
              ? "border-warning/40 bg-warning/10 text-warning"
              : "text-chart-2",
        )}
      >
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[13px] font-medium">{alert.title}</p>
          <Tag tone={severityTone(tone)}>{alert.severity}</Tag>
          <Tag>{alert.status}</Tag>
        </div>
        <p className="mt-1 text-[12px] text-muted-foreground">
          {alert.description ?? alert.recommendation ?? "No additional details"}
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Tag className="font-mono">Zone {zone}</Tag>
          {product?.sku && <Tag className="font-mono">{product.sku}</Tag>}
          <span className="text-[11px] text-muted-foreground">
            {product?.name} · {ago(minutesAgo(alert.created_at))}
          </span>
        </div>
      </div>
      {canMutate && !closed && (
        <div className="flex shrink-0 gap-1">
          {(alert.status === "OPEN" || alert.status === "ESCALATED") && (
            <button
              disabled={pending}
              onClick={() => onAction("acknowledge")}
              title="Acknowledge"
              className="grid size-8 place-items-center rounded-md border hover:text-primary"
            >
              <Check className="size-3.5" />
            </button>
          )}
          <button
            disabled={pending}
            onClick={() => onAction("resolve")}
            title="Resolve"
            className="grid size-8 place-items-center rounded-md border hover:text-healthy"
          >
            <CheckCircle2 className="size-3.5" />
          </button>
          <button
            disabled={pending}
            onClick={() => onAction("dismiss")}
            title="Dismiss"
            className="grid size-8 place-items-center rounded-md border hover:text-critical"
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}
    </article>
  );
}
