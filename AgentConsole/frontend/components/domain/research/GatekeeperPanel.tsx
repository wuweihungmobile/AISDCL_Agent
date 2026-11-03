"use client";

/**
 * Gatekeeper 審批面板（PRD 工作室的右欄；FR-R2P-08、09、10、18；TCS-ResearchToPRD-P0-20261102 AT-960-15-1～15-4、16-4、16-5、16-8、16-9、16-E-2、16-E-3）：
 * ① 審查結果（第 n 輪、加權總分、四方雷達圖與等效文字表、缺陷卡）② 動作區（一鍵自動迭代修正、重新審查、核准 PRD、退回修改）
 * ③ ESCALATION 區塊（重用 `SddEscalationBlock` 加兩顆按鈕）④ Gate 0 等待提醒 ⑤ 審查進行中與無效輸出的狀態。
 *
 * 設計要點（為什麼這樣做）：
 *  - **分數綁內容**：審查結果只對該輪審的那份 PRD 內容有效（PRD §5.1.3：綁 `prd_sha256`）；head 的內容（`sha256`）與該輪審的版本不同＝「已過期」，核准停用、提供「重新審查」。
 *    不是比版本號：Gate 0 核准會把通過的那一版再存成 BASELINE（版本號加一、內容不變），比版本號會把「剛通過、剛凍結」的審查誤標已過期（INT-09，見 `isReviewStale`）。
 *  - **審查狀態只由 stage run 與事件決定**（D-55、D-57）：審查沒有「進行中的輪列」，所以進行中看 REVIEW 的 `research.run` 事件，輪完成才有輪列與 `research.review`；
 *    審查者輸出無效＝`research.review_invalid`（不佔輪次、不是進行中），顯示原因與「重新審查」。事件走 `useResearchTimeline`（REST 加串流加缺口同步，與動態欄同一套）；
 *    輪表、版本、FSM 視圖在即時事件到達後重抓（頁面剛載入的歷史事件不觸發）。
 *  - **審查預算只認 FSM 視圖**：剩餘預算＝`remainingReviewBudget(currentCount)`，`currentCount` 取 `retryHistory.gates.SCG_VALIDATION.currentCount`；不自己累計任何重試計數。
 *    對照式（AC-R2P-08 邊界條件）：FSM 重試史筆數應等於「目前世代的 gate FAIL 輪數加人工退回數」，不一致顯示警示、不修正任何一邊。
 *  - **ESCALATION 只有人能解**：區塊只顯示原因、各輪分數、未結缺陷、FSM 現態與可複製的恢復指令（Bridge 組字、Console 不替換不執行）；沒有任何恢復動詞按鈕。
 *    兩顆按鈕：「我已恢復，繼續（僅一次機會）」＝再啟動修訂階段並帶 `afterEscalation`（Bridge 唯讀驗證 FSM 已離開 ESCALATION 才續跑）；
 *    「換世代」＝放棄舊鍵、全新預算，僅 ADMIN、須理由與二次確認。即時收到升級事件時另開一個彈窗（「稍後處理」關閉，同一事件不再彈出；頁面重載只重建區塊）。
 *  - **Gate 0 只有 ADMIN 的真人點擊**：核准與退回都在確認對話框內送出，請求本文沒有 approver（後端取 JWT subject）；等待提醒純顯示、零寫入。
 *  - 寫入失敗（含 Bridge 尚未實作的 502）一律顯示白話原因、保持原狀，不假裝成功。外部衍生文字（缺陷描述、無效原因）一律純文字渲染。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Clock, Crosshair, RotateCcw, ShieldCheck, TriangleAlert, Undo2, WandSparkles } from "lucide-react";
import dynamic from "next/dynamic";
import { memo, useEffect, useId, useMemo, useState } from "react";

import { SddEscalationBlock } from "@/components/domain/sdd/SddEscalationBlock";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogBody, DialogClose, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useNow } from "@/hooks/useNow";
import { ApiError } from "@/lib/api/client";
import { listResearchEvidence } from "@/lib/api/endpoints";
import {
  qk,
  useApproveResearchBaseline,
  usePrdVersions,
  useReinitResearchProject,
  useResearchFsm,
  useResearchProject,
  useReturnResearchPrd,
  useReviewRounds,
  useStartResearchStage,
} from "@/lib/api/queries";
import type { ResearchDefect, ResearchEvent, ResearchEvidenceMatrix, ResearchFsmView, ResearchPrdVersion, ResearchProjectDetail, ResearchReviewRound } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  RADAR_AXES,
  READONLY_TITLE,
  RESEARCH_REASONS,
  REVIEW_RETRY_LIMIT,
  REVIEW_VERDICT_LABEL,
  flowStatusLabel,
  gate0WaitView,
  remainingReviewBudget,
  researchErrorText,
  reviewRetryCount,
  scoreRadar,
} from "@/lib/domain/research";
import { sddShowsEscalation } from "@/lib/domain/sdd";
import { cn } from "@/lib/utils";
import { useResearchTimeline, type TimelineOptions } from "./EvidenceTimeline";

// ── 純函式（可單獨測試；不讀瀏覽器全域、不發請求）──────────────────────────────────────

/** 即時事件到達後，輪表、版本與 FSM 視圖重抓前的去抖（毫秒）：一輪審查會連續送好幾筆事件，只重抓一次。 */
export const GATE_REFRESH_DEBOUNCE_MS = 300;
/** Gate 0 決定理由的字數上限（契約：`reason` 1～500 字）。 */
export const GATE_REASON_MAX = 500;
/** 將被凍結的四個檔案（PRD FR-R2P-10；相對工作區的 POSIX 路徑）。 */
export const GATE0_FILES: ReadonlyArray<{ path: string; label: string }> = [
  { path: "01_specs/PRD-v1.0.0.md", label: "PRD 基線" },
  { path: "00_research/evidence_matrix.md", label: "證據矩陣" },
  { path: "00_research/issue_scope.json", label: "議題範圍" },
  { path: "01_specs/adr_draft.md", label: "ADR 草稿" },
];

