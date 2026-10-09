import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { CheckCircle2, Clock, Eye, ShieldCheck, Activity } from "lucide-react";
import { Logo } from "@/components/app/app-shell";
import { LiveIndicator, CountDisplay } from "@/components/app/primitives";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sign in — IntelliStock" },
      {
        name: "description",
        content: "Sign in to IntelliStock, the computer-vision verified shelf inventory dashboard.",
      },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login, user, ready } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && user) void navigate({ to: "/dashboard", replace: true });
  }, [ready, user, navigate]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get("email") ?? ""), String(form.get("password") ?? ""));
      await navigate({ to: "/dashboard", replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  };

  const field =
    "h-10 w-full rounded-md border bg-surface px-3 text-[13px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/60";

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="relative hidden flex-col justify-between overflow-hidden border-r bg-sidebar p-10 grid-bg lg:flex">
        <Logo />
        <div className="relative max-w-lg">
          <LiveIndicator label="Verified in real time" />
          <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight">
            Shelf inventory you can <span className="text-primary">actually trust.</span>
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">
            Cameras observe. The reconciliation engine verifies changes over time. Only confirmed
            inventory reaches the operations console.
          </p>
          <div className="mt-8 rounded-lg border bg-surface p-4">
            <div className="mb-3 flex items-center justify-between text-[11px] uppercase tracking-wider text-muted-foreground">
              <span>Shelf observation</span>
              <span className="font-mono">SECURE SESSION</span>
            </div>
            <div className="flex items-center gap-6">
              <div>
                <p className="mb-1 flex items-center gap-1 text-[11px] text-verified">
                  <CheckCircle2 className="size-3" /> Verified
                </p>
                <CountDisplay count={12} size="lg" />
              </div>
              <div className="h-10 w-px bg-border" />
              <div>
                <p className="mb-1 flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Clock className="size-3" /> Observed · reconciling
                </p>
                <span className="pending-hatch inline-flex rounded px-2 py-0.5 font-mono text-2xl text-muted-foreground">
                  9?
                </span>
              </div>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-3 gap-3 text-[12px]">
            {[
              { i: Eye, t: "Vision tracking" },
              { i: ShieldCheck, t: "Verified state" },
              { i: Activity, t: "Auditable agents" },
            ].map(({ i: Icon, t }) => (
              <div key={t} className="flex items-center gap-2 text-muted-foreground">
                <Icon className="size-4 text-primary" />
                {t}
              </div>
            ))}
          </div>
        </div>
        <p className="text-[12px] text-muted-foreground">
          © 2026 IntelliStock · Final Year Project
        </p>
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Welcome back</h2>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Sign in to your store operations console.
          </p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block space-y-1.5 text-[12px] font-medium">
              <span>Work email</span>
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                className={field}
                placeholder="you@store.com"
              />
            </label>
            <label className="block space-y-1.5 text-[12px] font-medium">
              <span>Password</span>
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className={field}
                placeholder="••••••••"
              />
            </label>
            {error && (
              <p
                role="alert"
                className="rounded-md border border-critical/40 bg-critical/10 px-3 py-2 text-[12px] text-critical"
              >
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="h-10 w-full rounded-md bg-primary text-[13px] font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-6 text-center text-[12px] text-muted-foreground">
            Accounts are provisioned by an IntelliStock administrator.
          </p>
        </div>
      </div>
    </div>
  );
}
