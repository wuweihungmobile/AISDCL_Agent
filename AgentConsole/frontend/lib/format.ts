/** 顯示用格式化（本機時區；一律不丟例外，缺值回「—」）。 */
import type { ResourceUsage } from "@/lib/api/types";

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

const BYTES_PER_MB = 1024 * 1024;
const BYTES_PER_GB = 1024 * BYTES_PER_MB;

/** 記憶體用量（契約 §4.3 M-19）：不足 1 MB 寫「<1 MB」；達 1,024 MB 改以 GB（小數 1 位）；其餘 MB 取整數。門檻都比未四捨五入的位元組數。 */
function formatMemory(bytes: number): string {
  if (bytes < BYTES_PER_MB) return "<1 MB";
  if (bytes >= BYTES_PER_GB) return `${(bytes / BYTES_PER_GB).toFixed(1)} GB`;
  return `${Math.round(bytes / BYTES_PER_MB)} MB`;
}

/**
 * Agent 即時狀態卡的「資源使用」（契約 §1.2.3、§4.3 M-19；US-M-10）：`CPU 12.3%・記憶體 345 MB・3 行程`，三段以全形中點相連。
 * 沒有資料（null／缺席）或任一欄位不是非負有限數字，一律回單一「—」——不顯示半截的數字。
 * 「批次已終態、Bridge 未連線」也是「沒有資料」，但那是呼叫端依批次狀態判的，不在這裡。
 */
export function formatResourceUsage(r?: ResourceUsage | null): string {
  if (!r) return DASH;
  const { cpuPercent, memoryBytes, processCount } = r;
  for (const n of [cpuPercent, memoryBytes, processCount]) {
    if (typeof n !== "number" || !Number.isFinite(n) || n < 0) return DASH;
  }
  return `CPU ${cpuPercent.toFixed(1)}%・記憶體 ${formatMemory(memoryBytes)}・${processCount} 行程`;
}

/** 01:23:45（執行頁耗時；缺值或負值「—」）。 */
export function formatElapsed(sec?: number | null): string {
  if (typeof sec !== "number" || !Number.isFinite(sec) || sec < 0) return DASH;
  const s = Math.floor(sec);
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}

/** 0～100 的整數百分比；total 為 0 時回 0 */
export function percent(done: number, total: number): number {
  return total > 0 ? Math.round((done / total) * 100) : 0;
}

/** 重試 x / y */
export function retryLabel(retryCount: number, maxRetries: number): string {
  return `${retryCount} / ${maxRetries}`;
}

/**
 * 手動重試後的文案（C-9；契約 §1.6.4、QA O-04）：手動重試不受 maxRetries 限制（那是引擎「自動重試」的上限），
 * 所以 retryCount 可以大於 maxRetries——不再寫成容易誤讀的「3 / 1」，明說「不計入自動重試上限」。
 */
export function manualRetryLabel(retryCount: number, maxRetries: number): string {
  return `手動重試第 ${retryCount} 次（不計入自動重試上限 ${maxRetries}）`;
}
