import { useMemo } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Search, PackageSearch } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, type InventoryDto } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import {
  ago,
  confidencePercent,
  inventoryTrustState,
  minutesAgo,
  type ReconStatus,
} from "@/lib/view-models";
import {
  PageHeader,
  ReconBadge,
  CountDisplay,
  Panel,
  Sparkline,
  EmptyState,
  Tag,
  SkeletonRow,
  ConfidenceBadge,
} from "@/components/app/primitives";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

type SearchParams = {
  q?: string | undefined;
  zone?: string | undefined;
  status?: ReconStatus | undefined;
  sku?: string | undefined;
};

export const Route = createFileRoute("/_console/inventory")({
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    q: typeof search["q"] === "string" && search["q"] ? search["q"] : undefined,
    zone: typeof search["zone"] === "string" && search["zone"] ? search["zone"] : undefined,
    status:
      search["status"] === "verified" ||
      search["status"] === "pending" ||
      search["status"] === "flagged"
        ? search["status"]
        : undefined,
    sku: typeof search["sku"] === "string" && search["sku"] ? search["sku"] : undefined,
  }),
  head: () => ({ meta: [{ title: "Inventory — IntelliStock" }] }),
  component: Inventory,
});

function Inventory() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/inventory" });
  const setSearch = (patch: Partial<SearchParams>) =>
    navigate({ search: (previous) => ({ ...previous, ...patch }), replace: true });
  const inventory = useQuery({
    queryKey: [...queryKeys.inventory, search.zone],
    queryFn: () => api.inventory({ zone_id: search.zone }),
    refetchInterval: 30_000,
  });
  const zones = useQuery({ queryKey: queryKeys.zones, queryFn: api.zones, staleTime: 30_000 });

  const rows = useMemo(() => {
    const query = (search.q ?? "").trim().toLowerCase();
    return (inventory.data ?? []).filter((item) => {
      const trust = inventoryTrustState(item);
      return (
        (!search.status || trust === search.status) &&
        (!query ||
          item.sku?.toLowerCase().includes(query) ||
          item.name?.toLowerCase().includes(query))
      );
    });
  }, [inventory.data, search.q, search.status]);

  const selected = inventory.data?.find((item) => item.sku === search.sku);
  const counts = (inventory.data ?? []).reduce<Record<ReconStatus, number>>(
    (result, item) => {
      result[inventoryTrustState(item)] += 1;
      return result;
    },
    { verified: 0, pending: 0, flagged: 0 },
  );
  const zoneName = new Map(zones.data?.map((zone) => [zone.id, zone.name]));

  return (
    <>
      <PageHeader
        title="Inventory"
        description="Verified quantities remain authoritative while new camera observations are reconciled."
      />
      {inventory.error && (
        <p
          role="alert"
          className="mb-4 rounded-md border border-critical/40 bg-critical/10 p-3 text-[12px] text-critical"
        >
          {inventory.error.message}
        </p>
      )}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex h-8 w-64 items-center gap-2 rounded-md border bg-surface px-2.5">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            value={search.q ?? ""}
            onChange={(event) => setSearch({ q: event.target.value || undefined })}
            placeholder="Search SKU or product"
            className="flex-1 bg-transparent text-[12px] outline-none"
          />
        </div>
        <select
          value={search.zone ?? ""}
          onChange={(event) => setSearch({ zone: event.target.value || undefined, sku: undefined })}
          className="h-8 rounded-md border bg-surface px-2 text-[12px] outline-none"
        >
          <option value="">All zones</option>
          {zones.data?.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name} · {zone.label}
            </option>
          ))}
        </select>
        <div className="flex rounded-md border p-0.5 text-[12px]">
          {([undefined, "verified", "pending", "flagged"] as const).map((status) => (
            <button
              key={status ?? "all"}
              onClick={() => setSearch({ status })}
              className={cn(
                "h-7 rounded px-2.5 capitalize",
                search.status === status ? "bg-secondary font-medium" : "text-muted-foreground",
              )}
            >
              {status ?? "All"}
              {status && <span className="ml-1 font-mono">{counts[status]}</span>}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[12px] text-muted-foreground">{rows.length} records</span>
      </div>

      <Panel bodyClassName="p-0">
        {inventory.isLoading ? (
          <div className="space-y-4 p-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <SkeletonRow key={index} />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={PackageSearch}
              title="No matching inventory"
              description="Configure products and shelf zones or clear the current filters."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="border-b bg-surface-2/50 text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  {[
                    "SKU",
                    "Product",
                    "Quantity",
                    "Zone",
                    "Trust",
                    "Stock state",
                    "Confidence",
                    "Updated",
                  ].map((label) => (
                    <th key={label} className="whitespace-nowrap px-4 py-2 text-left font-medium">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <InventoryRow
                    key={item.id}
                    item={item}
                    zone={zoneName.get(item.zone_id) ?? item.zone_id}
                    selected={search.sku === item.sku}
                    onSelect={() => item.sku && setSearch({ sku: item.sku })}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <InventoryDetails
        item={selected}
        zone={selected ? (zoneName.get(selected.zone_id) ?? selected.zone_id) : ""}
        onClose={() => setSearch({ sku: undefined })}
      />
    </>
  );
}

function InventoryRow({
  item,
  zone,
  selected,
  onSelect,
}: {
  item: InventoryDto;
  zone: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const trust = inventoryTrustState(item);
  return (
    <tr
      onClick={onSelect}
      className={cn(
        "cursor-pointer border-b last:border-0 hover:bg-accent/50",
        selected && "bg-accent/60",
        trust === "pending" && "bg-pending/[0.04]",
      )}
    >
      <td className="px-4 py-2 font-mono text-[12px] text-muted-foreground">{item.sku ?? "—"}</td>
      <td className="px-4 py-2">{item.name ?? "Unnamed product"}</td>
      <td className="px-4 py-2">
        <CountDisplay
          count={item.current_quantity}
          observed={item.pending_quantity}
          low={item.status === "low_stock" || item.status === "out_of_stock"}
        />
      </td>
      <td className="px-4 py-2 font-mono text-[12px]">{zone}</td>
      <td className="px-4 py-2">
        <ReconBadge status={trust} />
      </td>
      <td className="px-4 py-2">
        <Tag
          tone={
            item.status === "out_of_stock" || item.status === "camera_offline"
              ? "critical"
              : item.status === "low_stock" || item.status === "detection_uncertain"
                ? "warning"
                : "healthy"
          }
        >
          {item.status.replaceAll("_", " ")}
        </Tag>
      </td>
      <td className="px-4 py-2">
        <ConfidenceBadge value={confidencePercent(item.confidence)} />
      </td>
      <td className="px-4 py-2 text-[12px] text-muted-foreground">
        {ago(minutesAgo(item.updated_at))}
      </td>
    </tr>
  );
}

function InventoryDetails({
  item,
  zone,
  onClose,
}: {
  item: InventoryDto | undefined;
  zone: string;
  onClose: () => void;
}) {
  const history = useQuery({
    queryKey: [...queryKeys.history, item?.zone_id, item?.product_id],
    queryFn: () => api.inventoryHistory(item!.zone_id, item!.product_id),
    enabled: Boolean(item),
  });
  const points = [...(history.data?.data ?? [])].reverse().map((record) => record.new_quantity);
  return (
    <Sheet open={Boolean(item)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {item && (
          <>
            <SheetHeader>
              <p className="font-mono text-[11px] text-muted-foreground">
                {item.sku ?? item.product_id} · Zone {zone}
              </p>
              <SheetTitle className="text-base">{item.name ?? "Inventory details"}</SheetTitle>
            </SheetHeader>
            <div className="space-y-5 px-4 pb-6">
              <div className="flex items-end gap-4">
                <div>
                  <p className="mb-1 text-[11px] text-muted-foreground">Verified quantity</p>
                  <CountDisplay
                    count={item.current_quantity}
                    observed={item.pending_quantity}
                    size="lg"
                  />
                </div>
                <ReconBadge status={inventoryTrustState(item)} />
              </div>
              <div className="rounded-md border bg-surface-2 p-3">
                <div className="mb-2 flex justify-between text-[11px] text-muted-foreground">
                  <span>Committed history</span>
                  <span className="font-mono">threshold {item.threshold ?? "—"}</span>
                </div>
                {points.length > 1 ? (
                  <Sparkline data={points} className="h-16 text-primary" />
                ) : (
                  <p className="py-4 text-center text-[12px] text-muted-foreground">
                    Not enough history yet.
                  </p>
                )}
              </div>
              <div>
                <p className="mb-2 text-[12px] font-medium">Event history</p>
                <ol className="relative space-y-3 border-l pl-4">
                  {history.data?.data.map((record) => (
                    <li key={record.id} className="relative">
                      <span className="absolute -left-[21px] top-1 size-2.5 rounded-full bg-verified" />
                      <p className="text-[12px]">
                        {record.change_type.replaceAll("_", " ")}{" "}
                        <span className="font-mono">
                          {record.previous_quantity} → {record.new_quantity}
                        </span>
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {ago(minutesAgo(record.created_at))} · confidence{" "}
                        {confidencePercent(record.confidence)}%
                      </p>
                    </li>
                  ))}
                </ol>
                {history.isLoading && <SkeletonRow />}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
