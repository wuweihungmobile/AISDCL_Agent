import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import {
  EMPTY_WATCH_SOURCE_FORM,
  REGISTRY_SYNC_MESSAGES,
  RESEARCH_REGISTRY_REASONS,
  checkWatchUrl,
  fetchMaxWarning,
  registrySyncErrorMessage,
  registrySyncOutcomeMessage,
  registrySyncText,
  slugSuggestion,
  toWatchSourceRequest,
  watchExpandText,
  watchSourceCountText,
  watchSourceFormErrors,
  watchSourceWriteErrorText,
  type WatchSourceForm,
} from "@/lib/domain/researchRegistry";
import { REGISTRY_STATUS, WATCH_SOURCES_17 } from "@/tests/fixtures/research/registry";

/**
 * 研究來源單一化的前端純函式（TCS-ResearchRegistry-20261110 AT-965-8-1、AT-965-8-5 文案部分、AT-965-9-4 reason 三處相等）。
 * 判定指令：npx vitest run lib/domain/researchRegistry.test.ts
 */
const FIXTURE_DIR = path.join(process.cwd(), "tests", "fixtures", "research");
const APPENDIX_D_SHA256 = "25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89";

const valid = (over: Partial<WatchSourceForm> = {}): WatchSourceForm => ({
  slug: "my-blog",
  url: "https://example.org/blog",
  kind: "blog",
  layer: "INDUSTRY",
  extract: "逐字保留文章",
  expandMode: "",
  expandPrefix: "",
  expandMax: "",
  ...over,
});

describe("AT_965_8_1 checkWatchUrl 原樣判定：逐列等於根層附錄 D 的 CON 欄", () => {
  const bytes = readFileSync(path.join(FIXTURE_DIR, "appendix-d.txt"));

  it("AT_965_8_1 附錄 D 複本的 sha256 先對（不符即紅）；表非空", () => {
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(APPENDIX_D_SHA256);
    const rows = bytes
      .toString("utf-8")
      .split("\n")
      .filter((line) => line !== "");
    expect(rows.length).toBeGreaterThanOrEqual(40);
  });

  it("AT_965_8_1 逐列：CON=T 收、CON=F 拒（含大寫 host、顯式 :443、IP 字面、localhost、xn--、非 ASCII、#、空白）；拒收訊息非空；原樣、不改寫", () => {
    const rows = bytes
      .toString("utf-8")
      .split("\n")
      .filter((line) => line !== "")
      .map((line) => line.split("\t"));
    let accepted = 0;
    let rejected = 0;
    for (const [url, , con] of rows) {
      expect(con === "T" || con === "F", `附錄 D 欄位形狀：${url}`).toBe(true);
      const result = checkWatchUrl(url);
      if (con === "T") {
        expect(result, `CON=T 應收：${url}`).toBeNull();
        accepted += 1;
      } else {
        expect(typeof result, `CON=F 應拒：${url}`).toBe("string");
        expect((result ?? "").length).toBeGreaterThan(0);
        rejected += 1;
      }
    }
    expect(accepted).toBeGreaterThan(10);
    expect(rejected).toBeGreaterThan(10);
  });

  it("AT_965_8_1 大寫 host 與顯式 :443 拒絕且訊息指示使用者自行改寫（不自動改寫、輸入不被改動）", () => {
    const upper = "https://EXAMPLE.ORG/x";
    const port = "https://example.org:443/x";
    expect(checkWatchUrl(upper)).toMatch(/自行/);
    expect(checkWatchUrl(port)).toMatch(/自行/);
    // 純函式沒有任何副作用，輸入字串不變；表單轉請求時網址也原樣送出
    expect(toWatchSourceRequest(valid({ url: "https://example.org/Blog?Q=1" })).url).toBe("https://example.org/Blog?Q=1");
  });

  it("AT_965_8_1 長度：500 字元通過、501 字元被拒", () => {
    const base = "https://x.com/";
    expect(checkWatchUrl(base + "a".repeat(500 - base.length))).toBeNull();
    expect(checkWatchUrl(base + "a".repeat(501 - base.length))).not.toBeNull();
  });
});

