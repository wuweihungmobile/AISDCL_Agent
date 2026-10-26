import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { call, dataOf, ensureQuota, poll } from "./realBackend";

/**
 * 議題中心（Docker 全棧，經 nginx 同源；TCS-IssueCenter-20261027 AT-IC-07-2-2、AT-IC-09-6-2）——SCG-5 的實機證據，**不是每個 commit 的閘**（TCS Q4）：
 * `docker compose --profile db --profile app --profile full up -d` 之後，以 `npx playwright test -c tests/e2e/docker.config.ts -g "AT_IC_"` 執行（需要 docker CLI）。
 *  · AT-IC-07-2-2：console-api → 真 Bridge → 真根層 CLI 的全鏈——中文 status 與 source 篩選回對應的結果、不亂碼、不 500（補元件測試與 Bridge 測試各自缺的另一段）；
 *  · AT-IC-09-6-2：設定優先順序後重啟 backend 與資料庫容器，GET 仍回同值（順位住 `console.issue_priority`，不在容器記憶體）。
 * 帳本是 Bridge 容器所掛的 repo（唯讀）：這裡不寫帳本，只寫 Console 自有的順位，測完清掉。容器名稱預設為 compose 的 container_name。
 */
const execFileAsync = promisify(execFile);
const BACKEND = process.env.E2E_BACKEND_CONTAINER ?? "aisdlc-backend";
const PG = process.env.E2E_PG_CONTAINER ?? "aisdlc-pg-primary";

async function docker(...args: string[]): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync("docker", args, { timeout: 180_000, maxBuffer: 64 * 1024 * 1024 });
}
const health = async (container: string): Promise<string> => (await docker("inspect", "-f", "{{.State.Health.Status}}", container)).stdout.trim();

type IssueRow = { id: string; source: string | null; status: string; rankable: boolean; priority: number | null; priorityNote: string | null };
type IssuesData = {
  items: IssueRow[];
  truncated: boolean;
  nextSince: number | null;
  legend: { statuses: Array<{ name: string; tab: string | null }>; sources: Array<{ name: string }> };
};

/** 逐頁取完（limit 500）：同一組篩選下的全部議題。 */
async function fetchAll(request: APIRequestContext, query: string): Promise<IssuesData> {
  let since: number | null = null;
  let merged: IssuesData | null = null;
  for (let page = 0; page < 20; page += 1) {
    const suffix = since === null ? "" : `&since=${since}`;
    const reply = await call(request, "viewer", "GET", `/api/v1/issues?limit=500${query}${suffix}`);
    expect(reply.status, `GET /api/v1/issues?limit=500${query}${suffix} → ${JSON.stringify(reply.json).slice(0, 400)}`).toBe(200);
    const data = dataOf<IssuesData>(reply);
    merged = merged === null ? data : { ...data, items: [...merged.items, ...data.items] };
    if (!data.truncated || data.nextSince === null) return merged;
    since = data.nextSince;
  }
  throw new Error("議題清單超過 20 頁仍有下一頁：游標沒有收斂");
}

test.describe.configure({ mode: "serial" });

