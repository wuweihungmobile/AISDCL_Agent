import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, expectTypeOf, it } from "vitest";

import { reviewConsequence } from "@/components/domain/execute/reviewHelp";
import { GATE_LABEL } from "@/components/domain/import/gateErrors";
import { SERVICE_LABEL, type ServiceState } from "@/hooks/useServiceStatus";
import type { AlertRule, ExecutionStepStatus, GateName, GoalStatus, ImportStatus, ProjectStatus, ReviewDecision, ReviewKind, RunStatus, TaskStatus } from "@/lib/api/types";
import { SDD_PHASE_LABEL } from "@/lib/domain/sdd";
import { OBS_STATUS_OPTIONS, PROPOSAL_STATUS_OPTIONS, PROP_STATE_KEYS, propStatusClass, type ObsStatusClass, type PropStatusClass } from "@/lib/domain/si";
import {
  ALERT_RULE_LABEL,
  ALERT_SEVERITY,
  BRIDGE_TRANSITION,
  GOAL_STATUS,
  IMPORT_STATUS,
  PROJECT_STATUS,
  REVIEW_DECISION_LABEL,
  REVIEW_KIND,
  RUN_STATUS,
  STEP_STATUS,
  TASK_STATUS,
} from "@/lib/domain/status";
import { HELP_PAGES } from "@/lib/help/registry";
import { STATE_HELP } from "@/lib/help/states";
import type { HelpStateGroup, PageHelp, StateRow, StateTableId } from "@/lib/help/types";
import { STATE_SOURCES, type StateSource } from "./stateSources";

/**
 * 狀態詞不自持、鍵集合雙向鎖與型別鎖（TCS-PageHelp-20261027 FR-PH-04；R-PH-08～R-PH-10、R-PH-13、R-PH-14；載具 HK，輪 1a）：
 *  - AT-PH-04-1-1、1-2、1-3、1-E-1、1-E-2：STATE_SOURCES、STATE_HELP 與上游常數的鍵集合雙向相等；sddFsmState 只有子字串弱鎖；
 *  - AT-PH-04-2-1、2-2、2-3、2-E-1（TC）：StateRow 只有 meaning 與 next；十張表的鍵型別等式、serviceState 的字面值聯集；
 *    型別鎖由 `npx tsc --noEmit` 判定（tsc 含測試檔，@ts-expect-error 失效＝指令未使用＝tsc 紅）；
 *  - AT-PH-04-3-1、3-3、3-E-1：名稱模式（label 取自 labelOf、raw 取鍵本身；無 labelOf 的表只准 raw）；
 *  - AT-PH-04-6-1、6-3：自我進化三張表與 retired 的白話註記（PRD D-8）；
 *  - AT-PH-04-7-1、7-2、7-E-1：reviewDecision 與審核後果表的一致性（後果文字只住 execute/reviewHelp.ts）。
 * 判定指令：npx vitest run components/domain/help/stateKeys.test.ts -t "<AT 底線形>"；TC 者另跑 npx tsc --noEmit。
 *
 * UPSTREAM 一律在測試內**直接 import 既有常數**、不經 STATE_SOURCES：否則 STATE_SOURCES 與被測物同源，鎖就成了自己驗自己。
 */

const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");

/** 必備的 18 張表（PRD §8.2；只准增不准減）。 */
const REQUIRED_TABLE_IDS = [
  "projectStatus",
  "goalStatus",
  "taskStatus",
  "stepStatus",
  "importStatus",
  "runStatus",
  "runTransition",
  "reviewKind",
  "reviewDecision",
  "alertSeverity",
  "alertRule",
  "gateName",
  "sddPhase",
  "sddFsmState",
  "serviceState",
  "obsClass",
  "propClass",
  "propState",
] as const satisfies readonly StateTableId[];

/** sddFsmState 的五個鍵（PRD §8.2 備註 2；無單一常數可現讀，只有子字串弱鎖）。 */
const SDD_FSM_KEYS = ["HUMAN_PENDING", "SPEC_FROZEN", "ESCALATION", "ESCALATION_FINAL", "AUTOCLAUDE_DELEGATED"] as const;

type Upstream = { keys: () => string[]; label?: (key: string) => string | undefined };
type UpstreamId = Exclude<StateTableId, "sddFsmState">;

