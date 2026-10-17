import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { Engine, PROJECT_ID, TASKS } from "./execFixture";
import { MonitorWorld } from "./monitorFixture";
import { collectConsoleErrors, compose, fail, installApiMock, paged, shellHandler, signInAs, type MockCall, type MockHandler, type MockReply } from "./mockApi";

/**
 * 整合輪 115（v1.5）的前端 route mock 版：SDD 治理的畫面與流程，不需要後端、不需要資料庫（契約 §1.10、§3.3.2、§4.7；UI-SDD-01～03）。
 *  ① 專案詳情「SDD 治理」區：綁定與 FSM 狀態、核准凍結（成功／503／409／422）、編輯 SDD 專案、VIEWER 唯讀、焦點歸還、ESCALATION 與恢復指令（含人工恢復後不再顯示）；
 *  ② 匯入到既有專案（targetProjectId）：選專案→解析→SDD 規格資訊與警告→signoff→確認匯入（併入）；
 *  ③ 執行頁：追溯覆蓋（諮詢）面板 200／404／非終態／沒有綁定，execute 201 的 warnings；
 *  ④ 監控頁 SDD 卡：專案模式（?projectId=）、階段進度、ESCALATION 橫幅與恢復指令複製。
 * 這裡驗「前端對契約形狀的行為」；與真後端、真 Bridge 對接的漂移由 QA 波另驗（p9 系列真後端 spec）。
 * 截圖：設環境變數 E2E_SHOTS_DIR 才會把重點畫面存成 png（不進 repo）。
 */
const PID = PROJECT_ID;
const NOW = "2026-10-17T08:30:12Z";
const SPEC_DIR = "/work/core/docs/03_testing/contracts";
const SPEC_FILE = `${SPEC_DIR}/TCS-Alpha.md`;
const SPEC_REL = "docs/03_testing/contracts/TCS-Alpha.md";
const PS_CMD =
  'Push-Location "C:\\sdd\\AISDLC_SDD_v9.99" -ErrorAction Stop; $env:SDD_STATE_DIR = "C:\\work\\core\\build\\reports\\fsm"; & "python" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "core-fsm" --to IMPLEMENTATION --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR; Pop-Location';
const SH_CMD =
  'cd "/sdd/AISDLC_SDD_v9.99" && SDD_STATE_DIR="/work/core/build/reports/fsm" "python" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "core-fsm" --to IMPLEMENTATION --reason "<人工原因>"';

type Json = Record<string, unknown>;

async function shot(page: Page, name: string): Promise<void> {
  const dir = process.env.E2E_SHOTS_DIR;
  if (!dir) return;
  await page.setViewportSize({ width: 1440, height: 2000 });
  await page.screenshot({ path: `${dir}/${name}.png` });
  await page.setViewportSize({ width: 1440, height: 900 });
}

/** 本機時區的「2026-10-17 09:02:03」（測試自己組，不引用被測程式）。 */
const pad = (n: number) => String(n).padStart(2, "0");
const localTime = (iso: string) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

function fsmJson(patch: Json = {}): Json {
  return {
    project: "core-fsm",
    fsmProject: "core-fsm",
    currentState: "HUMAN_PENDING",
    currentSprint: 1,
    sessionId: "sid-core",
    updatedAt: "2026-10-17T01:02:03+00:00",
    frozenStages: [],
    decisionTrace: [],
    source: "FSM-STATE-core-fsm.yaml",
    humanPending: { count: 1, items: [{ entered_at: "2026-10-17T01:00:00+00:00", reminder_hours: 72 }] },
    retryHistory: { count: 0, last: null },
    rtmCoverage: null,
    phase: { name: "HUMAN_GATE", order: 3, blocking: false, observation: false },
    escalationHistory: [],
    escalationProvenance: null,
    recovery: null,
    ...patch,
  };
}

const ESCALATED = (): Json =>
  fsmJson({
    currentState: "ESCALATION",
    humanPending: { count: 0, items: [] },
    phase: { name: "BLOCKED", order: 0, blocking: true, observation: false },
    escalationHistory: [{ triggered_at: "2026-10-17T01:05:00+00:00", trigger_reason: "AutoClaude 委派失敗：評估未通過", resolved_at: null, resolution: null, source: "autoclaude_delegated" }],
    escalationProvenance: { rule_id: "R-9.20.2", source: "autoclaude_delegated_failed", reason: "ENGINE-ESCALATION" },
    recovery: { target: "IMPLEMENTATION", powershell: PS_CMD, posix: SH_CMD },
  });

/** 人工恢復後（SDD session 跑了 resume-from-escalation）：回 IMPLEMENTATION、歷史末筆有 resolved_at；escalationProvenance 不清除、recovery 缺席（ADR-016 §5.3）。 */
const RECOVERED = (): Json =>
  fsmJson({
    currentState: "IMPLEMENTATION",
    humanPending: { count: 0, items: [] },
    phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: false },
    escalationHistory: [{ triggered_at: "2026-10-17T01:05:00+00:00", trigger_reason: "AutoClaude 委派失敗", resolved_at: "2026-10-17T01:30:00+00:00", resolution: "人工恢復" }],
    escalationProvenance: { source: "autoclaude_delegated_failed" },
    recovery: null,
  });

function projectJson(patch: Json = {}): Json {
  return {
    id: PID,
    name: "AISDLC Core Platform",
    executionPath: "/work/core",
    passCriteria: "- ok",
    description: "SDD 治理示範專案",
    status: "READY",
    autonomyLevel: 4,
    signedOff: true,
    signedOffBy: "operator",
    signedOffAt: NOW,
    goalsCount: 2,
    tasksCount: 3,
    tasksDone: 0,
    createdAt: NOW,
    updatedAt: NOW,
    createdBy: "admin",
    sddProject: "core-fsm",
    sddSpecDir: SPEC_DIR,
    sddSpecFile: SPEC_FILE,
    goals: [
      { id: "a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11", name: "基礎", status: "PENDING", sortOrder: 0, signedOff: true, taskCount: 2, completedTaskCount: 0 },
      { id: "a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e12", name: "核心", status: "PENDING", sortOrder: 1, signedOff: true, taskCount: 1, completedTaskCount: 0 },
    ],
    ...patch,
  };
}

