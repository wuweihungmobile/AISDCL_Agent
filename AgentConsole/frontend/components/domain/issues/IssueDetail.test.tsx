/**
 * IssueDetail 的元件測試（TCS-IssueCenter-20261027 AT-IC-08-4-E-1、AT-IC-08-11-1、AT-IC-08-11-E-1；R-IC-65）：
 * 詳情側面板的關聯（可點／查無不可點）、已結案議題日期旁的「最後已知動靜」註記（取自 legend、不寫死），以及頭部、原列、時間線、純文字與失敗態。
 * 資料來自 issues.fixtures.ts 的假後端（`GET /api/v1/issues/{id}` 單筆：含 raw、timeline、priority，沒有 legend）。
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { IssueLegend } from "@/lib/api/types";
import { IssueDetail } from "./IssueDetail";
import { DEFAULT_TIMELINE, LEGEND, clone, makeIssue, newStub, notFound, renderIssues, unavailable } from "./tests/issues.fixtures";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身（詳情本身不導覽）
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/issues",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
afterEach(() => {
  delete (window as unknown as Record<string, unknown>).__xss;
});

/** 持有目前顯示的議題編號：關聯被點時換成那一個（同頁、不換路由）。 */
function Harness({ initial, legend = LEGEND, onClose = () => undefined }: { initial: string; legend?: IssueLegend; onClose?: () => void }) {
  const [id, setId] = useState(initial);
  return <IssueDetail id={id} legend={legend} onClose={onClose} onOpenIssue={setId} />;
}

const detail = () => screen.getByTestId("issue-detail");
const heading = () => within(detail()).getByRole("heading", { level: 2 });

describe("AT_IC_08_4_E_1 詳情的關聯", () => {
  it("AT_IC_08_4_E_1 關聯的議題可點（跳到該議題的詳情）；查無該議題＝顯示「不在議題中心（可能已歸檔）」且不可點", async () => {
    const user = userEvent.setup();
    renderIssues(<Harness initial="PROP-SI-004" />);
    const links = await screen.findByTestId("issue-detail-links");
    // 夾具：OBS-SI-009 在議題中心；DEF-999-404 不在（單筆查無＝404 si_not_found）
    const existing = await within(links).findByRole("button", { name: "OBS-SI-009" });
    const missing = within(links).getByTestId("issue-link-DEF-999-404");
    await waitFor(() => expect(missing).toHaveTextContent("不在議題中心（可能已歸檔）"));
    expect(missing).toHaveTextContent("DEF-999-404");
    expect(within(missing).queryByRole("button")).toBeNull();
    expect(within(links).getAllByRole("button")).toHaveLength(1);

    await user.click(existing);
    await waitFor(() => expect(heading()).toHaveTextContent("OBS-SI-009"));
    // 該議題沒有關聯：不渲染任何連結
    expect(await screen.findByText("沒有關聯的議題")).toBeInTheDocument();
  });

  it("關聯確認中不可點（避免點到查無的）；確認失敗但不是 404（資料面暫時不可用）時無法證明查無，仍給按鈕", async () => {
    const stub = newStub({
      overrides: {
        one: (call) => {
          if (call.path.endsWith("/OBS-SI-009")) return new Promise(() => undefined); // 永遠不回：確認中
          if (call.path.endsWith("/PROP-SI-004")) return undefined;
          return unavailable();
        },
      },
    });
    renderIssues(<Harness initial="PROP-SI-004" />, { stub });
    const links = await screen.findByTestId("issue-detail-links");
    const pending = within(links).getByTestId("issue-link-OBS-SI-009");
    expect(within(pending).queryByRole("button")).toBeNull();
    // DEF-999-404 的查詢回 503：仍可點（點開後由詳情自己顯示原因）
    expect(await within(links).findByRole("button", { name: "DEF-999-404" })).toBeInTheDocument();
    expect(within(links).getByTestId("issue-link-DEF-999-404")).not.toHaveTextContent("不在議題中心");
  });
});

