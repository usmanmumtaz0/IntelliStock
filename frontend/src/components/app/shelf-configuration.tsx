import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, type CameraDto, type ZoneDto } from "@/lib/api";
import { operations, type ZoneInput } from "@/lib/api/operations";
import { ActionButton, Field, OperationError } from "./operation-fields";

export function ShelfConfiguration({
  camera,
  zones,
  onCameraSaved,
}: {
  camera: CameraDto;
  zones: ZoneDto[];
  onCameraSaved: (camera: CameraDto) => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState("");
  const cameraSave = useMutation({
    mutationFn: (input: Parameters<typeof api.updateCamera>[1]) =>
      api.updateCamera(camera.id, input),
    onSuccess: async (updated) => {
      onCameraSaved(updated);
      toast.success("Camera saved. Restart its vision worker.");
      await queryClient.invalidateQueries();
    },
  });
  const config = useQuery({
    queryKey: ["zone-config", selected],
    queryFn: () => operations.zoneConfiguration(selected),
    enabled: Boolean(selected),
  });
  return (
    <div className="space-y-4 rounded-md border p-3">
      <h3 className="text-sm font-medium">Camera & shelf configuration</h3>
      <p className="text-xs text-warning">
        Disable the camera and stop its vision worker before editing. After saving, enable the
        camera and restart the worker. No live image is available for calibration yet.
      </p>
      <form
        key={`${camera.id}-${camera.updated_at}`}
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          cameraSave.mutate({
            name: String(data.get("name")),
            location: String(data.get("location")),
            source_url: String(data.get("source")) || null,
            fps: Number(data.get("fps")),
            offline_timeout_seconds: Number(data.get("timeout")),
          });
        }}
      >
        <Field
          label="Camera name"
          name="name"
          required
          defaultValue={camera.name}
          maxLength={255}
        />
        <Field
          label="Location"
          name="location"
          required
          defaultValue={camera.location}
          maxLength={255}
        />
        <Field
          label="Source URL or local path (may contain credentials)"
          name="source"
          type="password"
          autoComplete="off"
          defaultValue={camera.source_url ?? ""}
          maxLength={512}
        />
        <Field
          label="Target FPS"
          name="fps"
          type="number"
          min={1}
          max={30}
          required
          defaultValue={camera.fps}
        />
        <Field
          label="Offline timeout (seconds)"
          name="timeout"
          type="number"
          min={10}
          max={300}
          required
          defaultValue={camera.offline_timeout_seconds}
        />
        <ActionButton type="submit" disabled={cameraSave.isPending || camera.is_active}>
          Save camera
        </ActionButton>
        <OperationError error={cameraSave.error} />
      </form>
      <label className="grid gap-1 text-xs">
        Shelf zone
        <select
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          className="h-9 rounded-md border bg-background px-2"
        >
          <option value="">New shelf zone</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
      </label>
      <OperationError error={config.error} />
      {selected && config.isLoading ? (
        <p className="text-xs">Loading configuration…</p>
      ) : (
        (!selected || config.data) && (
          <ZoneEditor
            key={selected || "new"}
            camera={camera}
            initial={selected ? config.data : undefined}
            id={selected}
          />
        )
      )}
    </div>
  );
}

