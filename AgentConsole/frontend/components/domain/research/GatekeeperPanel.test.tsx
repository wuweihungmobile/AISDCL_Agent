import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchEvent, ResearchFsmView, ResearchPrdVersion, ResearchProjectDetail, ResearchReviewRound, Role } from "@/lib/api/types";
import { READONLY_TITLE, scoreRadar } from "@/lib/domain/research";
import { FSM_AFTER_RECOVERY, FSM_ESCALATION, FSM_HUMAN_PENDING, fsmView } from "@/tests/fixtures/research/fsm";
import { R2, T1, T2, sha } from "@/tests/fixtures/research/ids";
import { EVIDENCE } from "@/tests/fixtures/research/misc";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { FAIL3_ROUNDS, FAIL3_SCORES, PASS_SCORES, PRD_VERSIONS, defect, makeRound, type Scores } from "@/tests/fixtures/research/reviews";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls, type ApiCall, type Reply } from "@/tests/helpers/research";
import {
  GATE0_FILES,
  GATE_REASON_MAX,
  GatekeeperPanel,
  buildExpectedDigests,
  isEscalationEvent,
  isReviewStale,
  openDefects,
  retryHistoryCheck,
  reviewActivity,
  scoreText,
  sortDefects,
  unmetConditions,
} from "./GatekeeperPanel";

/**
 * Gatekeeper 審批面板（TCS-ResearchToPRD-P0-20261102 AT-960-15-1～15-4、16-4、16-5、16-8、16-9、16-E-2、16-E-3；AC-R2P-08、09、10、18）：
 * ESCALATION 區塊（內容、沒有恢復動詞按鈕、事件去重的彈窗、VIEWER 唯讀、兩個動作）、雷達圖與缺陷卡、動作區六種狀態、Gate 0 確認對話框、等待提醒（假時鐘）、
 * 審查狀態只由 stage run 與事件決定、「第 n 輪」對照 FSM 重試史。fetch 與 EventSource 是替身；recharts 以替身記下收到的資料（真圖表在真瀏覽器的 E2E 驗）。
 * 事件序號一律自 1 起連續（動態欄的顯示規則：缺口之後的事件在補齊前不渲染）。
 * 判定指令：npx vitest run components/domain/research/GatekeeperPanel.test.tsx -t "<AT 底線形>"
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(),
}));

type RadarProps = { data: Array<{ dimension: string; label: string; score: number | null }>; children?: ReactNode };
const radar = vi.hoisted(() => ({ charts: [] as Array<RadarProps["data"]> }));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div data-testid="radar-container">{children}</div>,
  RadarChart: (props: RadarProps) => {
    radar.charts.push(props.data);
    return <div data-testid="radar-chart-stub">{props.children}</div>;
  },
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
}));

beforeEach(() => {
  radar.charts.length = 0;
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
});

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

const HEAD_NO = 2; // PRD_VERSIONS 的 head
const at = (n: number): string => `2026-11-02T11:${String(Math.floor(n / 60) % 60).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}+08:00`;

function ev(seq: number, eventType: string, payload: Record<string, unknown>): ResearchEvent {
  return { seq, eventType, step: "studio", actor: "bridge", refKind: null, refId: null, payload, occurredAt: at(seq) };
}
const runEvent = (seq: number, status: string, roundNo: number, attempt = 1): ResearchEvent =>
  ev(seq, "research.run", { stage: "REVIEW", roundNo, attempt, stageRunId: `run-review-${roundNo}-${attempt}`, engineRunId: "eng-r", status, tokensUsed: 100 });
const reviewEvent = (seq: number, roundNo: number, verdict = "REVISE"): ResearchEvent =>
  ev(seq, "research.review", { roundNo, weightedScore: 82.75, minDimensionScore: 78, passed: verdict === "PASS", verdict, escalated: verdict === "ESCALATE" });
const alertEvent = (seq: number, kind: string, detail = "審查三輪未通過"): ResearchEvent => ev(seq, "research.alert", { kind, detail });

/** 事件帳的底（seq 1～3）：PRD 草稿、第 1 輪審查 run 收尾、第 1 輪完成。 */
const BASE_EVENTS: ResearchEvent[] = [
  ev(1, "research.prd", { versionNo: 1, semver: "v0.1.0-draft", authorKind: "AGENT", author: "spec-engineer", sha256: sha("1") }),
  runEvent(2, "SUCCEEDED", 1),
  reviewEvent(3, 1),
];

/** 第 1 輪未通過、審查的是 head 版本（新鮮）；輪列的重試計數故意與 FSM 視圖不同，證明剩餘預算不取輪列。 */
const FRESH_FAIL = makeRound(1, FAIL3_SCORES[0], HEAD_NO, { defects: [defect(1, 1), defect(1, 2, { severity: "P3", dimension: "PRODUCT" })], fsmRetryCount: 3 });
const FRESH_PASS = makeRound(2, PASS_SCORES[1], HEAD_NO, { defects: [defect(2, 1, { severity: "P3" })], finishedAt: T2 });
const OLD_PASS = makeRound(2, PASS_SCORES[1], 1, { defects: [defect(2, 1, { severity: "P3" })], finishedAt: T2 });
/** 三輪未過且 FSM 在 ESCALATION：三輪都審 head 版本，使「已過期」不干擾這組情境。 */
const ESC_ROUNDS: ResearchReviewRound[] = FAIL3_ROUNDS.map((r) => ({ ...r, prdVersionNo: HEAD_NO, prdVersion: "v0.2.0-draft" }));

const STUDIO = detailVariant("studio");
const ESCALATED = detailVariant("escalated");

type Stub = Parameters<typeof stubResearchApi>[0];
type MountOptions = { role?: Role; project?: ResearchProjectDetail; completed?: boolean; stub?: Stub };

/** Gate 0 的預設回應：核准與退回都回成功（測試以 stub.overrides 蓋過）。 */
const decisionReplies = (call: ApiCall): Reply => {
  if (call.method !== "POST") return undefined;
  if (/\/approve$/.test(call.path)) return { data: { gateDecisionId: "gd-1", stage: "Gate-0", specDocDigests: {}, fsmState: "SPEC_FROZEN" } };
  if (/\/return$/.test(call.path)) return { data: { gateDecisionId: "gd-2", fsmRetryCount: 1, escalated: false } };
  return undefined;
};

function mount(opts: MountOptions = {}) {
  const project = opts.project ?? STUDIO;
  const custom = opts.stub?.overrides;
  const api = stubResearchApi({
    details: { [R2]: project },
    events: BASE_EVENTS,
    rounds: [FRESH_FAIL],
    fsm: fsmView("SPEC_DRAFTING", {}, 1),
    prdVersions: PRD_VERSIONS,
    evidence: EVIDENCE,
    ...opts.stub,
    overrides: (call) => custom?.(call) ?? decisionReplies(call),
  });
  const onLocate = vi.fn();
  const ui = renderResearch(
    <GatekeeperPanel researchId={R2} project={project} completed={opts.completed === true} onLocate={onLocate} syncRetryMs={5} backoffMs={() => 5} refreshDebounceMs={5} />,
    opts.role ?? "OPERATOR",
  );
  return { ...ui, ...api, onLocate };
}

const nameOf = (el: Element): string => el.getAttribute("aria-label") ?? el.textContent?.replace(/\s+/g, " ").trim() ?? "";
const buttonNames = (root: HTMLElement = document.body): string[] => within(root).queryAllByRole("button").map(nameOf);
const button = (name: string | RegExp) => screen.getByRole("button", { name });
const send = (es: FakeEventSource, event: ResearchEvent) =>
  act(() => {
    es.emit(event.eventType, event, String(event.seq));
  });
/** 事件帳載入、EventSource 建好並開啟；回該連線。 */
async function connected(): Promise<FakeEventSource> {
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  const es = FakeEventSource.last;
  act(() => es.open());
  return es;
}
const settle = (ms = 30) => new Promise<void>((resolve) => setTimeout(resolve, ms));
/** ESCALATION 區塊的內容（FSM 視圖與輪表）載入完成：游標已是 ESCALATED 時區塊會先以占位內容出現，所以等重用的 SddEscalationBlock 與分數卡。 */
const escalationReady = async (): Promise<HTMLElement> => {
  await screen.findByTestId("sdd-escalation");
  await screen.findByTestId("review-score");
  return screen.getByTestId("escalation-section");
};

const RECOVER = "我已恢復，繼續（僅一次機會）";
const ITERATE = "一鍵自動迭代修正";

// ── AT_960_15_x ESCALATION ───────────────────────────────────────────────────────────

