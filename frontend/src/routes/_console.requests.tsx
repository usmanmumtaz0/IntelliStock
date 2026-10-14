import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import {
  requests,
  requestLabels,
  submissionFromForm,
  type RequestKind,
  type OperationalRequest,
} from "@/lib/api/requests";
import { PageHeader, Panel, Tag } from "@/components/app/primitives";
import { ActionButton, Field, OperationError } from "@/components/app/operation-fields";

export const Route = createFileRoute("/_console/requests")({
  component: RequestsPage,
  head: () => ({ meta: [{ title: "Requests — IntelliStock" }] }),
});

const inputClass = "min-h-10 w-full rounded-md border bg-surface px-3 py-2 text-sm";
function dateLabel(value: string) {
  return new Date(/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + "Z").toLocaleString();
}

function RequestsPage() {
  const { can } = useAuth();
  const client = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [inventoryOffset, setInventoryOffset] = useState(0);
  const [activityOffset, setActivityOffset] = useState(0);
  const [kind, setKind] = useState<RequestKind>("physical_count");
  const [formVersion, setFormVersion] = useState(0);
  const rows = useQuery({
    queryKey: ["requests", offset],
    queryFn: () => requests.list(offset),
    refetchInterval: 15_000,
  });
  const inventory = useQuery({
    queryKey: ["request-inventory", inventoryOffset],
    queryFn: () => api.inventory({ limit: 500, offset: inventoryOffset }),
    enabled: can("inventory.read"),
  });
  const zones = useQuery({ queryKey: ["zones"], queryFn: api.zones, enabled: can("shelves.read") });
  const activity = useQuery({
    queryKey: ["operational-audit", activityOffset],
    queryFn: () => requests.activity(activityOffset),
    enabled: can("audit.read_own"),
    refetchInterval: 30_000,
  });
  const save = useMutation({
    mutationFn: requests.submit,
    onSuccess: async () => {
      toast.success("Request submitted for review. Inventory has not changed.");
      setFormVersion((v) => v + 1);
      setOffset(0);
      await client.invalidateQueries({ queryKey: ["requests"] });
      await client.invalidateQueries({ queryKey: ["operational-audit"] });
    },
  });
  const names = new Map(
    inventory.data?.map((item) => [
      item.id,
      `${item.name ?? "Product"} · ${zones.data?.find((z) => z.id === item.zone_id)?.name ?? "Shelf"}`,
    ]),
  );
  return (
    <>
      <PageHeader
        title="Inventory requests"
        description={
          can("requests.read_all")
            ? "Review submitted counts, discrepancies and restock requests. Inventory changes require an authorized review."
            : "Submit a shelf count, report a discrepancy or request a restock. Track your own requests here."
        }
      />
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
        {can("requests.submit") && (
          <Panel title="Submit a request">
            <OperationError error={inventory.error || zones.error} />
            <form
              key={`${formVersion}-${inventoryOffset}`}
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (!save.isPending)
                  save.mutate(submissionFromForm(new FormData(event.currentTarget), kind));
              }}
            >
              <label className="grid gap-2 text-sm">
                Request type
                <select
                  className={inputClass}
                  value={kind}
                  onChange={(e) => {
                    setKind(e.target.value as RequestKind);
                    save.reset();
                  }}
                >
                  {Object.entries(requestLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2 text-sm">
                Product and shelf
                <select
                  name="inventory"
                  className={inputClass}
                  required
                  defaultValue=""
                  disabled={inventory.isLoading || !!inventory.error}
                >
                  <option value="" disabled>
                    Choose inventory to check
                  </option>
                  {inventory.data?.map((item) => (
                    <option key={item.id} value={item.id}>
                      {names.get(item.id)} · {item.current_quantity} recorded
                    </option>
                  ))}
                </select>
              </label>
              {inventory.isLoading && <p role="status">Loading inventory…</p>}
              {inventory.data?.length === 0 && <p>No inventory available on this page.</p>}
              <div className="flex flex-wrap gap-2">
                <ActionButton
                  disabled={inventoryOffset === 0 || inventory.isFetching}
                  onClick={() => setInventoryOffset((n) => Math.max(0, n - 500))}
                >
                  Previous products
                </ActionButton>
                <ActionButton
                  disabled={inventory.data?.length !== 500 || inventory.isFetching}
                  onClick={() => setInventoryOffset((n) => n + 500)}
                >
                  More products
                </ActionButton>
              </div>
              {kind === "physical_count" && (
                <Field
                  label="Count you physically checked"
                  name="quantity"
                  type="number"
                  min={0}
                  max={1000000}
                  step={1}
                  required
                />
              )}
              <label className="grid gap-2 text-sm">
                Reason or observations
                <textarea
                  className={inputClass}
                  name="reason"
                  required
                  minLength={5}
                  maxLength={500}
                  rows={3}
                  placeholder="Describe what you checked or what needs attention."
                />
              </label>
              <p className="text-xs text-muted-foreground">
                Submitting does not change inventory. Only an approved physical count updates the
                recorded quantity.
              </p>
              <OperationError error={save.error} />
              <ActionButton
                type="submit"
                disabled={
                  save.isPending ||
                  inventory.isLoading ||
                  !!inventory.error ||
                  !inventory.data?.length
                }
              >
                {save.isPending ? "Submitting…" : "Submit for review"}
              </ActionButton>
            </form>
          </Panel>
        )}
        <Panel title={can("requests.read_all") ? "Requests to review" : "My requests"}>
          <OperationError error={rows.error} />
          {rows.isLoading && <p role="status">Loading requests…</p>}
          {!rows.isLoading && !rows.error && !rows.data?.length && (
            <p className="text-sm text-muted-foreground">No requests on this page.</p>
          )}
          <div className="space-y-4">
            {rows.data?.map((row) => (
              <RequestCard
                key={`${row.id}-${row.status}`}
                row={row}
                name={names.get(row.inventory_id)}
              />
            ))}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <ActionButton
              disabled={!offset || rows.isFetching}
              onClick={() => setOffset((n) => Math.max(0, n - 50))}
            >
              Previous
            </ActionButton>
            <span className="text-xs">Page {offset / 50 + 1}</span>
            <ActionButton
              disabled={rows.data?.length !== 50 || rows.isFetching}
              onClick={() => setOffset((n) => n + 50)}
            >
              Next
            </ActionButton>
          </div>
        </Panel>
      </div>
      {can("audit.read_own") && (
        <Panel
          title={can("audit.read_operational") ? "Operational activity" : "My request activity"}
          className="mt-6"
        >
          <OperationError error={activity.error} />
          {activity.isLoading && <p role="status">Loading activity…</p>}
          {!activity.isLoading && !activity.error && !activity.data?.length && (
            <p className="text-sm text-muted-foreground">No activity on this page.</p>
          )}
          <ul className="divide-y">
            {activity.data?.map((entry) => (
              <li key={entry.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm">
                <span>
                  {entry.action.replaceAll("_", " ")} · {entry.resource_type} · {entry.outcome}
                </span>
                <time>{dateLabel(entry.timestamp)}</time>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <ActionButton
              disabled={!activityOffset || activity.isFetching}
              onClick={() => setActivityOffset((n) => Math.max(0, n - 50))}
            >
              Previous activity
            </ActionButton>
            <ActionButton
              disabled={activity.data?.length !== 50 || activity.isFetching}
              onClick={() => setActivityOffset((n) => n + 50)}
            >
              More activity
            </ActionButton>
          </div>
        </Panel>
      )}
    </>
  );
}

function RequestCard({ row, name }: { row: OperationalRequest; name?: string | undefined }) {
  const { can, user } = useAuth();
  const client = useQueryClient();
  const [decision, setDecision] = useState<"approved" | "rejected">("rejected");
  const [expanded, setExpanded] = useState(false);
  const item = useQuery({
    queryKey: ["request-review-inventory", row.inventory_id],
    queryFn: () => api.inventoryRecord(row.inventory_id),
    enabled: expanded && can("inventory.read"),
    staleTime: 0,
  });
  const review = useMutation({
    mutationFn: (reason: string) => requests.review(row.id, { decision, reason }),
    onSuccess: async () => {
      toast.success("Review saved");
      await client.invalidateQueries();
    },
  });
  return (
    <article className="space-y-3 rounded-xl border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-medium">{requestLabels[row.kind]}</h2>
        <Tag>{row.status}</Tag>
      </div>
      <p className="text-sm">{name ?? "Inventory item — details may be on another product page"}</p>
      <p className="whitespace-pre-wrap break-words text-sm">{row.reason}</p>
      {row.quantity !== null && (
        <p className="text-sm font-medium">Submitted count: {row.quantity}</p>
      )}
      <p className="text-xs text-muted-foreground">
        {row.submitter_id === user?.userId ? "Your request" : "Team request"} ·{" "}
        {dateLabel(row.created_at)}
      </p>
      {row.review_reason && <p className="text-sm">Review: {row.review_reason}</p>}
      {row.reviewed_at && (
        <p className="text-xs text-muted-foreground">Reviewed {dateLabel(row.reviewed_at)}</p>
      )}
      {can("requests.review") && row.status === "pending" && (
        <details onToggle={(event) => setExpanded(event.currentTarget.open)}>
          <summary className="cursor-pointer text-sm font-medium text-primary">
            Review request
          </summary>
          {item.isLoading && <p role="status">Checking current inventory…</p>}
          <OperationError error={item.error} />
          {item.data && (
            <p className="mt-3 text-sm">
              {item.data.name ?? "Product"}: {item.data.current_quantity} currently recorded.{" "}
              <a
                className="text-primary underline"
                href={`/inventory?record=${encodeURIComponent(row.inventory_id)}`}
              >
                View inventory and shelf
              </a>
            </p>
          )}
          <form
            className="mt-3 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (!review.isPending)
                review.mutate(
                  String(new FormData(event.currentTarget).get("review_reason")).trim(),
                );
            }}
          >
            <label className="grid gap-1 text-sm">
              Decision
              <select
                className={inputClass}
                value={decision}
                onChange={(e) => setDecision(e.target.value as typeof decision)}
              >
                <option value="rejected">Reject</option>
                <option value="approved">Approve</option>
              </select>
            </label>
            <Field
              label="Review reason"
              name="review_reason"
              required
              minLength={5}
              maxLength={255}
            />
            {decision === "approved" && row.kind === "physical_count" ? (
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" required className="mt-1" />I verified this count. Approval
                will update inventory; outdated counts are rejected automatically.
              </label>
            ) : (
              <p className="text-xs text-muted-foreground">
                This decision records the review without changing inventory.
              </p>
            )}
            <OperationError error={review.error} />
            {review.error instanceof ApiError && review.error.status === 409 && (
              <p role="alert" className="text-sm">
                This request was already reviewed or inventory changed. Refresh the list; for an
                outdated count, reject it and request a new count.
              </p>
            )}
            <ActionButton
              type="submit"
              disabled={
                review.isPending ||
                (decision === "approved" && (!item.data || !!item.error || item.isFetching))
              }
            >
              {review.isPending ? "Saving…" : "Save review"}
            </ActionButton>
          </form>
        </details>
      )}
    </article>
  );
}
