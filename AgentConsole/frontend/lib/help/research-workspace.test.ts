import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { READONLY_TITLE, ROUTE_DISABLED_TEXT } from "@/lib/domain/research";
import { lintText } from "./lint";
import { HELP_PAGES, PENDING_HELP_PAGES } from "./registry";
import { researchWorkspace } from "./research-workspace";

/**
 * 研究工作區說明的 P1 寫實內容（TCS-ResearchToPRD-P1-20261107 AT-961-19-2、AT-961-16-5 的文案登記面）：
 * 第 3、4 步說明寫實並過 lint；說明三道鎖與計數不變（由既有 registry.test.ts、content.test.ts 守，本檔不複寫）；停用文案的單一登記處逐字等於 IFACE §8.3。
 */
const FIELD = (name: string) => researchWorkspace.fields.find((f) => f.name === name);
const stepText = (n: number) => researchWorkspace.steps[n - 1];
/** 第 N 步的說明：該步的步驟句，加上登記在同一頁、專屬於該步的欄位釋義。 */
const route3Text = () => [stepText(3), ...["分流精靈", "軌道 A", "軌道 B", "預演", "確認執行", "建立 GitHub 遠端", "重試失敗步驟"].map((n) => `${n}：${FIELD(n)?.meaning ?? ""}`)].join("\n");

describe("AT_961_19_2 研究工作區說明：第 3、4 步寫實", () => {
  it("AT_961_19_2 第 3 步說明含：分流兩軌的差異、OPERATOR 可預演、僅 ADMIN 可確認、預演零副作用、軌道 B 的權杖不落地", () => {
    const text = route3Text();
    expect(text).toContain("軌道 A");
    expect(text).toContain("軌道 B");
    expect(stepText(3)).toContain("OPERATOR 可預演");
    expect(stepText(3)).toContain("僅 ADMIN 可確認");
    expect(FIELD("預演")?.meaning).toContain("完全不會改動任何東西");
    expect(FIELD("建立 GitHub 遠端")?.meaning).toContain("不會存進資料庫");
  });

  it("AT_961_19_2 第 4 步說明含：拆解、簽核、測試規格草擬與凍結走既有介面、看板屬後續", () => {
    const text = stepText(4);
    for (const word of ["拆解", "簽核", "測試規格", "既有介面", "看板屬後續"]) expect(text, word).toContain(word);
  });

  it("AT_961_19_2 步驟句與 P1 新增欄位都過 lint（無禁字、英文只用白名單詞、句長與句數界線）；步驟維持 8 項內、第 5 步仍標尚未開放", () => {
    expect(researchWorkspace.steps.length).toBeLessThanOrEqual(8);
    expect(lintText(stepText(3), { maxSentences: 1 })).toEqual([]);
    expect(lintText(stepText(4), { maxSentences: 1 })).toEqual([]);
    expect(stepText(5)).toContain("尚未開放");
    for (const name of ["分流精靈", "軌道 A", "軌道 B", "掛載目標", "預演", "確認執行", "重新輸入庫名", "建立 GitHub 遠端", "差異理由", "重試失敗步驟"]) {
      const field = FIELD(name);
      expect(field, `登記了欄位 ${name}`).toBeDefined();
      expect(lintText(field?.meaning ?? "", { maxSentences: 2 }), name).toEqual([]);
    }
  });

  it("AT_961_19_2 P1 新增欄位名都是畫面字樣的逐字引用（components/domain/research 內找得到）", () => {
    const dir = path.resolve(process.cwd(), "components", "domain", "research");
    const sources = ["RouteDrawer.tsx", "RouteCardA.tsx", "RouteCardB.tsx", "PublicRepoConfirm.tsx", "RoutePanel.tsx", "RouteStepsTimeline.tsx"]
      .map((f) => readFileSync(path.join(dir, f), "utf8"))
      .join("\n");
    for (const name of ["分流精靈", "軌道 A", "軌道 B", "掛載目標", "預演", "確認執行", "重新輸入庫名", "建立 GitHub 遠端", "差異理由", "重試失敗步驟"]) expect(sources, name).toContain(name);
  });

  it("AT_961_19_2 說明三道鎖的計數不變：寫實頁數與 PENDING 清單由既有鎖守；本頁仍登記為已寫頁", () => {
    expect(HELP_PAGES["research-workspace"]).toBe(researchWorkspace);
    expect(Object.keys(PENDING_HELP_PAGES)).toHaveLength(0);
  });
});

describe("AT_961_16_5 分流停用文案的單一登記處（IFACE §8.3 逐列）", () => {
  it("七個條件的文案逐字等於 IFACE §8.3，唯讀文案等於 READONLY_TITLE、OPERATOR 的說明含「權限不足」", () => {
    expect(ROUTE_DISABLED_TEXT.git).toBe("此部署找不到 git，無法分流");
    expect(ROUTE_DISABLED_TEXT.repo).toBe("此部署無法寫入 monorepo（容器模式）；請改用本機模式");
    expect(ROUTE_DISABLED_TEXT.gh).toBe("找不到 gh；可先建本地專案，之後自行推送");
    expect(ROUTE_DISABLED_TEXT.scaffold).toBe("尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本");
    expect(ROUTE_DISABLED_TEXT["mock-only"]).toBe("容器模式只跑 mock claude 的驗收；真分流限本機模式");
    expect(ROUTE_DISABLED_TEXT.viewer).toBe(READONLY_TITLE);
    expect(ROUTE_DISABLED_TEXT.adminOnly).toContain("權限不足");
    expect(ROUTE_DISABLED_TEXT.adminOnly).toContain("ADMIN");
  });
});
