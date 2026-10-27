"use client";

/**
 * 頂列的「本頁說明」鈕（TCS-PageHelp-20261027 D-PH-4、C4；PRD §7、FR-PH-01）：全站一顆、同一個元件、`data-testid="page-help-open"`，由 TopRegion 在右側群組末端（通知鈴與待審批佇列之後）、
 * `showTools` 分支內渲染（登入頁與未登入自然不出現），並以 `next/dynamic` 載入：說明文字本體與對話框不進每條路由的首屏（D-PH-17）。
 *  - 無 props：`usePathname()`→`helpForPath`→`HELP_PAGES[id]`；路由沒有對應說明項、或說明項還在 `PENDING_HELP_PAGES`（沒有已寫的內容）＝不渲染；
 *  - 路由變更即關閉、重繪不關閉（開在 A、走到 B、再回 A，仍是關閉）：外層取 pathname，以 `key={pathname}` 重掛載內層——內層持有開關狀態與對話框，
 *    路由一變內層整個重建、開關回到關閉。**不用** effect 內同步 `setState`（repo 的 `react-hooks/set-state-in-effect` 為 error），
 *    也**不用**「記住開在哪個路徑再比對」的衍生寫法（A→B→A 會誤重開）；
 *  - 名稱來自文字節點「本頁說明」（`max-md:sr-only`：< 768 只剩圖示、名稱不變），圖示 `BookOpen`（`aria-hidden`）；不另設 `aria-label`——可見文字與名稱一致（Label in Name）；
 *    與公告列靜態字樣「幫助中心」區別：圖示與鈕名都不同，那是不可點的字樣；
 *  - 顏色：白底主色字（`bg-white`、`text-wg-primary`，主色字在白底約 4.55:1）；不得用半透明底上的白字（約 3.5:1，低於 4.5:1）；焦點環沿用全域 `:focus-visible`。
 */
import { BookOpen } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { HELP_PAGES, helpForPath } from "@/lib/help/registry";
import type { PageHelp } from "@/lib/help/types";
import { PageHelpDialog } from "./PageHelpDialog";

/** 內層：開關狀態與對話框；外層以 `key={pathname}` 重掛載它，所以路由一變就回到關閉。 */
function PageHelpControl({ page }: { page: PageHelp }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        data-testid="page-help-open"
        onClick={() => setOpen(true)}
        className="inline-flex h-11 shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-full border-none bg-white px-4 text-sm font-medium whitespace-nowrap text-wg-primary transition-opacity hover:opacity-85 max-md:w-11 max-md:px-0"
      >
        <BookOpen size={20} aria-hidden />
        <span className="max-md:sr-only">本頁說明</span>
      </button>
      <PageHelpDialog page={page} open={open} onOpenChange={setOpen} />
    </>
  );
}

export function PageHelpButton() {
  const pathname = usePathname();
  const id = helpForPath(pathname);
  const page = id === null ? undefined : HELP_PAGES[id];
  if (page === undefined) return null;
  return <PageHelpControl key={pathname} page={page} />;
}
