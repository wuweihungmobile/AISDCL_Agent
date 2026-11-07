import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { FlaskConical } from "lucide-react";
import { describe, expect, it } from "vitest";

import { STATE_SOURCES } from "@/components/domain/help/stateSources";
import { FLOW_PHASE_DERIVED, FLOW_PHASE_LABEL, FLOW_STATUS_LABEL, FLOW_STEP_LABEL, flowVocabularyLabel } from "@/lib/domain/research";
import { codePointLength, lintText, splitSentences } from "@/lib/help/lint";
import { HELP_PAGES, HELP_ROUTES, NO_STATE_PAGES, PENDING_HELP_PAGES, helpForPath } from "@/lib/help/registry";
import { STATE_HELP } from "@/lib/help/states";
import type { HelpId, PageHelp } from "@/lib/help/types";
import { DELIVERED_NAV_ROWS } from "@/tests/helpers/navDelivered";
import { NAV_REGISTRY, navHref, type NavEntry } from "./registry";

/**
 * 研發工作流的導覽與說明接入（TCS-ResearchToPRD-P0-20261102 FR-R2P-21；AC-960-18；PRD AC-R2P-21-1、21-2；⚖1、⚖4；W-R9）：
 * 側欄只多一個入口「研發工作流」（`research`，末尾、order 35、mobile 為 false），整條工作流以單一路由加 `?step=` 切換五步；說明登記表多兩條（research、research-workspace）與一張狀態表（researchFlow）。
 * 本檔 AT：AT_960_18_1（登記表一列）、AT_960_18_2（說明三道鎖）、AT_960_18_3（狀態詞表 researchFlow）、AT_960_18_E_1（檢查函式的負控）；
 * AT_960_18_4（真渲染的側欄）住 components/layout/ToolsRegion.test.tsx，AT_960_18_5（既有導覽整併測試只改預期值）住 nav-consolidation.test.ts。
 * 判定指令：npx vitest run lib/nav/research-nav.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();

const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);
const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
/** 登記表層級（不看可見性、角色）命中某路徑的項 id。 */
const hitsOf = (pathname: string, registry: ReadonlyArray<NavEntry> = NAV_REGISTRY) => ids(registry.filter((e) => e.match(pathname)));

// ── 登記表檢查函式（沿 registry.test.ts 的判準複本：該檔的函式沒有 export，匯入測試檔會把它的整組 describe 一併註冊進本檔）──────────────

const PROBES = [
  "/",
  "/projects",
  "/projects/p1/execute",
  "/projects/p1/monitor",
  "/execute",
  "/monitor",
  "/import",
  "/settings",
  "/self-improving",
  "/issues",
  "/sysadmin",
  "/research",
  "/research/abc",
];

function pageRoutes(): string[][] {
  const routes: string[][] = [];
  const walk = (dir: string, segments: string[]) => {
    for (const name of readdirSync(dir)) {
      const full = path.join(dir, name);
      if (statSync(full).isDirectory()) walk(full, /^\(.*\)$/.test(name) ? segments : [...segments, name]);
      else if (name === "page.tsx") routes.push(segments);
    }
  };
  walk(path.join(ROOT, "app"), []);
  return routes;
}

function routeExists(pathname: string, routes: string[][]): boolean {
  const concrete = pathname === "/" ? [] : pathname.split("/").filter((s, i) => !(i === 0 && s === ""));
  return routes.some((pattern) => pattern.length === concrete.length && pattern.every((seg, i) => (/^\[[^\]]+\]$/.test(seg) ? concrete[i] !== "" : seg === concrete[i])));
}

type Problem = { kind: "duplicate-id" | "duplicate-order" | "bad-order" | "mobile-overflow" | "bad-href" | "match-overlap"; detail: string };

