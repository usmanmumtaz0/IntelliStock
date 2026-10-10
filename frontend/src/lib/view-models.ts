import type { AlertSeverity, InventoryDto, ZoneHealth } from "./api";

export type ReconStatus = "verified" | "pending" | "flagged";
export type SeverityTone = "critical" | "warning" | "info";
export type { ZoneHealth };

/** Observation age is separate from modification time (e.g. manual corrections). */
export function inventoryIsStale(item: InventoryDto, now = Date.now()): boolean {
  if (!item.last_observation_time) return true;
  const raw = item.last_observation_time;
  const time = Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/.test(raw) ? raw : `${raw}Z`);
  return !Number.isFinite(time) || now - time > 60_000;
}

export function inventoryTrustState(item: InventoryDto): ReconStatus {
  if (item.pending_quantity !== null && item.pending_quantity !== item.current_quantity)
    return "pending";
  return item.verified && !inventoryIsStale(item) ? "verified" : "flagged";
}

export function confidencePercent(value: number | null | undefined): number {
  if (value == null || Number.isNaN(value)) return 0;
  return Math.round((value <= 1 ? value * 100 : value) * 10) / 10;
}

export function minutesAgo(value: string | null | undefined): number {
  if (!value) return 0;
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return 0;
  return Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
}

export function alertSeverityTone(value: AlertSeverity): SeverityTone {
  if (value === "CRITICAL" || value === "HIGH") return "critical";
  if (value === "MEDIUM" || value === "LOW") return "warning";
  return "info";
}

export function ago(min: number): string {
  if (min <= 0) return "just now";
  if (min < 60) return `${min}m ago`;
  const hours = Math.floor(min / 60);
  return `${hours}h ${min % 60}m ago`;
}
