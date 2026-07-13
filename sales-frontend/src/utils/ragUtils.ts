import type { RAGChunk } from "../types";

export function scoreColor(s: number): string {
  if (s >= 0.75) return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (s >= 0.5)  return "bg-amber-50 text-amber-700 border-amber-200";
  if (s >= 0.3)  return "bg-orange-50 text-orange-700 border-orange-200";
  return "bg-red-50 text-red-700 border-red-200";
}

export function scoreBg(s: number): string {
  if (s >= 0.75) return "bg-emerald-400";
  if (s >= 0.5)  return "bg-amber-400";
  if (s >= 0.3)  return "bg-orange-400";
  return "bg-red-400";
}

export function groupByName(chunks: RAGChunk[]): Map<string, RAGChunk[]> {
  const map = new Map<string, RAGChunk[]>();
  for (const c of chunks) {
    const arr = map.get(c.name) ?? [];
    arr.push(c);
    map.set(c.name, arr);
  }
  return map;
}

export function fileIcon(meta: Record<string, unknown>): string {
  const ct = String(meta.content_type ?? "");
  if (ct.includes("json"))     return "{}";
  if (ct.includes("csv"))      return "📊";
  if (ct.includes("markdown")) return "📝";
  if (ct.includes("html"))     return "🌐";
  return "📄";
}
