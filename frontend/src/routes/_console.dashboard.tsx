import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Cctv,
  AlertTriangle,
  ShieldCheck,
  Activity,
  ArrowRight,
  ArrowDown,
  ArrowUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { ago, confidencePercent, type ZoneHealth } from "@/lib/view-models";
import {
  Panel,
  LiveIndicator,
  AnimatedNumber,
  ConfidenceBadge,
  StatusDot,
  PageHeader,
  SkeletonRow,
  EmptyState,
} from "@/components/app/primitives";

export const Route = createFileRoute("/_console/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — IntelliStock" }] }),
  component: Dashboard,
});

const healthStyles: Record<ZoneHealth, string> = {
  healthy: "border-healthy/30 bg-healthy/[0.07]",
  low: "border-warning/40 bg-warning/[0.08]",
  offline: "border-critical/50 bg-critical/[0.08] scanline",
  pending: "pending-hatch",
};
const healthLabel: Record<ZoneHealth, string> = {
  healthy: "Verified",
  low: "Low stock",
  offline: "Camera offline",
  pending: "Reconciling",
};

function Dashboard() {
  const metrics = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: api.dashboardMetrics,
    refetchInterval: 30_000,
  });
  const store = useQuery({
    queryKey: queryKeys.store,
    queryFn: api.storeInfo,
    staleTime: 5 * 60_000,
  });
  const zones = useQuery({
    queryKey: queryKeys.zones,
    queryFn: api.zones,
    refetchInterval: 30_000,
  });
  const events = useQuery({
    queryKey: queryKeys.events,
    queryFn: () => api.events(30),
    refetchInterval: 30_000,
  });
  const inventory = useQuery({
    queryKey: queryKeys.inventory,
    queryFn: () => api.inventory(),
    refetchInterval: 30_000,
  });

  const productNames = new Map(
    inventory.data?.map((item) => [item.product_id, item.name ?? item.sku ?? item.product_id]),
  );
  const zoneNames = new Map(zones.data?.map((zone) => [zone.id, zone.name]));
  const aisles = [...new Set((zones.data ?? []).map((zone) => zone.aisle))].sort();
  const loading = metrics.isLoading || zones.isLoading || events.isLoading;
  const failed = metrics.error ?? zones.error ?? events.error;
  const values = metrics.data;
  const kpis = [
    {
      label: "Total SKUs tracked",
      value: values?.total_skus ?? 0,
      icon: Boxes,
      sub: `across ${zones.data?.length ?? 0} zones`,
      to: "/inventory" as const,
    },
    {
      label: "Active cameras",
      value: values?.active_cameras ?? 0,
      suffix: ` / ${values?.total_cameras ?? 0}`,
      icon: Cctv,
      sub: `${Math.max(0, (values?.total_cameras ?? 0) - (values?.active_cameras ?? 0))} disabled`,
      to: "/shelves" as const,
    },
    {
      label: "Low stock items",
      value: values?.low_stock_alerts ?? 0,
      icon: AlertTriangle,
      sub: "verified state",
      tone: "warning",
      to: "/alerts" as const,
    },
    {
      label: "Reconciliation confidence",
      value: values?.reconciliation_confidence ?? 0,
      suffix: "%",
      icon: ShieldCheck,
      sub: "average confidence",
      to: "/inventory" as const,
    },
  ];

  return (
    <>
      <PageHeader
        title={store.data?.name ?? "Store overview"}
        description={
          store.data
            ? `${store.data.location} · ${store.data.floor}`
            : "Verified inventory operations"
        }
        actions={<LiveIndicator label="Auto-refresh" />}
      />
      {failed && (
        <p
          role="alert"
          className="mb-4 rounded-md border border-critical/40 bg-critical/10 p-3 text-[12px] text-critical"
        >
          {failed instanceof Error ? failed.message : "Dashboard data could not be loaded"}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Link
            key={kpi.label}
            to={kpi.to}
            className="group rounded-lg border bg-surface p-4 transition-colors hover:border-primary/40"
          >
            <div className="flex items-center justify-between text-[12px] text-muted-foreground">
              <span>{kpi.label}</span>
              <kpi.icon className={cn("size-4", kpi.tone === "warning" && "text-warning")} />
            </div>
            <div className="mt-3 text-[28px] font-semibold leading-none tracking-tight">
              <AnimatedNumber value={kpi.value} />
              {kpi.suffix && (
                <span className="font-mono text-base text-muted-foreground">{kpi.suffix}</span>
              )}
            </div>
            <div className="mt-2 flex items-center justify-between text-[12px]">
              <span className="text-muted-foreground">{kpi.sub}</span>
              <ArrowRight className="size-3.5 opacity-0 group-hover:opacity-100" />
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Panel title="Zone status map">
            {zones.data?.length ? (
              <div className="space-y-2.5">
                {aisles.map((aisle) => (
                  <div key={aisle} className="flex items-stretch gap-2.5">
                    <div className="grid w-8 shrink-0 place-items-center rounded-md border bg-surface-2 font-mono text-[11px] text-muted-foreground">
                      {aisle}
                    </div>
                    <div className="grid flex-1 grid-cols-2 gap-2.5 lg:grid-cols-4">
                      {zones.data
                        .filter((zone) => zone.aisle === aisle)
                        .map((zone) => (
                          <Link
                            key={zone.id}
                            to="/inventory"
                            search={{ zone: zone.id }}
                            className={cn(
                              "rounded-md border p-2.5 hover:-translate-y-px",
                              healthStyles[zone.health],
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[12px] font-semibold">
                                {zone.name}
                              </span>
                              <StatusDot state={zone.health} pulse={zone.health === "offline"} />
                            </div>
                            <p className="mt-1 truncate text-[11px] text-muted-foreground">
                              {zone.label}
                            </p>
                            <div className="mt-2 flex items-center justify-between text-[11px]">
                              <span>{healthLabel[zone.health]}</span>
                              <span className="font-mono text-muted-foreground">
                                {Math.round(zone.confidence)}%
                              </span>
                            </div>
                          </Link>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <SkeletonRow key={index} />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Cctv}
                title="No zones configured"
                description="Add cameras and shelf zones to begin monitoring inventory."
              />
            )}
          </Panel>
          <Link
            to="/agent-activity"
            className="flex items-center gap-3 rounded-lg border border-primary/25 bg-primary/[0.06] p-4 hover:border-primary/50"
          >
            <Activity className="size-5 text-primary" />
            <div className="flex-1">
              <p className="text-[13px] font-medium">Agent activity</p>
              <p className="text-[12px] text-muted-foreground">
                Review deterministic insights, anomaly checks and notification runs.
              </p>
            </div>
            <ArrowRight className="size-4 text-primary" />
          </Link>
        </div>

        <Panel
          title="Verified activity"
          action={<LiveIndicator label="Recent" />}
          bodyClassName="p-0"
        >
          <div className="max-h-[560px] overflow-y-auto">
            {loading ? (
              Array.from({ length: 7 }).map((_, index) => (
                <div key={index} className="space-y-2 border-b px-4 py-3">
                  <SkeletonRow className="w-2/3" />
                  <SkeletonRow className="w-1/3" />
                </div>
              ))
            ) : events.data?.length ? (
              events.data.map((event) => {
                const down = (event.to ?? 0) < (event.from ?? 0);
                return (
                  <div key={event.id} className="border-b px-4 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[12.5px]">
                        <span className="font-mono text-muted-foreground">
                          Shelf {event.zone ? (zoneNames.get(event.zone) ?? event.zone) : "—"}
                        </span>{" "}
                        ·{" "}
                        {event.product
                          ? (productNames.get(event.product) ?? event.product)
                          : "Inventory"}
                      </p>
                      <ConfidenceBadge value={confidencePercent(event.confidence)} />
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1 font-mono">
                        {event.from ?? "—"}
                        {down ? (
                          <ArrowDown className="size-3 text-warning" />
                        ) : (
                          <ArrowUp className="size-3 text-healthy" />
                        )}
                        <strong className="text-foreground">{event.to ?? "—"}</strong>
                      </span>
                      <span>{ago(event.minAgo)}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center text-[12px] text-muted-foreground">
                No verified inventory events yet.
              </div>
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}
