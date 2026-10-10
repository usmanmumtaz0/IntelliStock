import { useId, useState, type ComponentProps } from "react";
import { Eye, EyeOff } from "lucide-react";

type PasswordInputProps = Omit<ComponentProps<"input">, "type"> & {
  label: string;
};

export function PasswordInput({
  label,
  id,
  className = "",
  disabled,
  ...props
}: PasswordInputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const [visible, setVisible] = useState(false);
  const action = `${visible ? "Hide" : "Show"} ${label.toLowerCase()}`;

  return (
    <div className="space-y-1.5 text-[12px] font-medium">
      <label htmlFor={inputId} className="block">
        {label}
      </label>
      <div className="relative">
        <input
          {...props}
          id={inputId}
          disabled={disabled}
          type={visible ? "text" : "password"}
          className={`${className} pr-12`}
        />
        <button
          type="button"
          disabled={disabled}
          aria-label={action}
          aria-controls={inputId}
          title={action}
          onClick={() => setVisible((value) => !value)}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
        >
          {visible ? (
            <EyeOff className="size-4" aria-hidden="true" />
          ) : (
            <Eye className="size-4" aria-hidden="true" />
          )}
        </button>
      </div>
    </div>
  );
}
