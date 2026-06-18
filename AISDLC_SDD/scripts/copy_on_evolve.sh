#!/usr/bin/env bash
# DEF-38-001（P3）Copy-on-Evolve git-archive 版 —— 結構性只匯 git tracked 源碼。
#
# 用法：
#   scripts/copy_on_evolve.sh <from_dir> <to_dir>
#     <from_dir>  既有凍結版本目錄（須為 git tracked 且 committed 於 HEAD）
#     <to_dir>    新版本目錄（必須尚不存在，拒絕覆蓋）
#
# WHY（取代 DEF-11-001 tar --exclude 版的設計演進）：
#   舊版以 `tar --exclude` 在複製前剔除已知 runtime 產物（build/reports/ /
#   arch-fitness.json / chaos-report.json / __pycache__ / *.pyc）。但 **--exclude 清單未含
#   `tools/fsm_runtime/formal/states/`**（TLC 模型檢查每跑一次 dump 一個時間戳目錄）——
#   DEF-38-001：來源版若跑過 TLC 累積 states，tar 會把這坨 bloat 一路搬運繼承（v0.05~v0.13
#   實證每版肥 19MB／5193 檔，皆為從 v0.01 一路拖來的同一份副本）。
#   **git archive 從根本解決**：它只輸出 git tracked（committed 於 HEAD）的內容，一切
#   untracked / gitignored 的 runtime 產物（build/reports、formal/states、arch-fitness.json、
#   chaos-report.json、__pycache__、*.pyc…）**結構性被排除**，無需維護任何 --exclude 清單，
#   且永不再因新 runtime 產物類型而 bloat 回歸。tracked 即輸入、untracked 即輸出，邊界由 git
#   單一事實源裁定。FSM 種子模板（DEF-15-001，state_loader._load_template 必需的真輸入）因為
#   是 tracked（v0.13+ 在 tools/fsm_runtime/templates/；v0.05~v0.12 在 build/reports/fsm/ 經
#   `!` negate 保持 tracked），git archive 一律納入，舊版 tar 的「排除後補回」特例自然消失。
#
#   注意：git archive 取 **HEAD（committed）** 樹，非工作樹/index——故來源版須已 commit
#   （Copy-on-Evolve 的來源恆為凍結唯讀版，必已 commit，語意正確且更安全）。
#
#   本腳本置於 AISDLC_SDD/scripts/（versioned 目錄外＝共享 CI infra）→ 免 Copy-on-Evolve
#   （同 ci-gate.sh / conftest.py / cross_version_guard.py 精神）。
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

# git archive 需要「repo 根相對」的 tree-ish 路徑。以 `git -C "$FROM" rev-parse --show-prefix`
# 由 git 自身計算 FROM 相對 repo 根的路徑——避開 Windows Git Bash 中 `--show-toplevel`（回 D:/…）
# 與 `pwd`（回 /d/…）路徑形式不一致導致前綴剝除失敗的陷阱（smoke test 揭露）。
if ! FROM_REL="$(git -C "$FROM" rev-parse --show-prefix 2>/dev/null)"; then
  echo "❌ 來源不在 git 工作樹內: $FROM" >&2
  exit 1
fi
FROM_REL="${FROM_REL%/}"  # 去尾斜線

# 🔴 所有 tree 操作一律 `git -C "$TOP"`（以 repo 根為 cwd）。否則 `HEAD:<path>` 會被當成
# **cwd 相對**解析（從子目錄呼叫時 git 疊上 cwd 前綴 → 匯出 0 檔，smoke test 第二次揭露）。
TOP="$(git rev-parse --show-toplevel)"

# 來源須 tracked 於 HEAD（git archive 只認 committed tree；未追蹤目錄會 fatal）。
if ! git -C "$TOP" rev-parse --verify -q "HEAD:$FROM_REL" >/dev/null 2>&1; then
  echo "❌ 來源未被 git tracked 於 HEAD（git archive 版只匯 committed tracked 內容）: $FROM_REL" >&2
  echo "   若來源為本輪新建尚未 commit，請先 commit 後再 Copy-on-Evolve。" >&2
  exit 1
fi

mkdir -p "$TO"
git -C "$TOP" archive "HEAD:$FROM_REL" | tar -x -C "$TO"

_N="$(git -C "$TOP" ls-tree -r --name-only "HEAD:$FROM_REL" | wc -l | tr -d ' ')"
echo "✅ Copy-on-Evolve（git archive，純 tracked）: $FROM → $TO（匯出 ${_N} tracked 檔；結構性排除所有 untracked/gitignored runtime 產物，含 build/reports/ 與 formal/states/，DEF-38-001）"
