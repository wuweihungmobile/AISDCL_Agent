#!/usr/bin/env bash
# AISDLC-SDD — 安裝 git hooks（approach 三）。設 core.hooksPath=.githooks，
# 啟用 pre-push 本機 CI 閘門。對 Claude Code 的 .claude/hooks/ 無影響（那是
# settings.json 驅動，非 git hook）。
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true
echo "✅ 已設定 core.hooksPath=.githooks"
echo "   pre-push 閘門已啟用：每次 push 前自動跑 scripts/ci-gate.sh"
echo "   （選用）若改用 pre-commit 框架：pip install pre-commit && pre-commit install --hook-type pre-push"
