#!/usr/bin/env bash
# docker/pgbackrest/scripts/job-run.sh — 備份工作的包裝：維護鎖＋狀態檔＋遮罩後的輸出尾段
# （Console「系統管理／資料庫備份」的 sidecar 控制面；PRD §9.3、TCS-SysAdminBackup-20261027 §C1／§C2）
#
# 用法：job-run.sh <full|diff|dump|verify> <scheduled|manual> [<uuid>]
#   full→backup-full.sh、diff→backup-incr.sh、dump→pg_dump-offsite.sh、verify→verify-backup.sh
#   （工作腳本在 $BACKUP_CTL_SCRIPT_DIR，預設 /usr/local/bin；本檔不修改它們，也不碰它們各自維護的狀態檔）
#   crontab 的四條備份與驗證工作都經這支（scheduled）；手動請求由 backup-ctl-runner.sh 帶 <uuid> 啟動（manual，階段二）。
#
# 做什麼：
#   1. 命令形 `flock -o` 取維護鎖（sidecar 本地 /run/backup-ctl/maintenance.lock，不在共享卷）：
#      排程等待至 JOB_LOCK_WAIT_SECONDS（預設 7200），逾時＝不執行腳本、jobs 記 failed／lock_timeout／rc 75；
#      手動不等待，拿不到＝立即 rc 75（busy，不改狀態檔）。鎖檔開不了＝fail-open（照常執行、WARN、note=locking:unavailable）。
#   2. 持鎖期間：寫 jobs/<job>.json（running）→ 執行工作腳本（stdout、stderr 原樣透傳並同步擷取）→ 寫終態
#      （遮罩後取最後 2000 字元；有 <uuid> 時一併寫 results/<uuid>.json）→ 之後才釋放鎖。
#      終態一定要在持鎖行程內寫完：否則匯出的清掃會在「腳本已結束、狀態仍 running、鎖已釋放」的空窗把正常結束的
#      工作誤判成 interrupted。
#   3. 結束碼＝工作腳本的 rc 原樣；唯一例外是 75（EX_TEMPFAIL）：專指「手動拿不到鎖」與「排程等鎖逾時」。
#      （flock 的衝突碼就設成 75，所以工作腳本自己若回 75 會與之混淆——現有四支腳本不會。）
#
# 🔴 這支在每一條排程備份的路徑上（PRD §10 R1：包裝出錯＝排程備份失敗）：所以刻意不用 set -e／pipefail，
#   每一步都有退路——狀態檔寫不了、鎖開不了、擷取檔建不起來、遮罩失敗，一律 WARN 後照常執行並原樣回傳 rc。
# 🔴 不用 fd 形持鎖（`exec 9>`／`flock 9`）：fd 形持鎖時 /proc/locks 沒有該檔的列（lock_held 看不到），且 verify
#   起的暫存 PG 會繼承鎖 fd 而把鎖卡住；命令形加 -o 讓持鎖者是活的 flock 行程、子行程不繼承。
# 環境變數（預設值即生產值，只供測試與調參）：BACKUP_CTL_OUT_DIR、BACKUP_CTL_LOCK_FILE、BACKUP_CTL_SCRIPT_DIR、
#   JOB_LOCK_WAIT_SECONDS。
set -u

self="${BASH_SOURCE[0]}"
locked=0
if [ "${1:-}" = "--locked" ]; then
  locked=1
  shift
fi
job="${1:-}"
trigger="${2:-}"
request_id="${3:-}"

out_dir="${BACKUP_CTL_OUT_DIR:-/backup-out}"
lock_file="${BACKUP_CTL_LOCK_FILE:-/run/backup-ctl/maintenance.lock}"
script_dir="${BACKUP_CTL_SCRIPT_DIR:-/usr/local/bin}"
wait_seconds="${JOB_LOCK_WAIT_SECONDS:-7200}"
case "$wait_seconds" in '' | *[!0-9]*) wait_seconds=7200 ;; esac
jobs_dir="$out_dir/export/jobs"
results_dir="$out_dir/results"
conflict_rc=75

