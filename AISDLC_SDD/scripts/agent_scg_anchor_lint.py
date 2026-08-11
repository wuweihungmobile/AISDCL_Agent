#!/usr/bin/env python3
"""Agent 閘門錨點 ↔ SCG SSOT 一致性 lint（AGT-03／AGT-04，R84）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.XX`` 本體，免 Copy-on-Evolve；與 ``agent_template_lint.py`` /
``collaboration_symmetry_lint.py`` / ``scenario_frequency_lint.py`` 同精神）。
版本無關、read-only 純觀察者（不寫 FSM-STATE、不影響 churn/meta-loop）。

【立案事實（AGT-03）】LATEST agent 樹有 **16 個站點／14 支檔**把 RTM 的 AT 欄位錨在
``SCG-4（測試計畫後）``，而 SCG SSOT（``workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md``
的閘門表）逐字寫著「SCG-4 | PR Review Gate」「SCG-5 | RTM Completeness Gate」——
**SCG-4 根本不是測試閘門**；測試策略閘門是角色 sub-gate ``RG-TEST``
（``guides/system/sdd/SDD_GUIDE.md`` 的補充閘門表：SCG-3 後、測試開始前）。
照 agent 走的話 AT 欄位要等 PR 審查期才填，而 SCG-5 的把關者（qa-lead）在交付前
拿不到 100% 覆蓋依據 ⇒ **閘門順序被 agent prompt 反轉**。

【立案事實（AGT-04）】ci-gate 已跑 3 支 agent lint 且當回合實測全綠（各 rc=0）
⇒ 那 16 個錯錨在現行閘門下**結構上看不見**。基礎設施齊備、只缺這一支判準。

────────────────────────────────────────────────────────────────────────
判準（任一違反即非零硬閘擋下）
────────────────────────────────────────────────────────────────────────
1. **主題歸屬（topic ownership）**：agent 檔內每個 ``SCG-N`` 錨點的「標籤」若含有
   某個**主題標記**，而該標記在 SSOT 裡屬於另一個閘門（或根本不屬於任何 SCG），即紅。
   標籤＝錨點之後、到下一個子句分隔符（``、，。；：|"'`` 或換行）或下一個閘門碼
   （``SCG-`` / ``RG-``）為止，上限 24 字元。
2. **標記表自證（map is SSOT-derived, not a third home）**：本檔的標記表在每次執行時
   都必須通過自證——owner 為 ``SCG-N`` 的標記，必須在 SSOT 閘門表中**只**出現在該列；
   owner 為 ``RG-*`` 的標記，必須在 SSOT 閘門表中**一列都不出現**（＝沒有任何 SCG 擁有它）。
   自證失敗即紅（fail-loud）：SSOT 改了而本表沒跟上時，寧可整支 lint 紅，不可靜默放行。
   🔴 這一條的存在理由：不做自證的話，這張表就是同一份知識的第三個家。
3. **單一真相源引用可解析**：agent yaml 內以 ``inherits_from:`` / ``platform_neutrality:`` /
   ``correction_protocol:`` 指向的框架根相對 ``.md`` 路徑（本輪＝
   ``agent/EVIDENCE_DISCIPLINE.md``）必須在同版磁碟上存在。引用一個不存在的家＝
   把「只有一個家」寫成假話，而它不會有任何其他東西轉紅。
4. **version 欄不得寫死版號**：``agent.version`` 一律指向 SSOT
   （``see FRAMEWORK_STATUS.md`` 字樣），不得是 ``vX.YY`` 字面。
   🔴 立案事實（AGT-05）：27 支 agent 的 version 在框架走到 v0.30 時全部還寫著 v0.18，
   且無任何 lint 在守——讀者無從判斷手上這支 agent 是否隨框架演化過。修法選「指向 SSOT」
   而非「每輪回填版號」：回填會在下一次開版時再度全部過期，而指標不會。

【排除】
  * ``#`` 開頭的註解行（訂正協議要求把被訂正的原文逐字保留，那些原文必然含舊錯錨；
    與 ``agent_template_lint.py``「註解行一律忽略」同慣例）。
  * 只掃 LATEST（凍結基線與中間歷史版一律不動，改它們本身就是違規）。

用法：python scripts/agent_scg_anchor_lint.py <REPO_ROOT>
Exit：0 全部一致；1 任一違反。
"""
from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import (  # noqa: E402
    discover_frozen_versions,
    force_utf8_stdio,
    latest_version,
)

