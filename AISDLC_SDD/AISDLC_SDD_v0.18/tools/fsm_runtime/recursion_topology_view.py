"""Phase Y / ACT-160 — Recursion Topology View（meta⁸ 互遞迴呼叫圖人類視覺化）.

對應藍圖：build/planning/active/SDD_improving_Automation_26.md §A/§C；Rule 9.37 / formal/META_FSM.tla
VisualizationBounded。

GAP-Y1 解：Phase L~X 把元迴圈自我演化推到 meta⁸ + 具身接地，但其全部停機證書（良基 ranking
function、fuel、grounded-verdict）一路 machine-readable / machine-verified、**從未 human-auditable**
——當被人類 K=1 signoff 的是一張帶 rank 的互遞迴呼叫圖時，舵手事實上只能盲簽。本模組把
`RecursiveOperator.to_dict()` 的抽象算子代數 + rank/fuel，**有界、可稽核地**投影成人類看得懂的
拓樸 / 終止 / 接地三視圖（PY-1 AST 同構投影）。

紅線（Rule 9.37）：
  · PY-1 AST 同構：本模組是 `to_dict()` 序列化 dict 的**確定性純投影**，不獨立再推導拓樸。
  · PY-2 拓樸防偽：`verify_topology_consistency` 反解析渲染回 (nodes,edges,ranks)，獨立從 op_dict
    重算同一窗格子圖比對——任一不吻合（視覺欺騙：畫的圖比跑的簡單/偽 rank/刪邊）→ fail-closed。
  · PY-3 有界渲染：render budget（node/edge/depth/char）硬截斷 + 分頁；輸入再大（10⁶）也只讀窗格
    切片 → O(node_budget) 輸出，不卡死 / 不 OOM / 不超 token 預算。
  · 接地不 false-green：無客觀 ExecutionObservation / inconclusive → 灰佔位，絕不渲染綠勾。
  · 對抗分離：結構性**不 import** 任何 generator（operator_*_genesis / dimension_semantics_
    synthesizer / vocabulary_genesis）/ dimension_necessity_oracle / embodied_grounding_oracle。

純函式、deterministic、零 LLM、零外網、零 FSM-STATE 寫入、零 churn（read-only 純觀察者）。
"""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Sequence, Tuple

# render budget 預設 + clamp（緊語意 = VisualizationBounded runtime enforce）。
_DEFAULT_NODE_BUDGET = 24
_NODE_BUDGET_CLAMP = (4, 256)
_DEFAULT_EDGE_BUDGET = 48
_EDGE_BUDGET_CLAMP = (4, 512)
_DEFAULT_DEPTH_MAX = 8
_DEFAULT_CHAR_BUDGET = 8000
_CHAR_BUDGET_CLAMP = (1000, 65536)
# W-23-1 Folding 降維（_26.md §A.4.2 列入、§D 收官以 pagination 替代而未交付之子項）：
# 把窗內「結構無趣的線性鏈」塌縮為單一 [+k more] 超節點，降人類認知超載。預設 OFF＝v0.13
# 逐位元行為（零退化）；ON 時仍守 PY-3 有界 + PY-2 拓樸防偽（fold-aware 誠實收縮，見 verify）。
_DEFAULT_FOLD_MIN = 3          # 折疊內部鏈最短長度（>= 此長度才塌縮，避免瑣碎折疊）
_FOLD_MIN_CLAMP = (2, 64)


def _env_truthy(raw: Optional[str]) -> bool:
    return str(raw).strip().lower() in ("1", "true", "yes", "on") if raw else False


def _clamp_int(raw: Optional[str], default: int, clamp: Tuple[int, int]) -> int:
    if not raw:
        return default
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return default
    lo, hi = clamp
    return max(lo, min(hi, val))


@dataclass(frozen=True)
class RenderBudget:
    """渲染有界預算（PY-3 bulletproof 渲染 / VisualizationBounded 緊語意）。"""
    node_budget: int = _DEFAULT_NODE_BUDGET
    edge_budget: int = _DEFAULT_EDGE_BUDGET
    depth_max: int = _DEFAULT_DEPTH_MAX
    char_budget: int = _DEFAULT_CHAR_BUDGET
    fold_enabled: bool = False                 # W-23-1：預設 OFF＝v0.13 行為（零退化）
    fold_min: int = _DEFAULT_FOLD_MIN          # 折疊內部鏈最短長度


def render_budget() -> RenderBudget:
    """讀 SDD_VIZ_* env（皆 clamp，有預設）構造 RenderBudget。"""
    return RenderBudget(
        node_budget=_clamp_int(os.environ.get("SDD_VIZ_NODE_BUDGET"),
                               _DEFAULT_NODE_BUDGET, _NODE_BUDGET_CLAMP),
        edge_budget=_clamp_int(os.environ.get("SDD_VIZ_EDGE_BUDGET"),
                               _DEFAULT_EDGE_BUDGET, _EDGE_BUDGET_CLAMP),
        depth_max=_clamp_int(os.environ.get("SDD_VIZ_DEPTH_MAX"),
                             _DEFAULT_DEPTH_MAX, (2, 32)),
        char_budget=_clamp_int(os.environ.get("SDD_VIZ_CHAR_BUDGET"),
                               _DEFAULT_CHAR_BUDGET, _CHAR_BUDGET_CLAMP),
        fold_enabled=_env_truthy(os.environ.get("SDD_VIZ_FOLD")),
        fold_min=_clamp_int(os.environ.get("SDD_VIZ_FOLD_MIN"),
                            _DEFAULT_FOLD_MIN, _FOLD_MIN_CLAMP),
    )


