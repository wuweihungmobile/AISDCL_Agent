import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { RUN } from "./helpers";
import { snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, NEEDS_BRIDGE, bootstrapSettings, brd, call, createFixture, dataOf, ensureQuota, getRun, poll, signIn, waitRun, type Fixture } from "./realBackend";

/**
 * W5 複驗：設計系統與覆蓋層的真瀏覽器逐項證據（把 W4 停在「✅ 實作+測試」的五列補上真瀏覽器實測）——對真後端＋真 Bridge＋aisdlc-mock-claude：
 *   UI-DS-04 僅用 Lucide 線性圖示、UI-DS-06 動效規範（僅色彩／透明度；hover 不位移不縮放不浮起）、UI-DS-07 狀態中文標籤與顏色、
 *   UI-OVL-02 Toast（底部置中、一次一則、自動消失）、UI-OVL-03 載入 Skeleton／spinner；另量 NFR-9.1-05（Markdown 預覽更新時間，含 20KB）。
 * 依據：設計稿 README〈Iconography〉〈Motion〉〈狀態 enum〉〈全域覆蓋層〉（docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md）。
 * 量測值以 console.log 印出（`[ui-evidence]` 開頭），報告引用；斷言只釘設計規範本身，不釘本機的絕對毫秒數（NFR-9.1-05 除外：5KB 以內 < 100ms）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const nm = (base: string) => `${base} ${RUN}`;

let done: Fixture; // 已完成（專案「完成」、目標「完成」）
let failed: Fixture; // 失敗（專案「失敗」、任務「待人工」＋兩個「待處理」）
let ready: Fixture; // 取消後回到「就緒」
let draft: Fixture; // 草稿
let executing: Fixture; // 執行中（Level 1 暫停，專案狀態 EXECUTING）
let executingRun = "";
let llm: FakeLlm;

const toast = (page: Page) => page.locator('[data-slot="toast-host"]');

async function runTo(request: Parameters<typeof ensureQuota>[0], f: Fixture, level: number, until: string[]): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status, JSON.stringify(r.json).slice(0, 200)).toBe(201);
  const id = dataOf<{ id: string }>(r).id;
  await poll(
    () => getRun(request, id),
    (x) => until.includes(x.status) && (x.status === "COMPLETED" || (x.pendingReviews ?? []).length > 0),
    `批次 ${id} 進入 ${until.join("／")}`,
    120_000,
  );
  return id;
}

/**
 * 長批次夾具（26 個任務≈20 秒）：暫停中的批次，專案狀態是 READY（契約 §3.5.2：PAUSED 時專案 EXECUTING→READY），拿不到「執行中」的畫面；
 * 只有批次真的在跑時專案才是 EXECUTING，而 5 個任務的批次 4 秒就跑完。mock claude 沒有慢步驟旋鈕（QA 報告 O-21），所以用任務數撐時間。
 */
async function createLong(request: Parameters<typeof ensureQuota>[0]): Promise<Fixture> {
  await ensureQuota(request, "operator", 60);
  const f = await createFixture(request, { name: nm(`QA W5 證據 長批次 ${Math.random().toString(36).slice(2, 6)}`), kind: "A", level: 4 });
  for (let n = 4; n <= 26; n += 1) {
    const t = await call(request, "operator", "POST", `/api/v1/goals/${f.goalIds[0]}/tasks`, {
      name: `任務${n}`,
      description: `請輸出 [T${n}_DONE]`,
      passCriteria: `輸出含 [T${n}_DONE]`,
      expectedOutputRegex: `\\[T${n}_DONE\\]`,
      maxRetries: 1,
      draft: false,
    });
    expect(t.status, JSON.stringify(t.json).slice(0, 200)).toBe(201);
  }
  return f;
}

