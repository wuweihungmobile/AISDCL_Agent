"""Phase K M-K1 / ACT-081 — Intent Decomposer（意圖→規格 DAG 自主分解）.

補上 Planner 宏觀半邊：value_planner（ACT-068）只對「人工給定」的候選排 ROI；
本模組把一句 high-level intent 自主分解為 **acyclic spec-DAG**（候選 AC/FRD 節點 +
依賴邊），輸出 build/state/spec-dag-{date}.yaml 並餵給 value_planner.rank_candidates。

rule-based v1（零 LLM 成本，守 G/H/I/J 慣例；OPEN-K.2 採預設，LLM 留 v2）。
- 有界（Rule 9.23.1）：節點數 clamp SDD_INTENT_MAX_NODES[4,128] 預設 32；
  spec-DAG 必 acyclic（偵測環即 underspecified）；無可分解項 / 觸頂 → underspecified。
- 不自我裁決（Rule 9.23.2）：只產候選，最高 ROI 仍經 BACKLOG_PRIORITIZED 人工 signoff。

依賴標註語法（rule-based 可確定性解析）：需求列尾用 `[dep:1,3]`（1-based 引用其他需求列）。
自然語言依賴推斷屬 v2（LLM）範疇，v1 僅解析顯式標註，確保確定性可測。

intent-patterns 知識庫（對稱 SPL/ADV/FPL）：
- 啟動時 lazy 載入 knowledge/intent-patterns/INT-*.yaml 骨架（若有）作為分解提示，
  decompose 命中骨架時於 DAG 標註 skeleton_ref（advisory，不改節點，保確定性）。
- 結晶（Rule 9.23.2 治理）：≥3 次同型分解 → 結晶 proposed INT-*.yaml（禁自動 verified，
  比照 SPL/ADV，須人工 review 升級），file_lock 保護並行寫、遞增不覆寫。
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from tools.fsm_runtime.file_lock import file_lock
from tools.fsm_runtime.pattern_matcher import is_same_pattern

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_NODES = 32
MIN_MAX_NODES = 4
MAX_MAX_NODES = 128

INTENT_PATTERNS_DIR = FRAMEWORK_ROOT / "knowledge" / "intent-patterns"
CRYSTALLIZE_MIN_OCCURRENCES = 3        # 同型分解 ≥ N 次才結晶（防偶發誤結晶）
_INT_ID_RE = re.compile(r"^INT-(\d+)\.yaml$")

_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$")
_DEP_RE = re.compile(r"\[dep:\s*([0-9,\s]+)\]", re.IGNORECASE)


def clamp_max_nodes(n: int) -> int:
    return max(MIN_MAX_NODES, min(int(n), MAX_MAX_NODES))


def _resolve_max_nodes(max_nodes: int | None) -> int:
    if max_nodes is None:
        max_nodes = int(os.environ.get("SDD_INTENT_MAX_NODES", DEFAULT_MAX_NODES))
    return clamp_max_nodes(max_nodes)


@dataclass
class IntentNode:
    node_id: str
    title: str
    depends_on: List[str] = field(default_factory=list)


@dataclass
class SpecDAG:
    intent_ref: str
    nodes: List[IntentNode]
    status: str            # "decomposed" | "underspecified"
    reason: str = ""
    max_nodes: int = DEFAULT_MAX_NODES
    skeleton_ref: str = ""  # 命中的 INT-* 骨架（advisory，不改節點）

    def node_ids(self) -> List[str]:
        return [n.node_id for n in self.nodes]

    def signature(self) -> str:
        """分解「型」指紋：節點標題排序後串接（供同型聚類 / 骨架命中）。"""
        return " | ".join(sorted(n.title for n in self.nodes))

    def edges(self) -> List[Tuple[str, str]]:
        return [(n.node_id, dep) for n in self.nodes for dep in n.depends_on]

    def is_acyclic(self) -> bool:
        try:
            self.topological_order()
            return True
        except ValueError:
            return False

    def topological_order(self) -> List[str]:
        """Kahn's algorithm；偵測到環 raise ValueError。"""
        ids = self.node_ids()
        indeg = {nid: 0 for nid in ids}
        adj: dict[str, list[str]] = {nid: [] for nid in ids}
        for n in self.nodes:
            for dep in n.depends_on:
                if dep in indeg:           # edge dep -> n（dep 必先於 n）
                    adj[dep].append(n.node_id)
                    indeg[n.node_id] += 1
        queue = [nid for nid in ids if indeg[nid] == 0]
        order: List[str] = []
        while queue:
            cur = queue.pop(0)
            order.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(ids):
            raise ValueError("dependency cycle detected in spec-DAG")
        return order

    def to_candidates(self):
        """轉為 value_planner.BacklogCandidate（餵 rank_candidates；不自裁決）。"""
        from tools.fsm_runtime.value_planner import BacklogCandidate
        return [BacklogCandidate(candidate_id=n.node_id, title=n.title, cold_start=True)
                for n in self.nodes]