warn() { printf '[job-run] WARN: %s\n' "$*" >&2; }

usage() {
  printf 'usage: job-run.sh <full|diff|dump|verify> <scheduled|manual> [<uuid>]\n' >&2
  exit 2
}

case "$job" in
  full) work="backup-full.sh" ;;
  diff) work="backup-incr.sh" ;;
  dump) work="pg_dump-offsite.sh" ;;
  verify) work="verify-backup.sh" ;;
  *) usage ;;
esac
case "$trigger" in scheduled | manual) ;; *) usage ;; esac
uuid_re='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if [ -n "$request_id" ] && ! [[ "$request_id" =~ $uuid_re ]]; then
  # results 的檔名由它組成：不是小寫 UUID 一律不寫 results（擋路徑穿越），工作照跑
  warn "第三個引數不是小寫 UUID，不寫 results"
  request_id=""
fi
state_file="$jobs_dir/$job.json"

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# 寫同目錄的 .tmp 後經 mv 改名（改名一律經 mv 命令名：測試替身才攔得到）；檔 0644（讀取端是另一個 uid）
write_atomic() {
  local dest="$1" tmp
  tmp="${dest}.tmp.$$"
  if cat > "$tmp" 2> /dev/null && chmod 0644 "$tmp" 2> /dev/null && mv -f "$tmp" "$dest" 2> /dev/null; then
    return 0
  fi
  rm -f "$tmp" 2> /dev/null
  return 1
}

# 目錄 0755（讀取端是另一個 uid）；umask 不可信，逐層 install -d；失敗（唯讀、非擁有者）只是之後寫檔時 WARN
ensure_dirs() {
  local d
  for d in "$out_dir" "$out_dir/export" "$jobs_dir" "$results_dir"; do
    [ -d "$d" ] || install -d -m 0755 -- "$d" 2> /dev/null || true
  done
}

