import { HTMLAttributes } from "react";
import { Card as ShadcnCard } from "@/components/shadcn/card";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: "sm" | "md" | "lg";
}

const paddingClasses: Record<NonNullable<CardProps["padding"]>, string> = {
  sm: "p-3",
  md: "p-5",
  lg: "p-7",
};

export function Card({ padding = "md", className, children, ...props }: CardProps) {
  return (
    <ShadcnCard className={cn(paddingClasses[padding], className)} {...props}>
      {children}
    </ShadcnCard>
  );
}

export default Card;
