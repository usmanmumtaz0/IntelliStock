import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  History,
  PackagePlus,
  Plus,
  Search,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { api, ApiError, type InventoryDto } from "@/lib/api";
import {
  requests,
  requestLabels,
  submissionFromForm,
  type RequestKind,
  type OperationalRequest,
} from "@/lib/api/requests";
import { EmptyState, PageHeader, Panel, Tag } from "@/components/app/primitives";
import { ActionButton, Field, OperationError } from "@/components/app/operation-fields";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/_console/requests")({
  component: RequestsPage,
  head: () => ({ meta: [{ title: "Requests — IntelliStock" }] }),
});

const inputClass =
  "min-h-11 w-full rounded-lg border bg-background px-3 py-2 text-sm transition-colors focus:border-primary";

function dateLabel(value: string) {
  return new Date(/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + "Z").toLocaleString();
}

function statusTone(status: OperationalRequest["status"]) {
  return status === "approved" ? "healthy" : status === "rejected" ? "critical" : "warning";
}

function RequestsPage() {
  const { can } = useAuth();
  const client = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [inventoryOffset, setInventoryOffset] = useState(0);
  const [activityOffset, setActivityOffset] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | OperationalRequest["status"]>("all");
  const [search, setSearch] = useState("");
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
      setSubmitting(false);
      setFormVersion((version) => version + 1);
      setOffset(0);
      await client.invalidateQueries({ queryKey: ["requests"] });
      await client.invalidateQueries({ queryKey: ["operational-audit"] });
    },
    onError: (error) => toast.error(error.message),
  });

  const names = useMemo(
    () =>
      new Map(
        inventory.data?.map((item) => [
          item.id,
          `${item.name ?? "Product"} · ${zones.data?.find((zone) => zone.id === item.zone_id)?.name ?? "Shelf"}`,
        ]),
      ),
    [inventory.data, zones.data],
  );
  const counts = (rows.data ?? []).reduce(
    (result, row) => ({ ...result, [row.status]: result[row.status] + 1 }),
    { pending: 0, approved: 0, rejected: 0 },
  );
  const visibleRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (rows.data ?? []).filter((row) => {
      const matchesStatus = statusFilter === "all" || row.status === statusFilter;
      const matchesSearch =
        !term ||
        requestLabels[row.kind].toLowerCase().includes(term) ||
        row.reason.toLowerCase().includes(term) ||
        (names.get(row.inventory_id) ?? "").toLowerCase().includes(term);
      return matchesStatus && matchesSearch;
    });
  }, [rows.data, statusFilter, search, names]);

  return (
    <>
      <PageHeader
        title="Inventory requests"
        eyebrow="Controlled operations"
        icon={ClipboardList}
        description={
          can("requests.read_all")
            ? "Review verified counts, discrepancies and replenishment needs without bypassing authoritative inventory controls."
            : "Report shelf conditions and track decisions through a clear, auditable review workflow."
        }
        meta={
          <>
            <span className="console-stat-pill">
              <Clock3 className="size-3 text-warning" /> <strong>{counts.pending}</strong> pending
            </span>
            <span className="console-stat-pill">
              <CheckCircle2 className="size-3 text-healthy" /> <strong>{counts.approved}</strong>{" "}
              approved
            </span>
            <span className="console-stat-pill">
              <XCircle className="size-3 text-critical" /> <strong>{counts.rejected}</strong>{" "}
              rejected
            </span>
            <span className="console-stat-pill">
              <ShieldCheck className="size-3 text-primary" /> Audit protected
            </span>
          </>
        }
        actions={
          can("requests.submit") ? (
            <button
              onClick={() => {
                save.reset();
                setSubmitting(true);
              }}
              className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-[12px] font-semibold text-primary-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <Plus className="size-4" />
              New request
            </button>
          ) : undefined
        }
      />

      <RequestWorkflow />

      <Panel
        title={can("requests.read_all") ? "Review queue" : "My requests"}
        action={
          <span className="text-xs text-muted-foreground">
            {visibleRows.length} shown · refreshes every 15 seconds
          </span>
        }
      >
        <div className="mb-5 flex flex-col gap-3 rounded-xl border bg-surface-2/60 p-3 lg:flex-row lg:items-center lg:justify-between">
          <label className="relative block w-full lg:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <span className="sr-only">Search requests</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product, type or reason"
              className="h-10 w-full rounded-lg border bg-background pl-10 pr-3 text-sm focus:border-primary"
            />
          </label>
          <div className="flex flex-wrap gap-1 rounded-lg border bg-background p-1">
            {(["all", "pending", "approved", "rejected"] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={
                  statusFilter === status
                    ? "h-8 rounded-md bg-primary px-3 text-xs font-medium capitalize text-primary-foreground"
                    : "h-8 rounded-md px-3 text-xs font-medium capitalize text-muted-foreground hover:bg-accent"
                }
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <OperationError error={rows.error} />
        {rows.isLoading && (
          <div className="grid gap-3 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-40 animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
        )}
        {!rows.isLoading && !rows.error && !visibleRows.length && (
          <EmptyState
            icon={ClipboardCheck}
            title={rows.data?.length ? "No matching requests" : "No requests yet"}
            description={
              rows.data?.length
                ? "Change the search or status filter to see other requests."
                : "New count, discrepancy and restock requests will appear here with their review status."
            }
          />
        )}
        <div className="grid gap-4 lg:grid-cols-2">
          {visibleRows.map((row) => (
            <RequestCard
              key={`${row.id}-${row.status}`}
              row={row}
              name={names.get(row.inventory_id)}
            />
          ))}
        </div>
        <div className="mt-5 flex items-center justify-between border-t pt-4">
          <ActionButton
            disabled={!offset || rows.isFetching}
            onClick={() => setOffset((value) => Math.max(0, value - 50))}
          >
            Previous
          </ActionButton>
          <span className="text-xs text-muted-foreground">Page {offset / 50 + 1}</span>
          <ActionButton
            disabled={rows.data?.length !== 50 || rows.isFetching}
            onClick={() => setOffset((value) => value + 50)}
          >
            Next
          </ActionButton>
        </div>
      </Panel>

      {can("audit.read_own") && (
        <Panel
          title={
            <span className="flex items-center gap-2">
              <History className="size-4 text-primary" />
              {can("audit.read_operational") ? "Operational activity" : "My request activity"}
            </span>
          }
          className="mt-6"
        >
          <OperationError error={activity.error} />
          {activity.isLoading && <p role="status">Loading activity…</p>}
          {!activity.isLoading && !activity.error && !activity.data?.length && (
            <p className="text-sm text-muted-foreground">No request activity on this page.</p>
          )}
          <div className="divide-y rounded-xl border">
            {activity.data?.map((entry) => (
              <div
                key={entry.id}
                className="flex flex-col gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/[0.07] text-primary">
                    <History className="size-3.5" />
                  </span>
                  <div>
                    <p className="font-medium capitalize">{entry.action.replaceAll("_", " ")}</p>
                    <p className="text-xs text-muted-foreground">
                      {entry.resource_type} · {entry.outcome}
                    </p>
                  </div>
                </div>
                <time className="text-xs text-muted-foreground">{dateLabel(entry.timestamp)}</time>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <ActionButton
              disabled={!activityOffset || activity.isFetching}
              onClick={() => setActivityOffset((value) => Math.max(0, value - 50))}
            >
              Previous activity
            </ActionButton>
            <ActionButton
              disabled={activity.data?.length !== 50 || activity.isFetching}
              onClick={() => setActivityOffset((value) => value + 50)}
            >
              More activity
            </ActionButton>
          </div>
        </Panel>
      )}

      <RequestSubmissionDialog
        key={formVersion}
        open={submitting}
        onOpenChange={(open) => {
          if (!save.isPending) setSubmitting(open);
        }}
        inventory={inventory.data ?? []}
        inventoryLoading={inventory.isLoading}
        inventoryError={inventory.error || zones.error}
        names={names}
        inventoryOffset={inventoryOffset}
        setInventoryOffset={setInventoryOffset}
        pending={save.isPending}
        error={save.error}
        onSubmit={(input) => save.mutate(input)}
      />
    </>
  );
}

function RequestWorkflow() {
  const steps = [
    {
      icon: ClipboardCheck,
      title: "Physical count",
      copy: "Submit a count you checked in person. Only manager approval can update committed inventory.",
    },
    {
      icon: AlertTriangle,
      title: "Discrepancy",
      copy: "Report a mismatch, damaged stock or incorrect record for investigation. It never changes stock directly.",
    },
    {
      icon: PackagePlus,
      title: "Restock request",
      copy: "Ask the operations team to replenish a shelf. Completion is tracked separately from inventory correction.",
    },
  ];
  return (
    <section className="mb-6 rounded-2xl border border-primary/15 bg-primary/[0.035] p-4 sm:p-5">
      <div className="mb-4">
        <p className="text-sm font-semibold">How Requests protects inventory</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Requests coordinate work between staff and managers while keeping every decision
          permission checked and auditable.
        </p>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {steps.map(({ icon: Icon, title, copy }, index) => (
          <div key={title} className="flex gap-3 rounded-xl border bg-background/75 p-3.5">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-4" />
            </span>
            <div>
              <p className="text-xs font-semibold">
                <span className="mr-1 text-primary">0{index + 1}</span> {title}
              </p>
              <p className="mt-1 text-[11px] leading-5 text-muted-foreground">{copy}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RequestSubmissionDialog({
  open,
  onOpenChange,
  inventory,
  inventoryLoading,
  inventoryError,
  names,
  inventoryOffset,
  setInventoryOffset,
  pending,
  error,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  inventory: InventoryDto[];
  inventoryLoading: boolean;
  inventoryError: Error | null;
  names: Map<string, string>;
  inventoryOffset: number;
  setInventoryOffset: (value: number | ((value: number) => number)) => void;
  pending: boolean;
  error: Error | null;
  onSubmit: (input: ReturnType<typeof submissionFromForm>) => void;
}) {
  const [kind, setKind] = useState<RequestKind>("physical_count");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <span className="grid size-9 place-items-center rounded-xl bg-primary/10 text-primary">
              <ClipboardList className="size-4" />
            </span>
            New inventory request
          </DialogTitle>
          <DialogDescription>
            Describe verified shelf work or a condition that needs manager attention.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (!pending) onSubmit(submissionFromForm(new FormData(event.currentTarget), kind));
          }}
        >
          <fieldset disabled={pending} className="space-y-5 disabled:opacity-70">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-xs font-medium text-muted-foreground">
                Request type
                <select
                  className={inputClass}
                  value={kind}
                  onChange={(event) => setKind(event.target.value as RequestKind)}
                >
                  {Object.entries(requestLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2 text-xs font-medium text-muted-foreground">
                Product and shelf
                <select
                  name="inventory"
                  className={inputClass}
                  required
                  defaultValue=""
                  disabled={inventoryLoading || Boolean(inventoryError)}
                >
                  <option value="" disabled>
                    Choose inventory to check
                  </option>
                  {inventory.map((item) => (
                    <option key={item.id} value={item.id}>
                      {names.get(item.id)} · {item.current_quantity} recorded
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <OperationError error={inventoryError} />
            {inventoryLoading && (
              <p role="status" className="text-sm">
                Loading inventory…
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <ActionButton
                disabled={inventoryOffset === 0 || inventoryLoading}
                onClick={() => setInventoryOffset((value) => Math.max(0, value - 500))}
              >
                Previous products
              </ActionButton>
              <ActionButton
                disabled={inventory.length !== 500 || inventoryLoading}
                onClick={() => setInventoryOffset((value) => value + 500)}
              >
                More products
              </ActionButton>
            </div>
            {kind === "physical_count" && (
              <Field
                label="Count you physically verified"
                name="quantity"
                type="number"
                min={0}
                max={1000000}
                step={1}
                required
              />
            )}
            <label className="grid gap-2 text-xs font-medium text-muted-foreground">
              Reason or observations
              <textarea
                className={inputClass}
                name="reason"
                required
                minLength={5}
                maxLength={500}
                rows={4}
                placeholder="Describe what you checked, observed or need the team to do."
              />
            </label>
            <div className="flex gap-3 rounded-xl border border-primary/15 bg-primary/[0.04] p-3 text-xs leading-5 text-muted-foreground">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
              <p>
                Submission creates an auditable request. Only an approved physical count can update
                committed quantity; discrepancies and restock requests never change it directly.
              </p>
            </div>
            <OperationError error={error} />
            <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={pending}
                onClick={() => onOpenChange(false)}
                className="h-10 rounded-lg border px-4 text-sm font-medium hover:bg-accent"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={
                  pending || inventoryLoading || Boolean(inventoryError) || !inventory.length
                }
                className="h-10 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-50"
              >
                {pending ? "Submitting…" : "Submit for review"}
              </button>
            </div>
          </fieldset>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RequestCard({ row, name }: { row: OperationalRequest; name: string | undefined }) {
  const { can, user } = useAuth();
  const [reviewing, setReviewing] = useState(false);
  const icon =
    row.status === "approved" ? CheckCircle2 : row.status === "rejected" ? XCircle : Clock3;
  const StatusIcon = icon;
  return (
    <article className="flex h-full flex-col rounded-xl border bg-background p-4 transition-colors hover:border-primary/30">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/[0.07] text-primary">
            <StatusIcon className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold">{requestLabels[row.kind]}</p>
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {name ?? "Inventory item — load another product page for details"}
            </p>
          </div>
        </div>
        <Tag tone={statusTone(row.status)}>{row.status}</Tag>
      </div>

      <div className="mt-4 rounded-lg bg-surface-2/60 p-3">
        <p className="whitespace-pre-wrap break-words text-xs leading-5">{row.reason}</p>
        {row.quantity !== null && (
          <p className="mt-2 font-mono text-sm font-semibold">Submitted count: {row.quantity}</p>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span>{row.submitter_id === user?.userId ? "Your request" : "Team request"}</span>
        <time>{dateLabel(row.created_at)}</time>
      </div>
      {row.review_reason && (
        <div className="mt-3 border-t pt-3 text-xs">
          <p className="font-medium">Review decision</p>
          <p className="mt-1 text-muted-foreground">{row.review_reason}</p>
          {row.reviewed_at && (
            <time className="mt-1 block text-[11px] text-muted-foreground">
              Reviewed {dateLabel(row.reviewed_at)}
            </time>
          )}
        </div>
      )}
      {can("requests.review") && row.status === "pending" && (
        <button
          onClick={() => setReviewing(true)}
          className="mt-4 inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-primary/25 bg-primary/[0.05] text-xs font-semibold text-primary hover:bg-primary/10"
        >
          <ClipboardCheck className="size-3.5" />
          Review request
        </button>
      )}
      <ReviewDialog row={row} open={reviewing} onOpenChange={setReviewing} />
    </article>
  );
}

function ReviewDialog({
  row,
  open,
  onOpenChange,
}: {
  row: OperationalRequest;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { can } = useAuth();
  const client = useQueryClient();
  const [decision, setDecision] = useState<"approved" | "rejected">("rejected");
  const item = useQuery({
    queryKey: ["request-review-inventory", row.inventory_id],
    queryFn: () => api.inventoryRecord(row.inventory_id),
    enabled: open && can("inventory.read"),
    staleTime: 0,
  });
  const review = useMutation({
    mutationFn: (reason: string) => requests.review(row.id, { decision, reason }),
    onSuccess: async () => {
      onOpenChange(false);
      toast.success(decision === "approved" ? "Request approved" : "Request rejected");
      await client.invalidateQueries({ queryKey: ["requests"] });
      await client.invalidateQueries({ queryKey: ["inventory"] });
      await client.invalidateQueries({ queryKey: ["operational-audit"] });
    },
    onError: (error) => toast.error(error.message),
  });
  return (
    <Dialog open={open} onOpenChange={(next) => !review.isPending && onOpenChange(next)}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="size-5 text-primary" />
            Review {requestLabels[row.kind].toLowerCase()}
          </DialogTitle>
          <DialogDescription>
            Confirm the current record before making a permission-controlled decision.
          </DialogDescription>
        </DialogHeader>
        {item.isLoading && (
          <p role="status" className="text-sm">
            Checking current inventory…
          </p>
        )}
        <OperationError error={item.error} />
        {item.data && (
          <div className="grid grid-cols-2 gap-3 rounded-xl border bg-surface-2/60 p-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Current committed count</p>
              <p className="mt-1 font-mono text-xl font-semibold">{item.data.current_quantity}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Submitted count</p>
              <p className="mt-1 font-mono text-xl font-semibold">{row.quantity ?? "N/A"}</p>
            </div>
          </div>
        )}
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!review.isPending) {
              review.mutate(String(new FormData(event.currentTarget).get("review_reason")).trim());
            }
          }}
        >
          <label className="grid gap-2 text-xs font-medium text-muted-foreground">
            Decision
            <select
              className={inputClass}
              value={decision}
              onChange={(event) => setDecision(event.target.value as typeof decision)}
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
            <label className="flex items-start gap-3 rounded-xl border border-warning/20 bg-warning/[0.04] p-3 text-xs leading-5">
              <input type="checkbox" required className="mt-1" />
              <span>
                I verified this count. Approval will update authoritative inventory, and an outdated
                request will be rejected automatically.
              </span>
            </label>
          ) : (
            <p className="rounded-xl border p-3 text-xs leading-5 text-muted-foreground">
              This decision records the review without changing committed inventory.
            </p>
          )}
          <OperationError error={review.error} />
          {review.error instanceof ApiError && review.error.status === 409 && (
            <p
              role="alert"
              className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs"
            >
              This request was already reviewed or inventory changed. Refresh the queue and request
              a new physical count when necessary.
            </p>
          )}
          <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
            <button
              type="button"
              disabled={review.isPending}
              onClick={() => onOpenChange(false)}
              className="h-10 rounded-lg border px-4 text-sm font-medium hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                review.isPending ||
                (decision === "approved" && (!item.data || Boolean(item.error) || item.isFetching))
              }
              className={
                decision === "approved"
                  ? "h-10 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-50"
                  : "h-10 rounded-lg bg-critical px-5 text-sm font-semibold text-white disabled:opacity-50"
              }
            >
              {review.isPending
                ? "Saving decision…"
                : decision === "approved"
                  ? "Approve request"
                  : "Reject request"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
