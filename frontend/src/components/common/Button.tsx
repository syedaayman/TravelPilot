import React from 'react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-lg text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50 shadow-sm';
    const variants = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700',
      secondary: 'bg-white text-blue-700 border border-blue-200 hover:bg-blue-50',
      outline: 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900',
      ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 shadow-none',
      destructive: 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100',
    };
    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 py-2 text-sm',
      lg: 'h-11 px-6 text-base',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <span className="mr-2 animate-spin">⏳</span>}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
