#!/usr/bin/env bash
# DEF-06-001（P3）取證友善性 — 從 pytest 輸出擷取最終「N passed」收斂計數。
#
# 純函式（讀 stdin，印出單一整數到 stdout）：
#   - 取**最後一個** `N passed` summary（避免抓到中途進度行／多版串接）。
#   - 容忍尾隨修飾（`, M skipped`/`, K warnings`/`in Xs`）。
#   - 無任何匹配時印 0（fail-soft：取證輔助絕不該反害硬閘退出碼）。
#
# 抽為獨立純函式之理由：與 scripts/cross_version_guard.py 同精神，使收斂計數的
# 解析意圖能被 scripts/tests/ 快速單測鎖定，而不必實跑 ~95s 的整套 pytest。
set -euo pipefail

count="$(grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')" || true
echo "${count:-0}"