const DIMENSION_LABEL: Readonly<Record<string, string>> = Object.fromEntries(RADAR_AXES.map((axis) => [axis.dimension, axis.label]));
const SEVERITY_ORDER: Readonly<Record<string, number>> = { P1: 1, P2: 2, P3: 3, P4: 4 };
const DEFECT_STATUS_LABEL: Readonly<Record<ResearchDefect["status"], string>> = { OPEN: "未結", FIXED: "已修正", WAIVED: "已豁免", SUPERSEDED: "已被取代", REGRESSED: "再次出現" };

/** 缺陷卡的顯示序：嚴重度 P1 到 P4，同級依缺陷編號。 */
export function sortDefects(defects: readonly ResearchDefect[]): ResearchDefect[] {
  return [...defects].sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9) || a.defectNo.localeCompare(b.defectNo));
}

/** 未結缺陷（狀態 OPEN 或再次出現）。 */
export function openDefects(round: Pick<ResearchReviewRound, "defects">): ResearchDefect[] {
  return round.defects.filter((d) => d.status === "OPEN" || d.status === "REGRESSED");
}

/** 一輪審查不通過的原因（取自 `conditions`，不自己重算）；通過回空陣列。 */
export function unmetConditions(round: ResearchReviewRound): string[] {
  const { conditions } = round;
  const out: string[] = [];
  if (!conditions.precheckPassed) out.push("前置檢查未通過（章節、引用或驗收條件不完整）");
  if (conditions.weightedGeThreshold === false) out.push(`加權總分 ${scoreText(round)} 未達門檻 ${round.threshold.toFixed(2)}`);
  if (conditions.allDimensionsGeFloor === false) out.push(`有維度低於地板 ${round.floorScore}（最低 ${round.minDimensionScore ?? "—"}）`);
  if (!conditions.noOpenP1) out.push(`仍有 ${round.openP1Count} 個未結 P1 缺陷`);
  return out;
}

/** 加權總分的顯示字串：資料庫兩位小數原樣取 `toFixed(2)`，不經任何四捨五入；前置否決未計分為「未計分」。 */
export function scoreText(round: Pick<ResearchReviewRound, "weightedScore">): string {
  return round.weightedScore === null ? "未計分" : round.weightedScore.toFixed(2);
}

export type ReviewActivity = {
  /** 最近一次審查 run 還在跑（`research.run` 的 stage 為 REVIEW、status 為 QUEUED／RUNNING／BLOCKED_DB） */
  running: { roundNo: number | null } | null;
  /** 最近一次審查 run 沒有產生輪結果（失敗、取消或輸出無效）；`reason` 取自 `research.review_invalid` */
  attention: { status: string; reason: string | null } | null;
};

const payloadString = (event: ResearchEvent | undefined, key: string): string | null => {
  const value = event?.payload[key];
  return typeof value === "string" ? value : null;
};

/**
 * 審查的進行狀態（只由事件決定；審查沒有進行中的輪列）：最近一個 REVIEW 的 `research.run` 事件的狀態為準；
 * 之後出現 `research.review`（輪完成）就算收尾；`research.review_invalid` 只提供原因，不改變「這一輪沒有結果」的事實。
 */
export function reviewActivity(events: readonly ResearchEvent[]): ReviewActivity {
  let lastRun: ResearchEvent | undefined;
  let lastInvalid: ResearchEvent | undefined;
  let lastReview = 0;
  for (const event of events) {
    if (event.eventType === "research.run" && event.payload.stage === "REVIEW") {
      if (lastRun === undefined || event.seq > lastRun.seq) lastRun = event;
    } else if (event.eventType === "research.review_invalid") {
      if (lastInvalid === undefined || event.seq > lastInvalid.seq) lastInvalid = event;
    } else if (event.eventType === "research.review") {
      lastReview = Math.max(lastReview, event.seq);
    }
  }
  const invalidReason = lastInvalid !== undefined && lastInvalid.seq > lastReview ? payloadString(lastInvalid, "reason") : null;
  if (lastRun === undefined) return { running: null, attention: invalidReason === null ? null : { status: "FAILED", reason: invalidReason } };
  // 輪完成時會送 `research.review`（與輪列同一個交易）：它出現在這次 run 事件之後，就是這次審查已有結果，不論 run 事件的狀態更新到哪
  if (lastReview > lastRun.seq) return { running: null, attention: null };
  const status = payloadString(lastRun, "status") ?? "";
  if (status === "RUNNING" || status === "QUEUED" || status === "BLOCKED_DB") {
    const roundNo = lastRun.payload.roundNo;
    return { running: { roundNo: typeof roundNo === "number" ? roundNo : null }, attention: null };
  }
  if (status === "FAILED" || status === "CANCELLED") return { running: null, attention: { status, reason: invalidReason } };
  return { running: null, attention: invalidReason === null ? null : { status: "FAILED", reason: invalidReason } };
}

export type RetryHistoryCheck = { expected: number; actual: number; ok: boolean };