const optionKeys = (options: ReadonlyArray<{ id: string; label: string }>): string[] => options.filter((o) => o.id !== "").map((o) => o.id);
const optionLabel = (options: ReadonlyArray<{ id: string; label: string }>) => (key: string) => options.find((o) => o.id === key)?.label;

/** 表 id→上游常數的鍵取法與標籤取法（TCS §5.3 `UPSTREAM`；無 label＝只准 raw）。 */
const UPSTREAM: Record<UpstreamId, Upstream> = {
  projectStatus: { keys: () => Object.keys(PROJECT_STATUS), label: (k) => PROJECT_STATUS[k as ProjectStatus].label },
  goalStatus: { keys: () => Object.keys(GOAL_STATUS), label: (k) => GOAL_STATUS[k as GoalStatus].label },
  taskStatus: { keys: () => Object.keys(TASK_STATUS), label: (k) => TASK_STATUS[k as TaskStatus].label },
  stepStatus: { keys: () => Object.keys(STEP_STATUS), label: (k) => STEP_STATUS[k as ExecutionStepStatus].label },
  importStatus: { keys: () => Object.keys(IMPORT_STATUS), label: (k) => IMPORT_STATUS[k as ImportStatus].label },
  runStatus: { keys: () => Object.keys(RUN_STATUS), label: (k) => RUN_STATUS[k as RunStatus].label },
  runTransition: { keys: () => Object.keys(BRIDGE_TRANSITION), label: (k) => BRIDGE_TRANSITION[k as keyof typeof BRIDGE_TRANSITION]?.label },
  reviewKind: { keys: () => Object.keys(REVIEW_KIND), label: (k) => REVIEW_KIND[k as ReviewKind].label },
  reviewDecision: { keys: () => Object.keys(REVIEW_DECISION_LABEL), label: (k) => REVIEW_DECISION_LABEL[k as ReviewDecision] },
  alertSeverity: { keys: () => Object.keys(ALERT_SEVERITY), label: (k) => ALERT_SEVERITY[k as keyof typeof ALERT_SEVERITY].label },
  alertRule: { keys: () => Object.keys(ALERT_RULE_LABEL), label: (k) => ALERT_RULE_LABEL[k as AlertRule] },
  gateName: { keys: () => Object.keys(GATE_LABEL), label: (k) => GATE_LABEL[k as GateName] },
  sddPhase: { keys: () => Object.keys(SDD_PHASE_LABEL), label: (k) => SDD_PHASE_LABEL[k] },
  serviceState: { keys: () => Object.keys(SERVICE_LABEL), label: (k) => SERVICE_LABEL[k as ServiceState] },
  obsClass: { keys: () => optionKeys(OBS_STATUS_OPTIONS), label: optionLabel(OBS_STATUS_OPTIONS) },
  propClass: { keys: () => optionKeys(PROPOSAL_STATUS_OPTIONS), label: optionLabel(PROPOSAL_STATUS_OPTIONS) },
  propState: { keys: () => [...PROP_STATE_KEYS] },
};
const UPSTREAM_IDS = Object.keys(UPSTREAM) as UpstreamId[];

// ── 測試內的純函式（各有負控）─────────────────────────────────────────────────

/** 兩個鍵集合的差異：說明缺鍵、說明多出鍵各一筆；順序不同不算差異。 */
function keyProblems(upstreamKeys: readonly string[], helpKeys: readonly string[]): string[] {
  const out: string[] = [];
  for (const key of upstreamKeys) if (!helpKeys.includes(key)) out.push(`說明缺：${key}`);
  for (const key of helpKeys) if (!upstreamKeys.includes(key)) out.push(`說明多出：${key}`);
  return out;
}

function parse(source: string): ts.SourceFile {
  return ts.createSourceFile("scan.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

function walkAst(node: ts.Node, visit: (n: ts.Node) => void): void {
  visit(node);
  ts.forEachChild(node, (child) => walkAst(child, visit));
}

/** import／export from、動態 import()、require() 的模組位址節點（它們是位址，不是「文字」）。 */
function moduleSpecifierNodes(sf: ts.SourceFile): Set<ts.Node> {
  const specs = new Set<ts.Node>();
  walkAst(sf, (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier) specs.add(n.moduleSpecifier);
    if (ts.isCallExpression(n) && n.arguments.length > 0 && (n.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(n.expression) && n.expression.text === "require")))
      specs.add(n.arguments[0]);
  });
  return specs;
}

function moduleNames(source: string): string[] {
  return [...moduleSpecifierNodes(parse(source))].filter(ts.isStringLiteralLike).map((n) => n.text);
}

