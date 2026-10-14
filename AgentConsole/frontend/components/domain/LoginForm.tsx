"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Bot, LogIn } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { useAuth, useRedirectWhenAuthed } from "@/lib/auth/AuthProvider";

const schema = z.object({
  username: z.string().trim().min(1, "請輸入使用者名稱"),
  password: z.string().min(1, "請輸入密碼"),
});
type Values = z.infer<typeof schema>;

/** 只接受站內相對路徑，避免 next 參數被拿去做開放式轉址。 */
export function safeNext(raw: string | null): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : "/";
}

/** 登入頁（不在設計稿；風格依 token）：置中白卡、單一主色動作。 */
export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { username: "", password: "" } });

  useRedirectWhenAuthed(next);

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await login(values.username, values.password);
      router.replace(next);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setFormError("帳號或密碼錯誤");
      else if (e instanceof ApiError) setFormError(e.traceId ? `${e.message}（traceId：${e.traceId}）` : e.message);
      else setFormError("登入失敗，請稍後再試");
    }
  }

  return (
    <div className="flex min-h-full items-start justify-center pt-12 max-md:pt-4">
      <Card className="w-full max-w-[420px] p-8 max-md:p-6">
        <div className="mb-6 flex items-center gap-3">
          <span className="inline-flex size-12 items-center justify-center rounded-[10px] bg-wg-tertiary">
            <Bot size={26} className="text-wg-primary" aria-hidden />
          </span>
          <div>
            <h1 className="text-[24px] font-bold">登入 AISDLC Console</h1>
            <p className="text-sm text-wg-muted">AGENT CONTROL PANEL</p>
          </div>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Field label="使用者名稱" error={errors.username?.message}>
            <Input
              autoComplete="username"
              autoFocus
              aria-invalid={errors.username ? true : undefined}
              {...register("username")}
            />
          </Field>
          <Field label="密碼" error={errors.password?.message}>
            <Input
              type="password"
              autoComplete="current-password"
              aria-invalid={errors.password ? true : undefined}
              {...register("password")}
            />
          </Field>
          {formError ? (
            <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
              {formError}
            </p>
          ) : null}
          <Button type="submit" size="lg" iconLeft={LogIn} loading={isSubmitting} className="mt-1 w-full">
            登入
          </Button>
        </form>
      </Card>
    </div>
  );
}
