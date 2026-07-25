"""Phase L M-L2 / ACT-091 — Counterfactual Replay Engine（離線反事實實驗）.

對應藍圖：SDD_improving_Automation_12.md §1.3 / §3.1 ACT-091 / Rule 9.24.4。

L9 完整的「活體 canary/shadow 實驗」受 OPEN-10.6（本地唯讀 / 無 HTTP）約束暫不可行；
本引擎以框架**自身的歷史軌跡**作為「現實代理」做離線反事實重放——把「生成-評估分離」
從 code（Phase J）、spec 詮釋（Phase K）再往上游推到**規格假設層**：

  - 生成 = `spec_patch_proposer` 草擬的 AC diff（PatchProposal）
  - 現實判官 = 歷史失敗語料（knowledge/failure-patterns FPL、chaos 場景、PBS-DRIFT、
    decision_trace 的 escalation）

對每筆歷史失敗反事實判定「此補丁若早存在，能否改變該失敗的結局」，輸出
「擋住 X/Y 筆 + 反例清單」當證據，附在 SPEC_PATCH_PROPOSAL 上送人工 approve/reject。

設計（rule-based v1，零 LLM 成本，守 G~K 慣例）：
- 純函式核心 `replay(patch, cases)` 對傳入清單運算（deterministic、可重現、零外網）。
- 相關性 = 同 AC 或同語意指紋；命中 = 補丁的約束 token 覆蓋失敗成因 token。
- **有界**：重放筆數 clamp `SDD_REPLAY_MAX_CASES`[5,200]，預設 50。
- **advisory**：命中率僅為證據，不自動 approve/改寫補丁（Rule 9.24.4）。
- 相關語料為 0 → verdict=inconclusive（不臆測，導 HUMAN_PENDING，守 Rule 8）。
"""
from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

import yaml

from .file_lock import file_lock
from .pattern_matcher import is_same_pattern, normalize
from .state_loader import _sanitize_component

_ROOT = Path(__file__).resolve().parents[2]
REPLAY_REPORT_DIR = _ROOT / "build" / "reports" / "replay"
EXPERIMENT_PATTERNS_DIR = _ROOT / "knowledge" / "experiment-patterns"
CRYSTALLIZE_MIN_OCCURRENCES = 3
_EXP_ID_RE = re.compile(r"EXP-(\d+)\.yaml$")

_DEFAULT_REPLAY_MAX = 50
_REPLAY_MAX_CLAMP = (5, 200)
# 補丁約束 token 覆蓋失敗成因 token 的最低比例（覆蓋 ≥ 此值視為「擋得住」）。
_DEFAULT_COVER_THRESHOLD = 0.5


def replay_max() -> int:
    """讀 SDD_REPLAY_MAX_CASES（env 可調），clamp[5,200]，預設 50。"""
    raw = os.environ.get("SDD_REPLAY_MAX_CASES")
    if not raw:
        return _DEFAULT_REPLAY_MAX
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_REPLAY_MAX
    lo, hi = _REPLAY_MAX_CLAMP
    return max(lo, min(hi, val))


def _tokens(text: str) -> Set[str]:
    return set(normalize(text).split())


@dataclass
class PatchProposal:
    """spec_patch_proposer 草擬的補丁（生成半邊）。"""
    ac_id: str
    fingerprint: str = ""
    # 補丁新增的約束描述（normalize 後即為「約束 token」）
    guard_text: str = ""

    def guard_tokens(self) -> Set[str]:
        return _tokens(self.guard_text)


@dataclass
class HistoricalCase:
    """一筆歷史失敗（現實判官半邊）。來源：FPL / chaos / PBS-DRIFT / decision_trace。"""
    case_id: str
    ac_id: str = ""
    fingerprint: str = ""
    failure_text: str = ""
    source: str = ""          # fpl | chaos | pbs_drift | decision_trace

    def failure_tokens(self) -> Set[str]:
        return _tokens(self.failure_text)


