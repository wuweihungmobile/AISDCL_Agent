/** 顯示用格式化（本機時區；一律不丟例外，缺值回「—」）。 */

const DASH = "—";

function toDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

const pad = (n: number): string => String(n).padStart(2, "0");

/** 2026-06-17 */
export function formatDate(iso?: string | null): string {
  const d = toDate(iso);
  return d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : DASH;
}

/** 14:32:05 */
export function formatClock(iso?: string | null): string {
  const d = toDate(iso);
  return d ? `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` : DASH;
}

/** 2026-06-17 14:32 */
export function formatDateTime(iso?: string | null): string {
  const d = toDate(iso);
  return d ? `${formatDate(iso)} ${pad(d.getHours())}:${pad(d.getMinutes())}` : DASH;
}

/** 12,450；缺值「—」 */
export function formatNumber(n?: number | null): string {
  return typeof n === "number" && Number.isFinite(n) ? n.toLocaleString("en-US") : DASH;
}

/** 512 B／12.3 KB／4.0 MB（檔案大小顯示） */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** 0～100 的整數百分比；total 為 0 時回 0 */
export function percent(done: number, total: number): number {
  return total > 0 ? Math.round((done / total) * 100) : 0;
}

/** 重試 x / y */
export function retryLabel(retryCount: number, maxRetries: number): string {
  return `${retryCount} / ${maxRetries}`;
}
