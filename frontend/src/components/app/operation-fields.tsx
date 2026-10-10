import type { ReactNode, InputHTMLAttributes } from "react";

export function Field({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="grid gap-1 text-xs text-muted-foreground">
      {label}
      <input
        {...props}
        className="h-9 w-full rounded-md border bg-background px-3 text-sm text-foreground disabled:opacity-50"
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
      className="rounded-md border bg-secondary px-3 py-2 text-xs font-medium hover:bg-accent disabled:opacity-50"
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
