import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { operations, type ProductDto } from "@/lib/api/operations";
import { useAuth } from "@/lib/auth";
import { Panel } from "./primitives";
import { ActionButton, Field, OperationError } from "./operation-fields";

export function ProductManagement() {
  const { user } = useAuth();
  const canWrite = user?.role === "admin" || user?.role === "manager";
  const queryClient = useQueryClient();
  const products = useQuery({ queryKey: ["products"], queryFn: operations.products });
  const [editing, setEditing] = useState<ProductDto | "new" | null>(null);
  const save = useMutation({
    mutationFn: ({
      input,
      id,
    }: {
      input: Parameters<typeof operations.saveProduct>[0];
      id?: string;
    }) => operations.saveProduct(input, id),
    onSuccess: async () => {
      setEditing(null);
      toast.success("Product saved");
      await queryClient.invalidateQueries();
    },
  });
  return (
    <Panel
      title="Product catalog & stock thresholds"
      className="xl:col-span-2"
      action={
        canWrite && (
          <ActionButton
            onClick={() => {
              save.reset();
              setEditing("new");
            }}
          >
            Add product
          </ActionButton>
        )
      }
    >
      <OperationError error={products.error} />
      {products.isLoading && <p className="text-sm">Loading products…</p>}
      {!products.isLoading && !products.error && !products.data?.length && (
        <p className="text-sm text-muted-foreground">
          No products yet. Create products before mapping model classes to shelves.
        </p>
      )}
      <div className="max-h-80 overflow-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b">
              <th className="p-2">SKU / product</th>
              <th>Low stock at</th>
              <th>Reorder point</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {products.data?.map((product) => (
              <tr key={product.id} className="border-b">
                <td className="p-2">
                  <span className="font-mono text-muted-foreground">{product.sku}</span>
                  <p className="mt-1 font-medium">{product.name}</p>
                </td>
                <td>{product.low_stock_threshold}</td>
                <td>{product.reorder_point}</td>
                <td>
                  {canWrite && (
                    <ActionButton
                      onClick={() => {
                        save.reset();
                        setEditing(product);
                      }}
                    >
                      Edit
                    </ActionButton>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <form
          key={typeof editing === "string" ? editing : editing.id}
          className="mt-4 grid gap-3 rounded-md border p-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const input = {
              sku: String(data.get("sku")),
              name: String(data.get("name")),
              description: String(data.get("description")) || null,
              low_stock_threshold: Number(data.get("threshold")),
              reorder_point: Number(data.get("reorder")),
            };
            save.mutate(typeof editing === "string" ? { input } : { input, id: editing.id });
          }}
        >
          <Field
            label="SKU (immutable)"
            name="sku"
            required
            maxLength={64}
            readOnly={editing !== "new"}
            defaultValue={editing === "new" ? "" : editing.sku}
          />
          <Field
            label="Product name"
            name="name"
            required
            maxLength={255}
            defaultValue={editing === "new" ? "" : editing.name}
          />
          <Field
            label="Low-stock threshold (inclusive)"
            name="threshold"
            type="number"
            min={0}
            step={1}
            required
            defaultValue={editing === "new" ? 10 : editing.low_stock_threshold}
          />
          <Field
            label="Reorder point (planning reference)"
            name="reorder"
            type="number"
            min={0}
            step={1}
            required
            defaultValue={editing === "new" ? 50 : editing.reorder_point}
          />
          <Field
            label="Description"
            name="description"
            maxLength={1024}
            defaultValue={editing === "new" ? "" : (editing.description ?? "")}
          />
          <p className="text-xs text-muted-foreground">
            Threshold changes re-evaluate trusted stock states. Uncertain and offline states remain
            unchanged.
          </p>
          <OperationError error={save.error} />
          <div className="flex gap-2">
            <ActionButton type="submit" disabled={save.isPending}>
              Save product
            </ActionButton>
            <ActionButton disabled={save.isPending} onClick={() => setEditing(null)}>
              Cancel
            </ActionButton>
          </div>
        </form>
      )}
    </Panel>
  );
}
