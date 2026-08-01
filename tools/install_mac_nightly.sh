#!/usr/bin/env bash
# install_mac_nightly.sh — mac nightly launchd 一鍵安裝器（R13 ARCH-R13-3）。
#
# 為何存在：ONBOARDING.md §8 的 launchd plist 至今是「手抄範本」——開發者須自行
# 替換絕對路徑、手打 launchctl 指令，步驟長且易錯（路徑打錯 → launchd 靜默不跑，
# 正是 R12 心跳哨兵要抓的斷載型缺口）。本腳本把範本機械化：動態解析 repo 絕對
# 路徑 → heredoc 產 plist → plutil -lint 驗合法 → launchctl 冪等重載。
#
# 用法（ONBOARDING §6 執行權限政策：以 bash 呼叫、644 入庫，不依賴 exec bit）：
#   bash tools/install_mac_nightly.sh                       # install（預設）
#   bash tools/install_mac_nightly.sh --uninstall           # unload + 刪 plist
#   bash tools/install_mac_nightly.sh --status              # launchctl 比對 + 心跳三態
#   bash tools/install_mac_nightly.sh --render-only <path>  # 只產 plist + lint（smoke 用）
#
# plist 內容對齊 ONBOARDING.md §8 現行範本語意：Label=com.autoclaude.nightly、
# ProgramArguments=/bin/bash + AutoClaude/tools/run_local_nightly.sh 絕對路徑、
# StartCalendarInterval 02:00、RunAtLoad（R15 SCAN-C-1：02:00 關機/睡眠錯過時，
# 開機/載入即補跑；載體自帶「心跳當日去重」故不重複跑——等價 Windows
# StartWhenAvailable）、StandardOut/ErrorPath=AutoClaude/logs/nightly_mac_launchd.{log,err}
#（R14 ARCH-GAP-3：原導 /tmp 會被 macOS 週期清理＋重開機清空，深夜失敗數日後排查 log 已散失；
# 改與心跳檔同目錄（gitignored）集中取證，install 時 mkdir -p 保證目錄存在）。
#
# --status 心跳語意對齊 tools/dev_start.py _check_nightly_heartbeat（R12 ARCH-R12-2、
# R67-E21）。對齊維度以下列機讀清單為準（DIMENSIONS: 三態, FAIL 計數, 年齡顯示）——
# tools/tests/test_dev_start.py 的跨站行為等價鎖會解析本清單並斷言「宣稱的維度數
# ＝鎖實際比對的維度數」，防 R67-E21 重演（該次是 dev_start 於 R15 新增 FAIL 維度、
# 本檔沒跟上，而等價鎖被寫死在 R12 的「三態」語意上，契約破裂零訊號）：
#   三態      — 缺席→提示（排程可能未啟用）；mtime > 8 天→過期警告；否則新鮮
#   FAIL 計數 — 心跳檔前 3 行的 `FAIL=N`，N>0 多印一行 ⚠️（語意對齊 dev_start
#               _heartbeat_fail_count／ARCH-R15-1：mtime 只證明「在跑」不證明「在綠」）
#   年齡顯示  — 「距今 N.N 天」這個**顯示值**本身（R68-M32）。判定早已對齊到秒
#               （R67-M40），顯示卻沿用整數十分位截斷，與 dev_start 的
#               `{age_days:.1f}` 在 age_s=74304 秒分別印 0.8／0.9——同一台機器
#               同一顆心跳檔、兩支官方工具給出不同天數。修法見 report_heartbeat
#
# --status 另有兩段 mac 專屬報表（皆 advisory）：
#   ① 補跑保護能力表（R67-M37）：逐項印「已安裝 plist 的實際值 (expected 期望值)」，
#      對齊 install_windows_nightly.ps1 Show-TaskDetail 的四項 (expected X) 體例。
#      查的是**磁碟上已安裝的 plist**，不是本檔 heredoc——R15 之前安裝過的機器其
#      plist 至今無 RunAtLoad，而 --status 過去只做 [ -f ] 存在性判斷，恆報綠。
#   ② 覆蓋連續性（R67-F29）：心跳只看「最後一次距今幾天」，看不見中間漏跑，且任何
#      補跑會把空窗蓋掉；改掃 RunId log 檔名時間戳列出近 N 天的缺口。這同時是 mac
#      側對 Windows `NextRunTime` 前瞻憑證的替代——launchd 不提供 next-run。
#
# Exit codes：0＝成功（--status 時＝launchd 已載入）；1＝失敗（--status 時＝未載入
# 或 plist 缺席）。心跳三態／FAIL 計數／上述兩段報表**皆屬 advisory**，不影響
# --status exit code（對齊 dev_start「皆不阻擋」語意——排程「有沒有載入」才是本
# 工具的機械判準）。
# 🔴 R68-M31：「或 plist 缺席」這半句自 R13 起就寫在這裡，實作卻只看 launchctl
# 是否列出 label——「已載入但磁碟上 plist 已被刪」時 rc=0 全綠且整段跳過能力表。
# 那是 macOS 專屬的「載入 ≠ 已持久化」狀態：launchd 的載入只活在當前 login
# session 的記憶體裡，磁碟沒有 plist 就不會在下次登入/重開機時被重新載入，是一個
# 註定死掉的排程。故 plist 存在性是硬判準（本行契約的兌現），不是 advisory。
#
# 測試縫（fake 環境驗證用；正常安裝不需理會）：IMN_LAUNCHCTL 可指向 stub 以驗證
# launchctl 呼叫序列而不真載入（本 repo 紀律：真安裝屬使用者 ops，須另行核可；
# install／--uninstall 路徑自 R68-M64 起亦以此縫受行為鎖覆蓋，不再只有 --status）；
# IMN_NOW 可凍結 report_heartbeat 的「現在」為指定 epoch 秒，供跨站等價鎖在 8.0 天
# 整秒邊界做**確定性**比對（兩份實作各自呼叫 date/time.time 會落在不同秒，該邊界
# 上會 flaky——R67-M40）。IMN_NOW 只影響心跳年齡，不影響覆蓋連續性的日期換算。
#
# 相容性：bash 3.2（macOS /bin/bash；禁 declare -A / mapfile / ${var,,}）+ BSD
# 工具（stat -f、date +%s）。全程 ${var} 大括號展開（DEF-101-163 紀律）。
set -euo pipefail