test.describe("Docker 全棧：議題中心", () => {
  test.setTimeout(600_000);

  test("AT_IC_07_2_2 全鏈：中文 status 與 source 篩選（含逗號聯集）回對應結果、不亂碼、不 500；含空白的 source 值＝503 si_unavailable（根層 CLI 不認該值，不是 500）", async ({ request }) => {
    await ensureQuota(request, "viewer", 30);
    const everything = await fetchAll(request, "");
    expect(everything.items.length, "全棧的帳本至少有一個議題").toBeGreaterThan(0);
    const sourceNames = everything.legend.sources.map((s) => s.name);
    expect(sourceNames.length).toBeGreaterThanOrEqual(2);
    const statusNames = new Set(everything.legend.statuses.map((s) => s.name));
    const tabOf = new Map(everything.legend.statuses.map((s) => [s.name, s.tab]));

    // 中文分頁別名（逗號聯集）加兩個中文來源：結果＝全部議題在同一組條件下的子集合（逐編號相等），每一筆的狀態與來源都落在條件內且不亂碼
    const statusAlias = ["待處理", "待您決定"];
    const sources = sourceNames.slice(0, 2);
    const filtered = await fetchAll(request, `&status=${encodeURIComponent(statusAlias.join(","))}&source=${encodeURIComponent(sources.join(","))}`);
    const expected = everything.items.filter((i) => statusAlias.includes(tabOf.get(i.status) ?? "") && i.source !== null && sources.includes(i.source)).map((i) => i.id);
    expect(filtered.items.map((i) => i.id)).toEqual(expected);
    for (const item of filtered.items) {
      expect(statusNames.has(item.status), `狀態 ${item.status} 不在圖例（亂碼或表外值）`).toBe(true);
      expect(sources, `來源 ${String(item.source)}`).toContain(item.source);
      expect(JSON.stringify(item)).not.toContain("�");
    }

    // 含空白的 source 值：根層 CLI 不認（rc 3）→ 503 si_unavailable；重點是編碼這一段沒有炸成 500，stderr 的中文也不亂碼
    const spaced = await call(request, "viewer", "GET", `/api/v1/issues?source=${encodeURIComponent(`${sources[0]} 含空白`)}`);
    expect(spaced.status, JSON.stringify(spaced.json).slice(0, 400)).toBe(503);
    expect(spaced.json.reason).toBe("si_unavailable");
    const details = (spaced.json.details ?? {}) as { cause?: string; detail?: string };
    expect(details.cause).toBe("nonzero_rc");
    expect(String(details.detail)).not.toContain("�");
    console.log(
      `[issues-docker] AT-IC-07-2-2：全部 ${everything.items.length} 件；篩選（${statusAlias.join("、")}／${sources.join("、")}）${filtered.items.length} 件；含空白的 source＝${spaced.status} ${String(spaced.json.reason)}`,
    );
  });

  test("AT_IC_09_6_2 設定順位後重啟 backend 與資料庫容器：GET 仍回同值（單筆與清單），清掉後回到 null", async ({ request }) => {
    await ensureQuota(request, "admin", 30);
    const pool = await fetchAll(request, `&status=${encodeURIComponent("待處理,待您決定")}`);
    const target = pool.items.find((i) => i.rankable);
    expect(target, "全棧的帳本沒有任何可排的議題（待您決定、待解、進行中）：無法驗證順位的持久性——請先讓帳本有一筆可排的議題").toBeTruthy();
    const id = (target as IssueRow).id;
    const path = `/api/v1/issues/${encodeURIComponent(id)}`;
    try {
      const put = await call(request, "admin", "PUT", `${path}/priority`, { rank: 7, note: "重啟前設定" });
      expect(put.status, JSON.stringify(put.json)).toBe(200);
      expect(dataOf<{ rank: number; note: string }>(put)).toMatchObject({ rank: 7, note: "重啟前設定" });
      const before = dataOf<{ items: IssueRow[] }>(await call(request, "viewer", "GET", path)).items[0];
      expect({ priority: before.priority, priorityNote: before.priorityNote }).toEqual({ priority: 7, priorityNote: "重啟前設定" });

      // 重啟資料庫與 backend（資料庫在 compose 裡是具名資料卷；順位必須活過兩者的重啟）
      await docker("restart", PG, BACKEND);
      await poll(
        () => health(PG),
        (s) => s === "healthy",
        "資料庫容器 healthy",
        240_000,
        3_000,
      );
      await poll(
        () => health(BACKEND),
        (s) => s === "healthy",
        "backend 容器 healthy",
        240_000,
        3_000,
      );
      await ensureQuota(request, "viewer", 10);

      const after = dataOf<{ items: IssueRow[] }>(await call(request, "viewer", "GET", path)).items[0];
      expect({ priority: after.priority, priorityNote: after.priorityNote }, "重啟後單筆仍回同一個順位與備註").toEqual({ priority: 7, priorityNote: "重啟前設定" });
      const listed = (await fetchAll(request, `&status=${encodeURIComponent("待處理,待您決定")}`)).items.find((i) => i.id === id);
      expect({ priority: listed?.priority, priorityNote: listed?.priorityNote }, "重啟後清單仍回同一個順位與備註").toEqual({ priority: 7, priorityNote: "重啟前設定" });
    } finally {
      // 清掉遺留的順位（冪等）；清不掉不遮蓋上面的失敗訊息
      await call(request, "admin", "DELETE", `${path}/priority`).catch(() => undefined);
    }
    const cleared = dataOf<{ items: IssueRow[] }>(await call(request, "viewer", "GET", path)).items[0];
    expect({ priority: cleared.priority, priorityNote: cleared.priorityNote }).toEqual({ priority: null, priorityNote: null });
  });
});
