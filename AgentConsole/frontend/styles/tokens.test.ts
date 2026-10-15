import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { contrastRatio, tokenHex } from "@/tests/helpers/tokens";

/**
 * 設計 token 的無障礙底線（W5 C-18；DEF-AC-004）：WCAG 2.1 AA 一般文字要 4.5:1。
 * 真正的頁面層級把關在 Playwright 的 axe 掃描（tests/e2e/a11y.ts）；這裡鎖的是 token 本身，
 * 讓有人改色碼時在單元測試就紅，而不是等到 E2E 才發現。
 */
const read = (file: string) => readFileSync(path.join(process.cwd(), file), "utf-8");
const hex = (name: string): string => {
  const value = tokenHex(name);
  if (!value) throw new Error(`找不到 token --${name}`);
  return value;
};

/** 淺色面的底色：頁面底、卡片、tertiary（側欄 active／輕量標籤）、草案底、告警底、skeleton。 */
const LIGHT_SURFACES = ["color-bg-base", "color-bg-surface", "color-tertiary", "color-draft-bg", "color-alert-bg", "color-skeleton"];

describe("次要文字色 --color-text-muted（DEF-AC-004）", () => {
  it.each([...LIGHT_SURFACES, "color-disabled-bg"])("在 %s 上對比 ≥ 4.5:1（QA 建議的 #6B7766 在 bg-base 只有 4.37、tertiary 3.96，所以不採用）", (surface) => {
    expect(contrastRatio(hex("color-text-muted"), hex(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it("設計稿原值 #7A8775 確實不過（這條測試證明改色有必要，不是憑空加深）", () => {
    expect(contrastRatio("#7A8775", hex("color-bg-surface"))).toBeLessThan(4.5);
    expect(contrastRatio("#6B7766", hex("color-bg-base"))).toBeLessThan(4.5);
  });

  it("原生 select 的下拉箭頭（data-URI 無法引用變數）與 --color-text-muted 同色", () => {
    const m = /select\.wg-sel\s*\{[^}]*stroke='%23([0-9A-Fa-f]{6})'/.exec(read("app/globals.css"));
    expect(m, "app/globals.css 找不到 select.wg-sel 的箭頭色").not.toBeNull();
    expect(`#${m![1].toUpperCase()}`).toBe(hex("color-text-muted"));
  });
});

describe("強調色 --color-accent 與錯誤色 --color-error 當文字時（DEF-AC-004）", () => {
  it.each(LIGHT_SURFACES)("accent 在 %s 上 ≥ 4.5:1", (surface) => {
    expect(contrastRatio(hex("color-accent"), hex(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(LIGHT_SURFACES)("error 在 %s 上 ≥ 4.5:1", (surface) => {
    expect(contrastRatio(hex("color-error"), hex(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it("accent 當底色（徽章、警示按鈕）時白字 ≥ 4.5:1；hover 用的 accent-strong 比 accent 更深（否則 hover 反而變亮）", () => {
    expect(contrastRatio("#FFFFFF", hex("color-accent"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio("#FFFFFF", hex("color-accent-strong"))).toBeGreaterThan(contrastRatio("#FFFFFF", hex("color-accent")));
  });

  it("設計稿原值 #E55B3C／#D35B58 確實不過", () => {
    expect(contrastRatio("#E55B3C", hex("color-bg-surface"))).toBeLessThan(4.5);
    expect(contrastRatio("#E55B3C", hex("color-draft-bg"))).toBeLessThan(4.5);
    expect(contrastRatio("#D35B58", hex("color-bg-surface"))).toBeLessThan(4.5);
  });
});

describe("其他文字色（DEF-AC-004）", () => {
  it.each(["color-bg-base", "color-bg-surface", "color-alert-bg", "color-draft-bg"])("淺底上的警示文字 --color-warning-text 在 %s 上 ≥ 4.5:1", (surface) => {
    expect(contrastRatio(hex("color-warning-text"), hex(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it("日誌等級 INFO 用的 primary-strong 在 bg-base 上 ≥ 4.5:1；主色本身不夠（所以放在 bg-base 上的文字不直接用主色）", () => {
    expect(contrastRatio(hex("color-primary-strong"), hex("color-bg-base"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(hex("color-primary"), hex("color-bg-base"))).toBeLessThan(4.5);
  });

  it("終端機深底上的強調與錯誤文字（terminal-accent／terminal-error）、一般文字、警示色 ≥ 4.5:1", () => {
    const bg = hex("color-terminal-bg");
    for (const name of ["color-terminal-accent", "color-terminal-error", "color-terminal-text", "color-warning"]) {
      expect(contrastRatio(hex(name), bg), name).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("主色 --color-primary 不動（圖表線色與焦點環的 E2E 斷言釘著 rgb(73, 132, 40)）；純白在主色上 ≥ 4.5:1，任何 alpha／opacity 的白都不過", () => {
    expect(hex("color-primary")).toBe("#498428");
    const primary = hex("color-primary");
    expect(contrastRatio("#FFFFFF", primary)).toBeGreaterThanOrEqual(4.5);
    // 90% 白疊在主色上（QA 掃到的 #EDF3E9）：4.03:1
    expect(contrastRatio("#EDF3E9", primary)).toBeLessThan(4.5);
  });
});

describe("程式碼語法高亮的顏色（styles/markdown.css；DEF-AC-004）", () => {
  it("每條 .hljs-* 規則用的色票，在程式碼底（bg-base）上都 ≥ 4.5:1", () => {
    const rules = [...read("styles/markdown.css").matchAll(/\.md-view \.hljs-[^{]+\{[^}]*color:\s*var\(--([a-z-]+)\)/g)];
    expect(rules.length, "markdown.css 應有 .hljs-* 上色規則").toBeGreaterThanOrEqual(8);
    for (const [, name] of rules) {
      expect(contrastRatio(hex(name), hex("color-bg-base")), `--${name}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("secondary-text（變數、參數的顏色）在 bg-base／白底上 ≥ 4.5:1；secondary 本色不夠（所以不直接拿來當文字）", () => {
    for (const surface of ["color-bg-base", "color-bg-surface"]) {
      expect(contrastRatio(hex("color-secondary-text"), hex(surface)), surface).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrastRatio(hex("color-secondary"), hex("color-bg-base"))).toBeLessThan(4.5);
  });
});

describe("覆寫機制：tokens.css 保持設計稿逐字，偏離只發生在 tokens.console.css", () => {
  it("tokens.css 的原值還在；覆寫值在 tokens.console.css；載入順序是 tokens.css 在前（同層，後者勝出）", () => {
    const original = read("styles/tokens.css");
    expect(original).toMatch(/--color-text-muted:\s+#7A8775;/);
    expect(original).toMatch(/--color-accent:\s+#E55B3C;/);
    expect(original).toMatch(/--color-error:\s+#D35B58;/);
    const console_ = read("styles/tokens.console.css");
    expect(console_).toMatch(/--color-text-muted:\s+#5F6B5A;/);
    expect(console_).toMatch(/--color-accent:\s+#B93F22;/);
    expect(console_).toMatch(/--color-error:\s+#B8433F;/);
    const css = read("app/globals.css");
    expect(css.indexOf('@import "../styles/tokens.css"')).toBeGreaterThan(-1);
    expect(css.indexOf('@import "../styles/tokens.console.css"')).toBeGreaterThan(css.indexOf('@import "../styles/tokens.css"'));
    // tests/helpers/tokens.ts 與瀏覽器一樣「後者勝出」
    expect([hex("color-text-muted"), hex("color-accent"), hex("color-error")]).toEqual(["#5F6B5A", "#B93F22", "#B8433F"]);
  });
});
