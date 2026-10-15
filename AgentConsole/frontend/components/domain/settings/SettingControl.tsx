"use client";

/**
 * 參數控制項（設計稿畫面 9）：依 valueType 渲染——
 *  STRING／INTEGER／LONG／FLOAT → input（44px、圓角 8px；數值用 inputMode，不用 type=number，
 *  才能讓使用者輸入到一半的非法值也看得到並收到驗證紅字）；ENUM → select；
 *  BOOLEAN → 自訂 toggle（46×26，knob 20）；ENCRYPTED → password input ＋ 顯示／隱藏。
 * 這支元件只管「怎麼畫、怎麼回報輸入」，不知道儲存、驗證與角色（由 SettingRow／SettingsView 決定）。
 */
import { Eye, EyeOff } from "lucide-react";
import { Switch } from "radix-ui";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { Config } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { MASK } from "./settingsModel";

export type SettingControlProps = {
  config: Config;
  /** 無障礙名稱（通常是中文標籤） */
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
  /** 等寬字體（URL、路徑、命令等技術字串） */
  mono?: boolean;
  /** ENCRYPTED：目前是否以明文顯示 */
  visible?: boolean;
  onToggleVisible?: () => void;
  /** ENCRYPTED：能否揭露（僅 ADMIN） */
  canReveal?: boolean;
  /** ENCRYPTED：揭露請求進行中 */
  revealing?: boolean;
};

export function SettingControl({
  config,
  label,
  value,
  onChange,
  disabled = false,
  invalid = false,
  mono = false,
  visible = false,
  onToggleVisible,
  canReveal = false,
  revealing = false,
}: SettingControlProps) {
  switch (config.valueType) {
    case "BOOLEAN":
      return (
        <Switch.Root
          checked={value === "true"}
          onCheckedChange={(on) => onChange(on ? "true" : "false")}
          disabled={disabled}
          aria-label={label}
          data-testid="setting-toggle"
          className="relative h-[26px] w-[46px] shrink-0 cursor-pointer rounded-full border-none bg-wg-disabled-text p-0 transition-colors data-[state=checked]:bg-wg-primary disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Switch.Thumb className="absolute top-[3px] left-[3px] block size-5 rounded-full bg-white transition-[left] data-[state=checked]:left-[23px]" />
        </Switch.Root>
      );

    case "ENUM": {
      const options = config.options ?? [];
      // 目前值不在選項內（後端新增選項、舊資料）時仍要顯示出來，避免 select 悄悄跳到第一項
      const shown = options.includes(value) || value === "" ? options : [...options, value];
      return (
        <Select aria-label={label} aria-invalid={invalid || undefined} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {shown.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </Select>
      );
    }

    case "ENCRYPTED": {
      const masked = value === MASK;
      return (
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Input
            type={visible ? "text" : "password"}
            aria-label={label}
            aria-invalid={invalid || undefined}
            value={value}
            disabled={disabled}
            autoComplete="off"
            spellCheck={false}
            placeholder={config.hasValue ? undefined : "尚未設定"}
            className="min-w-0 flex-1 font-mono text-sm"
            // 遮罩字串不是真值：聚焦就全選，輸入時直接取代，而不是接在 ●●●●●●●● 後面
            onFocus={(e) => masked && e.currentTarget.select()}
            onChange={(e) => onChange(e.target.value)}
          />
          <Button
            variant="ghost"
            size="sm"
            iconLeft={visible ? EyeOff : Eye}
            loading={revealing}
            disabled={disabled || !canReveal || !config.hasValue}
            title={canReveal ? (config.hasValue ? undefined : "尚未設定，沒有可顯示的值") : "僅 ADMIN 可揭露敏感參數"}
            aria-label={`${visible ? "隱藏" : "顯示"}：${label}`}
            onClick={onToggleVisible}
          >
            {visible ? "隱藏" : "顯示"}
          </Button>
        </div>
      );
    }

    case "INTEGER":
    case "LONG":
    case "FLOAT":
    case "STRING":
    default:
      return (
        <Input
          aria-label={label}
          aria-invalid={invalid || undefined}
          value={value}
          disabled={disabled}
          inputMode={config.valueType === "FLOAT" ? "decimal" : config.valueType === "STRING" ? "text" : "numeric"}
          autoComplete="off"
          spellCheck={false}
          className={cn("min-w-0 flex-1", mono && "font-mono text-sm")}
          onChange={(e) => onChange(e.target.value)}
        />
      );
  }
}
