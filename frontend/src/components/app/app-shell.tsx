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
  ScanEye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
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
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/reports", label: "Reports", icon: Boxes },
  { to: "/agent-activity", label: "Agent Activity", icon: Activity },
  { to: "/assistant", label: "Assistant", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Logo({ collapsed }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">
        <ScanEye className="size-4" />
      </div>
      {!collapsed && <span className="text-[14px] font-semibold tracking-tight">IntelliStock</span>}
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
    <div className="flex h-screen overflow-hidden bg-background">
      <aside
        id="desktop-sidebar"
        className={cn(
          "hidden w-56 shrink-0 flex-col border-r bg-sidebar md:flex",
          !sidebarOpen && "md:hidden",
        )}
      >
        <div className="flex h-14 items-center border-b px-3.5">
          <Logo />
        </div>
        <nav className="flex-1 space-y-0.5 p-2" aria-label="Main navigation">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="group flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[13px] text-sidebar-foreground hover:bg-sidebar-accent"
              activeProps={{
                className: "bg-sidebar-accent !text-sidebar-accent-foreground font-medium",
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
        <div className="border-t p-2">
          <div className="rounded-md border bg-surface px-2.5 py-2 text-[11px]">
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
        <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-background px-4">
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
          <div className="flex h-8 max-w-md flex-1 items-center gap-2 rounded-md border bg-surface px-2.5 text-muted-foreground">
            <Search className="size-3.5" />
            <input
              placeholder="Search SKUs, products, zones…"
              className="flex-1 bg-transparent text-[13px] text-foreground outline-none"
              onKeyDown={(event) => {
                if (event.key === "Enter")
                  void navigate({ to: "/inventory", search: { q: event.currentTarget.value } });
              }}
            />
          </div>
          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="grid size-8 place-items-center rounded-md text-muted-foreground hover:bg-accent"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger
                className="relative grid size-8 place-items-center rounded-md text-muted-foreground hover:bg-accent"
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
              <DropdownMenuTrigger className="ml-1 grid size-8 place-items-center rounded-full bg-secondary text-[11px] font-semibold">
                {initials}
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
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1440px] p-5 lg:p-6">{children}</div>
        </main>
        <nav className="flex border-t bg-sidebar md:hidden">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex flex-1 justify-center py-2.5 text-muted-foreground"
              activeProps={{ className: "!text-primary" }}
              aria-label={item.label}
            >
              <item.icon className="size-4" />
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
            {nav.map((item) => (
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
