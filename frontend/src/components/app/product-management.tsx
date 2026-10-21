import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, PackagePlus, Pencil, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";
import { operations, type ProductDto } from "@/lib/api/operations";
import { useAuth } from "@/lib/auth";
import { Panel, Tag } from "./primitives";
import { Field, OperationError } from "./operation-fields";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type EditingProduct = ProductDto | "new" | null;

export function ProductManagement() {
  const { can } = useAuth();
  const canWrite = can("products.update");
  const canThresholds = can("thresholds.manage");
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<EditingProduct>(null);
  const [search, setSearch] = useState("");
  const products = useQuery({
    queryKey: ["products"],
    queryFn: operations.products,
    enabled: can("products.read"),
  });
  const save = useMutation({
    mutationFn: ({
      input,
      id,
    }: {
      input: Parameters<typeof operations.saveProduct>[0];
      id?: string;
    }) => operations.saveProduct(input, id),
    onSuccess: async (product) => {
      setEditing(null);
      toast.success(`${product.name} saved`);
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      await queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
    onError: (error) => toast.error(error.message),
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return products.data ?? [];
    return (products.data ?? []).filter((product) =>
      [product.sku, product.name, product.brand, product.category, product.barcode]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    );
  }, [products.data, search]);
  const categorized = products.data?.filter((product) => product.category).length ?? 0;

  return (
    <>
      <Panel
        title={
          <span className="flex items-center gap-2">
            <Boxes className="size-4 text-primary" />
            Product catalog
          </span>
        }
        className="xl:col-span-2"
        action={
          can("products.create") && (
            <button
              onClick={() => {
                save.reset();
                setEditing("new");
              }}
              className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-[12px] font-semibold text-primary-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <PackagePlus className="size-4" />
              Add product
            </button>
          )
        }
      >
        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <CatalogMetric label="Catalog products" value={products.data?.length ?? 0} />
          <CatalogMetric label="Categorized" value={categorized} />
          <CatalogMetric
            label="Threshold policy"
            value={canThresholds ? "Admin managed" : "Read only"}
          />
        </div>

        <div className="mb-4 flex flex-col gap-3 rounded-xl border bg-surface-2/60 p-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="relative block w-full sm:max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <span className="sr-only">Search products</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, SKU, brand, category or barcode"
              className="h-10 w-full rounded-lg border bg-background pl-10 pr-3 text-sm focus:border-primary"
            />
          </label>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <ShieldCheck className="size-4 text-primary" />
            Threshold edits are permission controlled and audited
          </div>
        </div>

        <OperationError error={products.error} />
        {products.isLoading && (
          <div className="grid gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
        )}
        {!products.isLoading && !products.error && !products.data?.length && (
          <div className="rounded-xl border border-dashed px-6 py-12 text-center">
            <PackagePlus className="mx-auto size-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">Build your product catalog</p>
            <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-muted-foreground">
              Add products before mapping model classes to shelves or tracking committed stock.
            </p>
          </div>
        )}
        {!products.isLoading && Boolean(products.data?.length) && !filtered.length && (
          <div className="rounded-xl border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
            No products match “{search}”.
          </div>
        )}

        <div className="grid gap-3">
          {filtered.map((product) => (
            <article
              key={product.id}
              className="group grid gap-4 rounded-xl border bg-background p-4 transition-colors hover:border-primary/35 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
            >
              <div className="flex min-w-0 items-start gap-3">
                <div className="grid size-10 shrink-0 place-items-center rounded-xl border bg-primary/[0.07] text-primary">
                  <Boxes className="size-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold">{product.name}</p>
                    <Tag className="font-mono">{product.sku}</Tag>
                    {product.category && (
                      <Tag tone="info">{product.category.replaceAll("_", " ")}</Tag>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {[product.brand, product.variant, product.package_size]
                      .filter(Boolean)
                      .join(" · ") || "No brand or package details"}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="console-stat-pill">
                      <SlidersHorizontal className="size-3 text-warning" />
                      Low at <strong>{product.low_stock_threshold}</strong>
                    </span>
                    <span className="console-stat-pill">
                      Reorder at <strong>{product.reorder_point}</strong>
                    </span>
                    {product.barcode && (
                      <span className="console-stat-pill font-mono">{product.barcode}</span>
                    )}
                  </div>
                </div>
              </div>
              {canWrite && (
                <button
                  onClick={() => {
                    save.reset();
                    setEditing(product);
                  }}
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border px-3 text-xs font-medium transition-colors hover:border-primary/40 hover:bg-primary/[0.06] hover:text-primary"
                >
                  <Pencil className="size-3.5" />
                  Edit
                </button>
              )}
            </article>
          ))}
        </div>
      </Panel>

      <ProductDialog
        editing={editing}
        canThresholds={canThresholds}
        pending={save.isPending}
        error={save.error}
        onOpenChange={(open) => {
          if (!open && !save.isPending) setEditing(null);
        }}
        onSubmit={(input, id) => save.mutate(id ? { input, id } : { input })}
      />
    </>
  );
}

function CatalogMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border bg-surface-2/50 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function ProductDialog({
  editing,
  canThresholds,
  pending,
  error,
  onOpenChange,
  onSubmit,
}: {
  editing: EditingProduct;
  canThresholds: boolean;
  pending: boolean;
  error: Error | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: Parameters<typeof operations.saveProduct>[0], id?: string) => void;
}) {
  const isNew = editing === "new";
  const product = editing && editing !== "new" ? editing : null;
  return (
    <Dialog open={Boolean(editing)} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader className="pr-8">
          <DialogTitle className="flex items-center gap-2 text-xl">
            <span className="grid size-9 place-items-center rounded-xl bg-primary/10 text-primary">
              {isNew ? <PackagePlus className="size-4" /> : <Pencil className="size-4" />}
            </span>
            {isNew ? "Add product" : "Edit product"}
          </DialogTitle>
          <DialogDescription>
            {isNew
              ? "Create a catalog identity that can be mapped to shelves and vision detections."
              : "Update product identity and stock planning details. Changes are saved to the shared catalog."}
          </DialogDescription>
        </DialogHeader>

        {editing && (
          <form
            key={isNew ? "new" : product?.id}
            className="space-y-5"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              const input = {
                sku: String(data.get("sku")),
                name: String(data.get("name")),
                description: String(data.get("description")) || null,
                brand: String(data.get("brand")) || null,
                category: String(data.get("category")) || null,
                variant: String(data.get("variant")) || null,
                package_size: String(data.get("package_size")) || null,
                barcode: String(data.get("barcode")) || null,
                ...(canThresholds
                  ? {
                      low_stock_threshold: Number(data.get("threshold")),
                      reorder_point: Number(data.get("reorder")),
                    }
                  : {}),
              };
              onSubmit(input, product?.id);
            }}
          >
            <fieldset disabled={pending} className="space-y-5 disabled:opacity-70">
              <section className="rounded-xl border bg-surface-2/40 p-4">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold">Catalog identity</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Use stable values that match labels, invoices, and barcode records.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Product code / SKU"
                    name="sku"
                    required
                    maxLength={64}
                    readOnly={!isNew}
                    defaultValue={product?.sku ?? ""}
                  />
                  <Field
                    label="Product name"
                    name="name"
                    required
                    maxLength={255}
                    defaultValue={product?.name ?? ""}
                  />
                  <Field
                    label="Brand"
                    name="brand"
                    maxLength={100}
                    defaultValue={product?.brand ?? ""}
                  />
                  <Field
                    label="Category"
                    name="category"
                    maxLength={100}
                    placeholder="chips_snacks"
                    defaultValue={product?.category ?? ""}
                  />
                  <Field
                    label="Variant or flavor"
                    name="variant"
                    maxLength={100}
                    defaultValue={product?.variant ?? ""}
                  />
                  <Field
                    label="Package size"
                    name="package_size"
                    maxLength={64}
                    placeholder="250 ml"
                    defaultValue={product?.package_size ?? ""}
                  />
                  <Field
                    label="Barcode"
                    name="barcode"
                    maxLength={64}
                    defaultValue={product?.barcode ?? ""}
                  />
                  <Field
                    label="Description"
                    name="description"
                    maxLength={1024}
                    defaultValue={product?.description ?? ""}
                  />
                </div>
              </section>

              {canThresholds && (
                <section className="rounded-xl border border-warning/20 bg-warning/[0.04] p-4">
                  <div className="mb-4 flex items-start gap-3">
                    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-warning/10 text-warning">
                      <SlidersHorizontal className="size-4" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold">Stock policy</h3>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        Low stock is inclusive. Changing the threshold re-evaluates trusted
                        inventory while uncertain and offline states remain unchanged.
                      </p>
                    </div>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field
                      label="Low-stock threshold"
                      name="threshold"
                      type="number"
                      min={0}
                      max={1000000}
                      step={1}
                      required
                      defaultValue={product?.low_stock_threshold ?? 10}
                    />
                    <Field
                      label="Reorder point"
                      name="reorder"
                      type="number"
                      min={0}
                      max={1000000}
                      step={1}
                      required
                      defaultValue={product?.reorder_point ?? 50}
                    />
                  </div>
                </section>
              )}

              <OperationError error={error} />
              <div className="sticky bottom-0 flex flex-col-reverse gap-2 border-t bg-background/95 pt-4 backdrop-blur sm:flex-row sm:justify-end">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => onOpenChange(false)}
                  className="h-10 rounded-lg border px-4 text-sm font-medium hover:bg-accent disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={pending}
                  className="h-10 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-sm disabled:opacity-50"
                >
                  {pending ? "Saving product…" : isNew ? "Create product" : "Save changes"}
                </button>
              </div>
            </fieldset>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
