"use client";

/**
 * 自我進化（SelfImproving）頁（P1b 唯讀鏡像：TCS-SelfImprovingMirror-P1b R12～R19、PRD AC-SI-32-1～4；P2b 寫入載體：TCS-SelfImprovingDecide-P2b W18～W21、PRD AC-SI-33、35）：
 * 頁面資料＝根層 `si export` 的輸出，經 Bridge 子行程與 console-api 原樣（只改欄名）轉到這裡；Console 是顯示面，不是資料來源。
 *
 * 設計要點（為什麼這樣做）：
 *  - 每個資料面板各自取數、各自有 loading／error／ok 三態（狀態橫幅一個查詢、目前分頁的清單一個、事件分頁另有運轉查詢）：
 *    任何一個失敗都只顯示該面板的錯誤態與原因，絕不渲染成空表、零筆、「無事件」或「通過」，也不渲染過期資料（SI 查詢不重試、不留快取）。
 *  - **Console 不寫帳本**：P1b 沒有任何非 GET 請求；P2b 起只有 ADMIN 看得到寫入入口（決定、新增觀察、更正、關閉、恢復），它們只把「簽好章的稽核檔」落到主機端的目錄，
 *    入帳由掌舵者在主機端用根層 CLI 做（pull 模式）。非 ADMIN：零控件、零 POST、零 `console-writes` 請求、沒有待入帳或警示字樣。是否在決定者名單由 backend 判（403 原因逐字 toast）。
 *  - 三個寫入對話框掛在這一層（不掛在各面板裡）：面板因重新整理或分頁切換卸載時，對話框與它已顯示的收據不會跟著消失；內容元件隨對話框卸載，所以關閉後重開不沿用上次結果。
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
import { useAuth } from "@/lib/auth/AuthProvider";
import { SiDecideDialog, type DecideTarget } from "./SiDecideDialog";
import { SiEventsPanel } from "./SiEventsPanel";
import { SiObsCloseDialog, type CloseTarget } from "./SiObsCloseDialog";
import { SiObsForm, type ObsFormTarget } from "./SiObsForm";
import { SiObservationsPanel } from "./SiObservationsPanel";
import { SiProposalsPanel } from "./SiProposalsPanel";
import { SiStatusBanner } from "./SiStatusBanner";
import { SiWritesPanel } from "./SiWritesPanel";

type SiTab = "observations" | "proposals" | "events";

const TABS: ReadonlyArray<{ id: SiTab; label: string }> = [
  { id: "observations", label: "觀察" },
  { id: "proposals", label: "提案" },
  { id: "events", label: "事件" },
];
const ID_BASE = "si-tab";

export function SiView() {
  const queryClient = useQueryClient();
  const { role } = useAuth();
  /** 寫入入口只對 ADMIN 渲染（W21）；帳號是否在 deciders 名單由 backend 判，前端沒有「我是否在名單」的端點。 */
  const isAdmin = role === "ADMIN";
  const [tab, setTab] = useState<SiTab>("observations");
  // 目前分頁的面板在 ok 態時回報的筆數字樣（例 `(12)`、`(5+)`）；其他分頁與非 ok 態為 null，標籤不帶筆數
  const [count, setCount] = useState<string | null>(null);
  const [decideTarget, setDecideTarget] = useState<DecideTarget | null>(null);
  const [obsTarget, setObsTarget] = useState<ObsFormTarget | null>(null);
  const [closeTarget, setCloseTarget] = useState<CloseTarget | null>(null);

  return (
    <div data-testid="si-view">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-[30px] font-bold max-md:text-2xl">
            <Dna size={26} className="shrink-0 text-wg-primary" aria-hidden />
            自我進化
          </h1>
          <p className="mt-1 text-[15px] text-wg-muted">
            {isAdmin
              ? "鏡像：畫面內容逐欄來自根層 si export 的輸出；Console 不寫入帳本——您的決定與新增觀察只落稽核檔，由主機端 CLI 驗簽入帳。"
              : "唯讀鏡像：畫面內容逐欄來自根層 si export 的輸出，Console 不寫入帳本。"}
          </p>
        </div>
        <Button variant="ghost" iconLeft={RefreshCw} data-testid="si-refresh" onClick={() => void queryClient.refetchQueries({ queryKey: qk.siAll, type: "active" })}>
          重新整理
        </Button>
      </div>

      <SiStatusBanner onResume={isAdmin ? (run) => setDecideTarget({ kind: "run", run }) : undefined} />

      {isAdmin ? <SiWritesPanel /> : null}

      <PillTabs
        label="自我進化資料"
        idBase={ID_BASE}
        tabs={TABS.map((t) => ({ id: t.id, label: t.id === tab && count ? `${t.label} ${count}` : t.label }))}
        value={tab}
        onChange={setTab}
        className="mb-4"
      />

      <Card role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)} data-testid={`si-panel-${tab}`} className="px-5 py-4">
        {tab === "observations" ? (
          <SiObservationsPanel
            onCount={setCount}
            actions={
              isAdmin
                ? {
                    onNew: () => setObsTarget({ mode: "new" }),
                    onCorrect: (id) => setObsTarget({ mode: "correct", corrects: id }),
                    onCloseObservation: (id) => setCloseTarget({ obsId: id }),
                  }
                : undefined
            }
          />
        ) : tab === "proposals" ? (
          <SiProposalsPanel onCount={setCount} onDecide={isAdmin ? (proposal) => setDecideTarget({ kind: "prop", proposal }) : undefined} />
        ) : (
          <SiEventsPanel onCount={setCount} />
        )}
      </Card>

      {isAdmin ? (
        <>
          <SiDecideDialog target={decideTarget} onClose={() => setDecideTarget(null)} />
          <SiObsForm target={obsTarget} onClose={() => setObsTarget(null)} />
          <SiObsCloseDialog target={closeTarget} onClose={() => setCloseTarget(null)} />
        </>
      ) : null}
    </div>
  );
}