# 🔴 刻意不自帶第 11 份行內 `reconfigure`：島內共用入口住 `rfc_lifecycle_lint`
# （見該函式 docstring 與 `tools/tests/test_platform_utils_dedup.py` 的 per-tree 棘輪）。
force_utf8_stdio()

# SSOT 檔（相對於版本目錄）
SCG_SSOT = os.path.join("workflow", "sdd-spec-first-gate", "SDD_SPEC_FIRST_GATE.md")
RG_SSOT = os.path.join("guides", "system", "sdd", "SDD_GUIDE.md")

# 主題標記 → 擁有它的閘門。每一筆的 owner 都由判準 2 對著 SSOT 自證，
# 所以本表不是「第三個家」，而是「SSOT 的可執行索引」。
TOPIC_OWNER: dict[str, str] = {
    # RG-* 擁有的主題：SCG 閘門表一列都不會提到它們 ⇒ 任何 SCG-N 宣稱擁有它即為錯錨。
    "測試計畫": "RG-TEST",
    "測試策略": "RG-TEST",
    "測試規格": "RG-TEST",
    # SCG-N 各自擁有的主題：只能出現在自己那一列。
    "RTM": "SCG-5",
    "PR Review": "SCG-4",
    "Contract Freeze": "SCG-3",
}

_ANCHOR = re.compile(r"SCG-([0-6])")
_LABEL_STOP = re.compile(r"[、，。；：|\n\"']|SCG-|RG-")
_LABEL_MAX = 24
# SSOT 閘門表列：`| 🔷 SCG-N | <名稱> | <觸發條件> | <主責> |`
_SSOT_ROW = re.compile(r"^\|\s*[^|]*SCG-([0-6])\s*\|(.*)$")
_VERSION_LINE = re.compile(r'^\s{2}version:\s*"(.*)"\s*$')
_VERSION_POINTER = "see FRAMEWORK_STATUS.md"
_VERSION_LITERAL = re.compile(r"^v\d+\.\d+$")
# 單一真相源引用：框架根相對 .md
_HOME_REF = re.compile(
    r"(?:inherits_from|platform_neutrality|correction_protocol)\s*:.*?"
    r"((?:agent|docs_template|guides|workflow)/[^\s\"'\]，、）]+\.md)"
)


def _agent_files(version_path: str) -> list[str]:
    pats = [os.path.join(version_path, "agent", "**", "*.yaml"),
            os.path.join(version_path, "agent", "**", "*.md")]
    out: list[str] = []
    for p in pats:
        out.extend(sorted(glob.glob(p, recursive=True)))
    return out


def parse_scg_ssot(version_path: str) -> dict[str, str]:
    """從 SCG SSOT 閘門表抽出 {gate: 該列全文}。找不到表即回空 dict（由呼叫端 fail-loud）。"""
    fp = os.path.join(version_path, SCG_SSOT)
    rows: dict[str, str] = {}
    if not os.path.isfile(fp):
        return rows
    with open(fp, encoding="utf-8") as f:
        for line in f:
            m = _SSOT_ROW.match(line)
            if m and "|" in m.group(2):
                rows.setdefault("SCG-" + m.group(1), m.group(2))
    return rows


