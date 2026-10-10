import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import type { InventoryDto } from "@/lib/api";
import { operations } from "@/lib/api/operations";
import { useAuth } from "@/lib/auth";
import { ActionButton, Field, OperationError } from "./operation-fields";

export function InventoryCorrection({ item }: { item: InventoryDto }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [snapshot, setSnapshot] = useState(item);
  const save = useMutation({
    mutationFn: (input: Parameters<typeof operations.correctInventory>[1]) =>
      operations.correctInventory(item.id, input),
    onSuccess: async () => {
      toast.success("Correction recorded with your account and reason");
      await queryClient.invalidateQueries();
    },
  });
  if (user?.role !== "admin" && user?.role !== "manager") return null;
  return (
    <form
      className="space-y-3 rounded-md border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        if (!snapshot.updated_at) return;
        save.mutate({
          quantity: Number(data.get("quantity")),
          reason: String(data.get("reason")),
          expected_updated_at: snapshot.updated_at,
        });
      }}
    >
      <h3 className="text-sm font-medium">Record a physical count</h3>
      <p className="text-xs text-muted-foreground">
        Audited manual correction, not camera verification. A later reconciled observation may
        replace this count; this is not a persistent override.
      </p>
      <Field
        key={snapshot.updated_at}
        label="Correct quantity"
        name="quantity"
        type="number"
        min={0}
        max={1000000}
        step={1}
        required
        defaultValue={snapshot.current_quantity}
      />
      <Field
        label="Reason (required for the audit trail)"
        name="reason"
        required
        minLength={5}
        maxLength={255}
      />
      <OperationError error={save.error} />
      <ActionButton type="submit" disabled={save.isPending || !item.updated_at}>
        Record correction
      </ActionButton>
      {item.updated_at !== snapshot.updated_at && (
        <p className="text-xs text-warning">
          This record changed while the form was open. Review the latest count before saving.
        </p>
      )}
      {(save.isError || item.updated_at !== snapshot.updated_at) && (
        <ActionButton
          onClick={() => {
            setSnapshot(item);
            save.reset();
            void queryClient.invalidateQueries();
          }}
        >
          Use latest count ({item.current_quantity})
        </ActionButton>
      )}
    </form>
  );
}
