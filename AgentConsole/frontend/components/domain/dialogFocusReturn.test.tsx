import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { ReviewCard } from "@/components/domain/execute/ReviewCard";
import { Providers, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { reviewItem } from "@/tests/helpers/runFixtures";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// Markdown 編輯器本體很重且與焦點歸還無關：換成 textarea
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} />,
}));

/**
 * DEF-AC-011（P3，WCAG 2.4.3 焦點順序）：「以頁面狀態（open／target）控制開啟」的對話框，關閉後焦點要回到開啟它的按鈕。
 * 根因：Radix DialogContent 的 onCloseAutoFocus 一律 preventDefault 再 focus() 它自己的 DialogTrigger（triggerRef）；
 * 本專案沒有任何 DialogTrigger，triggerRef 恆為 null，焦點就掉到 <body>（QA_W5_Reverification §4.5）。
 * 修在共用層 components/ui/dialog.tsx；這裡用真實元件（不是替身）逐一驗證四個已知對話框，各走三條關閉路徑。
 */
const CLOSERS = ["Esc", "右上角關閉鈕", "取消鈕"] as const;
type Closer = (typeof CLOSERS)[number];

/** 觸發鈕聚焦 → Enter 開 → 焦點進入對話框 → 以指定方式關 → 焦點應回到觸發鈕 */
async function openThenClose(trigger: HTMLElement, dialogName: string | RegExp, how: Closer) {
  const user = userEvent.setup();
  trigger.focus();
  expect(trigger).toHaveFocus();
  await user.keyboard("{Enter}");
  const dialog = await screen.findByRole("dialog", { name: dialogName });
  await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement)); // Radix 已把焦點搬進對話框
  expect(trigger).not.toHaveFocus();
  if (how === "Esc") await user.keyboard("{Escape}");
  else await user.click(within(dialog).getByRole("button", { name: how === "取消鈕" ? "取消" : "關閉" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(trigger).toHaveFocus()); // FocusScope 在卸載後的 setTimeout(0) 才發 onCloseAutoFocus
}

beforeEach(() => signIn("OPERATOR", "operator"));

describe("DEF-AC-011：對話框關閉後焦點回到觸發的按鈕（真實元件）", () => {
  describe.each(CLOSERS)("以「%s」關閉", (how) => {
    it("刪除專案確認（ConfirmDialog）：焦點回到「刪除專案」鈕", async () => {
      function Page() {
        const [open, setOpen] = useState(false);
        return (
          <>
            <button type="button" onClick={() => setOpen(true)}>
              刪除專案
            </button>
            <ConfirmDialog open={open} title="刪除專案" confirmLabel="確認刪除" onClose={() => setOpen(false)} onConfirm={async () => {}}>
              確定刪除專案？
            </ConfirmDialog>
          </>
        );
      }
      render(<Page />);
      await openThenClose(screen.getByRole("button", { name: "刪除專案" }), "刪除專案", how);
    });

    it("新建專案（EntityDialog，kind=project）：焦點回到「新建專案」鈕", async () => {
      function Page() {
        const [target, setTarget] = useState<EntityTarget | null>(null);
        return (
          <>
            <button type="button" onClick={() => setTarget({ kind: "project", mode: "create" })}>
              新建專案
            </button>
            <EntityDialog target={target} onClose={() => setTarget(null)} />
          </>
        );
      }
      stubApi(() => undefined);
      render(
        <Providers client={makeClient()}>
          <Page />
        </Providers>,
      );
      await openThenClose(screen.getByRole("button", { name: "新建專案" }), "新建專案", how);
    });

    it("新增目標（EntityDialog，kind=goal）：焦點回到「新增目標」鈕", async () => {
      function Page() {
        const [target, setTarget] = useState<EntityTarget | null>(null);
        return (
          <>
            <button type="button" onClick={() => setTarget({ kind: "goal", mode: "create", projectId: "p1" })}>
              新增目標
            </button>
            <EntityDialog target={target} onClose={() => setTarget(null)} />
          </>
        );
      }
      stubApi((c) => (c.method === "GET" && c.path === "/api/v1/projects/p1/goals" ? { data: [] } : undefined));
      render(
        <Providers client={makeClient()}>
          <Page />
        </Providers>,
      );
      await openThenClose(screen.getByRole("button", { name: "新增目標" }), "新建目標", how);
    });

    it("審核確認（ReviewCard）：焦點回到該列的「通過」鈕", async () => {
      render(
        <Providers client={makeClient()}>
          <ReviewCard projectId="p1" reviews={[reviewItem()]} canWrite onDecide={async () => {}} />
        </Providers>,
      );
      await openThenClose(screen.getByTestId("review-approve"), /^通過：/, how);
    });
  });
});
