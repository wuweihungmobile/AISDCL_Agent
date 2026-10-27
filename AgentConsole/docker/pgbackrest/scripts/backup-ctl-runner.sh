#!/usr/bin/env bash
# docker/pgbackrest/scripts/backup-ctl-runner.sh — sidecar 控制面的迴圈：清掃、心跳、匯出
# （Console「系統管理／資料庫備份」；PRD §9.2／§9.3、TCS-SysAdminBackup-20261027 §C1／§C2）
#
# 用法：backup-ctl-runner.sh [--once]      `--once`＝只做一輪（測試與診斷用）
# 由 pgbackrest-entrypoint.sh 以 postgres 身分在背景啟動（compose 的 sidecar 容器；只在 Linux 容器內執行）。
#
# 每輪（≤ BACKUP_CTL_POLL_SECONDS，預設 5 秒）：
#   1. 清掃：把「進行中但維護鎖沒有持有者」的工作改記 interrupted（呼叫 backup-ctl-export.sh sweep）
#   2. 原子更新 export/heartbeat ＝ {schema_rev:1, ts, lock_held}（console-api 以 30 秒判斷 runner 是否離線）
#   3. 必要時以 `timeout $BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` 在背景啟動匯出子行程（backup-ctl-export.sh）：
#      每 BACKUP_CTL_EXPORT_SECONDS（60）秒一次，以及維護鎖由「有持有者」變成「沒有」（一個工作結束）之後的下一輪；
#      前一個還沒結束就略過，不重疊
#   階段二：請求處理（R-BK-46／R-BK-47）接在第 3 步之後——掃 $BACKUP_CTL_REQ_DIR、撿最舊且 results 尚不存在的
#   合法請求、先寫 results（running）再背景啟動 `job-run.sh <type> manual <id>`。階段一沒有請求，這個目錄只是掛著。
# 啟動時另清 $BACKUP_CTL_REQ_DIR 內 mtime 逾 24 小時的請求檔（只記 WARN）——請求卷在 sidecar 是 ro 掛載，刪不掉時
# 只記一行 WARN（殘檔由寫入端 console-api 清；這裡能刪的場合只有測試與卷被改成可寫）。
#
# 🔴 迴圈永不等待子行程（工作、匯出皆背景）：長工作與匯出逾時都不使心跳中斷，否則 console-api 會誤報「控制面無回應」。
# 🔴 對維護鎖零次 flock 呼叫：lock_held 只讀 /proc/locks 比對鎖檔 dev:ino（見 backup-ctl-export.sh 同名函式）。
# 🔴 不用 set -e：單一步驟失敗只記 WARN，迴圈照常（runner 死掉只剩心跳過期可見）。
# 環境變數（預設值即生產值，只供測試與調參）：BACKUP_CTL_OUT_DIR、BACKUP_CTL_REQ_DIR、BACKUP_CTL_LOCK_FILE、
#   BACKUP_CTL_POLL_SECONDS、BACKUP_CTL_EXPORT_SECONDS、BACKUP_CTL_EXPORT_TIMEOUT_SECONDS。
set -u

once=0
if [ "${1:-}" = "--once" ]; then once=1; fi

ctl_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
out_dir="${BACKUP_CTL_OUT_DIR:-/backup-out}"
req_dir="${BACKUP_CTL_REQ_DIR:-/backup-req}"
lock_file="${BACKUP_CTL_LOCK_FILE:-/run/backup-ctl/maintenance.lock}"
poll="${BACKUP_CTL_POLL_SECONDS:-5}"
case "$poll" in '' | *[!0-9]*) poll=5 ;; esac
export_seconds="${BACKUP_CTL_EXPORT_SECONDS:-60}"
case "$export_seconds" in '' | *[!0-9]*) export_seconds=60 ;; esac
export_timeout="${BACKUP_CTL_EXPORT_TIMEOUT_SECONDS:-120}"
case "$export_timeout" in '' | *[!0-9]*) export_timeout=120 ;; esac
export_dir="$out_dir/export"
results_dir="$out_dir/results"

