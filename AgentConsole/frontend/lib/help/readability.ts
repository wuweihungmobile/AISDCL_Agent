/**
 * 說明文案的「可讀性」機械檢查（純函式；TCS-ConsoleUxSortHelp-20261108 §3、R-UX-H1～H9；PRD §0.10 D-UX-2）。
 * 疊加在 lint.ts 之上、不改它：lint.ts 管每句 ≤ 60、英文白名單、禁用字元；這裡再收緊成國高中程度——每句 ≤ 40 個字、步驟結構、動作詞、
 * 術語首次解釋、行話與過時句、每頁必須提到的事實。每個函式回傳「違規的事實」，空陣列＝合規；不改文字、不吞例外、不碰 React。
 * 訊息關鍵字契約（測試只斷言關鍵字）：句長、結構、動作、釋義、術語、行話、過時、事實。
 * 欄位名與狀態名是畫面字樣的逐字引用，呼叫端不要把它們餵進來（術語與英文詞規則都不管它們）。
 */
import { codePointLength, splitSentences } from "./lint";
import { STATE_HELP } from "./states";
import type { HelpField, PageHelp } from "./types";

/** 每句的長度上限（code point；R-UX-H1；lint.ts 的 60 仍是外層界線）。 */
export const MAX_SENTENCE_LENGTH = 40;

/** 動作詞（R-UX-H3；子字串比對，是「步驟以動作開頭」的機械近似，真正把關靠人讀）。 */
export const ACTION_WORDS: readonly string[] = [
  "按",
  "點",
  "選",
  "輸入",
  "填",
  "勾",
  "打開",
  "開啟",
  "進入",
  "查看",
  "看",
  "切換",
  "確認",
  "核准",
  "退回",
  "拖",
  "搜尋",
  "篩選",
  "回到",
  "返回",
  "重試",
  "建立",
  "新建",
  "封存",
  "復原",
  "刪除",
  "上傳",
  "貼上",
  "等",
  "檢查",
  "比對",
  "複製",
  "下載",
  "儲存",
  "送出",
  "啟動",
  "暫停",
  "恢復",
  "取消",
  "展開",
  "收合",
  "改",
  "換",
  "找",
  "讀",
  "留意",
  "設定",
  "開始",
  "審批",
  "簽核",
  "匯入",
  "排序",
  "移到",
  "繼續",
  "登入",
  "離開",
  "重新整理",
];

/** 首次出現要緊接「（白話解釋）」的術語（R-UX-H5）。 */
export const MUST_EXPLAIN: readonly string[] = ["FSM", "SSE", "PRD", "BRD", "SDD", "Token", "signoff", "Bridge", "Playbook", "DAG", "Regex", "API", "Agent", "Engine", "AISDLC", "AutoClaude"];

/** 中文行話（R-UX-H6）。 */
export const JARGON_BANNED: readonly string[] = [
  "端點",
  "游標",
  "雜湊",
  "冪等",
  "序列化",
  "非同步",
  "輪詢",
  "反向代理",
  "資料表",
  "連線池",
  "快取",
  "握手",
  "封包",
  "行程",
  "執行緒",
  "白名單",
  "黑名單",
];

/** 內部實作語彙（R-UX-H7；英文詞不分大小寫比對）。 */
export const IMPLEMENTATION_WORDS: readonly string[] = ["JDBC", "Spring", "Flyway", "Controller", "endpoint", "schema", "SQL", "唯讀連線", "API 路徑", "/api/"];

/** 占位與過時句（R-UX-H8）。 */
export const STALE_PHRASES: readonly string[] = ["本步驟於後續階段提供", "目前開放前兩步", "後續階段", "之後的版本", "敬請期待", "待補", "TODO"];

/** 有可排序表或排序控制列的頁（R-UX-H9）：前五者是表頁、後二者是控制列頁。 */
export const SORTABLE_HELP_PAGES: readonly string[] = ["import", "issues", "self-improving", "sysadmin-backup", "research-workspace", "projects", "research"];

/** 表頁（表頭可點排序）與控制列頁（排序下拉）的分界。 */
export const SORTABLE_TABLE_PAGES: readonly string[] = ["import", "issues", "self-improving", "sysadmin-backup", "research-workspace"];

/** R-UX-H1：每句 ≤ 40 個 code point；回傳過長的句子本身。 */
export function longSentences(text: string): string[] {
  return splitSentences(text).filter((sentence) => codePointLength(sentence) > MAX_SENTENCE_LENGTH);
}

/** R-UX-H2：purpose 合計 2～3 句；steps 5～10 項、每項恰 1 句。 */
export function shapeProblems(page: Pick<PageHelp, "purpose" | "steps">): string[] {
  const out: string[] = [];
  const purposeSentences = page.purpose.flatMap(splitSentences).length;
  if (purposeSentences < 2 || purposeSentences > 3) out.push(`結構：purpose 合計 ${purposeSentences} 句，須 2～3 句`);
  if (page.steps.length < 5 || page.steps.length > 10) out.push(`結構：steps 有 ${page.steps.length} 步，須 5～10 步`);
  page.steps.forEach((step, i) => {
    const n = splitSentences(step).length;
    if (n !== 1) out.push(`結構：steps[${i}] 有 ${n} 句，須恰 1 句`);
  });
  return out;
}