# 非 macOS fail-loud：plist/plutil/launchctl 皆為 macOS 專屬，任何模式（含
# --render-only）在他平台跑都是無意義假訊號。Windows 對等機制＝schtasks 家族
# （AutoClaude/tools/fix_nightly_catchup.ps1，見 ONBOARDING §8）。
if [ "$(uname)" != "Darwin" ]; then
  echo "❌ install_mac_nightly.sh 僅支援 macOS（launchd）——Windows 請用 schtasks 家族" \
       "AutoClaude/tools/fix_nightly_catchup.ps1（ONBOARDING §8）" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NIGHTLY_SH="${REPO_ROOT}/AutoClaude/tools/run_local_nightly.sh"
HEARTBEAT="${REPO_ROOT}/AutoClaude/logs/nightly_mac_latest.log"
# launchd stdout/stderr 落點（R14 ARCH-GAP-3：遷出 /tmp，與心跳檔同目錄集中取證）
LOG_DIR="${REPO_ROOT}/AutoClaude/logs"
LABEL="com.autoclaude.nightly"
PLIST_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${PLIST_DIR}/${LABEL}.plist"
LAUNCHCTL="${IMN_LAUNCHCTL:-launchctl}"
# 心跳過期門檻（天）：與 tools/dev_start.py _HEARTBEAT_MAX_AGE_DAYS 同值同語意。
HEARTBEAT_MAX_AGE_DAYS=8
# 覆蓋連續性回看天數（R67-F29）。刻意短於載體的 14 天 RunId log 輪替窗口
# （run_local_nightly.sh `find -mtime +14 -delete`），否則「缺席」會混入「被輪替
# 刪掉」的假訊號。
NIGHTLY_COVERAGE_DAYS=7

usage() {
  echo "用法：bash tools/install_mac_nightly.sh [--uninstall | --status | --render-only <path>]" >&2
}

# 產 plist 到 $1 並 plutil -lint。路徑以 heredoc 原文嵌入（XML 未跳脫——repo 路徑
# 含 &、< 等 XML 特殊字元時 plutil -lint 會攔下，fail-loud 而非靜默壞 plist）。
render_plist() {
  _target="$1"
  if [ ! -f "${NIGHTLY_SH}" ]; then
    echo "❌ 找不到 nightly 載體：${NIGHTLY_SH}" >&2
    return 1
  fi
  cat > "${_target}" <<EOF_PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${NIGHTLY_SH}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>${LOG_DIR}/nightly_mac_launchd.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/nightly_mac_launchd.err</string>
</dict>
</plist>
EOF_PLIST
  plutil -lint "${_target}" >/dev/null || {
    echo "❌ 產出的 plist 未通過 plutil -lint：${_target}" >&2
    return 1
  }
  echo "✅ plist 已產出並通過 plutil -lint：${_target}（含 RunAtLoad 開機/載入補跑，載體當日去重）"
}

