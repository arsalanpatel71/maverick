import { useRef, useState } from "react";
import { createPortal } from "react-dom";

export default function InfoTip({ text }: { text: string }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const ref = useRef<HTMLSpanElement>(null);

  function handleMouseEnter() {
    if (ref.current) {
      const r = ref.current.getBoundingClientRect();
      setPos({ x: r.left + r.width / 2, y: r.top });
    }
  }

  return (
    <span
      ref={ref}
      className="inline-flex items-center ml-1.5 align-middle"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setPos(null)}
    >
      <span className="w-4 h-4 rounded-full bg-bg border border-border text-muted text-[10px] flex items-center justify-center cursor-help select-none font-medium leading-none">?</span>
      {pos && createPortal(
        <div
          style={{ position: "fixed", left: pos.x, top: pos.y - 8, transform: "translate(-50%, -100%)" }}
          className="z-[9999] bg-slate-800 text-white text-xs rounded-lg px-3 py-2 w-56 leading-relaxed shadow-xl pointer-events-none whitespace-normal"
        >
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
        </div>,
        document.body
      )}
    </span>
  );
}
