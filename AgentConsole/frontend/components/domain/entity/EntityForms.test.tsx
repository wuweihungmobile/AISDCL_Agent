import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EXECUTION_PATH_HINT } from "@/components/domain/import/sourceRules";
import { ToastProvider } from "@/components/ui/toast";
import { ProjectForm } from "./EntityForms";
import { PROJECT_DEFAULTS } from "./schemas";

function renderProjectForm(over: Partial<Parameters<typeof ProjectForm>[0]> = {}) {
  return render(
    <ToastProvider>
      <ProjectForm mode="create" variant="page" defaultValues={PROJECT_DEFAULTS} onSubmit={vi.fn()} onCancel={vi.fn()} {...over} />
    </ToastProvider>,
  );
}

describe("專案表單的執行路徑欄（Architecture §12.1 L-8：本機與 Docker 全棧的寫法不同）", () => {
  it("欄位下方有兩種模式的說明：本機填主機路徑；Docker 全棧填 Bridge 容器內路徑，且須在 BRIDGE_ALLOWED_PATH_ROOTS 內", () => {
    renderProjectForm();
    // 沒有這行提示，使用者在 Docker 全棧下照本機習慣填主機路徑，要到執行時才被 Bridge 的 allowlist 擋下（OBS-SI-204）
    const hint = screen.getByText(EXECUTION_PATH_HINT);
    expect(hint).toHaveTextContent("本機開發填主機路徑");
    expect(hint).toHaveTextContent("Docker 全棧填 Bridge 容器內的路徑");
    expect(hint).toHaveTextContent("/workspace/");
    expect(hint).toHaveTextContent("BRIDGE_ALLOWED_PATH_ROOTS");
  });

  it("說明以 aria-describedby 連到輸入框，而不是塞進標籤：getByLabelText 仍可用精確的「執行路徑」取得輸入框", () => {
    renderProjectForm();
    const input = screen.getByLabelText("執行路徑");
    expect(input).toHaveAccessibleDescription(EXECUTION_PATH_HINT);
  });

  it("專案執行中（鎖定）：輸入框停用，說明仍在（唯讀情境也要看得到路徑語意）", () => {
    renderProjectForm({ mode: "edit", lockedToNameAndDescription: true });
    expect(screen.getByLabelText("執行路徑")).toBeDisabled();
    expect(screen.getByText(EXECUTION_PATH_HINT)).toBeInTheDocument();
  });
});
