#!/usr/bin/env bash
# AISDLC-SDD — 用 act 在地端跑 ci.yml（approach 二）。
# 前置：已安裝 act（見 README/ADR）+ Docker 執行中。
# 用法：bash scripts/act-ci.sh                # 跑 ci.yml 的 push 事件
#       bash scripts/act-ci.sh pull_request   # 改跑 pull_request 事件
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v act >/dev/null 2>&1; then
  echo "::error:: 未安裝 act。請先安裝（winget install nektos.act / choco install act-cli / scoop install act）。" >&2
  exit 2
fi

# 預拉 runner 鏡像（best-effort）：用 docker CLI 拉（正確處理 credsStore），
# 之後 .actrc 的 --pull=false 即可用本地鏡像，繞過 act forcePull 的認證問題。
docker pull catthehacker/ubuntu:act-latest 2>/dev/null || \
  echo "（鏡像預拉略過——若已存在本地可忽略）"

EVENT="${1:-push}"
echo "==> act：以 ${EVENT} 事件跑 .github/workflows/ci.yml"
if [[ "${EVENT}" == "push" ]]; then
  act push -W .github/workflows/ci.yml -e .github/act/push-event.json
else
  act "${EVENT}" -W .github/workflows/ci.yml
fi