/**
 * 「第 n 輪」對照 FSM 重試史（AC-R2P-08 邊界條件）：期望＝目前世代中 gate 判 FAIL 的輪數加人工退回數（`humanReturnCount`），
 * 實際＝`retryHistory.gates.SCG_VALIDATION.entries`。視圖沒有這個閘的資料時回 null（沒得對照，不警示）。只比對、不累計、不修正。
 */
export function retryHistoryCheck(rounds: readonly ResearchReviewRound[], generation: number, fsm: Pick<ResearchFsmView, "retryHistory" | "humanReturnCount">): RetryHistoryCheck | null {
  const gate = fsm.retryHistory?.gates?.SCG_VALIDATION;
  if (gate === undefined) return null;
  const expected = rounds.filter((r) => r.fsmGeneration === generation && r.fsmGateResult === "FAIL").length + fsm.humanReturnCount;
  return { expected, actual: gate.entries, ok: expected === gate.entries };
}

const withSha256 = (hex: string): string => (hex.startsWith("sha256:") ? hex : `sha256:${hex}`);
/** 比較用的雜湊形：去掉 `sha256:` 前綴、轉小寫（兩邊同源時本來就同形；這裡只是不讓前綴與大小寫決定「過期」）。 */
const shaKey = (hex: string): string => hex.replace(/^sha256:/i, "").toLowerCase();

/**
 * 審查結果是否「已過期」（分數綁內容；PRD §5.1.3、AC-R2P-09-6；INT-09）：該輪審的那一版與目前的 head 是同一份內容（`sha256` 相同）就沒過期。
 * 判準取內容而不是版本號——Gate 0 核准會把通過的那一版再存成 BASELINE（版本號加一、內容與雜湊不變），比版本號會把剛通過、剛凍結的審查標成「已過期」；
 * 人工存檔（內容變了、雜湊不同）才是真過期。審查輪只帶 `prdVersionNo`，所以先用版本號在版本清單裡找出被審的那一版取雜湊。
 * 找不到被審的版本或 head（清單不完整）時無從確認內容相同，退回比版本號：寧可多要一次審查，也不放過一份可能不是被審內容的 PRD。
 * `headNo` 為 null＝還沒有任何版本，沒有東西可以過期。
 */
export function isReviewStale(round: Pick<ResearchReviewRound, "prdVersionNo">, headNo: number | null, versions: ReadonlyArray<Pick<ResearchPrdVersion, "versionNo" | "sha256">> | undefined): boolean {
  if (headNo === null || round.prdVersionNo === headNo) return false;
  const reviewed = versions?.find((v) => v.versionNo === round.prdVersionNo);
  const head = versions?.find((v) => v.versionNo === headNo);
  if (reviewed === undefined || head === undefined) return true;
  return shaKey(reviewed.sha256) !== shaKey(head.sha256);
}

/**
 * 核准請求的 `expectedDigests`（核准人當時看到的檔案摘要；鍵＝相對 POSIX 路徑、值＝`sha256:<64hex>`）。
 * 目前 API 只讓前端拿得到 head PRD 與證據矩陣兩個檔的 sha256（`PrdVersionDto.sha256`、`EvidenceMatrixDto.sha256`）；
 * 議題範圍與 ADR 草稿的摘要沒有任何端點提供，這裡不猜、不編造——缺的鍵由後端依其檢查序回報，畫面照實顯示後端的原因。
 */
export function buildExpectedDigests(prd: Pick<ResearchPrdVersion, "sha256">, matrix: Pick<ResearchEvidenceMatrix, "sha256">): Record<string, string> {
  return { "01_specs/PRD-v1.0.0.md": withSha256(prd.sha256), "00_research/evidence_matrix.md": withSha256(matrix.sha256) };
}

/** 升級相關的事件（一次升級可能同時有警示、游標與審查事件；彈窗以「升級事件的最大 seq」去重）。 */
export function isEscalationEvent(event: ResearchEvent): boolean {
  return (
    (event.eventType === "research.alert" && event.payload.kind === "ESCALATED") ||
    (event.eventType === "research.step" && event.payload.flowStatus === "ESCALATED") ||
    (event.eventType === "research.review" && event.payload.escalated === true)
  );
}

/** 會讓輪表、版本或 FSM 視圖變舊的事件。 */
const REFRESHING_EVENTS: ReadonlySet<string> = new Set([
  "research.run",
  "research.review",
  "research.review_invalid",
  "research.prd",
  "research.defect",
  "research.gate",
  "research.step",
  "research.alert",
]);

const charCount = (text: string): number => Array.from(text).length;

// ── 雷達圖（recharts；整個函式庫延遲到真的要畫時才下載，不進頁面首屏）────────────────────────

type RadarDatum = ReturnType<typeof scoreRadar>[number];

const RadarView = dynamic(
  async () => {
    const { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } = await import("recharts");
    return function RadarView({ data }: { data: RadarDatum[] }) {
      return (
        <ResponsiveContainer width="100%" height={240}>
          <RadarChart data={data} outerRadius="68%">
            <PolarGrid stroke="var(--color-border)" />
            <PolarAngleAxis dataKey="label" tick={{ fill: "var(--color-text-main)", fontSize: 13 }} />
            {/* 刻度軸放在「架構」軸與「商業」軸之間（45 度）：放在 90 度會與頂端的軸名稱疊在一起（真瀏覽器截圖現形） */}
            <PolarRadiusAxis angle={45} domain={[0, 100]} tickCount={5} axisLine={false} tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} />
            <Radar dataKey="score" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.25} isAnimationActive={false} />
          </RadarChart>
        </ResponsiveContainer>
      );
    };
  },
  { ssr: false, loading: () => <Skeleton className="h-60 rounded-md" /> },
);

