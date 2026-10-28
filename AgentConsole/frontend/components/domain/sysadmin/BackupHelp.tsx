"use client";

/**
 * 「還原與說明」分頁（TCS-SysAdminBackup-20261027 FR-BK-08、R-BK-43～45；PRD §5 AC-BK-08-1～08-3）：**只有說明，沒有按鈕**——不提供還原按鈕、不送任何請求（明寫原因：還原要先停 primary、
 * `restore.sh` 在 primary 運作時拒絕、replica 的時間軸會分岔須重建），所以這一頁的 DOM 裡沒有任何可聚焦的控制項。
 * 三塊內容：還原三步（停 primary → 容器內 restore.sh → 啟動並核對；bash 與 PowerShell 兩種形態）、還原後的核對三項（只有 bash 形態，PowerShell 以一句前後綴說明）、
 * 涵蓋範圍表（逐卷分類，並提醒兩把金鑰遺失就救不回來）。
 *
 * 設計要點（為什麼這樣做）：
 *  - 指令與涵蓋表的**資料都在 `lib/domain/sysadminBackup.ts`**（`RESTORE_STEPS`、`RESTORE_CHECKS`、`VOLUME_COVERAGE`）；它們分別由 `backup-docs.test.ts` 與真 `docker/README.md` 〈4.3〉、
 *    真 `docker-compose.yml` 的卷集合單向／雙向鎖住——README 或 compose 改了而這邊沒跟著改，`npx vitest run` 當場轉紅，畫面上的指令就不會悄悄過期。
 *  - 指令以 `<pre>` 顯示（可選取、不經 HTML 或 Markdown）；每一條都是整行的原字串，不拆、不改。
 */
import { CHECKS_POWERSHELL_NOTE, COVERAGE_CATEGORY_LABEL, KEY_LOSS_NOTE, NO_RESTORE_BUTTON_NOTE, RESTORE_CHECKS, RESTORE_STEPS, VOLUME_COVERAGE } from "@/lib/domain/sysadminBackup";

function CodeBlock({ label, lines }: { label: string; lines: readonly string[] }) {
  return (
    <div className="min-w-0">
      <p className="mb-1 text-xs font-medium text-wg-muted">{label}</p>
      <pre className="rounded-md border border-wg-line bg-white px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap text-wg-text">{lines.join("\n")}</pre>
    </div>
  );
}

export function BackupHelp() {
  return (
    <div data-testid="bk-help" className="flex flex-col gap-6">
      <section aria-labelledby="bk-help-restore" className="flex flex-col gap-3">
        <h3 id="bk-help-restore" className="text-base font-semibold">
          還原三步
        </h3>
        <p data-testid="bk-no-restore-note" className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm text-wg-warning-text">
          {NO_RESTORE_BUTTON_NOTE}
        </p>
        <ol data-testid="bk-restore-steps" className="flex flex-col gap-4">
          {RESTORE_STEPS.map((step) => (
            <li key={step.title} className="flex flex-col gap-2">
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-sm text-wg-muted">{step.description}</p>
              <div className="grid gap-3 xl:grid-cols-2">
                <CodeBlock label="bash" lines={step.bash} />
                <CodeBlock label="PowerShell" lines={step.powershell} />
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="bk-help-checks" className="flex flex-col gap-3">
        <h3 id="bk-help-checks" className="text-base font-semibold">
          還原後的核對三項
        </h3>
        <ol data-testid="bk-restore-checks" className="flex flex-col gap-3">
          {RESTORE_CHECKS.map((check) => (
            <li key={check.title} className="flex flex-col gap-1">
              <p className="text-sm font-medium">{check.title}</p>
              <p className="text-sm text-wg-muted">{check.hint}</p>
              <CodeBlock label="bash" lines={[check.command]} />
            </li>
          ))}
        </ol>
        <p className="text-sm text-wg-muted">{CHECKS_POWERSHELL_NOTE}</p>
      </section>

      <section aria-labelledby="bk-help-coverage" className="flex flex-col gap-3">
        <h3 id="bk-help-coverage" className="text-base font-semibold">
          涵蓋範圍：哪些資料有備份
        </h3>
        <div className="relative overflow-x-auto">
          <table data-testid="bk-coverage" className="w-full min-w-[40rem] border-collapse text-left text-sm">
            <caption className="sr-only">各資料卷的備份涵蓋範圍</caption>
            <thead>
              <tr className="border-b border-wg-line text-xs text-wg-muted">
                <th scope="col" className="py-2 pr-3">
                  資料卷
                </th>
                <th scope="col" className="py-2 pr-3">
                  分類
                </th>
                <th scope="col" className="py-2">
                  說明
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(VOLUME_COVERAGE).map(([volume, coverage]) => (
                <tr key={volume} data-testid={`bk-coverage-row-${volume}`} data-category={coverage.category} className="border-b border-wg-line align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{volume}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{COVERAGE_CATEGORY_LABEL[coverage.category]}</td>
                  <td className="py-2 break-words">{coverage.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p data-testid="bk-key-loss-note" className="text-sm font-medium text-wg-warning-text">
          {KEY_LOSS_NOTE}
        </p>
      </section>
    </div>
  );
}