# 心跳三態＋FAIL 計數（advisory；語意鏡射 tools/dev_start.py _check_nightly_heartbeat，
# 對齊維度＝檔頭 DIMENSIONS 清單）。
report_heartbeat() {
  if [ ! -f "${HEARTBEAT}" ]; then
    # 成因提示由 cmd_status 依 launchctl 第 2 欄（last exit status）決定（R68-M30）；
    # 本函式被跨站等價鎖單獨擷取執行時 ABSENT_HINT 未設定，退回原本的「未啟用／
    # 尚未首跑」措辭。絕不可把該措辭寫死在這裡——那正是缺陷本體：排程每晚照跑、
    # 載體每晚在寫心跳前就非零退出時，這句「尚未跑過第一輪」是**確定為假**的因果。
    echo "  心跳：未偵測（AutoClaude/logs/nightly_mac_latest.log 不存在）${ABSENT_HINT:-——排程可能未啟用或尚未跑過第一輪（設定見 ONBOARDING §8）}"
    return 0
  fi
  # FAIL 維度（R67-E21）：心跳 mtime 只證明「排程在跑」，不證明「驗證全綠」——
  # nightly 連續全紅時本工具過去隻字未提，而同一顆心跳檔在 dev_start 會出 ⚠️。
  # 讀前 3 行即涵蓋兩態（第 2 行恆為 `===== nightly 彙總：PASS=n FAIL=n =====`，
  # 第 3 行僅 FAIL>0 才存在），與 dev_start._heartbeat_fail_count 同契約。
  # 無命中時 grep 回 rc=1、head -1 提前關管線會讓上游收 SIGPIPE——本段全屬
  # advisory，以 `|| true` 收斂，絕不可讓 set -e 中斷 --status。
  _fail_n="$(head -3 "${HEARTBEAT}" 2>/dev/null | grep -oE 'FAIL=[0-9]+' | head -1 | cut -d= -f2 || true)"
  if [ -n "${_fail_n}" ] && [ "${_fail_n}" -gt 0 ]; then
    echo "  ⚠️ 最近一輪 FAIL=${_fail_n}——排程在跑但驗證未全綠，請查 AutoClaude/logs/ 最新 nightly_mac log（ARCH-R15-1）"
  fi
  _mtime="$(stat -f %m "${HEARTBEAT}")"
  _now="${IMN_NOW:-$(date +%s)}"
  _age_s=$(( _now - _mtime ))
  # 時鐘倒退／mtime 在未來：夾到 0，否則下方合成小數會產出 "-0.-5" 這種壞字串。
  if [ "${_age_s}" -lt 0 ]; then _age_s=0; fi
  # 顯示精度與判定精度一致（R67-M39）：判定自 SD-R13-1 起以秒比較，顯示卻仍是
  # 整數天除法截斷，(8,9) 天整整 24 小時窗口會印出「距今 8 天 > 8 天」這種數學上
  # 為偽的文案。訊息一併改為不含不等式的敘述句，避免「8.0 天 > 8 天」在整秒邊界
  # 再現同型矛盾。
  # R68-M32：合成一位小數的手法由「先乘 10 再整除」（＝十分位**截斷**）改為 awk
  # 的 `%.1f`。WHY：dev_start.py 印的是 `{age_days:.1f}`＝IEEE double 的正確捨入，
  # 截斷在 age_s=74304 印 0.8 而 dev_start 印 0.9，是確定性分歧而非邊界抖動。
  # 不改成 round-half-up（`(_age_s * 10 + 43200) / 86400`）：那只是把分歧點從
  # 74304 平移到 12960（該點 double 落在 0.15 之下，python 印 0.1、half-up 印
  # 0.2），沒有消除分歧。awk 與 python 讀同一個 double、套同一條捨入規則，分歧
  # 被結構性消除（本輪 3400 組隨機＋邊界取樣 0 筆不一致）。bash 3.2 無浮點運算，
  # awk 是 POSIX 必備工具，不引入新相依。
  _age_days="$(awk -v a="${_age_s}" 'BEGIN{printf "%.1f", a/86400}')"
  # 過期判定以「秒」比較（與 dev_start.py 整數秒年齡 > 8 天精確等價）：shell 整數
  # 除法會把 8.5 天截斷成 8 天而誤判「新鮮」，(8,9) 天窗口與 dev_start 背離
  # （SD-R13-1）。dev_start 側自 R67-M40 起亦先把 mtime／now 截成整數秒，兩份實作
  # 在同一秒內對同一顆心跳檔的裁決自此完全一致（BSD `stat -f %m` 本就只給整數秒）。
  if [ "${_age_s}" -gt $(( HEARTBEAT_MAX_AGE_DAYS * 86400 )) ]; then
    echo "  ⚠️ 心跳：過期（距今 ${_age_days} 天，已超過 ${HEARTBEAT_MAX_AGE_DAYS} 天門檻）——排程可能已斷載，請檢查 launchctl（ONBOARDING §8）"
  else
    echo "  ✅ 心跳：新鮮（距今 ${_age_days} 天）"
  fi
}