/** R-UX-H3：步驟不以「這」「此」「系統」開頭，且含至少一個動作詞。 */
export function stepProblems(step: string): string[] {
  const out: string[] = [];
  const text = step.trim();
  if (/^(?:這|此|系統)/.test(text)) out.push(`動作：步驟不可以「這」「此」「系統」開頭：${text}`);
  if (!ACTION_WORDS.some((word) => text.includes(word))) out.push(`動作：步驟沒有任何動作詞：${text}`);
  return out;
}

/** R-UX-H4：`meaning` 去空白後 ≥ 10 個 code point。 */
export function fieldProblems(field: Pick<HelpField, "meaning">): string[] {
  const length = codePointLength(field.meaning.replace(/\s/g, ""));
  return length < 10 ? [`結構：欄位釋義只有 ${length} 個字，至少 10 個字`] : [];
}

const isAsciiTerm = (term: string): boolean => /^[A-Za-z]+$/.test(term);

/** 該術語在 corpus 中第一次出現的位置（ASCII 詞以前後非英文字母為界；中文與其他詞用子字串）；沒有回 -1。 */
function firstIndexOfTerm(corpus: string, term: string): number {
  if (!isAsciiTerm(term)) return corpus.indexOf(term);
  const match = new RegExp(`(?<![A-Za-z])${term}(?![A-Za-z])`).exec(corpus);
  return match === null ? -1 : match.index;
}

/** R-UX-H5：依畫面順序串接的語料中，MUST_EXPLAIN 詞第一次出現後要緊接「（」且括號內 ≥ 2 個字；之後出現免括號。 */
export function unexplainedTerms(corpus: string): string[] {
  const out: string[] = [];
  for (const term of MUST_EXPLAIN) {
    const at = firstIndexOfTerm(corpus, term);
    if (at < 0) continue;
    const rest = corpus.slice(at + term.length);
    const m = /^（([^）]*)）/.exec(rest);
    if (m === null) out.push(`釋義：術語「${term}」第一次出現後沒有緊接「（白話解釋）」`);
    else if (codePointLength(m[1].trim()) < 2) out.push(`釋義：術語「${term}」的括號解釋少於 2 個字`);
  }
  return out;
}

/** R-UX-H6～H8：行話、內部實作語彙、過時句。 */
export function bannedFindings(text: string): string[] {
  const out: string[] = [];
  for (const word of JARGON_BANNED) if (text.includes(word)) out.push(`行話：不可出現「${word}」`);
  const lower = text.toLowerCase();
  for (const word of IMPLEMENTATION_WORDS) if (lower.includes(word.toLowerCase())) out.push(`行話：不可出現內部實作語彙「${word}」`);
  for (const phrase of STALE_PHRASES) if (text.includes(phrase)) out.push(`過時：不可出現占位或過時句「${phrase}」`);
  return out;
}

/** 一頁的語料，依畫面順序串接：purpose → steps → 欄位 meaning 與 sourceNote → 狀態列 meaning 與 next（狀態列由 STATE_HELP 取；議題 legend 無列）。 */
export function pageCorpus(page: PageHelp): string {
  const parts: string[] = [...page.purpose, ...page.steps];
  for (const field of page.fields) {
    parts.push(field.meaning);
    if (field.sourceNote !== undefined) parts.push(field.sourceNote);
  }
  for (const group of page.states) {
    if ("legend" in group) continue;
    const rows = STATE_HELP[group.table] as Record<string, { meaning: string; next: string }>;
    for (const row of Object.values(rows)) parts.push(row.meaning, row.next);
  }
  return parts.join("\n");
}

/**
 * 事實規格（TCS §3.4）：`words` 每一項是一個詞，或「任選其一」的詞組（陣列）。
 *  - words：每項都要在頁面全文出現；
 *  - sentence：每項都要出現在同一句；
 *  - order：只看 steps，每項第一次出現的位置要嚴格遞增。
 */
export type PageFact = { id: string; label: string; kind: "words" | "sentence" | "order"; words: ReadonlyArray<string | readonly string[]> };

const alternatives = (word: string | readonly string[]): readonly string[] => (typeof word === "string" ? [word] : word);
const labelOf = (word: string | readonly string[]): string => alternatives(word).join("／");

/** 回報頁面缺哪些事實（含 `id` 與 `label`）；空陣列＝全部命中。 */
export function factProblems(page: PageHelp, facts: readonly PageFact[]): string[] {
  const out: string[] = [];
  const corpus = pageCorpus(page);
  const stepsText = page.steps.join("\n");
  for (const fact of facts) {
    let ok = true;
    if (fact.kind === "words") {
      ok = fact.words.every((word) => alternatives(word).some((alt) => corpus.includes(alt)));
    } else if (fact.kind === "sentence") {
      ok = splitSentences(corpus).some((sentence) => fact.words.every((word) => alternatives(word).some((alt) => sentence.includes(alt))));
    } else {
      let last = -1;
      for (const word of fact.words) {
        const positions = alternatives(word)
          .map((alt) => stepsText.indexOf(alt))
          .filter((i) => i >= 0);
        if (positions.length === 0) {
          ok = false;
          break;
        }
        const at = Math.min(...positions);
        if (at <= last) {
          ok = false;
          break;
        }
        last = at;
      }
    }
    if (!ok) out.push(`事實：${page.id} 缺 ${fact.id}（${fact.label}；詞組 ${fact.words.map(labelOf).join("＋")}）`);
  }
  return out;
}
