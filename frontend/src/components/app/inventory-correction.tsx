import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import type { InventoryDto } from "@/lib/api";
import { operations } from "@/lib/api/operations";
import { useAuth } from "@/lib/auth";
import { ActionButton, Field, OperationError } from "./operation-fields";

export function InventoryCorrection({ item }: { item: InventoryDto }) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [snapshot, setSnapshot] = useState(item);
  const canAdjust = can("inventory.adjust_stock");
  const canSetThreshold = can("thresholds.manage");

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["inventory"] });
    await queryClient.invalidateQueries({ queryKey: ["products"] });
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  const correction = useMutation({
    mutationFn: (input: Parameters<typeof operations.correctInventory>[1]) =>
      operations.correctInventory(item.id, input),
    onSuccess: async (updated) => {
      setSnapshot(updated);
      toast.success("Starting quantity recorded");
      await refresh();
    },
  });

  const checkout = useMutation({
    mutationFn: (input: Parameters<typeof operations.checkoutInventory>[1]) =>
      operations.checkoutInventory(item.id, input),
    onSuccess: async (updated, input) => {
      setSnapshot(updated);
      toast.success(`${input.quantity} unit${input.quantity === 1 ? "" : "s"} checked out`);
      await refresh();
    },
  });

  const threshold = useMutation({
    mutationFn: (value: number) => operations.updateProductThreshold(item.product_id, value),
    onSuccess: async (product) => {
      toast.success(`Low-stock threshold set to ${product.low_stock_threshold}`);
      await refresh();
    },
  });

  if (!canAdjust && !canSetThreshold) return null;
  const stale = item.updated_at !== snapshot.updated_at;
  const checkoutBlocked =
    !snapshot.updated_at ||
    snapshot.current_quantity <= 0 ||
    snapshot.status === "unknown" ||
    snapshot.status === "detection_uncertain";

  return (
    <div className="space-y-4 rounded-xl border bg-surface-2/40 p-4">
      <div>
        <h3 className="text-sm font-semibold">Inventory controls</h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Set the starting count, record checkout sales, and keep the low-stock policy current.
          Every change is audited.
        </p>
      </div>

      {canSetThreshold && (
        <form
          className="space-y-3 rounded-lg border bg-background p-3"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            threshold.mutate(Number(data.get("threshold")));
          }}
        >
          <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Alert threshold
          </h4>
          <Field
            key={item.threshold}
            label="Generate a low-stock alert at or below"
            name="threshold"
            type="number"
            min={0}
            max={1000000}
            step={1}
            required
            defaultValue={item.threshold ?? 10}
          />
          <OperationError error={threshold.error} />
          <ActionButton type="submit" disabled={threshold.isPending}>
            {threshold.isPending ? "Saving threshold…" : "Save threshold"}
          </ActionButton>
        </form>
      )}

      {canAdjust && (
        <>
          <form
            className="space-y-3 rounded-lg border bg-background p-3"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              if (!snapshot.updated_at) return;
              correction.mutate({
                quantity: Number(data.get("quantity")),
                reason: String(data.get("reason")),
                expected_updated_at: snapshot.updated_at,
              });
            }}
          >
            <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Starting or physical count
            </h4>
            <p className="text-xs text-muted-foreground">
              Use this for the initial quantity, restocking, or a verified shelf correction.
            </p>
            <Field
              key={snapshot.updated_at}
              label="Verified quantity"
              name="quantity"
              type="number"
              min={0}
              max={1000000}
              step={1}
              required
              defaultValue={snapshot.current_quantity}
            />
            <Field
              label="Reason"
              name="reason"
              required
              minLength={5}
              maxLength={255}
              placeholder="Initial physical count"
            />
            <OperationError error={correction.error} />
            <ActionButton type="submit" disabled={correction.isPending || !snapshot.updated_at}>
              {correction.isPending ? "Recording…" : "Record quantity"}
            </ActionButton>
          </form>

          <form
            className="space-y-3 rounded-lg border border-primary/20 bg-primary/[0.03] p-3"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              if (!snapshot.updated_at) return;
              const reason = String(data.get("reason")).trim();
              checkout.mutate({
                quantity: Number(data.get("quantity")),
                ...(reason ? { reason } : {}),
                expected_updated_at: snapshot.updated_at,
              });
            }}
          >
            <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-primary">
              Check out stock
            </h4>
            <p className="text-xs text-muted-foreground">
              Subtract sold units from the committed quantity. Alerts and email delivery are
              evaluated automatically after checkout.
            </p>
            <Field
              key={`checkout-${snapshot.updated_at}`}
              label={`Units checked out · ${snapshot.current_quantity} available`}
              name="quantity"
              type="number"
              min={1}
              max={Math.max(1, snapshot.current_quantity)}
              step={1}
              required
              defaultValue={1}
              disabled={checkoutBlocked}
            />
            <Field
              label="Reason (optional)"
              name="reason"
              minLength={5}
              maxLength={255}
              placeholder="Customer checkout"
              disabled={checkoutBlocked}
            />
            {checkoutBlocked && (
              <p className="text-xs text-warning">
                Record a starting quantity before processing checkout sales.
              </p>
            )}
            <OperationError error={checkout.error} />
            <ActionButton type="submit" disabled={checkout.isPending || checkoutBlocked}>
              {checkout.isPending ? "Processing…" : "Check out units"}
            </ActionButton>
          </form>
        </>
      )}

      {stale && (
        <div className="space-y-2 rounded-lg border border-warning/30 bg-warning/[0.05] p-3">
          <p className="text-xs text-warning">
            This record changed while the controls were open. Refresh before another stock change.
          </p>
          <ActionButton
            onClick={() => {
              setSnapshot(item);
              correction.reset();
              checkout.reset();
              void refresh();
            }}
          >
            Use latest count ({item.current_quantity})
          </ActionButton>
        </div>
      )}
    </div>
  );
}