log() { printf '[%s] [backup-ctl-runner] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# 寫同目錄的 .tmp 後經 mv 改名（改名一律經 mv 命令名）；檔 0644（讀取端是另一個 uid）
write_atomic() {
  local dest="$1" tmp
  tmp="${dest}.tmp.$$"
  if cat > "$tmp" 2> /dev/null && chmod 0644 "$tmp" 2> /dev/null && mv -f "$tmp" "$dest" 2> /dev/null; then
    return 0
  fi
  rm -f "$tmp" 2> /dev/null
  return 1
}

# 目錄 0755；umask 不可信，逐層 install -d
ensure_dirs() {
  local d
  for d in "$out_dir" "$export_dir" "$export_dir/jobs" "$results_dir"; do
    [ -d "$d" ] || install -d -m 0755 -- "$d" 2> /dev/null || true
  done
}

# 維護鎖有沒有持有者：只讀 /proc/locks 比對鎖檔的 dev:ino（major:minor 是十六進位、inode 是十進位），不取鎖。
# 只算持有者的列（排隊等待的列在類型前多一個 `->`）。印 true 或 false。
lock_held() {
  local dev ino key
  if [ ! -e "$lock_file" ]; then
    echo false
    return 0
  fi
  dev="$(stat -c '%d' -- "$lock_file" 2> /dev/null)" || dev=""
  ino="$(stat -c '%i' -- "$lock_file" 2> /dev/null)" || ino=""
  if [ -z "$dev" ] || [ -z "$ino" ]; then
    echo false
    return 0
  fi
  key="$(printf '%02x:%02x:%d' $(((dev >> 8) & 0xfff)) $(((dev & 0xff) | ((dev >> 12) & 0xfff00))) "$ino")"
  if awk -v k="$key" '$2 != "->" && $6 == k { found = 1 } END { exit !found }' /proc/locks 2> /dev/null; then
    echo true
  else
    echo false
  fi
}

# 啟動時清逾 24 小時的請求檔（只認一般檔，不跟隨符號連結；WARN 不帶檔名）
clean_stale_requests() {
  local f removed=0 failed=0
  [ -d "$req_dir" ] || return 0
  while IFS= read -r -d '' f; do
    if rm -f -- "$f" 2> /dev/null && [ ! -e "$f" ]; then removed=$((removed + 1)); else failed=$((failed + 1)); fi
  done < <(find "$req_dir" -maxdepth 1 -type f -name '*.json' -mmin +1440 -print0 2> /dev/null)
  if [ "$removed" -gt 0 ]; then log "WARN: 已清除 $removed 份逾 24 小時的殘留請求檔"; fi
  if [ "$failed" -gt 0 ]; then
    log "WARN: $failed 份逾 24 小時的殘留請求檔無法刪除（請求卷在 sidecar 是唯讀掛載時屬預期，由 console-api 端清理）"
  fi
}

export_pid=""
last_export=0
export_due=0
prev_held=false

# 背景啟動匯出子行程：前一個還沒結束就略過（不重疊、不共用 .tmp）
maybe_start_export() {
  local now
  now="$(date +%s)"
  if [ -n "$export_pid" ] && kill -0 "$export_pid" 2> /dev/null; then return 0; fi
  if [ "$export_due" = "1" ] || [ $((now - last_export)) -ge "$export_seconds" ]; then
    if [ "$once" = "1" ]; then
      # 一輪就結束的模式：子行程不握著呼叫端的 stdout／stderr，免得呼叫端（測試的 exec）等它
      timeout "$export_timeout" bash "$ctl_dir/backup-ctl-export.sh" > /dev/null 2>&1 < /dev/null &
    else
      timeout "$export_timeout" bash "$ctl_dir/backup-ctl-export.sh" < /dev/null &
    fi
    export_pid=$!
    last_export="$now"
    export_due=0
  fi
}

round() {
  local held
  ensure_dirs
  # 清掃只讀幾個小檔，30 秒是安全上限：卡住的清掃不該連帶讓心跳停下來（心跳＝runner 迴圈還活著）
  timeout 30 bash "$ctl_dir/backup-ctl-export.sh" sweep || log "WARN: 清掃失敗或逾時"
  held="$(lock_held)"
  printf '{"schema_rev":1,"ts":"%s","lock_held":%s}\n' "$(now_iso)" "$held" \
    | write_atomic "$export_dir/heartbeat" || log "WARN: 心跳寫入失敗"
  if [ "$prev_held" = "true" ] && [ "$held" = "false" ]; then export_due=1; fi
  prev_held="$held"
  maybe_start_export
}

clean_stale_requests
while true; do
  round
  if [ "$once" = "1" ]; then break; fi
  sleep "$poll"
done
exit 0
