"use client";

/**
 * 自我進化（SelfImproving）唯讀鏡像頁（P1b；TCS-SelfImprovingMirror-P1b R12～R19；PRD AC-SI-32-1～4）：
 * 頁面資料＝根層 `si export` 的輸出，經 Bridge 子行程與 console-api 原樣（只改欄名）轉到這裡；Console 是顯示面，不是資料來源。
 *
 * 設計要點（為什麼這樣做）：
 *  - 每個資料面板各自取數、各自有 loading／error／ok 三態（狀態橫幅一個查詢、目前分頁的清單一個、事件分頁另有運轉查詢）：
 *    任何一個失敗都只顯示該面板的錯誤態與原因，絕不渲染成空表、零筆、「無事件」或「通過」，也不渲染過期資料（SI 查詢不重試、不留快取）。
 *  - 零寫入：沒有表單、沒有 mutation、沒有任何非 GET 的請求；唯一的「動作」是重新抓取（重新整理、重試、載入更多）。
 *  - 純文字：帳本字串（九欄、marks、卡面、事件 JSON、ne／problems）一律以 React 文字節點渲染，不經 HTML 或 Markdown，
 *    含 `<script>` 與 Markdown 語法的候選列原樣顯示為字面文字。
 *  - 只有目前分頁的面板掛載：切分頁即卸載舊面板（gcTime 為 0，資料隨之丟棄），回到該分頁時重新載入，不顯示上一次的資料。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Dna, RefreshCw } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { pillPanelId, pillTabId, PillTabs } from "@/components/ui/pill-tabs";
import { qk } from "@/lib/api/queries";
import { SiEventsPanel } from "./SiEventsPanel";
import { SiObservationsPanel } from "./SiObservationsPanel";
import { SiProposalsPanel } from "./SiProposalsPanel";
import { SiStatusBanner } from "./SiStatusBanner";

type SiTab = "observations" | "proposals" | "events";

const TABS: ReadonlyArray<{ id: SiTab; label: string }> = [
  { id: "observations", label: "觀察" },
  { id: "proposals", label: "提案" },
  { id: "events", label: "事件" },
];
const ID_BASE = "si-tab";

export function SiView() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<SiTab>("observations");
  // 目前分頁的面板在 ok 態時回報的筆數字樣（例 `(12)`、`(5+)`）；其他分頁與非 ok 態為 null，標籤不帶筆數
  const [count, setCount] = useState<string | null>(null);

  return (
    <div data-testid="si-view">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-[30px] font-bold max-md:text-2xl">
            <Dna size={26} className="shrink-0 text-wg-primary" aria-hidden />
            自我進化
          </h1>
          <p className="mt-1 text-[15px] text-wg-muted">唯讀鏡像：畫面內容逐欄來自根層 si export 的輸出，Console 不寫入帳本。</p>
        </div>
        <Button variant="ghost" iconLeft={RefreshCw} data-testid="si-refresh" onClick={() => void queryClient.refetchQueries({ queryKey: qk.siAll, type: "active" })}>
          重新整理
        </Button>
      </div>

      <SiStatusBanner />

      <PillTabs
        label="自我進化資料"
        idBase={ID_BASE}
        tabs={TABS.map((t) => ({ id: t.id, label: t.id === tab && count ? `${t.label} ${count}` : t.label }))}
        value={tab}
        onChange={setTab}
        className="mb-4"
      />

      <Card role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)} data-testid={`si-panel-${tab}`} className="px-5 py-4">
        {tab === "observations" ? <SiObservationsPanel onCount={setCount} /> : tab === "proposals" ? <SiProposalsPanel onCount={setCount} /> : <SiEventsPanel onCount={setCount} />}
      </Card>
    </div>
  );
}
