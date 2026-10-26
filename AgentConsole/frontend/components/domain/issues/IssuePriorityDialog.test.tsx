/**
 * IssuePriorityDialog 的元件測試（TCS-IssueCenter-20261027 AT-IC-09-9-2、AT-IC-09-9-E-1、AT-IC-12-5-E-1；R-IC-70、R-IC-74）：
 * ADMIN 在議題中心頁對可排的列設定／清除優先順序——排序鈕只在可排的列、儲存＝PUT 清除＝DELETE、**以回應為準重排（不樂觀）**、
 * 表單先擋 backend 必拒的形態並就地說明、對話框的鍵盤與 aria。整頁以 IssuesView 渲染，資料來自 issues.fixtures.ts 的假後端（PUT、DELETE 有狀態）。
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { failure } from "@/tests/helpers/api";
import { IssuesView } from "./IssuesView";
import { newStub, renderIssues, unavailable, type IssuesStub } from "./tests/issues.fixtures";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身（頁面本身不導覽）
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/issues",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// 待處理分頁（第一條規則、尚無任何順位）的列序：緊急的最前；高嚴重度中較舊的在前；嚴重度量不到的排最後（日期 null 更後）
const PENDING_ORDER = ["OBS-SI-006", "DEF-999-005", "OBS-SI-007", "OBS-SI-008", "OBS-SI-009"];

const dialog = () => screen.getByTestId("issue-priority-dialog");
const rankInput = () => screen.getByTestId("issue-priority-rank") as HTMLInputElement;
const noteInput = () => screen.getByTestId("issue-priority-note") as HTMLInputElement;
const saveButton = () => screen.getByTestId("issue-priority-save");
const rowIds = () => Array.from(document.querySelectorAll<HTMLElement>('[data-testid^="issue-row-"]')).map((el) => (el.dataset.testid as string).replace("issue-row-", ""));
const puts = (stub: IssuesStub) => stub.calls.filter((c) => c.method === "PUT");
const deletes = (stub: IssuesStub) => stub.calls.filter((c) => c.method === "DELETE");

async function renderAdmin(stub = newStub()) {
  const user = userEvent.setup();
  const view = renderIssues(<IssuesView />, { role: "ADMIN", stub });
  await screen.findByTestId("issues-table");
  return { user, stub, view };
}

describe("AT_IC_09_9_2 ADMIN 設定與清除優先順序", () => {
  it("AT_IC_09_9_2 排序鈕只在可排的列；儲存＝PUT、清除＝DELETE；請求送出到回應回來之前列序與順位欄都不動（不樂觀），回應回來後依回應重排", async () => {
    // PUT 由測試控制何時回應：回應之前什麼都不能變
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const stub = newStub({ overrides: { put: () => gate.then(() => undefined) } });
    const { user } = await renderAdmin(stub);

    // 只有可排的四列有「排序」鈕；不可排的 OBS-SI-008 沒有，順位欄空白
    expect(screen.getAllByRole("button", { name: /^排序 / }).map((b) => b.getAttribute("aria-label"))).toEqual(["排序 OBS-SI-006", "排序 DEF-999-005", "排序 OBS-SI-007", "排序 OBS-SI-009"]);
    expect(screen.queryByTestId("issue-priority-open-OBS-SI-008")).toBeNull();
    expect(within(screen.getByTestId("issue-row-OBS-SI-008")).getAllByRole("cell")[5].textContent).toBe("");
    expect(rowIds()).toEqual(PENDING_ORDER);

    // 對最後一列設定順位 1 與備註
    await user.click(screen.getByTestId("issue-priority-open-OBS-SI-009"));
    expect(screen.getByRole("dialog", { name: "優先順序：OBS-SI-009" })).toBeInTheDocument();
    expect(rankInput().value).toBe("");
    expect(noteInput().value).toBe("");
    expect(screen.getByTestId("issue-priority-clear")).toBeDisabled(); // 目前沒有順位，沒有東西可清
    await user.type(rankInput(), "1");
    await user.type(noteInput(), "先做");
    await user.click(saveButton());

    // 回應之前：請求已送出、對話框還在、列序與順位欄不動
    await waitFor(() => expect(puts(stub)).toHaveLength(1));
    expect(dialog()).toBeInTheDocument();
    expect(rowIds()).toEqual(PENDING_ORDER);
    expect(screen.queryByTestId("issue-priority-OBS-SI-009")).toBeNull();
    expect(saveButton()).toBeDisabled();

    // 回應回來：對話框關閉、該列依回應的順位排到最前並顯示順位與備註
    await act(async () => release());
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());
    await waitFor(() => expect(rowIds()[0]).toBe("OBS-SI-009"));
    expect(rowIds()).toEqual(["OBS-SI-009", "OBS-SI-006", "DEF-999-005", "OBS-SI-007", "OBS-SI-008"]);
    expect(screen.getByTestId("issue-priority-OBS-SI-009").textContent).toBe("1");
    expect(screen.getByTestId("issue-priority-note-OBS-SI-009").textContent).toBe("先做");
    expect(puts(stub)[0].path).toBe("/api/v1/issues/OBS-SI-009/priority");
    expect(JSON.parse(puts(stub)[0].body as string)).toEqual({ rank: 1, note: "先做" });
    expect(screen.getByText("已儲存 OBS-SI-009 的優先順序")).toBeInTheDocument();

    // 再開同一列：預填目前的順位與備註；清除＝DELETE，回應（204）回來後該列回到原位、順位欄顯示「—」
    await user.click(screen.getByTestId("issue-priority-open-OBS-SI-009"));
    expect(rankInput().value).toBe("1");
    expect(noteInput().value).toBe("先做");
    await user.click(screen.getByTestId("issue-priority-clear"));
    await waitFor(() => expect(deletes(stub)).toHaveLength(1));
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());
    await waitFor(() => expect(rowIds()).toEqual(PENDING_ORDER));
    expect(deletes(stub)[0].path).toBe("/api/v1/issues/OBS-SI-009/priority");
    expect(screen.queryByTestId("issue-priority-OBS-SI-009")).toBeNull();
    expect(within(screen.getByTestId("issue-row-OBS-SI-009")).getAllByRole("cell")[5]).toHaveTextContent("—");
    expect(puts(stub)).toHaveLength(1);
  });

  it("儲存失敗：409（議題狀態已不可排）以逐字訊息顯示在對話框內、對話框不關、列序不動；503 顯示原因；送出中不能連點", async () => {
    const stub = newStub({
      overrides: {
        put: (call) =>
          call.path.includes("OBS-SI-007") ? unavailable() : failure(409, { message: "服務端的另一句話", reason: "issue_not_rankable", details: { id: "OBS-SI-006", status: "已完成" } }),
      },
    });
    const { user } = await renderAdmin(stub);
    await user.click(screen.getByTestId("issue-priority-open-OBS-SI-006"));
    await user.type(rankInput(), "3");
    await user.click(saveButton());
    expect(await screen.findByTestId("issue-priority-error")).toHaveTextContent("此議題目前的狀態不能設定優先順序");
    expect(screen.getByTestId("issue-priority-error")).not.toHaveTextContent("服務端的另一句話");
    expect(dialog()).toBeInTheDocument();
    expect(rowIds()).toEqual(PENDING_ORDER);
    expect(puts(stub)).toHaveLength(1);
    // 再試一次（失敗後按鈕恢復可按）
    await user.click(saveButton());
    await waitFor(() => expect(puts(stub)).toHaveLength(2));
    await user.click(screen.getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());

    // 503：原因逐字
    await user.click(screen.getByTestId("issue-priority-open-OBS-SI-007"));
    await user.type(rankInput(), "2");
    await user.click(saveButton());
    expect(await screen.findByTestId("issue-priority-error")).toHaveTextContent("SI 資料面不可用：si_unavailable");
  });
});

describe("AT_IC_09_9_E_1 不可排的列與表單驗證", () => {
  it("AT_IC_09_9_E_1 不可排的列沒有排序鈕、順位欄不顯示遺留順位，也不因它而改變列序", async () => {
    const stub = newStub();
    const legacy = stub.items.find((i) => i.id === "OBS-SI-008");
    if (!legacy) throw new Error("夾具缺 OBS-SI-008");
    legacy.priority = 1;
    legacy.priorityNote = "遺留的備註";
    await renderAdmin(stub);
    expect(screen.queryByTestId("issue-priority-open-OBS-SI-008")).toBeNull();
    expect(screen.queryByTestId("issue-priority-OBS-SI-008")).toBeNull();
    expect(screen.queryByTestId("issue-priority-note-OBS-SI-008")).toBeNull();
    expect(screen.getByTestId("issue-row-OBS-SI-008")).not.toHaveTextContent("遺留的備註");
    expect(within(screen.getByTestId("issue-row-OBS-SI-008")).getAllByRole("cell")[5].textContent).toBe("");
    expect(rowIds()).toEqual(PENDING_ORDER);
  });

  it("AT_IC_09_9_E_1 順位 0、10000、1.5、全形「１２」、「1e3」與備註 201 個 code point 被表單驗證擋下：不送請求、就地說明；「 12 」（前後空白）與恰 200 個 code point 的備註通過", async () => {
    const { user, stub } = await renderAdmin();
    await user.click(screen.getByTestId("issue-priority-open-OBS-SI-006"));
    for (const bad of ["0", "10000", "1.5", "１２", "1e3", "-3", "abc"]) {
      fireEvent.change(rankInput(), { target: { value: bad } });
      expect(screen.getByTestId("issue-priority-blocked"), bad).toHaveTextContent("尚不能送出：順位須為 1～9999 的整數");
      expect(
        within(dialog())
          .getAllByRole("alert")
          .some((el) => el.textContent?.includes("順位須為")),
        `${bad} 的就地說明`,
      ).toBe(true);
      expect(saveButton(), bad).toBeDisabled();
      await user.click(saveButton()); // 停用的按鈕點了沒有任何請求
    }
    fireEvent.change(rankInput(), { target: { value: "" } });
    expect(screen.getByTestId("issue-priority-blocked")).toHaveTextContent("順位為必填");
    expect(saveButton()).toBeDisabled();

    // 備註 201 個字被擋、全形與表情符號各算 1 個；200 個通過
    fireEvent.change(rankInput(), { target: { value: "5" } });
    fireEvent.change(noteInput(), { target: { value: "字".repeat(201) } });
    expect(screen.getByTestId("issue-priority-blocked")).toHaveTextContent("備註為 201 個字元，超過上限 200");
    expect(saveButton()).toBeDisabled();
    fireEvent.change(noteInput(), { target: { value: "😀".repeat(201) } });
    expect(saveButton()).toBeDisabled();
    expect(puts(stub)).toHaveLength(0);

    fireEvent.change(rankInput(), { target: { value: " 12 " } });
    fireEvent.change(noteInput(), { target: { value: "😀".repeat(200) } });
    expect(screen.queryByTestId("issue-priority-blocked")).toBeNull();
    expect(saveButton()).toBeEnabled();
    await user.click(saveButton());
    await waitFor(() => expect(puts(stub)).toHaveLength(1));
    expect(JSON.parse(puts(stub)[0].body as string)).toEqual({ rank: 12, note: "😀".repeat(200) });
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());
  });
});

describe("AT_IC_12_5_E_1 排序對話框的鍵盤與 aria", () => {
  it("AT_IC_12_5_E_1 Tab 焦點循環困在對話框內；分頁、對話框、輸入與按鈕皆有 aria 名稱；Esc 關閉並把焦點還給「排序」鈕", async () => {
    const { user } = await renderAdmin();
    // 頁面上的分頁與按鈕以名稱取得
    expect(screen.getByRole("tablist", { name: "議題分頁" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "待處理" })).toHaveAttribute("aria-selected", "true");
    const trigger = screen.getByRole("button", { name: "排序 OBS-SI-006" });
    await user.click(trigger);

    const root = screen.getByRole("dialog", { name: "優先順序：OBS-SI-006" });
    expect(within(root).getByRole("textbox", { name: /順位/ })).toBeInTheDocument();
    expect(within(root).getByRole("textbox", { name: /備註/ })).toBeInTheDocument();
    for (const name of ["儲存", "取消", "清除順位", "關閉"]) expect(within(root).getByRole("button", { name })).toBeInTheDocument();
    expect(rankInput()).toHaveFocus(); // 開啟時焦點落在第一個欄位

    // 填好順位讓儲存鈕可按，再連按 Tab、Shift+Tab：焦點始終在對話框內，且每個可操作的控制項都輪得到
    await user.type(rankInput(), "4");
    const seen = new Set<string>();
    for (let i = 0; i < 12; i++) {
      await user.tab();
      expect(root.contains(document.activeElement), `Tab 第 ${i + 1} 次`).toBe(true);
      seen.add(document.activeElement?.getAttribute("data-testid") ?? document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent ?? "");
    }
    for (let i = 0; i < 12; i++) {
      await user.tab({ shift: true });
      expect(root.contains(document.activeElement), `Shift+Tab 第 ${i + 1} 次`).toBe(true);
    }
    expect([...seen]).toEqual(expect.arrayContaining(["issue-priority-rank", "issue-priority-note", "取消", "issue-priority-save", "關閉"]));

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());
    expect(trigger).toHaveFocus();
  });
});