const summaryOf = (p: Json): Json => ({
  id: p.id,
  name: p.name,
  executionPath: p.executionPath,
  status: p.status,
  autonomyLevel: p.autonomyLevel,
  signedOff: p.signedOff,
  goalsCount: p.goalsCount,
  tasksCount: p.tasksCount,
  tasksDone: p.tasksDone,
  updatedAt: p.updatedAt,
});

/** `GET /engines/sdd` 的回應（契約 §1.7.1、§1.10.4）。 */
function engineReply(fsm: Json | null, reason: string | null = null): MockReply {
  const entries = fsm ? [{ project: fsm.fsmProject, source: fsm.source, currentState: fsm.currentState, updatedAt: fsm.updatedAt }] : [];
  return {
    data: { available: true, reason: fsm ? null : reason, version: { latest: "AISDLC_SDD_v9.99", root: "/sdd/AISDLC_SDD_v9.99" }, projects: entries, fsm, checkedAt: new Date().toISOString() },
  };
}

/** 專案詳情頁的假後端：專案、FSM（可被核准凍結改寫）、核准凍結與編輯綁定端點。 */
class SddProjectWorld {
  project: Json = projectJson();
  fsm: Json | null = fsmJson();
  /** fsm 為 null 時 engines/sdd 回的 reason（預設＝尚無狀態檔） */
  reason: string | null = null;
  freezeMode: "ok" | "503" | "409-state" | "422-tcs" = "ok";
  bindingMode: "ok" | "409" = "ok";
  readonly engineCalls: MockCall[] = [];
  readonly freezeBodies: unknown[] = [];
  readonly bindingBodies: unknown[] = [];

  readonly handler: MockHandler = (call): MockReply => {
    const { method, path } = call;
    if (method === "GET" && path === `/api/v1/projects/${PID}`) return { data: this.project };
    if (method === "GET" && path === "/api/v1/engines/sdd") {
      this.engineCalls.push(call);
      return engineReply(this.fsm, this.reason);
    }
    if (method === "POST" && path === `/api/v1/projects/${PID}/sdd/freeze`) {
      this.freezeBodies.push(call.body);
      if (this.freezeMode === "503") return fail(503, { message: "SDD 寫入未啟用", reason: "sdd_write_disabled" });
      if (this.freezeMode === "409-state")
        return fail(409, { message: "FSM 不在 HUMAN_PENDING", reason: "sdd_fsm_state_conflict", details: { currentState: "SPEC_FROZEN", expectedState: "HUMAN_PENDING" } });
      if (this.freezeMode === "422-tcs")
        return fail(422, { message: "引擎拒絕", reason: "引擎拒絕此請求", details: { bridgeReason: "sdd_invalid_argument", violations: [{ field: "docs", rule: "missing_tcs" }] } });
      this.fsm = fsmJson({
        currentState: "SPEC_FROZEN",
        humanPending: { count: 0, items: [] },
        phase: { name: "FROZEN", order: 4, blocking: false, observation: false },
        frozenStages: [{ stage: "Stage-1", frozen_at: "2026-10-17T02:00:00+00:00", approved_by: "operator", spec_doc_digests: { [SPEC_REL]: `sha256:${"a".repeat(64)}` } }],
      });
      return { data: this.fsm };
    }
    if (method === "PUT" && path === `/api/v1/projects/${PID}/sdd-binding`) {
      this.bindingBodies.push(call.body);
      if (this.bindingMode === "409") {
        return fail(409, {
          message: "綁定衝突",
          reason: "sdd_binding_conflict",
          details: { cause: "already_bound_elsewhere", sddProject: "taken-fsm", holderProjectId: "1a2b3c4d-0000-4000-8000-000000000001" },
        });
      }
      this.project = { ...this.project, sddProject: (call.body as { sddProject: string | null }).sddProject };
      return { data: this.project };
    }
    return undefined;
  };
}

function expectClean(errors: string[], unhandled: string[]) {
  expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  expect(unhandled, "mock 沒處理的請求").toEqual([]);
}

async function openProject(page: Page, world: SddProjectWorld, opts: { role?: "ADMIN" | "OPERATOR" | "VIEWER" } = {}) {
  await signInAs(page, opts.role ?? "OPERATOR");
  const unhandled: string[] = [];
  const tail: MockHandler = (call) => {
    unhandled.push(`${call.method} ${call.path}`);
    return undefined;
  };
  const { calls } = await installApiMock(page, compose(world.handler, shellHandler(), tail));
  const errors = collectConsoleErrors(page);
  await page.goto(`/projects/${PID}`);
  await expect(page.getByTestId("project-title")).toHaveText("AISDLC Core Platform", { timeout: 60_000 });
  return { calls, errors, unhandled };
}