describe("AT_965_8_1 watchSourceFormErrors 與 toWatchSourceRequest", () => {
  it("AT_965_8_1 合法表單回空物件；空白預設表單逐欄回第一則錯誤（slug、url、extract）", () => {
    expect(watchSourceFormErrors(valid())).toEqual({});
    const empty = watchSourceFormErrors(EMPTY_WATCH_SOURCE_FORM);
    expect(Object.keys(empty).sort()).toEqual(["extract", "slug", "url"]);
    for (const message of Object.values(empty)) expect(typeof message).toBe("string");
  });

  it("AT_965_8_1 slug：大寫、底線、33 字、連字號開頭一律拒；32 字通過；小寫建議不改使用者輸入", () => {
    for (const bad of ["My-Blog", "my_blog", "a".repeat(33), "-abc", ""]) expect(watchSourceFormErrors(valid({ slug: bad })).slug, bad).toBeDefined();
    expect(watchSourceFormErrors(valid({ slug: "a".repeat(32) })).slug).toBeUndefined();
    expect(slugSuggestion("My-Blog")).toBe("my-blog");
    expect(slugSuggestion("my-blog")).toBeNull();
    expect(slugSuggestion("My_Blog")).toBeNull(); // 小寫化後仍不合法就不給建議
    const form = valid({ slug: "My-Blog" });
    watchSourceFormErrors(form);
    expect(form.slug, "驗證不改輸入").toBe("My-Blog");
  });

  it("AT_965_8_1 kind、layer 須在列舉內；extract 1～200 字、無控制字元", () => {
    expect(watchSourceFormErrors(valid({ kind: "rss" })).kind).toBeDefined();
    expect(watchSourceFormErrors(valid({ layer: "OTHER" })).layer).toBeDefined();
    expect(watchSourceFormErrors(valid({ extract: "" })).extract).toBeDefined();
    expect(watchSourceFormErrors(valid({ extract: "a".repeat(201) })).extract).toBeDefined();
    expect(watchSourceFormErrors(valid({ extract: "a".repeat(200) })).extract).toBeUndefined();
    expect(watchSourceFormErrors(valid({ extract: "含\u0007控制字元" })).extract).toBeDefined();
  });

  it("AT_965_8_1 expand 三欄「全空或全填」：缺一或缺二報錯；全填時 mode、prefix、max 逐項驗", () => {
    expect(watchSourceFormErrors(valid({ expandMode: "links" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ expandMode: "links", expandPrefix: "/blog/" })).expand).toBeDefined();
    const full = { expandMode: "links", expandPrefix: "/blog/", expandMax: "3" };
    expect(watchSourceFormErrors(valid(full))).toEqual({});
    expect(watchSourceFormErrors(valid({ ...full, expandMode: "rss" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandPrefix: "blog/" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandPrefix: "/a b" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandPrefix: "/a?x" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandMax: "0" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandMax: "4" })).expand).toBeDefined();
    expect(watchSourceFormErrors(valid({ ...full, expandMax: "1.5" })).expand).toBeDefined();
  });

  it("AT_965_8_1 toWatchSourceRequest 的鍵集合恰 slug、url、kind、extract、layer、expand（無 addedBy）；expand 全空為 null、全填為物件且 max 為數字", () => {
    const plain = toWatchSourceRequest(valid());
    expect(Object.keys(plain).sort()).toEqual(["expand", "extract", "kind", "layer", "slug", "url"]);
    expect(plain.expand).toBeNull();
    const withExpand = toWatchSourceRequest(valid({ expandMode: "sitemap", expandPrefix: "/news/", expandMax: "2" }));
    expect(withExpand.expand).toEqual({ mode: "sitemap", prefix: "/news/", max: 2 });
    expect(Object.keys(withExpand).sort()).toEqual(["expand", "extract", "kind", "layer", "slug", "url"]);
  });
});

