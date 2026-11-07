"use client";

/**
 * 單一未覆蓋 AC 的人工豁免理由輸入（AC-R2P-14-2、14-3；AT-961-18-2）：一句話、1～500 字；不設 `maxLength`，
 * 超長要讓使用者看見欄位錯誤（無效），而不是被瀏覽器默默截斷。是否有效由 `waiverReasonError` 判（呼叫端算好 `error` 傳入）。
 */
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { WAIVER_REASON_MAX } from "@/lib/domain/research";

export function WaiverInput({
  ac,
  value,
  onChange,
  disabled,
  title,
  error,
}: {
  ac: string;
  value: string;
  onChange: (next: string) => void;
  disabled: boolean;
  /** 停用時的說明（唯讀、已完成、規格變更中） */
  title?: string;
  /** 欄位錯誤（只在輸入過、卻無效時給；空輸入不顯示錯誤，由簽核停用原因說明） */
  error?: string;
}) {
  return (
    <Field label={`豁免理由：${ac}`} hint={`一句話，最多 ${WAIVER_REASON_MAX} 字`} error={error}>
      <Input value={value} disabled={disabled} title={disabled ? title : undefined} aria-invalid={error ? true : undefined} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}