test.describe("專案詳情「SDD 治理」區（route mock；UI-SDD-01）", () => {
  test.setTimeout(120_000);

  test("已使用 SDD 的專案預設展開：綁定、標準鍵、規格目錄與檔、目前狀態、階段、凍結狀態、待人工、靜態提示；只發 ?projectId= 一個請求；axe 無違規", async ({ page }) => {
    const world = new SddProjectWorld();
    const { errors, unhandled } = await openProject(page, world);
    const gov = page.getByTestId("sdd-governance");
    await expect(gov).toHaveAttribute("data-used", "true");
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("HUMAN_PENDING");
    await expect(gov.getByTestId("sdd-gov-project")).toContainText("core-fsm");
    await expect(gov.getByTestId("sdd-gov-key")).toHaveText("core-fsm");
    await expect(gov.getByTestId("sdd-gov-dir")).toHaveText(SPEC_DIR);
    await expect(gov.getByTestId("sdd-gov-file")).toHaveText(SPEC_FILE);
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("人工確認");
    await expect(gov.getByTestId("sdd-phase")).toHaveAttribute("data-order", "3");
    await expect(gov.getByTestId("sdd-phase-step")).toHaveCount(8);
    await expect(gov.getByTestId("sdd-gov-frozen")).toHaveText("尚未凍結");
    await expect(gov.getByTestId("sdd-gov-pending")).toHaveText("等待人工確認");
    await expect(gov.getByTestId("sdd-gov-note")).toHaveText("FSM 狀態檔位於專案根的 build/reports/fsm，請把 build/reports/ 加入該專案的 .gitignore。");
    expect(world.engineCalls.map((c) => c.query.get("projectId"))).toEqual([PID]);
    expect(world.engineCalls.every((c) => !c.query.has("project"))).toBe(true);
    await shot(page, "sdd-governance-human-pending");
    await expectNoA11yViolations(page, "專案詳情（SDD 治理區：HUMAN_PENDING）");
    expectClean(errors, unhandled);
  });

  test("從未使用 SDD 的專案預設收合（標題「SDD 治理（尚未使用）」）且不發請求；展開後「SDD 專案」顯示預設值、目前狀態說明尚無狀態檔並加註建立位置", async ({ page }) => {
    const world = new SddProjectWorld();
    world.project = projectJson({ sddProject: null, sddSpecDir: null, sddSpecFile: null });
    world.fsm = null;
    const { errors, unhandled } = await openProject(page, world);
    const toggle = page.getByRole("button", { name: "SDD 治理（尚未使用）" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByTestId("sdd-governance-body")).toHaveCount(0);
    await page.waitForTimeout(500);
    expect(world.engineCalls).toHaveLength(0);
    await toggle.click();
    await expect(page.getByTestId("sdd-gov-project")).toContainText("（預設：AISDLC Core Platform）");
    await expect(page.getByTestId("sdd-gov-message")).toContainText("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）");
    await expect(page.getByTestId("sdd-gov-hint")).toHaveText("請在專案根的 SDD session 建立：/work/core/build/reports/fsm");
    for (const id of ["sdd-gov-key", "sdd-gov-phase", "sdd-gov-frozen", "sdd-gov-pending", "sdd-gov-dir", "sdd-gov-file"]) await expect(page.getByTestId(id)).toHaveText("—");
    await expect(page.getByTestId("sdd-freeze-button")).toBeDisabled();
    await expect(page.getByTestId("sdd-freeze-hint")).toHaveText("FSM 目前不在 HUMAN_PENDING（目前：—）");
    await expectNoA11yViolations(page, "專案詳情（SDD 治理區：尚未使用、已展開）");
    expectClean(errors, unhandled);
  });

  test("核准凍結成功：對話框預填 docs、理由必填且即時字數；送出的 body 只有 reason 與 docs；toast「已核准凍結」，區塊換成 SPEC_FROZEN／已凍結，鈕停用；axe 無違規", async ({ page }) => {
    const world = new SddProjectWorld();
    const { errors, unhandled } = await openProject(page, world);
    await expect(page.getByTestId("sdd-freeze-button")).toBeEnabled();
    await page.getByTestId("sdd-freeze-button").click();
    const dialog = page.getByRole("dialog", { name: "核准凍結規格" });
    await expect(dialog).toContainText("核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定；此動作無法由 Console 退回");
    await expect(dialog.getByTestId("sdd-freeze-docs")).toHaveValue(SPEC_REL);
    await expect(dialog.getByTestId("sdd-freeze-approver")).toContainText("核准人：operator");

    // 理由必填：空白送出 → 欄位錯誤、沒有請求
    await dialog.getByRole("button", { name: "核准凍結" }).click();
    await expect(dialog.getByText("請填寫核准理由")).toBeVisible();
    expect(world.freezeBodies).toHaveLength(0);

    await dialog.getByTestId("sdd-freeze-reason").fill("  規格已走完 SCG-0～3，核准凍結  ");
    await expect(dialog.getByTestId("sdd-freeze-reason-count")).toContainText("18 / 500");
    await expectNoA11yViolations(page, "核准凍結對話框（已填理由）");
    await shot(page, "sdd-freeze-dialog");
    await dialog.getByRole("button", { name: "核准凍結" }).click();

    await expect(page.getByText("已核准凍結")).toBeVisible();
    await expect(dialog).toHaveCount(0);
    expect(world.freezeBodies).toEqual([{ reason: "規格已走完 SCG-0～3，核准凍結", docs: [SPEC_REL] }]);
    const gov = page.getByTestId("sdd-governance");
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("SPEC_FROZEN");
    await expect(gov.getByTestId("sdd-gov-frozen")).toHaveText(`已凍結：Stage-1（${localTime("2026-10-17T02:00:00+00:00")}）`);
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("規格凍結");
    await expect(page.getByTestId("sdd-freeze-button")).toBeDisabled();
    await expect(page.getByTestId("sdd-freeze-hint")).toHaveText("FSM 目前不在 HUMAN_PENDING（目前：SPEC_FROZEN）");
    await shot(page, "sdd-governance-frozen");
    await expectNoA11yViolations(page, "專案詳情（SDD 治理區：已凍結）");
    expectClean(errors, unhandled);
  });

  test("核准凍結失敗：503 sdd_write_disabled、409 sdd_fsm_state_conflict、422 missing_tcs 的白話句子與 traceId；對話框不關；Esc 關閉後焦點回到「核准凍結」鈕", async ({ page }) => {
    const world = new SddProjectWorld();
    const { errors, unhandled } = await openProject(page, world);
    const trigger = page.getByTestId("sdd-freeze-button");
    await trigger.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "核准凍結規格" });
    await dialog.getByTestId("sdd-freeze-reason").fill("核准");

    world.freezeMode = "503";
    await dialog.getByRole("button", { name: "核准凍結" }).click();
    const error = dialog.getByTestId("sdd-freeze-error");
    await expect(error).toContainText("SDD 寫入功能未啟用（需管理員設定寫入權杖）");
    await expect(error).toContainText("traceId：tr-mock-503");
    await expect(dialog).toBeVisible();
    await expectNoA11yViolations(page, "核准凍結對話框（503 錯誤）");

    world.freezeMode = "409-state";
    await dialog.getByRole("button", { name: "核准凍結" }).click();
    await expect(error).toContainText("FSM 目前不在 HUMAN_PENDING（目前：SPEC_FROZEN）");

    world.freezeMode = "422-tcs";
    await dialog.getByRole("button", { name: "核准凍結" }).click();
    await expect(error).toContainText("docs／missing_tcs「規格文件須含至少一份 TCS」");
    expect(world.freezeBodies).toHaveLength(3);
    await expect(page.getByText("已核准凍結")).toHaveCount(0);

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    expectClean(errors, unhandled);
  });

  test("編輯 SDD 專案：預填目前值、送 {sddProject}；留空送 null 回到預設；409 sdd_binding_conflict 顯示衝突專案前 8 碼；取消後焦點回「編輯」鈕", async ({ page }) => {
    const world = new SddProjectWorld();
    const { errors, unhandled } = await openProject(page, world);
    const trigger = page.getByTestId("sdd-binding-edit");
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: "編輯 SDD 專案" });
    const input = dialog.getByTestId("sdd-binding-input");
    await expect(input).toHaveValue("core-fsm");
    await expect(dialog).toContainText("值會交給引擎橋接淨化後生效；改綁不搬移 FSM 狀態檔，也不影響進行中的批次");
    await expectNoA11yViolations(page, "編輯 SDD 專案對話框");

    world.bindingMode = "409";
    await input.fill("taken-fsm");
    await dialog.getByRole("button", { name: "儲存" }).click();
    await expect(dialog.getByTestId("sdd-binding-error")).toContainText("同一個專案根下已有另一個專案（1a2b3c4d）綁定了這個 FSM 專案");
    await expect(dialog).toBeVisible();

    world.bindingMode = "ok";
    await input.fill("core-new");
    await dialog.getByRole("button", { name: "儲存" }).click();
    await expect(page.getByText("已更新 SDD 專案")).toBeVisible();
    await expect(page.getByTestId("sdd-gov-project")).toContainText("core-new");
    expect(world.bindingBodies).toEqual([{ sddProject: "taken-fsm" }, { sddProject: "core-new" }]);

    await trigger.click();
    await page.getByRole("dialog", { name: "編輯 SDD 專案" }).getByTestId("sdd-binding-input").fill("   ");
    await page.getByRole("dialog", { name: "編輯 SDD 專案" }).getByRole("button", { name: "儲存" }).click();
    await expect(page.getByTestId("sdd-gov-project")).toContainText("（預設：AISDLC Core Platform）");
    expect(world.bindingBodies.at(-1)).toEqual({ sddProject: null });

    await trigger.click();
    await page.getByRole("dialog", { name: "編輯 SDD 專案" }).getByRole("button", { name: "取消" }).click();
    await expect(trigger).toBeFocused();
    expectClean(errors, unhandled);
  });

  test("VIEWER 唯讀：看得到綁定與狀態，沒有「編輯」與「核准凍結」", async ({ page }) => {
    const world = new SddProjectWorld();
    const { errors, unhandled } = await openProject(page, world, { role: "VIEWER" });
    await expect(page.getByTestId("sdd-gov-state")).toHaveText("HUMAN_PENDING");
    await expect(page.getByTestId("sdd-binding-edit")).toHaveCount(0);
    await expect(page.getByTestId("sdd-freeze-button")).toHaveCount(0);
    expectClean(errors, unhandled);
  });

  test("ESCALATION（E2E-17 第 19 列的畫面面）：專案詳情顯示紅色阻塞橫幅、ESCALATION 區塊與兩段可複製的恢復指令，核准凍結停用；人工恢復後重新整理，不再顯示未解的升級（provenance 仍在）", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const world = new SddProjectWorld();
    world.fsm = ESCALATED();
    const { errors, unhandled } = await openProject(page, world);
    const gov = page.getByTestId("sdd-governance");
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("ESCALATION");
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("阻塞（需人工）");
    await expect(gov.getByTestId("sdd-blocked-banner")).toContainText("阻塞：ESCALATION（需人工恢復）");
    await expect(gov.getByTestId("sdd-blocked-banner")).toContainText("請在 SDD session 依恢復指令處理，Console 不提供恢復動作");
    await expect(gov.getByTestId("sdd-escalation-summary")).toHaveText(`ESCALATION・${localTime("2026-10-17T01:05:00+00:00")}・AutoClaude 委派失敗：評估未通過`);
    await expect(gov.getByTestId("sdd-escalation-source")).toHaveText("來源：autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）");
    await expect(gov.getByTestId("sdd-freeze-button")).toBeDisabled();
    await expect(gov.getByTestId("sdd-freeze-hint")).toHaveText("FSM 目前不在 HUMAN_PENDING（目前：ESCALATION）");
    const recovery = gov.getByTestId("sdd-recovery");
    await expect(recovery.locator("[data-shell]")).toHaveCount(2);
    await expect(recovery.getByTestId("sdd-recovery-command-powershell")).toHaveText(PS_CMD);
    await expect(recovery.getByTestId("sdd-recovery-command-posix")).toHaveText(SH_CMD);
    await shot(page, "sdd-governance-escalation");
    await expectNoA11yViolations(page, "專案詳情（SDD 治理區：ESCALATION 與恢復指令）");

    await recovery.getByRole("button", { name: "複製 PowerShell 指令" }).click();
    await expect(recovery.getByRole("button", { name: "已複製 PowerShell 指令" })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(PS_CMD);
    await recovery.getByRole("button", { name: "複製 POSIX（bash／zsh） 指令" }).click();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(SH_CMD);

    // 測試扮演 SDD session 跑完 resume-from-escalation 之後：重新整理（或等下一輪 30 秒輪詢）→ 不再顯示未解的升級，判斷式看 currentState 與歷史末筆
    world.fsm = RECOVERED();
    await page.reload();
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("IMPLEMENTATION", { timeout: 60_000 });
    await expect(gov.getByTestId("sdd-blocked-banner")).toHaveCount(0);
    await expect(gov.getByTestId("sdd-escalation")).toHaveCount(0);
    await expect(gov.getByTestId("sdd-recovery")).toHaveCount(0);
    await expect(gov).not.toContainText("autoclaude_delegated_failed");
    await expect(gov.getByTestId("sdd-freeze-hint")).toHaveText("FSM 目前不在 HUMAN_PENDING（目前：IMPLEMENTATION）");
    expectClean(errors, unhandled);
  });
});

