import type { AuthUser } from "./api/types";

export function can(user: AuthUser | null, permission: string): boolean {
  return user?.permissions?.includes(permission) === true;
}

export const routePermissions: Record<string, string | null> = {
  "/dashboard": "reports.read",
  "/inventory": "inventory.read",
  "/alerts": "alerts.read",
  "/shelves": "shelves.read",
  "/reports": "reports.read",
  "/agent-activity": "activity.read",
  "/assistant": "chatbot.use",
  "/requests": "requests.read_own",
  "/settings": null,
  "/video-processing": "video_jobs.read",
};

export function canVisit(user: AuthUser | null, path: string): boolean {
  const normalized = path.replace(/\/+$/, "") || "/";
  if (!user || !(normalized in routePermissions)) return false;
  const permission = routePermissions[normalized];
  return permission === null || (typeof permission === "string" && can(user, permission));
}

export function authorizationKey(user: AuthUser | null): string {
  return user
    ? JSON.stringify([user.userId, user.role, [...(user.permissions ?? [])].sort()])
    : "anonymous";
}