describe("AT_IC_08_11 已結案議題日期旁註明「最後已知動靜」", () => {
  it("AT_IC_08_11_1 已結案議題：詳情頭部日期＝該議題 updatedAt，日期旁註明「最後已知動靜」（文字取自 legend.updatedAtNote）", async () => {
    renderIssues(<Harness initial="OBS-SI-001" />);
    const date = await screen.findByTestId("issue-detail-date");
    expect(date.textContent).toBe("2026-10-18");
    const note = screen.getByTestId("issue-detail-date-note");
    expect(note.textContent).toBe(LEGEND.updatedAtNote);
    expect(note.textContent).toContain("最後已知動靜");
    expect(date.parentElement).toContainElement(note);
    // 頭部也寫明狀態與結果
    expect(detail()).toHaveTextContent("已完成・已裁決");
  });

  it("AT_IC_08_11_E_1 非已結案議題不帶此註記；註記隨 legend 換字、legend 沒帶就不顯示", async () => {
    // 非已結案（待解）：日期在、註記不在
    const open = renderIssues(<Harness initial="OBS-SI-006" />);
    expect((await screen.findByTestId("issue-detail-date")).textContent).toBe("2026-10-10");
    expect(screen.queryByTestId("issue-detail-date-note")).toBeNull();
    expect(detail().textContent).not.toContain("最後已知動靜");
    open.unmount();

    // 已結案，legend 換字：顯示新字、不顯示舊字
    const swapped: IssueLegend = { ...clone(LEGEND), updatedAtNote: "§新註記§" };
    const done = renderIssues(<Harness initial="OBS-SI-001" legend={swapped} />);
    expect((await screen.findByTestId("issue-detail-date-note")).textContent).toBe("§新註記§");
    expect(detail().textContent).not.toContain(LEGEND.updatedAtNote);
    done.unmount();

    // 已結案，legend 沒有註記（空字串）：不顯示
    renderIssues(<Harness initial="OBS-SI-001" legend={{ ...clone(LEGEND), updatedAtNote: "" }} />);
    await screen.findByTestId("issue-detail-date");
    expect(screen.queryByTestId("issue-detail-date-note")).toBeNull();
  });
});

describe("詳情的頭部、原列、時間線與純文字", () => {
  it("頭部：編號、標題、來源、狀態、嚴重度、順位與備註、最後更新；來源與嚴重度為 null 顯示「—」；不可排的列即使帶遺留順位也不顯示順位", async () => {
    const stub = newStub();
    stub.priorities.set("OBS-SI-006", { rank: 3, note: "備註一" });
    renderIssues(<Harness initial="OBS-SI-006" />, { stub });
    await screen.findByTestId("issue-detail-priority");
    expect(heading()).toHaveTextContent("OBS-SI-006");
    expect(screen.getByTestId("issue-detail-title")).toHaveTextContent("緊急的缺陷");
    expect(screen.getByTestId("issue-detail-priority").textContent).toBe("3：備註一");
    for (const text of ["系統缺陷", "待解", "緊急", "2026-10-10"]) expect(detail()).toHaveTextContent(text);
  });

  it("來源與嚴重度為 null、沒有順位時各顯示「—」；不可排且帶遺留順位的列順位仍是「—」", async () => {
    const stub = newStub({ items: [makeIssue("DEF-999-091", { source: null, severity: null, severityRank: null, updatedAt: null, rankable: false, priority: 7, priorityNote: "遺留" })] });
    renderIssues(<Harness initial="DEF-999-091" />, { stub });
    await screen.findByTestId("issue-detail-priority");
    expect(screen.getByTestId("issue-detail-priority").textContent).toBe("—");
    expect(screen.getByTestId("issue-detail-date").textContent).toBe("—");
    expect(within(detail()).getAllByText("—").length).toBeGreaterThanOrEqual(4);
  });

  it("原列顯示中文標籤與逐字的原值（唯一可見英文原值處）；時間線逐筆列出；下一步在頭部之後", async () => {
    renderIssues(<Harness initial="OBS-SI-003" />);
    const raw = await screen.findByTestId("issue-detail-raw");
    expect(Array.from(raw.querySelectorAll("dt")).map((el) => el.textContent)).toEqual(["處置", "症狀"]);
    expect(Array.from(raw.querySelectorAll("dd")).map((el) => el.textContent)).toEqual(["open", "原列的症狀全文，含 deferred 與 handed-off 等英文原值"]);
    const timeline = screen.getByTestId("issue-detail-timeline");
    const entry = DEFAULT_TIMELINE[0];
    expect(timeline.textContent).toContain(`#${entry.seq}　${entry.t}　${entry.by}　${entry.action}`);
    expect(within(detail()).getByRole("region", { name: "下一步" })).toHaveTextContent("等再開症狀出現");
  });

  it("單筆沒有 raw、timeline、links 時各區塊顯示說明，不渲染空表", async () => {
    const stub = newStub({
      overrides: {
        one: () => ({
          data: {
            schemaRev: 1,
            kind: "issues",
            generatedAt: "t",
            headSha: null,
            items: [{ ...makeIssue("OBS-SI-006"), raw: [], timeline: [] }],
            nextSince: null,
            truncated: false,
            ne: [],
            problems: [],
          },
        }),
      },
    });
    renderIssues(<Harness initial="OBS-SI-006" />, { stub });
    await screen.findByTestId("issue-detail-raw");
    expect(within(screen.getByTestId("issue-detail-raw")).getByText("沒有原列資料")).toBeInTheDocument();
    expect(within(screen.getByTestId("issue-detail-timeline")).getByText("沒有事件紀錄")).toBeInTheDocument();
    expect(within(screen.getByTestId("issue-detail-links")).getByText("沒有關聯的議題")).toBeInTheDocument();
  });

  it("純文字：原列與標題含 <script>、markdown 與 HTML 時一律是文字（不執行、不成元素）", async () => {
    const hostile = "<script>window.__xss=1</script> **粗體** `碼` <img src=x onerror=alert(1)>";
    const stub = newStub({
      overrides: {
        one: () => ({
          data: {
            schemaRev: 1,
            kind: "issues",
            generatedAt: "t",
            headSha: null,
            items: [{ ...makeIssue("OBS-SI-006", { title: hostile }), raw: [{ label: "症狀", value: hostile }], timeline: [] }],
            nextSince: null,
            truncated: false,
            ne: [],
            problems: [],
          },
        }),
      },
    });
    renderIssues(<Harness initial="OBS-SI-006" />, { stub });
    const raw = await screen.findByTestId("issue-detail-raw");
    expect(raw.querySelector("dd")?.textContent).toBe(hostile);
    expect(screen.getByTestId("issue-detail-title").textContent).toBe(hostile);
    expect(detail().querySelector("script, img, strong, code, b")).toBeNull();
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined();
  });
});