@dataclass(frozen=True)
class TopoNode:
    """拓樸節點（投影自 RecursiveOperator.to_dict() 的 ranks/edges + base）。"""
    id: int
    base: str
    rank: int
    fuel_consumed: int        # 工作單元 = 1（base 求值）+ 折疊的窗內 callee 數
    calls: Tuple[int, ...]    # 窗內可見 callee（cross-page callee 折疊隱藏）
    visited: bool             # 是否在 fuel 預算內被求值（否 → 計數器歸零強制打斷）
    critical: bool = False    # 是否為窗內 max-fuel 算子（🔴）
    entry: bool = False       # i == to_dict()["entry"]
    folded: bool = False      # W-23-1：是否為折疊超節點（鏈塌縮）
    folds: Tuple[int, ...] = ()  # 被收縮的成員 id（鏈序；空＝非超節點）


@dataclass(frozen=True)
class TopoEdge:
    """拓樸邊（投影自 to_dict()["edges"]；rank_decrement = rank[src]-rank[dst]）。"""
    src: int
    dst: int
    rank_decrement: int       # > 0 ⇒ 良基（嚴格遞減）
    kind: str                 # "forward" | "back-candidate"
    well_founded: bool        # rank[dst] < rank[src]


@dataclass(frozen=True)
class CriticalPath:
    max_fuel_node: int        # 窗內消耗最多 fuel 的算子 id（-1 = 無）
    fuel_at_node: int
    longest_chain: Tuple[int, ...]
    break_point: str          # 迴圈如何被計數器（fuel/rank）強制打斷的人類說明


@dataclass(frozen=True)
class GroundingView:
    """接地視圖（投影自 embodied_grounding_oracle.GroundedVerdict 及其 .observation；零觀測 fail-closed）。"""
    has_observation: bool
    grounded_verdict: str                 # grounded_pass/grounded_fail/spec_defect/inconclusive/none
    oqs: Optional[float]
    baseline_oqs: Optional[float]
    runtime_errors: Optional[int]
    nonzero_exit: Optional[bool]
    sandbox_timed_out: bool
    note: str = ""


@dataclass(frozen=True)
class TopologyView:
    """有界、可分頁、可稽核的拓樸投影（三視圖共用單一來源；PY-1 AST 同構）。"""
    operator_fingerprint: str
    operator_name: str
    budget: RenderBudget
    n_total_nodes: int
    fuel: int
    truncated: bool
    page_cursor: int
    total_pages: int
    terminating: bool
    acyclic: bool
    well_founded: bool
    termination_reason: str
    nodes: Tuple[TopoNode, ...]
    edges: Tuple[TopoEdge, ...]
    critical_path: CriticalPath
    grounding: GroundingView
    audit_digest: str = ""


# ---------------------------------------------------------------------------
# duck 讀取（grounding 可為 dict 或 GroundedVerdict 物件，皆唯讀）
# ---------------------------------------------------------------------------

def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _short_base(name: str, *, limit: int = 18) -> str:
    s = str(name)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# 良基求值序（鏡像 operator_recursion_genesis._eval_order：rank 升序，tie 索引序）
# ---------------------------------------------------------------------------

def _eval_order(ranks: Sequence[int]) -> List[int]:
    return sorted(range(len(ranks)), key=lambda i: (int(ranks[i]), i))


def _canonical_graph(node_ids: Sequence[int],
                     rank_of: Mapping[int, int],
                     edges_within: Sequence[Tuple[int, int]]) -> str:
    """子圖 (nodes, ranks, edges) 的正規化指紋（排序去重 → sha256）。供 PY-2 防偽稽核。"""
    nodes_sorted = sorted(int(i) for i in node_ids)
    ranks_sorted = sorted((int(i), int(rank_of[i])) for i in node_ids)
    edges_sorted = sorted((int(u), int(w)) for (u, w) in edges_within)
    blob = repr((nodes_sorted, ranks_sorted, edges_sorted))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PY-1 + PY-3：從 to_dict() 抽取有界拓樸（只讀窗格切片，輸入再大也 O(node_budget)）
# ---------------------------------------------------------------------------

