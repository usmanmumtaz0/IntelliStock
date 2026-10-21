import { createFileRoute, Link } from "@tanstack/react-router";
import {
  BellRing,
  Check,
  Cctv,
  ExternalLink,
  LockKeyhole,
  Moon,
  Palette,
  ShieldCheck,
  Sun,
  UserRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
import { PageHeader, Panel, Tag } from "@/components/app/primitives";
import { ProductManagement } from "@/components/app/product-management";
import { UserManagement } from "@/components/app/user-management";
import { NotificationDeliveries } from "@/components/app/notification-deliveries";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export const Route = createFileRoute("/_console/settings")({
  head: () => ({
    meta: [
      { title: "Settings — IntelliStock" },
      { name: "description", content: "Manage your account and application preferences." },
    ],
  }),
  component: SettingsPage,
});

function SectionTitle({
  icon: Icon,
  children,
}: {
  icon: typeof UserRound;
  children: React.ReactNode;
}) {
  return (
    <span className="flex items-center gap-2">
      <Icon className="size-4 text-primary" />
      {children}
    </span>
  );
}

export function SettingsPage() {
  const { theme, setTheme } = useStore();
  const { user, can } = useAuth();
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
        eyebrow="Personal & administrative settings"
        icon={UserRound}
        description="Manage your account and application preferences."
        meta={
          <>
            <span className="console-stat-pill">
              Signed in as <strong className="capitalize">{user?.role}</strong>
            </span>
            <span className="console-stat-pill">
              <ShieldCheck className="size-3 text-healthy" /> Server permissions enforced
            </span>
          </>
        }
      />
      <Tabs defaultValue="account">
        <div className="mb-5 overflow-x-auto pb-1">
          <TabsList aria-label="Settings sections" className="h-11 justify-start">
            <TabsTrigger value="account">Personal settings</TabsTrigger>
            {can("products.read") && <TabsTrigger value="products">Products</TabsTrigger>}
            {can("users.read") && <TabsTrigger value="users">Users & access</TabsTrigger>}
            {can("settings.read") && <TabsTrigger value="email">Email delivery</TabsTrigger>}
          </TabsList>
        </div>

        <TabsContent value="account" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title={<SectionTitle icon={UserRound}>My Account</SectionTitle>}>
              <div className="flex items-center gap-3">
                <div
                  className="grid size-12 shrink-0 place-items-center rounded-full bg-secondary text-sm font-semibold"
                  aria-hidden="true"
                >
                  {initials}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{user?.username}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{user?.email}</p>
                </div>
                <Tag className="ml-auto capitalize">{user?.role}</Tag>
              </div>
              <div className="mt-4 flex gap-2 rounded-lg border bg-surface-2 p-3 text-xs leading-5 text-muted-foreground">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
                <p>
                  Account identity and role are verified by the server. Contact an administrator to
                  update profile details or access permissions.
                </p>
              </div>
            </Panel>

            <Panel title={<SectionTitle icon={LockKeyhole}>Security</SectionTitle>}>
              <dl className="divide-y rounded-lg border bg-background text-xs">
                <div className="flex items-center justify-between gap-4 px-3 py-2.5">
                  <dt className="text-muted-foreground">Authentication</dt>
                  <dd className="font-medium">Password protected</dd>
                </div>
                <div className="flex items-center justify-between gap-4 px-3 py-2.5">
                  <dt className="text-muted-foreground">Session verification</dt>
                  <dd className="font-medium">Automatic</dd>
                </div>
                <div className="flex items-center justify-between gap-4 px-3 py-2.5">
                  <dt className="text-muted-foreground">Authorization</dt>
                  <dd className="font-medium capitalize">{user?.role} permissions</dd>
                </div>
              </dl>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Self-service password changes and session management are not currently supported.
                Contact an administrator for account recovery or access changes.
              </p>
            </Panel>

            <Panel title={<SectionTitle icon={Palette}>Appearance</SectionTitle>}>
              <p className="mb-3 text-xs leading-5 text-muted-foreground">
                Choose the interface theme for this browser. Your selection is saved automatically
                on this device.
              </p>
              <div className="grid grid-cols-2 gap-3">
                {(
                  [
                    ["dark", Moon, "Dark", "Optimized for low-light workspaces"],
                    ["light", Sun, "Light", "Higher contrast in bright environments"],
                  ] as const
                ).map(([value, Icon, label, description]) => {
                  const selected = theme === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setTheme(value)}
                      className={cn(
                        "relative min-w-0 rounded-lg border p-3 text-left transition-colors",
                        selected
                          ? "border-primary bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent",
                      )}
                    >
                      <span className="flex items-center gap-2 text-sm font-medium">
                        <Icon className="size-4 shrink-0" />
                        {label}
                      </span>
                      <span className="mt-1.5 block text-[11px] leading-4 text-muted-foreground">
                        {description}
                      </span>
                      {selected && (
                        <Check
                          className="absolute right-3 top-3 size-4"
                          aria-label={label + " theme selected"}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            </Panel>

            <Panel title={<SectionTitle icon={BellRing}>Notification Preferences</SectionTitle>}>
              <div className="rounded-lg border bg-background p-3">
                <p className="text-sm font-medium">Operational notifications</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Personal email or in-app notification preferences are not currently available.
                  Open alerts remain visible in the console according to your existing permissions.
                </p>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Administrators can review server-managed email readiness and delivery history from
                the Email delivery tab. Alert rules and recipients are configured outside this
                personal settings area.
              </p>
            </Panel>
          </div>

          <Panel title={<SectionTitle icon={Cctv}>Camera configuration</SectionTitle>}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[13px] font-medium">Cameras and shelf-zone assignments</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Use the Shelves page for backend-backed camera configuration. No camera settings
                  are duplicated or stored only in this browser.
                </p>
              </div>
              <Link
                to="/shelves"
                className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors hover:bg-accent"
              >
                Open shelves <ExternalLink className="size-3.5" />
              </Link>
            </div>
          </Panel>
        </TabsContent>

        {can("products.read") && (
          <TabsContent value="products">
            <ProductManagement />
          </TabsContent>
        )}
        {can("users.read") && (
          <TabsContent value="users">
            <UserManagement />
          </TabsContent>
        )}
        {can("settings.read") && (
          <TabsContent value="email">
            <NotificationDeliveries />
          </TabsContent>
        )}
      </Tabs>
    </>
  );
}
