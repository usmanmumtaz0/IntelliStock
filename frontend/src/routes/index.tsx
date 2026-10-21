import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  Check,
  Eye,
  LockKeyhole,
  ScanLine,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Logo } from "@/components/app/app-shell";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { PasswordInput } from "@/components/app/password-input";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sign in — IntelliStock" },
      {
        name: "description",
        content: "Secure access to the IntelliStock retail inventory operations platform.",
      },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [signup, setSignup] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { login, user, ready } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && user) void navigate({ to: "/dashboard", replace: true });
  }, [ready, user, navigate]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    const element = event.currentTarget;
    const form = new FormData(element);
    try {
      if (signup) {
        const password = String(form.get("password") ?? "");
        if (password !== String(form.get("confirmation") ?? "")) {
          throw new Error("Passwords do not match");
        }
        const result = await api.signup(
          String(form.get("email") ?? ""),
          String(form.get("username") ?? ""),
          password,
        );
        element.reset();
        setSignup(false);
        setNotice(result.message);
        return;
      }
      await login(String(form.get("email") ?? ""), String(form.get("password") ?? ""));
      await navigate({ to: "/dashboard", replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 422
          ? "Check your email, username (3–64 letters, numbers, dots, underscores or hyphens) and password (12–128 characters)."
          : cause instanceof Error
            ? cause.message
            : "Unable to submit request",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const field =
    "h-11 w-full rounded-lg border border-border/80 bg-background/70 px-3.5 text-sm outline-none transition-all placeholder:text-muted-foreground/70 focus:border-primary/70 focus:ring-4 focus:ring-primary/10";

  return (
    <main className="auth-shell grid min-h-screen overflow-x-hidden lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]">
      <section className="auth-showcase relative hidden min-h-screen overflow-hidden border-r border-white/10 bg-[#071713] px-8 py-7 text-white lg:flex lg:flex-col xl:px-12 xl:py-9">
        <div className="auth-orb auth-orb-one" />
        <div className="auth-orb auth-orb-two" />

        <div className="relative z-10 flex items-center justify-between">
          <Logo />
          <span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/60">
            Inventory intelligence
          </span>
        </div>

        <div className="relative z-10 my-auto max-w-2xl py-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-60" />
              <span className="relative inline-flex size-2 rounded-full bg-primary" />
            </span>
            Live operations platform
          </div>

          <h1 className="mt-6 max-w-xl text-4xl font-semibold leading-[1.05] tracking-[-0.04em] xl:text-5xl">
            Know what is on every shelf, <span className="text-primary">as it changes.</span>
          </h1>
          <p className="mt-5 max-w-xl text-[15px] leading-6 text-white/65">
            IntelliStock turns camera observations into verified inventory, actionable alerts, and a
            clear operational record for your entire store.
          </p>

          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
            {[
              { icon: Eye, title: "Continuous vision", copy: "Observe shelves in real time" },
              { icon: ShieldCheck, title: "Verified counts", copy: "Reconcile before committing" },
              { icon: Activity, title: "Clear decisions", copy: "Trace every operational action" },
            ].map(({ icon: Icon, title, copy }) => (
              <div
                key={title}
                className="rounded-xl border border-white/10 bg-white/[0.055] p-3.5 backdrop-blur-sm"
              >
                <div className="grid size-9 place-items-center rounded-xl bg-primary/15 text-primary">
                  <Icon className="size-4" />
                </div>
                <p className="mt-4 text-sm font-semibold text-white/90">{title}</p>
                <p className="mt-1 text-xs leading-5 text-white/45">{copy}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 flex max-w-xl items-center justify-between rounded-xl border border-white/10 bg-black/20 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
                <ScanLine className="size-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-white/90">Vision systems online</p>
                <p className="mt-0.5 text-xs text-white/45">
                  Monitoring and reconciliation are active
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
              <Check className="size-3.5" /> Operational
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-[11px] text-white/35">
          <span>© 2026 IntelliStock</span>
          <span className="flex items-center gap-1.5">
            <LockKeyhole className="size-3" /> Secure access
          </span>
        </div>
      </section>

      <section className="relative flex min-h-screen min-w-0 items-center justify-center overflow-hidden bg-background px-4 py-6 sm:px-8">
        <div className="auth-mobile-glow absolute inset-x-0 top-0 h-80 lg:hidden" />

        <div className="relative z-10 min-w-0 w-full max-w-[440px]">
          <div className="mb-7 flex items-center justify-between lg:hidden">
            <Logo />
            <span className="hidden rounded-full border bg-surface/80 px-2.5 py-1 text-[10px] font-medium text-muted-foreground shadow-sm backdrop-blur min-[360px]:inline-flex">
              Secure console
            </span>
          </div>

          <div className="mb-6">
            <div className="mb-4 grid size-10 place-items-center rounded-xl border border-primary/20 bg-primary/10 text-primary shadow-sm">
              {signup ? <Sparkles className="size-5" /> : <LockKeyhole className="size-5" />}
            </div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              {signup ? "Account request" : "Operations console"}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">
              {signup ? "Request an account" : "Welcome back"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {signup
                ? "Submit your details. An administrator will review and activate your access."
                : "Sign in to monitor inventory and manage store operations."}
            </p>
          </div>

          <div className="w-full min-w-0 rounded-2xl border border-border/80 bg-surface/90 p-5 shadow-[0_24px_80px_-32px_rgba(0,0,0,0.45)] backdrop-blur sm:p-6">
            {notice && (
              <p
                role="status"
                className="mb-5 rounded-xl border border-healthy/25 bg-healthy/10 p-3.5 text-sm text-healthy"
              >
                {notice}
              </p>
            )}

            <form key={signup ? "signup" : "login"} onSubmit={submit} className="space-y-4">
              {signup && (
                <label className="block space-y-2 text-[13px] font-medium">
                  <span>Username</span>
                  <input
                    name="username"
                    autoComplete="username"
                    required
                    minLength={3}
                    maxLength={64}
                    pattern="[A-Za-z0-9_.\-]+"
                    className={field}
                    placeholder="e.g. store.manager"
                  />
                </label>
              )}

              <label className="block space-y-2 text-[13px] font-medium">
                <span>Work email</span>
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className={field}
                  placeholder="you@company.com"
                />
              </label>

              <PasswordInput
                label="Password"
                name="password"
                autoComplete={signup ? "new-password" : "current-password"}
                minLength={signup ? 12 : 1}
                maxLength={signup ? 128 : 1024}
                required
                className={field}
                placeholder="••••••••"
              />

              {signup && (
                <PasswordInput
                  label="Confirm password (12–128 characters)"
                  name="confirmation"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  maxLength={128}
                  className={field}
                />
              )}

              {error && (
                <p
                  role="alert"
                  className="rounded-xl border border-critical/35 bg-critical/10 px-3.5 py-3 text-[12px] leading-5 text-critical"
                >
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="group flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/15 transition-all hover:-translate-y-0.5 hover:brightness-105 disabled:translate-y-0 disabled:opacity-50"
              >
                {submitting ? "Please wait…" : signup ? "Request access" : "Sign in securely"}
                {!submitting && (
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                )}
              </button>
            </form>

            <div className="my-5 h-px bg-border/70" />
            <p className="text-center text-[12px] text-muted-foreground">
              <button
                type="button"
                disabled={submitting}
                className="font-medium text-primary hover:underline"
                onClick={() => {
                  setSignup(!signup);
                  setError(null);
                  setNotice(null);
                }}
              >
                {signup ? "Already approved? Sign in" : "Need access? Request an account"}
              </button>
            </p>
          </div>

          <p className="mx-auto mt-5 flex max-w-sm items-start justify-center gap-2 px-3 text-center text-[11px] leading-5 text-muted-foreground">
            <ShieldCheck className="size-3.5 text-primary" />
            Protected access to your organization’s inventory data
          </p>
        </div>
      </section>
    </main>
  );
}
