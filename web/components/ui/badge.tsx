import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-[color:var(--color-accent)] text-[color:var(--color-accent-foreground)]',
        secondary:
          'border-transparent bg-[color:var(--color-muted)] text-[color:var(--color-foreground)]',
        outline:
          'border-[color:var(--color-border)] text-[color:var(--color-foreground)] bg-transparent',
        positive:
          'border-transparent bg-[color:var(--color-positive)]/15 text-[color:var(--color-positive)]',
        negative:
          'border-transparent bg-[color:var(--color-negative)]/15 text-[color:var(--color-negative)]',
        warning:
          'border-transparent bg-[color:var(--color-warning)]/15 text-[color:var(--color-warning)]',
      },
    },
    defaultVariants: { variant: 'default' },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
