import type { ButtonHTMLAttributes } from "react";

export type BaseButtonVariant = "primary" | "secondary" | "destructive";

export interface BaseButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BaseButtonVariant;
  loading?: boolean;
}

const BASE_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

const VARIANT_CLASSES: Record<BaseButtonVariant, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-700 focus-visible:outline-blue-600",
  secondary:
    "border border-gray-300 bg-white text-gray-800 hover:bg-gray-50 focus-visible:outline-gray-500",
  destructive: "bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600",
};

function Spinner() {
  return (
    <svg
      aria-hidden="true"
      data-testid="base-button-spinner"
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

export function BaseButton({
  variant = "primary",
  loading = false,
  type,
  disabled,
  className,
  children,
  ...rest
}: BaseButtonProps) {
  const classes = [BASE_CLASSES, VARIANT_CLASSES[variant], className].filter(Boolean).join(" ");

  return (
    <button
      {...rest}
      type={type ?? "button"}
      disabled={disabled || loading}
      aria-busy={loading}
      className={classes}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  );
}
