"use client";

/**
 * BRD/PRD 智能匯入（設計稿畫面 6；PRD §5.2；契約 §1.1、§4.1）。
 * 流程：步驟 1 輸入來源 →「開始解析」（建立匯入記錄＋同步解析，一次完成）→ 解析中 spinner →
 *       步驟 2 結構預覽與編輯 → signoff 審批 → 確認匯入（導到 /projects/[id]）。
 *
 * 目前操作的匯入記錄 id 放在網址（?id=…）：重新整理、從歷史重開都能還原同一個畫面
 * （GET /import/{id} 的 parsedResult 還原樹、lastParseErrors 還原有界閘清單；契約 §4.1 I-08／I-10）。
 */
import { CircleCheckBig, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { PageTitle } from "@/components/domain/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { Spinner } from "@/components/ui/spinner";
import { useToast } from "@/components/ui/toast";
import { ApiError, describeError } from "@/lib/api/client";
import { useImportDetail, useImportText, useParseImport, useSettingsCategory, useUploadImport } from "@/lib/api/queries";
import type { ParseWarning } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { parseFailureFromError, parseFailureFromRecord, type ParseFailure } from "./gateErrors";
import { SourceCard, type ParseRequest } from "./SourceCard";
import { StructureCard } from "./StructureCard";

/** 後端 400 的欄位錯誤（例：executionPath）→ 欄位名對訊息。 */
function fieldErrorsOf(error: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (error instanceof ApiError && error.status === 400) {
    for (const e of error.errors) if (!(e.field in out)) out[e.field] = e.message;
  }
  return out;
}

function clampLevel(value: string | undefined): number {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 && n <= 10 ? n : 3;
}

export function ImportView() {
  const router = useRouter();
  const id = useSearchParams().get("id") || undefined;
  const toast = useToast();
  const { canWrite } = useAuth();
  const detail = useImportDetail(id);
  const record = detail.data;
  const upload = useUploadImport();
  const importText = useImportText();
  const parse = useParseImport();
  // 預設自治等級＝設定 agent.defaultAutonomyLevel（契約 §4.1 I-04）；讀不到就用 3
  const agent = useSettingsCategory("agent");
  const defaultAutonomy = clampLevel(agent.data?.find((c) => c.key === "defaultAutonomyLevel")?.value);

  const [creating, setCreating] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<{ id: string; value: ParseFailure } | null>(null);
  const [warnings, setWarnings] = useState<{ id: string; items: ParseWarning[] } | null>(null);

  const openRecord = (rid: string) => router.replace(`/import?id=${rid}`);
  const startOver = () => {
    setFailure(null);
    setSourceError(null);
    setFieldErrors({});
    router.replace("/import");
  };

  async function start(request: ParseRequest) {
    setFailure(null);
    setSourceError(null);
    setFieldErrors({});
    setWarnings(null);

    let rid = id;
    const { source } = request;
    if (source.kind !== "existing") {
      setCreating(true);
      try {
        const created =
          source.kind === "file"
            ? await upload.mutateAsync(source.file)
            : await importText.mutateAsync({
                content: source.content,
                sourceFileName: source.sourceFileName,
                sourceType: source.sourceType,
              });
        rid = created.id;
        openRecord(created.id);
      } catch (e) {
        setSourceError(describeError(e));
        return;
      } finally {
        setCreating(false);
      }
    }
    if (!rid) return;

    try {
      const result = await parse.mutateAsync({ id: rid, options: request.options });
      setWarnings({ id: rid, items: result.warnings ?? [] });
      toast.success(`解析完成：${result.parsedResult.goals.length} 個目標，請檢視後 signoff`);
    } catch (e) {
      setFieldErrors(fieldErrorsOf(e));
      setFailure({ id: rid, value: parseFailureFromError(e) });
    }
  }

  const parsing = parse.isPending || record?.status === "PARSING";
  const status = record?.status;
  const hasTree = (status === "PARSED" || status === "REVIEWING") && Boolean(record?.parsedResult);
  // 失敗清單：本次操作的結果優先；沒有就用記錄上「最近一次被有界閘拒絕」的 lastParseErrors（重新整理／歷史重開後還原）
  const shownFailure = (failure && failure.id === id ? failure.value : null) ?? parseFailureFromRecord(record?.lastParseErrors);

  return (
    <div className="max-w-[960px]">
      <PageTitle
        title="BRD / PRD 智能匯入"
        subtitle={
          <>
            AI 解析需求文件 → 自動拆解三層結構 → <span aria-hidden className="mr-1 inline-block size-2 rounded-full bg-wg-accent align-middle" />
            人工 signoff 後落為正式專案
          </>
        }
      />

      {id && detail.isError && !record ? (
        <div className="mb-6">
          <ErrorState error={detail.error} onRetry={() => detail.refetch()} title="無法載入這份匯入記錄" />
          <Button className="mt-3" variant="ghost" onClick={startOver}>
            開始新的匯入
          </Button>
        </div>
      ) : null}

      {id && !record && detail.isLoading ? (
        <div aria-busy="true" aria-label="匯入記錄載入中" className="flex flex-col gap-4">
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : null}

      {parsing ? (
        <Card className="mb-6 flex flex-col items-center gap-4 px-6 py-14 text-center" data-testid="import-parsing">
          <Spinner size={40} label="AI 解析中" />
          <p className="text-[15px] font-medium">AI 解析中…（套用有界閘：步驟 ≤24 / Kahn 無環 / prompt 非空）</p>
          <p className="text-sm text-wg-muted">解析是同步作業，最長約 model.timeout 秒；請勿關閉此頁。</p>
        </Card>
      ) : null}

      {/*
        步驟 1 卡在解析期間只是隱藏、不卸載：解析若被有界閘擋下，使用者回來時執行路徑、自治等級、補充說明都還在，
        不必重打一遍（卸載會讓表單暫存全部消失）。解析成功後狀態轉 PARSED，這張卡才會真的卸載。
      */}
      {!id || record?.status === "UPLOADED" || parse.isPending ? (
        <div hidden={parsing}>
          <SourceCard
            existing={record?.status === "UPLOADED" ? record : null}
            canWrite={canWrite}
            busy={creating}
            defaultAutonomy={defaultAutonomy}
            failure={shownFailure}
            sourceError={sourceError}
            fieldErrors={fieldErrors}
            onStart={start}
            onLeaveExisting={startOver}
            onOpenFromHistory={openRecord}
          />
        </div>
      ) : null}

      {!parsing && record && hasTree ? (
        <StructureCard
          key={record.id}
          record={record}
          canWrite={canWrite}
          // 本次操作（解析／儲存編輯）的結果優先；沒有就用記錄上存的 warnings——重新整理或從歷史重開後黃色提示照樣在（C-10；契約 §1.1.9）
          warnings={warnings && warnings.id === record.id ? warnings.items : (record.warnings ?? [])}
          onWarnings={(items) => setWarnings({ id: record.id, items })}
          onDiscarded={startOver}
        />
      ) : null}

      {!parsing && record && (status === "IMPORTED" || status === "REJECTED") ? (
        <Card className="mb-6 flex flex-col items-start gap-3 p-6" data-testid="import-finished">
          <div className="flex items-center gap-2.5 text-[15px] font-medium">
            <CircleCheckBig size={22} className="text-wg-primary" aria-hidden />
            {status === "IMPORTED" ? "這份匯入已完成，專案已建立。" : "這份匯入已放棄，沒有建立任何專案。"}
          </div>
          <div className="flex flex-wrap gap-2.5">
            {status === "IMPORTED" && record.projectId ? (
              <Button asChild>
                <Link href={`/projects/${record.projectId}`}>前往專案</Link>
              </Button>
            ) : null}
            <Button variant="ghost" iconLeft={Plus} onClick={startOver}>
              開始新的匯入
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