const stripComments = (source: string): string => source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");

/** 端點檔裡研究端點函式的起點（FE-A 的段落標記）；既有的 `resumeExecution` 是執行中心的續跑，與 ESCALATION 無關，不在掃描範圍。 */
const RESEARCH_ENDPOINTS_MARKER = "ResearchToPRD P0";

/** 靜態掃描：不得有 `resume-from-escalation` 字串，端點檔的研究段落也不得有名稱含 resume 的匯出函式。 */
function resumeViolations(file: string, source: string): string[] {
  const code = stripComments(source);
  const found: string[] = [];
  if (/resume-from-escalation/.test(code)) found.push(`${file}：字串 resume-from-escalation`);
  if (file.endsWith("endpoints.ts")) {
    const start = source.indexOf(RESEARCH_ENDPOINTS_MARKER);
    const researchPart = start < 0 ? code : stripComments(source.slice(start));
    for (const match of researchPart.matchAll(/export\s+(?:async\s+)?(?:function|const)\s+(\w*[Rr]esume\w*)/g)) found.push(`${file}：端點函式 ${match[1]}`);
  }
  return found;
}

describe("AT_960_15_1 ESCALATION 區塊內容與沒有任何恢復動詞按鈕", () => {
  it.each(["ADMIN", "OPERATOR"] as const)(
    "AT_960_15_1 %s：重用的 SddEscalationBlock、可複製的恢復指令、原因、各輪分數、未結缺陷數與 FSM 現態都在；區塊內的動作按鈕恰為兩顆；畫面上沒有任何恢復動詞按鈕",
    async (role) => {
      const { calls } = mount({ role, project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
      const section = await escalationReady();
      expect(within(section).getAllByTestId("sdd-escalation"), "重用 SddEscalationBlock，恰一個").toHaveLength(1);
      expect(within(section).getByTestId("sdd-escalation-summary")).toHaveTextContent("SCG_VALIDATION 第 3 次未通過");
      expect(within(section).getByTestId("sdd-recovery-command-powershell")).toHaveTextContent("python -m tools.fsm_runtime");
      expect(within(section).getByTestId("sdd-recovery-command-posix")).toBeInTheDocument();
      expect(within(section).getByRole("button", { name: /複製 PowerShell 指令/ })).toBeInTheDocument();
      expect(within(section).getByTestId("escalation-state")).toHaveTextContent("ESCALATION");
      expect(within(section).getByTestId("escalation-scores")).toHaveTextContent("第 1 輪 79.90");
      expect(within(section).getByTestId("escalation-scores")).toHaveTextContent("第 2 輪 82.75");
      expect(within(section).getByTestId("escalation-scores")).toHaveTextContent("第 3 輪 84.60");
      expect(within(section).getByTestId("escalation-open-defects")).toHaveTextContent("1 個");
      // 區塊內的動作按鈕恰為兩顆（複製鈕不計）
      expect(buttonNames(section).filter((n) => !/複製/.test(n))).toEqual([RECOVER, "換世代"]);
      // 整個畫面：名稱含「恢復」「resume」的動作只有那一顆唯讀驗證鈕；「換世代」不是恢復
      expect(buttonNames().filter((n) => /恢復|resume/i.test(n) && n !== RECOVER)).toEqual([]);
      expect(nameOf(button("換世代"))).not.toMatch(/恢復|resume/i);
      expect(writeCalls(calls), "渲染期間沒有任何寫入請求").toEqual([]);
    },
  );

  it("AT_960_15_1 靜態掃描：lib/api/endpoints.ts 與 components/domain/research 的非測試原始碼沒有 resume-from-escalation 字串與名稱含 resume 的端點函式；掃描範圍非空、掃描器有負控", () => {
    const dir = path.join(process.cwd(), "components", "domain", "research");
    const files = readdirSync(dir)
      .filter((name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name))
      .map((name) => path.join(dir, name));
    files.push(path.join(process.cwd(), "lib", "api", "endpoints.ts"));
    expect(files.length, "掃描範圍非空").toBeGreaterThanOrEqual(10);
    expect(files.map((f) => path.basename(f))).toEqual(expect.arrayContaining(["GatekeeperPanel.tsx", "StudioPanel.tsx", "endpoints.ts"]));
    for (const file of files) expect(resumeViolations(file, readFileSync(file, "utf-8")), file).toEqual([]);
    expect(readFileSync(path.join(process.cwd(), "lib", "api", "endpoints.ts"), "utf-8"), "研究端點段落的標記存在").toContain(RESEARCH_ENDPOINTS_MARKER);
    expect(resumeViolations("a.tsx", 'const cmd = "resume-from-escalation --to X";')).not.toEqual([]);
    expect(resumeViolations("endpoints.ts", "// ── ResearchToPRD P0\nexport function resumeFromEscalation(id: string) {}")).not.toEqual([]);
    expect(resumeViolations("endpoints.ts", "// ── ResearchToPRD P0\nexport const resumeResearch = () => 1;")).not.toEqual([]);
    expect(resumeViolations("endpoints.ts", "export function resumeExecution() {}\n// ── ResearchToPRD P0\nexport function startResearchStage() {}"), "研究段落之前的既有續跑函式不算").toEqual([]);
    expect(resumeViolations("a.tsx", '// 註解提到 "resume-from-escalation" 不算\nconst ok = 1;')).toEqual([]);
    expect(resumeViolations("endpoints.ts", "export function startResearchStage() {}")).toEqual([]);
  });
});

describe("AT_960_15_2 SSE 重播造成重複事件時同一待處理項只有一個彈窗", () => {
  it("AT_960_15_2 連續送兩次相同 id 的升級事件與重播的第三次：ESCALATION 區塊與彈窗各恰一個；關閉後同一事件重播不再彈出；較晚的新升級才再彈；頁面重載只由資料庫狀態重建一個區塊", async () => {
    const user = userEvent.setup();
    const first = mount({ project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    await screen.findByTestId("escalation-section");
    const es = await connected();
    expect(screen.queryByRole("dialog"), "頁面剛載入：歷史事件不彈窗").toBeNull();
    const escalated = alertEvent(4, "ESCALATED");
    await send(es, escalated);
    await send(es, escalated);
    await send(es, escalated); // 重播的第三次
    const dialog = await screen.findByRole("dialog", { name: "審查已升級，需要人工處理" });
    expect(screen.getAllByRole("dialog"), "彈窗恰一個").toHaveLength(1);
    expect(screen.getAllByTestId("sdd-escalation"), "ESCALATION 區塊恰一個").toHaveLength(1);
    expect(screen.getAllByTestId("escalation-section")).toHaveLength(1);
    await user.click(within(dialog).getByRole("button", { name: "稍後處理" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await send(es, escalated); // 同一事件重播
    expect(screen.queryByRole("dialog"), "關閉後同一事件重播不再彈出（以事件 id 記憶）").toBeNull();
    expect(screen.getAllByTestId("sdd-escalation"), "稍後處理＝不視為已處理：區塊仍在").toHaveLength(1);
    await send(es, alertEvent(5, "ESCALATED", "第二次升級"));
    await screen.findByRole("dialog", { name: "審查已升級，需要人工處理" });
    first.unmount();

    // 頁面重載：事件帳已含這些升級事件，只由資料庫狀態重建一個區塊、不彈窗
    FakeEventSource.reset();
    mount({ project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION, events: [...BASE_EVENTS, escalated, alertEvent(5, "ESCALATED", "第二次升級")] } });
    await screen.findByTestId("escalation-section");
    await connected();
    expect(screen.getAllByTestId("sdd-escalation")).toHaveLength(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("AT_960_15_2 三種升級相關事件都算（警示 ESCALATED、游標轉 ESCALATED、審查判定 escalated）；一般警示與沒升級的審查不算", () => {
    expect(isEscalationEvent(alertEvent(1, "ESCALATED"))).toBe(true);
    expect(isEscalationEvent(ev(1, "research.step", { flowStatus: "ESCALATED" }))).toBe(true);
    expect(isEscalationEvent(reviewEvent(1, 3, "ESCALATE"))).toBe(true);
    expect(isEscalationEvent(alertEvent(1, "DENIED_FETCH"))).toBe(false);
    expect(isEscalationEvent(ev(1, "research.step", { flowStatus: "IDLE" }))).toBe(false);
    expect(isEscalationEvent(reviewEvent(1, 1, "REVISE"))).toBe(false);
  });
});

describe("AT_960_15_3 VIEWER 可讀 ESCALATION 內容但所有決定按鈕停用", () => {
  it("AT_960_15_3 區塊內容完整可見；「我已恢復，繼續」「換世代」與核准、退回、迭代都 disabled 且 title 為「權限不足（唯讀角色）」；複製指令仍可用", async () => {
    mount({ role: "VIEWER", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    const section = await escalationReady();
    expect(within(section).getByTestId("sdd-escalation-summary")).toBeInTheDocument();
    expect(within(section).getByTestId("sdd-recovery-command-powershell")).toBeVisible();
    expect(within(section).getByTestId("escalation-scores")).toHaveTextContent("第 3 輪 84.60");
    for (const name of [RECOVER, "換世代", "核准 PRD", "退回修改", ITERATE]) {
      const target = button(name);
      expect(target, name).toBeDisabled();
      expect(target, name).toHaveAttribute("title", READONLY_TITLE);
    }
    expect(within(section).getByRole("button", { name: /複製 PowerShell 指令/ })).toBeEnabled();
  });
});

describe("AT_960_15_4 ESCALATION 區塊兩個動作", () => {
  it("AT_960_15_4 OPERATOR 按「我已恢復，繼續」兩次：只送 POST stages/revise 本文 {afterEscalation:true}；第一次 409 顯示現態並保持區塊，第二次 202 後 flow 由待人工處理回到閒置、區塊消失", async () => {
    const user = userEvent.setup();
    let revises = 0;
    const overrides = (call: ApiCall): Reply => {
      if (call.method === "POST" && /\/stages\/revise$/.test(call.path)) {
        revises += 1;
        return revises === 1
          ? failure(409, { message: "狀態機現態不允許", reason: "fsm_state_conflict", details: { current_state: "ESCALATION" } })
          : { status: 202, data: { stageRunId: "run-revise-1", flowPhase: "REVISING", flowStatus: "RUNNING" } };
      }
      return undefined;
    };
    const { calls, options } = mount({ role: "OPERATOR", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION, overrides } });
    await screen.findByTestId("escalation-section");
    expect(screen.getByTestId("flow-status")).toHaveTextContent("待人工處理");
    const recover = button(RECOVER);
    expect(recover).toBeEnabled();
    expect(nameOf(recover)).toContain("僅一次機會");
    await user.click(recover);
    expect(await screen.findByTestId("recover-notice")).toHaveTextContent("ESCALATION");
    expect(screen.getByTestId("escalation-section"), "409：保持區塊").toBeInTheDocument();
    // 人在 Console 外恢復後：資料庫與 FSM 視圖都已離開 ESCALATION
    options.details[R2] = detailVariant("studio", { flowStatus: "IDLE", flowPhase: "REVISING" });
    options.fsm = FSM_AFTER_RECOVERY;
    await user.click(button(RECOVER));
    await waitFor(() => expect(screen.queryByTestId("escalation-section")).toBeNull());
    await waitFor(() => expect(screen.getByTestId("flow-status")).toHaveTextContent("閒置"));
    const posts = callsOf(calls, "POST", /\/stages\/revise$/);
    expect(posts.map((c) => c.body)).toEqual([{ afterEscalation: true }, { afterEscalation: true }]);
    expect(writeCalls(calls), "只有 revise 兩次寫入").toHaveLength(2);
  });

  it("AT_960_15_4 ADMIN 按「換世代」：二次確認對話框說明舊鍵不再使用、預算重新計、留稽核紀錄；理由為空或 501 字確認鈕停用；合法理由送 POST reinit {generation:next, reason}；409 顯示現態並保持區塊；200 後世代加一、區塊消失、剩餘預算顯示 3", async () => {
    const user = userEvent.setup();
    let reinits = 0;
    const gen2 = detailVariant("studio", { fsmGeneration: 2, flowStatus: "IDLE", flowPhase: "REVISING" });
    const overrides = (call: ApiCall): Reply => {
      if (call.method === "POST" && /\/reinit$/.test(call.path)) {
        reinits += 1;
        return reinits === 1
          ? failure(409, { message: "現態不是 ESCALATION", reason: "fsm_state_conflict", details: { current_state: "SPEC_DRAFTING" } })
          : { data: { flow: gen2.flow, fsmProject: "research-vector-db-g2", fsmGeneration: 2, gateDecisionId: "gd-1" } };
      }
      return undefined;
    };
    const { calls, options } = mount({ role: "ADMIN", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION, overrides } });
    await screen.findByTestId("escalation-section");
    expect(screen.getByTestId("generation")).toHaveTextContent("世代 1");
    expect(button("換世代")).toBeEnabled();
    await user.click(button("換世代"));
    const dialog = await screen.findByRole("dialog", { name: "換世代" });
    expect(dialog).toHaveTextContent("舊鍵不再使用");
    expect(dialog).toHaveTextContent("預算重新計");
    expect(dialog).toHaveTextContent("稽核紀錄");
    const confirm = within(dialog).getByRole("button", { name: "確認換世代" });
    const reason = within(dialog).getByRole("textbox");
    expect(confirm, "理由為空").toBeDisabled();
    await user.click(reason);
    await user.paste("x".repeat(GATE_REASON_MAX + 1));
    expect(within(dialog).getByTestId("reason-count")).toHaveTextContent(`${GATE_REASON_MAX + 1} ／ ${GATE_REASON_MAX} 字`);
    expect(confirm, "501 字").toBeDisabled();
    await user.clear(reason);
    await user.paste("   "); // 只有空白＝空理由
    expect(confirm).toBeDisabled();
    await user.clear(reason);
    await user.paste("三輪審查後決定放棄這把鍵重新來過");
    expect(confirm).toBeEnabled();
    // 焦點被困在對話框內
    for (let i = 0; i < 8; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement), `Tab 第 ${i + 1} 次`).toBe(true);
    }
    // 第一次：後端回 409 → 顯示現態、保持區塊與對話框
    await user.click(confirm);
    expect(await within(dialog).findByTestId("reinit-error")).toHaveTextContent("SPEC_DRAFTING");
    expect(screen.getByTestId("escalation-section")).toBeInTheDocument();
    // 第二次：成功 → 重抓專案詳情與 FSM 視圖
    options.details[R2] = gen2;
    options.fsm = fsmView("SPEC_DRAFTING", {}, 0);
    await user.click(within(dialog).getByRole("button", { name: "確認換世代" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(screen.queryByTestId("escalation-section")).toBeNull());
    expect(screen.getByTestId("generation")).toHaveTextContent("世代 2");
    expect(await screen.findByTestId("budget-remaining")).toHaveTextContent("3");
    const bodies = callsOf(calls, "POST", /\/reinit$/).map((c) => c.body);
    expect(bodies).toEqual([
      { generation: "next", reason: "三輪審查後決定放棄這把鍵重新來過" },
      { generation: "next", reason: "三輪審查後決定放棄這把鍵重新來過" },
    ]);
    expect(writeCalls(calls), "兩個動作之外沒有其他寫入").toHaveLength(2);
    expect(
      buttonNames().filter((n) => /換鍵重開/.test(n)),
      "沒有無理由、無確認的單鍵",
    ).toEqual([]);
  });

  it("AT_960_15_4 「換世代」鈕僅 ADMIN 啟用：OPERATOR 的 title 說明權限不足、VIEWER 為唯讀提示；「我已恢復，繼續」OPERATOR 可用、VIEWER 停用；Esc 關閉對話框、焦點歸還到觸發鈕", async () => {
    const user = userEvent.setup();
    const operator = mount({ role: "OPERATOR", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    await screen.findByTestId("escalation-section");
    expect(button("換世代")).toBeDisabled();
    expect(button("換世代").getAttribute("title")).toContain("權限不足");
    expect(button(RECOVER)).toBeEnabled();
    operator.unmount();
    const viewer = mount({ role: "VIEWER", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    await screen.findByTestId("escalation-section");
    expect(button("換世代")).toHaveAttribute("title", READONLY_TITLE);
    expect(button(RECOVER)).toBeDisabled();
    viewer.unmount();
    mount({ role: "ADMIN", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    await screen.findByTestId("escalation-section");
    const trigger = button("換世代");
    await user.click(trigger);
    await screen.findByRole("dialog", { name: "換世代" });
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(trigger).toHaveFocus();
  });
});

// ── AT_960_16_4 雷達圖與缺陷卡 ───────────────────────────────────────────────────────

describe("AT_960_16_4 雷達圖四軸等於 DB 分數並附等效文字表，缺陷卡排序與定位", () => {
  const defects = [
    defect(1, 1, { severity: "P3", dimension: "PRODUCT", prdAnchor: "§3.1", description: "商業指標沒有基準值", suggestion: "補上現況數字", status: "FIXED" }),
    defect(1, 2, { severity: "P1", dimension: "ARCHITECTURE", prdAnchor: "§5.2", description: "資料流沒有失敗路徑", suggestion: "補上重試與降級", status: "OPEN" }),
    defect(1, 3, { severity: "P2", dimension: "QA", prdAnchor: "§4.2", description: "驗收條件沒有可量測的判準", suggestion: "補上門檻" }),
  ];

  it("AT_960_16_4 雷達圖四軸資料（scoreRadar 輸出）等於 78、84、70、90；等效文字表恰四列同值；加權總分是資料庫兩位小數字串", async () => {
    mount({ stub: { rounds: [makeRound(1, FAIL3_SCORES[0], HEAD_NO, { defects })] } });
    await screen.findByTestId("review-score");
    await screen.findByTestId("radar-chart-stub");
    const expected = scoreRadar({ scores: makeRound(1, FAIL3_SCORES[0], HEAD_NO).scores });
    expect(expected.map((a) => a.score)).toEqual([78, 84, 70, 90]);
    expect(radar.charts[radar.charts.length - 1]).toEqual(expected);
    expect(screen.getByRole("img", { name: /四方審查雷達圖：架構 78、商業 84、QA 70、資安 90/ })).toBeInTheDocument();
    const rows = within(screen.getByTestId("radar-table")).getAllByRole("row");
    expect(rows).toHaveLength(4);
    expect(rows.map((r) => [within(r).getByRole("rowheader").textContent, within(r).getByRole("cell").textContent])).toEqual([
      ["架構", "78"],
      ["商業", "84"],
      ["QA", "70"],
      ["資安", "90"],
    ]);
    expect(screen.getByTestId("weighted-score")).toHaveTextContent("79.90");
    expect(screen.getByTestId("min-dimension")).toHaveTextContent("70");
  });

  it("AT_960_16_4 缺陷卡依嚴重度 P1、P2、P3 排序，每張含維度、章節定位、描述、修訂建議、狀態；點定位連結回報該錨點", async () => {
    const user = userEvent.setup();
    const { onLocate } = mount({ stub: { rounds: [makeRound(1, FAIL3_SCORES[0], HEAD_NO, { defects })] } });
    const cards = await screen.findAllByTestId("defect-card");
    expect(cards.map((c) => c.getAttribute("data-severity"))).toEqual(["P1", "P2", "P3"]);
    expect(cards.map((c) => c.getAttribute("data-defect-no"))).toEqual(["D-1-002", "D-1-003", "D-1-001"]);
    const [p1, p2, p3] = cards;
    expect(p1).toHaveTextContent("架構");
    expect(p1).toHaveTextContent("資料流沒有失敗路徑");
    expect(p1).toHaveTextContent("修訂建議：補上重試與降級");
    expect(within(p1).getByTestId("defect-status")).toHaveTextContent("未結");
    expect(p2).toHaveTextContent("QA");
    expect(within(p2).getByTestId("defect-status")).toHaveTextContent("未結");
    expect(p3).toHaveTextContent("商業");
    expect(within(p3).getByTestId("defect-status")).toHaveTextContent("已修正");
    await user.click(within(p1).getByRole("button", { name: "定位 §5.2" }));
    await user.click(within(p3).getByRole("button", { name: "定位 §3.1" }));
    expect(onLocate.mock.calls.map((c) => c[0])).toEqual(["§5.2", "§3.1"]);
  });

  it("AT_960_16_4 純函式：sortDefects 嚴重度優先、同級依編號；unmetConditions 取自 conditions；openDefects 含再次出現；scoreText 前置否決顯示未計分、兩位小數原樣", () => {
    const list = [defect(1, 3, { severity: "P2" }), defect(1, 1, { severity: "P3" }), defect(1, 2, { severity: "P1" }), defect(1, 4, { severity: "P2" })];
    expect(sortDefects(list).map((d) => d.defectNo)).toEqual(["D-1-002", "D-1-003", "D-1-004", "D-1-001"]);
    const failed = makeRound(1, FAIL3_SCORES[0], HEAD_NO, { defects: [defect(1, 1, { severity: "P1" })] });
    expect(unmetConditions(failed)).toEqual(["加權總分 79.90 未達門檻 85.00", "仍有 1 個未結 P1 缺陷"]);
    expect(unmetConditions(FRESH_PASS)).toEqual([]);
    const precheckFail: ResearchReviewRound = {
      ...failed,
      weightedScore: null,
      minDimensionScore: null,
      conditions: { precheckPassed: false, weightedGeThreshold: null, allDimensionsGeFloor: null, noOpenP1: true },
    };
    expect(unmetConditions(precheckFail)).toEqual(["前置檢查未通過（章節、引用或驗收條件不完整）"]);
    expect(scoreText(precheckFail)).toBe("未計分");
    expect(scoreText({ weightedScore: 85 })).toBe("85.00");
    expect(scoreText({ weightedScore: 84.95 })).toBe("84.95");
    expect(openDefects({ defects: [defect(1, 1), defect(1, 2, { status: "FIXED" }), defect(1, 3, { status: "REGRESSED" }), defect(1, 4, { status: "WAIVED" })] }).map((d) => d.defectNo)).toEqual([
      "D-1-001",
      "D-1-003",
    ]);
  });
});

// ── AT_960_16_5 動作區矩陣 ───────────────────────────────────────────────────────────

describe("AT_960_16_5 動作區矩陣：未通過、通過、非 ADMIN、escalated、人工恢復後的按鈕啟停與說明", () => {
  const queryButton = (name: string) => screen.queryByRole("button", { name });

  it("AT_960_16_5 未通過（FSM currentCount 為 1）：「一鍵自動迭代修正」啟用並顯示剩餘預算 2（取自 FSM 視圖，不取輪列的重試計數）；「核准 PRD」停用並說明不成立的條件", async () => {
    mount({ role: "ADMIN", stub: { rounds: [FRESH_FAIL], fsm: fsmView("SPEC_DRAFTING", {}, 1) } });
    await waitFor(() => expect(screen.getByTestId("budget-remaining")).toHaveTextContent("2"));
    expect(FRESH_FAIL.fsmRetryCount, "輪列的值故意不同於 FSM 視圖").toBe(3);
    expect(button(ITERATE)).toBeEnabled();
    expect(button("核准 PRD")).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("審查未通過");
    expect(screen.getByTestId("approve-note")).toHaveTextContent("加權總分 79.90 未達門檻 85.00");
    expect(screen.queryByTestId("budget-after-recovery")).toBeNull();
    expect(queryButton("重新審查"), "新鮮的未通過審查：不提供重新審查（迭代已涵蓋）").toBeNull();
  });

  it("AT_960_16_5 通過且 head 即審查版：「核准 PRD」啟用（ADMIN）、迭代鈕與重新審查隱藏、沒有已過期標示", async () => {
    mount({ role: "ADMIN", stub: { rounds: [FRESH_FAIL, FRESH_PASS], fsm: FSM_HUMAN_PENDING } });
    await waitFor(() => expect(button("核准 PRD")).toBeEnabled());
    expect(queryButton(ITERATE)).toBeNull();
    expect(queryButton("重新審查")).toBeNull();
    expect(screen.queryByTestId("review-stale")).toBeNull();
    expect(screen.getByTestId("approve-note")).toBeEmptyDOMElement();
    expect(button("退回修改")).toBeEnabled();
  });

  it("AT_960_16_5 通過但 head 較新（審查的是第 1 版、head 是第 2 版）：核准停用並標「審查已過期」，提供「重新審查」", async () => {
    mount({ role: "ADMIN", stub: { rounds: [OLD_PASS], fsm: FSM_HUMAN_PENDING } });
    await waitFor(() => expect(screen.getByTestId("review-stale")).toHaveTextContent("已過期"));
    expect(button("核准 PRD")).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("審查已過期");
    expect(screen.getByTestId("approve-note")).toHaveTextContent("第 2 版");
    expect(button("重新審查")).toBeEnabled();
    expect(queryButton(ITERATE), "最新一輪是通過的：不提供迭代").toBeNull();
  });

  it("AT_960_16_5 通過且角色為 OPERATOR：核准與退回停用且 title 為權限不足", async () => {
    mount({ role: "OPERATOR", stub: { rounds: [FRESH_PASS], fsm: FSM_HUMAN_PENDING } });
    await screen.findByTestId("review-score");
    await settle();
    expect(button("核准 PRD")).toBeDisabled();
    expect(button("核准 PRD").getAttribute("title")).toContain("權限不足");
    expect(button("退回修改")).toBeDisabled();
    expect(button("退回修改").getAttribute("title")).toContain("權限不足");
  });

  it("AT_960_16_5 escalated：兩顆按鈕停用並顯示 ESCALATION 區塊", async () => {
    mount({ role: "ADMIN", project: ESCALATED, stub: { rounds: ESC_ROUNDS, fsm: FSM_ESCALATION } });
    await escalationReady();
    expect(button("核准 PRD")).toBeDisabled();
    expect(button(ITERATE)).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("審查已升級給人工");
  });

  it("AT_960_16_5 人工恢復後（FSM 現態 SPEC_DRAFTING、currentCount 仍為 3、最新輪未通過）：剩餘預算顯示 0 並標「恢復後僅一次機會」，「一鍵自動迭代修正」仍啟用，「核准 PRD」停用", async () => {
    mount({ role: "ADMIN", stub: { rounds: ESC_ROUNDS, fsm: FSM_AFTER_RECOVERY } });
    await waitFor(() => expect(screen.getByTestId("budget-remaining")).toHaveTextContent("0"));
    expect(screen.getByTestId("budget-after-recovery")).toHaveTextContent("恢復後僅一次機會");
    expect(button(ITERATE)).toBeEnabled();
    expect(button("核准 PRD")).toBeDisabled();
    expect(screen.queryByTestId("escalation-section")).toBeNull();
  });

  it("AT_960_16_5 迭代送 POST stages/iterate（本文為空）；寫入失敗（含 Bridge 尚未實作的 502）顯示原因、不假裝成功", async () => {
    const user = userEvent.setup();
    const overrides = (call: ApiCall): Reply => (call.method === "POST" && /\/stages\/iterate$/.test(call.path) ? failure(502, { message: "Bridge 尚未實作", reason: "not_implemented" }) : undefined);
    const { calls } = mount({ role: "OPERATOR", stub: { rounds: [FRESH_FAIL], fsm: fsmView("SPEC_DRAFTING", {}, 1), overrides } });
    await waitFor(() => expect(button(ITERATE)).toBeEnabled());
    await user.click(button(ITERATE));
    expect(await screen.findByText(/一鍵自動迭代修正失敗：這個功能尚未開放/)).toBeInTheDocument();
    expect(screen.queryByText(/已送出/)).toBeNull();
    expect(callsOf(calls, "POST", /\/stages\/iterate$/).map((c) => c.body)).toEqual([{}]);
  });

  it("AT_960_16_5 已凍結（flow_phase FROZEN 且步驟已完成）：迭代、核准、退回都停用並說明已凍結", async () => {
    mount({ role: "ADMIN", project: detailVariant("frozen"), completed: true, stub: { rounds: [FRESH_FAIL], fsm: fsmView("SPEC_DRAFTING", {}, 1) } });
    await screen.findByTestId("review-score");
    for (const name of [ITERATE, "核准 PRD", "退回修改"]) expect(button(name), name).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("規格已凍結");
  });
});

// ── INT-09 「已過期」以內容（sha256）判定，不比版本號 ───────────────────────────────────

/** Gate 0 核准後的 BASELINE 版：版本號加一、內容與雜湊同通過的那一版（第 2 版）。 */
const BASELINE_V3: ResearchPrdVersion = {
  ...PRD_VERSIONS[1],
  versionNo: 3,
  semver: "v1.0.0",
  kind: "BASELINE",
  authorKind: "HUMAN",
  author: "admin",
  parentVersionNo: 2,
  changeSummary: "Gate 0 核准：凍結為基線",
  createdAt: T2,
};
/** 人工存檔的第 3 版：內容變了（雜湊不同）。 */
const HUMAN_V3: ResearchPrdVersion = { ...BASELINE_V3, semver: "v0.3.0-draft", kind: "DRAFT", changeSummary: "人工修改", sha256: sha("3") };

describe("INT-09 審查結果是否已過期：以被審那一版與 head 的內容（sha256）判定", () => {
  const V = [
    { versionNo: 1, sha256: sha("1") },
    { versionNo: 2, sha256: sha("2") },
    { versionNo: 3, sha256: sha("2") },
    { versionNo: 4, sha256: sha("4") },
  ];
  const round = (prdVersionNo: number) => ({ prdVersionNo });

  it("isReviewStale：同一版、內容相同的新版本（BASELINE）＝沒過期；內容不同的新版本＝過期；沒有任何版本＝沒東西可過期", () => {
    expect(isReviewStale(round(2), 2, V), "審的就是 head").toBe(false);
    expect(isReviewStale(round(2), 3, V), "head 是第 3 版（BASELINE）：內容與第 2 版相同").toBe(false);
    expect(isReviewStale(round(2), 4, V), "head 是第 4 版：內容不同").toBe(true);
    expect(isReviewStale(round(1), 3, V), "審的是更早、內容不同的第 1 版").toBe(true);
    expect(isReviewStale(round(2), null, V), "還沒有任何版本").toBe(false);
  });

  it("isReviewStale：雜湊的 sha256: 前綴與大小寫不決定結果；找不到被審的版本或 head（清單不完整、尚未載入）時退回比版本號，寧可多要一次審查", () => {
    expect(
      isReviewStale(round(2), 3, [
        { versionNo: 2, sha256: `sha256:${sha("a")}` },
        { versionNo: 3, sha256: sha("A") },
      ]),
    ).toBe(false);
    expect(
      isReviewStale(round(2), 3, [
        { versionNo: 2, sha256: sha("a") },
        { versionNo: 3, sha256: sha("b") },
      ]),
    ).toBe(true);
    expect(isReviewStale(round(2), 3, [{ versionNo: 3, sha256: sha("2") }]), "清單裡沒有被審的版本").toBe(true);
    expect(isReviewStale(round(2), 3, [{ versionNo: 2, sha256: sha("2") }]), "清單裡沒有 head").toBe(true);
    expect(isReviewStale(round(2), 3, undefined), "版本清單尚未載入").toBe(true);
    expect(isReviewStale(round(3), 3, undefined), "同一版號不需要清單").toBe(false);
  });

  it("INT-09 凍結後（Gate 0 核准寫了 BASELINE 第 3 版、內容同通過的第 2 版）：通過的審查不標「已過期」，核准說明是「規格已凍結」而不是「審查已過期」", async () => {
    mount({
      role: "ADMIN",
      project: detailVariant("frozen", { headPrdVersion: 3 }),
      completed: true,
      stub: { rounds: [FRESH_FAIL, FRESH_PASS], prdVersions: [...PRD_VERSIONS, BASELINE_V3], fsm: fsmView("SPEC_FROZEN", {}, 0) },
    });
    await screen.findByTestId("review-score");
    expect(screen.getByTestId("round-label")).toHaveTextContent("第 2 輪");
    expect(screen.queryByTestId("review-stale"), "head 是 BASELINE、內容與被審版本相同：沒有過期標示").toBeNull();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("規格已凍結");
    expect(screen.getByTestId("approve-note")).not.toHaveTextContent("已過期");
    expect(screen.queryByRole("button", { name: "重新審查" }), "凍結後不提供重新審查").toBeNull();
  });

  it("INT-09 人工存檔後（第 3 版內容不同）：審查標「已過期」，核准停用並說明，提供「重新審查」", async () => {
    mount({ role: "ADMIN", project: detailVariant("studio", { headPrdVersion: 3 }), stub: { rounds: [FRESH_FAIL, FRESH_PASS], prdVersions: [...PRD_VERSIONS, HUMAN_V3], fsm: FSM_HUMAN_PENDING } });
    await waitFor(() => expect(screen.getByTestId("review-stale")).toHaveTextContent("已過期"));
    expect(button("核准 PRD")).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("審查已過期：PRD 已有新版本（第 3 版），審查的是第 2 版");
    expect(button("重新審查")).toBeEnabled();
  });
});

// ── AT_960_16_8 Gate 0 確認對話框 ────────────────────────────────────────────────────

describe("AT_960_16_8 Gate 0 確認對話框內容、退回需理由、焦點陷阱與歸還", () => {
  const passReady = (stub: Stub = {}) => mount({ role: "ADMIN", stub: { rounds: [FRESH_FAIL, FRESH_PASS], fsm: FSM_HUMAN_PENDING, ...stub } });
  const openApprove = async (user: ReturnType<typeof userEvent.setup>) => {
    await waitFor(() => expect(button("核准 PRD")).toBeEnabled());
    await user.click(button("核准 PRD"));
    return await screen.findByRole("dialog", { name: "Gate 0：核准或退回 PRD" });
  };

  it("AT_960_16_8 按「核准 PRD」：對話框顯示 PRD 版本、sha256 前 8 碼、加權總分、最低維度分、未結缺陷數、將凍結的四個檔案與選填理由", async () => {
    const user = userEvent.setup();
    passReady();
    const dialog = await openApprove(user);
    const summary = within(dialog).getByTestId("gate-summary");
    expect(summary).toHaveTextContent("v0.2.0-draft（第 2 版）");
    expect(summary).toHaveTextContent(sha("2").slice(0, 8));
    expect(summary).toHaveTextContent("90.30");
    expect(within(summary).getByText("最低維度分").nextElementSibling).toHaveTextContent("88");
    expect(within(summary).getByText("未結缺陷數").nextElementSibling).toHaveTextContent("1");
    expect(
      within(dialog)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(GATE0_FILES.map((f) => `${f.path}（${f.label}）`));
    expect(GATE0_FILES.map((f) => f.path)).toEqual(["01_specs/PRD-v1.0.0.md", "00_research/evidence_matrix.md", "00_research/issue_scope.json", "01_specs/adr_draft.md"]);
    expect(within(dialog).getByRole("textbox")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "退回修改" }), "理由為空：退回停用").toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "核准並凍結" })).toBeEnabled();
  });

  it("AT_960_16_8 「核准並凍結」送 POST approve：本文只有 prdVersion、expectedDigests（sha256: 加雜湊）與選填理由，沒有 approver；成功後關閉對話框並提示", async () => {
    const user = userEvent.setup();
    const { calls } = passReady();
    const dialog = await openApprove(user);
    await user.click(within(dialog).getByRole("textbox"));
    await user.paste("缺陷已處理，確認凍結");
    await user.click(within(dialog).getByRole("button", { name: "核准並凍結" }));
    await waitFor(() => expect(callsOf(calls, "POST", /\/approve$/)).toHaveLength(1));
    const body = callsOf(calls, "POST", /\/approve$/)[0].body as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(["expectedDigests", "prdVersion", "reason"]);
    expect(body.prdVersion).toBe(2);
    expect(body.reason).toBe("缺陷已處理，確認凍結");
    expect(body.expectedDigests).toEqual({ "01_specs/PRD-v1.0.0.md": `sha256:${sha("2")}`, "00_research/evidence_matrix.md": `sha256:${EVIDENCE.sha256}` });
    expect(body).not.toHaveProperty("approver");
    expect(await screen.findByText("已核准並凍結：規格進入下一步")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("AT_960_16_8 理由留空時請求本文沒有 reason 鍵", async () => {
    const user = userEvent.setup();
    const { calls } = passReady();
    const dialog = await openApprove(user);
    await user.click(within(dialog).getByRole("button", { name: "核准並凍結" }));
    await waitFor(() => expect(callsOf(calls, "POST", /\/approve$/)).toHaveLength(1));
    expect(Object.keys(callsOf(calls, "POST", /\/approve$/)[0].body as Record<string, unknown>).sort()).toEqual(["expectedDigests", "prdVersion"]);
  });

  it("AT_960_16_8 「退回修改」理由為空時停用、非空時送 POST return（本文只有 reason）；回應已升級時提示預算用盡", async () => {
    const user = userEvent.setup();
    const overrides = (call: ApiCall): Reply => (call.method === "POST" && /\/return$/.test(call.path) ? { data: { gateDecisionId: "gd-2", fsmRetryCount: 3, escalated: true } } : undefined);
    const { calls } = passReady({ overrides });
    await waitFor(() => expect(button("退回修改")).toBeEnabled());
    await user.click(button("退回修改"));
    const dialog = await screen.findByRole("dialog");
    const back = within(dialog).getByRole("button", { name: "退回修改" });
    expect(back).toBeDisabled();
    await user.click(within(dialog).getByRole("textbox"));
    await user.paste("驗收條件仍不可量測");
    expect(back).toBeEnabled();
    await user.click(back);
    await waitFor(() => expect(callsOf(calls, "POST", /\/return$/)).toHaveLength(1));
    expect(callsOf(calls, "POST", /\/return$/)[0].body).toEqual({ reason: "驗收條件仍不可量測" });
    expect(await screen.findByText(/已退回修改，且審查預算用盡：已升級給人工/)).toBeInTheDocument();
  });

  it("AT_960_16_8 核准被後端拒絕（含 Bridge 尚未實作的 502）：對話框保持開啟、顯示白話原因、不出現成功提示，也沒有其他寫入", async () => {
    const user = userEvent.setup();
    const overrides = (call: ApiCall): Reply =>
      call.method === "POST" && /\/approve$/.test(call.path) ? failure(502, { message: "Bridge 尚未實作核准", reason: "not_implemented", details: { endpoint: "approve-baseline" } }) : undefined;
    const { calls } = passReady({ overrides });
    const dialog = await openApprove(user);
    await user.click(within(dialog).getByRole("button", { name: "核准並凍結" }));
    expect(await within(dialog).findByTestId("gate-error")).toHaveTextContent("這個功能尚未開放");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByText("已核准並凍結：規格進入下一步")).toBeNull();
    expect(writeCalls(calls).map((c) => c.path)).toEqual([`/api/v1/research/projects/${R2}/approve`]);
  });

  it("AT_960_16_8 以鍵盤 Tab 操作焦點被困在對話框內、Esc 關閉後焦點歸還到觸發鈕；理由超過 500 字時兩個決定都停用", async () => {
    const user = userEvent.setup();
    passReady();
    await waitFor(() => expect(button("核准 PRD")).toBeEnabled());
    const trigger = button("核准 PRD");
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog");
    for (let i = 0; i < 10; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement), `Tab 第 ${i + 1} 次`).toBe(true);
    }
    await user.click(within(dialog).getByRole("textbox"));
    await user.paste("y".repeat(GATE_REASON_MAX + 1));
    expect(within(dialog).getByRole("button", { name: "核准並凍結" })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "退回修改" })).toBeDisabled();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(trigger).toHaveFocus();
  });

  it("AT_960_16_8 buildExpectedDigests：鍵為相對 POSIX 路徑、值為 sha256: 加雜湊（已帶前綴不重複加）；只含目前 API 拿得到的兩個檔", () => {
    expect(buildExpectedDigests({ sha256: "a".repeat(64) }, { sha256: "b".repeat(64) })).toEqual({
      "01_specs/PRD-v1.0.0.md": `sha256:${"a".repeat(64)}`,
      "00_research/evidence_matrix.md": `sha256:${"b".repeat(64)}`,
    });
    expect(buildExpectedDigests({ sha256: `sha256:${"c".repeat(64)}` }, { sha256: "d".repeat(64) })["01_specs/PRD-v1.0.0.md"]).toBe(`sha256:${"c".repeat(64)}`);
  });
});

// ── AT_960_16_9 Gate 0 等待提醒 ──────────────────────────────────────────────────────

describe("AT_960_16_9 Gate 0 等待中顯示已等待小時數，滿 72 小時顯示提醒橫幅（純前端、假時鐘、零寫入）", () => {
  const HOUR = 3_600_000;
  const PASS_ROUND = makeRound(1, PASS_SCORES[1], HEAD_NO, { fsmGateResult: "PASS", fsmRetryCount: 0, finishedAt: T1 });
  const finished = Date.parse(T1);

  /** 只假造 Date 與時鐘的 interval（不碰 setTimeout：查詢庫與 waitFor 要照常運作）。 */
  function waitedAt(offsetMs: number, opts: MountOptions = {}) {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(finished + offsetMs);
    return mount({ role: "ADMIN", ...opts, stub: { rounds: [PASS_ROUND], fsm: FSM_HUMAN_PENDING, ...opts.stub } });
  }

  it.each([
    { label: "5 小時", offset: 5 * HOUR, text: "已等待 5 小時", banner: false },
    { label: "71 小時 59 分", offset: 71 * HOUR + 59 * 60_000, text: "已等待 71 小時", banner: false },
    { label: "72 小時", offset: 72 * HOUR, text: "已等待 72 小時", banner: true },
    { label: "100 小時", offset: 100 * HOUR, text: "已等待 100 小時", banner: true },
  ])("AT_960_16_9 距最近一個 gate PASS 輪的 finishedAt $label：顯示「$text」（向下取整）；橫幅 $banner；推進一小時後數字加一；零寫入", async ({ offset, text, banner }) => {
    try {
      const { calls } = waitedAt(offset);
      await waitFor(() => expect(screen.getByTestId("gate-wait")).toHaveTextContent(text));
      if (banner) expect(screen.getByTestId("gate-wait-banner")).toHaveTextContent("已等待超過 72 小時，尚未核准");
      else expect(screen.queryByTestId("gate-wait-banner")).toBeNull();
      const hours = Number(/已等待 (\d+) 小時/.exec(screen.getByTestId("gate-wait").textContent ?? "")?.[1]);
      await act(async () => {
        vi.advanceTimersByTime(HOUR);
      });
      expect(screen.getByTestId("gate-wait")).toHaveTextContent(`已等待 ${hours + 1} 小時`);
      expect(writeCalls(calls), "全程只有讀取請求：橫幅只是顯示").toEqual([]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("AT_960_16_9 FSM 現態不是 HUMAN_PENDING（SCG_VALIDATION、ESCALATION）：不顯示等待時長；現態為 HUMAN_PENDING 但較新的一輪是 POST_HUMAN 通過時，起點取較早的 gate PASS 輪", async () => {
    try {
      const a = waitedAt(80 * HOUR, { stub: { fsm: fsmView("SCG_VALIDATION", {}, 1) } });
      await waitFor(() => expect(a.calls.some((c) => c.path.endsWith("/fsm"))).toBe(true));
      await settle();
      expect(screen.queryByTestId("gate-wait")).toBeNull();
      a.unmount();
      const b = waitedAt(80 * HOUR, { project: ESCALATED, stub: { fsm: FSM_ESCALATION } });
      await waitFor(() => expect(b.calls.some((c) => c.path.endsWith("/fsm"))).toBe(true));
      await settle();
      expect(screen.queryByTestId("gate-wait")).toBeNull();
      b.unmount();
      const postHuman = makeRound(2, PASS_SCORES[1], HEAD_NO, { triggerKind: "POST_HUMAN", fsmGateResult: null, fsmRetryCount: null, finishedAt: T2 });
      waitedAt(80 * HOUR, { stub: { rounds: [PASS_ROUND, postHuman] } });
      await waitFor(() => expect(screen.getByTestId("gate-wait")).toHaveTextContent("已等待 80 小時"));
    } finally {
      vi.useRealTimers();
    }
  });
});

// ── AT_960_16_E_2 審查狀態只由 stage run 與事件決定 ─────────────────────────────────────

describe("AT_960_16_E_2 審查狀態只由 stage run 與事件決定：進行中聽 research.run，輪完成才顯示分數與判定，無效輸出顯示原因與重新審查鈕且不出現新輪", () => {
  const HOSTILE = "<b>驗證失敗</b><script>alert(1)</script> ARCHITECTURE 缺少 rubric";
  const ROUND2 = makeRound(2, FAIL3_SCORES[1], HEAD_NO, { defects: [defect(2, 1, { severity: "P3" })] });

  it("AT_960_16_E_2 （一）REVIEW run 進行中：顯示審查中與四位審查者各自的進度列，分數區仍只有第 1 輪；（二）research.run 終態與 research.review 送達後才出現第 2 輪的分數與判定", async () => {
    const { options } = mount({ stub: { rounds: [FRESH_FAIL], events: [...BASE_EVENTS, runEvent(4, "RUNNING", 2)] } });
    const progress = await screen.findByTestId("review-progress");
    expect(progress).toHaveTextContent("審查中（第 2 輪）");
    expect(
      within(progress)
        .getAllByTestId("reviewer-progress")
        .map((r) => r.textContent),
    ).toEqual(["架構審查者審查中", "商業審查者審查中", "QA審查者審查中", "資安審查者審查中"]);
    expect(screen.getAllByTestId("review-score"), "審查中沒有輪列：只有第 1 輪的分數卡").toHaveLength(1);
    expect(screen.getByTestId("round-label")).toHaveTextContent("第 1 輪");
    expect(screen.queryByTestId("review-invalid")).toBeNull();
    expect(screen.queryByRole("button", { name: "重新審查" })).toBeNull();
    expect(button(ITERATE), "審查進行中：不能再送迭代").toBeDisabled();

    const es = await connected();
    options.rounds = [FRESH_FAIL, ROUND2];
    await send(es, runEvent(5, "SUCCEEDED", 2));
    expect(screen.queryByTestId("review-progress"), "run 已收尾").toBeNull();
    expect(screen.getByTestId("round-label"), "只有 run 終態、還沒有 research.review：輪表尚未更新").toHaveTextContent("第 1 輪");
    await send(es, reviewEvent(6, 2, "REVISE"));
    await waitFor(() => expect(screen.getByTestId("round-label")).toHaveTextContent("第 2 輪"), { timeout: 3000 });
    expect(screen.getByTestId("weighted-score")).toHaveTextContent("82.75");
    expect(screen.getAllByTestId("review-score")).toHaveLength(1);
  });

  it("AT_960_16_E_2 （三）REVIEW run 終態失敗並有 research.review_invalid：reason 以純文字顯示（哨兵不成為標記）、輪數仍為 1、沒有進行中的輪；按「重新審查」送 POST stages/review（本文不帶輪號與 attempt）", async () => {
    const user = userEvent.setup();
    const events = [...BASE_EVENTS, runEvent(4, "RUNNING", 2), runEvent(5, "FAILED", 2), ev(6, "research.review_invalid", { stageRunId: "run-review-2-1", roundNo: 2, attempt: 1, reason: HOSTILE })];
    const { calls, container } = mount({ role: "OPERATOR", stub: { rounds: [FRESH_FAIL], events } });
    const invalid = await screen.findByTestId("review-invalid");
    expect(within(invalid).getByTestId("review-invalid-reason").textContent, "reason 逐字純文字").toBe(HOSTILE);
    expect(invalid).toHaveTextContent("不佔輪次");
    expect(container.querySelector("script, b")).toBeNull();
    expect(screen.getByTestId("round-label")).toHaveTextContent("第 1 輪");
    expect(screen.getAllByTestId("review-score")).toHaveLength(1);
    expect(screen.queryByTestId("review-progress"), "沒有任何輪被標成進行中").toBeNull();
    await user.click(button("重新審查"));
    await waitFor(() => expect(callsOf(calls, "POST", /\/stages\/review$/)).toHaveLength(1));
    const body = callsOf(calls, "POST", /\/stages\/review$/)[0].body as Record<string, unknown>;
    expect(body).toEqual({});
    expect(body).not.toHaveProperty("roundNo");
    expect(body).not.toHaveProperty("attempt");
  });

  it("AT_960_16_E_2 （三）VIEWER：「重新審查」停用且 title 為權限不足", async () => {
    const events = [...BASE_EVENTS, runEvent(4, "FAILED", 2), ev(5, "research.review_invalid", { stageRunId: "x", roundNo: 2, attempt: 1, reason: "維度缺 rubric" })];
    mount({ role: "VIEWER", stub: { rounds: [FRESH_FAIL], events } });
    await screen.findByTestId("review-invalid");
    expect(button("重新審查")).toBeDisabled();
    expect(button("重新審查")).toHaveAttribute("title", READONLY_TITLE);
  });

  it("AT_960_16_E_2 reviewActivity 純函式：只看最近一次 REVIEW run；之後出現 research.review 就算收尾（不論 run 事件更新到哪）；研究 run 與 research.review 本身都不是進行中訊號；取消與失敗各有說明", () => {
    expect(reviewActivity([])).toEqual({ running: null, attention: null });
    expect(reviewActivity([runEvent(1, "RUNNING", 1)])).toEqual({ running: { roundNo: 1 }, attention: null });
    expect(reviewActivity([runEvent(1, "QUEUED", 3)])).toEqual({ running: { roundNo: 3 }, attention: null });
    expect(reviewActivity([runEvent(1, "RUNNING", 1), reviewEvent(2, 1)])).toEqual({ running: null, attention: null });
    expect(reviewActivity([reviewEvent(1, 1)])).toEqual({ running: null, attention: null });
    expect(reviewActivity([ev(1, "research.run", { stage: "RESEARCH", status: "RUNNING" })])).toEqual({ running: null, attention: null });
    expect(reviewActivity([runEvent(1, "RUNNING", 2), runEvent(2, "FAILED", 2)])).toEqual({ running: null, attention: { status: "FAILED", reason: null } });
    expect(reviewActivity([runEvent(1, "CANCELLED", 2)])).toEqual({ running: null, attention: { status: "CANCELLED", reason: null } });
    expect(reviewActivity([runEvent(1, "FAILED", 2), ev(2, "research.review_invalid", { reason: "缺維度" })])).toEqual({ running: null, attention: { status: "FAILED", reason: "缺維度" } });
    expect(reviewActivity([ev(1, "research.review_invalid", { reason: "缺維度" })])).toEqual({ running: null, attention: { status: "FAILED", reason: "缺維度" } });
    // 無效之後重新審查開始：回到進行中；新一輪完成：舊的無效原因不再顯示
    expect(reviewActivity([runEvent(1, "FAILED", 2), ev(2, "research.review_invalid", { reason: "舊" }), runEvent(3, "RUNNING", 2, 2)])).toEqual({ running: { roundNo: 2 }, attention: null });
    expect(reviewActivity([runEvent(1, "FAILED", 2), ev(2, "research.review_invalid", { reason: "舊" }), runEvent(3, "SUCCEEDED", 2, 2), reviewEvent(4, 2)])).toEqual({
      running: null,
      attention: null,
    });
    // 亂序到達也只看 seq
    expect(reviewActivity([runEvent(5, "RUNNING", 2), runEvent(4, "FAILED", 2)])).toEqual({ running: { roundNo: 2 }, attention: null });
  });

  it("AT_960_16_E_2 頁面剛載入的歷史事件不觸發重抓；載入之後的即時事件才讓輪表、版本與 FSM 視圖重抓（去抖成一次）", async () => {
    const { calls } = mount({ stub: { rounds: [FRESH_FAIL], events: BASE_EVENTS } });
    await screen.findByTestId("review-score");
    const es = await connected();
    await settle(450);
    const count = (re: RegExp) => callsOf(calls, "GET", re).length;
    expect(count(/\/review-rounds$/), "載入時各一次，歷史事件不再觸發").toBe(1);
    await send(es, runEvent(4, "RUNNING", 2));
    await send(es, alertEvent(5, "QUOTA", "額度"));
    await waitFor(() => expect(count(/\/review-rounds$/)).toBe(2), { timeout: 3000 });
    expect(count(/\/prd\/versions$/)).toBe(2);
    expect(count(/\/fsm$/)).toBe(2);
    expect(await screen.findByTestId("review-progress")).toBeInTheDocument();
  });
});

// ── AT_960_16_E_3 「第 n 輪」對照 FSM 重試史 ─────────────────────────────────────────────

describe("AT_960_16_E_3 「第 n 輪」取自輪表列數，並以 FSM 重試史筆數對照「目前世代的未通過輪數加 humanReturnCount」，不一致顯示警示、不自建第二套計數", () => {
  type Spec = { result: "PASS" | "FAIL" | null; generation?: number };
  const roundsOf = (specs: Spec[]): ResearchReviewRound[] =>
    specs.map((spec, i) => {
      const scores: Scores = spec.result === "FAIL" ? FAIL3_SCORES[1] : PASS_SCORES[1];
      return makeRound(i + 1, scores, HEAD_NO, {
        fsmGeneration: spec.generation ?? 1,
        fsmGateResult: spec.result,
        fsmRetryCount: spec.result === "FAIL" ? 1 : spec.result === "PASS" ? 0 : null,
        triggerKind: spec.result === null ? "POST_HUMAN" : "AUTO",
        defects: [defect(i + 1, 1, { severity: "P3" })],
      });
    });
  const fsmOf = (entries: number, humanReturnCount: number): ResearchFsmView =>
    fsmView("SPEC_DRAFTING", {
      humanReturnCount,
      retryHistory: {
        count: entries,
        last: null,
        gates: { SCG_VALIDATION: { currentCount: entries, entries }, PR_REVIEW: { currentCount: 0, entries: 0 }, RTM_VERIFY: { currentCount: 0, entries: 0 } },
      },
    });

  const CASES = [
    { name: "甲＝兩輪皆 gate FAIL、entries 為 2", specs: [{ result: "FAIL" }, { result: "FAIL" }] as Spec[], entries: 2, human: 0, generation: 1, label: 2, warn: null, actual: 2 },
    {
      name: "乙＝第 1 輪 PASS、人工退回一次、第 2 輪（POST_HUMAN）FAIL、entries 為 2",
      specs: [{ result: "PASS" }, { result: "FAIL" }] as Spec[],
      entries: 2,
      human: 1,
      generation: 1,
      label: 2,
      warn: null,
      actual: 2,
    },
    { name: "丙＝同甲而 entries 為 1", specs: [{ result: "FAIL" }, { result: "FAIL" }] as Spec[], entries: 1, human: 0, generation: 1, label: 2, warn: 2, actual: 1 },
    { name: "丁＝同乙而 entries 為 3", specs: [{ result: "PASS" }, { result: "FAIL" }] as Spec[], entries: 3, human: 1, generation: 1, label: 2, warn: 2, actual: 3 },
    {
      name: "戊＝第 1 輪 PASS、人工退回一次、第 2 輪 POST_HUMAN 通過（fsmGateResult 為 NULL）、entries 為 1",
      specs: [{ result: "PASS" }, { result: null }] as Spec[],
      entries: 1,
      human: 1,
      generation: 1,
      label: 2,
      warn: null,
      actual: 1,
    },
    {
      name: "己＝專案世代 2：世代 1 的兩輪 FAIL 與世代 2 的一輪 FAIL、entries 為 1",
      specs: [{ result: "FAIL" }, { result: "FAIL" }, { result: "FAIL", generation: 2 }] as Spec[],
      entries: 1,
      human: 0,
      generation: 2,
      label: 3,
      warn: null,
      actual: 1,
    },
  ];

  it.each(CASES)("AT_960_16_E_3 $name：「第 n 輪」為 $label、警示 $warn", async ({ specs, entries, human, generation, label, warn, actual }) => {
    const { calls } = mount({ project: detailVariant("studio", { fsmGeneration: generation }), stub: { rounds: roundsOf(specs), fsm: fsmOf(entries, human) } });
    await waitFor(() => expect(screen.getByTestId("round-label")).toHaveTextContent(`第 ${label} 輪`));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith("/fsm"))).toBe(true));
    await settle();
    if (warn === null) {
      expect(screen.queryByTestId("integrity-warning")).toBeNull();
    } else {
      const alert = await screen.findByTestId("integrity-warning");
      expect(alert).toHaveTextContent(`期望 ${warn}`);
      expect(alert).toHaveTextContent(`實際 ${actual}`);
    }
    expect(writeCalls(calls), "全程只有讀取請求").toEqual([]);
  });

  it("AT_960_16_E_3 retryHistoryCheck 純函式：期望＝目前世代 gate FAIL 輪數加 humanReturnCount、實際只取 retryHistory.gates.SCG_VALIDATION.entries；沒有該閘資料回 null（不警示）", () => {
    const rounds = roundsOf([{ result: "FAIL" }, { result: "FAIL", generation: 2 }, { result: "PASS", generation: 2 }, { result: null, generation: 2 }]);
    expect(retryHistoryCheck(rounds, 2, fsmOf(1, 0))).toEqual({ expected: 1, actual: 1, ok: true });
    expect(retryHistoryCheck(rounds, 2, fsmOf(2, 1))).toEqual({ expected: 2, actual: 2, ok: true });
    expect(retryHistoryCheck(rounds, 1, fsmOf(2, 0))).toEqual({ expected: 1, actual: 2, ok: false });
    const noGate = { ...fsmOf(0, 0), retryHistory: { count: 0, last: null, gates: {} } } as ResearchFsmView;
    expect(retryHistoryCheck(rounds, 2, noGate)).toBeNull();
    expect(retryHistoryCheck(rounds, 2, { humanReturnCount: 0, retryHistory: { count: 0, last: null } } as unknown as ResearchFsmView)).toBeNull();
  });

  it("AT_960_16_E_3 元件原始碼沒有自己累計重試計數：不讀輪列的重試計數欄位、不自寫上限；剩餘預算經 remainingReviewBudget 與 reviewRetryCount；只有一處讀 retryHistory", () => {
    const source = stripComments(readFileSync(path.join(process.cwd(), "components", "domain", "research", "GatekeeperPanel.tsx"), "utf-8"));
    expect(source).not.toMatch(/fsmRetryCount|setRetry\w*|retryCount\s*\+\+/);
    expect(source).toMatch(/remainingReviewBudget\(/);
    expect(source).toMatch(/reviewRetryCount\(fsm\)/);
    expect(source.match(/\.retryHistory/g)?.length, "retryHistory 只在 retryHistoryCheck 內讀取一次").toBe(1);
    expect(source).not.toMatch(/\b3\s*-\s*[\w.?]*[cC]ount|RETRY_LIMIT\s*=\s*\d/);
  });
});
