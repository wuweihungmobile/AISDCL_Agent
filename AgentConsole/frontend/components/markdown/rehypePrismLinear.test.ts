import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

import { rehype } from "rehype";
import rehypePrismUpstream from "rehype-prism-plus/all";
import { describe, expect, it } from "vitest";

import nextConfig from "../../next.config";
import rehypePrismLinear, { type RehypePrismOptions } from "./rehypePrismLinear";

/**
 * rehypePrismLinear 與上游 rehype-prism-plus 2.0.2 的行為等價（NFR-9.1-05）。
 * 意圖：本檔只改「逐行拆分的複雜度」，輸出必須和上游一模一樣——同一輸入、同一選項，hast 結構（含每個節點的 position）與 HTML 字串逐位相等。
 * 上游那一側用 `rehype-prism-plus/all`（子路徑不受 next.config.ts 的別名影響；預設匯出與它是同一個實作）。
 * 上游升版若改了輸出，這裡會紅，提醒回頭檢視這份改寫（package.json 把上游釘在 2.0.2 就是為了這個）。
 */

type Plugin = typeof rehypePrismUpstream | typeof rehypePrismLinear;
/** unified 的泛型型別在這裡只會礙事（兩個外掛的節點型別不同、測試用的注入外掛也不是 Root 型別）：收成最小介面。 */
type Processor = {
  data: (key: string, value: unknown) => Processor;
  use: (plugin: unknown, ...options: unknown[]) => Processor;
  parse: (html: string) => unknown;
  runSync: (tree: unknown) => unknown;
  stringify: (tree: unknown) => string;
};
type TestNode = { tagName?: string; data?: unknown; children?: TestNode[] };

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const block = (lang: string | null, code: string, attrs = "") => `<pre><code${lang ? ` class="language-${lang}"` : ""}${attrs}>${esc(code)}</code></pre>`;

/** 解析 → 套外掛 → 回傳 hast（JSON）與 HTML。meta 以 data.meta 注入（預覽端的路徑：retrieveMeta 把 fence 的 meta 放在 data.meta）。 */
function run(plugin: Plugin, html: string, options?: RehypePrismOptions, dataMeta?: string) {
  const injectMeta = () => (tree: TestNode) => {
    if (!dataMeta) return;
    const walk = (node: TestNode) => {
      if (node.tagName === "code") node.data = { meta: dataMeta };
      for (const child of node.children ?? []) walk(child);
    };
    walk(tree);
  };
  const processor = (rehype() as unknown as Processor).data("settings", { fragment: true }).use(injectMeta).use(plugin, options);
  const tree = processor.runSync(processor.parse(html));
  return { json: JSON.stringify(tree), html: processor.stringify(tree) };
}

/** 同一輸入餵上游與本檔，兩種輸出都要逐位相等；回傳本檔的 HTML 供額外斷言。 */
function expectSame(html: string, options?: RehypePrismOptions, dataMeta?: string): string {
  const theirs = run(rehypePrismUpstream, html, options, dataMeta);
  const ours = run(rehypePrismLinear, html, options, dataMeta);
  expect(ours.html).toBe(theirs.html);
  expect(ours.json).toBe(theirs.json);
  return ours.html;
}

const PY = "def f(x):\n    return x * 2\n";
const TS = "export const answer: number = 42; // 註解\nfunction g<T>(a: T): T {\n  return a;\n}\n";
const SECTION = (i: number) =>
  `## 第 ${i} 節 設計說明\n\n這是一段說明文字，包含 **粗體**、*斜體*、\`行內程式碼\` 與 [連結](https://example.com/${i})。\n\n- [x] 已完成項目 ${i}\n- [ ] 待辦項目 ${i}\n\n| 欄位 | 說明 | 值 |\n|------|------|----|\n| a${i} | 範例 | ${i} |\n\n\`\`\`python\n${PY}\`\`\`\n\n`;
const DOC = (sections: number) => Array.from({ length: sections }, (_, i) => SECTION(i + 1)).join("");

