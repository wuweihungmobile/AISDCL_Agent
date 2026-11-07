import { render, screen, within } from "@testing-library/react";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ResearchFlowStatus, ResearchFlowStepId } from "@/lib/api/types";
import { FLOW_STEP_IDS, FLOW_STEP_LABEL, STEP_STATE_LABEL, deriveSteps } from "@/lib/domain/research";
import { contrastRatio, tokenHex } from "@/tests/helpers/tokens";
import { FlowStepper } from "./FlowStepper";

/**
 * 工作流五步列（TCS-ResearchToPRD-P0-20261102 AT-960-19-3；AC-R2P-01-1）：
 * 恆五項；序號小於游標為已完成、等於為進行中、大於為待做；BLOCKED／ESCALATED／FAILED 時進行中的那一項改標「受阻」；
 * 每項的可及名稱含狀態文字（不只靠顏色與圖示）；整個 `components/domain/research/**` 只有 `FlowStepper.tsx` 這一份五步列實作。
 * 判定指令：npx vitest run components/domain/research/FlowStepper.test.tsx -t AT_960_19_3
 */
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const ALL_STATUSES: readonly ResearchFlowStatus[] = ["IDLE", "RUNNING", "PAUSED", "WAITING_HUMAN", "BLOCKED", "ESCALATED", "FAILED", "COMPLETED", "CANCELLED"];
const BLOCKING: readonly ResearchFlowStatus[] = ["BLOCKED", "ESCALATED", "FAILED"];
const STATE_WORDS = Object.values(STEP_STATE_LABEL);

const stepAt = (k: number): ResearchFlowStepId => FLOW_STEP_IDS[k - 1];
const items = (): HTMLElement[] => screen.getAllByRole("listitem");

