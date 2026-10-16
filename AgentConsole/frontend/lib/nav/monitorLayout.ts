/**
 * 監控頁「自訂儀表板」的版面順序（US-M-08；契約 §4.3 M-18：純前端、存 localStorage，沒有後端欄位）。
 * 各區塊可用 @dnd-kit 拖曳重排，順序存 localStorage 鍵 `console.monitor.layout`（JSON 陣列，區塊 id）。
 *  - 讀到的內容一律先淨化：丟掉未知 id、去重、把缺的區塊依預設順序補回尾端（之後新增區塊不會因舊資料而消失）。
 *  - localStorage 在隱私模式、被停用或額度用盡時會丟例外：一律吞掉，退回預設順序（版面是方便功能，不能擋住頁面）。
 *  - 小型外部 store（useSyncExternalStore 用）：SSR 與水合第一次渲染回預設，不造成水合不一致。
 */
export const LAYOUT_STORAGE_KEY = "console.monitor.layout";

/** `sdd`（v1.4，D-16；契約 §4.3 M-20）接在 `agent` 之後：舊的已存版本會把缺的 `sdd` 補在尾端（sanitizeLayout），不必遷移。 */
export const SECTION_IDS = ["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "compare", "agent", "sdd"] as const;
export type SectionId = (typeof SECTION_IDS)[number];

export const DEFAULT_LAYOUT: readonly SectionId[] = SECTION_IDS;

export const SECTION_TITLE: Record<SectionId, string> = {
  kpi: "指標卡",
  token: "Token 使用趨勢",
  distribution: "任務狀態與執行時間分佈",
  trends: "任務執行趨勢",
  timeline: "事件時間軸",
  logs: "執行日誌查詢",
  alerts: "告警",
  compare: "批次比較",
  agent: "Agent 即時狀態",
  sdd: "AISDLC_SDD 引擎",
};

const KNOWN = new Set<string>(SECTION_IDS);

/** 淨化：非陣列回預設；丟未知與重複；缺的依預設順序補在尾端。 */
export function sanitizeLayout(raw: unknown): SectionId[] {
  const kept: SectionId[] = [];
  if (Array.isArray(raw)) {
    for (const id of raw) {
      if (typeof id === "string" && KNOWN.has(id) && !kept.includes(id as SectionId)) kept.push(id as SectionId);
    }
  }
  return [...kept, ...DEFAULT_LAYOUT.filter((id) => !kept.includes(id))];
}

/** 把 from 位置的區塊移到 to 位置（拖曳放下）；位置越界或相同回原陣列。 */
export function moveSection(order: readonly SectionId[], from: number, to: number): SectionId[] {
  if (from === to || from < 0 || to < 0 || from >= order.length || to >= order.length) return [...order];
  const next = [...order];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

type Listener = () => void;
const listeners = new Set<Listener>();
let cache: readonly SectionId[] | undefined;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function sameOrder(a: readonly SectionId[], b: readonly SectionId[]): boolean {
  return a.length === b.length && a.every((id, i) => id === b[i]);
}

/** 目前版面（引用穩定：寫入才換新陣列）。 */
export function getLayout(): readonly SectionId[] {
  if (cache === undefined) {
    let parsed: unknown;
    try {
      const raw = storage()?.getItem(LAYOUT_STORAGE_KEY);
      parsed = raw ? JSON.parse(raw) : null;
    } catch {
      parsed = null; // 損毀的 JSON 或讀取失敗：當作沒有存過
    }
    const next = sanitizeLayout(parsed);
    cache = sameOrder(next, DEFAULT_LAYOUT) ? DEFAULT_LAYOUT : next;
  }
  return cache;
}

/** SSR 與水合第一次渲染用：永遠是預設順序（同一個常數，引用穩定）。 */
export function getServerLayout(): readonly SectionId[] {
  return DEFAULT_LAYOUT;
}

export function saveLayout(order: readonly SectionId[]): void {
  const next = sanitizeLayout(order);
  cache = sameOrder(next, DEFAULT_LAYOUT) ? DEFAULT_LAYOUT : next;
  try {
    storage()?.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(cache));
  } catch {
    // 額度用盡或被停用：這次的順序只活在記憶體裡，不丟例外
  }
  listeners.forEach((fn) => fn());
}

export function resetLayout(): void {
  cache = DEFAULT_LAYOUT;
  try {
    storage()?.removeItem(LAYOUT_STORAGE_KEY);
  } catch {
    // 同上
  }
  listeners.forEach((fn) => fn());
}

export function subscribeLayout(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** 測試用：丟掉記憶體快取，下次重新讀 localStorage。 */
export function resetLayoutCache(): void {
  cache = undefined;
}
