"use client";

/**
 * 步驟 1 卡「輸入來源」（設計稿畫面 6；US-I-01／02／05／06／07／08）：
 * 來源 tab（檔案上傳／貼上文字／歷史記錄）、拖放區、自治等級、執行路徑（等寬）、補充說明、「開始解析」。
 * 兩種模式：
 *  - 新來源（沒有記錄）：選檔或貼文字，按「開始解析」時才建立匯入記錄並解析（一次完成兩個呼叫）；
 *  - 沿用既有記錄（status=UPLOADED：從歷史重開，或解析被有界閘拒絕後）：來源已定，只調整解析選項後重試；
 *    要改來源文字時按「改用其他來源」，原文會帶回「貼上文字」供修改。
 */
import { ClipboardPaste, CloudUpload, FileText, FileUp, History, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { PillTabs, pillPanelId, pillTabId } from "@/components/ui/pill-tabs";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ABSOLUTE_PATH } from "@/components/domain/entity/schemas";
import type { ImportRecordDetail, ImportSourceType, ParseOptions } from "@/lib/api/types";
import { formatBytes, formatDateTime, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ParseFailure } from "./gateErrors";
import { HistoryPanel } from "./HistoryPanel";
import { ParseFailurePanel, StepHeader } from "./parts";
import {
  ALLOWED_EXTENSIONS,
  EXECUTION_PATH_HINT,
  MAX_ADDITIONAL_PROMPT_CHARS,
  MAX_TEXT_CHARS,
  validateSourceFile,
} from "./sourceRules";

export type SourcePayload =
  | { kind: "file"; file: File }
  | { kind: "text"; content: string; sourceFileName?: string; sourceType: "PLAIN_TEXT" | "MARKDOWN" }
  | { kind: "existing" };

export type ParseRequest = { source: SourcePayload; options: ParseOptions };

type SourceTab = "file" | "text" | "history";

const TABS = [
  { id: "file", label: "上傳檔案", icon: FileUp },
  { id: "text", label: "貼上文字", icon: ClipboardPaste },
  { id: "history", label: "歷史記錄", icon: History },
] as const;

const SOURCE_TYPE_LABEL: Record<ImportSourceType, string> = {
  MARKDOWN: "Markdown",
  PDF: "PDF",
  DOCX: "Word",
  PLAIN_TEXT: "純文字",
};

const ID_BASE = "import-source";
const LEVELS = Array.from({ length: 10 }, (_, i) => i + 1);