describe("AT_960_19_3 FlowStepper 恆五項，狀態與可及名稱含狀態文字", () => {
  it.each([1, 2, 3, 4, 5])("AT_960_19_3 游標在第 %i 步（非受阻）：恆有 5 項；序號小於它為已完成、等於為進行中、大於為待做；可及名稱＝「序號 名稱，狀態」且畫面上也印出狀態文字", (k) => {
    render(<FlowStepper steps={deriveSteps(stepAt(k), "IDLE")} />);
    const rows = items();
    expect(rows).toHaveLength(5);
    rows.forEach((row, i) => {
      const expected = i + 1 < k ? "DONE" : i + 1 === k ? "CURRENT" : "TODO";
      expect(row, `第 ${i + 1} 項的狀態`).toHaveAttribute("data-state", expected);
      const name = `${i + 1} ${FLOW_STEP_LABEL[FLOW_STEP_IDS[i]]}，${STEP_STATE_LABEL[expected]}`;
      expect(row).toHaveAccessibleName(name);
      expect(row, "狀態文字也印在畫面上，不只在可及名稱").toHaveTextContent(STEP_STATE_LABEL[expected]);
      expect(row).toHaveTextContent(FLOW_STEP_LABEL[FLOW_STEP_IDS[i]]);
    });
  });

  it.each(BLOCKING)("AT_960_19_3 flow_status 為 %s：只有第 k 項改標「受阻」（可及名稱含「受阻」），其餘項照舊；沒有任何一項同時是進行中", (status) => {
    for (const k of [1, 2, 3, 4, 5]) {
      const { unmount } = render(<FlowStepper steps={deriveSteps(stepAt(k), status)} />);
      const rows = items();
      expect(rows).toHaveLength(5);
      const states = rows.map((row) => row.getAttribute("data-state"));
      expect(states, `游標 ${k}、${status}`).toEqual(FLOW_STEP_IDS.map((_, i) => (i + 1 < k ? "DONE" : i + 1 === k ? "BLOCKED" : "TODO")));
      expect(rows[k - 1]).toHaveAccessibleName(`${k} ${FLOW_STEP_LABEL[stepAt(k)]}，受阻`);
      expect(rows[k - 1]).toHaveTextContent("受阻");
      expect(states).not.toContain("CURRENT");
      unmount();
    }
  });

  it("AT_960_19_3 窮舉：5 個游標 × 9 個 flow_status，每一項的可及名稱恰含四個狀態詞之一、畫面也印出同一個詞；受阻只出現在三種受阻狀態", () => {
    for (const k of [1, 2, 3, 4, 5]) {
      for (const status of ALL_STATUSES) {
        const { unmount } = render(<FlowStepper steps={deriveSteps(stepAt(k), status)} />);
        const rows = items();
        expect(rows).toHaveLength(5);
        for (const row of rows) {
          const label = row.getAttribute("aria-label") ?? "";
          const hits = STATE_WORDS.filter((word) => label.endsWith(`，${word}`));
          expect(hits, `游標 ${k}、${status}：「${label}」`).toHaveLength(1);
          expect(row, "畫面也印出同一個狀態詞").toHaveTextContent(hits[0]);
        }
        const blockedCount = rows.filter((row) => row.getAttribute("data-state") === "BLOCKED").length;
        expect(blockedCount, `游標 ${k}、${status}`).toBe(BLOCKING.includes(status) ? 1 : 0);
        unmount();
      }
    }
  });

  it("AT_960_19_3 步驟連結：hrefFor 回網址者是連結、回 null 者只顯示文字（不是連結）；selected 的那項標 aria-current=step", () => {
    render(<FlowStepper steps={deriveSteps("studio", "IDLE")} selected="studio" hrefFor={(id) => (FLOW_STEP_IDS.indexOf(id) <= 1 ? `/research/x?step=${id}` : null)} />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["/research/x?step=topic", "/research/x?step=studio"]);
    expect(links[1]).toHaveAttribute("aria-current", "step");
    expect(links[0]).not.toHaveAttribute("aria-current");
    for (const id of ["route", "build", "deliver"] as const) {
      const row = screen.getByTestId(`flow-step-${id}`);
      expect(within(row).queryByRole("link"), `${id} 超前，不是連結`).toBeNull();
      expect(row, "不可達的項仍然顯示文字與狀態").toHaveTextContent(`${FLOW_STEP_LABEL[id]}`);
    }
  });

  it("AT_960_19_3 selected 指在沒有連結的項上：標記落在該項自己的元素上，不是別項", () => {
    render(<FlowStepper steps={deriveSteps("topic", "IDLE")} selected="topic" />);
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    const current = screen.getByTestId("flow-step-topic").querySelector('[aria-current="step"]');
    expect(current).not.toBeNull();
    expect(document.querySelectorAll('[aria-current="step"]')).toHaveLength(1);
  });

  it("AT_960_19_3 迷你版（compact，清單列用）：仍是五項、可及名稱含狀態，名稱與狀態改為螢幕閱讀器專用文字，只印序號", () => {
    const { container } = render(<FlowStepper compact steps={deriveSteps("route", "IDLE")} label="RP-0003 的步驟" />);
    const list = screen.getByRole("list", { name: "RP-0003 的步驟" });
    expect(list).toHaveAttribute("data-compact", "true");
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(5);
    expect(rows[2]).toHaveAccessibleName("3 分流，進行中");
    expect(rows[0]).toHaveAccessibleName("1 研究，已完成");
    expect(rows[4]).toHaveAccessibleName("5 交付，待做");
    // 名稱與狀態文字只在 sr-only 的 span 內，可見的只有序號
    const hidden = container.querySelectorAll(".sr-only");
    expect(hidden).toHaveLength(5);
    expect(hidden[2]).toHaveTextContent("分流，進行中");
  });

  it("AT_960_19_3 預設與自訂的列表名稱", () => {
    const { rerender } = render(<FlowStepper steps={deriveSteps("topic", "IDLE")} />);
    expect(screen.getByRole("list", { name: "研發工作流步驟" })).toBeInTheDocument();
    rerender(<FlowStepper steps={deriveSteps("topic", "IDLE")} label="自訂名稱" />);
    expect(screen.getByRole("list", { name: "自訂名稱" })).toBeInTheDocument();
  });

  // 四種狀態的 chip 字色對比（WCAG AA 一般文字 4.5:1）：chip 只有進行中與受阻有自己的底，已完成與待做的字直接坐在頁面底色上。
  // 已完成曾用主色字（bg-base 上 4.22:1，真瀏覽器 axe 在 1440 的 /research/<id> 量到 4.21 而紅）；改用 primary-strong（6.02:1）。真頁面層級的把關在 tests/e2e/a11y.mock.spec.ts 的 axe 掃描。
  const CHIP_TEXT: ReadonlyArray<{ step: ResearchFlowStepId; status: ResearchFlowStatus; state: string; textClass: string; fg: string; bg: string }> = [
    { step: "studio", status: "IDLE", state: "DONE", textClass: "text-wg-primary-strong", fg: "color-primary-strong", bg: "color-bg-base" },
    { step: "studio", status: "IDLE", state: "CURRENT", textClass: "text-white", fg: "#FFFFFF", bg: "color-primary" },
    { step: "studio", status: "BLOCKED", state: "BLOCKED", textClass: "text-wg-accent", fg: "color-accent", bg: "color-draft-bg" },
    { step: "studio", status: "IDLE", state: "TODO", textClass: "text-wg-muted", fg: "color-text-muted", bg: "color-bg-base" },
  ];
  it.each(CHIP_TEXT)("AT_960_19_3 $state 的 chip：字色 class 是 $textClass，對它坐的底色對比 ≥ 4.5:1（設計 token 實際值；DONE 不得退回主色字）", ({ step, status, state, textClass, fg, bg }) => {
    render(<FlowStepper steps={deriveSteps(step, status)} />);
    const row = items().find((li) => li.getAttribute("data-state") === state);
    expect(row, `有一項是 ${state}`).toBeDefined();
    const chip = (row as HTMLElement).querySelector("span.inline-flex");
    expect(chip).not.toBeNull();
    const classes = (chip as HTMLElement).className.split(/\s+/);
    expect(classes).toContain(textClass);
    if (state === "DONE") expect(classes, "主色字坐在 bg-base 上只有 4.22:1").not.toContain("text-wg-primary");
    const fgHex = fg.startsWith("#") ? fg : tokenHex(fg);
    const bgHex = tokenHex(bg);
    expect(fgHex, `找不到前景 token ${fg}`).toBeDefined();
    expect(bgHex, `找不到底色 token ${bg}`).toBeDefined();
    expect(contrastRatio(fgHex as string, bgHex as string)).toBeGreaterThanOrEqual(4.5);
  });
});

