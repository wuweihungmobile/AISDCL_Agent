#!/usr/bin/env bash
# DEF-11-001（P3）Copy-on-Evolve 通用安全複製 helper —— 只入真框架源碼、排除 runtime 產物。
#
# 用法：
#   scripts/copy_on_evolve.sh <from_dir> <to_dir>
#     <from_dir>  既有凍結版本目錄（如 AISDLC_SDD_v0.05）
#     <to_dir>    新版本目錄（如 AISDLC_SDD_v0.06；必須尚不存在，拒絕覆蓋）
#
# 排除清單（「輸出非輸入」runtime 產物，與 AISDLC_SDD/.gitignore 之 v0.0X 區塊同源）：
#   __pycache__/ *.pyc *.pyo  — Python 編譯快取
#   build/reports/            — FSM/abort/drift/test-analysis/formal 等運行時取證輸出
#   arch-fitness.json         — arch_fitness / ci-gate 每跑重生
#   chaos-report.json         — chaos sweep 重生
# 保留 build/planning/、build/logs/README.md 等真源碼。
#
# WHY（Rule 9 設計意圖）：v0.01 官方 AISDLC_SDD_UPGRADE_SOP.md §2.1 用 `cp -r` 整碗複製
# + §5 `git add .`，會把上述 runtime 產物一併夾帶入 Copy-on-Evolve commit（DEF-11-001：
# would-add 1013 含 173 build/reports + arch-fitness.json）。本 helper 以 `tar --exclude`
# 串流複製（排除發生在複製「之前」，runtime 產物從不落地），避免污染。
# rsync 在 Windows Git Bash 不可用（`command -v rsync` rc=1），故採 GNU tar（Git Bash /
# Linux / macOS 通用）。本腳本置於 AISDLC_SDD/scripts/（versioned 目錄外＝共享 CI infra）
# → 免 Copy-on-Evolve（同 ci-gate.sh / conftest.py / pytest_passed_count.sh /
# cross_version_guard.py 精神）。
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "用法: $0 <from_dir> <to_dir>" >&2
  exit 2
fi

FROM="$1"
TO="$2"

if [ ! -d "$FROM" ]; then
  echo "❌ 來源目錄不存在: $FROM" >&2
  exit 1
fi
if [ -e "$TO" ]; then
  echo "❌ 目標已存在（拒絕覆蓋，請先移除或改名）: $TO" >&2
  exit 1
fi

mkdir -p "$TO"
# tar --exclude：無斜線樣式（__pycache__/*.pyc/*.pyo）比對 basename → 任意深度命中；
# 含斜線樣式（./build/reports 等）比對完整成員名 → 僅頂層命中（對齊 .gitignore 語意）。
tar -C "$FROM" \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='./build/reports' \
  --exclude='./arch-fitness.json' \
  --exclude='./chaos-report.json' \
  -cf - . | tar -C "$TO" -xf -

# DEF-15-001（improving_15 B 軌 dogfooding）：build/reports/ 整樹排除會誤刪
# build/reports/fsm/FSM-STATE-TEMPLATE.yaml —— 它是 state_loader._load_template()
# 必需的 FSM 種子模板（真輸入、非運行時輸出；.gitignore 對 v0.01 以 `!` 負向保留同此意）。
# 若漏帶，演化版整個 FSM runtime 無法 bootstrap（_load_template 觸 FileNotFoundError，
# 46+ FSM 測試全紅）。故排除後補回該模板（來源存在時）。
_TMPL_REL="build/reports/fsm/FSM-STATE-TEMPLATE.yaml"
if [ -f "$FROM/$_TMPL_REL" ]; then
  mkdir -p "$TO/$(dirname "$_TMPL_REL")"
  cp "$FROM/$_TMPL_REL" "$TO/$_TMPL_REL"
  _TMPL_NOTE="；已保留 FSM 種子模板 $_TMPL_REL（DEF-15-001）"
else
  _TMPL_NOTE=""
fi

echo "✅ Copy-on-Evolve 完成: $FROM → $TO（已排除 __pycache__/*.pyc/*.pyo + build/reports/ + arch-fitness.json + chaos-report.json${_TMPL_NOTE}）"