export function SourceCard({
  existing,
  canWrite,
  busy,
  defaultAutonomy,
  failure,
  sourceError,
  fieldErrors,
  onStart,
  onLeaveExisting,
  onOpenFromHistory,
}: {
  /** 已建立、尚未解析成功的記錄（status=UPLOADED）；null＝新來源模式 */
  existing: ImportRecordDetail | null;
  canWrite: boolean;
  /** 建立記錄（上傳）或解析進行中 */
  busy: boolean;
  /** 設定 agent.defaultAutonomyLevel（讀不到時為 3） */
  defaultAutonomy: number;
  /** 上一次解析失敗（標題＋逐項清單） */
  failure: ParseFailure | null;
  /** 建立記錄階段的失敗說明（413／415／422…，含契約 reason） */
  sourceError: string | null;
  /** 後端 400 的欄位錯誤（例：executionPath） */
  fieldErrors: Record<string, string>;
  onStart: (request: ParseRequest) => void;
  /** 離開沿用模式（清掉目前記錄）；原文由本元件先放進「貼上文字」 */
  onLeaveExisting: () => void;
  onOpenFromHistory: (id: string) => void;
}) {
  const [tab, setTab] = useState<SourceTab>("file");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState<"PLAIN_TEXT" | "MARKDOWN">("PLAIN_TEXT");
  const [executionPath, setExecutionPath] = useState("");
  const [autonomy, setAutonomy] = useState<number | null>(null);
  const [additional, setAdditional] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  /** 最近一次按「開始解析」時所在的 tab：建立記錄階段的失敗說明只顯示在那個 tab，切走就不跟過去 */
  const [startedTab, setStartedTab] = useState<SourceTab | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const writeHint = canWrite ? undefined : "權限不足（唯讀角色）";

  function chooseFile(next: File | undefined) {
    if (!next) return;
    const reason = validateSourceFile(next);
    setErrors((e) => ({ ...e, source: "" }));
    if (reason) {
      setFile(null);
      setFileError(reason);
      return;
    }
    setFileError(null);
    setFile(next);
  }

  function start() {
    setStartedTab(tab);
    const next: Record<string, string> = {};
    let source: SourcePayload = { kind: "existing" };
    if (!existing) {
      if (tab === "text") {
        if (!text.trim()) next.source = "請貼上需求文字";
        else if (text.length > MAX_TEXT_CHARS) next.source = `文字超過 ${formatNumber(MAX_TEXT_CHARS)} 字元上限`;
        source = {
          kind: "text",
          content: text,
          sourceFileName: sourceName.trim() || undefined,
          sourceType,
        };
      } else if (tab === "file") {
        if (!file) next.source = fileError ?? "請選擇要上傳的檔案";
        else source = { kind: "file", file };
      } else {
        next.source = "請先到「上傳檔案」或「貼上文字」提供來源";
      }
    }
    const path = executionPath.trim();
    if (!path) next.executionPath = "執行路徑不能為空";
    else if (path.length > 500) next.executionPath = "執行路徑最多 500 個字元";
    else if (!ABSOLUTE_PATH.test(path)) {
      next.executionPath = "執行路徑必須是絕對路徑（POSIX 以 / 開頭，或 Windows 磁碟機代號／UNC 開頭）";
    }
    if (additional.length > MAX_ADDITIONAL_PROMPT_CHARS) {
      next.additionalPrompt = `補充說明最多 ${formatNumber(MAX_ADDITIONAL_PROMPT_CHARS)} 字元`;
    }
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    onStart({
      source,
      options: {
        autonomyLevel: autonomy ?? defaultAutonomy,
        executionPath: path,
        additionalPrompt: additional.trim() || undefined,
      },
    });
  }

  function leaveExisting() {
    if (existing) {
      // 原文（檔案則是後端擷取出的文字）帶回「貼上文字」，讓使用者修改後以新記錄重新解析
      setText(existing.sourceContent);
      setSourceName(existing.sourceFileName ?? "");
      setSourceType(existing.sourceType === "MARKDOWN" ? "MARKDOWN" : "PLAIN_TEXT");
      setFile(null);
      setFileError(null);
      setTab("text");
    }
    onLeaveExisting();
  }

  const effectiveAutonomy = autonomy ?? defaultAutonomy;
  const sourceMessage =
    errors.source || (tab === "file" ? fileError : null) || (startedTab === tab ? sourceError : null);

  const existingPanel = existing ? (
    <div data-testid="existing-source" className="rounded-md border border-wg-line bg-wg-base p-4">
      <div className="flex flex-wrap items-center gap-2">
        <FileText size={18} className="shrink-0 text-wg-primary" aria-hidden />
        <span className="font-medium break-all">{existing.sourceFileName ?? "（貼上文字）"}</span>
        <span className="text-xs text-wg-muted">
          {SOURCE_TYPE_LABEL[existing.sourceType]} · {formatNumber(existing.sourceContent.length)} 字元 · 建立於{" "}
          {formatDateTime(existing.createdAt)}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto"
          disabled={!canWrite}
          title={writeHint}
          onClick={leaveExisting}
        >
          改用其他來源
        </Button>
      </div>
      {existing.sourceContent ? (
        <pre className="mt-3 max-h-32 overflow-auto font-mono text-xs break-words whitespace-pre-wrap text-wg-muted">
          {existing.sourceContent.slice(0, 600)}
          {existing.sourceContent.length > 600 ? `\n…（來源預覽，全文共 ${formatNumber(existing.sourceContent.length)} 字元）` : ""}
        </pre>
      ) : null}
      <p className="mt-2 text-[13px] text-wg-muted">
        已建立匯入記錄，來源不會重複上傳；調整下方解析選項後按「開始解析」重試。
      </p>
    </div>
  ) : null;

  return (
    <Card className="mb-6 p-6" data-testid="import-step1">
      <StepHeader step={1} title="輸入來源" />
      <PillTabs
        label="輸入來源"
        idBase={ID_BASE}
        tabs={TABS}
        value={tab}
        onChange={(next) => setTab(next)}
        className="mb-[18px]"
      />

      {tab === "history" ? (
        <div role="tabpanel" id={pillPanelId(ID_BASE, "history")} aria-labelledby={pillTabId(ID_BASE, "history")}>
          <HistoryPanel
            onOpen={(id) => {
              setTab("file");
              onOpenFromHistory(id);
            }}
          />
        </div>
      ) : (
        <>
          <div role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)}>
            {existingPanel ?? (tab === "file" ? (
              <div>
                <input
                  ref={inputRef}
                  type="file"
                  accept={ALLOWED_EXTENSIONS.join(",")}
                  className="sr-only"
                  tabIndex={-1}
                  aria-label="選擇要匯入的檔案"
                  data-testid="import-file-input"
                  onChange={(e) => {
                    chooseFile(e.target.files?.[0]);
                    e.target.value = ""; // 允許連續選同一個檔案
                  }}
                />
                <button
                  type="button"
                  disabled={!canWrite}
                  title={writeHint}
                  data-testid="import-dropzone"
                  onClick={() => inputRef.current?.click()}
                  onDragEnter={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    if (canWrite) chooseFile(e.dataTransfer.files?.[0]);
                  }}
                  className={cn(
                    "flex w-full cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-[38px] text-center transition-colors disabled:cursor-not-allowed disabled:bg-wg-disabled-bg",
                    dragging ? "border-wg-primary bg-wg-tertiary" : "border-wg-line bg-wg-surface hover:border-wg-secondary",
                  )}
                >
                  <CloudUpload size={40} className="text-wg-secondary" aria-hidden />
                  <span className="text-[15px] font-medium">拖曳檔案至此，或點擊選擇</span>
                  <span className="text-[13px] text-wg-muted">支援格式：.md · .pdf · .docx　|　檔案大小限制 10MB</span>
                </button>
                {file ? (
                  <div
                    data-testid="selected-file"
                    className="mt-3 flex items-center gap-2 rounded-md border border-wg-line px-3 py-2 text-sm"
                  >
                    <FileText size={16} className="shrink-0 text-wg-primary" aria-hidden />
                    <span className="min-w-0 flex-1 truncate">{file.name}</span>
                    <span className="shrink-0 text-wg-muted">{formatBytes(file.size)}</span>
                    <IconButton icon={X} label="移除檔案" size={28} onClick={() => setFile(null)} />
                  </div>
                ) : null}
                {sourceMessage ? (
                  <p role="alert" data-testid="source-error" className="mt-2 text-[13px] text-wg-error">
                    {sourceMessage}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <Field label="需求文字" hint="(支援 Markdown)" error={sourceMessage ?? undefined}>
                  <Textarea
                    className="min-h-[220px]"
                    value={text}
                    disabled={!canWrite}
                    placeholder="貼上 BRD／PRD 內容…"
                    onChange={(e) => setText(e.target.value)}
                  />
                </Field>
                <div className="grid grid-cols-[1fr_200px] gap-4 max-md:grid-cols-1">
                  <Field label="來源名稱" hint="(選填，例如 e2e-brd.md)">
                    <Input value={sourceName} disabled={!canWrite} onChange={(e) => setSourceName(e.target.value)} maxLength={500} />
                  </Field>
                  <Field label="格式">
                    <Select
                      value={sourceType}
                      disabled={!canWrite}
                      onChange={(e) => setSourceType(e.target.value as "PLAIN_TEXT" | "MARKDOWN")}
                    >
                      <option value="PLAIN_TEXT">純文字</option>
                      <option value="MARKDOWN">Markdown</option>
                    </Select>
                  </Field>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-[200px_1fr] gap-4 max-md:grid-cols-1">
            <Field label="自治等級" hint="(影響任務粒度)">
              <Select
                value={String(effectiveAutonomy)}
                disabled={!canWrite}
                onChange={(e) => setAutonomy(Number(e.target.value))}
              >
                {LEVELS.map((n) => (
                  <option key={n} value={n}>
                    Level {n}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="執行路徑" error={errors.executionPath || fieldErrors.executionPath}>
              <Input
                className="font-mono text-sm"
                value={executionPath}
                disabled={!canWrite}
                placeholder="/home/user/projects/new-service"
                aria-invalid={errors.executionPath || fieldErrors.executionPath ? true : undefined}
                onChange={(e) => setExecutionPath(e.target.value)}
              />
            </Field>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-wg-muted">{EXECUTION_PATH_HINT}</p>

          <Field
            className="mt-4"
            label="補充說明"
            hint="(可選，引導 AI 解析方向)"
            error={errors.additionalPrompt || fieldErrors.additionalPrompt}
          >
            <Textarea
              value={additional}
              disabled={!canWrite}
              placeholder="引導 AI 解析方向…"
              onChange={(e) => setAdditional(e.target.value)}
            />
          </Field>

          {failure ? <ParseFailurePanel failure={failure} className="mt-5" /> : null}

          <div className="mt-5 flex justify-end">
            <Button
              size="lg"
              className="min-h-11"
              iconLeft={Sparkles}
              loading={busy}
              disabled={!canWrite}
              title={writeHint}
              onClick={start}
            >
              開始解析
            </Button>
          </div>
        </>
      )}
    </Card>
  );
}
