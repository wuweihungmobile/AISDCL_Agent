import { describe, expect, it } from "vitest";

import { ENGLISH_WHITELIST, codePointLength, forbiddenFindings, lintText, splitSentences, unlistedEnglishWords } from "./lint";

/**
 * 說明文字「白話」檢查的純函式鎖（TCS-PageHelp-20261027 R-PH-15、R-PH-16 的函式層；載具 HN，輪 1a）：
 *  - AT-PH-05-1-E-1：切句與 code point 長度的邊界（對應 AC-PH-05-1）；
 *  - AT-PH-05-2-2、AT-PH-05-2-E-1：英文詞白名單（31 詞，PRD §8.3）與偵測、負控（AC-PH-05-2）；
 *  - AT-PH-05-3-2：禁用字元各類與邊界（AC-PH-05-3；ID 形態先剔除，D-PH-10）；
 *  - AT-PH-05-6-1、AT-PH-05-6-E-1：PRD AC-PH-05-6 的負控樣本逐一餵 lintText，與合規樣本、選項（AC-PH-05-6）。
 * 判定指令：npx vitest run lib/help/lint.test.ts -t "<AT 底線形>"，例 -t "AT_PH_05_2_2"
 *
 * 樣本一律在執行期組出會觸發違規的形態；DEF 編號一律執行期組字串（缺陷帳本引用完整性鎖不得誤抓測試碼）。
 */

/** PRD §8.3 的白名單（單一出處；增詞必須改這裡，即走複審）。 */
const PRD_WHITELIST = [
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
] as const;

/** 執行期組出的 DEF 形態字串（不把 DEF 編號字面寫進 repo）。 */
const defId = (a: number, b: number): string => "DEF-" + `${a}-${b}`;

const hasKeyword = (messages: readonly string[], keyword: string): boolean => messages.some((m) => m.includes(keyword));

describe("AT_PH_05_1_E_1 切句與 code point 長度的邊界（R-PH-15）", () => {
  it("AT_PH_05_1_E_1 60 個字的句子通過、61 個不通過；60 個 U+20BB7（UTF-16 長度 120）通過——句長以 code point 計，不用 String.length", () => {
    const sixty = "字".repeat(60);
    expect(codePointLength(sixty)).toBe(60);
    expect(lintText(sixty)).toEqual([]);
    expect(hasKeyword(lintText("字".repeat(61)), "句長")).toBe(true);

    const astral = String.fromCodePoint(0x20bb7);
    expect(astral.repeat(60).length, "代理對的 UTF-16 長度是 code point 數的兩倍").toBe(120);
    expect(codePointLength(astral.repeat(60))).toBe(60);
    expect(lintText(astral.repeat(60))).toEqual([]);
    expect(hasKeyword(lintText(astral.repeat(61)), "句長")).toBe(true);
    // 組合附加符號各算 1（不做字素叢集）：e 加 U+0301 是兩個 code point
    expect(codePointLength("e\u0301")).toBe(2);
    expect(codePointLength("")).toBe(0);
  });

  it("AT_PH_05_1_E_1 切句：「。！？；」與換行是切分點，空段不產生空句；英文標點、頓號與間隔號不是切分點", () => {
    expect(splitSentences("甲。乙！丙？丁；戊")).toEqual(["甲", "乙", "丙", "丁", "戊"]);
    expect(splitSentences("甲\r\n乙\n丙")).toEqual(["甲", "乙", "丙"]);
    expect(splitSentences("甲。。乙")).toEqual(["甲", "乙"]);
    expect(splitSentences("甲。")).toEqual(["甲"]);
    expect(splitSentences("  甲　")).toEqual(["甲"]);
    expect(splitSentences("。 ！\n　\n")).toEqual([]);
    expect(splitSentences("")).toEqual([]);
    // 全形「；」也是切句點
    expect(splitSentences("A；B")).toEqual(["A", "B"]);
    // 英文句點、逗號、冒號、頓號、間隔號都不是切分點
    expect(splitSentences("A.B,C:D、E・F")).toHaveLength(1);
  });
});

