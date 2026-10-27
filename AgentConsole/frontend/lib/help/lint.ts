/**
 * 說明文字的「白話」機械檢查（純函式；TCS-PageHelp-20261027 D-PH-9、D-PH-10、C5；PRD §8.3、AC-PH-05-1～05-3、05-6）：
 * 切句、句長（以 code point 計）、英文詞白名單、禁用字元。只回「違規的事實」，不改文字、不吞例外。
 * 說明內容（lib/help/**）由 content.test.ts 逐筆餵進來，寫錯會在 `npx vitest run` 當場轉紅，不必等到真機。
 *
 * 取捨（PRD §8.3）：議題中心既有的英文偵測（lib/domain/issues.ts）是「黑名單」、只管狀態詞；本功能文字涵蓋全部頁面，
 * 黑名單擋不住任意英文，所以改採「預設拒絕＋白名單」；代價是新增英文詞要走複審（改 ENGLISH_WHITELIST 的同時改 lint.test.ts 的 PRD 對照表）。
 * 欄位名與狀態名是畫面字樣的逐字引用，不受英文詞限制——呼叫端不要把它們餵進來。
 */

/** 英文詞白名單 v1（PRD §8.3，31 詞）：整詞、不分大小寫；這些詞畫面本身就出現。 */
export const ENGLISH_WHITELIST: readonly string[] = [
  "ID",
  "API",
  "URL",
  "AI",
  "Token",
  "Agent",
  "PRD",
  "BRD",
  "SDD",
  "FSM",
  "AISDLC",
  "AutoClaude",
  "Console",
  "Engine",
  "Bridge",
  "Playbook",
  "Markdown",
  "PDF",
  "DOCX",
  "CSV",
  "JSON",
  "SSE",
  "DAG",
  "Regex",
  "CPU",
  "ADMIN",
  "OPERATOR",
  "VIEWER",
  "signoff",
  "Run",
  "Level",
];

const WHITELIST_LOWER: ReadonlySet<string> = new Set(ENGLISH_WHITELIST.map((word) => word.toLowerCase()));

/** 每句的長度上限（code point，不是 UTF-16 單元；PRD AC-PH-05-1）。 */
const MAX_SENTENCE_LENGTH = 60;

/**
 * 議題 ID 形態（D-PH-10；PRD AC-PH-05-2）：`OBS-SI-<數字>`、`PROP-SI-<數字>`、`DEF-<數字>-<數字>`。英文詞與連續數字的判斷都先把它們剔除，
 * 否則說明文字連引用一個真編號都違規。只剔除完整形態：殘形（沒有編號）不算。
 */
const ID_FORM = /\b(?:OBS-SI-\d+|PROP-SI-\d+|DEF-\d+-\d+)\b/g;

const stripIdForms = (text: string): string => text.replace(ID_FORM, " ");

/** 以「。！？；」與換行切句，去前後空白、丟空段。英文句點、逗號、冒號、頓號與間隔號不是切分點。 */
export function splitSentences(text: string): string[] {
  return text
    .split(/[。！？；\r\n]/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence !== "");
}

/** code point 數（代理對算 1、組合附加符號各算 1；不做字素叢集）。 */
export function codePointLength(text: string): number {
  return Array.from(text).length;
}

/** 先剔除 ID 形態，再取連續 ASCII 字母（長度 ≥ 2；底線、連字號、數字都是分隔）；不在白名單者原樣回傳（整詞、不分大小寫）。 */
export function unlistedEnglishWords(text: string): string[] {
  const words = stripIdForms(text).match(/[A-Za-z]{2,}/g) ?? [];
  return words.filter((word) => !WHITELIST_LOWER.has(word.toLowerCase()));
}

/** 逐類判定的樣式；命中的原值會被回傳（Markdown 記號與 `://` 另以子字串判）。 */
const FORBIDDEN_PATTERNS: readonly RegExp[] = [
  /\p{Extended_Pictographic}/gu, // emoji
  /#[0-9a-fA-F]{3,}/g, // 色碼：# 後接 ≥ 3 位十六進位字元
  /<\/?[A-Za-z][^<>]*>/g, // HTML 標籤
  /(?<![A-Za-z])[A-Za-z]:[\\/]/g, // 磁碟機路徑
  /\/(?:Users|home)\//g, // 家目錄路徑
  /[0-9]{3,}/g, // 連續 ≥ 3 位半形數字（全形數字不算）
];
const FORBIDDEN_TOKENS: readonly string[] = ["**", "`", "](", "://"];

/** 禁用字元與形態：emoji、色碼、Markdown 記號、HTML 標籤、`://`、磁碟機或家目錄路徑、連續 ≥ 3 位數字（先剔除 ID 形態）。回原始命中值，空陣列＝合規。 */
export function forbiddenFindings(text: string): string[] {
  const body = stripIdForms(text);
  const found: string[] = [];
  for (const pattern of FORBIDDEN_PATTERNS) found.push(...(body.match(pattern) ?? []));
  for (const token of FORBIDDEN_TOKENS) if (body.includes(token)) found.push(token);
  return found;
}

/**
 * 綜合檢查：每句 ≤ 60 code point、可選的句數上限、英文詞、禁用字元；空陣列＝合規。
 * 訊息關鍵字契約（D-PH-9；測試只斷言關鍵字）：句長違規含「句長」、句數違規含「句數」、英文詞違規含「英文」並列出該詞、字元違規含「字元」並列出命中形態。
 */
export function lintText(text: string, opts: { maxSentences?: number } = {}): string[] {
  const problems: string[] = [];
  const sentences = splitSentences(text);
  for (const sentence of sentences) {
    const length = codePointLength(sentence);
    if (length > MAX_SENTENCE_LENGTH) problems.push(`句長 ${length} 超過 ${MAX_SENTENCE_LENGTH} 個字：${sentence}`);
  }
  if (opts.maxSentences !== undefined && sentences.length > opts.maxSentences) problems.push(`句數 ${sentences.length} 超過 ${opts.maxSentences} 句`);
  const words = unlistedEnglishWords(text);
  if (words.length > 0) problems.push(`英文詞不在白名單：${[...new Set(words)].join("、")}`);
  const findings = forbiddenFindings(text);
  if (findings.length > 0) problems.push(`含不允許的字元：${[...new Set(findings)].join("、")}`);
  return problems;
}