/** 字串字面值（含 JSX 屬性值）、樣板字串片段與 JSX 文字；不含註解與模組位址（沿 issues.static.test.ts 的 literalTexts，另加 JSX 文字）。 */
function collectTexts(source: string): string[] {
  const sf = parse(source);
  const specs = moduleSpecifierNodes(sf);
  const out: string[] = [];
  walkAst(sf, (n) => {
    if (specs.has(n)) return;
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) out.push(n.text);
    else if (ts.isTemplateExpression(n)) {
      out.push(n.head.text);
      for (const span of n.templateSpans) out.push(span.literal.text);
    } else if (ts.isJsxText(n)) out.push(n.text);
  });
  return out;
}

/** 弱鎖：每個鍵須以子字串出現在某段文字內（不是等號，也不看註解）；回傳找不到的鍵。 */
function weakLockProblems(keys: readonly string[], sources: readonly string[]): string[] {
  const texts = sources.flatMap(collectTexts);
  return keys.filter((key) => !texts.some((text) => text.includes(key)));
}

/** 名稱模式：無 labelOf 的表只准 raw；name 只能是 label 或 raw；表 id 要在來源表內；legend 群只有議題中心一種。 */
function nameModeProblems(group: HelpStateGroup, sources: Readonly<Record<string, StateSource | undefined>>): string[] {
  if ("legend" in group) return (group.legend as string) === "issues" ? [] : [`未知的詞表群：${String(group.legend)}`];
  const source = sources[group.table];
  if (!source) return [`表 id 不在來源表：${group.table}`];
  const name: string = group.name ?? "label";
  if (name !== "label" && name !== "raw") return [`名稱模式只能是 label 或 raw：${name}`];
  if (name === "label" && !source.labelOf) return [`${group.table} 沒有 labelOf，只准 raw`];
  return [];
}

/** 每個決定至少要在一個審核種類有非預設的後果句；回傳沒有的決定。 */
function decisionCoverageProblems(decisions: readonly string[], kinds: readonly string[], consequence: (kind: string, decision: string) => string, defaultSentence: string): string[] {
  return decisions.filter((decision) => kinds.every((kind) => consequence(kind, decision) === defaultSentence));
}

function walkSources(dir: string, out: string[] = []): string[] {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (!["node_modules", "tests"].includes(name)) walkSources(full, out);
    } else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name) && !/\.fixtures\.ts$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

// ── AC-PH-04-1：鍵集合雙向鎖 ────────────────────────────────────────────────────