describe("AT_PH_05_2_2 英文詞白名單與偵測（R-PH-15、R-PH-16）", () => {
  it("AT_PH_05_2_2 ENGLISH_WHITELIST 與 PRD §8.3 的 31 詞逐字相同（個數、無重複、集合相等）", () => {
    expect(PRD_WHITELIST).toHaveLength(31);
    expect(new Set(PRD_WHITELIST).size).toBe(31);
    expect(ENGLISH_WHITELIST).toHaveLength(31);
    expect([...ENGLISH_WHITELIST].sort()).toEqual([...PRD_WHITELIST].sort());
  });

  it("AT_PH_05_2_2 每個白名單詞（原樣、全大寫、全小寫）出現在句子裡都不被判成白名單外", () => {
    for (const word of PRD_WHITELIST) {
      for (const form of [word, word.toUpperCase(), word.toLowerCase()]) expect(unlistedEnglishWords(`這裡用到 ${form} 這個詞`), form).toEqual([]);
    }
  });

  it("AT_PH_05_2_2 整詞、不分大小寫；連字號與底線當分隔；數字相接取字母段；單一字母不算；全形字母與中文不算", () => {
    expect(unlistedEnglishWords("由 autoclaude 啟動 與 SIGNOFF")).toEqual([]);
    expect(unlistedEnglishWords("console-api 與 well_known")).toEqual(["well", "known"]);
    expect(unlistedEnglishWords("auto-claude")).toEqual(["auto", "claude"]);
    expect(unlistedEnglishWords("Level2 等級")).toEqual([]);
    expect(unlistedEnglishWords("第 A 步與 I 型")).toEqual([]);
    expect(unlistedEnglishWords("全形字母Ａ與中文不算")).toEqual([]);
    // 整詞比對：白名單詞的前綴或延伸都不放行
    expect(unlistedEnglishWords("Tokens")).toEqual(["Tokens"]);
    expect(unlistedEnglishWords("MyToken")).toEqual(["MyToken"]);
  });

  it("AT_PH_05_2_2 ID 形態先剔除：OBS-SI-001、PROP-SI-004 與執行期組出的 DEF 形態都不回詞；不完整的形態不被剔除", () => {
    expect(unlistedEnglishWords("OBS-SI-001")).toEqual([]);
    expect(unlistedEnglishWords("PROP-SI-004")).toEqual([]);
    expect(unlistedEnglishWords(defId(1, 2))).toEqual([]);
    expect(unlistedEnglishWords(defId(200, 481))).toEqual([]);
    expect(unlistedEnglishWords(`見 OBS-SI-001、PROP-SI-004 與 ${defId(3, 4)} 的紀錄`)).toEqual([]);
    // 沒有編號的殘形不算 ID 形態
    expect(unlistedEnglishWords("OBS-SI-")).toEqual(["OBS", "SI"]);
    // 缺陷編號的另一種寫法（字母段不是數字）也不是 ID 形態；一樣在執行期組字串
    expect(unlistedEnglishWords(["DEF", "AC", "003"].join("-"))).toEqual(["DEF", "AC"]);
  });
});

describe("AT_PH_05_2_E_1 英文詞負控（R-PH-15、R-PH-16）", () => {
  it("AT_PH_05_2_E_1 Foo、GitHub、Review & Approve、https、Users 各回非空；「由 Foo 啟動」回 Foo", () => {
    expect(unlistedEnglishWords("Foo")).toEqual(["Foo"]);
    expect(unlistedEnglishWords("GitHub")).toEqual(["GitHub"]);
    expect(unlistedEnglishWords("Review & Approve")).toEqual(["Review", "Approve"]);
    expect(unlistedEnglishWords("https")).toEqual(["https"]);
    expect(unlistedEnglishWords("Users")).toEqual(["Users"]);
    expect(unlistedEnglishWords("由 Foo 啟動")).toEqual(["Foo"]);
    expect(unlistedEnglishWords("Level 3 · Review & Approve")).toEqual(["Review", "Approve"]);
  });
});