def _parse_items(text: str) -> List[Tuple[str, List[int]]]:
    """抽出需求列：回傳 [(title, [dep_idx(1-based)...]), ...]。"""
    items: List[Tuple[str, List[int]]] = []
    for line in text.splitlines():
        m = _ITEM_RE.match(line)
        if not m:
            continue
        raw = m.group(1)
        deps: List[int] = []
        dm = _DEP_RE.search(raw)
        if dm:
            deps = [int(x) for x in re.findall(r"\d+", dm.group(1))]
            raw = _DEP_RE.sub("", raw).strip()
        items.append((raw, deps))
    return items


def load_intent_skeletons(src_dir: Path | None = None) -> List[Dict]:
    """lazy 載入 knowledge/intent-patterns/INT-*.yaml 骨架（缺檔/壞檔不報錯，回空清單）。

    對稱 SPL/ADV 的狀態感知 lazy load（INTENT_DECOMPOSITION 狀態），不汙染 eager 地圖。
    """
    target = src_dir or INTENT_PATTERNS_DIR
    out: List[Dict] = []
    if not target.exists():
        return out
    for p in sorted(target.glob("INT-*.yaml")):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("id"):
            out.append(doc)
    return out


def _match_skeleton(dag: SpecDAG, skeletons: List[Dict]) -> str:
    """以分解 signature 對骨架 signature 同型比對，回傳命中的 INT-* id（advisory）。"""
    sig = dag.signature()
    for sk in skeletons:
        sk_sig = sk.get("signature", "")
        if sk_sig and is_same_pattern(sig, sk_sig):
            return str(sk.get("id", ""))
    return ""


def decompose(intent_text: str, *, max_nodes: int | None = None,
              intent_ref: str = "", skeletons: List[Dict] | None = None) -> SpecDAG:
    """rule-based 分解 high-level intent → SpecDAG（有界 + acyclic 守門）。

    skeletons：可選的 INT-* 骨架清單（命中則標 skeleton_ref，advisory 不改節點，保確定性）。
    """
    bound = _resolve_max_nodes(max_nodes)
    items = _parse_items(intent_text)

    if not items:
        return SpecDAG(intent_ref, [], "underspecified",
                       "no decomposable requirement items (intent too vague)", bound)
    if len(items) > bound:
        return SpecDAG(intent_ref, [], "underspecified",
                       f"item count {len(items)} exceeds bound {bound} (cannot bound)", bound)

    count = len(items)
    nodes: List[IntentNode] = []
    for idx, (title, deps) in enumerate(items, start=1):
        # 僅保留 in-range 引用；self/out-of-range 處理見下（self 保留以利偵環）
        dep_ids = [f"N{d}" for d in deps if 1 <= d <= count]
        nodes.append(IntentNode(node_id=f"N{idx}", title=title, depends_on=dep_ids))

    dag = SpecDAG(intent_ref, nodes, "decomposed", "", bound)
    if not dag.is_acyclic():
        dag.status = "underspecified"
        dag.reason = "dependency cycle detected (needs human ordering)"
        return dag
    if skeletons:
        dag.skeleton_ref = _match_skeleton(dag, skeletons)
    return dag


def _next_int_id(out_dir: Path) -> str:
    """掃描既有 INT-*.yaml 取下一編號（遞增不覆寫）。"""
    nums = [0]
    if out_dir.exists():
        for p in out_dir.glob("INT-*.yaml"):
            m = _INT_ID_RE.match(p.name)
            if m:
                nums.append(int(m.group(1)))
    return f"INT-{max(nums) + 1:03d}"