describe("與上游逐位相等：編輯器左欄的真實形態（整份 Markdown 當成一個 language-markdown 區塊）", () => {
  it("1 節／5 節／60 節的文件（含表格、核取清單、巢狀程式碼 fence、中文）", () => {
    for (const sections of [1, 5, 60]) {
      const html = `<pre class="language-markdown w-md-editor-text-pre"><code class="language-markdown">${esc(DOC(sections))}\n</code></pre>`;
      const out = expectSame(html, { ignoreMissing: true });
      expect(out).toContain("code-line");
      expect(out).toContain("token");
    }
  });

  it("多行 token（跨行的 fence、表格、區塊引用）與「以換行結尾的 token 會在下一行留下空殼」這個上游細節都照樣保留", () => {
    const md = "> 引用第一行\n> 引用第二行\n\n```js\nconst a = `多行\n樣板`;\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n結尾";
    expectSame(`<pre><code class="language-markdown">${esc(md)}\n</code></pre>`, { ignoreMissing: true });
    expectSame(`<pre><code class="language-markdown">${esc(md)}</code></pre>`, { ignoreMissing: true });
  });
});

describe("與上游逐位相等：預覽端的程式碼區塊（各語言、各選項、各種邊角內容）", () => {
  it("各語言的區塊；未註冊的語言在 ignoreMissing 下維持未高亮（仍包 code-line），沒有語言的區塊也一樣", () => {
    const samples: Array<[string | null, string]> = [
      ["python", PY],
      ["ts", TS],
      ["typescript", TS],
      ["bash", 'echo "hi"\nls -la | grep foo # c\n'],
      ["json", '{\n  "a": [1, 2, {"b": null}],\n  "c": "字串"\n}\n'],
      ["css", "a:hover {\n  color: #fff;\n}\n/* 多行\n註解 */\n"],
      ["html", '<div class="a">\n  <span>x</span>\n</div>\n<!-- 註解\n多行 -->\n'],
      ["yaml", "a:\n  - b\n  - c: d\n"],
      ["sql", "SELECT *\nFROM t\nWHERE a = 'x';\n"],
      ["js", "const s = `第一行\n第二行 ${x}\n第三行`;\n"],
      ["python", 'doc = """\n三引號\n多行\n"""\nprint(doc)\n'],
      ["foobar", "未註冊的語言\n第二行\n"],
      [null, "沒有語言\n第二行\n"],
    ];
    for (const [lang, code] of samples) expectSame(block(lang, code), { ignoreMissing: true });
  });

  it("邊角內容：空、只有換行、沒有結尾換行、結尾多個換行、前導空行、CRLF、tab、極長單行、emoji 與 CJK", () => {
    const contents = ["", "\n", "\n\n\n", "x", "x\n", "x\n\n\n", "\n\nx\ny", "a\r\nb\r\nc", "\ta\n\t\tb", `${"長".repeat(5000)}\n短`, "😀 emoji\n中文與 English 混排\n"];
    for (const code of contents) {
      expectSame(block("python", code), { ignoreMissing: true });
      expectSame(block(null, code), { ignoreMissing: true });
    }
  });

  it("選項：showLineNumbers（true／只對指定語言）、defaultLanguage、ignoreMissing 關閉時的行為", () => {
    const html = block("ts", TS) + block("python", PY) + block(null, "plain\ntext\n");
    expectSame(html, { showLineNumbers: true, ignoreMissing: true });
    expectSame(html, { showLineNumbers: ["ts"], ignoreMissing: true });
    expectSame(html, { defaultLanguage: "javascript" });
    expectSame(html, { showLineNumbers: false, ignoreMissing: true });
  });

  it("meta：{1,3-5}、showLineNumbers、showLineNumbers=5、showLineNumbers=false、組合；兩種來源（data.meta 與 metastring 屬性）", () => {
    const code = Array.from({ length: 8 }, (_, i) => `line ${i + 1}`).join("\n") + "\n";
    for (const meta of ["{1,3-5}", "showLineNumbers", "showLineNumbers=5", "showLineNumbers=false", "{2} showLineNumbers=3", "{8-6,1}", "title=a.ts {1}", "{1, 3}"]) {
      expectSame(block("ts", code), { ignoreMissing: true }, meta);
      expectSame(block("ts", code, ` metastring="${meta}"`), { ignoreMissing: true });
    }
  });

  it("diff：+ 與 - 開頭的行標 inserted／deleted；diff-js 先取後半當語言", () => {
    const diff = "--- a\n+++ b\n@@ -1,2 +1,2 @@\n-舊的一行\n+新的一行\n 沒變\n";
    expectSame(block("diff", diff), { ignoreMissing: true });
    expectSame(block("diff-js", "-const a = 1;\n+const a = 2;\n"), { ignoreMissing: true });
  });

  it("只處理 pre 底下的 code：行內 code、其他元素不動；pre 的其他子節點（例如複製鈕）保留，pre 另外多一個 language-* 類別", () => {
    const html = `<p>行內 <code class="language-ts">const a = 1;</code> 不動</p><pre><code class="language-ts">${esc(TS)}</code><div class="copied" data-code="x">複製</div></pre><div><pre><code class="language-python">${esc(PY)}</code></pre></div>`;
    const out = expectSame(html, { ignoreMissing: true });
    expect(out).toContain('<code class="language-ts">const a = 1;</code>'); // 行內 code 原封不動
    expect(out).toContain('class="copied"');
    expect(out).toMatch(/<pre class="language-ts">/);
  });

  it("className 的各種既有形態（沒有、字串、陣列、含 hljs）都能接上", () => {
    for (const attrs of ['class="language-ts hljs"', 'class="hljs language-ts"', 'class="x language-ts y"', 'class="language-TS"']) {
      expectSame(`<pre><code ${attrs}>${esc(TS)}</code></pre>`, { ignoreMissing: true });
    }
  });

  it("錯誤行為一致：未註冊語言且沒開 ignoreMissing → 丟同樣的錯；defaultLanguage 未註冊 → 外掛建立時就丟同樣的錯", () => {
    const messageOf = (fn: () => unknown) => {
      try {
        fn();
      } catch (error) {
        return (error as Error).message;
      }
      return "（沒有丟錯）";
    };
    const unknown = block("foobar", "x\n");
    const theirs = messageOf(() => run(rehypePrismUpstream, unknown));
    expect(messageOf(() => run(rehypePrismLinear, unknown))).toBe(theirs);
    expect(theirs).toMatch(/Unknown language/);
    const noDefault = messageOf(() => run(rehypePrismUpstream, unknown, { defaultLanguage: "nope" }));
    expect(messageOf(() => run(rehypePrismLinear, unknown, { defaultLanguage: "nope" }))).toBe(noDefault);
    expect(noDefault).toMatch(/not registered/);
  });
});

