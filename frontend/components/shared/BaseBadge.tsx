import type { ReactNode } from "react";

export type BadgeColor = "gray" | "blue" | "green" | "yellow" | "red";

export interface BaseBadgeProps {
  color?: BadgeColor;
  className?: string;
  children: ReactNode;
}

const BASE_CLASSES =
  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium";

const COLOR_CLASSES: Record<BadgeColor, string> = {
  gray: "bg-gray-100 text-gray-800",
  blue: "bg-blue-100 text-blue-700",
  green: "bg-green-100 text-green-700",
  yellow: "bg-yellow-100 text-yellow-800",
  red: "bg-red-100 text-red-700",
};

export function BaseBadge({ color = "gray", className, children }: BaseBadgeProps) {
  const classes = [BASE_CLASSES, COLOR_CLASSES[color], className].filter(Boolean).join(" ");

  return <span className={classes}>{children}</span>;
}
