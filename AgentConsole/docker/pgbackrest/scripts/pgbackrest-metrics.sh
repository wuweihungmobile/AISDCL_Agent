#!/usr/bin/env bash
# docker/pgbackrest/scripts/pgbackrest-metrics.sh — 產出 pgBackRest 備份狀態與儲存用量的 Prometheus 指標檔
# 由 pgbackrest-entrypoint.sh 每 METRICS_INTERVAL 秒呼叫一次，busybox httpd 在 :9854/metrics 提供；
# Prometheus job `pgbackrest` 抓取（ADR-001 G-04：PRD §12.6.2 的 pgbackrest_* 指標沒有現成 exporter，由此產出）。
#
# 指標（皆為 gauge）：
#   pgbackrest_exporter_info_ok                      pgbackrest info 是否成功（1／0）
#   pgbackrest_exporter_scrape_timestamp_seconds     本檔產生時間（判斷指標是否過期）
#   pgbackrest_stanza_status{stanza}                 0=ok 1=缺 stanza 路徑 2=尚無有效備份 3=缺 stanza 資料 4=repo 間不一致 5=資料庫不符 6=找不到備份 99=其他
#   pgbackrest_repo_status{stanza,repo}              repo 狀態碼（0=ok）
#   pgbackrest_backup_count{stanza,repo,type}        各 repo 內 full／diff／incr 的備份份數
#   pgbackrest_backup_since_last_full_seconds{stanza,repo}     距該 repo 最近一次完整備份完成的秒數（PRD §12.6.2；> 8 天告警）
#   pgbackrest_backup_since_last_backup_seconds{stanza,repo}   距該 repo 最近一次任何類型備份完成的秒數
#   pgbackrest_backup_last_duration_seconds{stanza,repo}       該 repo 最近一份備份的耗時
#   pgbackrest_backup_last_database_size_bytes{stanza,repo}    最近一份備份對應的資料庫大小
#   pgbackrest_backup_last_repo_size_bytes{stanza,repo}        最近一份備份在 repo 內的大小（壓縮＋加密後）
#   pgbackrest_backup_last_status{stanza,type}       最近一次「備份腳本」執行結果（0=成功 1=失敗；PRD §12.6.2；≠0 告警）
#   pgbackrest_backup_last_run_timestamp_seconds{stanza,type}  該次執行時間
#   aisdlc_backup_job_last_status{backup_job}        四個備份工作（full／diff／dump／verify）最近一次的結果（0=成功 1=失敗或中斷）；
#                                                    來源＝job-run.sh 的狀態檔（BACKUP_CTL_OUT_DIR/export/jobs/<job>.json）；
#                                                    無狀態檔、或正在執行（running）的 job 不輸出序列（PRD §9.3、TCS §C6）
#   aisdlc_backup_job_last_finished_timestamp_seconds{backup_job}  該次結束時間（unix 秒；running 中不輸出）
#   aisdlc_backup_ctl_heartbeat_timestamp_seconds    runner 最近一次心跳（unix 秒；export/heartbeat 的 ts；無檔不輸出）
#   🔴 上面三個新指標的標籤名是 backup_job、不是 job：抓取目標標籤 job="pgbackrest"（prometheus.yml 未設 honor_labels）
#      會把曝光的 job 改名成 exported_job，alerts.yml 的 {backup_job=~"dump|verify"} 才匹配得到。
#   aisdlc_storage_bytes{path}                       目錄實際用量（repo1、WAL 歸檔）
#   aisdlc_storage_used_ratio{path}                  該路徑所在檔案系統的使用率（0~1）
# 失敗的備份不會出現在 `pgbackrest info`，所以 last_status 由 backup-full.sh／backup-incr.sh 寫入狀態檔
# （/var/lib/pgbackrest/.last_backup_status）後在這裡讀取；從未執行過備份腳本時這兩個指標不存在。
# 大型 repo（數百 GB）的 du 每輪都掃一次會偏貴，請調大 METRICS_INTERVAL。
set -euo pipefail

out="${1:?usage: pgbackrest-metrics.sh <output-file>}"
stanza="aisdlc"
state_file="/var/lib/pgbackrest/.last_backup_status"
repo1_path="/var/lib/pgbackrest"
wal_archive_path="/var/lib/postgresql/wal_archive"
data_path="/var/lib/postgresql/data"
now="$(date +%s)"
tmp="${out}.tmp.$$"
trap 'rm -f "$tmp"' EXIT

