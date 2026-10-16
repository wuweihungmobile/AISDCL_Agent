/**
 * rehype 外掛：程式碼區塊語法高亮（Prism／refractor ＋ 逐行 `code-line` 包裝）。
 * 是 rehype-prism-plus 2.0.2 預設匯出（all 語言版）的行為等價版，**只改一件事：逐行拆分的複雜度**。
 *
 * 為什麼存在（NFR-9.1-05）：上游對「每一行」都把整棵高亮樹重新過濾一遍（unist-util-filter），時間是 O(行數 × 節點數)。
 * 編輯器左欄的原始碼著色（@uiw/react-md-editor 的 TextArea/Markdown）把「整份」Markdown 當成**一個**程式碼區塊交給它：
 * 20KB 的文件約 1,070 行、4,300 個 token，單次貼入光這一步就占掉約 40～50ms（W7-FE 的瀏覽器 CPU profile 51ms；左欄著色完成時間 57～71ms → 18～24ms；見 docs/06_quality/rtm_backfill_W7FE.md）。
 * 這裡每個節點只走訪一次、依它涵蓋的行放進各行（單行節點整棵沿用、不複製）⇒ O(節點數 ＋ 輸出大小)。
 * 其餘（語言判定、meta 的 `{1,3-5}`／`showLineNumbers`、diff 的 deleted／inserted、結尾空行）逐項照上游。
 *
 * 接線：next.config.ts 的 turbopack.resolveAlias 把裸名稱 `rehype-prism-plus` 指到本檔。
 * 兩個匯入者（@uiw/react-markdown-preview 的預覽、@uiw/react-md-editor 的左欄著色）都是 `import rehypePrism from 'rehype-prism-plus'`，
 * 所以兩處一起生效；`rehype-prism-plus/common`、`/all`、`/generator` 等子路徑不受影響（測試拿 `/all` 當「上游」做逐位比對）。
 * 行為等價由 rehypePrismLinear.test.ts 釘住：同一輸入餵上游與本檔，比對 hast 結構（JSON）與 HTML 字串，全部逐位相等。
 *
 * 改寫自 rehype-prism-plus 2.0.2（MIT License，Copyright (c) 2021 Timothy；授權全文附在檔尾）。
 */
import parseNumericRange from "parse-numeric-range";
import { refractor } from "refractor/all";

type Point = { line: number; column: number };
type HastNode = {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
  data?: { meta?: string };
  position?: { start: Point; end: Point };
};

export type RehypePrismOptions = {
  /** true＝每個區塊都顯示行號；字串陣列＝只對這些語言顯示 */
  showLineNumbers?: boolean | string[];
  /** 遇到未註冊的語言不丟錯，維持未高亮（仍然包上 code-line） */
  ignoreMissing?: boolean;
  /** 沒標語言時套用的預設語言（須已註冊） */
  defaultLanguage?: string;
};

/** 節點的純文字（同 hast-util-to-string）。 */
function textOf(node: HastNode): string {
  if (!node.children) return node.value ?? "";
  let text = "";
  for (const child of node.children) text += textOf(child);
  return text;
}

/**
 * 標上每個節點所在的行（1 起算）：文字節點依換行拆成「一行一個」節點（換行留在前一段的結尾），元素的範圍＝它的子節點涵蓋的行。
 * 與上游逐項相同，包含「以換行結尾的文字會多出一個空文字節點落在下一行」——所以結尾帶換行的 token 在下一行也會出現一個空殼，
 * 這是輸出逐位相等的前提，不是失誤。
 */
function addPositions(nodes: HastNode[], cursor: { line: number }): HastNode[] {
  const out: HastNode[] = [];
  for (const node of nodes) {
    if (node.type === "text") {
      const parts = (node.value ?? "").split("\n");
      if (parts.length === 1) {
        node.position = { start: { line: cursor.line, column: 1 }, end: { line: cursor.line, column: 1 } };
        out.push(node);
      } else {
        parts.forEach((part, i) => {
          const line = cursor.line + i;
          out.push({ type: "text", value: i === parts.length - 1 ? part : `${part}\n`, position: { start: { line, column: 1 }, end: { line, column: 1 } } });
        });
      }
      cursor.line += parts.length - 1;
    } else if (Object.prototype.hasOwnProperty.call(node, "children")) {
      const start = cursor.line;
      node.children = addPositions(node.children ?? [], cursor);
      out.push(node);
      node.position = { start: { line: start, column: 1 }, end: { line: cursor.line, column: 1 } };
    } else {
      // 文字與元素以外的葉節點（refractor 的輸出裡沒有）：上游此處不標位置、之後讀位置時會丟 TypeError；這裡歸在當下那一行
      node.position = { start: { line: cursor.line, column: 1 }, end: { line: cursor.line, column: 1 } };
      out.push(node);
    }
  }
  return out;
}

/**
 * 把一個（已標好行的）節點依行拆開，逐行交給 put。語意＝上游對每一行做的
 * `filter(tree, n => n.position.start.line <= line && n.position.end.line >= line)`：
 * 該行只留涵蓋它的節點，元素的子孫在該行全被濾掉就連元素一起丟掉。
 * 單行節點（絕大多數 token）的所有後代都在同一行，整棵直接沿用；多行元素才逐行淺拷貝、只帶該行的子節點。
 */
