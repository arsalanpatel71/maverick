export default function Logo({ size = "md" }: { size?: "sm" | "md" }) {
  const cls = size === "sm" ? "w-5 h-5" : "w-6 h-6";
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" className={cls}>
      <path d="M2 16V4L10 12L18 4V16" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
