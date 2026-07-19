#!/usr/bin/env python3
"""核心 agent collaboration_rules 對稱性 lint（DEF-AGTREV-004 機械防復發）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.0X`` 凍結本體，免 Copy-on-Evolve；與 ``cross_version_guard.py`` /
``rfc_lifecycle_lint.py`` / ``gitignore_coverage_lint.py`` / ``agent_template_lint.py`` /
``framework_status_snapshot.py`` 同精神）。版本無關、read-only 純觀察者
（不寫 FSM-STATE、不影響 churn/meta-loop）。

【問題（DEF-AGTREV-003 家族）】核心 agent 的 ``collaboration_rules`` 以
upstream/downstream/peer 三類人工宣告協作關係。這份宣告本應構成**對稱有向圖**：
  * 每條 downstream X→Y（X 把 Y 列為下游）必有對側 Y upstream←X（Y 把 X 列為上游）；
  * 每條 peer X~Y 必有對側 peer Y~X（peer 語意天生雙向）。
但全靠人工同步 → 長期累積多處**斷鏈**（單向 downstream 漏對側 upstream、peer 單向）。
DEF-AGTREV-003 只修了 BA→SA/SD 一處；本 lint 機械強制全圖對稱，杜絕再生。

【判準（任一不對稱即非零硬閘擋下）】
  1. downstream X→Y 但 Y 無 upstream←X。
  2. peer X~Y 但 Y 無 peer~X（自環 X~X 不要求對側，忽略）。
  3. upstream X←Y 但 Y 既無 downstream→X 亦無 peer~X（Y 完全不承認 X＝真實斷鏈；
     DEF-AGTREV-014 補上游反向盲區。接受 down 或 peer 任一為合法對側，故 upstream
     vs peer 的視角差不誤判）。

【排除】
  * 模板示例檔（``01.agent-template*``）：非真實 agent，僅結構範例。
  * 外部角色（``Stakeholders/Business`` 等不對應任何核心 agent 檔者）：圖的外部來源，
    不在 7 核心 agent 集合內，無從要求對側宣告 → 只在「內部↔內部」邊上判對稱。
  * 註解掉的 YAML（``#`` 開頭）：由 ``yaml.safe_load`` 自然忽略。

掃磁碟最新演化版（``discover_frozen_versions`` + ``latest_version``，複用
``rfc_lifecycle_lint``，對齊 ``scripts/sdd_version.py`` SSOT 的 LATEST 語意；沿用磁碟
掃描之 WHY 見該檔豁免註記）的 ``agent/core/*.yaml``。

用法：python scripts/collaboration_symmetry_lint.py <REPO_ROOT>
Exit：0 全對稱；1 任一不對稱（內部↔內部邊）。
"""
from __future__ import annotations

import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# SDLC 角色本體（框架固定的 6 核心角色，跨版穩定，非 per-version 細節）。
# 把 collaboration_rules 的 ``agent_type`` 字串與 agent.id 前綴都正規化到同一 key，
# 不在此表者（如 Stakeholders/Business）視為外部來源，不參與內部對稱判定。
_ROLE_ALIASES = {
    "ba": "BA",
    "ba-business-analyst": "BA",
    "pm/po": "PM/PO",
    "pm-po": "PM/PO",
    "po": "PM/PO",
    "pm": "PM/PO",
    "sa": "SA",
    "sa-analyst": "SA",
    "sd": "SD",
    "sd-architect": "SD",
    "dev": "Dev",
    "dev-developer": "Dev",
    "developer": "Dev",
    "qa": "QA",
    "qa-tester": "QA",
}

# 模板示例檔（非真實 agent，僅結構範例）排除。
_TEMPLATE_PREFIXES = ("01.agent-template",)


def _normalize(raw: str | None) -> str | None:
    """把 agent_type / agent.id 正規化到核心角色 key；非核心角色（外部）→ None。"""
    if not raw:
        return None
    return _ROLE_ALIASES.get(raw.strip().lower())


def _self_role(doc: dict, filename: str) -> str | None:
    """以 agent.id 判該檔自身角色；缺失則 fallback 檔名（NN.<role>...）。"""
    agent = doc.get("agent") if isinstance(doc, dict) else None
    if isinstance(agent, dict):
        role = _normalize(agent.get("id"))
        if role:
            return role
    # fallback：檔名 NN.<token>... 取 token 第一段
    base = os.path.basename(filename)
    token = base.split(".", 1)[-1].split("-", 1)[0]
    return _normalize(token)


def _edge_targets(rules: dict, key: str) -> list[str | None]:
    """取 collaboration_rules[key] 各項的 agent_type（正規化）。非 dict/list → []。"""
    items = rules.get(key) if isinstance(rules, dict) else None
    if not isinstance(items, list):
        return []
    out: list[str | None] = []
    for it in items:
        if isinstance(it, dict):
            out.append(_normalize(it.get("agent_type")))
    return out