def extract_topology(
    op_dict: Mapping[str, Any],
    *,
    grounding: Optional[Any] = None,
    budget: Optional[RenderBudget] = None,
    page_cursor: int = 0,
) -> TopologyView:
    """從 RecursiveOperator.to_dict() 抽取**有界**拓樸特徵（PY-1 AST 同構 + PY-3 有界）.

    · 不假設輸入來自有界文法（防禦縱深：對抗者可餵 10⁶ 節點圖）→ 一律套 budget 截斷 + 分頁；
      只讀窗格切片 [start, end)，故輸入再大輸出仍 O(node_budget)、不卡死不 OOM。
    · 每窗內節點計 fuel_consumed（= 1 base + 窗內折疊 callee 數）+ critical path（max-fuel 算子）
      + 每邊 rank_decrement；break_point 說明迴圈如何在計數器（fuel/rank）歸零被強制打斷。
    · grounding 為 None / inconclusive / 無 observation → GroundingView fail-closed 灰佔位（不 false-green）。
    · audit_digest = 窗格正規化圖指紋，供 verify_topology_consistency 反向稽核。
    """
    b = budget if budget is not None else render_budget()
    ranks_all = list(op_dict.get("ranks") or [])
    edges_all = op_dict.get("edges") or []        # [[i, [callees]], ...]
    n_total = len(ranks_all)
    fuel = int(op_dict.get("fuel") or op_dict.get("cost") or n_total or 0)
    entry = int(op_dict.get("entry") or 0)
    fingerprint = str(op_dict.get("fingerprint") or "")
    op_name = str(op_dict.get("name") or "")
    terminating = bool(op_dict.get("terminating", False))
    acyclic = bool(op_dict.get("acyclic", False))
    well_founded = bool(op_dict.get("well_founded", False))

    # to_dict()["edges"] → 全域 calls 對照（只在窗格內展開，避免遍歷 10⁶）。
    calls_by_id = {}
    for pair in edges_all:
        try:
            i = int(pair[0])
            cs = tuple(int(c) for c in (pair[1] or ()))
        except (TypeError, ValueError, IndexError):
            continue
        calls_by_id[i] = cs

    nb = max(1, b.node_budget)
    total_pages = max(1, math.ceil(n_total / nb)) if n_total else 1
    page = max(0, min(int(page_cursor), total_pages - 1))
    start = page * nb
    end = min(start + nb, n_total)
    window_ids = list(range(start, end))
    window_set = set(window_ids)
    truncated = n_total > nb

    rank_of = {i: int(ranks_all[i]) for i in window_ids}

    # 窗內邊（cross-page callee 折疊隱藏；edge_budget 截斷）。
    edges_within: List[Tuple[int, int]] = []
    for i in window_ids:
        for w in calls_by_id.get(i, ()):  # 全域 callee
            if w in window_set:
                edges_within.append((i, w))
    edges_within = edges_within[: b.edge_budget]

    # 良基求值序（窗內）：rank 升序。fuel 歸零（步數 >= fuel）後的節點 = 未訪問（強制打斷）。
    order = _eval_order([rank_of[i] for i in window_ids])  # local positions
    visited_local = set()
    for pos, local_idx in enumerate(order):
        if pos >= fuel:
            break
        visited_local.add(window_ids[local_idx])

    # 每節點 fuel_consumed = 1（base）+ 窗內折疊 callee 數（fan hub 自然最高）。
    within_callee_count = {i: 0 for i in window_ids}
    for (u, _w) in edges_within:
        within_callee_count[u] += 1

    nodes: List[TopoNode] = []
    max_fuel = -1
    max_fuel_node = -1
    for i in window_ids:
        fc = (1 + within_callee_count[i]) if i in visited_local else 0
        node = TopoNode(
            id=i,
            base=_short_base(_base_name_for(i, op_dict)),
            rank=rank_of[i],
            fuel_consumed=fc,
            calls=tuple(w for (u, w) in edges_within if u == i),
            visited=(i in visited_local),
            entry=(i == entry and i in window_set),
        )
        nodes.append(node)
        if fc > max_fuel:
            max_fuel = fc
            max_fuel_node = i

    # critical 標記（窗內 max-fuel 算子）。
    nodes = tuple(  # type: ignore[assignment]
        TopoNode(id=n.id, base=n.base, rank=n.rank, fuel_consumed=n.fuel_consumed,
                 calls=n.calls, visited=n.visited, critical=(n.id == max_fuel_node and max_fuel > 0),
                 entry=n.entry)
        for n in nodes
    )

    edges: List[TopoEdge] = []
    for (u, w) in edges_within:
        dec = rank_of[u] - rank_of[w]
        edges.append(TopoEdge(src=u, dst=w, rank_decrement=dec,
                              kind=("forward" if w > u else "back-candidate"),
                              well_founded=(dec > 0)))

    # break_point：fuel 歸零強制打斷 vs rank→0 自然終止。
    n_unvisited = sum(1 for i in window_ids if i not in visited_local)
    if n_total > fuel and n_unvisited > 0:
        break_point = (f"⛔ fuel={fuel} 耗盡，窗內 {n_unvisited} 節點未訪問"
                       f"（良基測度計數器歸零 → 迴圈被強制打斷，不無限跑）")
    elif window_ids:
        last = order[-1] if order else 0
        sink_id = window_ids[last]
        break_point = (f"rank→{rank_of.get(sink_id, 0)} sink @ node{sink_id}"
                       f"（良基測度嚴格遞減至下界 → 自然終止）")
    else:
        break_point = "（空呼叫圖）"

    critical = CriticalPath(
        max_fuel_node=max_fuel_node,
        fuel_at_node=max(0, max_fuel),
        longest_chain=tuple(window_ids[i] for i in order),
        break_point=break_point,
    )

    gview = _build_grounding_view(grounding)

    audit = _canonical_graph(window_ids, rank_of, edges_within)

    view = TopologyView(
        operator_fingerprint=fingerprint,
        operator_name=op_name,
        budget=b,
        n_total_nodes=n_total,
        fuel=fuel,
        truncated=truncated,
        page_cursor=page,
        total_pages=total_pages,
        terminating=terminating,
        acyclic=acyclic,
        well_founded=well_founded,
        termination_reason=str(op_dict.get("termination_reason") or ""),
        nodes=tuple(nodes),
        edges=tuple(edges),
        critical_path=critical,
        grounding=gview,
        audit_digest=audit,
    )
    # W-23-1：fold_enabled 時把窗內結構無趣的線性鏈塌縮（誠實收縮，可被 PY-2 反解析稽核）。
    if b.fold_enabled:
        view = fold_topology(view)
    return view


# ---------------------------------------------------------------------------
# W-23-1 Folding 降維（純函式轉換：把窗內極大「內部簡單鏈」塌縮為單一 [+k more] 超節點）
# ---------------------------------------------------------------------------