# 備份控制面指標（job-run.sh 的狀態檔與 runner 心跳）。🔴 附加在既有指標之後：這個函式的任何失敗都不得影響
# 既有 14 個指標的輸出，所以每一步自己兜底（狀態檔壞掉、日期解析不了＝跳過該序列，不是整支腳本失敗）。
ctl_out_dir="${BACKUP_CTL_OUT_DIR:-/backup-out}"
emit_backup_ctl_metrics() {
  local job f line st fin epoch hb statuses="" finishes=""
  for job in full diff dump verify; do
    f="$ctl_out_dir/export/jobs/$job.json"
    [ -f "$f" ] || continue
    line="$(jq -r '[.last.status // "", .last.finished_at // ""] | join("|")' "$f" 2> /dev/null)" || continue
    st="${line%%|*}"
    fin="${line#*|}"
    case "$st" in
      succeeded) statuses+="aisdlc_backup_job_last_status{backup_job=\"${job}\"} 0"$'\n' ;;
      failed | interrupted) statuses+="aisdlc_backup_job_last_status{backup_job=\"${job}\"} 1"$'\n' ;;
      *) continue ;; # running（上一次終態不冒充這一次）或不認得的值：不輸出序列
    esac
    epoch="$(date -u -d "$fin" +%s 2> /dev/null)" || epoch=""
    if [ -n "$epoch" ]; then
      finishes+="aisdlc_backup_job_last_finished_timestamp_seconds{backup_job=\"${job}\"} ${epoch}"$'\n'
    fi
  done
  echo '# HELP aisdlc_backup_job_last_status 備份工作最近一次的結果（0=成功 1=失敗或中斷；執行中不輸出）'
  echo '# TYPE aisdlc_backup_job_last_status gauge'
  printf '%s' "$statuses"
  echo '# HELP aisdlc_backup_job_last_finished_timestamp_seconds 備份工作最近一次結束時間（unix 秒；執行中不輸出）'
  echo '# TYPE aisdlc_backup_job_last_finished_timestamp_seconds gauge'
  printf '%s' "$finishes"
  echo '# HELP aisdlc_backup_ctl_heartbeat_timestamp_seconds 備份控制面 runner 最近一次心跳（unix 秒）'
  echo '# TYPE aisdlc_backup_ctl_heartbeat_timestamp_seconds gauge'
  hb="$(jq -r '.ts // empty' "$ctl_out_dir/export/heartbeat" 2> /dev/null)" || hb=""
  if [ -n "$hb" ]; then
    epoch="$(date -u -d "$hb" +%s 2> /dev/null)" || epoch=""
    if [ -n "$epoch" ]; then echo "aisdlc_backup_ctl_heartbeat_timestamp_seconds ${epoch}"; fi
  fi
  return 0
}

info_ok=1
if ! info_json="$(pgbackrest --stanza="$stanza" --output=json --log-level-console=off info 2>/dev/null)" \
   || ! printf '%s' "$info_json" | jq -e . > /dev/null 2>&1; then
  info_ok=0
  info_json='[]'
fi