@dataclass
class ReplayReport:
    verdict: str                         # "done" | "inconclusive"
    relevant_total: int = 0
    prevented: int = 0
    prevented_ratio: float = 0.0
    prevented_ids: List[str] = field(default_factory=list)
    counterexample_ids: List[str] = field(default_factory=list)
    out_of_scope_ids: List[str] = field(default_factory=list)
    examined: int = 0
    report_path: Optional[str] = None

    def evidence_line(self) -> str:
        """一行人類可讀證據（附在 SPEC_PATCH_PROPOSAL / steersman）。"""
        if self.verdict == "inconclusive":
            return "反事實重放：歷史語料不足（0 相關案例），無法判定命中率 → 導人工裁決"
        cex = f"，反例 {len(self.counterexample_ids)} 筆" if self.counterexample_ids else ""
        return (f"反事實重放：此補丁可擋住過去 {self.prevented}/{self.relevant_total} "
                f"筆同源歷史失敗（{self.prevented_ratio:.0%}）{cex}")


def _is_relevant(patch: PatchProposal, case: HistoricalCase) -> bool:
    if patch.ac_id and case.ac_id and patch.ac_id == case.ac_id:
        return True
    if patch.fingerprint and case.fingerprint and patch.fingerprint == case.fingerprint:
        return True
    return False


def _prevents(patch: PatchProposal, case: HistoricalCase,
              cover_threshold: float) -> bool:
    """補丁是否擋得住此（相關）案例：約束 token 覆蓋失敗成因 token ≥ 門檻。"""
    fail = case.failure_tokens()
    if not fail:
        return False
    guard = patch.guard_tokens()
    if not guard:
        return False
    coverage = len(guard & fail) / len(fail)
    return coverage >= cover_threshold


def replay(patch: PatchProposal, cases: List[HistoricalCase], *,
           cover_threshold: float = _DEFAULT_COVER_THRESHOLD,
           max_cases: Optional[int] = None) -> ReplayReport:
    """對歷史失敗語料反事實重放此補丁。純函式、deterministic。

    - 相關案例（同 AC / 同指紋）才計入命中率分母；不相關案例列為 out_of_scope。
    - 相關案例數為 0 → verdict=inconclusive（不臆測）。
    - 重放筆數 clamp max_cases（預設讀 SDD_REPLAY_MAX_CASES）。相關案例優先納入。
    """
    cap = max_cases if max_cases is not None else replay_max()
    # 相關案例優先排序後 cap（確保有限預算下先看相關的）
    ordered = sorted(cases, key=lambda c: 0 if _is_relevant(patch, c) else 1)
    examined = ordered[:cap]

    prevented_ids: List[str] = []
    counterexample_ids: List[str] = []
    out_of_scope_ids: List[str] = []
    for c in examined:
        if not _is_relevant(patch, c):
            out_of_scope_ids.append(c.case_id)
            continue
        if _prevents(patch, c, cover_threshold):
            prevented_ids.append(c.case_id)
        else:
            counterexample_ids.append(c.case_id)

    relevant_total = len(prevented_ids) + len(counterexample_ids)
    if relevant_total == 0:
        return ReplayReport(
            verdict="inconclusive", relevant_total=0, examined=len(examined),
            out_of_scope_ids=out_of_scope_ids,
        )
    ratio = round(len(prevented_ids) / relevant_total, 4)
    return ReplayReport(
        verdict="done",
        relevant_total=relevant_total,
        prevented=len(prevented_ids),
        prevented_ratio=ratio,
        prevented_ids=prevented_ids,
        counterexample_ids=counterexample_ids,
        out_of_scope_ids=out_of_scope_ids,
        examined=len(examined),
    )