def _window_degrees(node_ids, edges):
    """窗內 in/out degree（僅計兩端皆在窗內之邊）。"""
    indeg = {i: 0 for i in node_ids}
    outdeg = {i: 0 for i in node_ids}
    succ = {i: [] for i in node_ids}
    pred = {i: [] for i in node_ids}
    for e in edges:
        if e.src in outdeg and e.dst in indeg:
            outdeg[e.src] += 1
            indeg[e.dst] += 1
            succ[e.src].append(e.dst)
            pred[e.dst].append(e.src)
    return indeg, outdeg, succ, pred


def _is_kept(n, indeg, outdeg):
    """kept-node＝結構要角，永不被折疊：entry / critical(max-fuel) / fuel 歸零未訪問 /
    分支(out!=1) / 匯聚(in!=1) / source(in=0) / sink(out=0)。"""
    return (n.entry or n.critical or (not n.visited)
            or indeg.get(n.id, 0) != 1 or outdeg.get(n.id, 0) != 1)


def fold_topology(view: "TopologyView") -> "TopologyView":
    """把窗內極大內部簡單鏈（連續 in==1∧out==1∧非 kept-node）塌縮為單一折疊超節點.

    · 超節點公開 `folds=[成員 id]`（鏈序）→ PY-2 verify_topology_consistency 可反解析稽核為
      「可驗證無損的分組」（誠實收縮，非視覺欺騙：畫的圖以商圖忠實表達真圖，nothing dropped）。
    · 永不折疊 entry / critical / 分支 / 匯聚 / sink / 未訪問節點（結構要角恆可見）。
    · 鏈長 < budget.fold_min 不折疊（避免瑣碎折疊）。無合格鏈 → 原 view 原樣返回。
    · 純函式、deterministic、零 while（鏈走訪以有界 for + 已訪集），零自呼叫。
    """
    node_by_id = {n.id: n for n in view.nodes}
    node_ids = list(node_by_id.keys())
    indeg, outdeg, succ, pred = _window_degrees(node_ids, view.edges)
    fold_min = max(2, int(view.budget.fold_min))

    # 掃描鏈首（非 kept、其唯一前驅為 kept 或不在窗內）→ 沿唯一 succ 走到撞 kept。
    member_of = {}                       # member id → super (chain head) id
    chains = []                          # [[m0, m1, ...], ...]
    for i in node_ids:
        n = node_by_id[i]
        if _is_kept(n, indeg, outdeg) or i in member_of:
            continue
        p = pred.get(i, [])
        head_pred = p[0] if p else None
        pred_is_chainable = (head_pred is not None and head_pred in node_by_id
                             and not _is_kept(node_by_id[head_pred], indeg, outdeg))
        if pred_is_chainable:
            continue                     # 非鏈首（前驅也是可折疊鏈節點）
        chain, cur, seen = [], i, set()
        for _ in range(len(node_ids)):   # 有界 for（最多窗內節點數），代替 while
            if cur is None or cur in seen or cur not in node_by_id:
                break
            cn = node_by_id[cur]
            if _is_kept(cn, indeg, outdeg):
                break
            chain.append(cur)
            seen.add(cur)
            nxt = succ.get(cur, [])
            cur = nxt[0] if nxt else None
        if len(chain) >= fold_min:
            chains.append(chain)
            for m in chain:
                member_of[m] = chain[0]

    if not chains:
        return view                      # 無合格鏈 → 零行為改變

    # 重建 nodes：kept 與非鏈成員原樣保留；每條鏈 → 一個錨定鏈首的折疊超節點。
    folded_ids = set(member_of.keys())
    new_nodes = [n for n in view.nodes if n.id not in folded_ids]
    rank_of = {n.id: n.rank for n in view.nodes}
    for chain in chains:
        head, tail = chain[0], chain[-1]
        tail_succ = succ.get(tail, [])
        exit_dst = tail_succ[0] if tail_succ else None
        new_nodes.append(TopoNode(
            id=head,
            base=f"[+{len(chain)} more]",
            rank=rank_of[head],
            fuel_consumed=sum(node_by_id[m].fuel_consumed for m in chain),
            calls=tuple(d for d in (exit_dst,) if d is not None),
            visited=True,
            critical=False,
            entry=False,
            folded=True,
            folds=tuple(chain),
        ))
    new_nodes.sort(key=lambda n: n.id)

    # 重建 edges：以「render group」（成員→鏈首；其餘→自身）對真圖窗內邊取商圖（去自環、去重）。
    def grp(x):
        return member_of.get(x, x)
    quotient = set()
    for e in view.edges:
        gu, gv = grp(e.src), grp(e.dst)
        if gu != gv:
            quotient.add((gu, gv))
    new_edges = []
    for (u, w) in sorted(quotient):
        dec = rank_of[u] - rank_of[w]
        new_edges.append(TopoEdge(src=u, dst=w, rank_decrement=dec,
                                  kind=("forward" if w > u else "back-candidate"),
                                  well_founded=(dec > 0)))

    from dataclasses import replace
    return replace(view, nodes=tuple(new_nodes), edges=tuple(new_edges))


def _base_name_for(i: int, op_dict: Mapping[str, Any]) -> str:
    """取節點 i 的 base 短名。to_dict() 未逐節點吐 base 名 → 退回 node 索引標籤（不杜撰拓樸）。"""
    bases = op_dict.get("node_bases")
    if isinstance(bases, (list, tuple)) and 0 <= i < len(bases):
        return str(bases[i])
    return f"op[{i}]"


