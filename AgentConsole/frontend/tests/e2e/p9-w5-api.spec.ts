import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { extractPdfText } from "./pdfText";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, getRun, poll, waitRun, type Fixture, type RunView } from "./realBackend";
import { BRIDGE_LOG, BRIDGE_URL, PG_CONTAINER, fetchRaw, psql } from "./w5";

/**
 * W5 修復波複驗（API 面）——契約 v1.2 §5 E2E-13 的最低驗證矩陣，對真後端（e2e profile）＋真 Bridge＋aisdlc-mock-claude：
 *   列 1 task-totals（C-1）、列 2～3 專案復原（C-3）、列 4 PDF 報表（C-4）、列 7 升級跨批次不被吞（C-7）、列 8 執行中刪除（C-8）、
 *   列 9 手動重試（C-9）、列 11 批次列表 bridgeStatus（C-11）、列 12 traceId 貫穿 Bridge（C-12）。
 * 列 5（refresh 502）與 Docker 側的列 13 在 p8-docker-stack.stack.ts；列 6（設定原樣匯入）在 p6-settings.spec.ts；列 10（匯入記錄重開）在 p9-w5-ui.spec.ts；
 * 列 13 的本機半邊（Bridge 深度探針的 200 與兩種 503）在 p9-w5-bridge.spec.ts。
 * 輪詢一律用 viewer、寫入用 operator（限流以 JWT subject 計，UI 與 REST 共用同一個桶）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
const execBody = (level = 4) => ({ autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });

type Totals = { from: string; to: string; started: number; completed: number; failed: number; retried: number; projectsCounted: number };
type TrendPoint = { bucketStart: string; started: number; completed: number; failed: number; retried: number };
type AlertRow = { id: string; rule: string; severity: string; subject: string; acknowledged: boolean };

async function start(request: APIRequestContext, f: Fixture, level = 4): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, execBody(level));
  expect(r.status, `execute ${f.name} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(201);
  return dataOf<{ id: string }>(r).id;
}

/** 等批次進終態；FAILED 時再等審核項建立（契約 §2.4：Bridge 直寫 DB 的終態比 Console 消費事件建審核項早一步）。 */
const finish = (request: APIRequestContext, runId: string, timeoutMs = 120_000): Promise<RunView> =>
  poll(
    () => getRun(request, runId),
    (r) => TERMINAL.includes(r.status) && (r.status !== "FAILED" || (r.pendingReviews ?? []).length > 0),
    `批次 ${runId} 進入終態`,
    timeoutMs,
  );

