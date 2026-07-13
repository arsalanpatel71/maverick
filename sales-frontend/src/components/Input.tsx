import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  size?: "sm" | "md";
}

export default function Input({ size = "md", className = "", ...props }: InputProps) {
  const base = "w-full bg-surface border border-border rounded-lg text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors";
  const sizing = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2.5 text-sm";
  return <input className={`${base} ${sizing} ${className}`} {...props} />;
}