// ── 面板各區塊 ───────────────────────────────────────────────────────────────────────

function ScoreSection({ round, roundCount, stale }: { round: ResearchReviewRound; roundCount: number; stale: boolean }) {
  const radar = scoreRadar(round);
  const complete = radar.every((axis) => axis.score !== null);
  const unmet = unmetConditions(round);
  return (
    <Card data-testid="review-score" className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-semibold" data-testid="round-label">
          第 {roundCount} 輪
        </h3>
        <span className={cn("rounded-sm px-1.5 py-0.5 text-xs font-semibold", round.passed ? "bg-wg-tertiary text-wg-primary-strong" : "bg-wg-draft-bg text-wg-accent")}>
          {REVIEW_VERDICT_LABEL[round.verdict] ?? round.verdict}
        </span>
        {stale ? (
          <span data-testid="review-stale" className="rounded-sm bg-wg-alert-bg px-1.5 py-0.5 text-xs font-semibold text-wg-warning-text">
            已過期
          </span>
        ) : null}
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt className="text-wg-muted">加權總分</dt>
        <dd data-testid="weighted-score" className="font-semibold">
          {scoreText(round)}
          <span className="font-normal text-wg-muted"> ／ 門檻 {round.threshold.toFixed(2)}</span>
        </dd>
        <dt className="text-wg-muted">最低維度分</dt>
        <dd data-testid="min-dimension">
          {round.minDimensionScore ?? "—"}
          <span className="text-wg-muted"> ／ 地板 {round.floorScore}</span>
        </dd>
        <dt className="text-wg-muted">審查的 PRD 版本</dt>
        <dd>{round.prdVersion}</dd>
      </dl>
      {unmet.length > 0 ? (
        <ul data-testid="unmet-conditions" className="list-disc pl-5 text-sm text-wg-accent">
          {unmet.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      ) : null}
      {complete ? (
        <div role="img" aria-label={`四方審查雷達圖：${radar.map((axis) => `${axis.label} ${axis.score}`).join("、")}`} data-testid="radar-chart">
          <RadarView data={radar} />
        </div>
      ) : null}
      <table data-testid="radar-table" aria-label="四方審查分數（雷達圖的等效文字表）" className="w-full text-sm">
        <tbody>
          {radar.map((axis) => (
            <tr key={axis.dimension} data-dimension={axis.dimension} className="border-t border-wg-line first:border-t-0">
              <th scope="row" className="py-1 pr-2 text-left font-normal text-wg-muted">
                {axis.label}
              </th>
              <td className="py-1 text-right font-semibold">{axis.score ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function DefectCards({ round, onLocate }: { round: ResearchReviewRound; onLocate: (anchor: string) => void }) {
  const defects = sortDefects(round.defects);
  if (defects.length === 0) return <p className="text-sm text-wg-muted">這一輪沒有缺陷。</p>;
  return (
    <ul data-testid="defect-list" aria-label="缺陷卡" className="flex flex-col gap-2">
      {defects.map((d) => (
        <li
          key={d.defectNo}
          data-testid="defect-card"
          data-defect-no={d.defectNo}
          data-severity={d.severity}
          className="flex flex-col gap-1 rounded-md border border-wg-line bg-wg-surface px-3 py-2 text-sm"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("rounded-sm px-1.5 py-0.5 text-xs font-semibold", d.severity === "P1" ? "bg-wg-draft-bg text-wg-accent" : "bg-wg-base text-wg-muted")}>{d.severity}</span>
            <span className="font-mono text-xs text-wg-muted">{d.defectNo}</span>
            <span className="text-xs">{DIMENSION_LABEL[d.dimension] ?? d.dimension}</span>
            <span data-testid="defect-status" className="ml-auto text-xs text-wg-muted">
              {DEFECT_STATUS_LABEL[d.status] ?? d.status}
            </span>
          </div>
          <p className="break-words">{d.description}</p>
          <p className="break-words text-wg-muted">
            <span className="font-medium text-wg-text">修訂建議：</span>
            {d.suggestion}
          </p>
          <Button variant="ghost" size="sm" iconLeft={Crosshair} className="self-start" onClick={() => onLocate(d.prdAnchor)}>
            定位 {d.prdAnchor}
          </Button>
        </li>
      ))}
    </ul>
  );
}

const REVIEWERS: ReadonlyArray<string> = RADAR_AXES.map((axis) => `${axis.label}審查者`);

function ReviewProgress({ roundNo }: { roundNo: number }) {
  return (
    <Card data-testid="review-progress" className="flex flex-col gap-2 p-4">
      <p role="status" className="flex items-center gap-2 text-sm font-semibold">
        <Clock size={16} aria-hidden />
        審查中（第 {roundNo} 輪）
      </p>
      <p className="text-xs text-wg-muted">四位審查者在同一個階段內依序執行；完成後才會顯示分數與判定（審查中沒有輪結果）。</p>
      <ul className="flex flex-col gap-1">
        {REVIEWERS.map((name) => (
          <li key={name} data-testid="reviewer-progress" className="flex items-center justify-between rounded-sm border border-wg-line px-2 py-1 text-sm">
            <span>{name}</span>
            <span className="text-wg-muted">審查中</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

type DecisionSummary = { version: ResearchPrdVersion; round: ResearchReviewRound };

/** Gate 0 確認對話框的內容：摘要、選填理由、兩個決定（核准並凍結／退回修改）。 */
function DecisionBody({ summary, onApprove, onReturn }: { summary: DecisionSummary; onApprove: (reason: string) => Promise<void>; onReturn: (reason: string) => Promise<void> }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<"approve" | "return" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { version, round } = summary;
  const trimmed = reason.trim();
  const tooLong = charCount(trimmed) > GATE_REASON_MAX;

  async function run(kind: "approve" | "return", action: (r: string) => Promise<void>) {
    setBusy(kind);
    setError(null);
    try {
      await action(trimmed);
    } catch (e) {
      setError(researchErrorText(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <DialogBody>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm" data-testid="gate-summary">
          <dt className="text-wg-muted">PRD 版本</dt>
          <dd>
            {version.semver}（第 {version.versionNo} 版）
          </dd>
          <dt className="text-wg-muted">sha256 前 8 碼</dt>
          <dd className="font-mono">{version.sha256.replace(/^sha256:/, "").slice(0, 8)}</dd>
          <dt className="text-wg-muted">加權總分</dt>
          <dd>{scoreText(round)}</dd>
          <dt className="text-wg-muted">最低維度分</dt>
          <dd>{round.minDimensionScore ?? "—"}</dd>
          <dt className="text-wg-muted">未結缺陷數</dt>
          <dd>{openDefects(round).length}</dd>
        </dl>
        <div>
          <p className="text-sm font-medium">將凍結的檔案（核准後不可改，只能經變更請求修改）</p>
          <ul data-testid="gate-files" className="mt-1 list-disc pl-5 text-sm">
            {GATE0_FILES.map((file) => (
              <li key={file.path}>
                <span className="font-mono">{file.path}</span>（{file.label}）
              </li>
            ))}
          </ul>
        </div>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          理由（核准時選填；退回修改時必填）
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={tooLong || undefined} placeholder="例如：缺陷已處理，確認凍結／缺少可量測的驗收條件，請補上" />
        </label>
        <p className={cn("text-xs", tooLong ? "text-wg-error" : "text-wg-muted")} data-testid="reason-count">
          {charCount(trimmed)} ／ {GATE_REASON_MAX} 字
        </p>
        {error === null ? null : (
          <p role="alert" data-testid="gate-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        )}
      </DialogBody>
      <DialogFooter>
        <DialogClose asChild>
          <Button variant="ghost" disabled={busy !== null}>
            取消
          </Button>
        </DialogClose>
        <Button variant="accent" iconLeft={Undo2} disabled={trimmed === "" || tooLong || busy !== null} loading={busy === "return"} onClick={() => void run("return", onReturn)}>
          退回修改
        </Button>
        <Button iconLeft={ShieldCheck} disabled={tooLong || busy !== null} loading={busy === "approve"} onClick={() => void run("approve", onApprove)}>
          核准並凍結
        </Button>
      </DialogFooter>
    </>
  );
}

/** 「換世代」對話框的內容：說明、必填理由（1～500 字）、二次確認。 */
function ReinitBody({ onConfirm, error }: { onConfirm: (reason: string) => Promise<void>; error: string | null }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const trimmed = reason.trim();
  const count = charCount(trimmed);
  const invalid = count < 1 || count > GATE_REASON_MAX;
  return (
    <>
      <DialogBody>
        <p className="text-sm">
          換世代會<strong>放棄目前這把狀態機的鍵</strong>（舊鍵不再使用、永遠停在 ESCALATION），另開新世代的鍵，審查預算重新計。這不是恢復，也不能反悔；此動作會留稽核紀錄。
        </p>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          理由（必填，1～{GATE_REASON_MAX} 字）
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={count > GATE_REASON_MAX || undefined} />
        </label>
        <p className={cn("text-xs", count > GATE_REASON_MAX ? "text-wg-error" : "text-wg-muted")} data-testid="reason-count">
          {count} ／ {GATE_REASON_MAX} 字
        </p>
        {error === null ? null : (
          <p role="alert" data-testid="reinit-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        )}
      </DialogBody>
      <DialogFooter>
        <DialogClose asChild>
          <Button variant="ghost" disabled={busy}>
            取消
          </Button>
        </DialogClose>
        <Button
          variant="accent"
          disabled={invalid || busy}
          loading={busy}
          onClick={() => {
            setBusy(true);
            void onConfirm(trimmed).finally(() => setBusy(false));
          }}
        >
          確認換世代
        </Button>
      </DialogFooter>
    </>
  );
}

// ── 面板本體 ─────────────────────────────────────────────────────────────────────────

export type GatekeeperPanelProps = {
  researchId: string;
  project: ResearchProjectDetail;
  /** 這一步已完成（專案已凍結、游標在後面的步驟）：所有動作停用 */
  completed: boolean;
  /** 缺陷卡的定位連結：回報錨點（例：「§4.2」），由工作室把編輯器捲過去 */
  onLocate: (anchor: string) => void;
} & TimelineOptions;

function GatekeeperPanelImpl({ researchId, project, completed, onLocate, EventSourceCtor, syncRetryMs, refreshDebounceMs, backoffMs }: GatekeeperPanelProps) {
  const toast = useToast();
  const qc = useQueryClient();
  const noteId = useId();
  const { role, canWrite } = useAuth();
  const isAdmin = role === "ADMIN";
  const liveProject = useResearchProject(researchId).data ?? project;
  const versionsQuery = usePrdVersions(researchId);
  const roundsQuery = useReviewRounds(researchId);
  const fsmQuery = useResearchFsm(researchId);
  const timeline = useResearchTimeline(researchId, { EventSourceCtor, syncRetryMs, refreshDebounceMs, backoffMs });
  const start = useStartResearchStage();
  const approve = useApproveResearchBaseline();
  const returnPrd = useReturnResearchPrd();
  const reinit = useReinitResearchProject();

  const [decisionOpen, setDecisionOpen] = useState(false);
  const [reinitOpen, setReinitOpen] = useState(false);
  const [reinitError, setReinitError] = useState<string | null>(null);
  const [recoverNotice, setRecoverNotice] = useState<string | null>(null);
  const [dismissedUpTo, setDismissedUpTo] = useState(0);

  const versions = versionsQuery.data;
  const rounds = roundsQuery.data;
  const fsm = fsmQuery.data;
  const head = useMemo(() => (versions === undefined || versions.length === 0 ? undefined : versions.reduce((a, v) => (v.versionNo > a.versionNo ? v : a))), [versions]);
  const headNo = head?.versionNo ?? liveProject.headPrdVersion;
  const latest = useMemo(() => (rounds === undefined || rounds.length === 0 ? undefined : rounds.reduce((a, r) => (r.roundNo > a.roundNo ? r : a))), [rounds]);
  const stale = latest !== undefined && isReviewStale(latest, headNo, versions);
  const escalated = fsm !== undefined ? sddShowsEscalation(fsm) : liveProject.flowStatus === "ESCALATED";
  const frozen = completed || liveProject.flowPhase === "FROZEN" || head?.kind === "BASELINE";

  // 審查狀態（只由事件決定）與「頁面載入之後」的即時事件
  const events = timeline.view.visible;
  const activity = useMemo(() => reviewActivity(events), [events]);
  const [baseline, setBaseline] = useState<number | null>(null);
  if (baseline === null && timeline.ready) setBaseline(timeline.view.lastSeq);
  const liveEvents = useMemo(() => (baseline === null ? [] : events.filter((e) => e.seq > baseline)), [events, baseline]);
  const refreshSeq = useMemo(() => liveEvents.reduce((max, e) => (REFRESHING_EVENTS.has(e.eventType) ? Math.max(max, e.seq) : max), 0), [liveEvents]);
  const escalationSeq = useMemo(() => liveEvents.reduce((max, e) => (isEscalationEvent(e) ? Math.max(max, e.seq) : max), 0), [liveEvents]);

  useEffect(() => {
    if (refreshSeq === 0) return;
    const timer = setTimeout(() => {
      for (const queryKey of [qk.researchReviewRounds(researchId), qk.researchPrdVersions(researchId), qk.researchFsm(researchId)]) void qc.invalidateQueries({ queryKey });
    }, GATE_REFRESH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [refreshSeq, researchId, qc]);

  // Gate 0 等待提醒：純顯示（FSM 現態為 HUMAN_PENDING 才有；每分鐘更新一次時鐘）
  const now = useNow(fsm?.currentState === "HUMAN_PENDING", 60_000);
  const wait = rounds === undefined ? null : gate0WaitView(fsm?.currentState, rounds, now);

  // 審查預算只認 FSM 視圖
  const currentCount = reviewRetryCount(fsm);
  const remaining = remainingReviewBudget(currentCount);
  const afterRecovery = fsm !== undefined && !escalated && currentCount >= REVIEW_RETRY_LIMIT;
  const integrity = fsm !== undefined && rounds !== undefined ? retryHistoryCheck(rounds, liveProject.fsmGeneration, fsm) : null;

  const reviewing = activity.running !== null;
  const busy = start.isPending || approve.isPending || returnPrd.isPending || reinit.isPending;
  const roleTitle = !canWrite ? READONLY_TITLE : undefined;
  const adminTitle = !canWrite ? READONLY_TITLE : !isAdmin ? "權限不足：這個動作僅 ADMIN 可用" : undefined;
  const locked = roleTitle !== undefined || frozen || busy;

  const showIterate = latest !== undefined && !latest.passed;
  const showReview = head !== undefined && (latest === undefined || stale || activity.attention !== null);
  const iterateDisabled = locked || escalated || reviewing;
  const reviewDisabled = locked || escalated || reviewing;
  const approveBlock = frozen
    ? "規格已凍結，不能再核准"
    : escalated
      ? "審查已升級給人工，請先處理 ESCALATION"
      : reviewing
        ? "審查進行中，完成後才能核准"
        : latest === undefined
          ? "尚未審查：請先送審"
          : stale
            ? `審查已過期：PRD 已有新版本（第 ${headNo} 版），審查的是第 ${latest.prdVersionNo} 版，請重新審查`
            : latest.passed
              ? null
              : `審查未通過：${unmetConditions(latest).join("；")}`;
  const approveDisabled = adminTitle !== undefined || approveBlock !== null || busy;
  const returnDisabled = adminTitle !== undefined || frozen || escalated || fsm?.currentState !== "HUMAN_PENDING" || busy;
  const returnBlock = fsm?.currentState === "HUMAN_PENDING" ? null : "退回修改只在等待人工核准（Gate 0）時可用";
  const approveNote = [approveBlock, returnDisabled && adminTitle === undefined && !frozen && !escalated ? returnBlock : null].filter((text): text is string => text !== null).join("；");

  async function startStage(stage: "iterate" | "review", label: string) {
    try {
      await start.mutateAsync({ id: researchId, stage });
      toast.success(`${label}：已送出，審查結果會即時更新`);
    } catch (e) {
      toast.error(`${label}失敗：${researchErrorText(e)}`);
    }
  }

  async function recover() {
    setRecoverNotice(null);
    try {
      await start.mutateAsync({ id: researchId, stage: "revise", body: { afterEscalation: true } });
      toast.success("已送出：恢復後預算不歸零，至多再跑一輪審查");
    } catch (e) {
      if (e instanceof ApiError && e.reason === RESEARCH_REASONS.FSM_STATE_CONFLICT) {
        const state = typeof e.details?.current_state === "string" ? e.details.current_state : "ESCALATION";
        setRecoverNotice(`狀態機現態是 ${state}，還沒有離開 ESCALATION：請先在 Console 外用上面的恢復指令恢復，再按這顆鈕。`);
      } else {
        toast.error(`繼續失敗：${researchErrorText(e)}`);
      }
    }
  }

  async function reinitNext(reason: string) {
    setReinitError(null);
    try {
      await reinit.mutateAsync({ id: researchId, body: { generation: "next", reason } });
      setReinitOpen(false);
      toast.success("已換世代：舊鍵不再使用，審查預算重新計");
    } catch (e) {
      if (e instanceof ApiError && e.reason === RESEARCH_REASONS.FSM_STATE_CONFLICT) {
        setReinitError(`狀態機現態是 ${typeof e.details?.current_state === "string" ? e.details.current_state : "不是 ESCALATION"}，目前不能換世代。`);
      } else {
        setReinitError(researchErrorText(e));
      }
    }
  }

  async function approveBaseline(reason: string) {
    if (head === undefined) return;
    const matrix = await qc.fetchQuery({ queryKey: qk.researchEvidence(researchId, null), queryFn: ({ signal }) => listResearchEvidence(researchId, { signal }), staleTime: 0 });
    await approve.mutateAsync({ id: researchId, body: { prdVersion: head.versionNo, expectedDigests: buildExpectedDigests(head, matrix), ...(reason === "" ? {} : { reason }) } });
    setDecisionOpen(false);
    toast.success("已核准並凍結：規格進入下一步");
  }

  async function returnForChanges(reason: string) {
    const result = await returnPrd.mutateAsync({ id: researchId, body: { reason } });
    setDecisionOpen(false);
    toast.success(result.escalated ? "已退回修改，且審查預算用盡：已升級給人工" : "已退回修改，PRD 回到可編輯狀態（退回算一次審查預算）");
  }

  const popupOpen = escalationSeq > dismissedUpTo;
  const loading = (rounds === undefined && !roundsQuery.isError) || (versions === undefined && !versionsQuery.isError);

  return (
    <div data-testid="gatekeeper-panel" className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold">審批</h2>
        <span data-testid="flow-status" className="text-sm text-wg-muted">
          流程：{flowStatusLabel(liveProject.flowStatus)}
        </span>
        <span data-testid="generation" className="text-sm text-wg-muted">
          狀態機世代 {liveProject.fsmGeneration}
        </span>
      </div>

      {fsmQuery.isError ? (
        <p role="alert" data-testid="fsm-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          無法取得狀態機視圖：{researchErrorText(fsmQuery.error)}。審查結果仍取自資料庫，但剩餘預算與等待時間暫時無法顯示。
        </p>
      ) : null}

      {integrity !== null && !integrity.ok ? (
        <p role="alert" data-testid="integrity-warning" className="flex items-start gap-2 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm text-wg-warning-text">
          <TriangleAlert size={16} aria-hidden className="mt-0.5 shrink-0" />
          <span>
            審查輪與狀態機的重試史不一致：期望 {integrity.expected}、實際 {integrity.actual}（期望＝目前世代未通過的輪數加人工退回數；系統只顯示差異，不會自動修正）。
          </span>
        </p>
      ) : null}

      {wait !== null ? (
        <div className="flex flex-col gap-2">
          <p role="status" data-testid="gate-wait" className="flex items-center gap-2 text-sm">
            <Clock size={16} aria-hidden />
            已等待 {wait.hours} 小時
          </p>
          {wait.overdue ? (
            <p role="alert" data-testid="gate-wait-banner" className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm font-semibold text-wg-warning-text">
              已等待超過 72 小時，尚未核准
            </p>
          ) : null}
        </div>
      ) : null}

      {escalated ? (
        <section data-testid="escalation-section" aria-label="ESCALATION 人工處理" className="flex flex-col gap-3">
          {fsm !== undefined ? <SddEscalationBlock fsm={fsm} /> : <p className="text-sm text-wg-muted">審查已升級給人工，正在載入狀態機視圖…</p>}
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm" data-testid="escalation-facts">
            <dt className="text-wg-muted">狀態機現態</dt>
            <dd data-testid="escalation-state">{fsm?.currentState ?? "—"}</dd>
            <dt className="text-wg-muted">各輪分數</dt>
            <dd data-testid="escalation-scores">
              {rounds === undefined || rounds.length === 0
                ? "—"
                : rounds.map((r) => (
                    <span key={r.roundNo} className="mr-3 inline-block">
                      第 {r.roundNo} 輪 {scoreText(r)}
                    </span>
                  ))}
            </dd>
            <dt className="text-wg-muted">未結缺陷</dt>
            <dd data-testid="escalation-open-defects">{latest === undefined ? "—" : `${openDefects(latest).length} 個`}</dd>
          </dl>
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                iconLeft={RotateCcw}
                disabled={roleTitle !== undefined || frozen || busy}
                title={roleTitle}
                loading={start.isPending && start.variables?.body?.afterEscalation === true}
                onClick={() => void recover()}
              >
                我已恢復，繼續（僅一次機會）
              </Button>
              <Button variant="accent" disabled={adminTitle !== undefined || frozen || busy} title={adminTitle} onClick={() => setReinitOpen(true)}>
                換世代
              </Button>
            </div>
            <p className="text-xs text-wg-muted">
              「我已恢復，繼續」要先在 Console 外用上面的指令恢復，系統只會唯讀確認狀態機已離開 ESCALATION；恢復後預算不歸零，至多再審一輪。「換世代」僅 ADMIN 可用，放棄舊鍵並重新計預算。
            </p>
            {recoverNotice === null ? null : (
              <p role="alert" data-testid="recover-notice" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
                {recoverNotice}
              </p>
            )}
          </div>
        </section>
      ) : null}

      {loading ? (
        <div aria-busy="true" aria-label="審查結果載入中" role="status">
          <Skeleton className="h-60 rounded-lg" />
        </div>
      ) : null}
      {roundsQuery.isError ? <ErrorState error={roundsQuery.error} title="無法載入審查結果" onRetry={() => void roundsQuery.refetch()} /> : null}

      {activity.running !== null ? <ReviewProgress roundNo={activity.running.roundNo ?? (rounds?.length ?? 0) + 1} /> : null}
      {activity.attention !== null ? (
        <div role="alert" data-testid="review-invalid" className="flex flex-col gap-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
          <p className="font-semibold text-wg-accent">
            {activity.attention.reason !== null ? "審查者的輸出無效，這一輪沒有結果" : activity.attention.status === "CANCELLED" ? "審查已取消，這一輪沒有結果" : "審查沒有完成，這一輪沒有結果"}
            （不佔輪次）
          </p>
          {activity.attention.reason === null ? null : (
            <p data-testid="review-invalid-reason" className="break-words whitespace-pre-wrap">
              {activity.attention.reason}
            </p>
          )}
        </div>
      ) : null}

      {rounds !== undefined && latest === undefined && activity.running === null ? (
        <Card data-testid="review-empty" className="p-4 text-sm text-wg-muted">
          還沒有審查結果。PRD 草稿完成後送審，四位審查者各自評分，結果會顯示在這裡。
        </Card>
      ) : null}
      {latest !== undefined && rounds !== undefined ? <ScoreSection round={latest} roundCount={rounds.length} stale={stale} /> : null}
      {latest !== undefined ? (
        <section className="flex flex-col gap-2" aria-label="缺陷">
          <h3 className="text-base font-semibold">缺陷（第 {latest.roundNo} 輪）</h3>
          <DefectCards round={latest} onLocate={onLocate} />
        </section>
      ) : null}

      <section data-testid="gate-actions" aria-label="審批動作" className="flex flex-col gap-3 border-t border-wg-line pt-4">
        {fsm !== undefined && showIterate ? (
          <p data-testid="budget-text" className="text-sm">
            剩餘預算 <strong data-testid="budget-remaining">{remaining}</strong> 次
            {afterRecovery ? (
              <span data-testid="budget-after-recovery" className="ml-1 font-semibold text-wg-warning-text">
                （恢復後僅一次機會）
              </span>
            ) : null}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          {showIterate ? (
            <Button
              iconLeft={WandSparkles}
              disabled={iterateDisabled}
              title={roleTitle}
              loading={start.isPending && start.variables?.stage === "iterate"}
              onClick={() => void startStage("iterate", "一鍵自動迭代修正")}
            >
              一鍵自動迭代修正
            </Button>
          ) : null}
          {showReview ? (
            <Button
              variant="ghost"
              iconLeft={RotateCcw}
              disabled={reviewDisabled}
              title={roleTitle}
              loading={start.isPending && start.variables?.stage === "review"}
              onClick={() => void startStage("review", latest === undefined ? "送審" : "重新審查")}
            >
              {latest === undefined ? "送審" : "重新審查"}
            </Button>
          ) : null}
          <Button iconLeft={ShieldCheck} disabled={approveDisabled} title={adminTitle} aria-describedby={noteId} onClick={() => setDecisionOpen(true)}>
            核准 PRD
          </Button>
          <Button variant="ghost" iconLeft={Undo2} disabled={returnDisabled} title={adminTitle} onClick={() => setDecisionOpen(true)}>
            退回修改
          </Button>
        </div>
        <p id={noteId} data-testid="approve-note" className="text-sm text-wg-muted">
          {approveNote}
        </p>
      </section>

      <Dialog open={decisionOpen} onOpenChange={setDecisionOpen}>
        {decisionOpen && head !== undefined && latest !== undefined ? (
          <DialogContent title="Gate 0：核准或退回 PRD" description="確認要凍結的版本與檔案，或退回修改">
            <DecisionBody summary={{ version: head, round: latest }} onApprove={approveBaseline} onReturn={returnForChanges} />
          </DialogContent>
        ) : null}
      </Dialog>

      <Dialog
        open={reinitOpen}
        onOpenChange={(open) => {
          setReinitOpen(open);
          if (!open) setReinitError(null);
        }}
      >
        {reinitOpen ? (
          <DialogContent title="換世代" description="放棄舊鍵、全新預算，須填理由並二次確認">
            <ReinitBody onConfirm={reinitNext} error={reinitError} />
          </DialogContent>
        ) : null}
      </Dialog>

      <Dialog open={popupOpen} onOpenChange={(open) => !open && setDismissedUpTo(Math.max(escalationSeq, timeline.view.lastSeq))}>
        {popupOpen ? (
          <DialogContent title="審查已升級，需要人工處理" description="審查沒有在預算內通過，已升級給人工">
            <DialogBody>
              <p className="text-sm">審查沒有在預算內通過，已升級給人工處理。請在審批欄的 ESCALATION 區塊看原因與恢復指令；Console 不會替您恢復。</p>
            </DialogBody>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="ghost">稍後處理</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  );
}

export const GatekeeperPanel = memo(GatekeeperPanelImpl);
