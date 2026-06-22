#!/usr/bin/env python3
"""Agent scenario_usage frequency SSOT 一致性 lint（DEF-AGTREV-015 機械防復發）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.0X`` 凍結本體，免 Copy-on-Evolve；與 ``collaboration_symmetry_lint.py`` /
``agent_template_lint.py`` / ``framework_status_snapshot.py`` 同精神）。版本無關、
read-only 純觀察者（不寫 FSM-STATE、不影響 churn/meta-loop）。

【問題（DEF-AGTREV-015 家族）】各 persona agent 的 ``scenario_usage.frequency`` 以
``N/10`` 宣告其涵蓋場景數。此數有兩個一致性義務，長期靠人工同步 → 累積漂移
（v0.18 第四輪重審揭露 6 個 agent 與權威統計段系統性不一致 + integration 內部矛盾）：

  1. **跨源 SSOT**：掌舵者裁定 ``scenarios/SCENARIO_AGENT_MAPPING.md`` 的「Agent 使用
     頻率統計（SDD 版）」段為**唯一 SSOT**。凡在該統計段列出的 agent，其 yaml
     ``frequency`` 分子必須等於統計段值。
  2. **內部一致**：``frequency`` 分子必須等於 ``primary_scenarios`` +
     ``supporting_scenarios`` 的場景項數（杜絕「寫 1/10 卻自列 4 場景」這類內部矛盾）。

【判準（任一違反即非零硬閘擋下）】
  * SSOT：統計段列出之 agent，yaml 分子 ≠ 統計段值。
  * 內部：yaml 分子 ≠ (primary + supporting) 場景項數。

【排除】
  * 模板示例檔（``01.agent-template*``）。
  * 無 ``scenario_usage`` 的 runtime agent（``sdd-*``，runtime-schema）。
  * 統計段未列之 agent：僅受「內部一致」約束，不受 SSOT 約束（無對應權威值）。

掃磁碟最新演化版（``discover_frozen_versions`` + ``latest_version``，對齊 ci-gate.sh
``sort -V | tail -1``）的 ``agent/core/*.yaml`` + ``agent/specialized/*.yaml``，
SSOT 來源為同版 ``scenarios/SCENARIO_AGENT_MAPPING.md``。

用法：python scripts/scenario_frequency_lint.py <REPO_ROOT>
Exit：0 全一致；1 任一不一致。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

_TEMPLATE_PREFIXES = ("01.agent-template",)
# 統計段內 "<key>: N/10" 之 key；亦為 agent 檔名去 NN. 前綴與 -zh 後綴之 stem。
_FREQ_NUM_RE = re.compile(r"(\d+)\s*/\s*10")
# 統計段行：行首（容許前導空白）<key>: ... N/10 ...
_STATS_LINE_RE = re.compile(r"^\s*([a-z][a-z0-9-]+):\s*(\d+)\s*/\s*10")
# agent/README.md 核心表列：| # | <NN.role-zh.yaml> | 名 | 角色 | <Label> (N/10) | ... |
# 擷取檔名與 N/10 分子（DEF-AGTREV-017：README 摘要表為 lint 未覆蓋之第三來源，曾與
# 對齊後的 yaml SSOT 漂移〔ba/dev/qa 三處〕）。
_README_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*([\w.\-]+\.ya?ml)\s*\|.*?\((\d+)\s*/\s*10\)")


def _file_key(path: str) -> str:
    """檔名 → 統計段 key：去 ``NN.`` 前綴與 ``-zh.yaml`` / ``.yaml`` 後綴。"""
    base = os.path.basename(path)
    base = re.sub(r"^\d+\.", "", base)
    base = re.sub(r"-zh\.ya?ml$|\.ya?ml$", "", base)
    return base


def parse_stats(mapping_md: str) -> dict[str, int]:
    """解析 SCENARIO_AGENT_MAPPING.md 的頻率統計段 → {key: 分子}。

    只取「Agent 使用頻率統計」標題之後、「SDD Skills 使用對應」之前的區段，
    避免誤抓其他段落的 N/10 字樣。
    """
    out: dict[str, int] = {}
    in_section = False
    for line in mapping_md.splitlines():
        if "使用頻率統計" in line:
            in_section = True
            continue
        if in_section and ("Skills 使用對應" in line or line.startswith("## ") and "頻率" not in line):
            break
        if not in_section:
            continue
        m = _STATS_LINE_RE.match(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def _freq_numerator(scenario_usage: dict) -> int | None:
    freq = scenario_usage.get("frequency") if isinstance(scenario_usage, dict) else None
    if not isinstance(freq, str):
        return None
    m = _FREQ_NUM_RE.search(freq)
    return int(m.group(1)) if m else None


def _listed_count(scenario_usage: dict) -> int:
    total = 0
    for key in ("primary_scenarios", "supporting_scenarios"):
        items = scenario_usage.get(key)
        if isinstance(items, list):
            total += sum(1 for it in items if isinstance(it, dict) and it.get("scenario"))
    return total


def check_readme_table(version_path: str, yaml_nums: dict[str, int]) -> list[str]:
    """DEF-AGTREV-017：agent/README.md 核心表的頻率分子須等於對應 yaml 分子。

    README 摘要表是 yaml/統計段之外的**第三來源**，原 lint 未覆蓋 → 曾在 yaml 對齊
    SSOT 後仍滯留舊值（ba 4≠3、dev 7≠4、qa 7≠8）。此檢查以 yaml 分子為基準
    （yaml 已受上方 SSOT + 內部一致雙約束），擋下 README 與 yaml 漂移。
    README 不存在或某列無對應 yaml 時靜默略過（不誤擋測試 fixture / 模板列）。
    """
    out: list[str] = []
    readme_fp = os.path.join(version_path, "agent", "README.md")
    if not os.path.isfile(readme_fp):
        return out
    with open(readme_fp, encoding="utf-8") as f:
        for line in f:
            m = _README_ROW_RE.match(line)
            if not m:
                continue
            base, rnum = m.group(1), int(m.group(2))
            if base not in yaml_nums:
                continue
            if rnum != yaml_nums[base]:
                out.append(
                    f"agent/README.md：{base} 表列分子 {rnum} ≠ yaml frequency 分子 "
                    f"{yaml_nums[base]}（README 摘要表與 yaml SSOT 漂移）"
                )
    return out


def check(version_path: str) -> list[str]:
    problems: list[str] = []
    mapping_fp = os.path.join(version_path, "scenarios", "SCENARIO_AGENT_MAPPING.md")
    if not os.path.isfile(mapping_fp):
        return [f"找不到 SSOT 來源 {mapping_fp}"]
    with open(mapping_fp, encoding="utf-8") as f:
        stats = parse_stats(f.read())
    if not stats:
        return [f"無法從 {mapping_fp} 解析出頻率統計段（SSOT 來源異常）"]

    files = sorted(glob.glob(os.path.join(version_path, "agent", "core", "*.yaml")) +
                   glob.glob(os.path.join(version_path, "agent", "specialized", "*.yaml")))
    yaml_nums: dict[str, int] = {}
    for fp in files:
        base = os.path.basename(fp)
        if any(base.startswith(p) for p in _TEMPLATE_PREFIXES):
            continue
        with open(fp, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            continue
        su = doc.get("scenario_usage")
        if not isinstance(su, dict):
            continue  # runtime agent / 無 scenario_usage → 豁免
        num = _freq_numerator(su)
        if num is None:
            problems.append(f"{base}：scenario_usage.frequency 無法解析 N/10 分子")
            continue
        yaml_nums[base] = num
        # 內部一致：分子 == 場景清單項數
        listed = _listed_count(su)
        if num != listed:
            problems.append(
                f"{base}：frequency 分子 {num} ≠ 場景清單項數 {listed}"
                f"（primary+supporting；內部矛盾）"
            )
        # 跨源 SSOT：統計段列出者，分子須等於統計段值
        key = _file_key(fp)
        if key in stats and num != stats[key]:
            problems.append(
                f"{base}：frequency 分子 {num} ≠ SCENARIO_AGENT_MAPPING 統計段 SSOT "
                f"{stats[key]}（key={key}）"
            )
    # README 摘要表（第三來源）對齊 yaml SSOT
    problems.extend(check_readme_table(version_path, yaml_nums))
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    latest = latest_version(discover_frozen_versions(repo_root))
    if latest is None:
        print("::error:: 找不到任何 AISDLC_SDD_v0.* 版本目錄")
        return 1
    version_path = os.path.join(repo_root, latest)
    problems = check(version_path)
    if not problems:
        print(f"✅ scenario frequency lint：{latest} 全部 agent frequency 分子與"
              f" SCENARIO_AGENT_MAPPING 統計段 SSOT 一致、且與場景清單項數內部一致")
        return 0
    print(f"::error:: scenario frequency lint 失敗（{latest}），偵測 {len(problems)} 項不一致：")
    for p in problems:
        print(f"  FREQ  {p}")
    print("  修法：對齊 frequency 分子到 SCENARIO_AGENT_MAPPING 統計段 SSOT，並使場景清單項數相符。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