describe("AT_965_8_5 registrySyncText：四態文案（與元件共用）", () => {
  const text = (kind: Parameters<typeof REGISTRY_STATUS>[0]) => registrySyncText(REGISTRY_STATUS(kind));

  it("AT_965_8_5 synced＝已同步到自我進化；unsynced＝有變更尚未同步（從未同步另加「尚未同步過」）", () => {
    expect(text("synced")).toBe("已同步到自我進化");
    expect(text("unsynced")).toBe("有變更尚未同步");
    expect(text("unsynced-never")).toContain("有變更尚未同步");
    expect(text("unsynced-never")).toContain("尚未同步過");
    expect(text("unsynced")).not.toContain("尚未同步過");
  });

  it("AT_965_8_5 pending＝已送出，待自我進化入帳（主機巡邏會自動處理）並列送出時間；不出現「已同步」", () => {
    const pending = text("pending");
    expect(pending).toContain("已送出，待自我進化入帳（主機巡邏會自動處理）");
    expect(pending).toContain("2026-11-10T16:05:00+08:00");
    expect(pending).not.toContain("已同步");
  });

  it("AT_965_8_5 unknown＝量不到同步狀態加原因中文（四種 unknownCause）；不出現「已同步」", () => {
    expect(text("unknown-si_unavailable")).toBe("量不到同步狀態：自我進化目前讀不到");
    expect(text("unknown-scan_cap_exceeded")).toBe("量不到同步狀態：帳本太大掃不完");
    expect(text("unknown-bridge_unreachable")).toContain("引擎橋接服務");
    expect(text("unknown-bridge_timeout")).toContain("引擎橋接服務");
    for (const kind of ["unknown-si_unavailable", "unknown-scan_cap_exceeded", "unknown-bridge_unreachable", "unknown-bridge_timeout"] as const) {
      expect(text(kind)).toMatch(/^量不到同步狀態/);
      expect(text(kind)).not.toContain("已同步");
    }
  });
});

describe("AT_965_8_6 同步結果與錯誤文案（單一表 REGISTRY_SYNC_MESSAGES）", () => {
  const err = (status: number, reason: string, details?: Record<string, unknown>) => new ApiError({ status, message: "m", reason, details });

  it("AT_965_8_6 文案逐字：403／503 兩種／422／502／504（outcomeUnknown 真與假）", () => {
    expect(registrySyncErrorMessage(err(403, "si_write_forbidden")).text).toBe("此帳號不在自我進化寫入名單，未同步");
    expect(registrySyncErrorMessage(err(503, "si_write_disabled", { cause: "audit_key_unset" })).text).toBe("自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步");
    expect(registrySyncErrorMessage(err(503, "si_write_disabled", { cause: "bridge_token_unset" })).text).toBe("自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步");
    expect(registrySyncErrorMessage(err(503, "si_unavailable")).text).toBe("自我進化暫時讀不到，稍後再試");
    expect(registrySyncErrorMessage(err(422, "registry_too_large", { what: "registry_text" })).text).toBe("追蹤來源總量超過可同步上限，請停用部分來源後再同步");
    expect(registrySyncErrorMessage(err(422, "registry_too_large", { what: "audit_file" })).text).toBe("追蹤來源總量超過可同步上限，請停用部分來源後再同步");
    expect(registrySyncErrorMessage(err(502, "bridge_unreachable", { outcomeUnknown: false })).text).toBe("連不上引擎橋接服務，未同步");
    expect(registrySyncErrorMessage(err(504, "bridge_timeout")).text).toBe("連不上引擎橋接服務，未同步");
    expect(registrySyncErrorMessage(err(504, "bridge_timeout", { outcomeUnknown: true })).text).toBe("送出結果不明，稽核檔可能已落地，請先看狀態再決定是否重試");
    expect(registrySyncErrorMessage(err(502, "bridge_unreachable", { outcomeUnknown: true })).text).toContain("結果不明");
  });

  it("AT_965_8_6 重試鈕：除 403 與 registry_too_large 外皆可重試；成功結果不重試；unchanged／written 文案", () => {
    expect(registrySyncErrorMessage(err(403, "si_write_forbidden")).retry).toBe(false);
    expect(registrySyncErrorMessage(err(422, "registry_too_large")).retry).toBe(false);
    for (const e of [err(503, "si_write_disabled"), err(503, "si_unavailable"), err(502, "bridge_unreachable"), err(504, "bridge_timeout", { outcomeUnknown: true })]) {
      expect(registrySyncErrorMessage(e).retry).toBe(true);
    }
    expect(registrySyncOutcomeMessage("unchanged")).toEqual({ text: "已是最新，未重送", retry: false, tone: "ok" });
    const written = registrySyncOutcomeMessage("written");
    expect(written.text).toBe("已送出，待入帳");
    expect(written.text).not.toContain("已同步");
    expect(written.retry).toBe(false);
  });

  it("AT_965_8_6 沒有對映的錯誤退回通用訊息且可重試；文案表只有一份", () => {
    const generic = registrySyncErrorMessage(new Error("boom"));
    expect(generic.retry).toBe(true);
    expect(generic.tone).toBe("error");
    expect(Object.keys(REGISTRY_SYNC_MESSAGES).sort()).toEqual(["bridge", "disabled", "forbidden", "outcomeUnknown", "tooLarge", "unavailable", "unchanged", "written"]);
  });

  it("AT_965_8_3 新增失敗文案：host_not_allowed 指向上方網域清單；slug 已存在說明不重用", () => {
    expect(watchSourceWriteErrorText(err(422, "host_not_allowed", { host: "x.org" }))).toBe("這個網域還沒開放，請先在上方網域清單新增");
    expect(watchSourceWriteErrorText(err(409, "watch_source_exists", { slug: "a" }))).toContain("識別碼");
  });
});

