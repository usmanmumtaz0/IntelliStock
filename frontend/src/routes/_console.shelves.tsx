import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CameraOff, Cctv, Plus, Trash2, Power, Layers3, Radio, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { api, type CameraDto, type CameraInput } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";
import { inventoryTrustState } from "@/lib/view-models";
import {
  PageHeader,
  StatusDot,
  Tag,
  CountDisplay,
  ReconBadge,
  EmptyState,
  SkeletonRow,
} from "@/components/app/primitives";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ShelfConfiguration } from "@/components/app/shelf-configuration";

export const Route = createFileRoute("/_console/shelves")({
  head: () => ({ meta: [{ title: "Shelves & Cameras — IntelliStock" }] }),
  component: Shelves,
});

function CameraPreview({
  camera,
  zones,
  large,
}: {
  camera: CameraDto;
  zones: string[];
  large?: boolean;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md border bg-sidebar grid-bg",
        large ? "aspect-video" : "aspect-[16/9]",
        !camera.is_active && "border-critical/40",
      )}
    >
      {camera.is_active ? (
        <>
          <div className="absolute inset-0 scanline" />
          {zones.map((zone, index) => (
            <div
              key={zone}
              className="absolute rounded-sm border border-primary/70"
              style={{
                left: `${8 + index * (84 / Math.max(zones.length, 1))}%`,
                top: "22%",
                width: `${78 / Math.max(zones.length, 1)}%`,
                height: "56%",
              }}
            >
              <span className="absolute -top-4 left-0 rounded-sm bg-primary px-1 font-mono text-[9px] text-primary-foreground">
                ROI {zone}
              </span>
            </div>
          ))}
          <div className="absolute left-2 top-2 rounded bg-background/80 px-1.5 py-0.5 font-mono text-[10px]">
            <StatusDot state="live" /> ENABLED · {camera.fps}fps target
          </div>
        </>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-critical/[0.06]">
          <CameraOff className="size-6 text-critical" />
          <span className="font-mono text-[11px] text-critical">CAMERA DISABLED</span>
        </div>
      )}
      <span className="absolute bottom-2 left-2 rounded bg-background/80 px-1.5 py-0.5 text-[10px] text-muted-foreground">
        Illustrative layout · not live video or calibrated ROI
      </span>
      <span className="absolute top-2 right-2 rounded bg-background/80 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
        {camera.id.slice(0, 8)}
      </span>
    </div>
  );
}

