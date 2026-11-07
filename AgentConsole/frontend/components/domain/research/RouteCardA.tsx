"use client";

/**
 * 分流卡 A：併入 AISDLC 模組（FR-R2P-12；TCS-ResearchToPRD-P1-20261107 AT-961-17-3）。
 * 欄位：分支名（預設 `feature/issue-<NNNN>`，即時驗證）、基底 ref（預設 `main`）、掛載目標（下拉，只能取落點目標清單的四個模組，旁邊附出處句；
 * 不是自由文字輸入——使用者輸入任意路徑只增加逃逸面，D-106）。目標路徑由 Bridge 導出，這裡不收 `targetPath`。
 */
import { GitBranch } from "lucide-react";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { PLACEMENT_TARGETS, ROUTE_TRACK_LABEL, type RouteForm, type RouteFormField } from "@/lib/domain/research";
import type { ResearchPlacementTarget } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function RouteCardA({
  selected,
  onSelect,
  form,
  onChange,
  errors,
  defaultModule,
  disabled,
  disabledReason,
}: {
  selected: boolean;
  onSelect: () => void;
  form: RouteForm;
  onChange: (patch: Partial<RouteForm>) => void;
  errors: Partial<Record<RouteFormField, string>>;
  /** PRD 解析出的預設掛載目標（標「預設」） */
  defaultModule: ResearchPlacementTarget;
  /** 整張卡停用（唯讀角色、缺項、容器模式）；停用說明放 `disabledReason`（同時是 `title`） */
  disabled: boolean;
  disabledReason?: string | null;
}) {
  const picked = PLACEMENT_TARGETS.find((t) => t.id === form.targetModule);
  return (
    <section
      data-testid="route-card-a"
      data-selected={selected}
      aria-label={ROUTE_TRACK_LABEL.A}
      className={cn("flex flex-col gap-3 rounded-md border px-4 py-3", selected ? "border-wg-primary bg-wg-surface" : "border-wg-line")}
    >
      <button
        type="button"
        role="radio"
        aria-checked={selected}
        disabled={disabled}
        title={disabled ? (disabledReason ?? undefined) : undefined}
        onClick={onSelect}
        className="flex cursor-pointer items-center gap-2 text-left font-semibold disabled:cursor-not-allowed disabled:text-wg-disabled-text"
      >
        <GitBranch size={18} aria-hidden />
        軌道 A：併入 AISDLC
      </button>
      <p className="text-sm text-wg-muted">把規格掛到既有模組，在獨立的工作樹建立功能分支，主工作樹不受影響。</p>
      {disabled && disabledReason ? (
        <p role="note" data-testid="route-card-a-disabled" className="text-[13px] text-wg-warning-text">
          {disabledReason}
        </p>
      ) : null}
      {selected && !disabled ? (
        <div className="flex flex-col gap-3">
          <Field label="分支名" hint="預設依議題編號" error={errors.branchName}>
            <Input value={form.branchName} aria-invalid={errors.branchName ? true : undefined} onChange={(event) => onChange({ branchName: event.target.value })} />
          </Field>
          <Field label="基底 ref" error={errors.baseRef}>
            <Input value={form.baseRef} aria-invalid={errors.baseRef ? true : undefined} onChange={(event) => onChange({ baseRef: event.target.value })} />
          </Field>
          <Field label="掛載目標" error={errors.targetModule}>
            <Select value={form.targetModule} aria-invalid={errors.targetModule ? true : undefined} onChange={(event) => onChange({ targetModule: event.target.value as ResearchPlacementTarget })}>
              <option value="" disabled>
                請選擇
              </option>
              {PLACEMENT_TARGETS.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                  {t.id === defaultModule ? "（預設）" : ""}
                </option>
              ))}
            </Select>
          </Field>
          <ul data-testid="placement-sources" className="flex flex-col gap-1 text-[13px] text-wg-muted">
            {PLACEMENT_TARGETS.map((t) => (
              <li key={t.id}>
                <span className="font-medium text-wg-text">{t.label}</span>：{t.source}
              </li>
            ))}
          </ul>
          <p data-testid="module-registry-preview" className="text-[13px] text-wg-muted">
            模組登錄預覽（唯讀）：{picked ? `${picked.label}　${picked.source}` : "尚未選擇掛載目標"}
          </p>
        </div>
      ) : null}
    </section>
  );
}
