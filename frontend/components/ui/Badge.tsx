import { HTMLAttributes } from "react";
import { Badge as ShadcnBadge } from "@/components/shadcn/badge";
import { cn } from "@/lib/utils";

type CookitBadgeVariant = "green" | "blue" | "yellow" | "red" | "gray";

interface BadgeProps extends Omit<HTMLAttributes<HTMLDivElement>, "color"> {
  variant?: CookitBadgeVariant;
}

const variantClasses: Record<CookitBadgeVariant, string> = {
  green:  "bg-green-100 text-green-700 border-transparent hover:bg-green-100",
  blue:   "bg-blue-100 text-blue-700 border-transparent hover:bg-blue-100",
  yellow: "bg-yellow-100 text-yellow-700 border-transparent hover:bg-yellow-100",
  red:    "bg-red-100 text-red-700 border-transparent hover:bg-red-100",
  gray:   "bg-slate-100 text-slate-600 border-transparent hover:bg-slate-100",
};

export function Badge({ variant = "gray", className, children, ...props }: BadgeProps) {
  return (
    <ShadcnBadge
      variant="secondary"
      className={cn(variantClasses[variant], className)}
      {...props}
    >
      {children}
    </ShadcnBadge>
  );
}

export default Badge;
