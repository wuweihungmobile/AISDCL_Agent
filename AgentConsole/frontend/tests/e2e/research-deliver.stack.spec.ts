import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

import { ADMIN, BASE, STACK_ON, approveViaApi, call, dataOf, detailOf, eventSeqs, hasCreds, newResearchKit, open, projectPath, signIn } from "../helpers/research-stack";

/**
 * 研發工作流（ResearchToPRD P2）整合 E2E（TCS-ResearchToPRD-P2-20261107 AT-962-28-4、28-5、28-7、28-8；AC-962-28；PKG-INT-P2）——
 * **實機冒煙，不是每個 commit 的閘**（沿 `*.stack.spec.ts` 形態）。兩種載具（兩者不同時掛）：
 *   - Docker mock-only（28-7、28-8）：真 console-api＋容器內 Bridge（mock claude）＋真 PostgreSQL；容器沒有 repo 寫入掛載與 gh，只驗唯讀面與負控；
 *   - 本機模式（28-4、28-5；`E2E_LOCAL_BRIDGE=1`）：Bridge 跑在主機（拋棄式 clone、假 gh），backend 的 `ENGINE_BRIDGE_URL` 指向主機 Bridge。
 * 啟用條件（缺項＝整支或該案略過並印 TOOL-ABSENCE，不當通過；INT 證據須零略過）：`E2E_STACK=1`、`E2E_ADMIN_USER`／`E2E_ADMIN_PASSWORD`；
 *   本機模式案例另需 `E2E_LOCAL_BRIDGE=1`、`E2E_LOCAL_TRACK_A=1`（`BRIDGE_REPO_ROOT` 是拋棄式 clone）。
 * 選配：`E2E_PG_CONTAINER`（預設 `aisdlc-pg-primary`）、`E2E_PG_USER`／`E2E_PG_DB`（預設 `aisdlc`）：資料庫逐位核對走 `docker exec psql`。
 * 本檔不改任何產品碼與設定；所有測試建立的研究專案在結束時封存。
 */
const LOCAL_BRIDGE = process.env.E2E_LOCAL_BRIDGE === "1";
const TRACK_A = process.env.E2E_LOCAL_TRACK_A === "1";
const PG_CONTAINER = process.env.E2E_PG_CONTAINER ?? "aisdlc-pg-primary";
const PG_USER = process.env.E2E_PG_USER ?? "aisdlc";
const PG_DB = process.env.E2E_PG_DB ?? "aisdlc";

const ABSENCE = !STACK_ON
  ? "TOOL-ABSENCE：未設 E2E_STACK=1（這支只對 Docker 全棧跑；見 tests/e2e/README.md〈研發工作流 Docker 全棧 E2E〉）"
  : !hasCreds(ADMIN)
    ? "TOOL-ABSENCE：缺環境變數 E2E_ADMIN_USER／E2E_ADMIN_PASSWORD"
    : "";
if (ABSENCE !== "") console.log(`[research-deliver.stack] ${ABSENCE}`);
test.skip(ABSENCE !== "", ABSENCE);

const { created, driveToGate0, archiveAll } = newResearchKit("research-deliver.stack");

test.afterAll(async ({ playwright }) => {
  const request = await playwright.request.newContext();
  try {
    await archiveAll(request);
  } finally {
    await request.dispose();
  }
});

