import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-caption font-medium transition-colors duration-micro ease-out",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground",
        outline: "border-border text-foreground",
        // Semantic data tiers — text uses the strong stop on a soft tint.
        low: "border-transparent bg-data-low-bg text-data-low",
        medium: "border-transparent bg-data-medium-bg text-data-medium",
        high: "border-transparent bg-data-high-bg text-data-high",
        neutral: "border-transparent bg-data-neutral-bg text-data-neutral",
        info: "border-transparent bg-data-info-bg text-data-info",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
