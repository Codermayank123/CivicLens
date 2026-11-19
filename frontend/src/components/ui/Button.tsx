import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost' | 'success';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium transition-all duration-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-6 py-3 gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-[#4b205b] hover:bg-[#351641] text-white shadow-sm hover:shadow-[#4b205b]/25 focus:ring-[#d9a84e]',
    secondary:
      'bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-100 focus:ring-slate-400',
    outline:
      'border border-[#b79f83] hover:bg-[#f4e8d5] text-[#4b205b] focus:ring-[#d9a84e]',
    danger:
      'bg-rose-600 hover:bg-rose-700 text-white shadow-sm hover:shadow-rose-500/25 focus:ring-rose-500 dark:bg-rose-600 dark:hover:bg-rose-700',
    ghost:
      'text-[#4b205b] hover:text-[#29232b] hover:bg-[#f4e8d5] focus:ring-[#d9a84e]',
    success:
      'bg-[#286b50] hover:bg-[#1d523d] text-white shadow-sm hover:shadow-[#286b50]/25 focus:ring-[#d9a84e]',
  };

  return (
    <button
      className={clsx(baseStyles, sizeStyles[size], variantStyles[variant], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : leftIcon}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