# 遮罩：鍵名含 pass／secret／key／token 且後接 = 或 : ⇒ 值改 ***（保留鍵名與分隔）；AWS 存取金鑰 id ⇒ ***；
# 連線字串 scheme://user:密碼@host ⇒ 密碼改 ***。只認形狀、不因 example／fake 放行；冪等。
# 規格與探針見 tests/fixtures/mask-probes.txt（與 console-api 的 BackupMasker 共讀同一檔，兩邊逐字相同）。
mask_output() {
  LC_ALL=C perl -pe '
    s/(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])/***/g;
    s{([A-Za-z][A-Za-z0-9+.\-]*://[^\s:/@]+:)[^\s@/]+(@)}{$1***$2}g;
    s/((?:pass|secret|key|token)[A-Za-z0-9_.\-]{0,64}["\x27]?\s*[=:]\s*)("[^"]*"|\x27[^\x27]*\x27|[^\s,;&"\x27]+)/$1***/gi;
  '
}

# jobs/<job>.json 的內容（stdout）：$1 狀態 $2 rc（數字或 null）$3 理由 $4 開始 $5 結束 $6 last_success_at $7 輸出尾段檔
build_state() {
  jq -c -n \
    --arg job "$job" --arg trigger "$trigger" --arg status "$1" --argjson rc "$2" --arg reason "$3" \
    --arg started "$4" --arg finished "$5" --arg success "$6" --arg note "$note" --rawfile tail "$7" '
    {schema_rev: 1, job: $job,
     last: {trigger: $trigger, status: $status, rc: $rc,
            reason: (if $reason == "" then null else $reason end),
            started_at: $started,
            finished_at: (if $finished == "" then null else $finished end),
            detail_tail: ($tail | .[-2000:]),
            note: (if $note == "" then null else $note end)},
     last_success_at: (if $success == "" then null else $success end)}'
}

write_state() {
  local json
  if json="$(build_state "$@")" && [ -n "$json" ] && printf '%s\n' "$json" | write_atomic "$state_file"; then
    return 0
  fi
  warn "狀態檔 $state_file 寫入失敗（工作照常執行，rc 與輸出不受影響）"
  return 1
}

# results/<uuid>.json 的終態：$1 狀態 $2 理由 $3 rc $4 結束 $5 輸出尾段檔；started_at 沿用 runner 寫下的「撿起時刻」
write_results() {
  [ -n "$request_id" ] || return 0
  local rfile="$results_dir/$request_id.json" picked="" json
  if [ -f "$rfile" ]; then picked="$(jq -r '.started_at // empty' "$rfile" 2> /dev/null)" || picked=""; fi
  [ -n "$picked" ] || picked="$started_at"
  if json="$(jq -c -n --arg id "$request_id" --arg type "$job" --arg status "$1" --arg reason "$2" \
    --argjson rc "$3" --arg started "$picked" --arg finished "$4" --rawfile tail "$5" '
    {schema_rev: 1, id: $id, type: $type, status: $status,
     reason: (if $reason == "" then null else $reason end), rc: $rc,
     started_at: $started, finished_at: $finished, detail_tail: ($tail | .[-2000:])}')" \
    && [ -n "$json" ] && printf '%s\n' "$json" | write_atomic "$rfile"; then
    return 0
  fi
  warn "results/$request_id.json 寫入失敗"
  return 1
}

# 上一次成功的時間（失敗與中斷都不覆蓋它）；檔案缺席、壞掉或格式不對一律當作沒有
read_prev_success() {
  local value=""
  if [ -f "$state_file" ]; then value="$(jq -r '.last_success_at // empty' "$state_file" 2> /dev/null)" || value=""; fi
  case "$value" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z) printf '%s' "$value" ;;
  esac
}

# ── 外層（未持鎖）：取鎖、處理 busy／lock_timeout／鎖不可用 ───────────────────────────────────────────
if [ "$locked" != "1" ]; then
  if ! command -v flock > /dev/null 2>&1; then
    warn "找不到 flock，照常執行但不互斥（note=locking:unavailable）"
    JOB_RUN_NOTE="locking:unavailable" exec bash "$self" --locked "$job" "$trigger" "$request_id"
  fi
  # 鎖檔要「讀得開」（flock 只需讀取權限）；不存在才建立。🔴 不可用寫入模式預檢既有的鎖檔：root 建立過的鎖檔
  # postgres 寫不開但讀得開，用寫入預檢會把之後每一次排程都誤判成「鎖不可用」而靜默失去互斥。
  mkdir -p -- "$(dirname -- "$lock_file")" 2> /dev/null || true
  if [ ! -e "$lock_file" ]; then (: >> "$lock_file") 2> /dev/null; fi
  if ! (: < "$lock_file") 2> /dev/null; then
    warn "維護鎖檔 $lock_file 無法開啟，照常執行但不互斥（note=locking:unavailable）"
    JOB_RUN_NOTE="locking:unavailable" exec bash "$self" --locked "$job" "$trigger" "$request_id"
  fi
  started_at="$(now_iso)"
  if [ "$trigger" = "manual" ]; then
    flock -n -E "$conflict_rc" -o "$lock_file" bash "$self" --locked "$job" "$trigger" "$request_id"
  else
    flock -w "$wait_seconds" -E "$conflict_rc" -o "$lock_file" bash "$self" --locked "$job" "$trigger" "$request_id"
  fi
  rc=$?
  if [ "$rc" -ne "$conflict_rc" ]; then exit "$rc"; fi
  # 衝突碼：工作腳本沒有被執行
  if [ "$trigger" = "manual" ]; then
    printf '[job-run] busy: 維護鎖被持有，手動 %s 請求未執行（rc=%s）\n' "$job" "$conflict_rc" >&2
    exit "$conflict_rc"
  fi
  message="[job-run] lock_timeout: 等待維護鎖 ${wait_seconds} 秒仍被持有，${job} 未執行（rc=${conflict_rc}）"
  printf '%s\n' "$message" >&2
  note=""
  ensure_dirs
  msg_file="$(mktemp "${TMPDIR:-/tmp}/job-run.XXXXXX" 2> /dev/null)" || msg_file=/dev/null
  printf '%s\n' "$message" > "$msg_file" 2> /dev/null
  write_state failed "$conflict_rc" lock_timeout "$started_at" "$(now_iso)" "$(read_prev_success)" "$msg_file"
  if [ "$msg_file" != "/dev/null" ]; then rm -f "$msg_file"; fi
  exit "$conflict_rc"
fi

# ── 內層（持鎖；鎖不可用時 fail-open 也走這裡）────────────────────────────────────────────────────────
note=""
if [ "${JOB_RUN_NOTE:-}" = "locking:unavailable" ]; then note="locking:unavailable"; fi
started_at="$(now_iso)"
cap="$(mktemp "${TMPDIR:-/tmp}/job-run.XXXXXX" 2> /dev/null)" || cap=""
tail_file="$(mktemp "${TMPDIR:-/tmp}/job-run.XXXXXX" 2> /dev/null)" || tail_file=""
trap 'rm -f "$cap" "$tail_file" 2> /dev/null' EXIT

ensure_dirs
prev_success="$(read_prev_success)"
write_state running null "" "$started_at" "" "$prev_success" /dev/null

# 等擷取用的 tee 排乾管線（EOF）。若有殘留的子行程（例如 verify 起的暫存 PG）仍握著管線寫端，最多等 3 秒就放棄並結束 tee，
# 免得卡住鎖與呼叫端的 stdout（擷取檔已含工作腳本自己寫的全部輸出）。
drain_tees() {
  local waited=0
  while { kill -0 "$1" 2> /dev/null || kill -0 "$2" 2> /dev/null; } && [ "$waited" -lt 30 ]; do
    sleep 0.1
    waited=$((waited + 1))
  done
  kill "$1" "$2" 2> /dev/null || true
}

# 工作腳本原本怎麼被 cron 呼叫就怎麼執行（可執行就直接執行；否則走 bash）；stdout、stderr 各自透傳到原本的目的地，
# 同時各自追加進同一個擷取檔（兩個 tee 各自 O_APPEND，順序近似實際輸出序）。
run_work() {
  local script="$script_dir/$work" runner out_pid err_pid rc
  if [ ! -f "$script" ]; then
    printf '[job-run] ERROR: 找不到工作腳本 %s\n' "$script" >&2
    return 127
  fi
  runner=("$script")
  [ -x "$script" ] || runner=(bash "$script")
  if [ -z "$cap" ]; then
    warn "擷取檔建不起來：照常執行，但沒有輸出尾段"
    "${runner[@]}"
    return $?
  fi
  # fd 7、8（不用 3、4：flock 命令形的鎖檔 fd 通常是 3，沿用它會讓「忘了 -o」被偶然遮住而測不出來）
  exec 7> >(tee -a "$cap")
  out_pid=$!
  exec 8> >(
    exec 7>&-
    exec tee -a "$cap" >&2
  )
  err_pid=$!
  "${runner[@]}" >&7 2>&8 7>&- 8>&-
  rc=$?
  exec 7>&- 8>&-
  drain_tees "$out_pid" "$err_pid"
  return "$rc"
}

run_work
rc=$?
finished_at="$(now_iso)"

# 先遮罩、後取最後 2000 字元（跨 2000 邊界的機密也要被遮到）；先砍到最後 64 KB 只為限制遮罩的成本
tail_src=/dev/null
if [ -n "$cap" ] && [ -n "$tail_file" ]; then
  if tail -c 65536 "$cap" 2> /dev/null | mask_output > "$tail_file" 2> /dev/null; then
    tail_src="$tail_file"
  else
    warn "輸出尾段遮罩失敗，狀態檔不附尾段"
  fi
fi

if [ "$rc" -eq 0 ]; then
  status=succeeded
  reason=""
  success="$finished_at"
else
  status=failed
  reason=script_failed
  success="$prev_success"
fi
write_state "$status" "$rc" "$reason" "$started_at" "$finished_at" "$success" "$tail_src"
write_results "$status" "$reason" "$rc" "$finished_at" "$tail_src"
exit "$rc"
