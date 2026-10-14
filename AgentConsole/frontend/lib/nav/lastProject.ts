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