describe("與上游逐位相等：隨機文件（固定種子，可重現）", () => {
  // mulberry32：固定種子的偽隨機，失敗時可用同一個種子重現
  function rng(seed: number) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const FRAGMENTS = [
    "const x = 1;",
    "// 註解",
    '"字串 with \\" quote"',
    "def f(x):",
    "    return x",
    '"""',
    "/* 多行",
    "   註解 */",
    "`樣板",
    "${x}`",
    "{",
    "}",
    '<div class="a">',
    "# 標題",
    "- 清單項目",
    "| a | b |",
    "|---|---|",
    "```",
    "```ts",
    "",
    "+ 新增的行",
    "- 刪除的行",
    "中文與 😀 emoji",
    "\tTab 縮排",
    "x".repeat(300),
  ];
  const LANGS = ["markdown", "ts", "python", "js", "css", "html", "diff", "bash", "json", null, "foobar"];
  it("300 份文件：語言、行數、結尾換行、meta 都隨機", () => {
    const rand = rng(20261016);
    for (let n = 0; n < 300; n += 1) {
      const lang = LANGS[Math.floor(rand() * LANGS.length)];
      const lineCount = Math.floor(rand() * 40);
      const lines = Array.from({ length: lineCount }, () => FRAGMENTS[Math.floor(rand() * FRAGMENTS.length)]);
      const code = lines.join("\n") + (rand() < 0.5 ? "\n" : "");
      const meta = rand() < 0.3 ? ["{1,3-5}", "showLineNumbers", "showLineNumbers=7 {2}"][Math.floor(rand() * 3)] : undefined;
      try {
        expectSame(block(lang, code), { ignoreMissing: true }, meta);
      } catch (error) {
        throw new Error(`第 ${n} 份不相等（lang=${lang}、meta=${meta}、${lineCount} 行）：${(error as Error).message.slice(0, 300)}`);
      }
    }
  });
});

