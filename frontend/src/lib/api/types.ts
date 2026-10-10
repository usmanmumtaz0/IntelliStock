export type UserRole = "admin" | "manager" | "staff";

export interface AuthUser {
  userId: string;
  username: string;
  email: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
}

export interface VerifyResponse {
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
  valid: boolean;
}

export interface DashboardMetrics {
  total_skus: number;
  active_cameras: number;
  total_cameras: number;
  low_stock_alerts: number;
  reconciliation_confidence: number;
}

export interface StoreInfo {
  name: string;
  location: string;
  floor: string;
}

export type ZoneHealth = "healthy" | "low" | "offline" | "pending";

export interface ZoneDto {
  id: string;
  name: string;
  description: string | null;
  camera_id: string;
  camera_name: string;
  health: ZoneHealth;
  skus: number;
  confidence: number;
  aisle: string;
  label: string;
}

export type InventoryStatus =
  "unknown" | "adequate" | "low_stock" | "out_of_stock" | "detection_uncertain" | "camera_offline";

export interface InventoryDto {
  id: string;
  zone_id: string;
  product_id: string;
  sku: string | null;
  name: string | null;
  current_quantity: number;
  threshold: number | null;
  status: InventoryStatus;
  verified: boolean;
  pending_quantity: number | null;
  confidence: number;
  last_observation_time: string | null;
  observations_count: number;
  created_at?: string;
  updated_at: string | null;
}

export interface EventDto {
  id: string;
  zone: string | null;
  product: string | null;
  from: number | null;
  to: number | null;
  confidence: number | null;
  minAgo: number;
}

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  pages: number;
}

export interface Paginated<T> {
  data: T[];
  pagination: Pagination;
}

export type AlertStatus =
  "OPEN" | "ACKNOWLEDGED" | "IN_PROGRESS" | "RESOLVED" | "DISMISSED" | "ESCALATED" | "EXPIRED";

export type AlertSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface AlertDto {
  id: string;
  zone_id: string;
  product_id: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  current_quantity: number;
  description: string | null;
  recommendation: string | null;
  confidence: number;
  impact_score: number;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  snoozed_until?: string | null;
  acknowledged_by_user: string | null;
  resolved_by_user: string | null;
}

export interface AlertActionResponse {
  status: string;
  alert_id: string | null;
  affected: number;
  message: string;
}

export interface AlertStats {
  total_alerts: number;
  open_alerts: number;
  critical: number;
  high: number;
  by_type: Record<string, number>;
}

export interface CameraDto {
  id: string;
  name: string;
  location: string;
  source_url: string | null;
  fps: number;
  offline_timeout_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CameraInput {
  name: string;
  location: string;
  source_url?: string | null;
  fps?: number;
  offline_timeout_seconds?: number;
  is_active?: boolean;
}

export interface InventoryHistoryDto {
  id: string;
  zone_id: string;
  product_id: string;
  previous_quantity: number;
  new_quantity: number;
  quantity_delta: number;
  change_type: string;
  confidence: number;
  source_system: string;
  reason: string | null;
  created_at: string;
  processed_at: string;
  actor_user_id: string | null;
  actor_system: string | null;
}

export interface AgentRunDto {
  id: string;
  agent_type: string;
  status: string;
  trigger_event: string | null;
  output_action: string | null;
  confidence_score: number | null;
  execution_time_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgentStats {
  period_hours: number;
  total_runs: number;
  completed: number;
  failed: number;
  success_rate: number;
  by_agent_type: Record<string, number>;
  average_confidence: number;
}

export interface BasicHealth {
  status: "ok" | "degraded";
  database: "connected" | "disconnected";
  redis: "connected" | "disconnected";
}
