import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";

// The only file allowed to render a raw <button> (FE-UI-01). ESLint enforces this.

export type BaseButtonVariant = "primary" | "secondary" | "destructive";

interface BaseButtonCommon {
  variant?: BaseButtonVariant;
  /** Disables the button and sets aria-busy while a request runs. */
  loading?: boolean;
  className?: string;
}

export type BaseButtonProps =
  | (BaseButtonCommon & ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined })
  | (BaseButtonCommon & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & { href: string });

const BASE_CLASSES =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-base font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60 aria-disabled:cursor-not-allowed aria-disabled:opacity-60";

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

export function BaseButton(props: BaseButtonProps) {
  const { variant = "primary", loading = false, className, children } = props;
  const classes = [BASE_CLASSES, VARIANT_CLASSES[variant], className].filter(Boolean).join(" ");

  if (props.href !== undefined) {
    const { href, variant: _variant, loading: _loading, className: _className, children: _children, ...anchorRest } =
      props;
    void _variant;
    void _loading;
    void _className;
    void _children;
    return (
      <Link
        {...anchorRest}
        href={href}
        aria-disabled={loading || undefined}
        aria-busy={loading || undefined}
        className={classes}
      >
        {loading ? <Spinner /> : null}
        {children}
      </Link>
    );
  }

  const {
    type,
    disabled,
    variant: _variant,
    loading: _loading,
    className: _className,
    children: _children,
    href: _href,
    ...buttonRest
  } = props;
  void _variant;
  void _loading;
  void _className;
  void _children;
  void _href;
  return (
    <button
      {...buttonRest}
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
