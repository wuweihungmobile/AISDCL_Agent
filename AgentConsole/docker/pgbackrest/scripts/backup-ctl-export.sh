#!/usr/bin/env bash
# docker/pgbackrest/scripts/backup-ctl-export.sh — 把備份狀態匯出成 console-api 讀得到的檔案
# （Console「系統管理／資料庫備份」的 sidecar 控制面；PRD §9.3、TCS-SysAdminBackup-20261027 §C1／§C2）
#
# 用法：
#   backup-ctl-export.sh            一輪匯出：清掃 interrupted → 原子寫 export/info.json →（距上次 ≥300 秒才）寫 export/logical.json
#                                   受單一實例鎖 export.lock（非維護鎖）保護，重疊則立即結束碼 0；
#                                   失敗只寫 ok:false、結束碼 0（要用「檔案內容」報告失敗，不是用結束碼）。
#   backup-ctl-export.sh schedule   由 crontab 與 TZ 產生 export/schedule.json（entrypoint 的 root 階段呼叫一次；
#                                   crontab 是 root:root 0600，只有 root 讀得到）
#   backup-ctl-export.sh sweep      只做清掃（runner 每輪呼叫）：把「進行中但維護鎖無持有者」的工作與 results 改記 interrupted
#
# 由 backup-ctl-runner.sh 每 BACKUP_CTL_EXPORT_SECONDS 秒與每次工作結束後以 `timeout $BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` 啟動。
# 被 timeout 的 TERM 終止時，正在寫的那份檔改記 ok:false（不留舊內容冒充新鮮）。
#
# 🔴 對維護鎖零次 flock 呼叫：lock_held 與清掃只讀 /proc/locks 比對鎖檔 dev:ino。用 flock -n 探測會短暫持鎖，
#   讓同時抵達的手動請求被誤判成 busy。維護鎖只由 job-run.sh 以命令形 flock -o 持有；本檔的 flock 只用在 export.lock。
# 🔴 pgbackrest info 的原輸出原樣嵌入（逐字，不經 jq 重新序列化）：system-id 這類 64 位元整數經 jq 1.6 會失真。
# 環境變數（預設值即生產值，只供測試與調參）：BACKUP_CTL_OUT_DIR、BACKUP_CTL_LOCK_FILE、BACKUP_CTL_CRONTAB、
#   BACKUP_CTL_POLL_SECONDS（孤兒寬限＝6×此值）、BACKUP_CTL_LOGICAL_MIN_SECONDS；
#   離站與保留：OFFSITE_S3_BUCKET／_ENDPOINT／_VERIFY_TLS、AWS_ACCESS_KEY_ID／AWS_SECRET_ACCESS_KEY、LOGICAL_BACKUP_RETENTION_DAYS。
set -u

self="${BASH_SOURCE[0]}"
mode="${1:-round}"
locked=0
if [ "$mode" = "--locked" ]; then
  locked=1
  mode=round
fi

out_dir="${BACKUP_CTL_OUT_DIR:-/backup-out}"
lock_file="${BACKUP_CTL_LOCK_FILE:-/run/backup-ctl/maintenance.lock}"
poll="${BACKUP_CTL_POLL_SECONDS:-5}"
case "$poll" in '' | *[!0-9]*) poll=5 ;; esac
logical_min="${BACKUP_CTL_LOGICAL_MIN_SECONDS:-300}"
case "$logical_min" in '' | *[!0-9]*) logical_min=300 ;; esac
export_dir="$out_dir/export"
jobs_dir="$export_dir/jobs"
results_dir="$out_dir/results"
# 單一實例鎖放在維護鎖的同一個本地目錄（/run/backup-ctl），不在共享卷
export_lock_file="$(dirname -- "$lock_file")/export.lock"
stanza="aisdlc"

