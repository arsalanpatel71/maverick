interface SpinnerProps {
  size?: "sm" | "md";
  variant?: "accent" | "white";
  className?: string;
}

export default function Spinner({ size = "md", variant = "accent", className = "" }: SpinnerProps) {
  const dim = size === "sm" ? "w-4 h-4" : "w-8 h-8";
  const color = variant === "white" ? "border-white/40 border-t-white" : "border-accent border-t-transparent";
  return <div className={`${dim} border-2 rounded-full animate-spin ${color} ${className}`} />;
}
