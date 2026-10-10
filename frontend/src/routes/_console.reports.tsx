import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { reporting } from "@/lib/api/reporting";
import { PageHeader, Panel } from "@/components/app/primitives";
import { ActionButton, OperationError } from "@/components/app/operation-fields";

export const Route = createFileRoute("/_console/reports")({
  component: Reports,
  head: () => ({ meta: [{ title: "Reports — IntelliStock" }] }),
});

function Reports() {
  const [days, setDays] = useState(7);
  const [zone, setZone] = useState("");
  const zones = useQuery({ queryKey: ["zones"], queryFn: api.zones });
  const summary = useQuery({
    queryKey: ["reports", days, zone],
    queryFn: () => reporting.summary(days, zone),
    refetchInterval: 30_000,
  });
  const download = useMutation({
    mutationFn: (kind: "inventory" | "history") => reporting.export(kind, days, zone),
    onSuccess: (csv, kind) => {
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `intellistock-${kind}.csv`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
  return (
    <>
      <PageHeader
        title="Operational reports"
        description="Committed inventory and recorded changes. No inferred sales or model-generated totals."
      />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-xs">
          History period
          <select
            className="h-9 rounded border bg-surface px-3"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            {[1, 7, 30, 90].map((value) => (
              <option key={value} value={value}>
                {value} days
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-xs">
          Shelf zone
          <select
            className="h-9 rounded border bg-surface px-3"
            value={zone}
            onChange={(event) => setZone(event.target.value)}
          >
            <option value="">All shelves</option>
            {zones.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.camera_name}
              </option>
            ))}
          </select>
        </label>
        <ActionButton disabled={download.isPending} onClick={() => download.mutate("inventory")}>
          Export current inventory
        </ActionButton>
        <ActionButton disabled={download.isPending} onClick={() => download.mutate("history")}>
          Export change history
        </ActionButton>
      </div>
      <OperationError error={summary.error || download.error || zones.error} />
      {summary.isLoading && <p className="text-sm">Loading report…</p>}
      {summary.data && (
        <>
          <p className="mb-4 text-xs text-muted-foreground">
            Generated {new Date(summary.data.generated_at).toLocaleString()} · {summary.data.note}
          </p>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["Shelf/product records", summary.data.inventory_records],
              ["Distinct products", summary.data.distinct_products],
              ["Committed units", summary.data.committed_units],
              ["Active alerts", summary.data.active_alerts],
            ].map(([label, value]) => (
              <Panel key={label} title={label}>
                <p className="font-mono text-2xl">{value}</p>
              </Panel>
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Current stock states">
              {Object.entries(summary.data.states).map(([state, count]) => (
                <div key={state} className="flex justify-between border-b py-2 text-sm">
                  <span className="capitalize">{state.replaceAll("_", " ")}</span>
                  <span className="font-mono">{count}</span>
                </div>
              ))}
              {!summary.data.inventory_records && (
                <p className="text-sm text-muted-foreground">
                  No inventory records in this selection.
                </p>
              )}
            </Panel>
            <Panel title={`Recorded changes · last ${days} days`}>
              {Object.entries(summary.data.change_types).map(([type, count]) => (
                <div key={type} className="flex justify-between border-b py-2 text-sm">
                  <span>{type.replaceAll("_", " ")}</span>
                  <span className="font-mono">{count}</span>
                </div>
              ))}
              {!summary.data.history_changes && (
                <p className="text-sm text-muted-foreground">
                  No committed changes in this period.
                </p>
              )}
            </Panel>
          </div>
        </>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
        Exports are limited to 10,000 rows; narrow the shelf or history period for larger datasets.
        Inventory export is current state, independent of history period.
      </p>
    </>
  );
}