// ── 單一實作掃描：components/domain/research/** 內只有 FlowStepper.tsx 這一份五步列實作 ─────────────────────

const DIR = path.join(process.cwd(), "components", "domain", "research");

/** 非測試的原始碼：檔名 → 內容。 */
function researchComponentSources(): Record<string, string> {
  return Object.fromEntries(
    readdirSync(DIR)
      .filter((name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name))
      .map((name) => [name, readFileSync(path.join(DIR, name), "utf-8")]),
  );
}

/**
 * 五步列的實作特徵：渲染步驟狀態文字（`STEP_STATE_LABEL`）、自己標 `flow-step-` 測試識別、或自己展開 `deriveSteps(...)` 的結果卻不交給 `<FlowStepper`。
 * 回傳違規描述；空陣列＝只有 FlowStepper.tsx 一份實作。
 */
function duplicateStepperProblems(sources: Record<string, string>): string[] {
  const problems: string[] = [];
  for (const [name, text] of Object.entries(sources)) {
    if (name === "FlowStepper.tsx") continue;
    if (text.includes("STEP_STATE_LABEL")) problems.push(`${name}：自己渲染步驟狀態文字（STEP_STATE_LABEL）`);
    if (text.includes("flow-step-")) problems.push(`${name}：自己標了 flow-step- 識別`);
    if (/deriveSteps\s*\(/.test(text) && !text.includes("<FlowStepper")) problems.push(`${name}：算了 deriveSteps 卻沒有交給 <FlowStepper`);
  }
  return problems;
}

describe("AT_960_19_3 全工作區只有一份五步列實作（單一檔案、各處共用）", () => {
  it("AT_960_19_3 掃描 components/domain/research/**：除 FlowStepper.tsx 外沒有任何檔案自己渲染五步列", () => {
    const sources = researchComponentSources();
    expect(Object.keys(sources), "FlowStepper.tsx 存在").toContain("FlowStepper.tsx");
    expect(duplicateStepperProblems(sources)).toEqual([]);
    // 兩個現有消費者（清單的迷你步驟列、工作區的五步列）都是 <FlowStepper
    for (const consumer of ["ResearchListView.tsx", "ResearchWorkspaceView.tsx"]) expect(sources[consumer], `${consumer} 用共用的 FlowStepper`).toContain("<FlowStepper");
    // 單一實作本身確實是那份（有狀態文字、有可及名稱）
    expect(sources["FlowStepper.tsx"]).toContain("STEP_STATE_LABEL");
    expect(sources["FlowStepper.tsx"]).toContain("aria-label");
  });

  it("AT_960_19_3 掃描器自證（負控）：自己渲染狀態文字、自己標 flow-step-、算 deriveSteps 卻不交給 FlowStepper，三種複製各被抓到", () => {
    const real = researchComponentSources();
    expect(duplicateStepperProblems({ ...real, "CopyA.tsx": "const t = STEP_STATE_LABEL[step.state];" })).toEqual(["CopyA.tsx：自己渲染步驟狀態文字（STEP_STATE_LABEL）"]);
    expect(duplicateStepperProblems({ ...real, "CopyB.tsx": "<li data-testid={`flow-step-${id}`} />" })).toEqual(["CopyB.tsx：自己標了 flow-step- 識別"]);
    expect(duplicateStepperProblems({ ...real, "CopyC.tsx": "const steps = deriveSteps(a, b); return steps.map(render);" })).toEqual(["CopyC.tsx：算了 deriveSteps 卻沒有交給 <FlowStepper"]);
    // 對照：把 deriveSteps 的結果交給 <FlowStepper 的檔案不算違規
    expect(duplicateStepperProblems({ ...real, "Okay.tsx": "<FlowStepper steps={deriveSteps(a, b)} />" })).toEqual([]);
  });
});

describe("AT_961_19_4 FlowStepper 的 route 與 build 步驟狀態：進行中、失敗阻擋、SCR 進行中標示（TCS-ResearchToPRD-P1-20261107）", () => {
  it("AT_961_19_4 route／ROUTING（RUNNING）：第 3 步為進行中、可及名稱含狀態；前兩步已完成、後兩步待做", () => {
    render(<FlowStepper steps={deriveSteps("route", "RUNNING")} />);
    const rows = items();
    expect(rows[2]).toHaveAttribute("data-state", "CURRENT");
    expect(rows[2]).toHaveAccessibleName("3 分流，進行中");
    expect(rows[0]).toHaveAttribute("data-state", "DONE");
    expect(rows[3]).toHaveAttribute("data-state", "TODO");
    expect(screen.queryByTestId("flow-scr-open")).toBeNull();
  });

  it("AT_961_19_4 route 失敗（FAILED）：第 3 步為受阻並顯示 blockedReason（flow_detail 的純文字，含 HTML 字元也不解析）", () => {
    render(<FlowStepper steps={deriveSteps("route", "FAILED")} blockedReason="GIT_SWITCH <b>x</b>" />);
    const rows = items();
    expect(rows[2]).toHaveAttribute("data-state", "BLOCKED");
    expect(rows[2]).toHaveAccessibleName("3 分流，受阻");
    const reason = within(rows[2]).getByTestId("flow-step-blocked-reason");
    expect(reason).toHaveTextContent("原因：GIT_SWITCH <b>x</b>");
    expect(reason.querySelector("b")).toBeNull();
    for (const i of [0, 1, 3, 4]) expect(within(rows[i]).queryByTestId("flow-step-blocked-reason")).toBeNull();
  });

  it("AT_961_19_4 route／ROUTED 完成：第 3 步已完成、第 4 步（build）為進行中；沒有 blockedReason 時不顯示原因", () => {
    render(<FlowStepper steps={deriveSteps("build", "IDLE")} blockedReason="不應顯示" />);
    const rows = items();
    expect(rows[2]).toHaveAttribute("data-state", "DONE");
    expect(rows[3]).toHaveAttribute("data-state", "CURRENT");
    expect(screen.queryByTestId("flow-step-blocked-reason")).toBeNull();
  });

  it("AT_961_19_4 SCR_OPEN：步驟列尾端標示「SCR 進行中」（文字加圖示，精簡版也有）；五步仍恆為五項狀態項", () => {
    render(<FlowStepper steps={deriveSteps("build", "IDLE")} scrOpen />);
    const marker = screen.getByTestId("flow-scr-open");
    expect(marker).toHaveTextContent("SCR 進行中");
    expect(marker).toHaveAccessibleName("SCR 進行中");
    expect(screen.getAllByTestId(/^flow-step-(topic|studio|route|build|deliver)$/)).toHaveLength(5);
  });
});
