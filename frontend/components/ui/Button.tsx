import { forwardRef } from "react";
import {
  Button as ShadcnButton,
  type ButtonProps as ShadcnButtonProps,
} from "@/components/shadcn/button";
import { cn } from "@/lib/utils";

type CookitVariant = "primary" | "secondary" | "danger" | "ghost";
type CookitSize = "sm" | "md" | "lg";

interface ButtonProps extends Omit<ShadcnButtonProps, "variant" | "size"> {
  variant?: CookitVariant;
  size?: CookitSize;
  loading?: boolean;
}

const variantMap: Record<CookitVariant, ShadcnButtonProps["variant"]> = {
  primary: "default",
  secondary: "secondary",
  danger: "destructive",
  ghost: "ghost",
};

const sizeMap: Record<CookitSize, ShadcnButtonProps["size"]> = {
  sm: "sm",
  md: "default",
  lg: "lg",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", loading = false, children, disabled, className, ...props },
    ref
  ) => (
    <ShadcnButton
      ref={ref}
      variant={variantMap[variant]}
      size={sizeMap[size]}
      disabled={disabled || loading}
      className={cn("cursor-pointer", className)}
      {...props}
    >
      {loading && (
        <svg
          className="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      )}
      {children}
    </ShadcnButton>
  )
);
Button.displayName = "Button";

export { Button };
export default Button;