describe("AT_PH_05_3_2 禁用字元各類與邊界（R-PH-15）", () => {
  it("AT_PH_05_3_2 emoji（Extended_Pictographic）回非空；箭頭與全形標點、間隔號回空", () => {
    for (const sample of ["完成 😀", "完成 ✅", "往返 ↔ 兩端", "產品™"]) expect(forbiddenFindings(sample), sample).not.toEqual([]);
    for (const sample of ["按 → 前往", "← ↑ ↓", "全形標點：「，。！？；（）」", "頓號、與・間隔號 · 都可以"]) expect(forbiddenFindings(sample), sample).toEqual([]);
  });

  it("AT_PH_05_3_2 色碼：# 後接至少 3 位十六進位字元回非空（#abcg 的 #abc 即命中），2 位與 1 位回空", () => {
    for (const sample of ["顏色 #abc123", "顏色 #abc", "第 #123 項", "顏色 #abcg"]) expect(forbiddenFindings(sample), sample).not.toEqual([]);
    expect(forbiddenFindings("顏色 #abc123")).toContain("#abc123");
    for (const sample of ["第 #12 項", "第 #1 項"]) expect(forbiddenFindings(sample), sample).toEqual([]);
  });

  it("AT_PH_05_3_2 Markdown 記號、HTML 標籤、://、磁碟機與家目錄路徑各回非空，並列出命中形態", () => {
    expect(forbiddenFindings("這是 **粗體**")).toContain("**");
    expect(forbiddenFindings("這是 `code`")).toContain("`");
    expect(forbiddenFindings("連結 [a](b)")).toContain("](");
    expect(forbiddenFindings("請看 <b>粗</b>")).toEqual(expect.arrayContaining(["<b>", "</b>"]));
    expect(forbiddenFindings("<script>alert(1)</script>")).toContain("<script>");
    expect(forbiddenFindings("網址 https://x.y")).toContain("://");
    expect(forbiddenFindings("a://b")).toContain("://");
    expect(forbiddenFindings("路徑 C:\\Users\\x").length).toBeGreaterThan(0);
    expect(forbiddenFindings("路徑 /Users/x").length).toBeGreaterThan(0);
    expect(forbiddenFindings("路徑 /home/x").length).toBeGreaterThan(0);
    // 不是標籤、不是路徑的良性寫法
    expect(forbiddenFindings("3 < 5 且 5 > 3")).toEqual([]);
    expect(forbiddenFindings("第 1 項與第 2 項")).toEqual([]);
  });

  it("AT_PH_05_3_2 連續半形數字：3 位以上回非空，2 位回空，全形數字不算", () => {
    expect(forbiddenFindings("共 1234 筆")).toContain("1234");
    expect(forbiddenFindings("共 123 筆")).toContain("123");
    expect(forbiddenFindings("共 12 筆")).toEqual([]);
    expect(forbiddenFindings("共 １２３４ 筆")).toEqual([]);
  });

  it("AT_PH_05_3_2 ID 形態先剔除：OBS-SI-001、PROP-SI-004 與執行期組出的 DEF 形態回空；沒被剔除的長數字仍回非空", () => {
    expect(forbiddenFindings("OBS-SI-001")).toEqual([]);
    expect(forbiddenFindings("PROP-SI-004")).toEqual([]);
    expect(forbiddenFindings(defId(1, 2))).toEqual([]);
    expect(forbiddenFindings(defId(200, 481))).toEqual([]);
    expect(forbiddenFindings(`見 OBS-SI-001 之後共 1234 筆`)).toEqual(["1234"]);
  });
});

describe("AT_PH_05_6_1 PRD AC-PH-05-6 的負控樣本逐一餵 lintText（R-PH-15）", () => {
  const NEGATIVE: ReadonlyArray<readonly [sample: string, keyword: string]> = [
    ["字".repeat(61), "句長"],
    ["這裡有 Foo 這個詞", "英文"],
    ["完成 😀", "字元"],
    ["顏色 #abc123", "字元"],
    ["顏色 #abc123", "英文"],
    ["這是 **粗體**", "字元"],
    ["這是 `標記`", "字元"],
    ["連結 [甲](乙)", "字元"],
    ["網址 a://b", "字元"],
    ["共 1234 筆", "字元"],
    ["共 123 筆", "字元"],
  ];

  it("AT_PH_05_6_1 61 字句子、白名單外英文詞、emoji、#abc123、Markdown 記號、://、4 位與 3 位數字各回非空，且訊息含對應類別關鍵字", () => {
    expect(NEGATIVE.length).toBeGreaterThanOrEqual(10);
    for (const [sample, keyword] of NEGATIVE) expect(hasKeyword(lintText(sample), keyword), `${sample} → ${keyword}`).toBe(true);
  });

  it("AT_PH_05_6_1 2 位數字回空（與 AT-PH-05-3-2 同界線）；訊息列出該英文詞與命中的字元形態", () => {
    expect(lintText("共 12 筆")).toEqual([]);
    expect(lintText("這裡有 Foo 這個詞").join("\n")).toContain("Foo");
    expect(lintText("這是 **粗體**").join("\n")).toContain("**");
  });
});

describe("AT_PH_05_6_E_1 合規樣本與選項（R-PH-15）", () => {
  it("AT_PH_05_6_E_1 合規樣本（白名單英文、ID 形態、全形標點、Level 3、OBS-SI-001）回空；恰 60 字的句子回空；空字串回空", () => {
    const compliant = [
      "把 Token 與 Agent 用在 Console 的 Run 與 Level",
      "見 OBS-SI-001 與 PROP-SI-004 的紀錄",
      `見 ${defId(1, 2)} 的紀錄`,
      "Level 3 是第三級。全形標點：「，。！？」都可以",
      "第 A 步與 I 型",
      "按 → 前往",
      "字".repeat(60),
    ];
    for (const sample of compliant) expect(lintText(sample), sample).toEqual([]);
    expect(lintText("")).toEqual([]);
    expect(lintText("   ")).toEqual([]);
  });

  it("AT_PH_05_6_E_1 maxSentences：3 句在上限 2 時回含「句數」的訊息，2 句與 3 句在各自上限內回空", () => {
    expect(hasKeyword(lintText("甲。乙。丙。", { maxSentences: 2 }), "句數")).toBe(true);
    expect(lintText("甲。乙。", { maxSentences: 2 })).toEqual([]);
    expect(lintText("甲。乙。丙。", { maxSentences: 3 })).toEqual([]);
    expect(lintText("甲。乙。丙。")).toEqual([]);
  });
});
