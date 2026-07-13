import type { SelectHTMLAttributes } from "react";

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  size?: "sm" | "md";
}

export default function Select({ size = "md", className = "", ...props }: SelectProps) {
  const base = "w-full bg-surface border border-border rounded-lg cursor-pointer text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors";
  const sizing = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2.5 text-sm";
  return <select className={`${base} ${sizing} ${className}`} {...props} />;
}