def _obs_has_signal(obs: Optional[Any]) -> bool:
    """ExecutionObservation 是否含實質客觀訊號（鏡像 output_quality_scorer.has_observation；空 dict / 全零 → False）.

    杜絕「observation 為非 None 空 dict 卻判 has_observation」的零觀測 false-green（防禦縱深）。
    """
    if obs is None:
        return False
    try:
        tt = int(_g(obs, "tests_total", 0) or 0)
        re_ = int(_g(obs, "runtime_errors", 0) or 0)
        ua = int(_g(obs, "ui_assertions_total", 0) or 0)
        pc = int(_g(obs, "perf_checks", 0) or 0)
    except (TypeError, ValueError):
        return False
    nz = bool(_g(obs, "nonzero_exit", False))
    return tt > 0 or re_ > 0 or ua > 0 or pc > 0 or nz


def _build_grounding_view(grounding: Optional[Any]) -> GroundingView:
    """接地視圖 fail-closed 構造：無客觀觀測 / inconclusive → 灰佔位，絕不 false-green。"""
    if grounding is None:
        return GroundingView(
            has_observation=False, grounded_verdict="none",
            oqs=None, baseline_oqs=None, runtime_errors=None, nonzero_exit=None,
            sandbox_timed_out=False,
            note="⚠️ 無具身接地紀錄（沙箱未實跑）→ fail-closed 灰佔位，不 false-green")
    verdict = str(_g(grounding, "grounded_verdict", "none"))
    obs = _g(grounding, "observation", None)
    runtime_errors = _g(obs, "runtime_errors", None) if obs is not None else None
    nonzero_exit = _g(obs, "nonzero_exit", None) if obs is not None else None
    sandbox_timed_out = bool(_g(grounding, "sandbox_timed_out", False))
    # 客觀觀測判據（fail-closed 強化，鏡像 output_quality_scorer.has_observation）：須有**含實質訊號**的
    # observation（非 None 且非空 dict——零訊號 obs 等同沙箱從未真正跑過/壞過 → 視為無觀測）且 verdict 非
    # inconclusive/none。杜絕「observation={}（空 dict 非 None）+ grounded_pass」的 false-green。
    has_obs = _obs_has_signal(obs) and verdict not in ("inconclusive", "none", "")
    note = ""
    if not has_obs:
        note = "⚠️ 無客觀 ExecutionObservation / inconclusive → fail-closed 灰佔位，不 false-green"
    return GroundingView(
        has_observation=has_obs,
        grounded_verdict=verdict,
        oqs=_as_float(_g(grounding, "oqs", None)) if has_obs else None,
        baseline_oqs=_as_float(_g(grounding, "baseline_oqs", None)) if has_obs else None,
        runtime_errors=runtime_errors,
        nonzero_exit=nonzero_exit,
        sandbox_timed_out=sandbox_timed_out,
        note=note,
    )


def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 三視圖渲染（皆有界：節點 <= node_budget、邊 <= edge_budget → 輸出結構性 <= char_budget）
# ---------------------------------------------------------------------------

def render_mermaid(view: TopologyView) -> str:
    """① 拓樸視圖：Mermaid flowchart，critical path 高亮 + 每邊 Δrank 標註 + fuel 歸零 ⛔。有界。"""
    lines = ["```mermaid", "flowchart TD",
             "    classDef crit fill:#ffd6d6,stroke:#c0392b,stroke-width:3px;",
             "    classDef sink fill:#d6f5d6,stroke:#27ae60;",
             "    classDef cut fill:#eeeeee,stroke:#888888,stroke-dasharray:4 3;",
             "    classDef fold fill:#fff3cd,stroke:#b8860b,stroke-dasharray:6 3;"]
    for n in view.nodes:
        if n.folded:                       # W-23-1：折疊超節點（虛線群組樣式 + 收縮計數）
            label = f"{n.base} · r={n.rank}↓ · Σfuel={n.fuel_consumed}"
            lines.append(f'    n{n.id}[["{label}"]]')
            continue
        label = f"{n.base} · r={n.rank} · fuel={n.fuel_consumed}"
        if n.critical:
            label += " 🔴max-fuel"
        if not n.visited:
            label += " ⛔未訪問(fuel歸零)"
        if n.entry:
            lines.append(f'    n{n.id}((("{label}")))')
        else:
            lines.append(f'    n{n.id}["{label}"]')
    for e in view.edges:
        mark = "✅良基" if e.well_founded else "❌無證書(可能環)"
        lines.append(f'    n{e.src} -->|"Δrank={-e.rank_decrement} {mark}"| n{e.dst}')
    for n in view.nodes:
        if n.folded:
            lines.append(f"    class n{n.id} fold;")
        elif n.critical:
            lines.append(f"    class n{n.id} crit;")
        elif not n.visited:
            lines.append(f"    class n{n.id} cut;")
        elif not n.calls:
            lines.append(f"    class n{n.id} sink;")
    trunc = (f" | ⚠️truncated page {view.page_cursor + 1}/{view.total_pages}"
             f"（顯示 {len(view.nodes)}/{view.n_total_nodes} 節點）" if view.truncated else "")
    lines.append(f"    %% nodes {len(view.nodes)}/{view.budget.node_budget} | "
                 f"edges {len(view.edges)}/{view.budget.edge_budget}{trunc}")
    lines.append("```")
    return "\n".join(lines)