function registryProblems(registry: ReadonlyArray<NavEntry>, pathProbes: ReadonlyArray<string>, routes: string[][]): Problem[] {
  const out: Problem[] = [];
  const seenIds = new Set<string>();
  const seenOrders = new Set<number>();
  for (const e of registry) {
    if (seenIds.has(e.id)) out.push({ kind: "duplicate-id", detail: e.id });
    seenIds.add(e.id);
    if (typeof e.order !== "number" || !Number.isFinite(e.order)) out.push({ kind: "bad-order", detail: `${e.id}：${String(e.order)}` });
    else {
      if (seenOrders.has(e.order)) out.push({ kind: "duplicate-order", detail: `${e.id}：${e.order}` });
      seenOrders.add(e.order);
    }
    const resolved = typeof e.href === "string" ? [e.href] : [e.href({ currentProjectId: null }), e.href({ currentProjectId: "p1" })];
    for (const href of resolved) {
      const pathname = href.split(/[?#]/)[0];
      if (!pathname.startsWith("/") || !routeExists(pathname, routes)) out.push({ kind: "bad-href", detail: `${e.id}：${href}` });
    }
  }
  if (registry.filter((e) => e.mobile === true).length > 6) out.push({ kind: "mobile-overflow", detail: "mobile 為 true 的項超過 6" });
  for (const probe of pathProbes) {
    const hits = registry.filter((e) => e.match(probe));
    if (hits.length > 1) out.push({ kind: "match-overlap", detail: `${probe} 被 ${ids(hits).join("、")} 同時命中` });
  }
  return out;
}

const ownPath = (e: NavEntry): string => navHref(e, { currentProjectId: "p1" }).split(/[?#]/)[0];

function ownPathProblems(registry: ReadonlyArray<NavEntry>): string[] {
  const out: string[] = [];
  for (const e of registry) {
    const own = ownPath(e);
    const hits = ids(registry.filter((x) => x.match(own)));
    if (hits.length !== 1 || hits[0] !== e.id) out.push(`${e.id} 的頁面 ${own} 被 ${hits.length === 0 ? "無項" : hits.join("、")} 認領`);
  }
  return out;
}

// ── AT_960_18_1：登記表恰多一列 ───────────────────────────────────────────────────────

describe("AT_960_18_1 登記表恰多一列 research（欄位逐值、唯一性、icon 互異、href 對應真路由、match 互斥）", () => {
  it("AT_960_18_1 第十列（陣列索引 9）逐欄：id research、label 研發工作流、icon FlaskConical、href /research、order 35、enabled 為 true、mobile 為 false、roles 缺；既有九列與 DELIVERED_NAV_ROWS 前綴逐項相等", () => {
    const row = NAV_REGISTRY[9];
    expect(row.id).toBe("research");
    expect(row.label).toBe("研發工作流");
    expect(row.icon).toBe(FlaskConical);
    expect(row.href).toBe("/research");
    expect(row.order).toBe(35);
    expect(row.enabled).toBe(true);
    expect(row.mobile).toBe(false);
    expect(row.roles, "roles 缺＝所有已登入角色").toBeUndefined();
    expect(NAV_REGISTRY.slice(0, 9).map((e) => [e.id, e.label, e.order, e.mobile, e.enabled, e.roles ?? null])).toEqual(DELIVERED_NAV_ROWS);
    expect(NAV_REGISTRY, "本期只多這一列").toHaveLength(10);
  });

  it("AT_960_18_1 唯一性與上限：id 與 order 各自唯一；mobile 為 true 的項數仍為 6（不超過 6）；icon 與其餘九個互異", () => {
    expect(new Set(ids(NAV_REGISTRY)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(NAV_REGISTRY.length);
    expect(NAV_REGISTRY.filter((e) => e.mobile)).toHaveLength(6);
    expect(NAV_REGISTRY.filter((e) => e.mobile).length).toBeLessThanOrEqual(6);
    const others = NAV_REGISTRY.filter((e) => e.id !== "research").map((e) => e.icon);
    expect(others).toHaveLength(9);
    expect(others, "與其餘九個 icon 互異").not.toContain(FlaskConical);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(NAV_REGISTRY.length);
  });

  it("AT_960_18_1 href 對應真路由與 match 互斥：app/research/page.tsx 存在；/research、/research/<id>、/projects/<id>/execute、/execute 四個代表路徑的命中集合依序為 research、research、execute、execute；/researchx 與 /research-x 無項命中；ownPathProblems 為空", () => {
    expect(existsSync(path.join(ROOT, "app", "research", "page.tsx")), "app/research/page.tsx").toBe(true);
    expect(existsSync(path.join(ROOT, "app", "research", "[researchId]", "page.tsx")), "app/research/[researchId]/page.tsx").toBe(true);
    expect([hitsOf("/research"), hitsOf("/research/abc"), hitsOf("/projects/p1/execute"), hitsOf("/execute")]).toEqual([["research"], ["research"], ["execute"], ["execute"]]);
    expect(hitsOf("/researchx")).toEqual([]);
    expect(hitsOf("/research-x")).toEqual([]);
    expect(hitsOf("/research/")).toEqual(["research"]);
    expect(byId("projects").match("/research"), "專案管理不吃掉 /research").toBe(false);
    expect(ownPathProblems(NAV_REGISTRY)).toEqual([]);
    expect(registryProblems(NAV_REGISTRY, PROBES, pageRoutes())).toEqual([]);
  });
});

// ── AT_960_18_E_1：檢查函式的負控 ────────────────────────────────────────────────────

describe("AT_960_18_E_1 登記表檢查函式對違規樣本回報", () => {
  it("AT_960_18_E_1 真登記表回空；research 列 mobile 為真、order 撞 40、match 命中 /execute 各自被抓，且各回報恰對應的一項", () => {
    const routes = pageRoutes();
    expect(registryProblems(NAV_REGISTRY, PROBES, routes)).toEqual([]);
    const withResearch = (patch: Partial<NavEntry>) => NAV_REGISTRY.map((e) => (e.id === "research" ? { ...e, ...patch } : e));
    const kinds = (registry: ReadonlyArray<NavEntry>) => registryProblems(registry, PROBES, routes).map((p) => p.kind);
    expect(kinds(withResearch({ mobile: true })), "mobile 為真使底部 Tab 超過 6").toEqual(["mobile-overflow"]);
    expect(kinds(withResearch({ order: 40 })), "order 與執行中心撞號").toEqual(["duplicate-order"]);
    expect(kinds(withResearch({ match: (pathname) => pathname === "/execute" || pathname.startsWith("/research") })), "match 命中 /execute").toEqual(["match-overlap"]);
    // 對照組：三種違規不會互相掩蓋——同時發生時三種各出現一次
    const all = withResearch({ mobile: true, order: 40, match: (pathname) => pathname === "/execute" || pathname.startsWith("/research") });
    expect([...new Set(kinds(all))].sort()).toEqual(["duplicate-order", "match-overlap", "mobile-overflow"]);
  });
});

// ── AT_960_18_2：說明三道鎖 ───────────────────────────────────────────────────────────

const written = (id: HelpId): PageHelp => HELP_PAGES[id] as PageHelp;

describe("AT_960_18_2 說明三道鎖：HELP_ROUTES、HELP_PAGES、頁檔雙向一致，PENDING 仍空，說明文字過 lint", () => {
  it("AT_960_18_2 路由鎖：兩條路由各解析到各自的說明 id（含 helpForPath 對具體路徑）；HELP_PAGES 由 20 項變 22 項、HELP_ROUTES 由 23 條變 25 條；導覽的 href 解得到說明 id", () => {
    expect(HELP_ROUTES["/research"]).toBe("research");
    expect(HELP_ROUTES["/research/[researchId]"]).toBe("research-workspace");
    expect(helpForPath("/research")).toBe("research");
    expect(helpForPath("/research/abc")).toBe("research-workspace");
    expect(helpForPath("/research/abc/extra")).toBeNull();
    expect(helpForPath("/researchx")).toBeNull();
    const idsToCheck: HelpId[] = ["research", "research-workspace"];
    for (const id of idsToCheck) expect(HELP_PAGES[id]?.id, `${id} 已寫入 HELP_PAGES`).toBe(id);
    expect(Object.keys(HELP_PAGES)).toHaveLength(22);
    expect(Object.keys(HELP_ROUTES)).toHaveLength(25);
    expect(helpForPath(navHref(byId("research"), { currentProjectId: null })), "導覽鎖：research 的 href 解得到說明 id").toBe("research");
  });

  it("AT_960_18_2 頁檔鎖與 pending：lib/help/research.ts、research-workspace.ts 存在且各恰匯出一個 PageHelp（id 等於檔名）；PENDING_HELP_PAGES 為空、PENDING_CEILING 為 0", async () => {
    for (const name of ["research", "research-workspace"]) {
      expect(existsSync(path.join(ROOT, "lib", "help", `${name}.ts`)), `lib/help/${name}.ts`).toBe(true);
      const mod = (await import(/* @vite-ignore */ `../help/${name}`)) as Record<string, { id?: string }>;
      expect(Object.keys(mod), `${name} 恰匯出一個值`).toHaveLength(1);
      expect(Object.values(mod)[0].id).toBe(name);
    }
    expect(PENDING_HELP_PAGES).toEqual([]);
    const ceiling = /const PENDING_CEILING = (\d+);/.exec(readFileSync(path.join(ROOT, "lib", "help", "registry.test.ts"), "utf-8"));
    expect(ceiling?.[1], "registry.test.ts 的 PENDING_CEILING 維持 0（兩頁直接寫實、不走 pending）").toBe("0");
  });

  it("AT_960_18_2 research-workspace 的 steps 欄寫明五步差異：五個步驟名各出現在至少一則步驟說明；研究專案清單頁 states 為空且登記在 NO_STATE_PAGES", () => {
    const workspace = written("research-workspace");
    expect(workspace.steps.length).toBeGreaterThanOrEqual(5);
    for (const [step, label] of Object.entries(FLOW_STEP_LABEL))
      expect(
        workspace.steps.some((text) => text.includes(`「${label}」`)),
        `steps 沒有寫到「${label}」（${step}）`,
      ).toBe(true);
    expect(workspace.states).toEqual([{ table: "researchFlow" }]);
    expect(NO_STATE_PAGES).not.toContain("research-workspace");
    expect(written("research").states).toEqual([]);
    expect(NO_STATE_PAGES).toContain("research");
    expect(written("research").title).toBe("研發工作流");
    expect(workspace.title).toBe("研究工作區");
  });

  it("AT_960_18_2 兩頁說明文字都通過 lint.ts 的白話規則：purpose 合計至多 3 句、steps 每項恰 1 句、欄位釋義至多 2 句、sourceNote 恰 1 句且不超過 30 字；句長、英文詞、禁用字元皆合規", () => {
    for (const page of [written("research"), written("research-workspace")]) {
      const sentences = page.purpose.flatMap(splitSentences);
      expect(sentences.length, `${page.id} purpose 句數`).toBeGreaterThanOrEqual(1);
      expect(sentences.length, `${page.id} purpose 句數`).toBeLessThanOrEqual(3);
      for (const text of page.purpose) expect(lintText(text), `${page.id} purpose：${text}`).toEqual([]);
      expect(page.steps.length).toBeGreaterThanOrEqual(2);
      expect(page.steps.length).toBeLessThanOrEqual(8);
      for (const text of page.steps) expect(lintText(text, { maxSentences: 1 }), `${page.id} step：${text}`).toEqual([]);
      for (const field of page.fields) {
        expect(lintText(field.meaning, { maxSentences: 2 }), `${page.id} 欄位「${field.name}」`).toEqual([]);
        if (field.sourceNote !== undefined) {
          expect(lintText(field.sourceNote, { maxSentences: 1 }), `${page.id} 欄位「${field.name}」的 sourceNote`).toEqual([]);
          expect(codePointLength(field.sourceNote)).toBeLessThanOrEqual(30);
        }
      }
      expect(new Set(page.fields.map((f) => f.name)).size, `${page.id} 欄位名互異`).toBe(page.fields.length);
    }
  });
});

// ── AT_960_18_3：researchFlow 狀態詞表 ─────────────────────────────────────────────────

/** 上游常數的鍵：flow_status 八個 DB 值加衍生的 PAUSED，加 flow_phase 十三個 DB 值與五個衍生相態。 */
const UPSTREAM_KEYS = [...Object.keys(FLOW_STATUS_LABEL), ...Object.keys(FLOW_PHASE_LABEL)];

describe("AT_960_18_3 狀態詞表 researchFlow：說明鍵、來源鍵與 flow_status／flow_phase 詞彙常數的鍵三者相等", () => {
  it("AT_960_18_3 三者集合相等（28 個：status 九、phase 十九，其中衍生值 BUILDING、HEALING、AWAITING_HUMAN、RELEASE_PENDING、DELIVERED 與 P1 的 BUILD_READY 標為衍生）", () => {
    const helpKeys = Object.keys(STATE_HELP.researchFlow);
    const sourceKeys = [...STATE_SOURCES.researchFlow.keys];
    expect([...helpKeys].sort()).toEqual([...UPSTREAM_KEYS].sort());
    expect([...sourceKeys].sort()).toEqual([...UPSTREAM_KEYS].sort());
    expect(helpKeys).toHaveLength(28);
    expect(Object.keys(FLOW_STATUS_LABEL)).toHaveLength(9);
    expect(Object.keys(FLOW_PHASE_LABEL).filter((k) => !(FLOW_PHASE_DERIVED as readonly string[]).includes(k))).toHaveLength(13);
    expect([...FLOW_PHASE_DERIVED].sort()).toEqual(["AWAITING_HUMAN", "BUILDING", "BUILD_READY", "DELIVERED", "HEALING", "RELEASE_PENDING"]);
    for (const key of FLOW_PHASE_DERIVED) expect(STATE_HELP.researchFlow[key].meaning, `${key} 的說明標明是衍生相態`).toContain("即時推算");
    expect(STATE_SOURCES.researchFlow.title.trim()).not.toBe("");
  });

  it("AT_960_18_3 名稱取自上游常數（labelOf 逐鍵等於 FLOW_STATUS_LABEL／FLOW_PHASE_LABEL；未登記的鍵顯示原值）；每列 meaning 與 next 為非空且過 lint（meaning 至多 2 句、next 恰 1 句）", () => {
    const labelOf = STATE_SOURCES.researchFlow.labelOf;
    expect(labelOf).toBeDefined();
    for (const key of UPSTREAM_KEYS) {
      const expected = (FLOW_STATUS_LABEL as Record<string, string | undefined>)[key] ?? (FLOW_PHASE_LABEL as Record<string, string | undefined>)[key];
      expect(typeof expected === "string" && expected !== "", `${key} 上游標籤`).toBe(true);
      expect(labelOf?.(key), key).toBe(expected);
      expect(flowVocabularyLabel(key), key).toBe(expected);
      const row = (STATE_HELP.researchFlow as Record<string, { meaning: string; next: string }>)[key];
      expect(row.meaning.trim(), `${key}.meaning`).not.toBe("");
      expect(row.next.trim(), `${key}.next`).not.toBe("");
      expect(lintText(row.meaning, { maxSentences: 2 }), `${key}.meaning`).toEqual([]);
      expect(lintText(row.next, { maxSentences: 1 }), `${key}.next`).toEqual([]);
    }
    expect(labelOf?.("__未登記的鍵__")).toBe("__未登記的鍵__");
  });

  it("AT_960_18_3 必備表清單同步：content.test.ts 的 REQUIRED_TABLE_IDS 由 18 張變 19 張、stateKeys.test.ts 的必備清單與 UPSTREAM 都新增 researchFlow（讀原始碼逐項核對）", () => {
    const requiredOf = (source: string): string[] => {
      const body = /const REQUIRED_TABLE_IDS = \[([\s\S]*?)\] as const/.exec(source)?.[1] ?? "";
      return [...body.matchAll(/"([A-Za-z]+)"/g)].map((m) => m[1]);
    };
    const content = readFileSync(path.join(ROOT, "lib", "help", "content.test.ts"), "utf-8");
    const stateKeys = readFileSync(path.join(ROOT, "components", "domain", "help", "stateKeys.test.ts"), "utf-8");
    for (const [name, source] of [
      ["content.test.ts", content],
      ["stateKeys.test.ts", stateKeys],
    ] as const) {
      const required = requiredOf(source);
      expect(required, `${name} 必備表清單`).toHaveLength(19);
      expect(required, `${name} 含 researchFlow`).toContain("researchFlow");
    }
    expect(stateKeys).toMatch(/researchFlow:\s*\{\s*keys:/);
  });
});

// ── AT_962_25_5：P2 不動導覽與詞彙 ───────────────────────────────────────────────────────

describe("AT_962_25_5 導覽與詞彙不動：登記表仍是 P1 的樣子，事件層新 kind 不入流程詞彙", () => {
  it("AT_962_25_5 登記表列數、research 列逐欄、mobile 為真恰 6；FLOW_STATUS／FLOW_PHASE 詞彙計數與 P1 相同（九＋十九）；HEALING_LOG_TRUNCATED、SPEC_CHANGE_FORBIDDEN 等事件層 kind 不在任何詞彙或衍生表", () => {
    expect(NAV_REGISTRY).toHaveLength(10);
    const research = byId("research");
    expect([research.label, research.href, research.order, research.mobile, research.enabled]).toEqual(["研發工作流", "/research", 35, false, true]);
    expect(NAV_REGISTRY.filter((e) => e.mobile === true)).toHaveLength(6);
    expect(Object.keys(FLOW_STATUS_LABEL)).toHaveLength(9);
    expect(Object.keys(FLOW_PHASE_LABEL)).toHaveLength(19);
    const vocabulary = [...Object.keys(FLOW_STATUS_LABEL), ...Object.keys(FLOW_PHASE_LABEL), ...Object.keys(FLOW_STEP_LABEL), ...FLOW_PHASE_DERIVED];
    for (const eventKind of ["HEALING_LOG_TRUNCATED", "SPEC_CHANGE_FORBIDDEN", "ESCALATED"]) {
      // ESCALATED 是 P0 就有的流程狀態值（flow_status）；其餘兩個是 P2 事件層 kind，不能混進流程詞彙
      expect(vocabulary.includes(eventKind), eventKind).toBe(eventKind === "ESCALATED");
    }
  });
});
