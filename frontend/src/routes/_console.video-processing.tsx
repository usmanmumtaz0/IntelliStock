import { useEffect, useMemo, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Ban,
  Cpu,
  FileVideo,
  Image,
  Play,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api, apiBlobRequest, ApiError, type VideoFrameDto, type VideoJobDto } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader, Panel, Tag } from "@/components/app/primitives";
import { operations } from "@/lib/api/operations";

export const Route = createFileRoute("/_console/video-processing")({
  head: () => ({ meta: [{ title: "Video Processing — IntelliStock" }] }),
  component: VideoProcessing,
});

const terminal = new Set(["completed", "failed", "cancelled"]);
const imageExtensions = new Set(["jpg", "jpeg", "png", "webp"]);

function isImageFile(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return file.type.startsWith("image/") || imageExtensions.has(extension);
}

function tone(status: string): "healthy" | "critical" | "warning" | "neutral" {
  if (status === "completed") return "healthy";
  if (status === "failed") return "critical";
  if (status === "processing") return "warning";
  return "neutral";
}

function identityTone(status: string): "healthy" | "warning" | "critical" | "neutral" {
  if (status === "identified") return "healthy";
  if (status === "category_only") return "warning";
  if (status === "ambiguous") return "critical";
  return "neutral";
}

function formatTime(milliseconds: number) {
  const seconds = milliseconds / 1000;
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

function AuthenticatedImage({ path, alt }: { path: string; alt: string }) {
  const [src, setSrc] = useState<string>();
  useEffect(() => {
    let current: string | undefined;
    let disposed = false;
    void apiBlobRequest(path).then((blob) => {
      if (disposed) return;
      current = URL.createObjectURL(blob);
      setSrc(current);
    });
    return () => {
      disposed = true;
      if (current) URL.revokeObjectURL(current);
    };
  }, [path]);
  return src ? (
    <img src={src} alt={alt} className="aspect-video w-full rounded-lg bg-muted object-contain" />
  ) : (
    <div className="grid aspect-video w-full place-items-center rounded-lg bg-muted text-xs text-muted-foreground">
      Loading annotation…
    </div>
  );
}

function FrameCard({ frame }: { frame: VideoFrameDto }) {
  return (
    <article className="min-w-0 rounded-xl border bg-surface p-3">
      {frame.annotated_image_url ? (
        <AuthenticatedImage
          path={frame.annotated_image_url}
          alt={`Annotated frame at ${formatTime(frame.timestamp_ms)}`}
        />
      ) : (
        <div className="grid aspect-video place-items-center rounded-lg bg-muted">
          <Image />
        </div>
      )}
      <div className="mt-3 flex items-center justify-between gap-2 text-xs">
        <span className="font-mono">{formatTime(frame.timestamp_ms)}</span>
        <Tag tone={frame.detection_count ? "primary" : "neutral"}>
          {frame.detection_count} detections
        </Tag>
      </div>
      {frame.detections.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {frame.detections.map((detection) => (
            <Tag key={detection.id} tone={identityTone(detection.identity_status)}>
              {detection.product_id
                ? detection.class_name
                : (detection.category ?? "Unknown product")}{" "}
              {Math.round(detection.identity_confidence * 100)}%
              {detection.track_id !== null ? ` · #${detection.track_id}` : ""}
            </Tag>
          ))}
        </div>
      )}
    </article>
  );
}