def render_termination_ladder(view: TopologyView) -> str:
    """② 終止視圖：rank 格 / fuel 階梯 Markdown，良基測度嚴格遞減的視覺證明。"""
    cert = ("✅ 可證良基終止（呼叫圖帶良基 ranking function：每呼叫邊嚴格遞減下有界 rank）"
            if view.terminating else "❌ 良基停機證書失敗（無 ranking function → 可能含環不停機）")
    lines = [
        f"**良基停機證書**：{cert}",
        f"- 整圖狀態：terminating={view.terminating} · acyclic={view.acyclic} · "
        f"well_founded={view.well_founded} · fuel={view.fuel} · 節點數={view.n_total_nodes}",
        "",
        "fuel 階梯（rank 由高到低，計數器歸零 = 強制打斷迴圈）",
        "```",
    ]
    for n in sorted(view.nodes, key=lambda x: (-x.rank, x.id)):
        bar = "▣" * max(0, n.fuel_consumed) or "·"
        flag = "" if n.visited else "  ⛔未訪問(fuel歸零)"
        lines.append(f" node{n.id:<3} {bar:<6} rank={n.rank}{flag}")
    lines += ["```", f"- 終止判讀：{view.critical_path.break_point}"]
    return "\n".join(lines)


def render_grounding_panel(view: TopologyView) -> str:
    """③ 接地視圖：沙箱 OQS Markdown；零觀測灰佔位不綠勾（fail-closed）。"""
    g = view.grounding
    if not g.has_observation:
        return ("**具身接地視圖**：⬜ 灰佔位 — " + (g.note or "無客觀觀測") +
                "（嚴格不 false-green）")
    icon = "🟢" if g.grounded_verdict == "grounded_pass" else (
        "🟠" if g.grounded_verdict in ("grounded_fail", "spec_defect") else "⬜")
    delta = (None if (g.oqs is None or g.baseline_oqs is None) else g.oqs - g.baseline_oqs)
    lines = [
        f"**具身接地視圖**：{icon} grounded_verdict = `{g.grounded_verdict}`"
        + ("（沙箱硬 timeout → grounded_fail）" if g.sandbox_timed_out else ""),
        "",
        "| 指標 | baseline | candidate | Δ |",
        "|------|----------|-----------|---|",
        f"| OQS | {_fmt(g.baseline_oqs)} | {_fmt(g.oqs)} | {_fmt(delta)} |",
        f"| runtime 錯誤數 | — | {g.runtime_errors if g.runtime_errors is not None else '—'} | — |",
        f"| 非零 exit | — | {g.nonzero_exit if g.nonzero_exit is not None else '—'} | — |",
    ]
    return "\n".join(lines)


def _fmt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:+.4f}" if v < 0 else f"{v:.4f}"


def render_json(view: TopologyView) -> dict:
    """機讀 JSON（schema_version=1）；與 Mermaid/Markdown 同出於同一 view，供 PY-2 反解析稽核。"""
    return {
        "schema_version": 1,
        "view": "recursion_topology",
        "operator_fingerprint": view.operator_fingerprint,
        "operator_name": view.operator_name,
        "render_budget": {
            "node_budget": view.budget.node_budget,
            "edge_budget": view.budget.edge_budget,
            "depth_max": view.budget.depth_max,
            "char_budget": view.budget.char_budget,
        },
        "n_total_nodes": view.n_total_nodes,
        "fuel": view.fuel,
        "truncated": view.truncated,
        "page": {"cursor": view.page_cursor, "total_pages": view.total_pages},
        "termination": {
            "terminating": view.terminating,
            "acyclic": view.acyclic,
            "well_founded": view.well_founded,
            "reason": view.termination_reason,
        },
        "nodes": [
            {"id": n.id, "base": n.base, "rank": n.rank, "fuel_consumed": n.fuel_consumed,
             "calls": list(n.calls), "visited": n.visited, "critical": n.critical,
             "entry": n.entry, "folded": n.folded, "folds": list(n.folds)}
            for n in view.nodes
        ],
        "edges": [
            {"src": e.src, "dst": e.dst, "rank_decrement": e.rank_decrement,
             "kind": e.kind, "well_founded": e.well_founded}
            for e in view.edges
        ],
        "critical_path": {
            "max_fuel_node": view.critical_path.max_fuel_node,
            "fuel_at_node": view.critical_path.fuel_at_node,
            "longest_chain": list(view.critical_path.longest_chain),
            "break_point": view.critical_path.break_point,
        },
        "grounding": {
            "has_observation": view.grounding.has_observation,
            "grounded_verdict": view.grounding.grounded_verdict,
            "oqs": view.grounding.oqs,
            "baseline_oqs": view.grounding.baseline_oqs,
            "runtime_errors": view.grounding.runtime_errors,
            "nonzero_exit": view.grounding.nonzero_exit,
            "sandbox_timed_out": view.grounding.sandbox_timed_out,
            "note": view.grounding.note,
        },
        "consistency": {"audit_digest": view.audit_digest},
    }


def render_dashboard_markdown(view: TopologyView) -> str:
    """組合三視圖為單一 Markdown（供 steersman 引用；有界）。"""
    return "\n\n".join([
        render_mermaid(view),
        render_termination_ladder(view),
        render_grounding_panel(view),
    ])


# ---------------------------------------------------------------------------
# PY-2 拓樸防偽稽核（對抗：渲染圖 ≠ 真跑圖 → fail-closed）
# ---------------------------------------------------------------------------

class TopologyConsistencyError(RuntimeError):
    """PY-2：渲染輸出反解析後與 to_dict() 原圖不同構（視覺欺騙）→ fail-closed → MFSM_ESCALATION。"""


