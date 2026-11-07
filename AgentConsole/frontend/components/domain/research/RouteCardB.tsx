"use client";

/**
 * 分流卡 B：獨立專案（FR-R2P-13；TCS-ResearchToPRD-P1-20261107 AT-961-17-4）。
 * 欄位：專案名稱（同時是內環鍵，D-119）、owner、庫名（省略時取專案名稱）、範本（下拉，只列 capabilities 的範本；P1 僅 `python-fastapi`）、
 * 可見度（預設 Private；Public 需 {@link PublicRepoConfirm}）、「建立 GitHub 遠端」勾選（`gh` 不可用時只停用這一項，本地骨架仍可）、CI 與 docker compose 勾選（預設勾選）。
 * GitHub 權杖不在這裡收：只由後端設定鍵帶入單次請求，前端從不碰（AC-R2P-13-4）。
 */
import { PackagePlus } from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { effectiveRepoName, ROUTE_TRACK_LABEL, type RouteForm, type RouteFormField } from "@/lib/domain/research";
import { cn } from "@/lib/utils";
import { PublicRepoConfirm } from "./PublicRepoConfirm";

export function RouteCardB({
  selected,
  onSelect,
  form,
  onChange,
  errors,
  templates,
  disabled,
  disabledReason,
  githubDisabledReason,
}: {
  selected: boolean;
  onSelect: () => void;
  form: RouteForm;
  onChange: (patch: Partial<RouteForm>) => void;
  errors: Partial<Record<RouteFormField, string>>;
  /** capabilities 的範本清單 */
  templates: readonly string[];
  disabled: boolean;
  disabledReason?: string | null;
  /** 非空＝「建立 GitHub 遠端」勾選停用，值為說明 */
  githubDisabledReason?: string | null;
}) {
  return (
    <section
      data-testid="route-card-b"
      data-selected={selected}
      aria-label={ROUTE_TRACK_LABEL.B}
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
        <PackagePlus size={18} aria-hidden />
        軌道 B：獨立專案
      </button>
      <p className="text-sm text-wg-muted">由範本展開專案骨架並初始化 git，研究工作區完整複製到新專案；可選擇是否建立 GitHub 遠端。</p>
      {disabled && disabledReason ? (
        <p role="note" data-testid="route-card-b-disabled" className="text-[13px] text-wg-warning-text">
          {disabledReason}
        </p>
      ) : null}
      {selected && !disabled ? (
        <div className="flex flex-col gap-3">
          <Field label="專案名稱" hint="同時是內環鍵" error={errors.projectName}>
            <Input value={form.projectName} aria-invalid={errors.projectName ? true : undefined} autoComplete="off" onChange={(event) => onChange({ projectName: event.target.value })} />
          </Field>
          <Field label="專案範本" error={errors.stackTemplate}>
            <Select value={form.stackTemplate} aria-invalid={errors.stackTemplate ? true : undefined} onChange={(event) => onChange({ stackTemplate: event.target.value })}>
              {templates.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="owner" hint="建立遠端時必填" error={errors.owner}>
            <Input value={form.owner} aria-invalid={errors.owner ? true : undefined} autoComplete="off" onChange={(event) => onChange({ owner: event.target.value })} />
          </Field>
          <Field label="庫名" hint="省略時取專案名稱" error={errors.repoName}>
            <Input
              value={form.repoName}
              placeholder={form.projectName}
              aria-invalid={errors.repoName ? true : undefined}
              autoComplete="off"
              onChange={(event) => onChange({ repoName: event.target.value })}
            />
          </Field>
          <Field label="可見度">
            <Select value={form.visibility} onChange={(event) => onChange({ visibility: event.target.value === "PUBLIC" ? "PUBLIC" : "PRIVATE", confirmRepoName: "" })}>
              <option value="PRIVATE">Private（私有，預設）</option>
              <option value="PUBLIC">Public（公開）</option>
            </Select>
          </Field>
          {form.visibility === "PUBLIC" ? <PublicRepoConfirm repoName={effectiveRepoName(form)} value={form.confirmRepoName} onChange={(next) => onChange({ confirmRepoName: next })} /> : null}
          <label className="flex items-center gap-2 text-sm" title={githubDisabledReason ?? undefined}>
            <Checkbox checked={form.createGithub && !githubDisabledReason} disabled={Boolean(githubDisabledReason)} onCheckedChange={(v) => onChange({ createGithub: v === true })} />
            建立 GitHub 遠端
          </label>
          {githubDisabledReason ? (
            <p role="note" data-testid="github-disabled" className="text-[13px] text-wg-warning-text">
              {githubDisabledReason}
            </p>
          ) : null}
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={form.ci} onCheckedChange={(v) => onChange({ ci: v === true })} />
            產生 CI 設定
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={form.dockerCompose} onCheckedChange={(v) => onChange({ dockerCompose: v === true })} />
            產生 docker compose
          </label>
        </div>
      ) : null}
    </section>
  );
}