describe("AT_965_8_2 清單輔助：啟用計數、展開設定、抓取上限警示", () => {
  it("AT_965_8_2 17 列種子：啟用 10／共 17；展開設定純文字；無展開為破折號", () => {
    const rows = WATCH_SOURCES_17();
    expect(rows).toHaveLength(17);
    expect(watchSourceCountText(rows)).toBe("啟用 10／共 17");
    expect(watchExpandText(null)).toBe("—");
    expect(watchExpandText({ mode: "links", prefix: "/engineering/", max: 3 })).toContain("/engineering/");
  });

  it("AT_965_8_2 上限 8 且啟用 10 ⇒ 警示（含數字 8）；上限 10 或 null ⇒ 不警示（null 時沒有任何數字上限字樣）", () => {
    expect(fetchMaxWarning(10, 8)).toBe("已超過自我進化每次抓取上限（8）");
    expect(fetchMaxWarning(10, 10)).toBeNull();
    expect(fetchMaxWarning(10, null)).toBeNull();
    expect(fetchMaxWarning(10, undefined)).toBeNull();
  });
});

describe("AT_965_9_4 RESEARCH_REGISTRY_REASONS 恰三值，且與 backend 常數、契約 §5A.5 三處相等", () => {
  it("AT_965_9_4 恰三值", () => {
    expect(Object.values(RESEARCH_REGISTRY_REASONS).sort()).toEqual(["host_not_allowed", "registry_too_large", "watch_source_exists"]);
  });

  it("AT_965_9_4 backend ErrorReasons 的 REGISTRY_ 常數字面逐字相等（靜態比對）", () => {
    const source = readFileSync(path.join(process.cwd(), "..", "backend", "src", "main", "java", "com", "aisdlc", "console", "domain", "exception", "ErrorReasons.java"), "utf-8");
    const found = [...source.matchAll(/String REGISTRY_\w+ = "([^"]+)";/g)].map((m) => m[1]).sort();
    expect(found).toEqual(Object.values(RESEARCH_REGISTRY_REASONS).sort());
  });

  it("AT_965_9_4 契約 API_Contract_ResearchToPRD 第 7a′ 列逐字含三個 reason", () => {
    const contract = readFileSync(path.join(process.cwd(), "..", "docs", "02_architecture", "API_Contract_ResearchToPRD.md"), "utf-8");
    const row = contract.split("\n").find((line) => line.includes("7a′"));
    expect(row, "契約 §0.2 找不到第 7a′ 列").toBeDefined();
    for (const reason of Object.values(RESEARCH_REGISTRY_REASONS)) expect(row, reason).toContain(reason);
  });
});