// ══ ② 匯入到既有專案 ══════════════════════════════════════════════════════════
const IMPORT_ID = "7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e77";
const SDD_TREE = {
  project: { name: "AISDLC Core Platform", executionPath: "/work/core", passCriteria: "規格「greenfield」的全部合約驗收通過", description: "由凍結 SDD 規格匯入", autonomyLevel: 4 },
  goals: [
    {
      key: "g1",
      name: "greenfield",
      description: "",
      passCriteria: "全部 2 個合約的驗收標準通過",
      sortOrder: 0,
      dependsOn: [],
      tasks: [
        {
          name: "AT-001-1",
          description: "請依規格實作並輸出 [AT_001_1_DONE]",
          passCriteria: "輸出符合 AT_001_1_DONE",
          sortOrder: 0,
          passCriteriaSpec: { source: "sdd", specDigest: "sha256:ab", stepId: "sdd-greenfield-at-001-1", weakRegex: false },
        },
        {
          name: "AT-001-2",
          description: "請依規格實作並輸出 [AT_001_2_DONE]",
          passCriteria: "輸出符合 AT_001_2_DONE",
          sortOrder: 1,
          passCriteriaSpec: { source: "sdd", specDigest: "sha256:ab", stepId: "sdd-greenfield-at-001-2", weakRegex: false },
        },
      ],
    },
  ],
  path: "SDD",
  specDigest: "sha256:ab",
  specFormatVersion: "1.0",
  sddProject: "core-fsm",
  sddSpecDir: SPEC_DIR,
  sddSpecFile: SPEC_FILE,
};
const AT_UNMAPPED = { code: "at_unmapped", detail: "規格出現但未編成步驟的 AT：AT-9-X", location: "specDir" };