describe("複雜度：行數放大 4 倍，時間只放大約 4 倍（上游約 17 倍）", () => {
  it("大區塊的耗時隨行數線性成長", () => {
    // 用 python：Prism 對它的斷詞是線性的；markdown 語法自己的斷詞就是二次方（refractor.highlight 4 倍行數約 16 倍時間），會把「逐行拆分」的訊號蓋掉
    const make = (pairs: number) => `<pre><code class="language-python">${esc(Array.from({ length: pairs }, (_, i) => `def f${i}(x):\n    return x * ${i}  # 註解`).join("\n"))}</code></pre>`;
    const best = (html: string) => {
      let min = Infinity;
      for (let i = 0; i < 5; i += 1) {
        const t = performance.now();
        run(rehypePrismLinear, html, { ignoreMissing: true });
        min = Math.min(min, performance.now() - t);
      }
      return min;
    };
    const small = make(1000); // 2,000 行
    const large = make(4000); // 8,000 行
    best(small); // 暖機
    const ratio = best(large) / best(small);
    // 線性實測 4.4～5.0（10 次），上游同一輸入 17；以 10 為界，雜訊吞得下、又分得開兩種形狀
    expect(ratio, `8,000 行 ÷ 2,000 行 的耗時比（線性≈4～5、二次方≈17）：${ratio.toFixed(1)}`).toBeLessThan(10);
  });
});

describe("接線：next.config.ts 的別名仍然有效，且沒有繞過它的匯入者", () => {
  const ROOT = process.cwd();

  it("turbopack.resolveAlias 把裸名稱 rehype-prism-plus 指到本檔（檔案存在）", () => {
    const target = nextConfig.turbopack?.resolveAlias?.["rehype-prism-plus"];
    expect(target).toBe("./components/markdown/rehypePrismLinear.ts");
    expect(existsSync(path.join(ROOT, target as string))).toBe(true);
  });

  /** 找出 @uiw 底下所有「ESM 入口」中匯入 rehype-prism-plus 的檔案與子路徑 */
  function importersUnder(dir: string, out: Array<{ file: string; specifier: string }> = []) {
    for (const name of readdirSync(dir)) {
      const full = path.join(dir, name);
      if (statSync(full).isDirectory()) {
        if (name === "node_modules" || name === "src" || name === "lib" || name === "dist") continue; // 只看 esm（打包器實際吃的那份）
        importersUnder(full, out);
      } else if (name.endsWith(".js")) {
        for (const m of readFileSync(full, "utf-8").matchAll(/from ['"](rehype-prism-plus[^'"]*)['"]/g)) out.push({ file: path.relative(ROOT, full).split(path.sep).join("/"), specifier: m[1] });
      }
    }
    return out;
  }

  it("兩個匯入者（預覽、左欄原始碼著色）都是 `import … from 'rehype-prism-plus'` 的裸名稱；子路徑版（/common）只出現在我們沒用的入口", () => {
    const found = ["react-markdown-preview", "react-md-editor"].flatMap((pkg) => importersUnder(path.join(ROOT, "node_modules/@uiw", pkg, "esm")));
    const bare = found.filter((f) => f.specifier === "rehype-prism-plus").map((f) => f.file);
    expect(bare.sort()).toEqual(["node_modules/@uiw/react-markdown-preview/esm/index.js", "node_modules/@uiw/react-md-editor/esm/components/TextArea/Markdown.js"]);
    // 子路徑版（common）若被我們採用就會繞過別名：我們的程式碼不得匯入 /common 或 /nohighlight 入口
    const sub = found.filter((f) => f.specifier !== "rehype-prism-plus").map((f) => f.file);
    expect(sub.every((f) => /common/.test(f))).toBe(true);
    const own = readFileSync(path.join(ROOT, "components/markdown/MarkdownEditorImpl.tsx"), "utf-8");
    expect(own).not.toMatch(/@uiw\/react-(md-editor|markdown-preview)\/(common|nohighlight)/);
  });

  it("兩個匯入者實際解析到的 rehype-prism-plus 是同一份、版本就是本檔拿來比對的 2.0.2（沒被巢狀安裝成別的版本，別名才不會悄悄換掉另一個版本的行為）", () => {
    const requireFrom = createRequire(import.meta.url);
    const resolvedFrom = (pkg: string) => requireFrom.resolve("rehype-prism-plus", { paths: [path.join(ROOT, "node_modules/@uiw", pkg)] });
    const versionOf = (entry: string): string => {
      for (let dir = path.dirname(entry); dir !== path.dirname(dir); dir = path.dirname(dir)) {
        const manifest = path.join(dir, "package.json");
        if (existsSync(manifest)) {
          const json = JSON.parse(readFileSync(manifest, "utf-8")) as { name?: string; version?: string };
          if (json.name === "rehype-prism-plus") return json.version ?? "";
        }
      }
      return "（找不到 package.json）";
    };
    const editor = resolvedFrom("react-md-editor");
    const preview = resolvedFrom("react-markdown-preview");
    expect(preview).toBe(editor);
    expect(versionOf(editor)).toBe("2.0.2");
  });
});
