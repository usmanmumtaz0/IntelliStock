import { apiRequest, queryString, uploadRequest } from "./client";
import type {
  AgentRunDto,
  AgentStats,
  AlertActionResponse,
  AlertDto,
  AlertStats,
  BasicHealth,
  CameraDto,
  CameraInput,
  DashboardMetrics,
  EventDto,
  InventoryDto,
  InventoryHistoryDto,
  LoginResponse,
  Paginated,
  StoreInfo,
  VerifyResponse,
  ZoneDto,
  VideoFrameListDto,
  VideoJobDto,
  VideoJobListDto,
  DetectorHealthDto,
  DetectionReviewListDto,
  VideoDetectionDto,
} from "./types";

export * from "./client";
export * from "./session";
export * from "./types";

export const api = {
  signup: (email: string, username: string, password: string) =>
    apiRequest<{ message: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    }),
  login: (email: string, password: string) =>
    apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  verify: () => apiRequest<VerifyResponse>("/auth/verify"),
  logout: () =>
    apiRequest<{ message: string; user_id: string }>("/auth/logout", { method: "POST" }),

  dashboardMetrics: () => apiRequest<DashboardMetrics>("/dashboard/metrics"),
  storeInfo: () => apiRequest<StoreInfo>("/dashboard/store-info"),
  zones: () => apiRequest<ZoneDto[]>("/zones"),
  events: (limit = 30) => apiRequest<EventDto[]>(`/events${queryString({ limit })}`),
  health: () => apiRequest<BasicHealth>("/health"),

  inventory: (
    filters: {
      zone_id?: string | undefined;
      product_id?: string | undefined;
      status?: string | undefined;
      limit?: number | undefined;
      offset?: number | undefined;
    } = {},
  ) => apiRequest<InventoryDto[]>(`/inventory${queryString({ limit: 500, ...filters })}`),
  inventoryHistory: (zoneId: string, productId: string, days = 30) =>
    apiRequest<Paginated<InventoryHistoryDto>>(
      `/inventory/${encodeURIComponent(zoneId)}/${encodeURIComponent(productId)}/history${queryString({ days, limit: 100 })}`,
    ),
  inventoryRecord: (id: string) => apiRequest<InventoryDto>(`/inventory/${encodeURIComponent(id)}`),

  alerts: (
    filters: {
      status?: string | undefined;
      severity?: string | undefined;
      alert_type?: string | undefined;
      limit?: number | undefined;
      offset?: number | undefined;
    } = {},
  ) => apiRequest<Paginated<AlertDto>>(`/alerts${queryString({ limit: 100, ...filters })}`),
  alertStats: () => apiRequest<AlertStats>("/alerts/stats"),
  acknowledgeAlert: (id: string) =>
    apiRequest<AlertActionResponse>(`/alerts/${encodeURIComponent(id)}/acknowledge`, {
      method: "POST",
    }),
  acknowledgeAllAlerts: () =>
    apiRequest<AlertActionResponse>("/alerts/acknowledge-all", { method: "POST" }),
  resolveAlert: (id: string) =>
    apiRequest<AlertActionResponse>(`/alerts/${encodeURIComponent(id)}/resolve`, {
      method: "POST",
    }),
  dismissAlert: (id: string) =>
    apiRequest<AlertActionResponse>(`/alerts/${encodeURIComponent(id)}/dismiss`, {
      method: "POST",
    }),
  snoozeAlert: (id: string, minutes = 60) =>
    apiRequest<AlertActionResponse>(`/alerts/${encodeURIComponent(id)}/snooze`, {
      method: "POST",
      body: JSON.stringify({ minutes }),
    }),

  cameras: () => apiRequest<CameraDto[]>("/cameras"),
  createCamera: (input: CameraInput) =>
    apiRequest<CameraDto>("/cameras", { method: "POST", body: JSON.stringify(input) }),
  updateCamera: (id: string, input: Partial<CameraInput>) =>
    apiRequest<CameraDto>(`/cameras/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  deleteCamera: (id: string) =>
    apiRequest<void>(`/cameras/${encodeURIComponent(id)}`, { method: "DELETE" }),

  agentRuns: (hours = 24) =>
    apiRequest<AgentRunDto[]>(`/agents/runs${queryString({ hours, limit: 100 })}`),
  agentStats: (hours = 24) => apiRequest<AgentStats>(`/agents/stats${queryString({ hours })}`),

  videoJobs: () => apiRequest<VideoJobListDto>("/video-jobs"),
  videoJob: (id: string) => apiRequest<VideoJobDto>(`/video-jobs/${encodeURIComponent(id)}`),
  videoFrames: (id: string) =>
    apiRequest<VideoFrameListDto>(`/video-jobs/${encodeURIComponent(id)}/frames?limit=200`),
  cancelVideoJob: (id: string) =>
    apiRequest<{ id: string; status: string; cancel_requested: boolean }>(
      `/video-jobs/${encodeURIComponent(id)}/cancel`,
      { method: "POST" },
    ),
  retryVideoJob: (id: string) =>
    apiRequest<VideoJobDto>(`/video-jobs/${encodeURIComponent(id)}/retry`, {
      method: "POST",
    }),
  createCameraVideoJob: (cameraId: string, options: Record<string, unknown>) =>
    apiRequest<VideoJobDto>(`/video-jobs/cameras/${encodeURIComponent(cameraId)}`, {
      method: "POST",
      body: JSON.stringify(options),
    }),
  uploadVideo: (body: FormData, onProgress?: (percent: number) => void) =>
    uploadRequest<VideoJobDto>("/video-jobs", body, onProgress),
  uploadImage: (body: FormData, onProgress?: (percent: number) => void) =>
    uploadRequest<VideoJobDto>("/video-jobs/images", body, onProgress),
  detectorHealth: () => apiRequest<DetectorHealthDto>("/video-jobs/model-health"),
  detectionReviewQueue: () =>
    apiRequest<DetectionReviewListDto>("/video-jobs/review-queue?limit=100"),
  deleteDetection: (detectionId: string) =>
    apiRequest<{ deleted_id: string; inventory_effect: string }>(
      `/video-jobs/detections/${encodeURIComponent(detectionId)}`,
      { method: "DELETE" },
    ),
  identifyDetection: (detectionId: string, productId: string) =>
    apiRequest<VideoDetectionDto>(
      `/video-jobs/detections/${encodeURIComponent(detectionId)}/identify`,
      { method: "POST", body: JSON.stringify({ product_id: productId }) },
    ),
};