/** 匯入頁的假後端（契約 §1.1、§1.10.8）：貼文字→parse（記下選項）→signoff→confirm（回目標專案）。 */
function importHandler(state: { parseOptions: unknown[]; confirmed: boolean; status: string; signed: boolean }): MockHandler {
  let parsed = false;
  let options: unknown = null;
  const detail = () => ({
    id: IMPORT_ID,
    sourceType: "MARKDOWN",
    sourceFileName: "TCS-Alpha.md",
    status: state.status,
    signedOff: state.signed,
    ...(state.signed ? { signedOffBy: "operator", signedOffAt: NOW } : {}),
    createdAt: NOW,
    parsePath: parsed ? "SDD" : undefined,
    sourceContent: "# TCS-Alpha",
    parsedResult: parsed ? SDD_TREE : null,
    warnings: parsed ? [AT_UNMAPPED] : [],
    parseOptions: options,
    ...(state.confirmed ? { projectId: PID } : {}),
  });
  return (call): MockReply => {
    const { method, path } = call;
    if (method === "GET" && path === "/api/v1/settings/agent") {
      return { data: [{ id: "c1", category: "agent", key: "defaultAutonomyLevel", value: "4", valueType: "INTEGER", defaultValue: "3", isEncrypted: false, hasValue: true, effect: "CONSOLE" }] };
    }
    if (method === "GET" && path === "/api/v1/projects") return { data: paged([summaryOf(projectJson())], 100) };
    if (method === "POST" && path === "/api/v1/import/text") {
      state.status = "UPLOADED";
      return { status: 201, data: { id: IMPORT_ID, sourceType: "MARKDOWN", sourceFileName: "TCS-Alpha.md", status: "UPLOADED", signedOff: false, createdAt: NOW } };
    }
    if (method === "GET" && path === `/api/v1/import/${IMPORT_ID}`) return { data: detail() };
    if (method === "POST" && path === `/api/v1/import/${IMPORT_ID}/parse`) {
      state.parseOptions.push(call.body);
      options = call.body;
      parsed = true;
      state.status = "PARSED";
      return { data: { importId: IMPORT_ID, status: "PARSED", path: "SDD", parsedResult: SDD_TREE, signedOff: false, errors: [], warnings: [AT_UNMAPPED] } };
    }
    if (method === "POST" && path === `/api/v1/import/${IMPORT_ID}/signoff`) {
      state.signed = true;
      return { data: { id: IMPORT_ID, sourceType: "MARKDOWN", status: "PARSED", signedOff: true, signedOffBy: "operator", signedOffAt: NOW, createdAt: NOW } };
    }
    if (method === "POST" && path === `/api/v1/import/${IMPORT_ID}/confirm`) {
      state.confirmed = true;
      state.status = "IMPORTED";
      return { status: 201, data: projectJson({ goals: undefined }) };
    }
    return undefined;
  };
}

