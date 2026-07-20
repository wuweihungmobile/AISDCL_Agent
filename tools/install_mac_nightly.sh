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
# StartCalendarInterval 02:00、StandardOut/ErrorPath=AutoClaude/logs/nightly_mac_launchd.{log,err}
#（R14 ARCH-GAP-3：原導 /tmp 會被 macOS 週期清理＋重開機清空，深夜失敗數日後排查 log 已散失；
# 改與心跳檔同目錄（gitignored）集中取證，install 時 mkdir -p 保證目錄存在）。
#
# --status 心跳三態語意對齊 tools/dev_start.py _check_nightly_heartbeat（R12
# ARCH-R12-2）：缺席→提示（排程可能未啟用）；mtime > 8 天→過期警告；否則新鮮。
#
# Exit codes：0＝成功（--status 時＝launchd 已載入）；1＝失敗（--status 時＝未載入
# 或 plist 缺席）。心跳三態屬 advisory，不影響 --status exit code（對齊 dev_start
# 「皆不阻擋」語意——排程「有沒有載入」才是本工具的機械判準）。
#
# 測試縫（fake 環境驗證用；正常安裝不需理會）：IMN_LAUNCHCTL 可指向 stub 以驗證
# launchctl 呼叫序列而不真載入（本 repo 紀律：真安裝屬使用者 ops，須另行核可）。
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
  <key>StandardOutPath</key><string>${LOG_DIR}/nightly_mac_launchd.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/nightly_mac_launchd.err</string>
</dict>
</plist>
EOF_PLIST
  plutil -lint "${_target}" >/dev/null || {
    echo "❌ 產出的 plist 未通過 plutil -lint：${_target}" >&2
    return 1
  }
  echo "✅ plist 已產出並通過 plutil -lint：${_target}"
}

# 心跳三態（advisory；語意鏡射 tools/dev_start.py _check_nightly_heartbeat）。
report_heartbeat() {
  if [ ! -f "${HEARTBEAT}" ]; then
    echo "  心跳：未偵測（AutoClaude/logs/nightly_mac_latest.log 不存在）——排程可能未啟用或尚未跑過第一輪（設定見 ONBOARDING §8）"
    return 0
  fi
  _mtime="$(stat -f %m "${HEARTBEAT}")"
  _now="$(date +%s)"
  _age_days=$(( (_now - _mtime) / 86400 ))
  # 過期判定以「秒」比較（與 dev_start.py 浮點天數 > 8 精確等價）：shell 整數除法
  # 會把 8.5 天截斷成 8 天而誤判「新鮮」，(8,9) 天窗口與 dev_start 背離（SD-R13-1）。
  if [ $(( _now - _mtime )) -gt $(( HEARTBEAT_MAX_AGE_DAYS * 86400 )) ]; then
    echo "  ⚠️ 心跳：過期（距今 ${_age_days} 天 > ${HEARTBEAT_MAX_AGE_DAYS} 天）——排程可能已斷載，請檢查 launchctl（ONBOARDING §8）"
  else
    echo "  ✅ 心跳：新鮮（距今 ${_age_days} 天）"
  fi
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
  "${LAUNCHCTL}" load "${PLIST_PATH}"
  echo "✅ 已安裝並載入 launchd 排程：${LABEL}（每日 02:00 → ${NIGHTLY_SH}）"
  echo "   驗證：bash tools/install_mac_nightly.sh --status"
}

cmd_uninstall() {
  "${LAUNCHCTL}" unload "${PLIST_PATH}" 2>/dev/null || true
  if [ -f "${PLIST_PATH}" ]; then
    rm -f "${PLIST_PATH}"
    echo "✅ 已解除安裝：unload 並刪除 ${PLIST_PATH}"
  else
    echo "✅ 無事可做：${PLIST_PATH} 不存在（unload 已冪等嘗試）"
  fi
}

cmd_status() {
  _loaded=0
  # label 全字比對（第 3 欄精確等值）——grep -F 子字串會把 com.autoclaude.nightly2
  # 之類前綴 label 誤判為已載入（SD-R13-4）；launchctl 失敗以 || true 收斂後判空。
  _row="$("${LAUNCHCTL}" list 2>/dev/null | awk -v l="${LABEL}" '$3 == l' || true)"
  if [ -n "${_row}" ]; then
    _loaded=1
    echo "✅ launchd 已載入：${_row}"
  else
    echo "❌ launchd 未載入 ${LABEL}——安裝：bash tools/install_mac_nightly.sh"
  fi
  if [ -f "${PLIST_PATH}" ]; then
    echo "  plist：存在（${PLIST_PATH}）"
  else
    echo "  plist：不存在（${PLIST_PATH}）"
  fi
  report_heartbeat
  [ "${_loaded}" -eq 1 ]
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
