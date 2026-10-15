import { cn } from "@/lib/utils";

/**
 * 載入轉圈（設計稿 wg-spin：0.8s linear）。
 * tone="primary"＝淺綠環＋主色弧（頁面級）；tone="onSolid"＝用在實底按鈕內，環線取半透明白。
 */
export function Spinner({ size = 40, tone = "primary", label = "載入中", className }: { size?: number; tone?: "primary" | "onSolid"; label?: string; className?: string }) {
  const border = Math.max(2, Math.round(size / 13));
  return (
    <span
      role="status"
      aria-label={label}
      className={cn("inline-block shrink-0 animate-wg-spin rounded-full", tone === "primary" ? "border-wg-tertiary border-t-wg-primary" : "border-white/40 border-t-white", className)}
      style={{ width: size, height: size, borderWidth: border, borderStyle: "solid" }}
    />
  );
}