def validate_topic_map(version_path: str) -> list[str]:
    """判準 2：標記表必須由 SSOT 自證，否則本 lint 就是第三個家。"""
    problems: list[str] = []
    rows = parse_scg_ssot(version_path)
    if len(rows) < 7:
        problems.append(
            f"SCG SSOT 閘門表解析失敗（{SCG_SSOT} 只解析到 {len(rows)} 列，預期 7 列 SCG-0~6）"
            "——判準的輸入不可信時一律 fail-loud，不得靜默放行"
        )
        return problems
    if not os.path.isfile(os.path.join(version_path, RG_SSOT)):
        problems.append(f"RG-* 補充閘門表 SSOT 不存在：{RG_SSOT}")
    for marker, owner in TOPIC_OWNER.items():
        holders = [g for g, text in rows.items() if marker in text]
        if owner.startswith("SCG-"):
            if holders != [owner]:
                problems.append(
                    f"標記表自證失敗：標記 {marker!r} 宣稱屬於 {owner}，但 SSOT 閘門表中"
                    f"擁有它的是 {holders or '（無）'} —— SSOT 已變動而本表未跟上"
                )
        else:
            if holders:
                problems.append(
                    f"標記表自證失敗：標記 {marker!r} 宣稱屬於角色 sub-gate {owner}"
                    f"（不該被任何 SCG 擁有），但 SSOT 閘門表中 {holders} 提到了它"
                )
    return problems


def _label(line: str, end: int) -> str:
    tail = line[end:end + _LABEL_MAX]
    m = _LABEL_STOP.search(tail)
    return tail[:m.start()] if m else tail


def check_anchors(version_path: str) -> list[str]:
    """判準 1：SCG-N 的標籤不得含有屬於別的閘門（或不屬於任何 SCG）的主題標記。"""
    problems: list[str] = []
    for fp in _agent_files(version_path):
        rel = os.path.relpath(fp, version_path)
        with open(fp, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if line.lstrip().startswith("#"):
                    continue  # 訂正協議要求保留的原文住在註解裡
                for m in _ANCHOR.finditer(line):
                    gate = "SCG-" + m.group(1)
                    label = _label(line, m.end())
                    for marker, owner in TOPIC_OWNER.items():
                        if marker in label and owner != gate:
                            problems.append(
                                f"{rel}:{lineno}：{gate} 的標籤 {label!r} 含主題 {marker!r}，"
                                f"而該主題屬於 {owner}（SSOT：{SCG_SSOT}／{RG_SSOT}）"
                            )
    return problems


def check_single_home_refs(version_path: str) -> list[str]:
    """判準 3：指向「單一真相源」的引用路徑必須真的存在。"""
    problems: list[str] = []
    for fp in _agent_files(version_path):
        if not fp.endswith(".yaml"):
            continue
        rel = os.path.relpath(fp, version_path)
        with open(fp, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if line.lstrip().startswith("#"):
                    continue
                for m in _HOME_REF.finditer(line):
                    target = m.group(1)
                    head = target.split("::")[0]
                    if not os.path.isfile(os.path.join(version_path, head)):
                        problems.append(
                            f"{rel}:{lineno}：單一真相源引用 {head!r} 在磁碟上不存在"
                            "（引用一個不存在的家＝把『只有一個家』寫成假話）"
                        )
    return problems


def check_version_pointer(version_path: str) -> list[str]:
    """判準 4：agent.version 不得寫死版號。"""
    problems: list[str] = []
    for fp in _agent_files(version_path):
        if not fp.endswith(".yaml"):
            continue
        rel = os.path.relpath(fp, version_path)
        with open(fp, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                m = _VERSION_LINE.match(line.rstrip("\n"))
                if not m:
                    continue
                val = m.group(1)
                if _VERSION_LITERAL.match(val) or (_VERSION_POINTER not in val):
                    problems.append(
                        f"{rel}:{lineno}：agent.version = {val!r} 寫死版號／未指向 SSOT；"
                        f"應含 {_VERSION_POINTER!r}（AGT-05：寫死即過期，27 支曾一起停在 v0.18）"
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else "."
    versions = discover_frozen_versions(repo_root)
    latest = latest_version(versions)
    if not latest:
        print("⚠️ 找不到任何版本目錄，略過 agent 閘門錨點 lint")
        return 0
    version_path = os.path.join(repo_root, latest)

    problems = validate_topic_map(version_path)
    problems += check_anchors(version_path)
    problems += check_single_home_refs(version_path)
    problems += check_version_pointer(version_path)

    if problems:
        print(f"❌ Agent 閘門錨點 lint 失敗（{latest}）：{len(problems)} 筆")
        for p in problems:
            print("   - " + p)
        return 1
    print(f"✅ Agent 閘門錨點 ↔ SCG SSOT 一致（{latest}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