# 近 N 天 nightly 覆蓋連續性（advisory；R67-F29）。
#
# WHY：心跳哨兵只看「最後一次距今幾天」——本機 07-28/29/30 三天零 nightly（整段
# 關機），--status 仍印「✅ 心跳：新鮮（距今 0 天）」，因為 07-31 開機後 RunAtLoad
# 補跑了一輪把計數歸零。空窗在唯一的每日回饋通道上結構性不可見。改掃 RunId log
# （run_local_nightly.sh 每輪產一份 nightly_mac_<時間戳>.log）的檔名日期。
#
# 只回看「昨天起」往前 N 天：今日 02:00 排程在當日凌晨前尚未觸發，把今天算進去會
# 讓每天 00:00~02:00 之間必然多報一天假缺口。
report_coverage() {
  if ! ls "${LOG_DIR}"/nightly_mac_2*.log >/dev/null 2>&1; then
    # 成因提示同 report_heartbeat（R68-M30）：非零 last exit status 時「尚未跑過
    # 第一輪」為假，由 cmd_status 覆寫 ABSENT_HINT。
    echo "  覆蓋連續性：無任何 RunId log（${LOG_DIR}/nightly_mac_2*.log 不存在）${ABSENT_HINT:-——排程可能未啟用或尚未跑過第一輪（設定見 ONBOARDING §8）}"
    return 0
  fi
  _missing=""
  _missing_n=0
  _i=1
  while [ "${_i}" -le "${NIGHTLY_COVERAGE_DAYS}" ]; do
    _day="$(date -v-"${_i}"d +%Y%m%d)"
    if ! ls "${LOG_DIR}"/nightly_mac_"${_day}"_*.log >/dev/null 2>&1; then
      _missing="${_missing}${_missing:+, }${_day}"
      _missing_n=$(( _missing_n + 1 ))
    fi
    _i=$(( _i + 1 ))
  done
  if [ "${_missing_n}" -eq 0 ]; then
    echo "  ✅ 覆蓋連續性：近 ${NIGHTLY_COVERAGE_DAYS} 天每日皆有 nightly 紀錄"
  else
    echo "  ⚠️ 覆蓋連續性：近 ${NIGHTLY_COVERAGE_DAYS} 天有 ${_missing_n} 天無 nightly 紀錄（${_missing}）——心跳「新鮮」只證明最後一次有跑，補跑會把先前空窗蓋掉（ONBOARDING §8）"
  fi
}

# 已安裝 plist 的補跑保護能力表（advisory；R67-M37）。
#
# WHY：cmd_status 過去只做 `[ -f "${PLIST_PATH}" ]`，從不讀內容——一份指向不存在
# 載體、且缺 RunAtLoad 的死排程三行全綠 rc=0。護欄側（macos_smoke_local.sh）鎖的
# 也只是**本檔 heredoc 原始碼**，不是**機器上實際安裝的產物**。Windows 側
# Show-TaskDetail 逐項印 4 個補跑保護設定的 `(expected X)` 供人比對，mac 側零對等物。
_cap_bad=0

# $1=plutil key path；鍵缺席／plist 壞損一律回字面 "(缺席)"（fail-soft：本段是報表）
_plist_raw() {
  plutil -extract "$1" raw -o - "${PLIST_PATH}" 2>/dev/null || echo "(缺席)"
}

