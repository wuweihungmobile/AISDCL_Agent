"use client";

/**
 * 一列參數（設計稿畫面 9：grid 220px 標籤＋說明／1fr 控制項；列尾是「重置」IconButton）。
 * 左欄：中文名稱、後端說明（description）、誠實標示（僅儲存／尚未驗證）。
 * 右欄：控制項、重置；下方依序是表單提示、數值範圍、影響範圍提示（US-S-08，ⓘ 行）、驗證錯誤紅字。
 */
import { Info, RotateCcw } from "lucide-react";

import { IconButton } from "@/components/ui/icon-button";
import type { Config } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { isMonoSetting, SETTING_HINTS, settingLabel } from "./labels";
import { SettingControl } from "./SettingControl";
import { configId } from "./settingsModel";

const EFFECT_TAG: Partial<Record<Config["effect"], string>> = {
  STORED_ONLY: "僅儲存、不影響引擎",
  UNVERIFIED: "尚未驗證對映",
};

export function rangeHint(c: Config): string | null {
  if (c.valueType !== "INTEGER" && c.valueType !== "LONG" && c.valueType !== "FLOAT") return null;
  const { min, max } = c;
  if (min != null && max != null) return `範圍 ${min}～${max}`;
  if (min != null) return `最小 ${min}`;
  if (max != null) return `最大 ${max}`;
  return null;
}

export type SettingRowProps = {
  config: Config;
  value: string;
  dirty: boolean;
  /** 驗證紅字（本地驗證或後端 400 對應到這列） */
  error?: string | null;
  /** 整列不可編輯（非 ADMIN 或儲存中） */
  disabled: boolean;
  onChange: (value: string) => void;
  canReset: boolean;
  resetHint?: string;
  onReset: () => void;
  visible?: boolean;
  onToggleVisible?: () => void;
  canReveal?: boolean;
  revealing?: boolean;
};

export function SettingRow({
  config: c,
  value,
  dirty,
  error,
  disabled,
  onChange,
  canReset,
  resetHint,
  onReset,
  visible,
  onToggleVisible,
  canReveal,
  revealing,
}: SettingRowProps) {
  const id = configId(c);
  const label = settingLabel(c.category, c.key);
  const range = rangeHint(c);
  const hint = SETTING_HINTS[id];
  const effect = EFFECT_TAG[c.effect];
  return (
    <div
      data-testid="setting-row"
      data-setting={id}
      data-dirty={dirty || undefined}
      className="grid grid-cols-[220px_1fr] gap-x-6 gap-y-1 border-t border-wg-line py-4 first:border-t-0 max-md:grid-cols-1"
    >
      <div className="min-w-0">
        <div className="text-[15px] font-medium break-words">{label}</div>
        {c.description ? <div className="mt-0.5 text-xs leading-relaxed text-wg-muted">{c.description}</div> : null}
        {effect ? (
          <span
            data-testid="effect-tag"
            className="mt-1.5 inline-flex rounded-sm border border-wg-line bg-wg-base px-1.5 py-0.5 text-[11px] text-wg-muted"
          >
            {effect}
          </span>
        ) : null}
      </div>
      <div className="min-w-0">
        <div className="flex max-w-[560px] items-center gap-2">
          <SettingControl
            config={c}
            label={label}
            value={value}
            onChange={onChange}
            disabled={disabled}
            invalid={Boolean(error)}
            mono={isMonoSetting(c.category, c.key)}
            visible={visible}
            onToggleVisible={onToggleVisible}
            canReveal={canReveal}
            revealing={revealing}
          />
          <IconButton
            icon={RotateCcw}
            label={`重置：${label}`}
            size={36}
            disabled={!canReset}
            title={canReset ? `重置為預設值：${label}` : resetHint}
            onClick={onReset}
          />
        </div>
        {hint || range ? (
          <p className="mt-1.5 text-xs text-wg-muted" data-testid="setting-hint">
            {[hint, range].filter(Boolean).join("；")}
          </p>
        ) : null}
        {c.impactNote ? (
          <p className="mt-1.5 flex items-start gap-1.5 text-xs text-wg-muted" data-testid="impact-note">
            <Info size={14} className="mt-px shrink-0 text-wg-secondary" aria-hidden />
            <span className="break-words">{c.impactNote}</span>
          </p>
        ) : null}
        {error ? (
          <p role="alert" data-testid="setting-error" className={cn("mt-1.5 text-[13px] break-words text-wg-error")}>
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
