import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  MessageSquare,
  Cctv,
  Boxes,
  Bell,
  Activity,
  Settings,
  Search,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  Moon,
  Sun,
  Video,
  BarChart3,
  ClipboardList,
  PackageCheck,
  Store,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
import { canVisit } from "@/lib/permissions";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useInventoryWebSocket } from "@/hooks/use-inventory-websocket";
import { ago, alertSeverityTone, minutesAgo } from "@/lib/view-models";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusDot, Tag } from "./primitives";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/shelves", label: "Shelves", icon: Cctv },
  { to: "/video-processing", label: "Video Processing", icon: Video },
  { to: "/inventory", label: "Inventory", icon: PackageCheck },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/agent-activity", label: "Agent Activity", icon: Activity },
  { to: "/assistant", label: "Assistant", icon: MessageSquare },
  { to: "/requests", label: "Requests", icon: ClipboardList },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Logo({ collapsed }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <img
        src="/intellistock-logo.svg"
        alt={collapsed ? "IntelliStock" : ""}
        width={28}
        height={28}
        className="size-7 shrink-0"
      />
      {!collapsed && (
        <div className="leading-none">
          <span className="block text-[14px] font-semibold tracking-[-0.02em]">IntelliStock</span>
          <span className="mt-1 block text-[8px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Retail intelligence
          </span>
        </div>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { theme, setTheme } = useStore();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const socketState = useInventoryWebSocket();
  const alerts = useQuery({
    queryKey: [...queryKeys.alerts, "open"],
    queryFn: () => api.alerts({ status: "OPEN", limit: 20 }),
    refetchInterval: 30_000,
  });
  const health = useQuery({
    queryKey: queryKeys.health,
    queryFn: api.health,
    refetchInterval: 30_000,
  });
  const unread = alerts.data?.data ?? [];
  const initials =
    user?.username
      .split(/[-_.\s]+/)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "IS";
  const signOut = async () => {
    await logout();
    await navigate({ to: "/", replace: true });
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-3 focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <aside
        id="desktop-sidebar"
        className={cn(
          "hidden w-[var(--sidebar-width)] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex",
          !sidebarOpen && "md:hidden",
        )}
      >
        <div className="flex h-[var(--app-header-height)] shrink-0 items-center border-b border-sidebar-border px-4">
          <Logo />
        </div>
        <nav
          className="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-3"
          aria-label="Main navigation"
        >
          <p className="mb-2 px-2.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-muted-foreground/70">
            Workspace
          </p>
          {nav
            .filter((item) => canVisit(user, item.to))
            .map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="group relative flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-[13px] font-medium text-sidebar-foreground/80 transition-all hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                activeProps={{
                  className: "bg-primary/10 !text-primary shadow-sm ring-1 ring-primary/10",
                }}
              >
                <item.icon className="size-4 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.to === "/alerts" && unread.length > 0 && (
                  <span className="rounded bg-critical/15 px-1.5 font-mono text-[10px] text-critical">
                    {unread.length}
                  </span>
                )}
              </Link>
            ))}
        </nav>
        <div className="border-t border-sidebar-border p-2.5">
          <div className="rounded-lg border border-sidebar-border bg-surface/60 px-3 py-2.5 text-[11px] shadow-sm">
            <div className="mb-1.5 flex items-center gap-2 font-medium text-sidebar-foreground">
              <Store className="size-3.5 text-primary" /> System status
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <StatusDot
                state={
                  socketState === "live"
                    ? "live"
                    : socketState === "connecting"
                      ? "pending"
                      : "offline"
                }
                pulse={socketState === "live"}
              />
              Realtime {socketState}
            </div>
            <div className="mt-1 font-mono text-muted-foreground">
              DB {health.data?.database ?? "checking"} · Redis {health.data?.redis ?? "checking"}
            </div>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[var(--app-header-height)] shrink-0 items-center gap-2 border-b bg-surface/95 px-3 backdrop-blur-lg sm:gap-3 sm:px-5">
          <Button
            variant="ghost"
            size="icon"
            className="hidden size-8 md:inline-flex"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? <PanelLeftClose /> : <PanelLeft />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 md:hidden"
            onClick={() => setMobileSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <PanelLeft />
          </Button>
          <div className="md:hidden">
            <Logo collapsed />
          </div>
          <div className="flex h-9 min-w-0 max-w-lg flex-1 items-center gap-2.5 rounded-lg border bg-background/70 px-3 text-muted-foreground shadow-sm transition-all focus-within:border-primary/60 focus-within:ring-4 focus-within:ring-primary/10">
            <Search className="size-3.5" />
            <input
              placeholder="Search products…"
              aria-label="Search inventory by product name or product code; press Enter"
              className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none"
              onKeyDown={(event) => {
                if (event.key === "Enter")
                  void navigate({ to: "/inventory", search: { q: event.currentTarget.value } });
              }}
            />
          </div>
          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="grid size-9 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger
                className="relative grid size-9 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                aria-label="Notifications"
              >
                <Bell className="size-4" />
                {unread.length > 0 && (
                  <span className="absolute right-1 top-1 grid min-w-4 place-items-center rounded-full bg-critical px-1 font-mono text-[9px] text-white">
                    {unread.length}
                  </span>
                )}
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80">
                <DropdownMenuLabel className="text-[12px]">Open alerts</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {unread.slice(0, 5).map((alert) => (
                  <DropdownMenuItem
                    key={alert.id}
                    onClick={() => navigate({ to: "/alerts" })}
                    className="flex items-start gap-2"
                  >
                    <StatusDot state={alertSeverityTone(alert.severity)} />
                    <div className="min-w-0">
                      <p className="truncate text-[12px] font-medium">{alert.title}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {ago(minutesAgo(alert.created_at))}
                      </p>
                    </div>
                  </DropdownMenuItem>
                ))}
                {unread.length === 0 && (
                  <p className="px-2 py-4 text-center text-[12px] text-muted-foreground">
                    No open alerts
                  </p>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => navigate({ to: "/alerts" })}
                  className="justify-center text-[12px] text-primary"
                >
                  View all alerts
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <DropdownMenu>
              <DropdownMenuTrigger
                aria-label="Account menu"
                className="ml-1 flex h-9 items-center gap-2 rounded-lg border bg-background/60 p-1 pr-2.5 text-left shadow-sm transition-colors hover:bg-accent"
              >
                <span className="grid size-7 place-items-center rounded-md bg-primary/12 text-xs font-semibold text-primary">
                  {initials}
                </span>
                <span className="hidden max-w-28 leading-tight xl:block">
                  <span className="block truncate text-[11px] font-semibold text-foreground">
                    {user?.username}
                  </span>
                  <span className="mt-0.5 block text-[9px] capitalize text-muted-foreground">
                    {user?.role}
                  </span>
                </span>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="text-[13px]">{user?.username}</p>
                  <p className="text-[11px] font-normal text-muted-foreground">{user?.email}</p>
                  <Tag className="mt-1 capitalize">{user?.role}</Tag>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate({ to: "/settings" })}>
                  <Settings className="size-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => void signOut()}>
                  <LogOut className="size-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          className="console-content min-h-0 flex-1 overflow-y-auto"
        >
          <div className="mx-auto w-full max-w-[1680px] p-3 sm:p-4 lg:p-5 xl:p-6">{children}</div>
        </main>
        <nav
          aria-label="Mobile navigation"
          className="flex shrink-0 overflow-x-auto border-t bg-sidebar pb-[env(safe-area-inset-bottom)] md:hidden"
        >
          {nav
            .filter((item) => canVisit(user, item.to))
            .slice(0, 5)
            .map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="flex min-w-20 flex-1 flex-col items-center justify-center gap-1 px-2 py-2.5 text-muted-foreground"
                activeProps={{ className: "!text-primary" }}
                aria-label={item.label}
              >
                <item.icon className="size-4" />
                <span className="whitespace-nowrap text-[10px]">{item.label}</span>
              </Link>
            ))}
        </nav>
      </div>

      <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar p-0">
          <SheetHeader className="flex h-14 justify-center border-b px-4 text-left">
            <SheetTitle>
              <Logo />
            </SheetTitle>
          </SheetHeader>
          <nav className="space-y-0.5 p-2">
            {nav
              .filter((item) => canVisit(user, item.to))
              .map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileSidebarOpen(false)}
                  className="flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[13px] hover:bg-sidebar-accent"
                  activeProps={{ className: "bg-sidebar-accent font-medium" }}
                >
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              ))}
          </nav>
        </SheetContent>
      </Sheet>
    </div>
  );
}
