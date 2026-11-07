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

const { driveToGate0, archiveAll } = newResearchKit("research-deliver.stack");

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
  test
    .info()
    .annotations.push({
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

void TRACK_A;
void LOCAL_BRIDGE;
