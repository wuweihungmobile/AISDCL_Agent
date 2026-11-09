import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetProjectId, getLastProjectId, rememberProjectId } from "@/lib/nav/lastProject";
import { signIn } from "@/tests/helpers/api";
import { ProjectGoneState } from "./ProjectGoneState";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

/**
 * 專案不存在或已刪除畫面（DEF-AC-035；TCS-ExecMonitorEntry 勘誤 11 W-E7）：
 * AT_953_6_E_1（只清相等的 id；兩個去處依 kind；各角色畫面相同，沒有寫入動作與重試）。
 * 判定指令：npx vitest run components/domain/entry/ProjectGoneState.test.tsx
 */
afterEach(() => {
  forgetProjectId("Z");
  forgetProjectId("Y");
});

describe("AT_953_6_E_1 ProjectGoneState", () => {
  it("kind monitor、projectId Y、最近造訪 Z：兩連結 href 正確、最近造訪仍是 Z（只清相等的 id）", () => {
    rememberProjectId("Z");
    render(<ProjectGoneState kind="monitor" projectId="Y" />);
    const gone = screen.getByTestId("project-gone-state");
    expect(within(gone).getByRole("link", { name: "選擇其他專案" })).toHaveAttribute("href", "/monitor");
    expect(within(gone).getByRole("link", { name: "回專案管理" })).toHaveAttribute("href", "/projects");
    expect(getLastProjectId()).toBe("Z");
  });

  it("最近造訪就是這個 id：掛載即遺忘；kind execute 的入口連結指向 /execute", () => {
    rememberProjectId("Y");
    render(<ProjectGoneState kind="execute" projectId="Y" />);
    expect(screen.getByRole("link", { name: "選擇其他專案" })).toHaveAttribute("href", "/execute");
    expect(getLastProjectId()).toBeNull();
  });

  it.each(["VIEWER", "OPERATOR"] as const)("%s：畫面相同——只有兩個連結，沒有任何按鈕（無重試、無寫入動作）", (role) => {
    signIn(role, role.toLowerCase());
    render(<ProjectGoneState kind="execute" projectId="Y" />);
    expect(screen.getAllByRole("link").map((a) => a.textContent)).toEqual(["選擇其他專案", "回專案管理"]);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByText("專案不存在或已刪除")).toBeInTheDocument();
  });
});
