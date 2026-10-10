import { apiRequest, apiTextRequest, queryString } from "./client";

export interface ReportSummary {
  generated_at: string;
  days: number;
  inventory_records: number;
  distinct_products: number;
  committed_units: number;
  states: Record<string, number>;
  history_changes: number;
  change_types: Record<string, number>;
  active_alerts: number;
  note: string;
}
export interface NotificationConfig {
  enabled: boolean;
  configured: boolean;
  ready: boolean;
  missing: string[];
  channel: string;
  max_attempts: number;
}
export interface Delivery {
  id: string;
  alert_id: string;
  alert_stage: string;
  recipient: string;
  status: string;
  attempts: number;
  last_error: string | null;
  created_at: string;
  available_at: string;
  accepted_at: string | null;
}
export const reporting = {
  summary: (days: number, zone_id: string) =>
    apiRequest<ReportSummary>(
      `/reports/summary${queryString({ days, zone_id: zone_id || undefined })}`,
    ),
  export: (kind: "inventory" | "history", days: number, zone_id: string) =>
    apiTextRequest(`/reports/export${queryString({ kind, days, zone_id: zone_id || undefined })}`),
  configuration: () => apiRequest<NotificationConfig>("/notifications/configuration"),
  deliveries: (offset: number) =>
    apiRequest<{ total: number; data: Delivery[] }>(
      `/notifications/deliveries${queryString({ offset, limit: 25 })}`,
    ),
};