async function startRun(request: Parameters<typeof ensureQuota>[0], f: Fixture): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 1_000_000, scope: { mode: "ALL" } });
  expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
  return dataOf<{ id: string }>(r).id;
}
test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  test.setTimeout(420_000);
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
  llm = new FakeLlm(nm("QA W5 證據"));
  await llm.listen();
  await ensureQuota(request, "operator", 70);
  done = await createFixture(request, { name: nm("QA W5 證據 完成"), kind: "A", level: 4 });
  await runTo(request, done, 4, ["COMPLETED"]);
  failed = await createFixture(request, { name: nm("QA W5 證據 失敗"), kind: "A", level: 4, failTasks: [1] });
  await runTo(request, failed, 4, ["FAILED"]);
  ready = await createFixture(request, { name: nm("QA W5 證據 就緒"), kind: "A", level: 1 });
  const readyRun = await runTo(request, ready, 1, ["PAUSED"]);
  expect((await call(request, "operator", "POST", `/api/v1/executions/${readyRun}/cancel`)).status).toBe(200);
  await waitRun(request, readyRun, ["CANCELLED"], 60_000);
  draft = await createFixture(request, { name: nm("QA W5 證據 草稿"), kind: "A", level: 4 });
  executing = await createFixture(request, { name: nm("QA W5 證據 執行中"), kind: "B", level: 1 });
  executingRun = await runTo(request, executing, 1, ["PAUSED"]);
});

test.afterAll(async ({ request }) => {
  await llm.close();
  if (executingRun) await call(request, "operator", "POST", `/api/v1/executions/${executingRun}/cancel`);
  await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 45);
});

/** 頁面上所有 svg 的普查：非圖表的一律要是 Lucide 線性圖示（fill:none、stroke-width:1.5）；另查 emoji 與 img。 */
async function iconCensus(page: Page): Promise<{ total: number; lucide: number; charts: number; nonLucide: string[]; badStyle: string[]; emoji: string[]; imgs: number }> {
  return page.evaluate(() => {
    const svgs = [...document.querySelectorAll("svg")];
    const inChart = (s: Element) => !!s.closest('[data-testid$="chart"], .recharts-wrapper, [class*="recharts"], .w-md-editor-toolbar');
    const lucide = svgs.filter((s) => (s.getAttribute("class") ?? "").includes("lucide"));
    const others = svgs.filter((s) => !(s.getAttribute("class") ?? "").includes("lucide"));
    const badStyle = lucide.filter((s) => getComputedStyle(s).fill !== "none" || getComputedStyle(s).strokeWidth !== "1.5px").map((s) => s.getAttribute("class") ?? "");
    return {
      total: svgs.length,
      lucide: lucide.length,
      charts: others.filter(inChart).length,
      nonLucide: others.filter((s) => !inChart(s)).map((s) => `${s.getAttribute("class") ?? ""} ${s.outerHTML.slice(0, 80)}`),
      badStyle,
      emoji: [...document.body.innerText.matchAll(/\p{Extended_Pictographic}/gu)].map((m) => m[0]),
      imgs: document.images.length,
    };
  });
}

const rectOf = (el: Locator) =>
  el.evaluate((e) => {
    const b = e.getBoundingClientRect();
    const cs = getComputedStyle(e);
    return {
      x: Math.round(b.x * 10) / 10,
      y: Math.round(b.y * 10) / 10,
      w: Math.round(b.width * 10) / 10,
      h: Math.round(b.height * 10) / 10,
      transform: cs.transform,
      shadow: cs.boxShadow,
      bg: cs.backgroundColor,
      color: cs.color,
      opacity: cs.opacity,
    };
  });