{
  echo '# HELP pgbackrest_exporter_info_ok pgbackrest info 是否成功執行（1=成功）'
  echo '# TYPE pgbackrest_exporter_info_ok gauge'
  echo "pgbackrest_exporter_info_ok ${info_ok}"
  echo '# HELP pgbackrest_exporter_scrape_timestamp_seconds 本指標檔產生時間（unix 秒）'
  echo '# TYPE pgbackrest_exporter_scrape_timestamp_seconds gauge'
  echo "pgbackrest_exporter_scrape_timestamp_seconds ${now}"

  # jq 的 `,` 比 `|` 優先：每一段「產生多行」的管線都要自己加括號，否則前面的字串會被當成後面管線的輸入
  printf '%s' "$info_json" | jq -r --argjson now "$now" --arg stanza "$stanza" '
    (.[0] // {}) as $s
    | ($s.name // $stanza) as $st
    | ($s.status.code // 99) as $code
    | [ ($s.backup // [])[]
        | { repo: ((.database["repo-key"] // 1) | tostring), type: .type,
            start: .timestamp.start, stop: .timestamp.stop,
            dbsize: (.info.size // 0), reposize: (.info.repository.size // 0) } ] as $b
    | [ ($s.repo // [])[] | (.key | tostring) ] as $repos
    | def lbl($r): "stanza=\"\($st)\",repo=\"\($r)\"";
      def last($r): ([ $b[] | select(.repo == $r) ] | max_by(.stop));
      def last_full($r): ([ $b[] | select(.repo == $r and .type == "full") ] | max_by(.stop));
      (
        "# HELP pgbackrest_stanza_status stanza 狀態碼（0=ok）",
        "# TYPE pgbackrest_stanza_status gauge",
        "pgbackrest_stanza_status{stanza=\"\($st)\"} \($code)",
        "# HELP pgbackrest_repo_status repo 狀態碼（0=ok）",
        "# TYPE pgbackrest_repo_status gauge",
        (($s.repo // [])[] | "pgbackrest_repo_status{\(lbl(.key | tostring))} \(.status.code)"),
        "# HELP pgbackrest_backup_count repo 內各類型備份份數",
        "# TYPE pgbackrest_backup_count gauge",
        ($repos[] as $r | ("full","diff","incr") as $t
          | "pgbackrest_backup_count{\(lbl($r)),type=\"\($t)\"} \([ $b[] | select(.repo == $r and .type == $t) ] | length)"),
        "# HELP pgbackrest_backup_since_last_full_seconds 距最近一次完整備份完成的秒數",
        "# TYPE pgbackrest_backup_since_last_full_seconds gauge",
        ($repos[] as $r | last_full($r) | select(. != null) | "pgbackrest_backup_since_last_full_seconds{\(lbl($r))} \($now - .stop)"),
        "# HELP pgbackrest_backup_since_last_backup_seconds 距最近一次任何類型備份完成的秒數",
        "# TYPE pgbackrest_backup_since_last_backup_seconds gauge",
        ($repos[] as $r | last($r) | select(. != null) | "pgbackrest_backup_since_last_backup_seconds{\(lbl($r))} \($now - .stop)"),
        "# HELP pgbackrest_backup_last_duration_seconds 最近一份備份的耗時",
        "# TYPE pgbackrest_backup_last_duration_seconds gauge",
        ($repos[] as $r | last($r) | select(. != null) | "pgbackrest_backup_last_duration_seconds{\(lbl($r))} \(.stop - .start)"),
        "# HELP pgbackrest_backup_last_database_size_bytes 最近一份備份對應的資料庫大小",
        "# TYPE pgbackrest_backup_last_database_size_bytes gauge",
        ($repos[] as $r | last($r) | select(. != null) | "pgbackrest_backup_last_database_size_bytes{\(lbl($r))} \(.dbsize)"),
        "# HELP pgbackrest_backup_last_repo_size_bytes 最近一份備份在 repo 內的大小",
        "# TYPE pgbackrest_backup_last_repo_size_bytes gauge",
        ($repos[] as $r | last($r) | select(. != null) | "pgbackrest_backup_last_repo_size_bytes{\(lbl($r))} \(.reposize)")
      )
  '

  if [ -f "$state_file" ]; then
    run_type="$(sed -n 's/^type=//p' "$state_file")"
    run_status="$(sed -n 's/^status=//p' "$state_file")"
    run_ts="$(sed -n 's/^timestamp=//p' "$state_file")"
    if [ -n "$run_type" ] && [ -n "$run_status" ] && [ -n "$run_ts" ]; then
      echo '# HELP pgbackrest_backup_last_status 最近一次備份腳本執行結果（0=成功 1=失敗）'
      echo '# TYPE pgbackrest_backup_last_status gauge'
      echo "pgbackrest_backup_last_status{stanza=\"${stanza}\",type=\"${run_type}\"} ${run_status}"
      echo '# HELP pgbackrest_backup_last_run_timestamp_seconds 最近一次備份腳本執行時間（unix 秒）'
      echo '# TYPE pgbackrest_backup_last_run_timestamp_seconds gauge'
      echo "pgbackrest_backup_last_run_timestamp_seconds{stanza=\"${stanza}\",type=\"${run_type}\"} ${run_ts}"
    fi
  fi

  emit_backup_ctl_metrics || true

  echo '# HELP aisdlc_storage_bytes 目錄實際用量（bytes）'
  echo '# TYPE aisdlc_storage_bytes gauge'
  for p in "$repo1_path" "$wal_archive_path"; do
    if [ -d "$p" ]; then
      echo "aisdlc_storage_bytes{path=\"${p}\"} $(du -sb "$p" | cut -f1)"
    fi
  done
  echo '# HELP aisdlc_storage_used_ratio 路徑所在檔案系統的使用率（0~1）'
  echo '# TYPE aisdlc_storage_used_ratio gauge'
  for p in "$data_path" "$repo1_path"; do
    if [ -d "$p" ]; then
      df -P "$p" | awk -v p="$p" 'NR==2 { printf "aisdlc_storage_used_ratio{path=\"%s\"} %.4f\n", p, $3 / ($3 + $4) }'
    fi
  done
} > "$tmp"

mv -f "$tmp" "$out"
