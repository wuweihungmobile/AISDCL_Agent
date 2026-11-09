/**
 * 「目前專案」脈絡：側欄的「執行中心／監控中心」需要一個 projectId。
 * 優先序：網址中的 /projects/<id>/… → 最近一次造訪的專案（sessionStorage）→ 專案列表第一筆。
 * 這裡是「最近造訪」的小型外部 store（SSR 與水合第一次渲染回 null，不造成水合不一致）。
 */
const KEY = "aisdlc.console.lastProject";

type Listener = () => void;
const listeners = new Set<Listener>();
let cache: string | null | undefined;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function getLastProjectId(): string | null {
  if (cache === undefined) cache = storage()?.getItem(KEY) ?? null;
  return cache;
}

export function rememberProjectId(id: string): void {
  if (getLastProjectId() === id) return;
  cache = id;
  storage()?.setItem(KEY, id);
  listeners.forEach((fn) => fn());
}

/** 遺忘最近造訪：只在記住的就是 `id` 時才清（避免清掉別的專案）；清 sessionStorage 與快取並通知訂閱者。 */
export function forgetProjectId(id: string): void {
  if (getLastProjectId() !== id) return;
  cache = null;
  try {
    storage()?.removeItem(KEY);
  } catch {
    // sessionStorage 不可用時，快取已清，本分頁內仍然一致
  }
  listeners.forEach((fn) => fn());
}

/** 專案列表的最小形狀（`PageData<{id}>` 的子集，讓純函式不依賴 API 型別）。 */
export type ProjectPageLike = { content: readonly { id: string }[]; totalElements: number };

/**
 * 目前專案 id 的純函式判斷（DEF-AC-035、TCS-ExecMonitorEntry 勘誤 11 W-E6）：
 * 網址 → 最近造訪 → 列表第一筆。「最近造訪」只在列表**已載入且完整**（totalElements <= content.length）而不含該 id 時視為失效（`stale: true`，
 * 由呼叫端負責 `forgetProjectId`）並退到列表第一筆；列表未載入或不完整（超過一頁）時樂觀沿用，交給頁面的 404 補救畫面。
 */
export function resolveCurrentProjectId(input: { fromPath: string | null; last: string | null; page: ProjectPageLike | undefined }): {
  id: string | null;
  stale: boolean;
} {
  const { fromPath, last, page } = input;
  const first = page?.content[0]?.id ?? null;
  if (fromPath) return { id: fromPath, stale: false };
  if (!last) return { id: first, stale: false };
  const complete = page !== undefined && page.totalElements <= page.content.length;
  if (complete && !page.content.some((p) => p.id === last)) return { id: first, stale: true };
  return { id: last, stale: false };
}

export function subscribeLastProject(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** /projects/<id>[/…] 中的 id；/projects、/projects/new 沒有 id。 */
export function projectIdFromPath(pathname: string): string | null {
  const match = /^\/projects\/([^/]+)/.exec(pathname);
  if (!match || match[1] === "new") return null;
  return match[1];
}