test.describe("設計系統與覆蓋層：真瀏覽器逐項證據", () => {
  test.setTimeout(240_000);

  test("UI-DS-04｜僅用 Lucide 線性圖示：10 個頁面／狀態逐頁普查——非圖表的 svg 一律是 Lucide（fill:none、stroke-width:1.5），沒有 emoji、沒有 img", async ({ page, request }) => {
    test.setTimeout(480_000);
    await signIn(page, request, "operator");
    const stops: Array<[string, () => Promise<void>]> = [
      [
        "總覽",
        async () => {
          await page.goto("/");
          await expect(page.getByTestId("kpi-week-done")).toHaveText(/^\d+$/, FIRST_LOAD);
        },
      ],
      [
        "專案列表",
        async () => {
          await page.goto("/projects");
          await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
        },
      ],
      [
        "新建專案對話框",
        async () => {
          await page.getByRole("button", { name: "新建專案" }).click();
          await expect(page.locator(".w-md-editor").first()).toBeVisible();
        },
      ],
      [
        "專案詳情",
        async () => {
          await page.goto(`/projects/${done.projectId}`);
          await expect(page.getByTestId("goal-row")).toHaveCount(2, FIRST_LOAD);
        },
      ],
      [
        "目標詳情",
        async () => {
          await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}`);
          await expect(page.getByTestId("task-row")).toHaveCount(2, FIRST_LOAD);
        },
      ],
      [
        "任務詳情",
        async () => {
          await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}/tasks/${done.taskIds[0]}`);
          await expect(page.getByTestId("task-title")).toBeVisible(FIRST_LOAD);
        },
      ],
      [
        "執行頁（完成）",
        async () => {
          await page.goto(`/projects/${done.projectId}/execute`);
          await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", FIRST_LOAD);
        },
      ],
      [
        "執行頁（暫停中審核卡）",
        async () => {
          await page.goto(`/projects/${executing.projectId}/execute`);
          await expect(page.getByTestId("review-row")).toHaveCount(1, FIRST_LOAD);
        },
      ],
      [
        "監控頁",
        async () => {
          await page.goto(`/projects/${done.projectId}/monitor`);
          await expect(page.getByTestId("token-trend-chart")).toBeVisible(FIRST_LOAD);
        },
      ],
      [
        "設定頁",
        async () => {
          await page.goto("/settings");
          await expect(page.getByTestId("settings-panel")).toBeVisible(FIRST_LOAD);
        },
      ],
      [
        "匯入頁",
        async () => {
          await page.goto("/import");
          await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
        },
      ],
    ];
    const seen: string[] = [];
    for (const [label, go] of stops) {
      await ensureQuota(request, "operator", 50); // 十一個頁面連續載入會超過每分鐘 100 次的額度（W4 DEF-AC-009 的同一個桶）
      await go();
      await page.waitForTimeout(600);
      const c = await iconCensus(page);
      seen.push(`${label}：svg ${c.total}＝Lucide ${c.lucide}＋圖表／編輯器工具列 ${c.charts}`);
      expect(c.nonLucide, `${label}：非 Lucide 的 svg`).toEqual([]);
      expect(c.badStyle, `${label}：Lucide 圖示不是線性（fill:none、stroke-width:1.5）`).toEqual([]);
      expect(c.emoji, `${label}：畫面文字不得有 emoji`).toEqual([]);
      expect(c.imgs, `${label}：不得有 img 當圖示`).toBe(0);
      expect(c.lucide, `${label}：至少有一個 Lucide 圖示（普查沒有掃空）`).toBeGreaterThan(0);
      if (label === "新建專案對話框") await page.keyboard.press("Escape");
    }
    console.log(`[ui-evidence] UI-DS-04 逐頁普查：${seen.join("；")}`);
  });

  test("UI-DS-06｜動效規範：hover 只改顏色／透明度（主色鈕→primary-strong、導覽項→tertiary 底、連結→主色字），transform 與陰影不變、版面不位移；過場只有 0.15／0.2／0.4 秒；執行中專案的狀態點 wg-blink 1.4s 無限呼吸；進度條 width 0.4s", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    const long = await createLong(request);
    await signIn(page, request, "operator");
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await page.waitForTimeout(800);
    const probes: Array<{ label: string; el: Locator; expectChange: Array<"bg" | "color" | "opacity"> }> = [
      { label: "主色實底按鈕（新建專案）", el: page.getByRole("button", { name: "新建專案" }), expectChange: ["bg"] },
      { label: "專案卡的名稱連結", el: page.getByTestId("project-card").first().getByRole("link").first(), expectChange: ["color"] },
      { label: "側欄導覽項", el: page.getByRole("navigation", { name: "主導覽" }).getByRole("link").first(), expectChange: ["bg"] },
      {
        label: "專案卡的 ghost 按鈕",
        el: page
          .getByTestId("project-card")
          .first()
          .getByRole("link", { name: /查看|編輯|執行|監控/ })
          .first(),
        expectChange: [],
      },
    ];
    const lines: string[] = [];
    for (const p of probes) {
      await page.mouse.move(2, 2);
      await page.waitForTimeout(350);
      const before = await rectOf(p.el);
      await p.el.hover();
      await page.waitForTimeout(450); // 過場 0.15～0.2s 之後
      const after = await rectOf(p.el);
      expect([after.x, after.y, after.w, after.h], `${p.label}：hover 不位移、不縮放`).toEqual([before.x, before.y, before.w, before.h]);
      expect(after.transform, `${p.label}：hover 不套 transform`).toBe(before.transform);
      expect(after.shadow, `${p.label}：hover 不浮起（無陰影）`).toBe("none");
      for (const k of p.expectChange) expect(after[k], `${p.label}：hover 改變 ${k}`).not.toBe(before[k]);
      lines.push(`${p.label}：${p.expectChange.map((k) => `${k} ${before[k]}→${after[k]}`).join("、") || "（無預期變色，僅驗不位移）"}`);
    }
    // 過場：全站只有顏色／透明度（Tailwind 的 transition-colors／-opacity 0.15s、全域 transition 0.2s ease-out）與進度條的 width／height 0.4s；
    // hover 不用 transform（見上）。逐元素取 computed 的 transition-property／duration，核對時間落在三個值之內，並回報有 transform 的過場有幾個。
    const transitions = await page.evaluate(() => {
      const out = new Map<string, { props: string; dur: string; timing: string; n: number }>();
      for (const el of document.querySelectorAll("*")) {
        const cs = getComputedStyle(el);
        if (cs.transitionDuration === "0s") continue;
        const key = `${cs.transitionProperty}|${cs.transitionDuration}|${cs.transitionTimingFunction}`;
        const hit = out.get(key);
        if (hit) hit.n += 1;
        else out.set(key, { props: cs.transitionProperty, dur: cs.transitionDuration, timing: cs.transitionTimingFunction, n: 1 });
      }
      return [...out.values()];
    });
    for (const t of transitions) expect(["0.15s", "0.2s", "0.4s"], `過場時間 ${t.dur}（${t.props.slice(0, 60)}）`).toContain(t.dur);
    const withTransform = transitions.filter((t) => t.props.split(", ").includes("transform"));
    const transitionSummary = transitions
      .map((t) => `${t.props.split(", ").length > 3 ? `${t.props.split(", ").slice(0, 2).join("、")}…（${t.props.split(", ").length} 項）` : t.props} ${t.dur} ×${t.n}`)
      .join("｜");

    // keyframes：執行中專案的狀態點呼吸（wg-blink 1.4s infinite）。暫停中的批次專案是 READY（契約 §3.5.2），所以用 25 個任務的長批次（約 20 秒）撐出 EXECUTING
    await ensureQuota(request, "operator", 40);
    const runId = await startRun(request, long);
    try {
      await page.goto(`/projects/${long.projectId}`);
      await expect(page.getByTestId("project-title")).toHaveText(long.name, FIRST_LOAD);
      await expect(page.locator('#main-content [data-slot="status-label"]').first()).toContainText("執行中");
      const blink = await page.evaluate(() =>
        document
          .getAnimations()
          .filter((a) => (a as CSSAnimation).animationName === "wg-blink")
          .map((a) => {
            const target = (a.effect as KeyframeEffect).target as HTMLElement | null;
            const timing = a.effect!.getTiming();
            return { slot: target?.getAttribute("data-slot") ?? "", inMain: !!target?.closest("#main-content"), dur: timing.duration, infinite: timing.iterations === Infinity };
          }),
      );
      const inMain = blink.filter((b) => b.inMain);
      expect(inMain.length, `主內容區裡執行中專案的狀態點在呼吸（全部 wg-blink 動畫：${JSON.stringify(blink)}）`).toBeGreaterThan(0);
      expect(inMain[0]).toEqual({ slot: "status-dot", inMain: true, dur: 1400, infinite: true });
      const bar = await page.evaluate(() =>
        [...document.querySelectorAll("*")]
          .map((e) => getComputedStyle(e))
          .filter((cs) => cs.transitionProperty === "width")
          .map((cs) => `${cs.transitionDuration} ${cs.transitionTimingFunction}`),
      );
      expect(bar.length, "專案詳情有進度條").toBeGreaterThan(0);
      expect([...new Set(bar)]).toEqual(["0.4s cubic-bezier(0.4, 0, 0.2, 1)"]);
      console.log(
        `[ui-evidence] UI-DS-06 hover：${lines.join("；")}；過場組合：${transitionSummary}（含 transform 的過場宣告 ${withTransform.length} 組，hover 皆未使用）；wg-blink：${JSON.stringify(inMain[0])}；進度條 width 過場：${bar[0]}`,
      );
    } finally {
      await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
    }
  });

  test("UI-DS-07｜狀態中文標籤與顏色：專案列表（草稿／就緒／執行中／完成／失敗）、目標頁的任務狀態（完成／待人工／待處理）、執行頁批次狀態（已完成／失敗／已暫停）——標籤逐字、圓點色取對應的設計 token", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    await signIn(page, request, "operator");
    const token = (name: string) =>
      page.evaluate((t) => {
        const e = document.createElement("span");
        e.style.background = `var(${t})`;
        document.body.appendChild(e);
        const c = getComputedStyle(e).backgroundColor;
        e.remove();
        return c;
      }, name);
    const dotOf = (scope: Locator) =>
      scope
        .locator('[data-slot="status-label"]')
        .first()
        .evaluate((l) => ({ text: (l.textContent ?? "").trim(), color: getComputedStyle(l.querySelector('[data-slot="status-dot"]')!).backgroundColor }));
    // 任務列：圓點在最前面、標籤是名稱連結後面的 span（TaskListCard）
    const taskDot = (row: Locator) =>
      row.evaluate((r) => ({ text: (r.querySelector("a")?.nextElementSibling?.textContent ?? "").trim(), color: getComputedStyle(r.querySelector('[data-slot="status-dot"]')!).backgroundColor }));
    const lines: string[] = [];

    // 執行中：長批次進行中，列表第一頁（依更新時間新→舊）就有它
    const long = await createLong(request);
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await ensureQuota(request, "operator", 40);
    const runId = await startRun(request, long);
    try {
      await page.reload();
      const runningCard = page.getByTestId("project-card").filter({ hasText: long.name });
      await expect(runningCard).toHaveCount(1, FIRST_LOAD);
      const running = await dotOf(runningCard);
      expect(running.text, "執行中專案的狀態標籤").toBe("執行中");
      expect(running.color, "執行中的圓點色＝--color-primary").toBe(await token("--color-primary"));
      expect(
        await runningCard
          .locator('[data-slot="status-dot"]')
          .first()
          .evaluate((el) => el.getAnimations().some((a) => (a as CSSAnimation).animationName === "wg-blink")),
        "執行中的圓點在呼吸",
      ).toBe(true);
      lines.push(`執行中＝${running.color}（--color-primary，呼吸）`);
      await page.goto(`/projects/${long.projectId}/execute`);
      await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "RUNNING", FIRST_LOAD);
      expect(((await page.getByTestId("run-status").innerText()) ?? "").trim()).toContain("執行中");
    } finally {
      await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
    }

    // 其餘四種專案狀態：用全域搜尋縮小清單
    await ensureQuota(request, "operator", 50);
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await page.getByRole("searchbox", { name: "搜尋專案、目標、任務" }).fill(`QA W5 證據`);
    await page.keyboard.press("Enter");
    const expectedProjects: Array<[Fixture, string, string]> = [
      [draft, "草稿", "--color-text-muted"],
      [ready, "就緒", "--color-secondary"],
      [done, "完成", "--color-primary"],
      [failed, "失敗", "--color-error"],
    ];
    for (const [f, label, tok] of expectedProjects) {
      const card = page.getByTestId("project-card").filter({ hasText: f.name });
      await expect(card, `專案列表有「${f.name}」`).toHaveCount(1, FIRST_LOAD);
      const got = await dotOf(card);
      expect(got.text, `${f.name} 的狀態標籤`).toBe(label);
      expect(got.color, `${label} 的圓點色＝${tok}`).toBe(await token(tok));
      lines.push(`${label}＝${got.color}（${tok}）`);
    }
    await snap(page, "p9-status-labels-projects.png");

    // 目標頁：失敗專案的第一個任務 ESCALATED「待人工」（accent）、其餘「待處理」（disabled-text）；完成專案的任務「完成」
    await ensureQuota(request, "operator", 50);
    await page.goto(`/projects/${failed.projectId}/goals/${failed.goalIds[0]}`);
    await expect(page.getByTestId("task-row")).toHaveCount(2, FIRST_LOAD);
    const rows = page.getByTestId("task-row");
    const t1 = await taskDot(rows.nth(0));
    const t2 = await taskDot(rows.nth(1));
    expect(t1.text).toBe("待人工");
    expect(t1.color).toBe(await token("--color-accent"));
    expect(t2.text).toBe("待處理");
    expect(t2.color).toBe(await token("--color-disabled-text"));
    await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}`);
    await expect(page.getByTestId("task-row")).toHaveCount(2, FIRST_LOAD);
    const tDone = await taskDot(page.getByTestId("task-row").first());
    expect(tDone.text).toBe("完成");
    expect(tDone.color).toBe(await token("--color-primary"));
    lines.push(`任務：待人工＝accent、待處理＝disabled、完成＝primary`);

    // 執行頁：批次狀態標籤（已完成／失敗／已暫停）
    const runLabel = async (f: Fixture) => {
      await ensureQuota(request, "operator", 50);
      await page.goto(`/projects/${f.projectId}/execute`);
      await expect(page.getByTestId("run-status")).toBeVisible(FIRST_LOAD);
      return { text: ((await page.getByTestId("run-status").innerText()) ?? "").trim(), status: await page.getByTestId("run-status").getAttribute("data-status") };
    };
    expect(await runLabel(done)).toMatchObject({ status: "COMPLETED", text: expect.stringContaining("已完成") });
    expect(await runLabel(failed)).toMatchObject({ status: "FAILED", text: expect.stringContaining("失敗") });
    expect(await runLabel(executing)).toMatchObject({ status: "PAUSED", text: expect.stringContaining("已暫停") });
    console.log(`[ui-evidence] UI-DS-07：${lines.join("；")}；批次狀態：已完成／失敗／已暫停（執行中見上）`);
  });
  test("UI-OVL-02｜Toast：底部置中（水平中線＝視窗中線、距底 28px）、一次只顯示一則（後來的取代先前的）、成功 2.4 秒與錯誤 6 秒後自動消失", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}/monitor`);
    await expect(page.getByRole("heading", { name: `專案監控：${done.name}` })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("token-trend-chart")).toBeVisible(FIRST_LOAD);
    const vp = page.viewportSize()!;

    // 位置＋一次一則：連按「匯出 CSV」「匯出 PDF」，取樣宿主內的訊息
    await page.getByTestId("export-csv").click();
    const csvToast = toast(page).getByText(/已匯出報表：monitor-report-.*\.csv/);
    await expect(csvToast).toBeVisible();
    const box = (await toast(page).boundingBox())!;
    const centerX = box.x + box.width / 2;
    expect(Math.abs(centerX - vp.width / 2), `水平中心 ${centerX.toFixed(1)} 對視窗中線 ${vp.width / 2}`).toBeLessThanOrEqual(2);
    expect(Math.abs(box.y + box.height - (vp.height - 28)), `底緣 ${(box.y + box.height).toFixed(1)} 對 視窗高 ${vp.height} − 28`).toBeLessThanOrEqual(2);
    const samples: string[] = [];
    const sampler = page.evaluate(
      () =>
        new Promise<string[]>((resolve) => {
          const out: string[] = [];
          const t = setInterval(() => out.push((document.querySelector('[data-slot="toast-host"]')?.textContent ?? "").trim()), 40);
          setTimeout(() => {
            clearInterval(t);
            resolve(out);
          }, 900);
        }),
    );
    await page.getByTestId("export-pdf").click();
    samples.push(...(await sampler));
    const distinct = [...new Set(samples.filter((s) => s !== ""))];
    expect(distinct.at(-1), `取樣到的訊息序列：${JSON.stringify(distinct)}`).toMatch(/\.pdf/);
    for (const s of samples) expect([(s.match(/已匯出報表/g) ?? []).length], `同一時間只有一則：${s}`).toEqual([s === "" ? 0 : 1]);
    expect(distinct.length, "csv 那則被 pdf 這則取代").toBeLessThanOrEqual(2);

    // 自動消失：成功 2.4 秒
    const t0 = Date.now();
    await expect(toast(page).getByText(/已匯出報表/)).toBeHidden({ timeout: 6_000 });
    const okMs = Date.now() - t0;
    // 註：上面最後一次觸發在 PDF 按下之後約 0.9 秒（取樣窗），所以從「看到」到「消失」的剩餘時間約 1.5 秒；另以全新觸發量整段
    await page.getByTestId("export-csv").click();
    const tStart = Date.now();
    await expect(toast(page).getByText(/已匯出報表/)).toBeVisible();
    await expect(toast(page).getByText(/已匯出報表/)).toBeHidden({ timeout: 6_000 });
    const successMs = Date.now() - tStart;
    expect(successMs, `成功 toast 存續 ${successMs}ms（規格 2400ms）`).toBeGreaterThanOrEqual(2000);
    expect(successMs).toBeLessThanOrEqual(3600);

    // 錯誤 toast 6 秒：把報表請求打斷
    await page.route(/\/monitor\/projects\/[0-9a-f-]+\/report/, (route) => route.abort());
    await page.getByTestId("export-csv").click();
    const errToast = toast(page).getByText(/匯出失敗/);
    const eStart = Date.now();
    await expect(errToast).toBeVisible({ timeout: 10_000 });
    await expect(errToast).toBeHidden({ timeout: 9_000 });
    const errMs = Date.now() - eStart;
    expect(errMs, `錯誤 toast 存續 ${errMs}ms（規格 6000ms）`).toBeGreaterThanOrEqual(5000);
    expect(errMs).toBeLessThanOrEqual(7600);
    console.log(
      `[ui-evidence] UI-OVL-02：水平中心偏差 ${Math.abs(centerX - vp.width / 2).toFixed(1)}px、底緣距視窗底 ${(vp.height - (box.y + box.height)).toFixed(1)}px；一次一則（取樣 ${samples.length} 次，訊息序列 ${distinct.length} 種）；成功 ${successMs}ms（規格 2400）、錯誤 ${errMs}ms（規格 6000）；先前一則剩餘 ${okMs}ms`,
    );
    await snap(page, "p9-toast-bottom-center.png");
  });

  test("UI-OVL-03｜載入 Skeleton／spinner：列表與詳情載入慢時顯示 Skeleton（wg-pulse 1.4s、aria-hidden）與頁面骨架（aria-busy）；匯入解析中顯示置中 spinner（wg-spin 0.8s linear）與說明；載入完成後都消失", async ({
    page,
    request,
  }) => {
    await signIn(page, request, "operator");
    // 列表：延遲 GET /projects 1.8 秒
    await page.route(/\/api\/v1\/projects(\?|$)/, async (route) => {
      if (route.request().method() === "GET") await new Promise((r) => setTimeout(r, 1800));
      await route.continue();
    });
    await page.goto("/projects");
    const sk = page.locator('[data-slot="skeleton"]');
    await expect(sk.first(), "列表載入中：Skeleton 出現").toBeVisible({ timeout: 5_000 });
    expect(await sk.first().getAttribute("aria-hidden")).toBe("true");
    // CSS 層的動畫規格取 computed style（effect.getTiming().easing 只反映 effect 層、與 animation-timing-function 不同）
    const pulse = await sk.first().evaluate((el) => {
      const cs = getComputedStyle(el);
      return { name: cs.animationName, dur: cs.animationDuration, easing: cs.animationTimingFunction, iter: cs.animationIterationCount, running: el.getAnimations().length > 0 };
    });
    expect(pulse, "Skeleton 的脈動動畫（設計稿：僅 opacity 脈動）").toEqual({ name: "wg-pulse", dur: "1.4s", easing: "ease-in-out", iter: "infinite", running: true });
    await snap(page, "p9-skeleton-projects.png");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await expect(sk, "載入完成後 Skeleton 消失").toHaveCount(0);
    await page.unroute(/\/api\/v1\/projects(\?|$)/);

    // 詳情：頁面級骨架（aria-busy、標籤「頁面載入中」）
    await page.route(new RegExp(`/api/v1/projects/${done.projectId}$`), async (route) => {
      await new Promise((r) => setTimeout(r, 1800));
      await route.continue();
    });
    await page.goto(`/projects/${done.projectId}`);
    await expect(page.getByLabel("頁面載入中")).toBeVisible({ timeout: 5_000 });
    expect(await page.getByLabel("頁面載入中").getAttribute("aria-busy")).toBe("true");
    await expect(page.getByTestId("project-title")).toHaveText(done.name, FIRST_LOAD);
    await expect(page.getByLabel("頁面載入中")).toHaveCount(0);
    await page.unrouteAll({ behavior: "ignoreErrors" });

    // 匯入解析中：spinner（假 OpenAI 相容伺服器延遲 1.5 秒）
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint })).status).toBe(200);
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "qa-dummy-key", confirm: true })).status).toBe(200);
    llm.gatesOn = false;
    llm.delayMs = 1500;
    try {
      await page.goto("/import");
      await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
      await page.getByRole("tab", { name: "貼上文字" }).click();
      await page.getByLabel("需求文字").fill(brd());
      await page.getByLabel("來源名稱").fill(`ovl03-${RUN}.md`);
      await page.getByLabel("格式").selectOption("MARKDOWN");
      await page.getByLabel("執行路徑").fill(path.join(E2E_ROOT, "projects", `ovl03-${RUN}`));
      await page.getByRole("button", { name: "開始解析" }).click();
      const parsing = page.getByTestId("import-parsing");
      await expect(parsing).toBeVisible();
      await expect(parsing).toContainText("AI 解析中");
      const spinner = parsing.getByRole("status", { name: "AI 解析中" }).first();
      await expect(spinner).toBeVisible();
      const spin = await spinner.evaluate((el) => {
        const cs = getComputedStyle(el);
        return { name: cs.animationName, dur: cs.animationDuration, easing: cs.animationTimingFunction, iter: cs.animationIterationCount, running: el.getAnimations().length > 0 };
      });
      expect(spin, "解析中的 spinner 在轉（設計稿：wg-spin 0.8s linear）").toEqual({ name: "wg-spin", dur: "0.8s", easing: "linear", iter: "infinite", running: true });
      await snap(page, "p9-spinner-import-parsing.png");
      await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
      await expect(page.getByTestId("import-parsing")).toHaveCount(0);
      const id = new URL(page.url()).searchParams.get("id");
      if (id) await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
      console.log(`[ui-evidence] UI-OVL-03：列表 Skeleton（${JSON.stringify(pulse)}）、頁面骨架（aria-busy）、匯入解析 spinner（${JSON.stringify(spin)}）`);
    } finally {
      llm.delayMs = 0;
      await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
      await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
    }
  });

  test("NFR-9.1-05｜Markdown 預覽更新時間（編輯器貼入 N KB → 預覽穩定；每種大小 7 次取中位數）：5KB 以內 < 100ms；20KB 重量（W4：112ms、W5-FE 去抖後：149ms）", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto("/projects/new");
    const box = page.getByRole("textbox", { name: "說明描述", exact: true });
    await box.waitFor({ timeout: 30_000 });
    const block = (i: number) =>
      `## 第 ${i} 節 設計說明\n\n這是一段說明文字，包含 **粗體**、*斜體*、\`行內程式碼\` 與 [連結](https://example.com/${i})。\n\n- [x] 已完成項目 ${i}\n- [ ] 待辦項目 ${i}\n\n| 欄位 | 說明 | 值 |\n|------|------|----|\n| a${i} | 範例 | ${i} |\n\n\`\`\`python\ndef f${i}(x):\n    return x * ${i}\n\`\`\`\n\n`;
    const doc = (bytes: number) => {
      let s = "";
      let i = 0;
      while (new TextEncoder().encode(s).length < bytes) s += block((i += 1));
      return s;
    };
    const medians: Record<string, number> = {};
    for (const kb of [1, 5, 20]) {
      const text = doc(kb * 1024);
      const samples: number[] = [];
      for (let n = 0; n < 7; n += 1) {
        await box.fill("");
        await page.waitForTimeout(400);
        const ms = await page.evaluate(
          (value) =>
            new Promise<number>((resolve) => {
              const ta = document.querySelector('textarea[aria-label="說明描述"], .w-md-editor-text-input') as HTMLTextAreaElement;
              const preview = document.querySelector(".w-md-editor-preview")!;
              let last = performance.now();
              let t0 = 0;
              let timer: ReturnType<typeof setTimeout> | undefined;
              const obs = new MutationObserver(() => {
                last = performance.now();
                clearTimeout(timer);
                timer = setTimeout(() => {
                  obs.disconnect();
                  resolve(last - t0);
                }, 150);
              });
              obs.observe(preview, { childList: true, subtree: true, characterData: true, attributes: true });
              const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
              t0 = performance.now();
              setter.call(ta, value);
              ta.dispatchEvent(new Event("input", { bubbles: true }));
              setTimeout(() => {
                obs.disconnect();
                resolve(-1);
              }, 8000);
            }),
          text,
        );
        expect(ms, `${kb}KB 第 ${n + 1} 次沒有量到預覽更新`).toBeGreaterThan(0);
        samples.push(ms);
      }
      const sorted = [...samples].sort((a, b) => a - b);
      medians[`${kb}KB`] = Math.round(sorted[3]);
      console.log(`[ui-evidence] NFR-9.1-05 ${kb}KB：樣本(ms)=${samples.map((x) => Math.round(x)).join(", ")}；中位數 ${Math.round(sorted[3])}ms、最大 ${Math.round(sorted[6])}ms`);
    }
    expect(medians["1KB"], "1KB 中位數").toBeLessThan(100);
    expect(medians["5KB"], "5KB 中位數").toBeLessThan(100);
    expect(medians["20KB"], "20KB 只設寬鬆上限（目標 100ms 未達屬已知 🟡，見 RTM NFR-9.1-05）").toBeLessThan(400);
  });
});