# $1=能力名 $2=實際值 $3=期望值 $4=補充說明（可省略）。不符即累計 _cap_bad。
# `${4:-}` 而非 `$4`：本檔 set -u，省略第四參數時裸 $4 會直接 unbound 中止 --status。
_cap_line() {
  if [ "$2" = "$3" ]; then
    echo "  ✅ $1 = $2   (expected $3)${4:-}"
  else
    echo "  ⚠️ $1 = $2   (expected $3)${4:-}"
    _cap_bad=$(( _cap_bad + 1 ))
  fi
}

report_plist_capabilities() {
  _cap_bad=0
  echo "  ── 補跑保護能力（查已安裝 plist 內容；對齊 install_windows_nightly.ps1 -Status 四項）──"
  _cap_line "RunAtLoad" "$(_plist_raw RunAtLoad)" "true" \
    "；≙ Windows StartWhenAvailable：開機/載入補跑錯過的一輪（R15 前安裝的 plist 無此鍵）"
  _cap_line "StartCalendarInterval Hour:Minute" \
    "$(_plist_raw StartCalendarInterval.Hour):$(_plist_raw StartCalendarInterval.Minute)" \
    "2:0" "；＝每日 02:00 觸發"
  _prog="$(_plist_raw ProgramArguments.1)"
  if [ -r "${_prog}" ]; then _prog_ok="是"; else _prog_ok="否"; fi
  _cap_line "ProgramArguments 載體可讀" "${_prog_ok}" "是" "；路徑 ${_prog}"
  _out="$(_plist_raw StandardOutPath)"
  case "${_out}" in
    "${LOG_DIR}"/*) _out_ok="是" ;;
    *) _out_ok="否" ;;
  esac
  _cap_line "StandardOutPath 位於 AutoClaude/logs" "${_out_ok}" "是" \
    "；路徑 ${_out}（R14 ARCH-GAP-3：導 /tmp 會被 macOS 週期清理）"
  # 以下三項 Windows 有、launchd 結構上沒有對應鍵——誠實列出「無從檢查」而不是
  # 靜默略過，讓兩側能力表能逐列對照（不列＝讀者無從得知這裡是缺口還是遺漏）。
  echo "  －  WakeToRun 對等：launchd 原生（睡眠期間錯過的觸發於喚醒時合併補跑，man launchd.plist），無對應 plist 鍵可查"
  echo "  －  電池策略對等：LaunchAgent 無 DisallowStartIfOnBatteries／StopIfGoingOnBatteries 對應鍵（不受電池阻擋）"
  echo "  －  NextRunTime 對等：launchd 不提供 next-run 憑證——改以上方「覆蓋連續性」回填此缺口"
  # 逐鍵檢查只認得「我們想得到的鍵」；整檔比對才抓得到其餘任何漂移（多餘鍵、
  # 路徑指向舊 checkout、Label 改名…）。renderer 產不出來時如實說跳過。
  _tmp_render="$(mktemp "${TMPDIR:-/tmp}/imn_status.XXXXXX")"
  if render_plist "${_tmp_render}" >/dev/null 2>&1; then
    if diff -q "${PLIST_PATH}" "${_tmp_render}" >/dev/null 2>&1; then
      echo "  ✅ plist 內容與現行安裝器產出逐位元組一致（無漂移）"
    else
      echo "  ⚠️ plist 內容已與現行安裝器產出漂移——重裝：bash tools/install_mac_nightly.sh"
      diff "${PLIST_PATH}" "${_tmp_render}" | sed 's/^/      /' || true
      _cap_bad=$(( _cap_bad + 1 ))
    fi
  else
    echo "  ⚠️ plist 漂移檢查跳過：renderer 無法產出（載體 ${NIGHTLY_SH} 缺失？）"
    _cap_bad=$(( _cap_bad + 1 ))
  fi
  rm -f "${_tmp_render}"
  if [ "${_cap_bad}" -gt 0 ]; then
    echo "  ⚠️ 上列 ${_cap_bad} 項與期望不符——重裝：bash tools/install_mac_nightly.sh（advisory，不改 exit code）"
  fi
}

# launchd 是否真的載入 LABEL：回傳 `launchctl list` 中第 3 欄精確等值 LABEL 的整列
# （空＝未載入）。第 3 欄精確等值而非 grep -F 子字串——後者會把 com.autoclaude.
# nightly2 之類前綴 label 誤判為已載入（SD-R13-4）；launchctl 失敗以 || true 收斂。
#
# 🔴 R68-M64：為何 install／uninstall 也必須走這裡，而不是相信 launchctl 的 rc——
# 本機實測 `launchctl load /不存在.plist` 印 `Load failed: 5: Input/output error`
# 卻仍 **exit 0**，`unload` 同型。也就是說 `set -e` 在這條路上結構上攔不到任何
# 失敗：安裝器會在排程根本沒載入的情況下印「✅ 已安裝並載入」並 rc=0，把「死排程」
# 製造出來還宣稱成功。載入與否只能查 list 自證（cmd_status 從 R13 起就是這樣查的，
# install 路徑卻一直沒用上這道現成的查核式）。
_launchctl_row() {
  "${LAUNCHCTL}" list 2>/dev/null | awk -v l="${LABEL}" '$3 == l' || true
}

cmd_install() {
  mkdir -p "${PLIST_DIR}"
  # launchd 不會自動建 StandardOutPath 的目錄，缺目錄時 log 靜默丟失（R14 ARCH-GAP-3）
  mkdir -p "${LOG_DIR}"
  # write-validate-install：先 render 到暫存檔、lint 通過才 mv 進最終路徑，
  # 避免 lint 失敗時壞檔殘留 LaunchAgents（launchd 掃描噪音＋--status 誤報，SD-R13-3）。
  _tmp_plist="$(mktemp "${TMPDIR:-/tmp}/imn_plist.XXXXXX")"
  if ! render_plist "${_tmp_plist}"; then
    rm -f "${_tmp_plist}"
    return 1
  fi
  mv "${_tmp_plist}" "${PLIST_PATH}"
  # 冪等：舊檔已載入時先 unload（未載入的 unload 失敗屬預期，不擋）。
  "${LAUNCHCTL}" unload "${PLIST_PATH}" 2>/dev/null || true
  # `|| true`：load 的 rc 不具鑑別力（見 _launchctl_row 檔頭說明），真正的判準是
  # 下面那道自證；讓 set -e 在此中斷只會讓失敗訊息更難懂。
  "${LAUNCHCTL}" load "${PLIST_PATH}" || true
  if [ -z "$(_launchctl_row)" ]; then
    echo "❌ launchctl load 未生效：${LABEL} 不在 launchctl list（plist 已寫入 ${PLIST_PATH}）" >&2
    if "${LAUNCHCTL}" print-disabled "gui/$(id -u)" 2>/dev/null \
        | grep -q "\"${LABEL}\" => disabled"; then
      echo "   成因：該 label 被標記為 disabled（launchctl print-disabled gui/$(id -u) 可覆核）——" >&2
      echo "   解除後重跑本腳本：launchctl enable gui/$(id -u)/${LABEL}" >&2
    else
      echo "   請看上方 launchctl 自身印出的錯誤（它載入失敗時仍 exit 0，故本腳本改以 list 自證）" >&2
    fi
    return 1
  fi
  echo "✅ 已安裝並載入 launchd 排程：${LABEL}（每日 02:00 → ${NIGHTLY_SH}）"
  echo "   另含 RunAtLoad：開機/載入時補跑當日錯過的一輪（載體自帶當日去重，不重複跑）"
  echo "   驗證：bash tools/install_mac_nightly.sh --status"
}

cmd_uninstall() {
  "${LAUNCHCTL}" unload "${PLIST_PATH}" 2>/dev/null || true
  # unload 自證（R68-M64 同型；unload 失敗亦恆 exit 0）。若不自證就逕行刪 plist，
  # 機器上會留下「仍載入、但磁碟已無 plist」的孤兒狀態——正是 R68-M31 那個下次
  # 登入必死、而舊 --status 報全綠的狀態。本工具不得自己製造它。
  if [ -n "$(_launchctl_row)" ]; then
    echo "❌ launchctl unload 未生效：${LABEL} 仍在 launchctl list——plist 保留未刪" >&2
    echo "   （逕行刪除會留下「已載入但無 plist」的孤兒排程，無法再以本工具卸載）" >&2
    echo "   手動排除後重跑：launchctl bootout gui/$(id -u)/${LABEL}" >&2
    return 1
  fi
  if [ -f "${PLIST_PATH}" ]; then
    rm -f "${PLIST_PATH}"
    echo "✅ 已解除安裝：unload 並刪除 ${PLIST_PATH}"
  else
    echo "✅ 無事可做：${PLIST_PATH} 不存在（unload 已冪等嘗試）"
  fi
}

cmd_status() {
  _loaded=0
  # 心跳／覆蓋連續性「缺席」時要附加的成因提示。預設是「未啟用或尚未跑過第一輪」，
  # 但下方讀到非零 last exit status 時會被覆寫（R68-M30）。
  ABSENT_HINT=""
  _row="$(_launchctl_row)"
  if [ -n "${_row}" ]; then
    _loaded=1
    echo "✅ launchd 已載入：${_row}"
    # 第 2 欄＝last exit status（launchctl list 三欄：PID／Status／Label）。
    # R68-M30：這一欄以前原樣印在螢幕上卻**不被解讀**——載體每晚照跑、每晚在寫出
    # 心跳前就非零退出時，心跳與 RunId log 都永遠不生成，於是兩段報表齊聲宣告
    # 「尚未跑過第一輪（正常）」且 rc=0。那句因果確定為假，且因為心跳檔從第一天起
    # 就不存在，8 天過期哨兵永遠不會啟動——假宣稱是無上界的。對齊
    # install_windows_nightly.ps1 Show-TaskDetail 的 LastTaskResult 列。
    _last_exit="$(printf '%s\n' "${_row}" | awk '{print $2}')"
    case "${_last_exit}" in
      0)
        echo "  ✅ 上次退出碼 = 0   (expected 0)；≙ Windows LastTaskResult"
        ;;
      ''|-)
        echo "  －  上次退出碼 = ${_last_exit:-(缺席)}   (expected 0)；launchctl 未提供數值（尚未跑過或正在執行中）"
        ;;
      *)
        echo "  ⚠️ 上次退出碼 = ${_last_exit}   (expected 0)；≙ Windows LastTaskResult——排程有觸發但載體非零退出，查 ${LOG_DIR}/nightly_mac_launchd.err"
        # 覆寫後「尚未跑過第一輪」這句**整段消失**（不是加註但保留）——保留它等於讓
        # 讀者在兩個互相矛盾的因果之間自行挑一個，而錯的那個才是好消息。
        ABSENT_HINT="——排程已觸發但載體以 exit ${_last_exit} 結束、未寫出心跳（查 AutoClaude/logs/nightly_mac_launchd.err）"
        ;;
    esac
  else
    echo "❌ launchd 未載入 ${LABEL}——安裝：bash tools/install_mac_nightly.sh"
  fi
  if [ -f "${PLIST_PATH}" ]; then
    echo "  plist：存在（${PLIST_PATH}）"
    # 存在性 ≠ 健康（R67-M37）：R15 之前安裝的 plist 無 RunAtLoad、R14 之前導 /tmp，
    # 兩者都會讓排程實際上不補跑/log 散失，而舊版 --status 只做 [ -f ] 恆報綠。
    report_plist_capabilities
  else
    echo "  plist：不存在（${PLIST_PATH}）"
    if [ "${_loaded}" -eq 1 ]; then
      # R68-M31：這是 macOS 專屬的「載入 ≠ 已持久化」狀態，只印一行「不存在」就走
      # 會讓讀者以為那只是少了份備份檔。
      echo "  ⚠️ 目前的載入狀態只活在本次登入 session——磁碟上沒有 plist，下次登入/重開機不會再載入。重裝：bash tools/install_mac_nightly.sh"
    fi
  fi
  report_heartbeat
  report_coverage
  # 硬判準（見檔頭 Exit codes）：已載入 **且** plist 仍在磁碟上。後者才是「下次
  # 登入還會在」的必要條件；只看前者等於把註定死掉的排程判成健康（R68-M31）。
  [ "${_loaded}" -eq 1 ] && [ -f "${PLIST_PATH}" ]
}

MODE="${1:-install}"
case "${MODE}" in
  install)
    cmd_install
    ;;
  --uninstall)
    cmd_uninstall
    ;;
  --status)
    cmd_status
    ;;
  --render-only)
    if [ -z "${2:-}" ]; then
      echo "❌ --render-only 需要輸出路徑參數" >&2
      usage
      exit 1
    fi
    render_plist "$2"
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "❌ 未知參數：${MODE}" >&2
    usage
    exit 1
    ;;
esac
