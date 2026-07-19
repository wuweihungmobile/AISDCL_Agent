#!/usr/bin/env bash
# bootstrap.sh — monorepo 一鍵開發環境整備（macOS / Linux）。
# Windows 對等腳本：tools/bootstrap.ps1
#
# 做什麼：
#   1. 若 .venv 已存在 → 直接沿用（免選直譯器）
#   2. 否則檢查 Python 直譯器 >= 3.11（讀 .python-version 為目標版）並建立 .venv
#      （偵測到 uv 則用 uv 加速，否則 python -m venv + pip）
#   3. 安裝 AutoClaude（editable, [dev,notifications,lint]）+ AISDLC_SDD CI 依賴
#   4. 印出啟用指引與 git-hooks 安裝選項（不自動改 core.hooksPath，見文末說明）
#
# 為何需要：本 repo 的 hooks/腳本大量使用裸 `python`；macOS 預設只有 `python3`。
# 啟用 .venv 後 `python` 在 macOS 與 Windows 都存在於 PATH，所有裸 python 呼叫
# （含 30 個凍結版 SDD hooks）即原樣可運作，無需逐一改動。
set -euo pipefail

# --- 定位 repo 根（本腳本位於 <root>/tools/）---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

VENV_DIR="$ROOT/.venv"
# redirect 順序：2>/dev/null 先於 < 檔案，檔案不存在時 shell 的 redirect 錯誤才會被吞掉
PY_TARGET="$(tr -d ' \t\r\n' 2>/dev/null < "$ROOT/.python-version" || echo '3.11')"
# 對齊 .ps1：三段版號（如 3.11.9）截為 major.minor（3.11）——「python3.11.9」命名的
# 直譯器不存在、uv --python 也以 major.minor 解析，與 tools/bootstrap.ps1 行為對等
PY_TARGET="$(printf '%s' "$PY_TARGET" | cut -d. -f1,2)"

echo "===== AISDCL_Agent bootstrap（macOS/Linux）====="
echo "repo 根：$ROOT"
echo "目標 Python：>= ${PY_TARGET}（.python-version）"

# --- 1. 選一個 >=3.11 的直譯器（僅 .venv 不存在時需要）---
pick_python() {
  local candidates=("python$PY_TARGET" "python3.12" "python3.11" "python3" "python")
  for c in "${candidates[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
        echo "$c"; return 0
      fi
    fi
  done
  return 1
}

USE_UV=0
if command -v uv >/dev/null 2>&1; then
  USE_UV=1
  echo "偵測到 uv → 使用 uv 建立/安裝（加速）"
fi

# --- 2. 建立 .venv（存在檢查先行：venv 已存在就不需系統有 >=3.11 直譯器）---
if [ -d "$VENV_DIR" ]; then
  # 形狀檢查：跨平台共用工作目錄時，Windows 建的 .venv 只有 Scripts\python.exe（無
  # bin/python），沿用會到後續 pip/pytest 才以不友善錯誤失敗 → 這裡先 fail-fast。
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "" >&2
    echo "❌ 既有 .venv 缺 bin/python（多半是 Windows 上建立的 .venv）— 本平台無法沿用。" >&2
    echo "   請刪除後重建：rm -rf .venv && bash tools/bootstrap.sh" >&2
    exit 1
  fi
  echo "偵測到既有 .venv → 沿用（如需重建請先 rm -rf .venv）"
else
  BASE_PY=""
  if [ "$USE_UV" -eq 0 ]; then
    if ! BASE_PY="$(pick_python)"; then
      echo "" >&2
      echo "❌ 找不到 Python >= ${PY_TARGET}。" >&2
      echo "   macOS 安裝建議：brew install python@3.11" >&2
      echo "   或安裝 uv（自動管理版本）：curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
      exit 1
    fi
    echo "使用直譯器：${BASE_PY}（$("$BASE_PY" --version 2>&1)）"
    # 版本一致性提醒（不 fail，維持「>=3.11 可用」既有語意）：與 .python-version 目標不同時警告
    ACTUAL_MM="$("$BASE_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo '')"
    if [ -n "$ACTUAL_MM" ] && [ "$ACTUAL_MM" != "$PY_TARGET" ]; then
      echo "⚠️  選定直譯器為 ${ACTUAL_MM}，與 .python-version 目標 ${PY_TARGET} 不一致（>=3.11 仍可用，僅提醒）"
    fi
  fi
  echo "建立虛擬環境：.venv"
  if [ "$USE_UV" -eq 1 ]; then
    uv venv --python "$PY_TARGET" "$VENV_DIR"
  else
    "$BASE_PY" -m venv "$VENV_DIR"
  fi
  # fail-fast（對照 tools/bootstrap.ps1 同款守門）：建立指令 rc=0 不保證真的產出
  # 可用直譯器（2026-07-13 runner 真實事故：建立指令秒退回報成功但未產出）。
  # set -e 只擋非零 rc，這裡補「假成功」驗證，與上方既有 .venv 沿用分支對稱。
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    if [ "$USE_UV" -eq 1 ]; then USED_INTERP="uv --python $PY_TARGET"; else USED_INTERP="$BASE_PY"; fi
    echo "" >&2
    echo "❌ .venv 建立指令回報成功（rc=0）但 bin/python 不存在（直譯器：$USED_INTERP）。" >&2
    echo "   請刪除後重試：rm -rf .venv && bash tools/bootstrap.sh" >&2
    exit 1
  fi
fi

VENV_PY="$VENV_DIR/bin/python"

# --- 3. 安裝依賴 ---
pip_install() {
  if [ "$USE_UV" -eq 1 ]; then
    uv pip install --python "$VENV_PY" "$@"
  else
    "$VENV_PY" -m pip install "$@"
  fi
}

echo ""
echo "----- 安裝依賴 -----"
if [ "$USE_UV" -eq 0 ]; then
  "$VENV_PY" -m pip install --upgrade pip >/dev/null
fi

echo "[1/2] AutoClaude（editable, [dev,notifications,lint]）"
pip_install -e "$ROOT/AutoClaude/.[dev,notifications,lint]"

SDD_REQ="$ROOT/AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt"
if [ -f "$SDD_REQ" ]; then
  echo "[2/2] AISDLC_SDD CI 依賴（requirements-ci.txt）"
  pip_install -r "$SDD_REQ"
else
  echo "[2/2] 略過：找不到 $SDD_REQ"
fi

# --- 4. 完成指引 ---
cat <<EOF

✅ bootstrap 完成。

下一步（每個新終端機都要做，或設進 shell profile / VSCode 直譯器）：
    source .venv/bin/activate

啟用後驗證：
    which python            # 應指向 .venv/bin/python
    cd AutoClaude && python -m pytest tests/ -q
    cd AISDLC_SDD && bash scripts/ci-gate.sh

🔴 重要：請在「已啟用 .venv 的終端機」中啟動 Claude Code，否則 hooks 用的
   裸 \`python\` 會在 macOS 找不到直譯器。VSCode 則於右下角選 .venv 為直譯器。

git hooks（選用）：安裝根層 dispatcher hooks — 兩子專案閘門同時生效
（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，依 commit/push
涉及路徑自動分流），不再互斥；任一支安裝腳本皆指向同一 dispatcher，跑一次即可：
    bash AutoClaude/tools/install_git_hooks.sh
    （或 bash AISDLC_SDD/scripts/install-hooks.sh，效果相同）
EOF