function ZoneEditor({
  camera,
  initial,
  id,
}: {
  camera: CameraDto;
  initial: ZoneInput | undefined;
  id: string;
}) {
  const queryClient = useQueryClient();
  const products = useQuery({ queryKey: ["products"], queryFn: operations.products });
  const [points, setPoints] = useState<[number, number][]>(
    initial?.polygon ?? [
      [0.1, 0.1],
      [0.9, 0.1],
      [0.9, 0.9],
      [0.1, 0.9],
    ],
  );
  const [mappings, setMappings] = useState<ZoneInput["products"]>(initial?.products ?? []);
  const save = useMutation({
    mutationFn: (input: ZoneInput) => operations.saveZone(input, id || undefined),
    onSuccess: async () => {
      toast.success("Shelf saved. Enable the camera and restart its vision worker.");
      await queryClient.invalidateQueries();
    },
  });
  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        save.mutate({
          camera_id: camera.id,
          name: String(data.get("zone-name")),
          description: String(data.get("description")) || null,
          polygon: points,
          products: mappings,
          detection_confidence_threshold: Number(data.get("confidence")),
        });
      }}
    >
      <fieldset
        disabled={camera.is_active || save.isPending}
        className="space-y-3 disabled:opacity-60"
      >
        <Field
          label="Zone name"
          name="zone-name"
          required
          maxLength={255}
          defaultValue={initial?.name ?? ""}
        />
        <Field
          label="Description"
          name="description"
          maxLength={512}
          defaultValue={initial?.description ?? ""}
        />
        <Field
          label="Detection confidence floor"
          name="confidence"
          type="number"
          min={0.6}
          max={1}
          step={0.01}
          required
          defaultValue={initial?.detection_confidence_threshold ?? 0.6}
        />
        <p className="text-xs text-muted-foreground">
          ROI preview (normalized coordinates, not a camera image). Enter corners in perimeter
          order. Model class IDs must match your final trained model.
        </p>
        <svg
          viewBox="0 0 100 100"
          role="img"
          aria-label="Shelf polygon preview"
          className="h-40 w-full rounded-md border bg-secondary"
        >
          <polygon
            points={points.map((p) => `${p[0] * 100},${p[1] * 100}`).join(" ")}
            className="fill-primary/20 stroke-primary"
            strokeWidth="1"
          />
        </svg>
        {points.map((point, index) => (
          <div key={index} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
            {([0, 1] as const).map((axis) => (
              <Field
                key={axis}
                label={`Point ${index + 1} ${axis === 0 ? "X" : "Y"}`}
                type="number"
                min={0}
                max={1}
                step={0.001}
                required
                value={point[axis]}
                onChange={(event) =>
                  setPoints(
                    points.map((p, i) =>
                      i === index
                        ? axis === 0
                          ? [Number(event.target.value), p[1]]
                          : [p[0], Number(event.target.value)]
                        : p,
                    ),
                  )
                }
              />
            ))}
            <ActionButton
              disabled={points.length <= 3}
              onClick={() => setPoints(points.filter((_, i) => i !== index))}
            >
              Remove
            </ActionButton>
          </div>
        ))}
        <ActionButton
          disabled={points.length >= 32}
          onClick={() => setPoints([...points, [0.5, 0.5]])}
        >
          Add corner
        </ActionButton>
        <h4 className="text-xs font-medium">Model class → product mapping</h4>
        <OperationError error={products.error} />
        {mappings.map((mapping, index) => (
          <div key={index} className="space-y-2 rounded-md border p-2">
            <Field
              label="Model class ID"
              type="number"
              min={0}
              step={1}
              required
              value={mapping.class_id}
              onChange={(event) =>
                setMappings(
                  mappings.map((m, i) =>
                    i === index ? { ...m, class_id: Number(event.target.value) } : m,
                  ),
                )
              }
            />
            <label className="grid gap-1 text-xs">
              Product
              <select
                required
                value={mapping.product_id}
                className="h-9 rounded-md border bg-background px-2"
                onChange={(event) =>
                  setMappings(
                    mappings.map((m, i) =>
                      i === index ? { ...m, product_id: event.target.value } : m,
                    ),
                  )
                }
              >
                <option value="">Select a product</option>
                {products.data?.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.sku} · {product.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={mapping.allow_empty}
                onChange={(event) =>
                  setMappings(
                    mappings.map((m, i) =>
                      i === index ? { ...m, allow_empty: event.target.checked } : m,
                    ),
                  )
                }
              />
              Allow empty shelf to commit zero (calibrated ROI only)
            </label>
            <ActionButton onClick={() => setMappings(mappings.filter((_, i) => i !== index))}>
              Remove mapping
            </ActionButton>
          </div>
        ))}
        <div className="flex gap-2">
          <ActionButton
            onClick={() =>
              setMappings([...mappings, { class_id: 0, product_id: "", allow_empty: false }])
            }
          >
            Add mapping
          </ActionButton>
          <ActionButton type="submit" disabled={!mappings.length || save.isPending}>
            Save shelf
          </ActionButton>
        </div>
      </fieldset>
      <OperationError error={save.error} />
    </form>
  );
}