test.describe("匯入到既有專案（route mock；契約 §1.10.8、§3.3.2；API-IMP-12）", () => {
  test.setTimeout(120_000);

  test("貼上規格文字→選目標專案（路徑取自專案且唯讀）→解析：parse 帶 targetProjectId→SDD 規格資訊、併入說明、at_unmapped 警告→signoff→確認匯入：toast「已併入專案」並導向該專案", async ({ page }) => {
    const state = { parseOptions: [] as unknown[], confirmed: false, status: "UPLOADED", signed: false };
    const world = new SddProjectWorld();
    await signInAs(page, "OPERATOR");
    const unhandled: string[] = [];
    const { calls } = await installApiMock(
      page,
      compose(importHandler(state), world.handler, shellHandler(), (call) => {
        unhandled.push(`${call.method} ${call.path}`);
        return undefined;
      }),
    );
    const errors = collectConsoleErrors(page);
    await page.goto("/import");

    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel(/^需求文字/).fill("# TCS-Alpha\n\n## AC-001\n- AT-001-1\n- AT-001-2");
    const select = page.getByTestId("import-target-select");
    await expect(select.locator("option")).toHaveText(["建立新專案（預設）", "AISDLC Core Platform"]);
    await select.selectOption({ label: "AISDLC Core Platform" });
    await expect(page.getByLabel("執行路徑")).toHaveValue("/work/core");
    await expect(page.getByLabel("執行路徑")).toHaveAttribute("readonly", "");
    await expect(page.getByTestId("import-target-path-note")).toContainText("執行路徑取自目標專案「AISDLC Core Platform」，不可修改");
    await shot(page, "import-target-selected");
    await expectNoA11yViolations(page, "匯入頁（已選目標專案）");

    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    expect(state.parseOptions).toEqual([{ autonomyLevel: 4, executionPath: "/work/core", targetProjectId: PID }]);

    const info = page.getByTestId("sdd-spec-info");
    await expect(info.getByTestId("sdd-info-format")).toHaveText("1.0");
    await expect(info.getByTestId("sdd-info-project")).toHaveText("core-fsm");
    await expect(info.getByTestId("sdd-info-dir")).toHaveText(SPEC_DIR);
    await expect(info.getByTestId("sdd-info-file")).toHaveText(SPEC_FILE);
    await expect(page.getByTestId("sdd-merge-note")).toContainText("併入既有專案");
    await expect(page.getByTestId("sdd-merge-note")).toContainText("「AISDLC Core Platform」");
    await expect(page.getByTestId("parse-warning")).toContainText("規格出現、但未編成步驟的 AT");
    await expect(page.getByTestId("parse-warning")).toContainText("AT-9-X");
    await expect(page.getByTestId("parse-path")).toHaveText("規格驅動（SDD）");
    await shot(page, "import-merge-parsed");
    await expectNoA11yViolations(page, "匯入頁（步驟 2：SDD 規格資訊與警告）");

    await page.getByRole("button", { name: "signoff 審批" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByTestId("import-signed-off")).toBeVisible();
    await page.getByRole("button", { name: "確認匯入" }).click();
    await expect(page).toHaveURL(new RegExp(`/projects/${PID}$`));
    await expect(page.getByText("已併入專案：AISDLC Core Platform")).toBeVisible();
    expect(calls.filter((c) => c.method === "POST" && c.path.endsWith("/confirm"))).toHaveLength(1);
    expectClean(errors, unhandled);
  });

  test("不選目標：parse 的請求沒有 targetProjectId（維持建立新專案）；路徑欄位可自由填寫", async ({ page }) => {
    const state = { parseOptions: [] as unknown[], confirmed: false, status: "UPLOADED", signed: false };
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(importHandler(state), shellHandler()));
    const errors = collectConsoleErrors(page);
    await page.goto("/import");
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel(/^需求文字/).fill("# TCS-Alpha");
    await page.getByLabel("執行路徑").fill("/home/user/new-service");
    await expect(page.getByLabel("執行路徑")).not.toHaveAttribute("readonly", "");
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    expect(state.parseOptions).toEqual([{ autonomyLevel: 4, executionPath: "/home/user/new-service" }]);
    await expect(page.getByTestId("sdd-merge-note")).toHaveCount(0);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});

// ══ ③ 執行頁：追溯覆蓋（諮詢）面板與 201 的 warnings ═══════════════════════════════════
const EXEC_URL = `/projects/${PID}/execute`;
const RTM_OK = {
  scenario: "greenfield",
  specDigest: "sha256:1f0e2b7a9c4d8e3f6a1b5c7d9e0f2a4b6c8d0e1f3a5b7c9d1e3f5a7b9c0d2e4f",
  at: { passed: 4, total: 5, unmapped: 1, pct: 80 },
  ac: { covered: 2, total: 2, pct: 100 },
  failedAtIds: ["AT-002-1"],
  weakRegexAtIds: ["AT-001-1"],
  unmappedAtIds: ["AT-9-X"],
  fullyCovered: false,
  advisory: true,
};

let activeEngine: Engine | null = null;

async function openExecute(page: Page, opts: { seed: (e: Engine) => void; sdd?: boolean; rtm?: (runId: string) => MockReply; startWarnings?: unknown[] }) {
  const engine = new Engine();
  await engine.listen();
  activeEngine = engine;
  opts.seed(engine);
  await signInAs(page, "OPERATOR");
  const unhandled: string[] = [];
  const before: MockHandler = async (call) => {
    if (call.method === "GET" && call.path === `/api/v1/projects/${PID}` && opts.sdd !== false) {
      const reply = (await engine.handler(call)) as { data: Json };
      return { data: { ...reply.data, sddProject: "core-fsm", sddSpecDir: SPEC_DIR, sddSpecFile: SPEC_FILE } };
    }
    const rtm = /^\/api\/v1\/executions\/([^/]+)\/rtm$/.exec(call.path);
    if (call.method === "GET" && rtm) return opts.rtm ? opts.rtm(rtm[1]) : undefined;
    if (call.method === "POST" && call.path === `/api/v1/projects/${PID}/execute` && opts.startWarnings) {
      const reply = (await engine.handler(call)) as { status?: number; data: Json };
      return { ...reply, data: { ...reply.data, warnings: opts.startWarnings } };
    }
    return undefined;
  };
  const { calls } = await installApiMock(
    page,
    compose(before, engine.handler, (call) => {
      unhandled.push(`${call.method} ${call.path}`);
      return undefined;
    }),
  );
  const errors = collectConsoleErrors(page);
  await page.goto(EXEC_URL);
  await expect(page.getByRole("heading", { name: "專案執行：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
  return { engine, calls, errors, unhandled };
}

/** 一個跑完的批次：三個任務依序完成（COMPLETED）。 */
const completedRun = (e: Engine) => {
  e.begin(4);
  for (let i = 0; i < TASKS.length; i++) {
    e.startNext();
    e.finishCurrent();
  }
};

test.describe("執行頁：追溯覆蓋（諮詢）面板與 execute 的 warnings（route mock；UI-SDD-02、API-EXE-15／16）", () => {
  test.setTimeout(150_000);

  test.afterEach(async () => {
    await activeEngine?.close();
    activeEngine = null;
  });

  test("終態批次、專案有規格綁定：面板顯示報告（諮詢視圖徽章與固定說明、AT／AC、SCG-5 不視為全覆蓋、摘要 tooltip、失敗／偏弱／無法歸屬的 AT 與說明）；只取一次；axe 無違規", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await openExecute(page, { seed: completedRun, rtm: () => ({ data: RTM_OK }) });
    const runId = engine.latest.id;
    const panel = page.getByTestId("rtm-panel");
    await expect(panel.getByRole("heading", { name: "追溯覆蓋" })).toBeVisible();
    await expect(panel.getByTestId("rtm-advisory-badge")).toHaveText("諮詢視圖");
    await expect(panel.getByTestId("rtm-advisory-note")).toHaveText("AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘。");
    await expect(panel.getByTestId("rtm-at")).toHaveText("4／5（80.0%）");
    await expect(panel.getByTestId("rtm-at-note")).toHaveText("其中 1 個無法歸屬到 AC");
    await expect(panel.getByTestId("rtm-ac")).toHaveText("2／2（100.0%）");
    await expect(panel.getByTestId("rtm-scg5")).toHaveText("AC 已達 100%，但有無法歸屬的 AT，不視為全覆蓋");
    await expect(panel.getByTestId("rtm-digest")).toHaveText("sha256:1f0e2b7a9c4d…");
    await expect(panel.getByTestId("rtm-digest")).toHaveAttribute("title", RTM_OK.specDigest);
    await expect(panel.getByTestId("rtm-scenario")).toHaveText("greenfield");
    await expect(panel.getByTestId("rtm-failed")).toHaveText("AT-002-1");
    await expect(panel.getByTestId("rtm-weak")).toHaveText("AT-001-1");
    await expect(panel.getByTestId("rtm-weak-note")).toContainText("驗收可能偏鬆");
    await expect(panel.getByTestId("rtm-unmapped")).toHaveText("AT-9-X");
    await expect(panel.getByTestId("rtm-unmapped-note")).toContainText("已計入 AT 總數但不計入任何 AC");
    await page.waitForTimeout(400);
    expect(calls.filter((c) => c.path === `/api/v1/executions/${runId}/rtm`)).toHaveLength(1); // 取一次、不輪詢
    await shot(page, "execute-rtm-panel");
    await expectNoA11yViolations(page, "執行頁（追溯覆蓋面板）");
    expectClean(errors, unhandled);
  });

  test("終態批次沒有報告（404 rtm_not_found）：中性文字「此批次沒有追溯覆蓋報告」，不是錯誤樣式；axe 無違規", async ({ page }) => {
    const { errors, unhandled } = await openExecute(page, { seed: completedRun, rtm: () => fail(404, { message: "此批次沒有追溯報告", reason: "rtm_not_found", details: { runId: "x" } }) });
    const empty = page.getByTestId("rtm-empty");
    await expect(empty).toContainText("此批次沒有追溯覆蓋報告");
    await expect(page.getByTestId("rtm-panel").getByRole("alert")).toHaveCount(0);
    await expect(page.getByTestId("rtm-advisory-badge")).toHaveCount(0);
    await expectNoA11yViolations(page, "執行頁（追溯覆蓋面板：沒有報告）");
    expectClean(errors, unhandled);
  });

  test("批次還在跑：只有一行「批次結束後才會有追溯覆蓋報告」，不呼叫端點；專案沒有規格綁定：整個面板不顯示、也不呼叫", async ({ page }) => {
    const running = await openExecute(page, {
      seed: (e) => {
        e.begin(4);
        e.startNext();
      },
      rtm: () => ({ data: RTM_OK }),
    });
    await expect(page.getByTestId("rtm-pending")).toHaveText("批次結束後才會有追溯覆蓋報告");
    await page.waitForTimeout(400);
    expect(running.calls.filter((c) => c.path.endsWith("/rtm"))).toHaveLength(0);
    expectClean(running.errors, running.unhandled);
    await activeEngine?.close();

    const unbound = await openExecute(page, { seed: completedRun, sdd: false, rtm: () => ({ data: RTM_OK }) });
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await page.waitForTimeout(400);
    await expect(page.getByTestId("rtm-panel")).toHaveCount(0);
    expect(unbound.calls.filter((c) => c.path.endsWith("/rtm"))).toHaveLength(0);
    expectClean(unbound.errors, unbound.unhandled);
  });

  test("啟動 201 帶 warnings：toast 併進同一句、執行控制卡列出每則警告（白話標題、原因、後端說明）；批次照常啟動", async ({ page }) => {
    const warnings = [
      { code: "sdd_governance_inactive", cause: "mixed_scope", detail: "範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理" },
      { code: "sdd_frozen_digest_absent", detail: "凍結時沒有記錄內容摘要" },
    ];
    const { errors, unhandled } = await openExecute(page, { seed: () => undefined, startWarnings: warnings });
    await page.getByTestId("control-start").click();
    await expect(page.getByText("已啟動 Run #1（另有 2 則警告，見執行控制卡）")).toBeVisible();
    const panel = page.getByTestId("control-card").getByTestId("execution-warnings");
    await expect(panel).toContainText("啟動警告（共 2 項；批次已啟動，不阻擋）");
    await expect(panel.getByTestId("execution-warning")).toHaveCount(2);
    await expect(panel.getByTestId("execution-warning").first()).toContainText("本批次沒有啟用 SDD 治理");
    await expect(panel.getByTestId("execution-warning-cause").first()).toHaveText("原因：範圍內有非 SDD 來源的任務");
    await expect(panel.getByTestId("execution-warning-detail").first()).toHaveText("範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理");
    await expect(panel.getByTestId("execution-warning").nth(1)).toContainText("無法偵測凍結後改檔");
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await shot(page, "execute-warnings");
    await expectNoA11yViolations(page, "執行頁（啟動警告）");
    expectClean(errors, unhandled);
  });
});

// ══ ④ 監控頁 SDD 卡：專案模式、階段進度、ESCALATION 與恢復指令 ═════════════════════════════
async function openMonitor(page: Page, opts: { fsm: Json | null; reason?: string | null; bound?: boolean }) {
  const engine = new Engine();
  engine.begin(4);
  for (let i = 0; i < TASKS.length; i++) {
    engine.startNext();
    engine.finishCurrent();
  }
  const world = new MonitorWorld(engine);
  await signInAs(page, "OPERATOR");
  const unhandled: string[] = [];
  const projectEngineCalls: MockCall[] = [];
  const before: MockHandler = async (call) => {
    if (call.method === "GET" && call.path === `/api/v1/projects/${PID}` && opts.bound !== false) {
      const reply = (await engine.handler(call)) as { data: Json };
      return { data: { ...reply.data, sddProject: "core-fsm", sddSpecDir: SPEC_DIR, sddSpecFile: SPEC_FILE } };
    }
    if (call.method === "GET" && call.path === "/api/v1/engines/sdd" && call.query.has("projectId")) {
      projectEngineCalls.push(call);
      return engineReply(opts.fsm, opts.reason ?? null);
    }
    return undefined;
  };
  const { calls } = await installApiMock(
    page,
    compose(before, world.handler, engine.handler, (call) => {
      unhandled.push(`${call.method} ${call.path}`);
      return undefined;
    }),
  );
  const errors = collectConsoleErrors(page);
  await page.goto(`/projects/${PID}/monitor`);
  await expect(page.getByRole("heading", { name: "專案監控：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
  return { world, calls, errors, unhandled, projectEngineCalls };
}

test.describe("監控頁 SDD 卡（route mock；M-21、UI-SDD-03）", () => {
  test.setTimeout(120_000);

  test("專案有綁定：卡片進專案模式——只請求 ?projectId=（沒有全域模式的清單請求）、階段進度標出目前步驟、下拉預選標準鍵；axe 無違規", async ({ page }) => {
    const fsm = fsmJson({ currentState: "IMPLEMENTATION", currentSprint: 2, humanPending: { count: 0, items: [] }, phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: false } });
    const { world, errors, unhandled, projectEngineCalls } = await openMonitor(page, { fsm });
    const card = page.getByTestId("sdd-card");
    await expect(card).toHaveAttribute("data-mode", "project");
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    await expect(card.getByTestId("sdd-sprint")).toHaveText("Sprint 2");
    await expect(card.getByTestId("sdd-phase")).toHaveAttribute("data-phase", "IMPLEMENTATION");
    await expect(card.getByTestId("sdd-phase")).toHaveAttribute("data-order", "5");
    await expect(card.getByTestId("sdd-phase-label")).toHaveText("實作");
    await expect(card.getByTestId("sdd-phase-step")).toHaveCount(8);
    await expect(card.locator('[data-testid="sdd-phase-step"][data-state="current"]')).toHaveAttribute("data-step", "IMPLEMENTATION");
    await expect(card.locator('[data-testid="sdd-phase-step"][data-state="done"]')).toHaveCount(4);
    await expect(card.getByTestId("sdd-project-select")).toHaveValue("core-fsm");
    expect(projectEngineCalls.map((c) => [c.query.get("projectId"), c.query.get("project")])).toEqual([[PID, null]]);
    expect(world.seen.filter((s) => s.path === "/api/v1/engines/sdd")).toHaveLength(0); // 專案模式不打全域那一份
    await shot(page, "monitor-sdd-card-implementation");
    await expectNoA11yViolations(page, "監控頁（SDD 卡：專案模式、階段進度）");
    expectClean(errors, unhandled);
  });

  test("ESCALATION：紅色阻塞橫幅、八個步驟全灰、ESCALATION 區塊（末筆、來源）與兩段恢復指令；複製鈕把 PowerShell 與 POSIX 指令各自原樣寫進剪貼簿；卡片仍唯讀（只有兩個複製鈕）", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const { errors, unhandled } = await openMonitor(page, { fsm: ESCALATED() });
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-blocked-banner")).toContainText("阻塞：ESCALATION（需人工恢復）");
    await expect(card.getByTestId("sdd-blocked-banner")).toContainText("請在 SDD session 依恢復指令處理，Console 不提供恢復動作");
    await expect(card.getByTestId("sdd-phase")).toHaveAttribute("data-blocking", "true");
    await expect(card.locator('[data-testid="sdd-phase-step"][data-state="upcoming"]')).toHaveCount(8);
    await expect(card.getByTestId("sdd-escalation-summary")).toHaveText(`ESCALATION・${localTime("2026-10-17T01:05:00+00:00")}・AutoClaude 委派失敗：評估未通過`);
    await expect(card.getByTestId("sdd-escalation-source")).toHaveText("來源：autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）");
    const recovery = card.getByTestId("sdd-recovery");
    await expect(recovery.locator("[data-shell]")).toHaveCount(2);
    await expect(recovery.getByTestId("sdd-recovery-command-powershell")).toHaveText(PS_CMD);
    await expect(recovery.getByTestId("sdd-recovery-command-posix")).toHaveText(SH_CMD);
    await expect(card.getByRole("button")).toHaveCount(2); // 唯讀：除了兩個複製鈕沒有任何按鈕
    await shot(page, "monitor-sdd-card-escalation");
    await expectNoA11yViolations(page, "監控頁（SDD 卡：ESCALATION 與恢復指令）");

    await recovery.getByRole("button", { name: "複製 PowerShell 指令" }).click();
    await expect(recovery.getByRole("button", { name: "已複製 PowerShell 指令" })).toHaveText("已複製");
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(PS_CMD);
    await recovery.getByRole("button", { name: "複製 POSIX（bash／zsh） 指令" }).click();
    await expect(recovery.getByRole("button", { name: "已複製 POSIX（bash／zsh） 指令" })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(SH_CMD);
    // 約 2.4 秒後回到「複製」
    await expect(recovery.getByRole("button", { name: "複製 PowerShell 指令" })).toHaveText("複製");
    expectClean(errors, unhandled);
  });

  test("人工恢復後（IMPLEMENTATION）escalationProvenance 還在、歷史末筆已有 resolved_at：不顯示橫幅、ESCALATION 區塊與恢復指令（判斷式不只看 provenance）", async ({ page }) => {
    const { errors, unhandled } = await openMonitor(page, { fsm: RECOVERED() });
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    await expect(card.getByTestId("sdd-blocked-banner")).toHaveCount(0);
    await expect(card.getByTestId("sdd-escalation")).toHaveCount(0);
    await expect(card.getByTestId("sdd-recovery")).toHaveCount(0);
    await expect(card).not.toContainText("autoclaude_delegated_failed");
    expectClean(errors, unhandled);
  });

  test("觀測態（AUTOCLAUDE_DELEGATED）：「觀測中」與「委派 AutoClaude 執行中」標籤、虛線外框的目前步驟；專案路徑被拒（sdd_root_rejected）顯示專案文案", async ({ page }) => {
    const delegated = fsmJson({ currentState: "AUTOCLAUDE_DELEGATED", humanPending: { count: 0, items: [] }, phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: true } });
    const first = await openMonitor(page, { fsm: delegated });
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-phase")).toHaveAttribute("data-observation", "true");
    await expect(card.getByTestId("sdd-phase-observation")).toHaveText("觀測中");
    await expect(card.getByTestId("sdd-phase-delegated")).toHaveText("委派 AutoClaude 執行中");
    await expect(card.locator('[data-testid="sdd-phase-step"][data-state="current"]')).toHaveClass(/border-dashed/);
    await expectNoA11yViolations(page, "監控頁（SDD 卡：觀測態）");
    expectClean(first.errors, first.unhandled);

    const rejected = await openMonitor(page, { fsm: null, reason: "sdd_root_rejected" });
    await expect(page.getByTestId("sdd-message")).toHaveText("專案路徑不在 Bridge 允許的根目錄內（或已不存在）");
    await expect(page.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expectClean(rejected.errors, rejected.unhandled);
  });

  test("專案沒有綁定（sddProject 為空）：維持全域模式——兩段請求、不帶 projectId（M-20）", async ({ page }) => {
    const { world, projectEngineCalls, errors, unhandled } = await openMonitor(page, { fsm: null, bound: false });
    await expect(page.getByTestId("sdd-card")).toHaveAttribute("data-mode", "global");
    await expect(page.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    expect(projectEngineCalls).toHaveLength(0);
    expect(world.seen.filter((s) => s.path === "/api/v1/engines/sdd").map((s) => s.query.get("project"))).toEqual([null, "e2e-alpha"]);
    expectClean(errors, unhandled);
  });
});