log() { printf '[%s] [backup-ctl-export] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
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
  for d in "$out_dir" "$export_dir" "$jobs_dir" "$results_dir"; do
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

# ── 清掃：進行中但鎖未持有 ⇒ interrupted ──────────────────────────────────────────────────────────────
mark_job_interrupted() {
  local job="$1" f="$jobs_dir/$1.json" json
  if json="$(jq -c --arg fin "$(now_iso)" \
    '.last.status = "interrupted" | .last.reason = "interrupted" | .last.finished_at = $fin' "$f" 2> /dev/null)" \
    && [ -n "$json" ] && printf '%s\n' "$json" | write_atomic "$f"; then
    log "WARN: $job 的狀態是 running 但維護鎖沒有持有者，改記 interrupted"
    return 0
  fi
  return 1
}

mark_results_interrupted() {
  local f="$1" json
  if json="$(jq -c --arg fin "$(now_iso)" \
    '.status = "failed" | .reason = "interrupted" | .finished_at = $fin' "$f" 2> /dev/null)" \
    && [ -n "$json" ] && printf '%s\n' "$json" | write_atomic "$f"; then
    log "WARN: results/$(basename -- "$f") 是 running 但維護鎖沒有持有者，改記 failed／interrupted"
    return 0
  fi
  return 1
}

# jobs/<job>.json 的 last.status=running，或 results/<id>.json 的 status=running 且 started_at（runner 的撿起時刻）
# 距今逾 6×BACKUP_CTL_POLL_SECONDS（避開剛撿起、尚未取鎖的視窗），而維護鎖無持有者 ⇒ 改記 interrupted
# （jobs：reason=interrupted、補 finished_at、保留 last_success_at；results：failed／interrupted）。
# 鎖被持有時只有一個 job 是真的在跑：status=running 的 job 以 started_at 最新者視為持有者，其餘是殘留。
# 先確認鎖的狀態再讀檔、寫之前再確認一次——終態一定先於鎖釋放寫完（job-run.sh），所以「鎖已空」之後讀到的 running 才可信。
sweep() {
  local held job f status started newest entry f_status f_type f_started now_epoch started_epoch grace
  local -a running=() stale=()
  local swept=" "
  held="$(lock_held)"
  for job in full diff dump verify; do
    f="$jobs_dir/$job.json"
    [ -f "$f" ] || continue
    status="$(jq -r '.last.status // empty' "$f" 2> /dev/null)" || continue
    [ "$status" = "running" ] || continue
    started="$(jq -r '.last.started_at // ""' "$f" 2> /dev/null)" || started=""
    running+=("$started|$job")
  done
  if [ "${#running[@]}" -gt 0 ]; then
    if [ "$held" = "false" ]; then
      stale=("${running[@]}")
      # 讀檔之後鎖又被持有了（剛好有新工作開始）：這一輪不清
      if [ "$(lock_held)" = "true" ]; then stale=(); fi
    else
      newest="$(printf '%s\n' "${running[@]}" | sort | tail -n 1)"
      for entry in "${running[@]}"; do
        if [ "$entry" != "$newest" ]; then stale+=("$entry"); fi
      done
    fi
  fi
  for entry in "${stale[@]}"; do
    job="${entry#*|}"
    if mark_job_interrupted "$job"; then swept+="$job "; fi
  done

  # results：只看確實是 running 的檔（一次 grep 先篩，避免每 5 秒對最多 50 份檔各跑一次 jq）
  [ -d "$results_dir" ] || return 0
  now_epoch="$(date +%s)"
  grace=$((6 * poll))
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    entry="$(jq -r '[.status // "", .type // "", .started_at // ""] | join("|")' "$f" 2> /dev/null)" || continue
    IFS='|' read -r f_status f_type f_started <<< "$entry"
    [ "$f_status" = "running" ] || continue
    case "$swept" in
      *" $f_type "*)
        # 與剛被清掃的 job 同一個工作的 results：整個動作都已中斷
        mark_results_interrupted "$f"
        continue
        ;;
    esac
    [ "$(lock_held)" = "false" ] || continue
    started_epoch=""
    if [ -n "$f_started" ]; then started_epoch="$(date -u -d "$f_started" +%s 2> /dev/null)" || started_epoch=""; fi
    if [ -z "$started_epoch" ]; then started_epoch="$(stat -c %Y -- "$f" 2> /dev/null)" || started_epoch="$now_epoch"; fi
    if [ $((now_epoch - started_epoch)) -gt "$grace" ]; then mark_results_interrupted "$f"; fi
  done < <(grep -l -E '"status"[[:space:]]*:[[:space:]]*"running"' "$results_dir"/*.json 2> /dev/null)
  return 0
}

# ── schedule.json：由 crontab 產生（啟動 root 階段一次）──────────────────────────────────────────────────
generate_schedule() {
  local crontab="${BACKUP_CTL_CRONTAB:-/etc/crontabs/postgres}" tz="${TZ:-UTC}"
  local line line_no=0 m h dom mon dow cmd job entries=""
  if [ ! -r "$crontab" ]; then
    log "ERROR: 讀不到 crontab（$crontab）；schedule.json 沒有產生"
    return 1
  fi
  ensure_dirs
  while IFS= read -r line || [ -n "$line" ]; do
    line_no=$((line_no + 1))
    case "$line" in '' | '#'* | [[:space:]]*'#'*) continue ;; esac
    # 環境變數列（NAME=value）不是排程
    if [[ "$line" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*= ]]; then continue; fi
    read -r m h dom mon dow cmd <<< "$line"
    if [ -z "${dow:-}" ] || [ -z "${cmd:-}" ]; then
      log "WARN: schedule：第 $line_no 列不是五個時間欄加指令，略過"
      continue
    fi
    if [[ "$cmd" =~ (^|[[:space:]/])job-run\.sh[[:space:]]+(full|diff|dump|verify)([[:space:]]|$) ]]; then
      job="${BASH_REMATCH[2]}"
    elif [[ "$cmd" =~ (^|[[:space:]])pgbackrest[[:space:]].*[[:space:]]expire([[:space:]]|$) ]]; then
      job="expire"
    elif [[ "$cmd" =~ (^|[[:space:]])find[[:space:]].*wal_archive ]]; then
      job="wal_clean"
    else
      log "WARN: schedule：第 $line_no 列的指令無法辨識，略過"
      continue
    fi
    entries+="$job"$'\t'"$m $h $dom $mon $dow"$'\n'
  done < "$crontab"
  if printf '%s' "$entries" | jq -R -s -c --arg tz "$tz" '
    {schema_rev: 1, tz: $tz,
     entries: [split("\n")[] | select(length > 0) | split("\t") | {job: .[0], cron: .[1]}]}' \
    | write_atomic "$export_dir/schedule.json"; then
    return 0
  fi
  log "ERROR: schedule.json 寫入失敗"
  return 1
}

# ── 一輪匯出 ─────────────────────────────────────────────────────────────────────────────────────────
work=""
phase=""

write_failed() {
  printf '{"schema_rev":1,"generated_at":"%s","ok":false}\n' "$(now_iso)" | write_atomic "$1" \
    || log "WARN: $1 寫入失敗"
}

uri_encode() { jq -rn --arg s "$1" '$s|@uri'; }

# repos：repo1 恆為本地 posix；repo2 是 S3，端點主機由 OFFSITE_S3_ENDPOINT 取（去埠號與括號）。
# local＝主機名不含 `.`、或為 localhost、127.0.0.0/8、::1、host.docker.internal（這些只可能指向同一台主機，
# 不加嚴會把本機儲存顯示成「外部 S3」）；含 `.` 的內網名稱（例 minio.example.internal）仍是 false。
compute_repos() {
  local endpoint="${OFFSITE_S3_ENDPOINT:-minio:9000}" host is_local=false
  host="${endpoint#*://}"
  host="${host%%/*}"
  if [[ "$host" == \[*\]* ]]; then
    host="${host#\[}"
    host="${host%%\]*}"
  elif [[ "$host" == *:* && "$host" != *:*:* ]]; then
    host="${host%%:*}"
  fi
  host="${host,,}"
  if [[ "$host" != *.* || "$host" == "localhost" || "$host" == "::1" || "$host" == "host.docker.internal" \
    || "$host" =~ ^127\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    is_local=true
  fi
  jq -c -n --arg host "$host" --argjson islocal "$is_local" '
    [{repo: 1, type: "posix", endpoint_host: null, local: true},
     {repo: 2, type: "s3", endpoint_host: $host, local: $islocal}]'
}

# pgbackrest help 的 `current:` 區段 → 每行「all <數字>」（單值，套用到所有 repo）或「repoN <數字>」。
# 解析不了（沒有該選項的說明橫幅、current 非數字、出現多個 current 區段）回非 0。help 輸出前後可能夾 INFO 日誌行，不影響。
parse_current() {
  awk -v opt="$1" '
    BEGIN { banner = 0; state = 0; bad = 0; sections = 0 }
    index($0, "\047" opt "\047 option help") > 0 { banner = 1 }
    /^current:[ \t]*$/ { sections++; state = 1; next }
    /^current:[ \t]*[0-9]+[ \t]*$/ { sections++; state = 0; print "all " $2; next }
    /^current:/ { bad = 1; state = 0; next }
    state == 1 && /^[ \t]+repo[0-9]+:[ \t]*[0-9]+[ \t]*$/ { gsub(/:/, " "); print $1 " " $2; next }
    state == 1 && /^[ \t]+repo[0-9]+:/ { bad = 1; next }
    state == 1 { state = 0 }
    END { if (!banner || bad || sections > 1) exit 1 }
  '
}

# retention：取 pgBackRest 自報的有效值（`help expire repo-retention-full`／`-diff` 的 current:；單值套用全部 repo、
# 逐 repo 列各取各的；不自己讀 pgbackrest.conf——環境變數優先於 conf 的語意由「問 pgBackRest」達成）加
# LOGICAL_BACKUP_RETENTION_DAYS。格式 {repo1:{full,diff},repo2:{full,diff},logical_days}，欄內 null＝該設定未設；
# 整體解析不到＝null（不填預設值）。
compute_retention() {
  local full_help diff_help full_rows diff_rows days="${LOGICAL_BACKUP_RETENTION_DAYS:-28}"
  full_help="$(pgbackrest --log-level-console=off help expire repo-retention-full 2> /dev/null)" || { echo null; return 0; }
  diff_help="$(pgbackrest --log-level-console=off help expire repo-retention-diff 2> /dev/null)" || { echo null; return 0; }
  full_rows="$(printf '%s\n' "$full_help" | parse_current repo-retention-full)" || { echo null; return 0; }
  diff_rows="$(printf '%s\n' "$diff_help" | parse_current repo-retention-diff)" || { echo null; return 0; }
  jq -c -n --arg full "$full_rows" --arg diff "$diff_rows" --arg days "$days" '
    def rows($t): [$t | split("\n")[] | select(length > 0) | split(" ")];
    def pick($rows; $repo): [$rows[] | select(.[0] == "all" or .[0] == $repo) | .[1] | tonumber] | .[0];
    rows($full) as $f | rows($diff) as $d
    | {repo1: {full: pick($f; "repo1"), diff: pick($d; "repo1")},
       repo2: {full: pick($f; "repo2"), diff: pick($d; "repo2")},
       logical_days: (if ($days | test("^[0-9]+$")) then ($days | tonumber) else null end)}' \
    || echo null
}

write_info() {
  local raw="$work/info.raw" assembled="$work/info.assembled" retention repos
  phase=info
  if pgbackrest --stanza="$stanza" --output=json --log-level-console=off info > "$raw" 2> /dev/null \
    && jq -e 'type == "array"' "$raw" > /dev/null 2>&1; then
    retention="$(compute_retention)"
    repos="$(compute_repos)" || repos="[]"
    {
      printf '{"schema_rev":1,"generated_at":"%s","ok":true,"info":' "$(now_iso)"
      cat -- "$raw"
      printf ',"retention":%s,"repos":%s}\n' "${retention:-null}" "${repos:-[]}"
    } > "$assembled"
    if jq -e . "$assembled" > /dev/null 2>&1 && write_atomic "$export_dir/info.json" < "$assembled"; then
      phase=""
      return 0
    fi
    log "WARN: info.json 組裝或寫入失敗，改記 ok:false"
  else
    log "WARN: pgbackrest info 失敗或輸出不是 JSON 陣列，info.json 記 ok:false"
  fi
  write_failed "$export_dir/info.json"
  phase=""
}

# mc ls --json 的 lastModified 有「Z」與「±hh:mm」兩種、帶不定位數的小數秒 ⇒ 一律換成 UTC 秒精度的 …Z
list_logical() {
  local bucket="${OFFSITE_S3_BUCKET:-aisdlc-db-backup}" endpoint="${OFFSITE_S3_ENDPOINT:-minio:9000}" raw="$work/logical.raw"
  local mc_cmd=(mc)
  export MC_CONFIG_DIR="$work/mc"
  mkdir -p -- "$MC_CONFIG_DIR" 2> /dev/null
  if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    MC_HOST_offsite="https://$(uri_encode "$AWS_ACCESS_KEY_ID"):$(uri_encode "$AWS_SECRET_ACCESS_KEY")@${endpoint}"
    export MC_HOST_offsite
  fi
  if [ "${OFFSITE_S3_VERIFY_TLS:-n}" = "n" ]; then mc_cmd+=(--insecure); fi
  "${mc_cmd[@]}" ls --json "offsite/${bucket}/logical/" > "$raw" 2> /dev/null || return 1
  jq -c -s '
    def utc_iso:
      capture("^(?<d>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\\.[0-9]+)?(?<tz>Z|[+-][0-9]{2}:[0-9]{2})$") as $m
      | ($m.d + "Z" | fromdateiso8601) as $e
      | (if $m.tz == "Z" then 0
         else ((($m.tz[1:3] | tonumber) * 3600 + ($m.tz[4:6] | tonumber) * 60)
               * (if $m.tz[0:1] == "-" then -1 else 1 end)) end) as $off
      | ($e - $off | todate);
    if any(.[]; .status == "error") then error("mc 回報錯誤")
    else [.[] | select(.status == "success" and .type == "file")
          | {name: .key, size: (.size // 0),
             modified: ((.lastModified | utc_iso) // error("lastModified 無法解析"))}] end' "$raw"
}

write_logical_if_due() {
  local dest="$export_dir/logical.json" last now objects
  if [ -f "$dest" ]; then
    last="$(stat -c %Y -- "$dest" 2> /dev/null)" || last=0
    now="$(date +%s)"
    if [ $((now - last)) -lt "$logical_min" ]; then return 0; fi
  fi
  phase=logical
  if objects="$(list_logical)" && [ -n "$objects" ] \
    && printf '{"schema_rev":1,"generated_at":"%s","ok":true,"objects":%s}\n' "$(now_iso)" "$objects" | write_atomic "$dest"; then
    phase=""
    return 0
  fi
  log "WARN: 離站邏輯備份清單取不到（mc 失敗），logical.json 記 ok:false（不寫部分清單、不保留舊清單）"
  write_failed "$dest"
  phase=""
}

round() {
  work="$(mktemp -d "${TMPDIR:-/tmp}/backup-ctl-export.XXXXXX" 2> /dev/null)" || work=""
  trap 'if [ -n "$work" ]; then rm -rf "$work" 2> /dev/null; fi' EXIT
  # 被 timeout 的 TERM 終止：正在寫的那份檔改記 ok:false（舊內容不能冒充新鮮）
  trap 'case "$phase" in info) write_failed "$export_dir/info.json" ;; logical) write_failed "$export_dir/logical.json" ;; esac; exit 143' TERM
  ensure_dirs
  sweep || log "WARN: 清掃失敗"
  if [ -z "$work" ]; then
    log "ERROR: 建不起暫存目錄，info.json 與 logical.json 記 ok:false"
    write_failed "$export_dir/info.json"
    write_failed "$export_dir/logical.json"
    return 0
  fi
  write_info
  write_logical_if_due
  return 0
}

case "$mode" in
  schedule)
    generate_schedule
    exit $?
    ;;
  sweep)
    ensure_dirs
    sweep
    exit 0
    ;;
  round)
    if [ "$locked" = "1" ]; then
      round
      exit 0
    fi
    # 單一實例：前一個還沒結束就立即結束碼 0（不等待、不碰 .tmp）。鎖檔開不了（唯讀、無此目錄）時不互斥照跑——
    # 每個行程的 .tmp 名稱不同，重疊最多是白做一輪，不會寫壞檔。
    mkdir -p -- "$(dirname -- "$export_lock_file")" 2> /dev/null || true
    if [ ! -e "$export_lock_file" ]; then (: >> "$export_lock_file") 2> /dev/null; fi
    if ! command -v flock > /dev/null 2>&1 || ! (: < "$export_lock_file") 2> /dev/null; then
      log "WARN: export.lock 不可用，不互斥照常匯出一輪"
      round
      exit 0
    fi
    flock -n -E 0 "$export_lock_file" bash "$self" --locked
    exit $?
    ;;
  *)
    printf 'usage: backup-ctl-export.sh [schedule|sweep]\n' >&2
    exit 2
    ;;
esac
