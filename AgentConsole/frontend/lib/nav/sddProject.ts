/**
 * 監控頁「AISDLC_SDD 引擎」卡記住上次選的 FSM 專案（契約 §4.3 M-20：存 `localStorage`，只是方便，不是狀態）。
 *  - 預設選哪個由 lib/domain/sdd.ts 的 pickSddProject 決定：這裡記的專案不在清單內就退回清單第一個。
 *  - localStorage 在隱私模式、被停用或額度用盡時會丟例外：一律吞掉，記不住就算了（卡片照常運作）。
 *  - 小型外部 store（useSyncExternalStore 用）：SSR 與水合第一次渲染回 null，不造成水合不一致。
 */
export const SDD_PROJECT_STORAGE_KEY = "console.monitor.sddProject";

type Listener = () => void;
const listeners = new Set<Listener>();
/** undefined＝尚未從 localStorage 讀過 */
let cache: string | null | undefined;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** 上次選的 FSM 專案（引用穩定：寫入才換值）；沒存過或讀不到回 null。 */
export function getRememberedSddProject(): string | null {
  if (cache === undefined) {
    try {
      const raw = storage()?.getItem(SDD_PROJECT_STORAGE_KEY);
      cache = raw ? raw : null;
    } catch {
      cache = null;
    }
  }
  return cache;
}

/** SSR 與水合第一次渲染用：永遠是 null。 */
export function getServerRememberedSddProject(): null {
  return null;
}

/** 使用者在下拉選了一個專案：記住並通知訂閱者（寫不進 localStorage 時只活在記憶體裡）。 */
export function rememberSddProject(project: string): void {
  cache = project;
  try {
    storage()?.setItem(SDD_PROJECT_STORAGE_KEY, project);
  } catch {
    // 額度用盡或被停用：這次的選擇只活在記憶體裡，不丟例外
  }
  listeners.forEach((fn) => fn());
}

export function subscribeSddProject(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** 測試用：丟掉記憶體快取，下次重新讀 localStorage。 */
export function resetSddProjectCache(): void {
  cache = undefined;
}