def verify_topology_consistency(
    render_json_obj: Mapping[str, Any],
    op_dict: Mapping[str, Any],
    *,
    node_budget: Optional[int] = None,
) -> bool:
    """反解析渲染 JSON → (nodes, edges, ranks)，獨立從 op_dict + **服務端權威 budget** 重算比對（PY-2 防偽）.

    **威脅模型（QA 對抗複驗強化）**：本稽核器**完全不信任 `render_json_obj`** ——其中**所有**自報欄位
    （`render_budget`、`page`、`n_total_nodes`、`truncated`…）皆可能被攻陷的 renderer 偽造。故窗格錨定**只
    採信 op_dict（真相）+ 由 caller 注入或 env 取得的服務端權威 `node_budget`**，**絕不**採信 render_json
    自報的 budget/cursor/n_total（否則攻擊者可同步偽造三者使窗格自洽縮空，把 4 節點 fan hub 偽裝成 2 節點
    完整小圖）。

    反「畫的圖比跑的簡單」三道（同型於 guard_embodied_grounding「獨立重算、不盲信 renderer 標籤」）：
      · (a0) 真實大小誠實：op_dict 真實 n_total。若渲染自報 n_total_nodes，須 == 真實 n_total（不得謊稱算子更小）。
      · (a1) 窗格錨定（權威 budget）：n_total <= budget → **必須完整顯示全圖** range(0,n_total) 且不得謊報
             truncated；n_total > budget → **必須誠實揭露 truncated** 且顯示集恰為某個**對齊權威 budget 的連續
             窗格**（由顯示集自身 min(id)//budget 推導頁，不採信 render 的 cursor）。
      · (a2)~(c) 每節點 rank、窗內邊、正規化指紋須與 op_dict 真相完全一致（杜絕偽 rank/刪邊/加邊/杜撰節點）。

    純函式、deterministic、零 import generator/oracle。一致 → True；否則 raise TopologyConsistencyError。
    """
    nodes = render_json_obj.get("nodes") or []
    edges = render_json_obj.get("edges") or []

    # 渲染節點：分離 normal 與 W-23-1 折疊超節點（folded==True，公開 folds=[成員]）。
    normal_ids: List[int] = []
    fold_members = {}                 # super_id -> [members]（鏈序）
    depicted_rank = {}
    for nd in nodes:
        try:
            i = int(nd["id"])
        except (KeyError, TypeError, ValueError):
            raise TopologyConsistencyError("渲染節點缺合法 id（拓樸防偽 fail-closed）")
        depicted_rank[i] = int(nd.get("rank"))
        if nd.get("folded"):
            try:
                members = [int(m) for m in (nd.get("folds") or [])]
            except (TypeError, ValueError):
                raise TopologyConsistencyError(f"折疊超節點 n{i} folds 非法（拓樸防偽 fail-closed）")
            if not members:
                raise TopologyConsistencyError(f"折疊超節點 n{i} folds 為空（拓樸防偽 fail-closed）")
            if i != members[0]:
                raise TopologyConsistencyError(
                    f"折疊超節點 n{i} 未錨定鏈首 {members[0]}（拓樸防偽 fail-closed）")
            fold_members[i] = members
        else:
            normal_ids.append(i)

    # repr＝人類實際看到的節點（normal ∪ 超節點）；group_of 把成員映回超節點，其餘恆等。
    repr_ids = list(normal_ids) + list(fold_members.keys())
    repr_set = set(repr_ids)
    if len(repr_set) != len(repr_ids):
        raise TopologyConsistencyError("渲染節點 id 重複（拓樸防偽 fail-closed）")
    group_of = {nid: nid for nid in normal_ids}
    expanded_ids: List[int] = list(normal_ids)
    for sid, members in fold_members.items():
        for m in members:
            if m in group_of:
                raise TopologyConsistencyError(f"節點 {m} 重複出現（normal/多折疊，拓樸防偽 fail-closed）")
            group_of[m] = sid
            expanded_ids.append(m)
    expanded_set = set(expanded_ids)   # 全部被代表的真實窗格節點（含折疊展開）
    if len(expanded_set) != len(expanded_ids):
        raise TopologyConsistencyError("折疊展開後節點 id 重複（拓樸防偽 fail-closed）")

    # op_dict 真相：ranks 全表 + calls 對照 + entry。
    ranks_all = list(op_dict.get("ranks") or [])
    n_total = len(ranks_all)
    calls_by_id = {}
    for pair in (op_dict.get("edges") or []):
        try:
            calls_by_id[int(pair[0])] = tuple(int(c) for c in (pair[1] or ()))
        except (TypeError, ValueError, IndexError):
            continue
    entry = int(op_dict.get("entry") or 0)

    # **權威 budget（信任來源：caller 注入 / env，絕不採信 render_json 自報）**。
    nb = max(1, int(node_budget) if node_budget is not None else render_budget().node_budget)

    # (a0) **真實大小誠實**：渲染若自報 n_total_nodes，須 == op_dict 真實 n_total（不得謊稱算子更小/更簡單）。
    claimed_total = render_json_obj.get("n_total_nodes")
    if claimed_total is not None:
        try:
            if int(claimed_total) != n_total:
                raise TopologyConsistencyError(
                    f"渲染謊報 n_total_nodes={claimed_total} != op_dict 真實 {n_total}"
                    f"（畫的圖比跑的簡單，拓樸防偽 fail-closed）")
        except (TypeError, ValueError):
            raise TopologyConsistencyError("渲染 n_total_nodes 非法（拓樸防偽 fail-closed）")

    # (a1) **窗格錨定（權威 budget）**：以 expanded_set（含折疊展開的真實節點全集）對齊；折疊只分組不丟節點。
    truncated_claim = bool(render_json_obj.get("truncated", False))
    if n_total <= nb:
        if expanded_set != set(range(0, n_total)):
            raise TopologyConsistencyError(
                f"小圖（n_total={n_total} <= budget={nb}）展開後未完整涵蓋（展開 {sorted(expanded_set)[:6]}… 應為全圖 "
                f"node[0:{n_total}]）：丟節點 / 縮窗 / 空渲染 / 折疊藏節點 = 畫的圖比跑的簡單，拓樸防偽 fail-closed")
        if truncated_claim:
            raise TopologyConsistencyError(
                "小圖卻謊報 truncated（無需截斷卻宣稱截斷以隱藏節點，拓樸防偽 fail-closed）")
    else:
        if not truncated_claim:
            raise TopologyConsistencyError(
                f"大圖（n_total={n_total} > budget={nb}）卻未揭露 truncated（畫的圖比跑的簡單，拓樸防偽 fail-closed）")
        if not expanded_ids:
            raise TopologyConsistencyError("截斷圖卻空渲染（畫的圖比跑的簡單，拓樸防偽 fail-closed）")
        page_idx = min(expanded_ids) // nb
        exp_start = page_idx * nb
        exp_end = min(exp_start + nb, n_total)
        if expanded_set != set(range(exp_start, exp_end)):
            raise TopologyConsistencyError(
                f"截斷頁展開集非合法權威窗格（展開 {sorted(expanded_set)[:6]}… 應為 node[{exp_start}:{exp_end}]）："
                f"縮窗 / 丟節點 / 折疊藏節點，拓樸防偽 fail-closed")

    # (a) 每個被顯示節點（normal 與超節點皆對其 id 的真相 rank）：id 在範圍內、rank 與真相一致。
    for i in repr_ids:
        if not (0 <= i < n_total):
            raise TopologyConsistencyError(
                f"渲染顯示不存在的節點 node{i}（杜撰節點，拓樸防偽 fail-closed）")
        if depicted_rank[i] != int(ranks_all[i]):
            raise TopologyConsistencyError(
                f"node{i} rank 不符：畫={depicted_rank[i]} 真相={int(ranks_all[i])}"
                f"（偽 rank 視覺欺騙，拓樸防偽 fail-closed）")

    # 窗內真相邊（兩端皆在 expanded_set）。
    true_window_edges = set()
    for u in expanded_ids:
        for w in calls_by_id.get(u, ()):
            if w in expanded_set:
                true_window_edges.add((u, w))

    # (f1/f2/f3) 折疊合法性：每折疊群須為真實內部簡單鏈（窗內 in==1∧out==1）、rank 嚴格遞減、不藏 entry。
    if fold_members:
        win_indeg = {i: 0 for i in expanded_set}
        win_outdeg = {i: 0 for i in expanded_set}
        for (u, w) in true_window_edges:
            win_outdeg[u] += 1
            win_indeg[w] += 1
        for sid, members in fold_members.items():
            for m in members:
                if m == entry:
                    raise TopologyConsistencyError(
                        f"折疊隱藏 entry 節點 {m}（結構要角不得折疊，拓樸防偽 fail-closed）")
                if win_indeg.get(m, 0) != 1 or win_outdeg.get(m, 0) != 1:
                    raise TopologyConsistencyError(
                        f"折疊成員 {m} 非內部鏈節點（窗內 in={win_indeg.get(m, 0)}/out={win_outdeg.get(m, 0)}）："
                        f"折疊分支/匯聚/sink/source 藏結構，拓樸防偽 fail-closed")
            for a, b in zip(members, members[1:]):
                if b not in calls_by_id.get(a, ()):
                    raise TopologyConsistencyError(
                        f"折疊鏈 {a}->{b} 非真實呼叫邊（假鏈，拓樸防偽 fail-closed）")
                if not (int(ranks_all[a]) > int(ranks_all[b])):
                    raise TopologyConsistencyError(
                        f"折疊鏈 {a}->{b} rank 未嚴格遞減（良基破，拓樸防偽 fail-closed）")

    # (b) 商圖邊比對：真窗邊按 group_of 映射去自環去重 = 期望被畫的邊（折疊內部邊吸收，跨群邊保留）。
    expected_q = set()
    for (u, w) in true_window_edges:
        gu, gw = group_of[u], group_of[w]
        if gu != gw:
            expected_q.add((gu, gw))
    depicted_edges = set()
    for e in edges:
        try:
            depicted_edges.add((int(e["src"]), int(e["dst"])))
        except (KeyError, TypeError, ValueError):
            raise TopologyConsistencyError("渲染邊缺合法 src/dst（拓樸防偽 fail-closed）")
    for (u, w) in depicted_edges:
        if u not in repr_set or w not in repr_set:
            raise TopologyConsistencyError(
                f"渲染邊 {u}->{w} 端點不在顯示集（拓樸防偽 fail-closed）")
    missing = expected_q - depicted_edges
    extra = depicted_edges - expected_q
    if missing:
        raise TopologyConsistencyError(
            f"渲染漏畫窗內真相邊（商圖）{sorted(missing)}（畫的圖比跑的簡單，視覺欺騙，拓樸防偽 fail-closed）")
    if extra:
        raise TopologyConsistencyError(
            f"渲染杜撰不存在的邊（商圖）{sorted(extra)}（拓樸防偽 fail-closed）")

    # (c) 正規化指紋雙證：digest 為 extract 對「未折疊窗格」(expanded + 全窗邊) 之指紋（折疊不改 digest）。
    recomputed = _canonical_graph(
        expanded_ids, {i: int(ranks_all[i]) for i in expanded_ids}, sorted(true_window_edges))
    claimed = (render_json_obj.get("consistency") or {}).get("audit_digest")
    if claimed is not None and claimed != recomputed:
        raise TopologyConsistencyError(
            f"拓樸指紋不符：宣稱={claimed} 重算={recomputed}（拓樸防偽 fail-closed）")
    return True
