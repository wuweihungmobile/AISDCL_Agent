"use client";

/**
 * 專案不存在或已刪除的專屬畫面（DEF-AC-035、TCS-ExecMonitorEntry 勘誤 11 W-E7；掌舵者 2026-11-09 真機回報）：
 * 執行頁／監控頁對專案回 404 時顯示本元件，取代只能「重試」的一般錯誤卡——專案不存在時重試永遠失敗。
 * 給兩個去處：「選擇其他專案」（回入口頁 /execute 或 /monitor）與「回專案管理」（/projects）；沒有寫入動作，各角色畫面相同。
 * 掛載時遺忘這個 id（只在記住的就是它時才清），讓側欄不再指向已不存在的專案。
 */
import { useEffect } from "react";
import { FolderX } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { forgetProjectId } from "@/lib/nav/lastProject";

export function ProjectGoneState({ kind, projectId }: { kind: "execute" | "monitor"; projectId: string }) {
  useEffect(() => {
    forgetProjectId(projectId);
  }, [projectId]);

  return (
    <Card data-testid="project-gone-state" role="alert" className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <FolderX size={32} className="text-wg-muted" aria-hidden />
      <p className="text-[15px] font-medium text-wg-text">專案不存在或已刪除</p>
      <p className="text-sm text-wg-muted">這個專案已被刪除或封存，或網址不正確。</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
        <Button asChild>
          <Link href={`/${kind}`}>選擇其他專案</Link>
        </Button>
        <Button asChild variant="ghost">
          <Link href="/projects">回專案管理</Link>
        </Button>
      </div>
    </Card>
  );
}