/** 在 Postgres 容器內跑一句唯讀 SQL（`-At`）；沒有 docker CLI 回 null（呼叫端註記略過）。 */
function psql(sql: string): string | null {
  try {
    return execFileSync("docker", ["exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-At", "-c", sql], { encoding: "utf-8", timeout: 30_000 }).trim();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

type ErrorJson = { reason?: string; details?: { missing?: Array<{ item: string; reason: string }>; unmet?: string[] }; violations?: Array<{ field: string; rule: string }> };

/** 研究表逐位快照（列數＋該專案的交付列數）：負控前後必須相等。 */
function deliverySnapshot(id: string): string {
  const out = psql(
    `SELECT (SELECT count(*) FROM console.research_deliveries) || '|' || (SELECT count(*) FROM console.research_deliveries WHERE research_id = '${id}') || '|' || (SELECT count(*) FROM console.research_gate_decisions WHERE research_id = '${id}') || '|' || (SELECT count(*) FROM console.research_events WHERE research_id = '${id}') || '|' || (SELECT flow_step || '/' || flow_phase || '/' || flow_status FROM console.research_projects WHERE id = '${id}')`,
  );
  if (out === null) throw new Error("TOOL-ABSENCE：沒有 docker CLI，無法 docker exec psql（28-8 的 DB 逐位核對必須在場）");
  return out;
}

test("AT_962_28_8 Docker 容器模式負控：寫入端點（delivery/tag、delivery/pr、gates）一律被擋且研究表與游標零變化；Bridge 直呼 :tag 的真回應逐字記錄", async ({ request }) => {
  test.setTimeout(900_000);
  const project = await driveToGate0(request, "p2neg");
  await approveViaApi(request, project.id);
  const caps = dataOf<{ mode: string; repoWritable: boolean }>(await call(request, ADMIN, "GET", "/api/v1/research/capabilities"));
  expect(caps.mode, "Docker 全棧是 mock-only").toBe("mock-only");
  expect(caps.repoWritable, "容器內 monorepo 不可寫").toBe(false);
  const before = { db: deliverySnapshot(project.id), seqs: await eventSeqs(request, project.id), detail: await detailOf(request, project.id) };

  // TCS 字面（422 route_unsupported_in_deployment）與真棧的偏差：容器模式的研究專案永遠分流不成功（分流需 repo_writable），
  // 所以 console-api 的交付前置（no_console_project）在 Bridge 之前就 409；Bridge 自己對未分流專案也先答 409 route_not_succeeded。
  // 422 route_unsupported_in_deployment 只在「分流已成功、之後部署變唯讀」才會出現（Bridge pytest AT-962-18-E-6 以模擬覆蓋）。這裡記錄真棧的實際回應，並以零變化為判準。
  const tag = await call(request, ADMIN, "POST", projectPath(project.id, "/delivery/tag"), { tagName: "v9.9.9", push: false });
  const tagJson = tag.json as ErrorJson;
  console.log(`[28-8] POST delivery/tag → HTTP ${tag.status} ${JSON.stringify(tag.json)}`);
  expect([tag.status, tagJson.reason], `delivery/tag → ${JSON.stringify(tag.json)}`).toEqual([409, "fsm_state_conflict"]);
  expect(tagJson.details?.unmet, "console-api 前置：沒有 Console 專案").toEqual(["no_console_project"]);
  const pr = await call(request, ADMIN, "POST", projectPath(project.id, "/delivery/pr"), { bodyPreviewAck: true });
  console.log(`[28-8] POST delivery/pr → HTTP ${pr.status} ${JSON.stringify(pr.json)}`);
  expect([pr.status, (pr.json as ErrorJson).reason], "delivery/pr：Bridge 透傳 409").toEqual([409, "fsm_state_conflict"]);
  const gates = await call(request, ADMIN, "POST", projectPath(project.id, "/gates"), {
    decisionId: "00000000-0000-4000-8000-000000000028",
    gate: "PR_REVIEW",
    result: "PASS",
    reason: "INT-P2 容器模式負控",
    reviewerIndependent: true,
  });
  console.log(`[28-8] POST gates → HTTP ${gates.status} ${JSON.stringify(gates.json)}`);
  expect([gates.status, (gates.json as ErrorJson).details?.unmet], "gates：前置不成立").toEqual([409, ["no_console_project"]]);

  // Bridge 直呼（容器內；寫入權杖取容器自己的環境變數、不外洩）：真回應逐字記錄
  const direct = execFileSync(
    "docker",
    [
      "exec",
      "aisdlc-engine-bridge",
      "python",
      "-c",
      "import os,json,urllib.request,sys,uuid\nb=json.dumps({'tag_name':'v9.9.9','approver':'admin@example.com','push':False,'run_id':str(uuid.uuid4()),'requested_by':'admin@example.com'}).encode()\nr=urllib.request.Request('http://127.0.0.1:8081/research/projects/'+sys.argv[1]+':tag',data=b,method='POST',headers={'Content-Type':'application/json','X-Bridge-Token':os.environ['BRIDGE_RESEARCH_WRITE_TOKEN']})\ntry:\n  x=urllib.request.urlopen(r);print(x.status,x.read().decode()[:500])\nexcept urllib.error.HTTPError as e:\n  print(e.code,e.read().decode()[:500])",
      project.id,
    ],
    { encoding: "utf-8" },
  ).trim();
  console.log(`[28-8] Bridge 容器內直呼 :tag → ${direct}`);
  expect(direct.startsWith("409 "), "Bridge 對未分流專案先答 409 route_not_succeeded").toBe(true);
  test.info().annotations.push({
    type: "TCS 偏差",
    description: "28-8 字面要求 422 route_unsupported_in_deployment；真棧容器模式下專案分流不可能成功，故實際為 409（console-api）／409 route_not_succeeded（Bridge）；零變化判準成立",
  });

  const after = { db: deliverySnapshot(project.id), seqs: await eventSeqs(request, project.id), detail: await detailOf(request, project.id) };
  expect(after.db, "研究交付列、閘決定列、事件數與游標（docker exec psql 逐位）前後相等").toBe(before.db);
  expect(after.seqs, "研究事件帳零新增").toEqual(before.seqs);
  expect([after.detail.flowStep, after.detail.flowPhase, after.detail.flowStatus], "游標原地不動").toEqual([before.detail.flowStep, before.detail.flowPhase, before.detail.flowStatus]);
});

test("AT_962_28_7 Docker mock-only：看板、自癒、交付概覽、追溯表的唯讀面可驗；步驟 4／5 超前導回游標步；沒有任何寫入 repo 的動作", async ({ page, request }) => {
  test.setTimeout(900_000);
  const project = await driveToGate0(request, "p2ro");
  await approveViaApi(request, project.id);
  const before = { db: deliverySnapshot(project.id), seqs: await eventSeqs(request, project.id) };
  for (const [name, suffix] of [
    ["kanban", "/kanban"],
    ["healing", "/healing"],
    ["delivery", "/delivery"],
    ["traceability", "/delivery/traceability"],
  ] as const) {
    const reply = await call(request, ADMIN, "GET", projectPath(project.id, suffix));
    console.log(`[28-7] GET ${name} → HTTP ${reply.status} ${JSON.stringify(reply.json).slice(0, 400)}`);
  }
  const kanban = await call(request, ADMIN, "GET", projectPath(project.id, "/kanban"));
  expect([200, 409], `kanban（尚無分流）→ ${JSON.stringify(kanban.json)}`).toContain(kanban.status);
  const healing = await call(request, ADMIN, "GET", projectPath(project.id, "/healing"));
  expect(healing.status, `healing → ${JSON.stringify(healing.json)}`).toBe(200);
  const delivery = await call(request, ADMIN, "GET", projectPath(project.id, "/delivery"));
  expect(delivery.status, `delivery → ${JSON.stringify(delivery.json)}`).toBe(200);
  expect(dataOf<{ containerMode: boolean }>(delivery).containerMode, "交付概覽標示容器模式").toBe(true);
  const trace = await call(request, ADMIN, "GET", projectPath(project.id, "/delivery/traceability"));
  expect([200, 409], `traceability → ${JSON.stringify(trace.json)}`).toContain(trace.status);

  await signIn(page, request, ADMIN);
  for (const step of ["build", "deliver"] as const) {
    await open(page, request, `${BASE}/research/${project.id}?step=${step}`);
    await expect(page, `超前的 ?step=${step} 導回游標所在步`).toHaveURL(/step=route/, { timeout: 30_000 });
    await expect(page.getByTestId("route-panel")).toBeVisible({ timeout: 60_000 });
  }
  expect(deliverySnapshot(project.id), "唯讀面不寫任何研究表").toBe(before.db);
  expect(await eventSeqs(request, project.id), "事件帳零新增").toEqual(before.seqs);
  // 容器內的 repo 面唯讀：/repo 只有唯讀掛載（SI 用的 tools、docs/06_quality、.git 局部），沒有寫入能力；可寫掛載只有 /workspace、/app/logs、/si-audit
  const probe = execFileSync("docker", ["exec", "aisdlc-engine-bridge", "sh", "-c", "touch /repo/.int_p2_probe 2>/dev/null && echo WRITABLE || echo READ_ONLY"], { encoding: "utf-8" }).trim();
  console.log(`[28-7] 容器內 /repo 寫入探測：${probe}`);
  expect(probe, "容器內 /repo 不可寫").toBe("READ_ONLY");
  const mounts = execFileSync("docker", ["inspect", "aisdlc-engine-bridge", "--format", "{{range .Mounts}}{{.Destination}}={{.RW}};{{end}}"], { encoding: "utf-8" }).trim();
  console.log(`[28-7] 容器掛載（目的地=可寫）：${mounts}`);
  expect(
    mounts.split(";").filter((m) => m.endsWith("=true") && m.startsWith("/repo")),
    "沒有可寫的 /repo 掛載",
  ).toEqual([]);
});

// ── 本機模式案例（第二套拋棄式棧：project r2p2int；Bridge 在主機 local mode；見 INT 證據檔〈第二套棧〉）──────────────────────────────
const PYTHON = process.env.INT_P2_PYTHON ?? "";
const BRIDGE_DIR = process.env.INT_P2_BRIDGE_DIR ?? "";
const LOCAL_ABSENCE = !LOCAL_BRIDGE
  ? "TOOL-ABSENCE：未設 E2E_LOCAL_BRIDGE=1（本機模式案例需第二套棧加主機 Bridge）"
  : !TRACK_A
    ? "TOOL-ABSENCE：未設 E2E_LOCAL_TRACK_A=1（BRIDGE_REPO_ROOT 須是拋棄式 clone）"
    : PYTHON === "" || BRIDGE_DIR === ""
      ? "TOOL-ABSENCE：缺 INT_P2_PYTHON／INT_P2_BRIDGE_DIR（Given 佈置借用 engine-bridge 的整合測試助手）"
      : "";

/** Given 佈置借用 `engine-bridge/tests/test_research_int_p2.py` 的助手（分流、構造 Stage-2、劇本審查等），回最後一行 JSON。 */
function pyHelper(call_: string, ...args: string[]): Record<string, unknown> {
  const code = `import json,sys;sys.path.insert(0,'.');import app.main;from tests import test_research_int_p2 as m;print(json.dumps(${call_},default=str))`;
  const out = execFileSync(PYTHON, ["-c", code, ...args], { cwd: BRIDGE_DIR, encoding: "utf-8", timeout: 900_000, env: process.env });
  return JSON.parse(out.trim().split("\n").at(-1) ?? "{}") as Record<string, unknown>;
}

test("AT_962_28_4 本機模式（真棧）：引擎真重試耗盡成 ESCALATED 後，步驟 4 彈窗出現，決定走既有 review 端點（review_requests 入決定欄、audit_log 一列、不寫 research_gate_decisions）", async ({
  page,
  request,
}) => {
  test.skip(LOCAL_ABSENCE !== "", LOCAL_ABSENCE);
  test.setTimeout(1_200_000);
  // 構造：內環鍵 Stage-2 凍結（框架 CLI＋:freeze）；引擎真、claude 為 mock：run 重試耗盡
  const made = pyHelper("m.stack_setup(sys.argv[1], sys.argv[2])", "escalated", "e4") as { rid: string; pid: string; runId: string; reviewId: string; kind: string; status: string };
  created.push(made.rid);
  console.log(`[28-4] 構造＋引擎真：${JSON.stringify({ rid: made.rid, runId: made.runId, reviewId: made.reviewId, kind: made.kind, status: made.status })}`);
  expect([made.kind, made.status]).toEqual(["ESCALATED", "FAILED"]);
  const gatesBefore = psql(`SELECT count(*) FROM console.research_gate_decisions WHERE research_id = '${made.rid}'`);
  const auditBefore = psql(`SELECT count(*) FROM console.audit_log WHERE method = 'POST' AND path LIKE '%${made.reviewId}%'`);
  if (gatesBefore === null || auditBefore === null) throw new Error("TOOL-ABSENCE：沒有 docker CLI，無法 docker exec psql");

  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${made.rid}?step=build`);
  const modal = page.getByTestId("decision-modal");
  await expect(modal).toBeVisible({ timeout: 90_000 });
  await expect(modal.getByTestId("decision-kind")).toHaveAttribute("data-kind", "ESCALATED");
  await expect(page.getByTestId("kanban-board")).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("28-4-escalated-modal.png") });
  await modal.getByTestId("decision-REJECT").click();
  await modal.getByTestId("decision-confirm").click();
  // 決定送出後，ESCALATED 那一項消失（引擎另回報的「升級事件」是 info-only 的第二項，沒有決定鈕；稍後處理即可）
  await expect(modal.getByTestId("decision-kind")).not.toHaveAttribute("data-kind", "ESCALATED", { timeout: 30_000 });

  const review = psql(`SELECT status || '|' || coalesce(decided_by,'') || '|' || (decided_at IS NOT NULL)::text FROM console.review_requests WHERE id = '${made.reviewId}'`);
  console.log(`[28-4] review_requests 決定欄：${review}`);
  expect(review, "review_requests 入決定欄").toMatch(/^[A-Z]+\|admin\|true$/);
  expect(Number(psql(`SELECT count(*) FROM console.audit_log WHERE method = 'POST' AND path LIKE '%${made.reviewId}%'`)) - Number(auditBefore), "audit_log 恰一列").toBe(1);
  expect(psql(`SELECT count(*) FROM console.research_gate_decisions WHERE research_id = '${made.rid}'`), "不寫 research_gate_decisions").toBe(gatesBefore);
});

test("AT_962_28_5 本機模式：自看板 UI 發起 MINOR SCR，起草與審查走研究劇本，Gate 0 為 API 代驗（approveViaApi），舊凍結版保留、新 digest 入庫、SCR 轉 APPLIED", async ({ page, request }) => {
  test.skip(LOCAL_ABSENCE !== "", LOCAL_ABSENCE);
  test.setTimeout(1_200_000);
  const made = pyHelper("m.stack_setup(sys.argv[1], sys.argv[2])", "scr", "e5") as { rid: string; pid: string };
  created.push(made.rid);
  const versionsBefore = dataOf<Array<{ versionNo: number; sha256: string }>>(await call(request, ADMIN, "GET", projectPath(made.rid, "/prd/versions")));
  const gate0 = (): string[] =>
    (psql(`SELECT frozen_digests::text FROM console.research_gate_decisions WHERE research_id = '${made.rid}' AND gate = 'GATE0' AND decision = 'APPROVED' ORDER BY decided_at`) ?? "")
      .split("\n")
      .filter((x) => x !== "");
  const gate0Before = gate0();
  expect(gate0Before.length, "SCR 前只有一次 Gate 0 核准").toBe(1);

  // UI：看板的「發起規格變更（SCR）」→ MINOR、理由、章節、證據連結
  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${made.rid}?step=build`);
  await expect(page.getByTestId("kanban-board")).toBeVisible({ timeout: 90_000 });
  await page.getByTestId("scr-launch").first().click();
  const dialog = page.getByTestId("scr-dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("變更理由").fill("INT-P2 28-5：MINOR 規格變更演練，補一段修訂註記並重新審查。");
  // 缺陷 D-6：選項裡的章節標題文字（例如「1. 專案願景與目標 …」）送出會被 Bridge 以 affected_unknown 拒（422）；只有單純的 AC 編號選項（如 AC-001-1）合法，所以選那一項
  await dialog
    .getByTestId("scr-sections")
    .locator("label")
    .filter({ hasText: /^\s*AC-001-1\s*$/ })
    .first()
    .locator("input[type=checkbox]")
    .check();
  await dialog.getByPlaceholder("https://").fill("https://example.com/int-p2/evidence");
  const [scrResponse] = await Promise.all([page.waitForResponse((r) => r.url().includes("/scr") && r.request().method() === "POST"), dialog.getByTestId("scr-submit").click()]);
  console.log(`[28-5] UI 送出 SCR → HTTP ${scrResponse.status()} 請求 ${scrResponse.request().postData()} 回應 ${(await scrResponse.text()).slice(0, 400)}`);
  // 發起成功（202）後游標轉 studio／SCR_OPEN，頁面回到步驟 2 並顯示「SCR 進行中」（對話框隨步驟面板卸載，不會停在 scr-started）
  await expect(page.getByText("SCR 進行中").first()).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: test.info().outputPath("28-5-scr-started.png") });
  const scrs = dataOf<Array<{ scrNo: number; status: string; evidenceUrl: string | null }>>(await call(request, ADMIN, "GET", projectPath(made.rid, "/scr")));
  expect([scrs.length, scrs[0].status, scrs[0].evidenceUrl], "UI 發起：OPEN 且帶證據連結").toEqual([1, "OPEN", "https://example.com/int-p2/evidence"]);

  // 起草（人工存新版 PRD）與審查（劇本第 N 輪）借 Python 助手；Gate 0 一律經 approveViaApi（API 代驗，構造情境，證據標明）
  const drafted = pyHelper("m.scr_draft_review_cli(sys.argv[1])", made.rid);
  console.log(`[28-5] 起草＋審查（劇本）：${JSON.stringify(drafted)}；Gate 0 為 API 代驗`);
  const digests = await approveViaApi(request, made.rid);
  const applied = await call(request, ADMIN, "POST", projectPath(made.rid, `/scr/${scrs[0].scrNo}/apply`), {});
  console.log(`[28-5] apply → HTTP ${applied.status} ${JSON.stringify(applied.json).slice(0, 300)}`);
  expect(applied.status, `apply → ${JSON.stringify(applied.json)}`).toBe(200);
  const after = dataOf<Array<{ scrNo: number; status: string }>>(await call(request, ADMIN, "GET", projectPath(made.rid, "/scr")));
  expect(after[0].status, "SCR 轉 APPLIED").toBe("APPLIED");

  const gate0After = gate0();
  expect(gate0After.length, "新增一次 Gate 0 核准列").toBe(2);
  expect(gate0After[0], "舊凍結版（第一筆 Gate 0 的 digest）保留不變").toBe(gate0Before[0]);
  expect(gate0After[1], "新 spec_doc_digests 入庫且不同").not.toBe(gate0Before[0]);
  expect(Object.keys(digests).length, "approveViaApi 回新的凍結摘要").toBeGreaterThan(0);
  const versionsAfter = dataOf<Array<{ versionNo: number; sha256: string }>>(await call(request, ADMIN, "GET", projectPath(made.rid, "/prd/versions")));
  for (const v of versionsBefore) expect(versionsAfter.find((x) => x.versionNo === v.versionNo)?.sha256, `舊 PRD 版本 ${v.versionNo} 位元組（sha256）不變`).toBe(v.sha256);
  const reconcile = await call(request, ADMIN, "POST", projectPath(made.rid, "/reconcile"), {});
  console.log(`[28-5] 對帳：${JSON.stringify(reconcile.json).slice(0, 200)}`);
  expect(dataOf<{ consistent: boolean }>(reconcile).consistent, "對帳 consistent").toBe(true);
});