def build_graph(version_path: str) -> tuple[dict, list[str]]:
    """讀 agent/core/*.yaml（排除 template）→ 回 (graph, 解析到的角色清單)。

    graph[role] = {"down": set, "up": set, "peer": set}（皆已正規化、去外部 None）。
    """
    graph: dict[str, dict[str, set[str]]] = {}
    roles_seen: list[str] = []
    files = sorted(glob.glob(os.path.join(version_path, "agent", "core", "*.yaml")))
    for fp in files:
        base = os.path.basename(fp)
        if any(base.startswith(p) for p in _TEMPLATE_PREFIXES):
            continue
        with open(fp, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            continue
        me = _self_role(doc, fp)
        if me is None:
            continue
        rules = doc.get("collaboration_rules") or {}
        node = graph.setdefault(me, {"down": set(), "up": set(), "peer": set()})
        for t in _edge_targets(rules, "downstream_collaboration"):
            if t:
                node["down"].add(t)
        for t in _edge_targets(rules, "upstream_collaboration"):
            if t:
                node["up"].add(t)
        for t in _edge_targets(rules, "peer_collaboration"):
            if t and t != me:  # 自環 peer~self 不要求對側
                node["peer"].add(t)
        roles_seen.append(me)
    return graph, roles_seen


def find_asymmetries(graph: dict) -> list[str]:
    """回所有不對稱邊的人類可讀描述（只判「內部↔內部」邊）。"""
    problems: list[str] = []
    internal = set(graph.keys())
    for x, node in sorted(graph.items()):
        # downstream X→Y 必有 Y upstream←X（僅當 Y 為內部 agent）
        for y in sorted(node["down"]):
            if y in internal and x not in graph[y]["up"]:
                problems.append(
                    f"downstream {x}→{y} 但 {y} 的 upstream 未列 {x}（漏對側 upstream←{x}）"
                )
        # peer X~Y 必有 Y peer~X（僅當 Y 為內部 agent）
        for y in sorted(node["peer"]):
            if y in internal and x not in graph[y]["peer"]:
                problems.append(
                    f"peer {x}~{y} 但 {y} 的 peer 未列 {x}（peer 應雙向，漏對側 peer~{x}）"
                )
        # upstream X←Y（X 把 Y 列為上游）必有 Y 在某方向承認 X：Y downstream→X（Y 把 X
        # 列為下游 handoff）或 Y peer~X（平級協作）。二者皆無＝Y 完全不提 X＝真實斷鏈。
        # （DEF-AGTREV-014：補 upstream 反向盲區。刻意接受 down 或 peer 為合法對側——
        #  upstream vs peer 的視角差〔如 SD←PM/PO upstream 對 PM/PO~SD peer〕屬可接受的
        #  協作視角不對稱，非斷鏈，不強制統一階層以免連鎖改寫。）
        for y in sorted(node["up"]):
            if y in internal and x not in graph[y]["down"] and x not in graph[y]["peer"]:
                problems.append(
                    f"upstream {x}←{y} 但 {y} 既未 downstream→{x} 亦未 peer~{x}"
                    f"（{y} 完全不承認 {x}，漏對側 downstream→{x} 或 peer~{x}）"
                )
    return problems


def find_missing_collaboration_rules(version_path: str) -> list[str]:
    """DEF-AGTREV-006：persona-schema agent（具 ``persona:`` 區塊）必須有非空
    ``collaboration_rules:``。runtime agent（``sdd-*``，runtime-schema 無 persona）豁免。

    緣由：4 個 specialized persona agent（qa-mobile/qa-web-tester、sd-mobile/sd-web-architect）
    長期缺 collaboration_rules，與其餘 10 個 persona 同儕不一致（v0.18 重審揭露）；core
    symmetry 只掃 core 故漏。此 presence 檢查機械防復發。
    """
    problems: list[str] = []
    files = sorted(glob.glob(os.path.join(version_path, "agent", "core", "*.yaml")) +
                   glob.glob(os.path.join(version_path, "agent", "specialized", "*.yaml")))
    for fp in files:
        base = os.path.basename(fp)
        if any(base.startswith(p) for p in _TEMPLATE_PREFIXES):
            continue
        with open(fp, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            continue
        if not doc.get("persona"):  # runtime-schema agent 無 persona → 豁免
            continue
        if not doc.get("collaboration_rules"):
            problems.append(f"{base} 具 persona 區塊但缺 collaboration_rules（persona-schema 必填）")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    latest = latest_version(discover_frozen_versions(repo_root))
    if latest is None:
        print("::error:: 找不到任何 AISDLC_SDD_v0.* 版本目錄")
        return 1
    version_path = os.path.join(repo_root, latest)
    graph, roles = build_graph(version_path)
    problems = find_asymmetries(graph)
    missing = find_missing_collaboration_rules(version_path)
    if not problems and not missing:
        print(
            f"✅ collaboration 對稱性 lint：{latest} 全部 downstream/upstream/peer 對稱"
            f"（核心角色：{', '.join(sorted(graph.keys()))}）；persona-schema agent 皆具 collaboration_rules"
        )
        return 0
    print(f"::error:: collaboration 對稱性 lint 失敗（{latest}），偵測 "
          f"{len(problems)} 條不對稱 + {len(missing)} 條缺 collaboration_rules：")
    for p in problems:
        print(f"  ASYMMETRY  {p}")
    for m in missing:
        print(f"  MISSING-RULES  {m}")
    print("  修法：additive 補對側 upstream/peer 宣告或 collaboration_rules 區塊（鏡像既有語意，勿刪既有邊）。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