describe("詳情的載入、失敗與鍵盤", () => {
  it("載入中顯示「載入中」；資料面不可用時顯示摘要與 reason、cause、detail 逐字；查無（404）顯示「查無此議題」", async () => {
    // 載入中
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const pending = renderIssues(<Harness initial="OBS-SI-006" />, { stub: newStub({ overrides: { one: () => gate.then(() => undefined) } }) });
    expect(await screen.findByTestId("issue-detail-loading")).toHaveTextContent("議題詳情載入中…");
    await act(async () => release());
    await screen.findByTestId("issue-detail-raw");
    pending.unmount();

    // 503
    const down = renderIssues(<Harness initial="OBS-SI-006" />, { stub: newStub({ overrides: { one: () => unavailable("nonzero_rc", "rc=2; stderr=boom 全形字元") } }) });
    const error = await screen.findByTestId("issue-detail-error");
    expect(error).toHaveTextContent("議題資料暫時無法取得");
    expect(error).toHaveTextContent("reason：si_unavailable");
    expect(error).toHaveTextContent("cause：nonzero_rc");
    expect(error).toHaveTextContent("rc=2; stderr=boom 全形字元");
    expect(screen.queryByTestId("issue-detail-raw")).toBeNull();
    down.unmount();

    // 404
    renderIssues(<Harness initial="DEF-999-404" />, { stub: newStub({ overrides: { one: () => notFound("DEF-999-404") } }) });
    expect(await screen.findByTestId("issue-detail-error")).toHaveTextContent("查無此議題");
  });

  it("開啟時焦點移進面板；Esc 與關閉鈕都呼叫 onClose（焦點還給開啟者由呼叫端處理）", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderIssues(<Harness initial="OBS-SI-006" onClose={onClose} />);
    await screen.findByTestId("issue-detail-raw");
    expect(detail()).toHaveFocus();
    expect(detail()).toHaveAccessibleName("議題 OBS-SI-006 詳情");
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "關閉詳情" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
