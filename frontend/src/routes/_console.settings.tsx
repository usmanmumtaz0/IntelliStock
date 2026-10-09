import { createFileRoute, Link } from "@tanstack/react-router";
import { Moon, Sun, ShieldCheck, Cctv, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
import { PageHeader, Panel, Tag } from "@/components/app/primitives";

export const Route = createFileRoute("/_console/settings")({
  head: () => ({
    meta: [
      { title: "Settings — IntelliStock" },
      { name: "description", content: "Account details, access level and application appearance." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const { theme, setTheme } = useStore();
  const { user } = useAuth();
  const initials =
    user?.username
      .split(/[-_.\s]+/)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "IS";

  return (
    <>
      <PageHeader
        title="Settings"
        description="Account information is managed by the authenticated IntelliStock backend."
      />
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Profile">
          <div className="flex items-center gap-3">
            <div className="grid size-12 place-items-center rounded-full bg-secondary text-sm font-semibold">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-[13px] font-medium">{user?.username}</p>
              <p className="truncate text-[12px] text-muted-foreground">{user?.email}</p>
            </div>
            <Tag className="ml-auto capitalize">{user?.role}</Tag>
          </div>
          <div className="mt-4 rounded-md border bg-surface-2 p-3 text-[12px] text-muted-foreground">
            <div className="flex gap-2">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
              <p>
                Your role is verified on every protected mutation. Contact an administrator to
                change account details or permissions.
              </p>
            </div>
          </div>
        </Panel>

        <Panel title="Appearance">
          <div className="grid grid-cols-2 gap-3">
            {(
              [
                ["dark", Moon, "Dark"],
                ["light", Sun, "Light"],
              ] as const
            ).map(([value, Icon, label]) => (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className={cn(
                  "flex items-center gap-2 rounded-md border p-3 text-[13px]",
                  theme === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent",
                )}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Camera configuration" className="xl:col-span-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-3">
              <Cctv className="mt-0.5 size-5 text-primary" />
              <div>
                <p className="text-[13px] font-medium">Cameras and shelf-zone assignments</p>
                <p className="mt-1 text-[12px] text-muted-foreground">
                  Use the Shelves page for live backend-backed camera configuration. No settings are
                  stored only in this browser.
                </p>
              </div>
            </div>
            <Link
              to="/shelves"
              className="inline-flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-md border px-3 text-[12px] hover:bg-accent"
            >
              Open shelves <ExternalLink className="size-3.5" />
            </Link>
          </div>
        </Panel>
      </div>
    </>
  );
}