describe("AT_PH_04_1 鍵集合雙向鎖（R-PH-08）", () => {
  it("AT_PH_04_1_1 除 sddFsmState 外每張表：STATE_SOURCES.keys、STATE_HELP 的鍵與上游常數的鍵三者集合相等（常數新增狀態而說明沒補、說明多出不存在的狀態都紅）", () => {
    expect(UPSTREAM_IDS.length, "防反空轉：檢查的表數").toBeGreaterThanOrEqual(17);
    for (const id of UPSTREAM_IDS) {
      const upstream = UPSTREAM[id].keys();
      expect(upstream.length, `${id} 的上游常數沒有任何鍵`).toBeGreaterThan(0);
      expect(keyProblems(upstream, STATE_SOURCES[id].keys), `${id} 的 STATE_SOURCES.keys 與上游常數`).toEqual([]);
      expect(keyProblems(upstream, Object.keys(STATE_HELP[id])), `${id} 的 STATE_HELP 與上游常數`).toEqual([]);
    }
  });

  it("AT_PH_04_1_2 sddFsmState：說明的鍵恰為五個，每個鍵都以子字串出現在 lib/domain/sdd.ts 或 components/domain/sdd/** 的字串字面值、樣板片段或 JSX 文字；只准 raw（沒有 labelOf）", () => {
    expect([...Object.keys(STATE_HELP.sddFsmState)].sort()).toEqual([...SDD_FSM_KEYS].sort());
    expect([...STATE_SOURCES.sddFsmState.keys].sort()).toEqual([...SDD_FSM_KEYS].sort());
    const files = [path.join(ROOT, "lib/domain/sdd.ts"), ...walkSources(path.join(ROOT, "components/domain/sdd"))];
    expect(files.length, "防反空轉：掃描檔數").toBeGreaterThanOrEqual(2);
    expect(
      weakLockProblems(
        SDD_FSM_KEYS,
        files.map((f) => readFileSync(f, "utf-8")),
      ),
      `掃描範圍：${files.map(rel).join("、")}`,
    ).toEqual([]);
    expect(STATE_SOURCES.sddFsmState.labelOf, "sddFsmState 沒有可現讀的名稱常數，只准 raw").toBeUndefined();
  });

  it("AT_PH_04_1_3 表登記總覽：STATE_HELP 與 STATE_SOURCES 的表 id 集合相等且包含必備的 18 張；每張表至少一列、每列 meaning 與 next 為非空字串，來源有標題與非空的鍵", () => {
    const helpIds = Object.keys(STATE_HELP).sort();
    expect(helpIds).toEqual(Object.keys(STATE_SOURCES).sort());
    for (const id of REQUIRED_TABLE_IDS) expect(helpIds, `必備的表 ${id}`).toContain(id);
    for (const id of helpIds as StateTableId[]) {
      const rows = Object.entries<StateRow>(STATE_HELP[id]);
      expect(rows.length, `${id} 至少一列`).toBeGreaterThan(0);
      for (const [key, row] of rows) {
        expect(typeof row.meaning === "string" && row.meaning.trim() !== "", `${id}.${key}.meaning`).toBe(true);
        expect(typeof row.next === "string" && row.next.trim() !== "", `${id}.${key}.next`).toBe(true);
        expect(Object.keys(row).sort(), `${id}.${key} 只有 meaning 與 next 兩欄`).toEqual(["meaning", "next"]);
      }
      expect(STATE_SOURCES[id].title.trim(), `${id} 的 title`).not.toBe("");
      expect(STATE_SOURCES[id].keys.length, `${id} 的 keys`).toBeGreaterThan(0);
    }
  });

  it("AT_PH_04_1_E_1 keyProblems 負控：說明缺一鍵回「說明缺」、多一鍵回「說明多出」、兩者並存各一筆；相等回空；順序不同不算差異", () => {
    expect(keyProblems(["A", "B", "C"], ["A", "B"])).toEqual(["說明缺：C"]);
    expect(keyProblems(["A", "B"], ["A", "B", "Z"])).toEqual(["說明多出：Z"]);
    expect(keyProblems(["A", "B"], ["A", "Z"])).toEqual(["說明缺：B", "說明多出：Z"]);
    expect(keyProblems(["A", "B"], ["B", "A"])).toEqual([]);
    expect(keyProblems([], [])).toEqual([]);
  });

  it("AT_PH_04_1_E_2 弱鎖掃描器負控：只在註解或完全不出現的鍵被回報；字串字面值的子字串、樣板片段、JSX 文字都算；五個鍵俱在回空", () => {
    const keys = ["HUMAN_PENDING", "SPEC_FROZEN"];
    expect(weakLockProblems(keys, ["// 這裡提到 HUMAN_PENDING 與 SPEC_FROZEN\nconst a = 1;"])).toEqual(keys);
    expect(weakLockProblems(keys, ["/* HUMAN_PENDING SPEC_FROZEN */\nconst a = 1;"])).toEqual(keys);
    expect(weakLockProblems(keys, ["const a = 1;"])).toEqual(keys);
    expect(weakLockProblems(["SPEC_FROZEN"], ['const t = "核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定";'])).toEqual([]);
    expect(weakLockProblems(["SPEC_FROZEN"], ["const t = `狀態 ${n} 是 SPEC_FROZEN`;"])).toEqual([]);
    expect(weakLockProblems(["SPEC_FROZEN"], ["const el = <p>現在是 SPEC_FROZEN 狀態</p>;"])).toEqual([]);
    expect(weakLockProblems(["SPEC_FROZEN"], ['const el = <Dialog description="進入 SPEC_FROZEN" />;'])).toEqual([]);
    // 模組位址不算文字
    expect(weakLockProblems(["SPEC_FROZEN"], ['import { x } from "@/lib/SPEC_FROZEN";'])).toEqual(["SPEC_FROZEN"]);
    // 兩個鍵分散在兩個檔案各自出現也算
    expect(weakLockProblems(keys, ['const a = "HUMAN_PENDING";', 'const b = "SPEC_FROZEN";'])).toEqual([]);
    expect(
      weakLockProblems(
        [...SDD_FSM_KEYS],
        SDD_FSM_KEYS.map((k) => `const x = "${k}";`),
      ),
    ).toEqual([]);
  });
});