// ── V-D5／SSE 看板真棧量測（不是 AT，只記錄分佈與方法，不判達標；D-138 Q-9）──────────────────────────────────────────────────────
// 方法：開步驟 4 看板；Node 端（同一台機器的同一個時鐘 Date.now）在框架 CLI 動作返回時記 t0（Python 助手回傳完成時刻），
// 再以 100 ms 間隔輪詢看板文字，看到「狀態機狀態」欄出現預期現態的時刻記 t1；延遲＝t1－t0（含最多一個輪詢間隔的量測誤差）。
// 看板更新來源是 console-api 的輪詢重抓（內環 FSM 無推播，IFACE §1.5），所以這是「檔案改變到畫面更新」的全鏈上界。
const VD5_STEPS: Array<[string, string]> = [
  ["to_pr_review", "PR_REVIEW"],
  ["pr_fail", "IMPLEMENTATION"],
  ["to_pr_review", "PR_REVIEW"],
  ["pr_fail", "IMPLEMENTATION"],
  ["to_pr_review", "PR_REVIEW"],
  ["pr_pass", "RTM_VERIFY"],
  ["rtm_pass", "RELEASE_READY"],
];

test("V_D5 看板真棧量測（只記錄）：FSM 動作返回到看板「狀態機狀態」欄更新的毫秒數分佈", async ({ page, request }) => {
  test.skip(LOCAL_ABSENCE !== "", LOCAL_ABSENCE);
  test.setTimeout(1_800_000);
  const samples: number[] = [];
  const apiSamples: number[] = [];
  for (const round of [1, 2]) {
    const made = pyHelper("m.stack_setup(sys.argv[1], sys.argv[2])", "scr", `vd${round}`) as { rid: string };
    created.push(made.rid);
    await signIn(page, request, ADMIN);
    await open(page, request, `${BASE}/research/${made.rid}?step=build`);
    const board = page.getByTestId("kanban-board");
    await expect(board).toBeVisible({ timeout: 90_000 });
    const column = page.getByTestId("kanban-col-implement");
    const text = async (): Promise<string> => column.innerText();
    let before = await text();
    for (const [step, expected] of VD5_STEPS) {
      const done = pyHelper("m.fsm_step(sys.argv[1], sys.argv[2])", made.rid, step) as { doneMs: number };
      const t0 = done.doneMs;
      // API 層：console-api 的看板端點讀到新現態的時刻（Bridge 讀內環鍵 FSM 檔→console-api 組裝）；100 ms 間隔
      let tApi = 0;
      while (Date.now() - t0 < 30_000) {
        const reply = await call(request, ADMIN, "GET", projectPath(made.rid, "/kanban"));
        const state = dataOf<{ columns: { implement: { fsmState: string | null } } }>(reply).columns.implement.fsmState;
        if (state === expected) {
          tApi = Date.now();
          break;
        }
        await page.waitForTimeout(100);
      }
      // 畫面層：已開著的看板 DOM 出現新現態的時刻（不重新整理頁面）
      let t1 = 0;
      while (Date.now() - t0 < 30_000) {
        const now = await text();
        if (now.includes(expected) && !before.includes(expected)) {
          t1 = Date.now();
          before = now;
          break;
        }
        await page.waitForTimeout(100);
      }
      if (t1 === 0) before = await text();
      console.log(`[V-D5] 輪 ${round} 動作 ${step} → 預期 ${expected}：API ${tApi === 0 ? "30 秒內未見" : `${tApi - t0} ms`}；畫面（不重整）${t1 === 0 ? "30 秒內未見更新" : `${t1 - t0} ms`}`);
      if (tApi !== 0) apiSamples.push(tApi - t0);
      if (t1 !== 0) samples.push(t1 - t0);
    }
  }
  const dist = (xs: number[]): string => {
    const s = [...xs].sort((a, b) => a - b);
    return `${JSON.stringify(s)}；樣本 ${s.length}；中位數 ${s.length === 0 ? null : s[Math.floor((s.length - 1) / 2)]}；最大 ${s.at(-1) ?? null}`;
  };
  console.log(`[V-D5] API 層原始分佈（ms，已排序）：${dist(apiSamples)}`);
  console.log(`[V-D5] 畫面層（不重整）原始分佈（ms，已排序）：${dist(samples)}；方法：同機 Date.now、100 ms 輪詢；API 層與畫面層各自逾時 30 秒`);
  expect(apiSamples.length, "至少十次有效 API 層樣本（只記錄，不判延遲達標）").toBeGreaterThanOrEqual(10);
});