const alertsOf = async (request: APIRequestContext, projectId: string): Promise<AlertRow[]> =>
  dataOf<AlertRow[]>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${projectId}/alerts?limit=200`));

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200); // 執行類情境要求 apiKey 為空
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 70); // 本檔輪詢與讀取都用 viewer（列 11 的快速輪詢一輪就 40 次）
});

test.describe("W5 複驗（API 面；E2E-13）", () => {
  test.setTimeout(300_000);

  test("列 1｜task-totals 與各專案 task-trend 加總逐欄相等（3 個專案、含失敗與重試）；viewer 200；軟刪專案不計；缺 from／視窗過長／from≥to 皆 400（C-1）", async ({ request }) => {
    const from = new Date(Date.now() - 60_000).toISOString();
    const a1 = await createFixture(request, { name: nm("QA W5 totals A1"), kind: "A", level: 4 });
    const a2 = await createFixture(request, { name: nm("QA W5 totals A2"), kind: "A", level: 4 });
    const b = await createFixture(request, { name: nm("QA W5 totals B（T2 失敗）"), kind: "A", level: 4, failTasks: [2] });
    const projects = [a1, a2, b];
    for (const f of projects) await finish(request, await start(request, f));
    const to = new Date().toISOString();
    const win = `from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;

    const totals = dataOf<Totals>(await call(request, "viewer", "GET", `/api/v1/monitor/task-totals?${win}`));
    const trend = async (f: Fixture): Promise<TrendPoint[]> => dataOf<TrendPoint[]>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${f.projectId}/task-trend?${win}&bucket=DAY`));
    const sum = (rows: TrendPoint[][], k: "started" | "completed" | "failed" | "retried") => rows.flat().reduce((n, p) => n + p[k], 0);
    const all = [await trend(a1), await trend(a2), await trend(b)];
    for (const k of ["started", "completed", "failed", "retried"] as const) expect(totals[k], `task-totals.${k}＝三個專案 task-trend 各桶加總（${JSON.stringify(totals)}）`).toBe(sum(all, k));
    // 數字本身要有鑑別力：不是三個 0 對三個 0
    expect(totals.completed, "A1 3＋A2 3＋B 的 T1 1").toBe(7);
    expect(totals.failed, "B 的 T2 失敗").toBeGreaterThanOrEqual(1);
    expect(totals.retried, "B 的 T2 重試").toBeGreaterThanOrEqual(1);
    expect(totals.started).toBeGreaterThanOrEqual(8);
    expect(totals.projectsCounted, "視窗內有步驟列的專案數＝這三個（若別處有批次在跑，這裡會多）").toBe(3);
    expect(Date.parse(totals.from)).toBeLessThanOrEqual(Date.parse(from) + 1000);
    expect(Object.keys(totals).sort()).toEqual(["completed", "failed", "from", "projectsCounted", "retried", "started", "to"]);

    // 角色：viewer 已是 200（上面全用 viewer）；operator／admin 亦可；未認證 401
    for (const role of ["operator", "admin"] as const) expect((await call(request, role, "GET", `/api/v1/monitor/task-totals?${win}`)).status, role).toBe(200);

    // 軟刪專案不計：刪掉 A2 之後，同一視窗的 completed 少 3、projectsCounted 少 1
    expect((await call(request, "operator", "DELETE", `/api/v1/projects/${a2.projectId}`)).status).toBe(204);
    const after = dataOf<Totals>(await call(request, "viewer", "GET", `/api/v1/monitor/task-totals?${win}`));
    expect({ completed: after.completed, projectsCounted: after.projectsCounted }).toEqual({ completed: totals.completed - 3, projectsCounted: 2 });

    // 400：缺 from、視窗過長（>92 天）、from 不早於 to
    const noFrom = await call(request, "viewer", "GET", "/api/v1/monitor/task-totals");
    expect(noFrom.status).toBe(400);
    expect((noFrom.json.errors as Array<{ field: string }>)[0].field).toBe("from");
    const tooLong = await call(request, "viewer", "GET", `/api/v1/monitor/task-totals?from=${encodeURIComponent(new Date(Date.now() - 93 * 86_400_000).toISOString())}&to=${encodeURIComponent(to)}`);
    expect(tooLong.status).toBe(400);
    expect(tooLong.json.reason).toBe("時間範圍不合法");
    expect((tooLong.json.errors as Array<{ field: string }>)[0].field).toBe("to");
    expect((tooLong.json.details as { maxDays: number }).maxDays).toBe(92);
    const exactly92 = await call(
      request,
      "viewer",
      "GET",
      `/api/v1/monitor/task-totals?from=${encodeURIComponent(new Date(Date.parse(to) - 92 * 86_400_000).toISOString())}&to=${encodeURIComponent(to)}`,
    );
    expect(exactly92.status, "剛好 92 天可以").toBe(200);
    const backwards = await call(request, "viewer", "GET", `/api/v1/monitor/task-totals?from=${encodeURIComponent(to)}&to=${encodeURIComponent(from)}`);
    expect(backwards.status).toBe(400);
    expect(backwards.json.reason).toBe("時間範圍不合法");
    const anon = await fetch(`${API_URL}/api/v1/monitor/task-totals?${win}`);
    expect(anon.status).toBe(401);
    // 這個視窗（from 在 60 秒前）之後的資料不會讓不變量失效：A1、B 的 trend 與 totals 仍逐欄相等（A2 已軟刪，不計）
    for (const k of ["started", "completed", "failed", "retried"] as const) expect(after[k], k).toBe(sum([all[0], all[2]], k));
  });

  test("列 4｜PDF 報表：200、application/pdf、%PDF-、檔名規則、可抽出專案名稱／標題／四個區段／中文任務名／totalTokens；CSV 與 PDF 同四區段；不再有 501（C-4）", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA W5 PDF 報表"), kind: "A", level: 4 });
    const runId = await start(request, f);
    await finish(request, runId);
    const base = `/api/v1/monitor/projects/${f.projectId}/report`;

    const pdf = await fetchRaw(request, "viewer", `${base}?format=pdf`, { Accept: "application/pdf" });
    expect(pdf.status).toBe(200);
    expect(pdf.headers["content-type"]).toBe("application/pdf");
    const cd = pdf.headers["content-disposition"] ?? "";
    expect(cd).toMatch(/^attachment; filename="monitor-report-[0-9a-f]{8}-\d{8}-\d{4}\.pdf"$/);
    expect(cd.slice(cd.indexOf("monitor-report-") + "monitor-report-".length, cd.indexOf("monitor-report-") + "monitor-report-".length + 8)).toBe(f.projectId.slice(0, 8));
    expect(pdf.body.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(pdf.body.subarray(-16).toString("latin1")).toContain("%%EOF");
    expect(pdf.body.length, "內嵌字型子集後仍是一份有內容的檔案").toBeGreaterThan(5_000);

    const text = extractPdfText(pdf.body);
    const flat = text.replace(/\s+/g, "");
    expect(text, "標題：專案名稱＋監控報表").toContain(`${f.name} 監控報表`);
    for (const label of ["時間範圍：", "範圍：全部批次", "產生時間（UTC）："]) expect(text).toContain(label);
    for (const section of ["summary", "runs", "tasks", "alerts"]) expect(text.split("\n"), `區段 ${section}`).toContain(section);
    expect(flat).toContain("totalTokens3720");
    for (const zh of ["基礎", "核心", "初始化", "設定", "實作"]) expect(text, `中文目標／任務名 ${zh} 要能抽出`).toContain(zh);
    expect(text).toContain("（無資料）"); // alerts 區段沒有資料

    // 與 CSV 同四區段、同數字
    const csv = await fetchRaw(request, "viewer", `${base}?format=csv`, { Accept: "text/csv" });
    expect(csv.status).toBe(200);
    expect(csv.headers["content-type"]).toContain("text/csv");
    const csvText = csv.body.toString("utf-8");
    for (const section of ["summary", "runs", "tasks", "alerts"]) expect(csvText).toContain(`#section,${section}`);
    expect(csvText).toContain("totalTokens,3720,");

    // 只看一個批次；Accept 不符也不回 406（以 format 為準）
    const one = await fetchRaw(request, "viewer", `${base}?format=pdf&runId=${runId}`, { Accept: "text/csv" });
    expect(one.status).toBe(200);
    expect(one.headers["content-type"]).toBe("application/pdf");
    expect(extractPdfText(one.body)).toContain(`範圍：${runId}`.slice(0, 12)); // 範圍行以 runId 為值（長 UUID 可能被換行，只比前綴）
    // 不支援的格式、不存在的專案、未認證
    const bad = await call(request, "viewer", "GET", `${base}?format=docx`);
    expect([bad.status, bad.json.reason]).toEqual([400, "不支援的報表格式"]);
    expect((await call(request, "viewer", "GET", `/api/v1/monitor/projects/00000000-0000-4000-8000-000000000000/report?format=pdf`)).status).toBe(404);
    expect((await fetch(`${API_URL}${base}?format=pdf`)).status).toBe(401);
  });

  test("列 7｜escalation 跨批次不被吞：兩批在同一步驟失敗、第一批告警不確認 → 第二批照樣新增告警（subject 帶各自的 runId）（C-7）", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA W5 升級跨批"), kind: "A", level: 4, failTasks: [1] });
    const run1 = await start(request, f);
    const failed1 = await finish(request, run1);
    expect(failed1.status).toBe("FAILED");
    const first = (await alertsOf(request, f.projectId)).filter((a) => a.rule === "ENGINE_ESCALATION");
    expect(first.map((a) => [a.subject, a.acknowledged])).toEqual([[`step:${run1}:G1-T1`, false]]);

    // 第一批的告警維持未確認（不呼叫 acknowledge），直接開第二批：同一個 stepId＝G1-T1 再失敗
    const run2 = await start(request, f);
    expect(run2).not.toBe(run1);
    const failed2 = await finish(request, run2);
    expect(failed2.status).toBe("FAILED");
    const both = (await alertsOf(request, f.projectId)).filter((a) => a.rule === "ENGINE_ESCALATION");
    expect(both.map((a) => a.subject).sort(), "兩批各一筆，subject 分別帶各自的 runId（新→舊）").toEqual([`step:${run1}:G1-T1`, `step:${run2}:G1-T1`].sort());
    expect(both.every((a) => !a.acknowledged)).toBe(true);
  });

  test("列 7（續）｜同一批次內同一步驟再次升級仍被去重：第二步失敗 → 審核 RETRY（還原後同批次再失敗）→ 出現第二個審核項，但 ENGINE_ESCALATION 告警仍只有一筆", async ({ request }) => {
    // 第一步失敗的 RETRY 會改開後續批次（沒有還原點，契約 §1.2.10），所以讓第二步失敗：T1 完成並留下 after-G1-T1 斷點，RETRY 還原到那裡、同批次重跑
    const f = await createFixture(request, { name: nm("QA W5 升級同批去重"), kind: "A", level: 4, failTasks: [2] });
    const run = await start(request, f);
    const failed = await finish(request, run);
    const first = failed.pendingReviews![0];
    expect((await alertsOf(request, f.projectId)).filter((a) => a.rule === "ENGINE_ESCALATION").map((a) => a.subject)).toEqual([`step:${run}:G1-T2`]);
    const retry = await call(request, "operator", "POST", `/api/v1/executions/${run}/review/${first.id}`, { decision: "RETRY" });
    expect(retry.status).toBe(204);
    expect(retry.headers["x-follow-up-run-id"], "同批次還原重跑：不開後續批次").toBeUndefined();
    const again = await poll(
      () => getRun(request, run),
      (r) => r.status === "FAILED" && (r.pendingReviews ?? []).some((x) => x.id !== first.id),
      "RETRY 後同批次再失敗並建立第二個審核項",
      120_000,
    );
    expect(again.pendingReviews).toHaveLength(1);
    const rows = (await alertsOf(request, f.projectId)).filter((a) => a.rule === "ENGINE_ESCALATION");
    expect(
      rows.map((a) => a.subject),
      "同批次同步驟的第二次升級被去重",
    ).toEqual([`step:${run}:G1-T2`]);
  });

  test("列 8｜執行中刪除：批次 RUNNING／PAUSED 時刪目標與任務一律 409 project_executing（details 帶 projectId／runId）；批次進終態後同一請求 204（C-8）", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA W5 執行中刪除"), kind: "B", level: 1 }); // 5 個任務；等級 1：第一步後暫停
    const runId = await start(request, f, 1);
    const g2 = f.goalIds[1];
    const t5 = f.taskIds[4];
    const expect409 = async (url: string, what: string) => {
      const r = await call(request, "operator", "DELETE", url);
      expect([r.status, r.json.reason], `${what} → ${JSON.stringify(r.json).slice(0, 200)}`).toEqual([409, "project_executing"]);
      expect(r.json.details, what).toMatchObject({ projectId: f.projectId, runId });
    };
    // 批次剛建立（INITIALIZING／RUNNING）
    await expect409(`/api/v1/goals/${g2}`, "RUNNING 時刪目標");
    await expect409(`/api/v1/tasks/${t5}`, "RUNNING 時刪尚未開始的任務");
    await waitRun(request, runId, ["PAUSED"], 90_000);
    await expect409(`/api/v1/goals/${g2}`, "PAUSED 時刪目標");
    await expect409(`/api/v1/tasks/${t5}`, "PAUSED 時刪尚未開始的任務");
    await expect409(`/api/v1/tasks/${f.taskIds[0]}`, "PAUSED 時刪已完成的任務");
    // 啟動執行被擋是另一組中文 reason（專案正在執行中／同專案同路徑已有執行中的批次），不是這裡的英文識別字（契約 §0.3 第 5 點，兩者不可混用）
    const exec = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, execBody(1));
    expect(exec.status).toBe(409);
    expect(["專案正在執行中", "同專案同路徑已有執行中的批次"]).toContain(exec.json.reason);
    // 取消批次（終態）後同一請求 204
    expect((await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`)).status).toBe(200);
    await waitRun(request, runId, ["CANCELLED"], 60_000);
    expect((await call(request, "operator", "DELETE", `/api/v1/tasks/${t5}`)).status, "終態後刪任務").toBe(204);
    expect((await call(request, "operator", "DELETE", `/api/v1/goals/${g2}`)).status, "終態後刪目標").toBe(204);
  });

  test("列 9｜手動重試不受 maxRetries 限制：ESCALATED 任務連按兩次重試都 200，retryCount 每次增加且大於 maxRetries，不回 409（C-9）", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA W5 手動重試"), kind: "A", level: 4, failTasks: [1] }); // maxRetries=1
    const t1 = f.taskIds[0];
    const taskOf = async () => dataOf<{ status: string; retryCount: number; maxRetries: number }>(await call(request, "viewer", "GET", `/api/v1/tasks/${t1}`));
    await finish(request, await start(request, f));
    const before = await taskOf();
    expect(before).toMatchObject({ status: "ESCALATED", maxRetries: 1 });
    const seen: number[] = [before.retryCount];
    for (let i = 0; i < 2; i += 1) {
      const r = await call(request, "operator", "POST", `/api/v1/tasks/${t1}/retry`);
      expect(r.status, `第 ${i + 1} 次手動重試 → ${JSON.stringify(r.json).slice(0, 200)}`).toBe(200);
      const d = dataOf<{ status: string; retryCount: number; maxRetries: number }>(r);
      expect(d.retryCount, "每次手動重試 retryCount 都增加").toBeGreaterThan(seen.at(-1)!);
      expect(d.retryCount, "且大於 maxRetries（不受上限限制）").toBeGreaterThan(d.maxRetries);
      expect(d.status).toBe("QUEUED");
      seen.push(d.retryCount);
      if (i === 0) {
        // 讓它再失敗一次（任務仍帶 [FAIL_ME]），才能再次重試
        await finish(request, await start(request, f));
        expect((await taskOf()).status).toBe("ESCALATED");
        seen[seen.length - 1] = (await taskOf()).retryCount;
      }
    }
    expect(seen, `retryCount 序列＝${seen.join("→")}`).toEqual([...seen].sort((x, y) => x - y));
  });

  test("列 11｜批次列表 bridgeStatus：pause 後立即列出 PAUSING（status 仍 RUNNING）、cancel 後 CANCELLING；終態批次的 bridgeStatus 等於 status（C-11）", async ({ request }) => {
    const listOf = async (projectId: string): Promise<Array<{ id: string; status: string; bridgeStatus?: string | null }>> =>
      dataOf<{ content: Array<{ id: string; status: string; bridgeStatus?: string | null }> }>(
        await call(request, "viewer", "GET", `/api/v1/projects/${projectId}/executions?sort=runNumber,desc&size=10`),
      ).content;

    // PAUSING：Level 4 的 5 任務批次，執行中呼叫 pause，在步驟邊界生效前列出
    const p = await createFixture(request, { name: nm("QA W5 bridgeStatus 暫停"), kind: "B", level: 4 });
    const pRun = await start(request, p);
    await poll(
      () => getRun(request, pRun),
      (r) => r.status === "RUNNING",
      "批次進入 RUNNING",
      60_000,
    );
    const pause = await call(request, "operator", "POST", `/api/v1/executions/${pRun}/pause`);
    expect(pause.status).toBe(200);
    expect(dataOf<RunView>(pause)).toMatchObject({ status: "RUNNING", bridgeStatus: "PAUSING" });
    const seenPausing: string[] = [];
    for (let i = 0; i < 40; i += 1) {
      const row = (await listOf(p.projectId)).find((x) => x.id === pRun)!;
      seenPausing.push(`${row.status}/${row.bridgeStatus ?? "∅"}`);
      if (row.bridgeStatus === "PAUSING") break;
      if (row.status === "PAUSED") break;
      await new Promise((r) => setTimeout(r, 40));
    }
    expect(seenPausing.at(-1), `列表序列：${seenPausing.join("、")}`).toBe("RUNNING/PAUSING");
    await waitRun(request, pRun, ["PAUSED"], 60_000);
    expect((await listOf(p.projectId)).find((x) => x.id === pRun)).toMatchObject({ status: "PAUSED", bridgeStatus: "PAUSED" });
    expect((await call(request, "operator", "POST", `/api/v1/executions/${pRun}/cancel`)).status).toBe(200);
    await waitRun(request, pRun, ["CANCELLED"], 60_000);

    // CANCELLING：另一個專案執行中呼叫 cancel
    const c = await createFixture(request, { name: nm("QA W5 bridgeStatus 取消"), kind: "B", level: 4 });
    const cRun = await start(request, c);
    await poll(
      () => getRun(request, cRun),
      (r) => r.status === "RUNNING",
      "批次進入 RUNNING",
      60_000,
    );
    const cancel = await call(request, "operator", "POST", `/api/v1/executions/${cRun}/cancel`);
    expect(cancel.status).toBe(200);
    expect(dataOf<RunView>(cancel)).toMatchObject({ status: "RUNNING", bridgeStatus: "CANCELLING" });
    const seenCancelling: string[] = [];
    for (let i = 0; i < 40; i += 1) {
      const row = (await listOf(c.projectId)).find((x) => x.id === cRun)!;
      seenCancelling.push(`${row.status}/${row.bridgeStatus ?? "∅"}`);
      if (row.bridgeStatus === "CANCELLING" || row.status === "CANCELLED") break;
      await new Promise((r) => setTimeout(r, 25));
    }
    expect(seenCancelling.at(-1), `列表序列：${seenCancelling.join("、")}`).toBe("RUNNING/CANCELLING");
    await waitRun(request, cRun, ["CANCELLED"], 60_000);
    // 終態：bridgeStatus 與 status 同名；專案其他終態批次也一樣
    for (const row of [...(await listOf(c.projectId)), ...(await listOf(p.projectId))]) expect(row.bridgeStatus, `${row.id} ${row.status}`).toBe(row.status);
  });

  test("列 12｜traceId 貫穿 Bridge：backend 回應的 X-Trace-Id 出現在 Bridge 日誌 POST /autoclaude/runs 那一行；Bridge 日誌每一行都有 trace_id；直連不帶標頭時自產並回帶（C-12）", async ({
    request,
  }) => {
    test.skip(!BRIDGE_LOG, "需要 E2E_BRIDGE_LOG（Bridge 以 BRIDGE_LOG_DIR 啟動時的 bridge.log 絕對路徑；見 README〈W5 複驗〉）");
    const f = await createFixture(request, { name: nm("QA W5 traceId"), kind: "A", level: 4 });
    const started = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, execBody());
    expect(started.status).toBe(201);
    const traceId = started.headers["x-trace-id"];
    expect(traceId, "backend 回應帶 X-Trace-Id").toBeTruthy();
    expect(started.json.traceId, "封包的 traceId 與標頭同值").toBe(traceId);
    const runId = dataOf<{ id: string }>(started).id;
    await waitRun(request, runId, ["COMPLETED"], 90_000);

    const lines = (): string[] =>
      readFileSync(BRIDGE_LOG, "utf-8")
        .split("\n")
        .filter((l) => l.trim() !== "");
    const hit = await poll(
      async () => lines().filter((l) => l.includes(`trace_id=${traceId} `)),
      (h) => h.some((l) => l.includes("POST /autoclaude/runs")),
      `Bridge 日誌出現 trace_id=${traceId} 的 POST /autoclaude/runs`,
      20_000,
      500,
    );
    expect(
      hit.some((l) => l.includes("POST /autoclaude/runs") && l.includes(" 201")),
      hit.join("\n"),
    ).toBe(true);
    expect(hit.length, "同一個 trace id 還貫穿該批次的其他 Bridge 請求（事件串流、狀態讀取）").toBeGreaterThanOrEqual(2);
    // 每一行日誌（含啟動行、uvicorn 存取行、引擎匯入警告）都有 trace_id 欄位
    const bare = lines().filter((l) => !/ trace_id=\S+/.test(l));
    expect(bare, `沒有 trace_id 的日誌行：${bare.slice(0, 3).join(" ⏎ ")}`).toEqual([]);
    // 直連 Bridge：不帶標頭 → 自產 uuid4 並回帶；帶合法標頭 → 原樣回帶
    const bare1 = await fetch(`${BRIDGE_URL}/health`);
    expect(bare1.status).toBe(200);
    expect(bare1.headers.get("x-trace-id") ?? "").toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    const given = `w5qa-${RUN}`;
    const echoed = await fetch(`${BRIDGE_URL}/health`, { headers: { "X-Trace-Id": given } });
    expect(echoed.headers.get("x-trace-id")).toBe(given);
    const deepLine = await poll(
      async () => lines().filter((l) => l.includes(`trace_id=${given} `)),
      (h) => h.length > 0,
      "直連請求的日誌行",
      10_000,
      500,
    );
    expect(deepLine[0]).toContain("GET /health");
  });

  test.describe("列 2～3｜專案復原（C-3）", () => {
    test("刪除 → 已刪除清單 → 復原：狀態回到刪除前、連帶軟刪的目標與任務回來、刪除專案前就單獨刪掉的不回來；再列得到、已刪除清單不再有；audit_log 記一筆", async ({ request }) => {
      const f = await createFixture(request, { name: nm("QA W5 復原"), kind: "A", level: 4 }); // G1：T1、T2；G2：T3
      expect((await call(request, "operator", "DELETE", `/api/v1/tasks/${f.taskIds[1]}`)).status, "先單獨刪 T2").toBe(204);
      expect((await call(request, "operator", "DELETE", `/api/v1/goals/${f.goalIds[1]}`)).status, "先單獨刪 G2（連同 T3）").toBe(204);
      const before = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`));
      expect((await call(request, "operator", "DELETE", `/api/v1/projects/${f.projectId}`)).status).toBe(204);
      expect((await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).status, "刪除後詳情 404").toBe(404);

      const deleted = await call(request, "operator", "GET", `/api/v1/projects?deleted=true&q=${encodeURIComponent(f.name)}&size=10`);
      expect(deleted.status).toBe(200);
      const row = dataOf<{ content: Array<{ id: string; deletedAt?: string | null; status: string }> }>(deleted).content.find((p) => p.id === f.projectId);
      expect(row, "已刪除清單含該專案").toBeTruthy();
      expect(Date.parse(row!.deletedAt ?? ""), "deletedAt 非 null 且是剛才").toBeGreaterThan(Date.now() - 120_000);
      const live = dataOf<{ content: Array<{ id: string }> }>(await call(request, "operator", "GET", `/api/v1/projects?q=${encodeURIComponent(f.name)}&size=10`)).content;
      expect(
        live.some((p) => p.id === f.projectId),
        "一般清單不含已刪除專案",
      ).toBe(false);

      const restored = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/restore`);
      expect(restored.status, JSON.stringify(restored.json).slice(0, 300)).toBe(200);
      const detail = dataOf<{ id: string; status: string; goals?: Array<{ id: string }> }>(restored);
      expect(detail.id).toBe(f.projectId);
      expect(detail.status, "狀態與刪除前相同").toBe(before.status);
      expect((await call(request, "viewer", "GET", `/api/v1/goals/${f.goalIds[0]}`)).status, "連帶軟刪的目標回來").toBe(200);
      expect((await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[0]}`)).status, "連帶軟刪的任務回來").toBe(200);
      expect((await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[1]}`)).status, "專案刪除前就單獨刪掉的任務不回來").toBe(404);
      expect((await call(request, "viewer", "GET", `/api/v1/goals/${f.goalIds[1]}`)).status, "專案刪除前就單獨刪掉的目標不回來").toBe(404);
      expect((await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[2]}`)).status, "該目標底下的任務也不回來").toBe(404);
      expect((await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).status).toBe(200);
      const live2 = dataOf<{ content: Array<{ id: string }> }>(await call(request, "operator", "GET", `/api/v1/projects?q=${encodeURIComponent(f.name)}&size=10`)).content;
      expect(
        live2.some((p) => p.id === f.projectId),
        "復原後一般清單又列得到",
      ).toBe(true);
      const deleted2 = dataOf<{ content: Array<{ id: string }> }>(await call(request, "operator", "GET", `/api/v1/projects?deleted=true&q=${encodeURIComponent(f.name)}&size=10`)).content;
      expect(
        deleted2.some((p) => p.id === f.projectId),
        "已刪除清單不再有",
      ).toBe(false);
      expect(detail.goals?.map((g) => g.id) ?? [f.goalIds[0]]).toEqual([f.goalIds[0]]);

      if (PG_CONTAINER) {
        // 審計落庫：POST …/restore、200、實體 project；（action=project.restore 另在 backend 的 audit JSON 日誌行，不在表內欄位）
        const n = await psql(
          `select count(*) from console.audit_log where method='POST' and path='/api/v1/projects/${f.projectId}/restore' and http_status=200 and entity_id='${f.projectId}' and subject='operator'`,
        );
        expect(Number(n), "audit_log 有這次復原").toBe(1);
      }
    });

    test("restore 的錯誤路徑：沒被刪 409 project_not_deleted、逾保留期 409 restore_window_expired（retentionDays=30）、亂 id 404、viewer 403；viewer 查已刪除清單 403", async ({ request }) => {
      test.skip(!PG_CONTAINER, "需要 E2E_PG_CONTAINER：把 deleted_at 撥到 31 天前要直接改資料庫（見 README〈W5 複驗〉）");
      const f = await createFixture(request, { name: nm("QA W5 復原錯誤"), kind: "A", level: 4 });
      // ① 沒被刪
      const notDeleted = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/restore`);
      expect([notDeleted.status, notDeleted.json.reason]).toEqual([409, "project_not_deleted"]);
      // ② 逾期：刪除後把 deleted_at 改到 31 天前
      expect((await call(request, "operator", "DELETE", `/api/v1/projects/${f.projectId}`)).status).toBe(204);
      expect(await psql(`update console.projects set deleted_at = now() - interval '31 days' where id = '${f.projectId}' returning id`)).toContain(f.projectId);
      const expired = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/restore`);
      expect([expired.status, expired.json.reason]).toEqual([409, "restore_window_expired"]);
      expect((expired.json.details as { retentionDays: number }).retentionDays).toBe(30);
      expect((await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).status, "逾期的專案不會因為復原失敗而復活").toBe(404);
      // ③ 隨機 uuid
      expect((await call(request, "operator", "POST", `/api/v1/projects/6f1c2a3e-0000-4000-8000-0000000000aa/restore`)).status).toBe(404);
      // ④ viewer
      const viewerRestore = await call(request, "viewer", "POST", `/api/v1/projects/${f.projectId}/restore`);
      expect([viewerRestore.status, viewerRestore.json.reason]).toEqual([403, "ACCESS_DENIED"]);
      const viewerList = await call(request, "viewer", "GET", "/api/v1/projects?deleted=true");
      expect([viewerList.status, viewerList.json.reason]).toEqual([403, "ACCESS_DENIED"]);
      expect((await call(request, "operator", "GET", "/api/v1/projects?deleted=maybe")).status, "deleted 非布林 → 400").toBe(400);
    });
  });
});
