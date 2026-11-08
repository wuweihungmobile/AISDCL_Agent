/**
 * 共用排序工具（TCS-ConsoleUxSortHelp W-UX1；純函式、不碰 React）。
 * 語意：id／text 共用 zh-Hant numeric collator；空值不論升降冪排最後；
 * 主比較相等時依識別欄 tie-break（方向由欄的 tieDir 決定，不隨使用者升降冪翻轉）。
 */

export type SortKind = "id" | "text" | "number" | "iso" | "rank";
export type SortDir = "asc" | "desc";

export interface SortColumn<T> {
  key: string;
  kind: SortKind;
  get: (row: T) => string | number | null | undefined;
  /** kind=rank 時由呼叫端提供序位；回 null 視同空值。 */
  rank?: (v: string) => number | null;
  /** 作為 tie-break 識別欄時的方向（預設升冪）。 */
  tieDir?: SortDir;
}

export type SortState = { key: string; dir: SortDir } | null;

const collator = new Intl.Collator("zh-Hant", { numeric: true });

/** 識別欄／文字欄共用的自然序比較。 */
export function compareId(a: string, b: string): number {
  return collator.compare(a, b);
}

function isEmpty(v: unknown): boolean {
  return v === null || v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v));
}

type Prepared = { empty: boolean; text: string; num: number };

function prepare<T>(col: SortColumn<T>, row: T): Prepared {
  const raw = col.get(row);
  if (isEmpty(raw)) return { empty: true, text: "", num: 0 };
  switch (col.kind) {
    case "number": {
      const n = typeof raw === "number" ? raw : Number(raw);
      return Number.isNaN(n) ? { empty: true, text: "", num: 0 } : { empty: false, text: String(raw), num: n };
    }
    case "iso": {
      const s = String(raw);
      const ms = Date.parse(s);
      // 無法解析者退回文字比較（以 NaN 標記）。
      return { empty: false, text: s, num: ms };
    }
    case "rank": {
      const r = col.rank ? col.rank(String(raw)) : null;
      return r === null || r === undefined ? { empty: true, text: "", num: 0 } : { empty: false, text: String(raw), num: r };
    }
    default:
      return { empty: false, text: String(raw), num: 0 };
  }
}

function comparePrepared(kind: SortKind, a: Prepared, b: Prepared): number {
  if (kind === "number" || kind === "rank") return a.num - b.num;
  if (kind === "iso") {
    if (!Number.isNaN(a.num) && !Number.isNaN(b.num)) return a.num - b.num;
    return collator.compare(a.text, b.text);
  }
  return collator.compare(a.text, b.text);
}

/** 比較單欄（含空值規則）；回傳依「升冪」語意，desc 時只翻轉非空值。 */
function compareByColumn<T>(col: SortColumn<T>, dir: SortDir, x: T, y: T): number {
  const a = prepare(col, x);
  const b = prepare(col, y);
  if (a.empty && b.empty) return 0;
  if (a.empty) return 1; // 空值永遠最後
  if (b.empty) return -1;
  const c = comparePrepared(col.kind, a, b);
  return dir === "desc" ? -c : c;
}

export function sortRows<T>(rows: readonly T[], columns: readonly SortColumn<T>[], state: SortState, defaultCompare?: (a: T, b: T) => number, tieBreak?: SortColumn<T>): T[] {
  const copy = [...rows];
  const col = state ? columns.find((c) => c.key === state.key) : undefined;
  if (!state || !col) {
    return defaultCompare ? copy.sort(defaultCompare) : copy;
  }
  const idCol = columns.find((c) => c.kind === "id") ?? tieBreak;
  const tie = (x: T, y: T): number => {
    if (!idCol) return 0;
    return compareByColumn(idCol, idCol.tieDir ?? "asc", x, y);
  };
  // 穩定排序＋主比較＋識別欄 tie-break
  return copy.sort((x, y) => compareByColumn(col, state.dir, x, y) || tie(x, y));
}

/** 表頭點擊的狀態機：有效狀態＝state ?? defaultSort；同欄反向、異欄升冪。 */
export function nextSort(state: SortState, key: string, defaultSort?: SortState): SortState {
  const eff = state ?? defaultSort ?? null;
  if (!eff || eff.key !== key) return { key, dir: "asc" };
  return { key, dir: eff.dir === "asc" ? "desc" : "asc" };
}
