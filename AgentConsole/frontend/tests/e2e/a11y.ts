import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

import { expect, type Page } from "@playwright/test";

/**
 * 真瀏覽器的無障礙掃描（axe-core；WCAG 2.0／2.1 A／AA，與 QA 報告 §11 DEF-AC-004／005 同一把尺）。
 *
 * jsdom 沒有版面與繪製，量不出 color-contrast、也看不出 label-content-name-mismatch 的可見文字，
 * 所以「色彩對比」「名稱含可見文字」「svg 替代文字」「list 結構」這幾類只能在真瀏覽器裡驗。
 * 這支輔助只給 mock spec 用（不依賴後端）：在情境走到畫面穩定後呼叫 expectNoA11yViolations(page)。
 */

const requireFromApp = createRequire(path.join(process.cwd(), "package.json"));
let axeSource: string | undefined;

/** QA 掃描用的規則集：WCAG 2.0／2.1 的 A 與 AA。 */
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

/** 不屬於本專案的節點：Next dev 模式的開發工具浮標（shadow DOM 的 <nextjs-portal>），production 沒有。 */
const EXCLUDE = ["nextjs-portal"];

export interface AxeFinding {
  id: string;
  impact: string | null;
  help: string;
  nodes: Array<{ target: string; html: string; summary: string }>;
}

/**
 * 掃描目前頁面；沒有違規時回空陣列。
 * 內容區是固定高度內捲動，視窗外的節點 axe 只會回 incomplete（outsideViewport）而不判違規——
 * 所以掃描當下把視窗拉高到整頁可見，掃完還原。
 * 掃的是「靜止狀態」：滑鼠移到角落（前一步點過的按鈕底下若還有游標，axe 量到的是 hover 色）、
 * 並要求減少動態（全站 CSS 在 prefers-reduced-motion 下把過場縮成 0.01ms；掃到一半的漸變色不是真實的色）。
 */
export async function axeViolations(page: Page): Promise<AxeFinding[]> {
  axeSource ??= readFileSync(requireFromApp.resolve("axe-core/axe.min.js"), "utf-8");
  const original = page.viewportSize();
  if (original) await page.setViewportSize({ width: original.width, height: Math.max(original.height, 2400) });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.mouse.move(0, 0);
  // 減少動態只縮短「之後才開始」的過場；剛點過的分頁、剛開的對話框正在跑的過場要等它跑完，否則量到的是漸變到一半的顏色。
  // 等不到也不擋：掃描照做，真的有對比問題會在結果裡現形（不會被這裡吞掉）。
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), undefined, { timeout: 5000 }).catch(() => undefined);
  try {
    await page.evaluate(axeSource);
    return await runAxe(page);
  } finally {
    await page.emulateMedia({ reducedMotion: null });
    if (original) await page.setViewportSize(original);
  }
}

async function runAxe(page: Page): Promise<AxeFinding[]> {
  return page.evaluate(
    async ({ tags, exclude }) => {
      const axe = (window as unknown as { axe: { run: (ctx: unknown, opts: unknown) => Promise<{ violations: AxeRaw[] }> } }).axe;
      interface AxeRaw {
        id: string;
        impact?: string | null;
        help: string;
        nodes: Array<{ target: unknown[]; html: string; failureSummary?: string }>;
      }
      const result = await axe.run({ include: [document], exclude: exclude.map((s) => [s]) }, { runOnly: { type: "tag", values: tags } });
      return result.violations.map((v) => ({
        id: v.id,
        impact: v.impact ?? null,
        help: v.help,
        nodes: v.nodes.map((n) => ({
          target: n.target.map(String).join(" "),
          html: n.html.slice(0, 160),
          summary: (n.failureSummary ?? "").replace(/\s+/g, " ").slice(0, 220),
        })),
      }));
    },
    { tags: WCAG_TAGS, exclude: EXCLUDE },
  );
}

/** 把違規整理成一段可讀的失敗訊息（每條規則列前 6 個節點）。 */
export function formatViolations(findings: AxeFinding[]): string {
  return findings
    .map((f) => {
      const head = `${f.id} [${f.impact ?? "?"}] ${f.help}：${f.nodes.length} 個節點`;
      const rows = f.nodes.slice(0, 6).map((n) => `    - ${n.target}\n      ${n.html}\n      ${n.summary}`);
      return [head, ...rows].join("\n");
    })
    .join("\n");
}

/** 斷言目前頁面沒有任何 WCAG 2.0／2.1 A／AA 違規；失敗時訊息列出規則與節點。 */
export async function expectNoA11yViolations(page: Page, label: string): Promise<void> {
  const findings = await axeViolations(page);
  expect(findings, `${label}：無障礙違規\n${formatViolations(findings)}`).toEqual([]);
}
