import type { ReactNode, InputHTMLAttributes } from "react";

export function Field({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="grid min-w-0 gap-2 text-xs font-medium text-muted-foreground">
      {label}
      <input
        {...props}
        className="h-11 w-full rounded-lg border bg-background px-3 text-sm text-foreground transition-colors focus:border-primary disabled:cursor-not-allowed disabled:opacity-50"
      />
    </label>
  );
}

export function ActionButton({
  children,
  disabled = false,
  onClick,
  type = "button",
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border bg-secondary px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export function OperationError({ error }: { error: Error | null }) {
  return error ? (
    <p
      role="alert"
      className="rounded-md border border-critical/30 bg-critical/10 p-3 text-xs text-critical"
    >
      {error.message}
    </p>
  ) : null;
}
