import type { ReactNode } from "react";

export type BadgeColor = "gray" | "blue" | "green" | "yellow" | "red";

export interface BaseBadgeProps {
  color?: BadgeColor;
  className?: string;
  children: ReactNode;
}

// Uses the .badge class from app/globals.css: 14px, medium weight (FE-UI-02, FE-UX-03).
const BASE_CLASSES = "badge";

const COLOR_CLASSES: Record<BadgeColor, string> = {
  gray: "bg-slate-200 text-slate-700",
  blue: "bg-brand-100 text-brand-700",
  green: "bg-emerald-100 text-emerald-700",
  yellow: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-700",
};

export function BaseBadge({ color = "gray", className, children }: BaseBadgeProps) {
  const classes = [BASE_CLASSES, COLOR_CLASSES[color], className].filter(Boolean).join(" ");

  return <span className={classes}>{children}</span>;
}