def write_report(patch: PatchProposal, report: ReplayReport, *,
                 out_dir: Optional[Path] = None, today: Optional[str] = None) -> Path:
    """落盤 build/reports/replay/REPLAY-{date}.md（AI 可推理格式，守智慧體可讀性）。"""
    target_dir = out_dir or REPLAY_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    safe_ac_id = _sanitize_component(patch.ac_id) if patch.ac_id else "unknown"
    path = target_dir / f"REPLAY-{safe_ac_id}-{date}.md"
    lines = [
        f"# 反事實重放報告 — {patch.ac_id} — {date}",
        "",
        f"- verdict：{report.verdict}",
        f"- 相關歷史案例：{report.relevant_total}（檢視 {report.examined} 筆，out-of-scope {len(report.out_of_scope_ids)}）",
        f"- 擋住：{report.prevented}（{report.prevented_ratio:.0%}）",
        f"- 反例（擋不住的相關案例）：{len(report.counterexample_ids)}",
        "",
        f"> {report.evidence_line()}",
        "",
        "## 擋住的歷史失敗",
        "",
    ]
    lines += [f"- {cid}" for cid in report.prevented_ids] or ["（無）"]
    lines += ["", "## 反例（補丁擋不住，須人工注意）", ""]
    lines += [f"- {cid}" for cid in report.counterexample_ids] or ["（無）"]
    lines += ["", "> advisory：命中率僅為證據，**不自動 approve 補丁**；最終由 HUMAN_PENDING 人工裁決（Rule 9.24.4）。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _next_exp_id(out_dir: Path) -> str:
    """掃描既有 EXP-*.yaml 取下一編號（遞增不覆寫）。"""
    nums = [0]
    if out_dir.exists():
        for p in out_dir.glob("EXP-*.yaml"):
            m = _EXP_ID_RE.search(p.name)
            if m:
                nums.append(int(m.group(1)))
    return f"EXP-{max(nums) + 1:03d}"


def crystallize_patterns(
    records: List[Tuple[PatchProposal, ReplayReport]],
    *,
    min_occurrences: int = CRYSTALLIZE_MIN_OCCURRENCES,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
    write: bool = True,
) -> List[Path]:
    """§2.1 承諾：≥ min_occurrences 次同型「補丁→歷史命中」→ 結晶 proposed EXP-*.yaml。

    對稱 intent_decomposer.crystallize_patterns / spl_consolidator：以 patch 約束 token
    （normalize(guard_text)）做同型聚類（pattern_matcher.is_same_pattern），達門檻才提案；
    file_lock 保護、遞增不覆寫。**強制 maturity=proposed，禁自動 verified**（Rule 9.24 治理）。
    """
    done = [(p, r) for (p, r) in records if r.verdict == "done"]
    clusters: List[List[Tuple[PatchProposal, ReplayReport]]] = []
    for rec in done:
        sig = normalize(rec[0].guard_text)
        placed = False
        for cl in clusters:
            if is_same_pattern(normalize(cl[0][0].guard_text), sig):
                cl.append(rec)
                placed = True
                break
        if not placed:
            clusters.append([rec])

    target = out_dir or EXPERIMENT_PATTERNS_DIR
    written: List[Path] = []
    eligible = [cl for cl in clusters if len(cl) >= min_occurrences]
    if not eligible or not write:
        return written

    target.mkdir(parents=True, exist_ok=True)
    lock = target / ".exp-id.lock"
    with file_lock(lock):
        for cl in eligible:
            exp_id = _next_exp_id(target)
            path = target / f"{exp_id}.yaml"
            head_patch, head_rep = cl[0]
            avg_ratio = round(sum(r.prevented_ratio for _, r in cl) / len(cl), 4)
            doc = {
                "id": exp_id,
                "patch_guard_signature": normalize(head_patch.guard_text),
                "guard_sample": head_patch.guard_text,
                "occurrences": len(cl),
                "avg_prevented_ratio": avg_ratio,
                "provenance": {
                    "source": "counterfactual_replay (ACT-091)",
                    "source_acs": [p.ac_id for p, _ in cl if p.ac_id],
                    "crystallized_at": (today or _dt.datetime.now(_dt.timezone.utc)
                                        .isoformat(timespec="seconds")),
                },
                "maturity": "proposed",     # 強制 proposed（禁自動 verified）
            }
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
            tmp.replace(path)
            written.append(path)
    return written