function VideoProcessing() {
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const [selectedId, setSelectedId] = useState<string>();
  const [uploadProgress, setUploadProgress] = useState<number>();
  const [uploadKind, setUploadKind] = useState<"video" | "image">("video");
  const [message, setMessage] = useState<string>();
  const [cameraId, setCameraId] = useState("");
  const [reviewProducts, setReviewProducts] = useState<Record<string, string>>({});
  const jobs = useQuery({
    queryKey: queryKeys.videoJobs,
    queryFn: api.videoJobs,
    refetchInterval: (query) =>
      query.state.data?.data.some((job) => !terminal.has(job.status)) ? 2_000 : 10_000,
  });
  const selected = useMemo(
    () => jobs.data?.data.find((job) => job.id === selectedId) ?? jobs.data?.data[0],
    [jobs.data, selectedId],
  );
  const frames = useQuery({
    queryKey: [...queryKeys.videoJobs, selected?.id, "frames"],
    queryFn: () => api.videoFrames(selected!.id),
    enabled: Boolean(selected && selected.frames_processed > 0),
    refetchInterval: selected && !terminal.has(selected.status) ? 2_000 : false,
  });
  const cameras = useQuery({
    queryKey: queryKeys.cameras,
    queryFn: api.cameras,
    enabled: can("video_jobs.camera"),
  });
  const detector = useQuery({
    queryKey: queryKeys.detectorHealth,
    queryFn: api.detectorHealth,
    staleTime: 30_000,
  });
  const review = useQuery({
    queryKey: queryKeys.detectionReview,
    queryFn: api.detectionReviewQueue,
    refetchInterval: 10_000,
  });
  const products = useQuery({
    queryKey: ["products"],
    queryFn: operations.products,
    enabled: can("video_jobs.review"),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: queryKeys.videoJobs });
  const upload = useMutation({
    mutationFn: ({ body, kind }: { body: FormData; kind: "video" | "image" }) =>
      kind === "image"
        ? api.uploadImage(body, setUploadProgress)
        : api.uploadVideo(body, setUploadProgress),
    onSuccess: (job) => {
      setSelectedId(job.id);
      setMessage("Upload accepted. The durable worker will process it shortly.");
      void refresh();
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Upload failed"),
    onSettled: () => window.setTimeout(() => setUploadProgress(undefined), 600),
  });
  const cameraJob = useMutation({
    mutationFn: () =>
      api.createCameraVideoJob(cameraId, {
        sample_interval_seconds: 1,
        max_duration_seconds: 60,
        tracking_enabled: true,
      }),
    onSuccess: (job) => {
      setSelectedId(job.id);
      setMessage("Camera capture queued.");
      void refresh();
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Camera job failed"),
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api.cancelVideoJob(id),
    onSuccess: () => void refresh(),
  });
  const retry = useMutation({
    mutationFn: (id: string) => api.retryVideoJob(id),
    onSuccess: (job) => {
      setSelectedId(job.id);
      setMessage("Retry queued. The worker will process the preserved source file.");
      void refresh();
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Retry failed"),
  });
  const identify = useMutation({
    mutationFn: ({ detectionId, productId }: { detectionId: string; productId: string }) =>
      api.identifyDetection(detectionId, productId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.detectionReview }),
        queryClient.invalidateQueries({ queryKey: queryKeys.videoJobs }),
      ]);
    },
    onError: (error) =>
      setMessage(error instanceof ApiError ? error.message : "Identity review failed"),
  });

  const submitUpload = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(undefined);
    const form = event.currentTarget;
    const input = form.elements.namedItem("media") as HTMLInputElement;
    if (!input.files?.[0]) {
      setMessage("Choose a video or image first.");
      return;
    }
    const file = input.files[0];
    const kind = isImageFile(file) ? "image" : "video";
    const data = new FormData(form);
    data.delete("media");
    data.set(kind === "image" ? "image" : "video", file);
    const tracking = form.elements.namedItem("tracking_enabled") as HTMLInputElement | null;
    if (tracking) data.set("tracking_enabled", String(tracking.checked));
    upload.mutate({ body: data, kind });
  };

  return (
    <>
      <PageHeader
        title="Vision processing"
        eyebrow="Detection & product identity"
        icon={ScanSearch}
        description="Process images, videos and bounded camera streams, then review catalog-constrained identities and timestamped evidence."
        meta={
          <>
            <span className="console-stat-pill">
              <Cpu className="size-3 text-primary" />
              <strong>{detector.data?.actual_device ?? "checking"}</strong> device
            </span>
            <span className="console-stat-pill">
              <strong>{detector.data?.class_count ?? 0}</strong> supported classes
            </span>
            <span className="console-stat-pill">
              {detector.data?.manifest_verified ? (
                <ShieldCheck className="size-3 text-healthy" />
              ) : (
                <AlertTriangle className="size-3 text-warning" />
              )}
              {detector.data?.manifest_verified ? "Manifest verified" : "Review-only mapping"}
            </span>
          </>
        }
        actions={
          <Button variant="outline" onClick={() => void refresh()}>
            <RefreshCw /> Refresh
          </Button>
        }
      />
      {detector.data?.error && (
        <p
          role="alert"
          className="mb-5 rounded-xl border border-warning/30 bg-warning/10 p-3 text-xs text-warning"
        >
          {detector.data.error}
        </p>
      )}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(300px,.8fr)]">
        <Panel
          title="Upload video or picture"
          className={!can("video_jobs.camera") ? "xl:col-span-2" : ""}
        >
          <form onSubmit={submitUpload} className="grid gap-4 sm:grid-cols-2">
            <label className="sm:col-span-2 grid cursor-pointer place-items-center rounded-lg border border-dashed p-6 text-center hover:bg-muted/40">
              <Upload className="mb-3 size-7 text-primary" />
              <span className="text-sm font-medium">Choose a video or picture</span>
              <span className="mt-1 text-xs text-muted-foreground">
                MP4, AVI, MOV, JPG, PNG, or WebP. The server validates the actual media before
                queueing it.
              </span>
              <input
                name="media"
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo,image/jpeg,image/png,image/webp,.mp4,.mov,.avi,.jpg,.jpeg,.png,.webp"
                className="mt-4 block max-w-full text-xs"
                onChange={(event) =>
                  setUploadKind(
                    event.target.files?.[0] && isImageFile(event.target.files[0])
                      ? "image"
                      : "video",
                  )
                }
              />
            </label>
            {uploadKind === "video" && (
              <label className="text-xs font-medium">
                Sample every (seconds)
                <input
                  name="sample_interval_seconds"
                  type="number"
                  min="0.1"
                  max="60"
                  step="0.1"
                  defaultValue="1"
                  className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                />
              </label>
            )}
            {uploadKind === "video" && (
              <label className="text-xs font-medium">
                Maximum frames
                <input
                  name="max_frames"
                  type="number"
                  min="1"
                  max="10000"
                  defaultValue="300"
                  className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                />
              </label>
            )}
            <label className="text-xs font-medium">
              Confidence threshold
              <input
                name="confidence_threshold"
                type="number"
                min="0.01"
                max="1"
                step="0.01"
                defaultValue="0.4"
                className="mt-1 h-9 w-full rounded-md border bg-background px-3"
              />
            </label>
            {uploadKind === "video" && (
              <label className="flex items-center gap-2 self-end pb-2 text-xs font-medium">
                <input name="tracking_enabled" type="checkbox" value="true" defaultChecked /> Track
                objects across frames
              </label>
            )}
            <Button type="submit" disabled={upload.isPending} className="sm:col-span-2">
              <Upload />{" "}
              {upload.isPending
                ? `Uploading ${uploadProgress ?? 0}%`
                : `Upload ${uploadKind} and queue`}
            </Button>
            {uploadProgress !== undefined && (
              <div className="sm:col-span-2 h-2 overflow-hidden rounded bg-muted">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            )}
          </form>
          {message && (
            <p role="status" className="mt-4 rounded-lg bg-muted px-3 py-2 text-xs">
              {message}
            </p>
          )}
        </Panel>

        <Panel title="Camera capture" className={!can("video_jobs.camera") ? "hidden" : ""}>
          <p className="mb-4 text-xs leading-5 text-muted-foreground">
            Administrators can queue a 60-second capture from an active, server-configured camera.
            Camera credentials never reach the browser.
          </p>
          <select
            value={cameraId}
            onChange={(event) => setCameraId(event.target.value)}
            className="h-9 w-full rounded-md border bg-background px-3 text-sm"
          >
            <option value="">Select an active camera</option>
            {cameras.data
              ?.filter((camera) => camera.is_active && camera.source_url)
              .map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name} · {camera.location}
                </option>
              ))}
          </select>
          <Button
            className="mt-3 w-full"
            disabled={!cameraId || cameraJob.isPending}
            onClick={() => cameraJob.mutate()}
          >
            <Play /> Queue camera capture
          </Button>
        </Panel>
      </div>

      {review.data && review.data.total > 0 && (
        <Panel
          className="mt-5"
          title={`Product identity review (${review.data.total})`}
          action={<Tag tone="warning">Inventory unchanged</Tag>}
        >
          <p className="mb-4 max-w-3xl text-xs leading-5 text-muted-foreground">
            These detections do not have enough evidence for an exact SKU. Assigning a catalog item
            records a reviewed identity only; it does not alter trusted stock quantities.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {review.data.data.slice(0, 9).map((item) => (
              <article key={item.id} className="rounded-xl border bg-muted/20 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{item.class_name}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {item.category?.replaceAll("_", " ") ?? "No category"} ·{" "}
                      {Math.round(item.confidence * 100)}% detector confidence
                    </p>
                  </div>
                  <Tag tone={identityTone(item.identity_status)}>
                    {item.identity_status.replaceAll("_", " ")}
                  </Tag>
                </div>
                {can("video_jobs.review") && (
                  <div className="mt-3 flex gap-2">
                    <select
                      aria-label={`Catalog product for ${item.class_name}`}
                      value={reviewProducts[item.id] ?? ""}
                      onChange={(event) =>
                        setReviewProducts((current) => ({
                          ...current,
                          [item.id]: event.target.value,
                        }))
                      }
                      className="h-9 min-w-0 flex-1 rounded-lg border bg-background px-2 text-xs"
                    >
                      <option value="">Select catalog product</option>
                      {products.data?.map((product) => (
                        <option key={product.id} value={product.id}>
                          {product.sku} · {product.name}
                        </option>
                      ))}
                    </select>
                    <Button
                      size="sm"
                      disabled={!reviewProducts[item.id] || identify.isPending}
                      onClick={() =>
                        identify.mutate({
                          detectionId: item.id,
                          productId: reviewProducts[item.id]!,
                        })
                      }
                    >
                      Confirm
                    </Button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </Panel>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Panel title={`Jobs${jobs.data ? ` (${jobs.data.total})` : ""}`} bodyClassName="space-y-2">
          {jobs.isLoading && <p className="text-sm text-muted-foreground">Loading jobs…</p>}
          {jobs.data?.data.length === 0 && (
            <EmptyState
              icon={FileVideo}
              title="No processing jobs"
              description="Upload a video or picture to create the first processing job."
            />
          )}
          {jobs.data?.data.map((job) => (
            <button
              key={job.id}
              onClick={() => setSelectedId(job.id)}
              className={`w-full rounded-lg border p-3 text-left ${selected?.id === job.id ? "border-primary bg-primary/5" : "hover:bg-muted/40"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium">
                  {job.original_filename ?? "Camera capture"}
                </span>
                <Tag tone={tone(job.status)}>{job.status}</Tag>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {job.frames_processed} frames · {job.detection_instances} detections ·{" "}
                {job.stage.replaceAll("_", " ")}
              </p>
            </button>
          ))}
        </Panel>

        <Panel
          title={selected ? (selected.original_filename ?? "Camera capture") : "Job results"}
          action={
            selected?.status === "failed" ? (
              <Button
                size="sm"
                variant="outline"
                disabled={retry.isPending}
                onClick={() => retry.mutate(selected.id)}
              >
                <RefreshCw /> {retry.isPending ? "Queueing…" : "Retry"}
              </Button>
            ) : selected && !terminal.has(selected.status) ? (
              <Button size="sm" variant="outline" onClick={() => cancel.mutate(selected.id)}>
                <Ban /> Cancel
              </Button>
            ) : undefined
          }
        >
          {!selected && (
            <EmptyState
              icon={Image}
              title="Select a job"
              description="Its sampled frames, annotations, confidence, and track IDs will appear here."
            />
          )}
          {selected && (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric label="Status" value={selected.status} />
                <Metric label="Frames" value={String(selected.frames_processed)} />
                <Metric label="Detection instances" value={String(selected.detection_instances)} />
                <Metric
                  label="Unique tracks"
                  value={selected.unique_tracked_objects?.toString() ?? "—"}
                />
              </div>
              {selected.error_message && (
                <p
                  role="alert"
                  className="mt-4 rounded-lg bg-critical/10 p-3 text-sm text-critical"
                >
                  {selected.error_message}
                </p>
              )}
              <div className="mt-5 grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                {frames.data?.data.map((frame) => (
                  <FrameCard key={frame.id} frame={frame} />
                ))}
              </div>
              {selected.frames_processed === 0 && selected.status === "queued" && (
                <p className="mt-5 text-sm text-muted-foreground">
                  Queued for processing. Start the vision worker if this status does not advance.
                </p>
              )}
              {selected.frames_processed === 0 && selected.status === "processing" && (
                <p className="mt-5 text-sm text-muted-foreground">
                  The worker is opening and processing the source. Results will appear here.
                </p>
              )}
              {selected.frames_processed === 0 && selected.status === "failed" && (
                <p className="mt-5 text-sm text-muted-foreground">
                  No evidence frames were saved. Review the failure above, then retry if the source
                  is still available.
                </p>
              )}
              {selected.frames_processed === 0 && selected.status === "cancelled" && (
                <p className="mt-5 text-sm text-muted-foreground">
                  This job was cancelled before any evidence frame was saved.
                </p>
              )}
            </>
          )}
        </Panel>
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 truncate font-mono text-lg font-semibold capitalize">{value}</p>
    </div>
  );
}
