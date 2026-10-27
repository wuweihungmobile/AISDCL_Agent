#!/usr/bin/env bash
# docker/pgbackrest/tests/stubs/_stub_job_common.sh — 四支 stub 工作腳本共用的行為（TCS-SysAdminBackup-20261027 §5.4）
# 用法：_stub_job_common.sh <full|diff|dump|verify>（由 backup-full.sh、backup-incr.sh、pg_dump-offsite.sh、
# verify-backup.sh 的 stub 版 exec 進來）；只在 Linux 容器內用。
# 行為由環境變數決定（都選填；預設＝立刻印 `stub <kind> done` 並 rc 0）：
#   STUB_JOB_SLEEP        睡眠秒數（預設 0；可小數）
#   STUB_JOB_RC           結束碼（預設 0）
#   STUB_JOB_OUT          印到 stdout 的一行（例 OUT-LINE）
#   STUB_JOB_ERR          印到 stderr 的一行（例 ERR-LINE）
#   STUB_JOB_PROBE_FILE   把該檔每一行的第一欄印到 stdout（遮罩探針；見 fixtures/mask-probes.txt）
#   STUB_JOB_BG_SLEEP     先在背景啟動 `sleep N &` 再結束（模擬 verify 起的暫存 PG：會繼承檔案描述子）
#   STUB_JOB_RUNLOG       有設就把 <kind> 追加一行（數行數＝執行次數；驗證至多一次）
#   STUB_JOB_TIMELOG      有設就追加 `<kind> start <毫秒>`／`<kind> end <毫秒>`（驗證排程互斥不重疊）
#   STUB_JOB_MARKER       有設就寫入 `1`（STUB_JOB_RESULTS_FILE 已存在）或 `0`（不存在）——驗證 runner 先寫 results 再啟動腳本
#   STUB_JOB_RESULTS_FILE 配合 STUB_JOB_MARKER 的檢查對象
# 最後一行 stdout 恆為 `stub <kind> done`。
set -u

kind="${1:?usage: _stub_job_common.sh <full|diff|dump|verify>}"

if [ -n "${STUB_JOB_RUNLOG:-}" ]; then printf '%s\n' "$kind" >> "$STUB_JOB_RUNLOG"; fi
if [ -n "${STUB_JOB_TIMELOG:-}" ]; then printf '%s start %s\n' "$kind" "$(date +%s%3N)" >> "$STUB_JOB_TIMELOG"; fi
if [ -n "${STUB_JOB_MARKER:-}" ]; then
  if [ -e "${STUB_JOB_RESULTS_FILE:-/nonexistent}" ]; then
    printf '1' > "$STUB_JOB_MARKER"
  else
    printf '0' > "$STUB_JOB_MARKER"
  fi
fi
if [ -n "${STUB_JOB_BG_SLEEP:-}" ]; then sleep "$STUB_JOB_BG_SLEEP" & fi
if [ -n "${STUB_JOB_OUT:-}" ]; then printf '%s\n' "$STUB_JOB_OUT"; fi
if [ -n "${STUB_JOB_ERR:-}" ]; then printf '%s\n' "$STUB_JOB_ERR" >&2; fi
if [ -n "${STUB_JOB_PROBE_FILE:-}" ]; then
  while IFS=$'\t' read -r line _rest; do
    case "$line" in '' | '#'*) continue ;; esac
    printf '%s\n' "$line"
  done < "$STUB_JOB_PROBE_FILE"
fi
sleep "${STUB_JOB_SLEEP:-0}"
printf 'stub %s done\n' "$kind"
if [ -n "${STUB_JOB_TIMELOG:-}" ]; then printf '%s end %s\n' "$kind" "$(date +%s%3N)" >> "$STUB_JOB_TIMELOG"; fi
exit "${STUB_JOB_RC:-0}"