function splitByLine(node: HastNode, put: (line: number, node: HastNode) => void): void {
  const { start, end } = node.position as { start: Point; end: Point };
  if (start.line === end.line || !node.children) {
    put(start.line, node);
    return;
  }
  const buckets = new Map<number, HastNode[]>();
  for (const child of node.children) {
    splitByLine(child, (line, piece) => {
      const bucket = buckets.get(line);
      if (bucket) bucket.push(piece);
      else buckets.set(line, [piece]);
    });
  }
  for (const line of [...buckets.keys()].sort((a, b) => a - b)) put(line, { ...node, children: buckets.get(line) });
}

/** meta 裡的 `{1,3-5}` → 要標 highlight-line 的行判斷（行號 1 起算）。 */
function linesToHighlight(meta: string): (index: number) => boolean {
  const joined = meta
    .split(",")
    .map((part) => part.trim())
    .join();
  const found = /{([\d,-]+)}/.exec(joined);
  if (!found) return () => false;
  const wanted = parseNumericRange(found[1]);
  return (index) => wanted.includes(index + 1);
}

function highlightBlock(code: HastNode, pre: HastNode, options: RehypePrismOptions): void {
  const meta = code.data?.meta || (code.properties?.metastring as string | undefined) || "";
  const properties = (code.properties ??= {});
  const rawClass = properties.className;
  const className = (rawClass ? (typeof rawClass === "boolean" ? [] : Array.isArray(rawClass) ? rawClass : [rawClass]) : []) as string[];
  properties.className = className;
  let language: string | null = null;
  for (const name of className) {
    if (name.slice(0, 9) === "language-") {
      language = name.slice(9).toLowerCase();
      break;
    }
  }
  if (!language && options.defaultLanguage) {
    language = options.defaultLanguage;
    className.push(`language-${language}`);
  }
  className.push("code-highlight");

  let result: HastNode = code;
  if (language) {
    try {
      const grammar = language.includes("diff-") ? language.split("-")[1] : language;
      result = refractor.highlight(textOf(code), grammar) as unknown as HastNode;
      const preProperties = (pre.properties ??= {});
      preProperties.className = ((preProperties.className as string[] | undefined) || []).concat(`language-${grammar}`);
    } catch (error) {
      if (!options.ignoreMissing || !/Unknown language/.test((error as Error).message)) throw error;
      result = code;
    }
  }

  result.children = addPositions(result.children ?? [], { line: 1 });
  const first = result.children[0];
  const last = result.children[result.children.length - 1];
  // 同上游：整個區塊的範圍也掛在 result 上（沒有語言時 result 就是 code 本身，這個 position 會留在輸出裡）
  result.position = first
    ? { start: { line: (first.position as { start: Point }).start.line, column: 0 }, end: { line: (last.position as { end: Point }).end.line, column: 0 } }
    : { start: { line: 0, column: 0 }, end: { line: 0, column: 0 } };
  const lineCount = result.position.end.line;

  // 每行收集到的子節點
  const perLine = new Map<number, HastNode[]>();
  for (const child of result.children) {
    splitByLine(child, (line, piece) => {
      const bucket = perLine.get(line);
      if (bucket) bucket.push(piece);
      else perLine.set(line, [piece]);
    });
  }

  const lowerMeta = meta.toLowerCase();
  const showNumbers =
    (lowerMeta.includes("showlinenumbers") || options.showLineNumbers === true || (typeof options.showLineNumbers === "object" && options.showLineNumbers.includes(language as string))) &&
    !["showlinenumbers=false", 'showlinenumbers="false"', "showlinenumbers={false}"].some((flag) => lowerMeta.includes(flag));
  const startNumber = /showLineNumbers=(\d+)/i.exec(meta);
  const firstLineNumber = startNumber ? Number(startNumber[1]) : 1;
  const isHighlighted = linesToHighlight(meta);
  const isDiff = language === "diff" || Boolean(language?.includes("diff-"));

  const lines: HastNode[] = [];
  for (let i = 0; i < lineCount; i += 1) {
    const classes = ["code-line"];
    const line: HastNode = { type: "element", tagName: "span", properties: { className: classes }, children: perLine.get(i + 1) ?? [] };
    if (showNumbers) {
      (line.properties as Record<string, unknown>).line = [(i + firstLineNumber).toString()];
      classes.push("line-number");
    }
    if (isHighlighted(i)) classes.push("highlight-line");
    if (isDiff) {
      const firstChar = textOf(line).substring(0, 1);
      if (firstChar === "-") classes.push("deleted");
      else if (firstChar === "+") classes.push("inserted");
    }
    lines.push(line);
  }
  // 以換行結尾的內容會多出一個空行：拿掉
  if (lines.length > 0 && textOf(lines[lines.length - 1]).trim() === "") lines.pop();
  code.children = lines;
}

function visit(node: HastNode, parent: HastNode | undefined, options: RehypePrismOptions): void {
  if (node.type === "element" && parent && parent.tagName === "pre" && node.tagName === "code") {
    highlightBlock(node, parent, options);
    return;
  }
  if (node.children) for (const child of node.children) visit(child, node, options);
}

export default function rehypePrismLinear(options: RehypePrismOptions = {}) {
  if (options.defaultLanguage && !refractor.registered(options.defaultLanguage)) {
    throw new Error(`The default language "${options.defaultLanguage}" is not registered with refractor.`);
  }
  return (tree: HastNode) => visit(tree, undefined, options);
}

/*
 * rehype-prism-plus 的授權（MIT License）：
 *
 * Copyright (c) 2021 Timothy
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