def crystallize_patterns(
    dags: List[SpecDAG],
    *,
    min_occurrences: int = CRYSTALLIZE_MIN_OCCURRENCES,
    out_dir: Path | None = None,
    today: str | None = None,
    write: bool = True,
) -> List[Path]:
    """≥ min_occurrences 次同型分解 → 結晶 proposed INT-*.yaml（禁自動 verified）.

    對稱 spl_consolidator：同型聚類（pattern_matcher.is_same_pattern over signature），
    達門檻才提案；file_lock 保護、遞增不覆寫。advisory（Rule 9.23.2 治理）。
    """
    decomposed = [d for d in dags if d.status == "decomposed" and d.nodes]
    clusters: List[List[SpecDAG]] = []
    for d in decomposed:
        placed = False
        for cl in clusters:
            if is_same_pattern(cl[0].signature(), d.signature()):
                cl.append(d)
                placed = True
                break
        if not placed:
            clusters.append([d])

    target = out_dir or INTENT_PATTERNS_DIR
    written: List[Path] = []
    eligible = [cl for cl in clusters if len(cl) >= min_occurrences]
    if not eligible or not write:
        return written

    target.mkdir(parents=True, exist_ok=True)
    lock = target / ".int-id.lock"
    with file_lock(lock):
        for cl in eligible:
            int_id = _next_int_id(target)
            path = target / f"{int_id}.yaml"
            head = cl[0]
            doc = {
                "id": int_id,
                "intent_type": head.signature(),
                "skeleton": [{"title": n.title, "depends_on": n.depends_on}
                             for n in head.nodes],
                "occurrences": len(cl),
                "provenance": {
                    "source": "intent_decomposer (ACT-081)",
                    "source_intents": [d.intent_ref for d in cl if d.intent_ref],
                    "crystallized_at": (today or _dt.datetime.now(_dt.timezone.utc)
                                        .isoformat(timespec="seconds")),
                },
                "signature": head.signature(),
                "maturity": "proposed",     # 強制 proposed（禁自動 verified）
            }
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
            tmp.replace(path)
            written.append(path)
    return written


def write_spec_dag(dag: SpecDAG, *, out_dir: Path | None = None,
                   today: str | None = None) -> Path:
    """落盤 build/state/spec-dag-{date}.yaml（不常駐 context，守漸進式揭露）。"""
    out_dir = out_dir or (FRAMEWORK_ROOT / "build" / "state")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = today or _dt.date.today().isoformat()
    path = out_dir / f"spec-dag-{today}.yaml"
    payload = {
        "intent_ref": dag.intent_ref,
        "status": dag.status,
        "reason": dag.reason,
        "max_nodes": dag.max_nodes,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "nodes": [{"node_id": n.node_id, "title": n.title, "depends_on": n.depends_on}
                  for n in dag.nodes],
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
    return path


def annotate_fragile(dag: SpecDAG, fragile_terms) -> List[str]:
    """Phase L M-L3 / ACT-094：分解時標記落在歷史脆弱領域的 DAG 節點（advisory）。

    委派 spec_fragility_scorer.fragile_node_ids 對 {node_id → title} 做領域關鍵詞比對；
    回傳脆弱 node_id 清單。**不改 DAG acyclic 結構、不阻塞分解**——僅供舵手凍結前注意
    （Rule 9.24.5）。`fragile_terms` 由 caller 從 PBS-DRIFT / 脆弱 AC 描述提供。
    """
    from tools.fsm_runtime.spec_fragility_scorer import fragile_node_ids
    return fragile_node_ids({n.node_id: n.title for n in dag.nodes}, set(fragile_terms))


def main(argv: List[str]) -> int:
    if len(argv) < 3 or argv[1] != "decompose":
        print("用法：python -m tools.fsm_runtime.intent_decomposer decompose <intent_file>")
        return 2
    text = Path(argv[2]).read_text(encoding="utf-8")
    dag = decompose(text, intent_ref=argv[2])
    path = write_spec_dag(dag)
    print(f"status={dag.status} nodes={len(dag.nodes)} bound={dag.max_nodes}")
    if dag.reason:
        print(f"reason={dag.reason}")
    print(f"spec-dag → {path}")
    return 0 if dag.status == "decomposed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