function Shelves() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<CameraDto | null>(null);
  const [adding, setAdding] = useState(false);
  const canWrite = can("cameras.manage");
  const canDelete = can("cameras.manage");
  const cameras = useQuery({
    queryKey: queryKeys.cameras,
    queryFn: api.cameras,
    refetchInterval: 30_000,
  });
  const zones = useQuery({ queryKey: queryKeys.zones, queryFn: api.zones, staleTime: 30_000 });
  const inventory = useQuery({
    queryKey: queryKeys.inventory,
    queryFn: () => api.inventory(),
    staleTime: 30_000,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: queryKeys.cameras });
  const createCamera = useMutation({
    mutationFn: api.createCamera,
    onSuccess: async () => {
      setAdding(false);
      toast.success("Camera created");
      await refresh();
    },
    onError: (error) => toast.error(error.message),
  });
  const updateCamera = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<CameraInput> }) =>
      api.updateCamera(id, input),
    onSuccess: async (camera) => {
      setSelected(camera);
      toast.success("Camera updated");
      await refresh();
    },
    onError: (error) => toast.error(error.message),
  });
  const deleteCamera = useMutation({
    mutationFn: api.deleteCamera,
    onSuccess: async () => {
      setSelected(null);
      toast.success("Camera removed");
      await refresh();
    },
    onError: (error) => toast.error(error.message),
  });
  const cameraZones = (cameraId: string) =>
    (zones.data ?? []).filter((zone) => zone.camera_id === cameraId);
  const activeCameras = cameras.data?.filter((camera) => camera.is_active).length ?? 0;
  const totalCameras = cameras.data?.length ?? 0;

  return (
    <>
      <PageHeader
        title="Shelves & cameras"
        eyebrow="Visual inventory network"
        icon={Cctv}
        description="Manage camera coverage, shelf zones and the visual inputs that support inventory verification."
        meta={
          <>
            <span className="console-stat-pill">
              <Radio className="size-3 text-healthy" /> <strong>{activeCameras}</strong> enabled
            </span>
            <span className="console-stat-pill">
              <strong>{Math.max(0, totalCameras - activeCameras)}</strong> disabled
            </span>
            <span className="console-stat-pill">
              <Layers3 className="size-3 text-primary" /> <strong>{zones.data?.length ?? 0}</strong>{" "}
              shelf zones
            </span>
            <span className="console-stat-pill">
              <ShieldCheck className="size-3 text-primary" /> Configuration secured
            </span>
          </>
        }
        actions={
          canWrite ? (
            <button
              onClick={() => setAdding(true)}
              className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-[12px] font-semibold text-primary-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <Plus className="size-4" />
              Add camera
            </button>
          ) : undefined
        }
      />
      <div className="mb-4 flex items-start gap-3 rounded-lg border border-primary/15 bg-primary/[0.05] p-3 text-[12px] text-muted-foreground">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
          <Cctv className="size-4" />
        </span>
        <div>
          <p className="font-medium text-foreground">Configuration monitoring</p>
          <p className="mt-1 leading-5">
            Camera cards show configured state and shelf coverage. Runtime heartbeat, live FPS and
            snapshots will appear when telemetry endpoints are connected.
          </p>
        </div>
      </div>
      {cameras.error && (
        <p role="alert" className="mb-4 text-[12px] text-critical">
          {cameras.error.message}
        </p>
      )}
      {cameras.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="rounded-lg border p-4">
              <SkeletonRow />
              <SkeletonRow className="mt-4" />
            </div>
          ))}
        </div>
      ) : cameras.data?.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cameras.data.map((camera) => {
            const linkedZones = cameraZones(camera.id);
            return (
              <button
                key={camera.id}
                onClick={() => setSelected(camera)}
                className="group min-w-0 rounded-xl border bg-surface p-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
              >
                <CameraPreview camera={camera} zones={linkedZones.map((zone) => zone.name)} />
                <div className="mt-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold transition-colors group-hover:text-primary">
                      {camera.name}
                    </p>
                    <p className="mt-1 truncate text-[11px] text-muted-foreground">
                      {camera.location}
                    </p>
                  </div>
                  <Tag tone={camera.is_active ? "healthy" : "critical"}>
                    {camera.is_active ? "Enabled" : "Disabled"}
                  </Tag>
                </div>
                <div className="mt-3 flex items-center justify-between border-t pt-2.5 text-[11px] text-muted-foreground">
                  <span className="flex min-w-0 items-center gap-1.5 truncate font-mono">
                    <Layers3 className="size-3 shrink-0 text-primary" />
                    {linkedZones.map((zone) => zone.name).join(" · ") || "No zones assigned"}
                  </span>
                  <span className="shrink-0 font-mono">{camera.fps} FPS</span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={Cctv}
          title="No cameras configured"
          description="Managers can connect the first camera to begin assigning shelf zones."
          action={
            canWrite ? (
              <button
                onClick={() => setAdding(true)}
                className="h-8 rounded-md bg-primary px-3 text-[12px] text-primary-foreground"
              >
                Add camera
              </button>
            ) : undefined
          }
        />
      )}

      <Sheet open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle>{selected.name}</SheetTitle>
              </SheetHeader>
              <div className="space-y-5 px-4 pb-6">
                {can("shelves.manage") && (
                  <ShelfConfiguration
                    key={selected.id}
                    camera={selected}
                    zones={cameraZones(selected.id)}
                    onCameraSaved={setSelected}
                  />
                )}
                <CameraPreview
                  camera={selected}
                  zones={cameraZones(selected.id).map((zone) => zone.name)}
                  large
                />
                <div className="grid grid-cols-3 gap-2 text-[12px]">
                  {[
                    ["Configuration", selected.is_active ? "Enabled" : "Disabled"],
                    ["Target FPS", String(selected.fps)],
                    ["Timeout", `${selected.offline_timeout_seconds}s`],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-md border bg-surface-2 p-2.5">
                      <p className="text-muted-foreground">{label}</p>
                      <p className="mt-0.5 font-mono">{value}</p>
                    </div>
                  ))}
                </div>
                {cameraZones(selected.id).map((zone) => {
                  const items = (inventory.data ?? []).filter((item) => item.zone_id === zone.id);
                  return (
                    <div key={zone.id}>
                      <div className="mb-2 flex justify-between">
                        <p className="text-[13px] font-medium">
                          {zone.name} · {zone.label}
                        </p>
                        <span className="text-[11px] text-muted-foreground">
                          {Math.round(zone.confidence)}% confidence
                        </span>
                      </div>
                      <div className="divide-y rounded-md border">
                        {items.map((item) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between px-3 py-2 text-[12px]"
                          >
                            <span className="truncate">{item.name ?? item.sku}</span>
                            <div className="flex gap-2">
                              <CountDisplay
                                count={item.current_quantity}
                                observed={item.pending_quantity}
                              />
                              <ReconBadge status={inventoryTrustState(item)} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                <div className="flex gap-2">
                  {canWrite && (
                    <button
                      disabled={updateCamera.isPending}
                      onClick={() =>
                        updateCamera.mutate({
                          id: selected.id,
                          input: { is_active: !selected.is_active },
                        })
                      }
                      className="inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[12px]"
                    >
                      <Power className="size-3.5" />
                      {selected.is_active ? "Disable" : "Enable"}
                    </button>
                  )}
                  {canDelete && (
                    <button
                      disabled={deleteCamera.isPending}
                      onClick={() =>
                        window.confirm(`Remove ${selected.name}?`) &&
                        deleteCamera.mutate(selected.id)
                      }
                      className="inline-flex h-8 items-center gap-1.5 text-[12px] text-critical"
                    >
                      <Trash2 className="size-3.5" />
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
      <CameraDialog
        open={adding}
        onOpenChange={setAdding}
        pending={createCamera.isPending}
        onSubmit={(input) => createCamera.mutate(input)}
      />
    </>
  );
}

function CameraDialog({
  open,
  onOpenChange,
  pending,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pending: boolean;
  onSubmit: (input: CameraInput) => void;
}) {
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit({
      name: String(data.get("name")),
      location: String(data.get("location")),
      source_url: String(data.get("source_url") || "") || null,
      fps: Number(data.get("fps") || 2),
      offline_timeout_seconds: Number(data.get("timeout") || 30),
    });
  };
  const field = "h-9 w-full rounded-md border bg-surface px-3 text-[13px]";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add camera</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <label className="block space-y-1 text-[12px]">
            <span>Name</span>
            <input name="name" required className={field} />
          </label>
          <label className="block space-y-1 text-[12px]">
            <span>Location</span>
            <input name="location" required className={field} />
          </label>
          <label className="block space-y-1 text-[12px]">
            <span>Webcam, RTSP, or HTTP source</span>
            <input name="source_url" placeholder="webcam://0 or rtsp://…" className={field} />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1 text-[12px]">
              <span>Target FPS</span>
              <input name="fps" type="number" min="1" max="30" defaultValue="2" className={field} />
            </label>
            <label className="block space-y-1 text-[12px]">
              <span>Offline timeout</span>
              <input
                name="timeout"
                type="number"
                min="10"
                max="300"
                defaultValue="30"
                className={field}
              />
            </label>
          </div>
          <button
            disabled={pending}
            className="h-9 w-full rounded-md bg-primary text-[13px] text-primary-foreground disabled:opacity-50"
          >
            {pending ? "Creating…" : "Create camera"}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