// ── AC-PH-04-2：型別鎖（TC；由 npx tsc --noEmit 判定）──────────────────────────────

describe("AT_PH_04_2 型別鎖（R-PH-01、R-PH-09）", () => {
  it("AT_PH_04_2_1 StateRow 只有 meaning 與 next：型別等式；帶 label 或 name 欄位的物件字面值都被型別擋下（兩個 @ts-expect-error 失效時 tsc 轉紅）", () => {
    expectTypeOf<StateRow>().toEqualTypeOf<{ meaning: string; next: string }>();
    // @ts-expect-error 多餘欄位 label：StateRow 刻意沒有名稱欄，名稱只取自既有常數表
    const withLabel: StateRow = { meaning: "x", next: "y", label: "z" };
    // @ts-expect-error 多餘欄位 name：同上
    const withName: StateRow = { meaning: "x", next: "y", name: "z" };
    expect([withLabel.meaning, withName.next]).toEqual(["x", "y"]);
    // 執行期側：真的列也只有兩欄
    for (const id of Object.keys(STATE_HELP) as StateTableId[]) for (const row of Object.values<StateRow>(STATE_HELP[id])) expect(Object.keys(row).sort()).toEqual(["meaning", "next"]);
  });

  it("AT_PH_04_2_2 十張有後端 enum 的表：各表的鍵型別等式於對應的 enum（enum 經 schema 重產而新增值時，這十行即編譯紅）", () => {
    expectTypeOf<keyof typeof STATE_HELP.projectStatus>().toEqualTypeOf<ProjectStatus>();
    expectTypeOf<keyof typeof STATE_HELP.goalStatus>().toEqualTypeOf<GoalStatus>();
    expectTypeOf<keyof typeof STATE_HELP.taskStatus>().toEqualTypeOf<TaskStatus>();
    expectTypeOf<keyof typeof STATE_HELP.importStatus>().toEqualTypeOf<ImportStatus>();
    expectTypeOf<keyof typeof STATE_HELP.runStatus>().toEqualTypeOf<RunStatus>();
    expectTypeOf<keyof typeof STATE_HELP.reviewKind>().toEqualTypeOf<ReviewKind>();
    expectTypeOf<keyof typeof STATE_HELP.reviewDecision>().toEqualTypeOf<ReviewDecision>();
    expectTypeOf<keyof typeof STATE_HELP.stepStatus>().toEqualTypeOf<ExecutionStepStatus>();
    expectTypeOf<keyof typeof STATE_HELP.alertRule>().toEqualTypeOf<AlertRule>();
    expectTypeOf<keyof typeof STATE_HELP.gateName>().toEqualTypeOf<GateName>();
    const tenTables = [
      STATE_HELP.projectStatus,
      STATE_HELP.goalStatus,
      STATE_HELP.taskStatus,
      STATE_HELP.importStatus,
      STATE_HELP.runStatus,
      STATE_HELP.reviewKind,
      STATE_HELP.reviewDecision,
      STATE_HELP.stepStatus,
      STATE_HELP.alertRule,
      STATE_HELP.gateName,
    ];
    expect(tenTables).toHaveLength(10);
    for (const table of tenTables) expect(Object.keys(table).length).toBeGreaterThan(0);
  });

  it("AT_PH_04_2_3 serviceState 以字面值聯集宣告且鍵型別等式於 ServiceState（另鎖 obsClass、propClass 的字面值聯集）；lib/help/** 沒有 import hooks 與 components", () => {
    expectTypeOf<keyof typeof STATE_HELP.serviceState>().toEqualTypeOf<ServiceState>();
    expectTypeOf<keyof typeof STATE_HELP.obsClass>().toEqualTypeOf<ObsStatusClass>();
    expectTypeOf<keyof typeof STATE_HELP.propClass>().toEqualTypeOf<Exclude<PropStatusClass, "unknown">>();
    expect(Object.keys(STATE_HELP.serviceState).sort()).toEqual(Object.keys(SERVICE_LABEL).sort());

    const files = walkSources(path.join(ROOT, "lib/help"));
    expect(files.length, "防反空轉：lib/help 非測試檔數").toBeGreaterThanOrEqual(5);
    for (const file of files) {
      for (const spec of moduleNames(readFileSync(file, "utf-8"))) {
        expect(/^@\/(hooks|components)\//.test(spec) || /(^|\/)(hooks|components)\//.test(spec), `${rel(file)} 不得 import ${spec}（lib 不依賴 hooks 與元件）`).toBe(false);
      }
    }
    // types.ts 是純型別檔：沒有任何 import
    expect(moduleNames(readFileSync(path.join(ROOT, "lib/help/types.ts"), "utf-8"))).toEqual([]);
  });

  it("AT_PH_04_2_E_1 「enum 多一值」與「表少一鍵」都被型別擋下：兩個 @ts-expect-error 必須生效（失效時 tsc 回報指令未使用）；真的表可指派給各自完整的 enum 紀錄型別", () => {
    type Widened = keyof (Record<ProjectStatus, 0> & { HOLD: 0 });
    // @ts-expect-error 缺 HOLD：專案狀態 enum 多出一個值而說明表沒補，型別必須紅
    const widened: Record<Widened, StateRow> = STATE_HELP.projectStatus;
    type MissingOne = Omit<typeof STATE_HELP.taskStatus, "PAUSED">;
    // @ts-expect-error 少一鍵：說明表缺一個狀態，指派給完整的 enum 紀錄型別必須紅
    const incomplete: Record<TaskStatus, StateRow> = {} as MissingOne;
    // 對照組：真的表本身可以指派給完整的 enum 紀錄型別（缺鍵時這幾行就編譯失敗）
    const projects: Record<ProjectStatus, StateRow> = STATE_HELP.projectStatus;
    const tasks: Record<TaskStatus, StateRow> = STATE_HELP.taskStatus;
    expect(widened).toBe(STATE_HELP.projectStatus);
    expect(incomplete).toEqual({});
    expect(Object.keys(projects).sort()).toEqual(Object.keys(PROJECT_STATUS).sort());
    expect(Object.keys(tasks).sort()).toEqual(Object.keys(TASK_STATUS).sort());
  });
});

// ── AC-PH-04-3：名稱模式 ────────────────────────────────────────────────────────

describe("AT_PH_04_3 名稱模式（R-PH-10）", () => {
  it("AT_PH_04_3_1 每張有 labelOf 的表：labelOf(鍵) 等於上游常數同鍵的標籤且為非空字串；sddFsmState、propState 沒有 labelOf", () => {
    let checked = 0;
    for (const id of UPSTREAM_IDS) {
      const upstream = UPSTREAM[id];
      const source = STATE_SOURCES[id];
      if (upstream.label === undefined) {
        expect(source.labelOf, `${id} 無上游標籤，只准 raw`).toBeUndefined();
        continue;
      }
      expect(source.labelOf, `${id} 必須有 labelOf`).toBeDefined();
      for (const key of upstream.keys()) {
        const expected = upstream.label(key);
        expect(typeof expected === "string" && expected !== "", `${id}.${key} 上游標籤`).toBe(true);
        expect(source.labelOf?.(key), `${id}.${key} 的 labelOf`).toBe(expected);
        checked += 1;
      }
      // 未登記的鍵顯示原值、不丟例外（與 lib/domain/status.ts 的 lookup 對未知狀態的行為一致：後端日後新增狀態，畫面不崩潰）
      expect(source.labelOf?.("__未登記的鍵__"), `${id} 對未登記的鍵顯示原值`).toBe("__未登記的鍵__");
    }
    expect(checked, "防反空轉：逐鍵檢查的標籤數").toBeGreaterThan(60);
    expect(STATE_SOURCES.sddFsmState.labelOf).toBeUndefined();
    expect(STATE_SOURCES.propState.labelOf).toBeUndefined();
    // 抽查幾個畫面字樣（PRD §8.2：名稱取自同一常數，說明不另抄）
    expect(STATE_SOURCES.projectStatus.labelOf?.("DRAFT")).toBe(PROJECT_STATUS.DRAFT.label);
    expect(STATE_SOURCES.reviewDecision.labelOf?.("APPROVE")).toBe(REVIEW_DECISION_LABEL.APPROVE);
    expect(STATE_SOURCES.serviceState.labelOf?.("online")).toBe(SERVICE_LABEL.online);
    expect(STATE_SOURCES.gateName.labelOf?.("cycle")).toBe(GATE_LABEL.cycle);
    expect(STATE_SOURCES.sddPhase.labelOf?.("INTAKE")).toBe(SDD_PHASE_LABEL.INTAKE);
    expect(STATE_SOURCES.obsClass.labelOf?.("open")).toBe(OBS_STATUS_OPTIONS.find((o) => o.id === "open")?.label);
  });

  it("AT_PH_04_3_3 每個已寫頁的每個狀態群：無 labelOf 的表只准 name 為 raw；name 只能是 label 或 raw；legend 群只出現在 issues 頁；每個表 id 都在 STATE_SOURCES 內", () => {
    const pages = Object.values(HELP_PAGES).filter((page): page is PageHelp => page !== undefined);
    let tableGroups = 0;
    let legendGroups = 0;
    for (const page of pages) {
      for (const group of page.states) {
        expect(nameModeProblems(group, STATE_SOURCES), `${page.id} 的狀態群 ${JSON.stringify(group)}`).toEqual([]);
        if ("legend" in group) {
          legendGroups += 1;
          expect(page.id, "legend 群只准出現在議題中心頁").toBe("issues");
        } else tableGroups += 1;
      }
    }
    expect(pages.length, "防反空轉：已寫頁數").toBeGreaterThanOrEqual(3);
    expect(tableGroups, "防反空轉：已寫頁至少有一個表群").toBeGreaterThanOrEqual(1);
    expect(legendGroups, "議題中心頁有 legend 群").toBe(1);
  });

  it("AT_PH_04_3_E_1 nameModeProblems 負控：缺省（label）卻沒有 labelOf、name 值不合法、表 id 不在來源表各回非空；raw 與有 labelOf 的表可選 raw 回空", () => {
    expect(nameModeProblems({ table: "propState" }, STATE_SOURCES)).not.toEqual([]);
    expect(nameModeProblems({ table: "propState", name: "label" }, STATE_SOURCES)).not.toEqual([]);
    expect(nameModeProblems({ table: "sddFsmState" }, STATE_SOURCES)).not.toEqual([]);
    expect(nameModeProblems({ table: "propState", name: "raw" }, STATE_SOURCES)).toEqual([]);
    expect(nameModeProblems({ table: "projectStatus", name: "raw" }, STATE_SOURCES)).toEqual([]);
    expect(nameModeProblems({ table: "projectStatus" }, STATE_SOURCES)).toEqual([]);
    expect(nameModeProblems({ table: "projectStatus", name: "label" }, STATE_SOURCES)).toEqual([]);
    expect(nameModeProblems({ table: "projectStatus", name: "foo" as "raw" }, STATE_SOURCES)).not.toEqual([]);
    expect(nameModeProblems({ table: "nope" as StateTableId }, STATE_SOURCES)).not.toEqual([]);
    expect(nameModeProblems({ legend: "issues" }, STATE_SOURCES)).toEqual([]);
  });
});

// ── AC-PH-04-6：自我進化三張表 ─────────────────────────────────────────────────

describe("AT_PH_04_6 自我進化的名稱模式（R-PH-13）", () => {
  it("AT_PH_04_6_1 PROP_STATE_KEYS 每個鍵都有歸類且 ⊇ 根層十個提案狀態並含 retired；propState 的來源鍵與說明鍵皆等於它；obsClass、propClass 的鍵與標籤取自各自的 OPTIONS（去掉「全部」）", () => {
    const rootProposalStates = ["proposed", "approved", "rejected", "returned", "handed-off", "sandboxed", "verified", "promoted", "measuring", "closed"];
    for (const key of PROP_STATE_KEYS) expect(propStatusClass(key), `${key} 沒有歸類`).not.toBe("unknown");
    for (const state of rootProposalStates) expect(PROP_STATE_KEYS, `根層提案狀態 ${state}`).toContain(state);
    expect(PROP_STATE_KEYS).toContain("retired");
    expect([...STATE_SOURCES.propState.keys].sort()).toEqual([...PROP_STATE_KEYS].sort());
    expect(Object.keys(STATE_HELP.propState).sort()).toEqual([...PROP_STATE_KEYS].sort());

    const optionTables: Array<[StateTableId, ReadonlyArray<{ id: string; label: string }>]> = [
      ["obsClass", OBS_STATUS_OPTIONS],
      ["propClass", PROPOSAL_STATUS_OPTIONS],
    ];
    for (const [id, options] of optionTables) {
      const expectedKeys = options.filter((o) => o.id !== "").map((o) => o.id);
      expect(expectedKeys.length, `${id} 的 OPTIONS 去掉「全部」後不該是空的`).toBeGreaterThan(0);
      expect([...STATE_SOURCES[id].keys].sort()).toEqual([...expectedKeys].sort());
      for (const option of options.filter((o) => o.id !== "")) expect(STATE_SOURCES[id].labelOf?.(option.id), `${id}.${option.id}`).toBe(option.label);
      // 「全部」不是一個狀態：說明表不列它
      expect(Object.keys(STATE_HELP[id])).not.toContain("");
    }
  });

  it("AT_PH_04_6_3 propState.retired 的 meaning 寫明「根層目前不會產生這個狀態，畫面為日後預留」（PRD D-8）", () => {
    expect(STATE_HELP.propState.retired.meaning).toContain("根層目前不會產生這個狀態，畫面為日後預留");
  });
});

// ── AC-PH-04-7：reviewDecision 與後果表 ──────────────────────────────────────────

const DEFAULT_CONSEQUENCE = "依後端規則處理。";
const REVIEW_KINDS = Object.keys(REVIEW_KIND) as ReviewKind[];
const REVIEW_DECISIONS = Object.keys(REVIEW_DECISION_LABEL) as ReviewDecision[];
const consequenceOf = (kind: string, decision: string): string => reviewConsequence(kind as ReviewKind, decision as ReviewDecision);

describe("AT_PH_04_7 reviewDecision 與審核後果表一致（R-PH-14）", () => {
  it("AT_PH_04_7_1 每個決定至少在一個審核種類回傳非預設句；STATE_HELP.reviewDecision 的鍵集合等於決定集合（決定新增而後果表沒補＝紅）", () => {
    expect(REVIEW_KINDS.length).toBeGreaterThanOrEqual(4);
    expect(REVIEW_DECISIONS.length).toBeGreaterThanOrEqual(4);
    expect(decisionCoverageProblems(REVIEW_DECISIONS, REVIEW_KINDS, consequenceOf, DEFAULT_CONSEQUENCE)).toEqual([]);
    // 預設句本身沒被改掉（否則「非預設」的判準就落空）
    expect(consequenceOf("TASK_CONFIRM", "SKIP")).toBe(DEFAULT_CONSEQUENCE);
    expect(Object.keys(STATE_HELP.reviewDecision).sort()).toEqual([...REVIEW_DECISIONS].sort());
  });

  it("AT_PH_04_7_2 reviewDecision 每列的 next 含「依審核項種類而定」；任一列的 meaning、next 都不含任何一句後果文字（後果只住 execute/reviewHelp.ts）", () => {
    const sentences = new Set<string>();
    for (const kind of REVIEW_KINDS) for (const decision of REVIEW_DECISIONS) if (consequenceOf(kind, decision) !== DEFAULT_CONSEQUENCE) sentences.add(consequenceOf(kind, decision));
    expect(sentences.size, "防反空轉：後果句的種類數").toBeGreaterThanOrEqual(5);
    for (const [decision, row] of Object.entries<StateRow>(STATE_HELP.reviewDecision)) {
      expect(row.next, `${decision}.next`).toContain("依審核項種類而定");
      for (const sentence of sentences) {
        expect(row.meaning.includes(sentence), `${decision}.meaning 抄了後果句：${sentence}`).toBe(false);
        expect(row.next.includes(sentence), `${decision}.next 抄了後果句：${sentence}`).toBe(false);
      }
    }
  });

  it("AT_PH_04_7_E_1 decisionCoverageProblems 負控：所有種類都回預設句的決定被回報；每個決定都有非預設句回空；全部回預設句時回全部決定", () => {
    const table: Record<string, Record<string, string>> = { K1: { OK: "做甲。" }, K2: { OK: DEFAULT_CONSEQUENCE, NO: "做乙。" } };
    const consequence = (kind: string, decision: string) => table[kind]?.[decision] ?? DEFAULT_CONSEQUENCE;
    expect(decisionCoverageProblems(["OK", "NO", "FOO"], ["K1", "K2"], consequence, DEFAULT_CONSEQUENCE)).toEqual(["FOO"]);
    expect(decisionCoverageProblems(["OK", "NO"], ["K1", "K2"], consequence, DEFAULT_CONSEQUENCE)).toEqual([]);
    expect(decisionCoverageProblems(["OK", "NO", "FOO"], ["K1", "K2"], () => DEFAULT_CONSEQUENCE, DEFAULT_CONSEQUENCE)).toEqual(["OK", "NO", "FOO"]);
    expect(decisionCoverageProblems([], ["K1"], consequence, DEFAULT_CONSEQUENCE)).toEqual([]);
  });
});
