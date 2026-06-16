"""Phase J / ACT-073 — Adversarial Test Synthesizer（對抗判官 / GAN discriminator 半邊）.

補 L6 缺口 PJ-1：既有 output_quality_scorer 是被動 oracle，從不主動「攻擊」生成碼。
本模組是 GAN 缺失的 discriminator 對抗半邊：對已通過 EXECUTION_EVALUATION 的程式，
主動合成 4 類攻擊去找反例：
  - property_based：從 AC 抽取可檢性質（單調/冪等/非負/邊界），生成違反輸入
  - metamorphic：輸入變換關係（f(2x) vs 2·f(x)、排序不變性）
  - fuzz：型別感知邊界 fuzz（空集合/極值/NaN/Unicode）
  - mutation_guided：對程式做語意保持變異，檢測 oracle 是否真能抓 bug（弱 oracle 偵測）

verdict（對應 ADVERSARIAL_EVALUATION 閘出口，Rule 9.22.1）：
  - robust         → PR_REVIEW（N 輪攻擊無破）
  - counterexample → IMPLEMENTATION（程式違反「已宣告」性質 / 崩潰 → runtime 缺陷）
  - spec_gap       → SPEC_AUDIT（程式滿足所有宣告 AC，卻違反隱含 latent 關係 → AC 漏寫）

v1 rule-based（零 LLM 成本、確定性、可 chaos 驗證；per OPEN-J.1 RESOLVED）。
強度權重凍結於 ADVERSARIAL_PROFILE_VERSION（變更須 bump，Rule 9.22.2 — 判官不自我放水）。
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Tuple

ATTACK_TYPES = ("property_based", "metamorphic", "fuzz", "mutation_guided")
ADVERSARIAL_PROFILE_VERSION = "v1.0"

# Rule 9.22.1 — 攻擊輪數硬上限（env 可調，clamp [1,16]）
_DEFAULT_ROUNDS = 8
_ROUNDS_MIN, _ROUNDS_MAX = 1, 16
# 去隨機共識輪數（沿用 Phase I evaluate_hermetic 精神）
FLAKY_RERUN_N = 5

DOMAINS = ("int", "list_int", "str")

# 凍結的確定性樣本集（profile 一部分；變更須 bump PROFILE_VERSION）
_INT_SAMPLES: Tuple[int, ...] = (0, 1, 2, 3, 5, 10, -1, -5, 100, 1000)
_LIST_SAMPLES: Tuple[Tuple[int, ...], ...] = (
    (), (1,), (3, 1, 2), (5, 5, 5), (-1, 0, 1), (9, 8, 7, 6), (2, 2, 1),
)
_STR_SAMPLES: Tuple[str, ...] = ("", "a", "abc", "ABC", "  ", "你好", "a" * 64, "1\n2")

# 已知可檢性質（property_based 用）
KNOWN_PROPERTIES = (
    "non_negative", "monotonic_increasing", "idempotent",
    "deterministic", "bounded", "order_invariant", "length_preserving",
)
# 隱含 metamorphic 關係（latent，不需宣告即探測）
KNOWN_LATENT = ("scaling", "order_invariant", "length_preserving")


def adversarial_rounds() -> int:
    """Rule 9.22.1：攻擊輪數（env SDD_ADVERSARIAL_ROUNDS，clamp [1,16]）。"""
    raw = os.environ.get("SDD_ADVERSARIAL_ROUNDS")
    if raw is None:
        return _DEFAULT_ROUNDS
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_ROUNDS
    return max(_ROUNDS_MIN, min(_ROUNDS_MAX, v))


@dataclass
class Target:
    """受測程式抽象。declared = AC 明確宣告的性質；latent = AC 隱含但未明寫的關係。"""
    fn: Callable[[Any], Any]
    domain: str = "int"
    declared_properties: Tuple[str, ...] = ()
    latent_relations: Tuple[str, ...] = ()


@dataclass
class AdversarialResult:
    verdict: str                       # robust | counterexample | spec_gap | inconclusive
    rounds_run: int
    attacks_run: int
    counterexamples: List[dict] = field(default_factory=list)
    spec_gaps: List[dict] = field(default_factory=list)
    profile_version: str = ADVERSARIAL_PROFILE_VERSION
    flaky: bool = False

    @property
    def robust(self) -> bool:
        return self.verdict == "robust"


def _samples_for(domain: str) -> Sequence[Any]:
    if domain == "int":
        return _INT_SAMPLES
    if domain == "list_int":
        return [list(t) for t in _LIST_SAMPLES]
    if domain == "str":
        return _STR_SAMPLES
    return _INT_SAMPLES


def _safe_call(fn: Callable[[Any], Any], x: Any) -> Tuple[bool, Any]:
    """回傳 (ok, value_or_exc)。crash 視為 ok=False。"""
    try:
        return True, fn(x)
    except Exception as exc:  # noqa: BLE001 — fuzz/property 攻擊本就期待可能 crash
        return False, repr(exc)


# ---------------------------------------------------------------------------
# Property checkers — 回傳 violation dict 或 None
# ---------------------------------------------------------------------------

def _check_property(fn: Callable, domain: str, prop: str) -> Optional[dict]:
    samples = _samples_for(domain)
    if prop == "non_negative":
        for x in samples:
            ok, v = _safe_call(fn, x)
            if not ok:
                return {"property": prop, "input": x, "detail": f"crash: {v}"}
            if isinstance(v, (int, float)) and v < 0:
                return {"property": prop, "input": x, "detail": f"fn={v} < 0"}
    elif prop == "deterministic":
        for x in samples:
            ok1, v1 = _safe_call(fn, x)
            ok2, v2 = _safe_call(fn, x)
            if (ok1, v1) != (ok2, v2):
                return {"property": prop, "input": x, "detail": f"{v1!r} != {v2!r}"}
    elif prop == "idempotent":
        for x in samples:
            ok1, v1 = _safe_call(fn, x)
            if not ok1:
                return {"property": prop, "input": x, "detail": f"crash: {v1}"}
            ok2, v2 = _safe_call(fn, v1)
            if not ok2 or v2 != v1:
                return {"property": prop, "input": x, "detail": f"f(f(x))={v2!r} != f(x)={v1!r}"}
    elif prop == "monotonic_increasing" and domain == "int":
        ordered = sorted(_INT_SAMPLES)
        prev_x = prev_v = None
        for x in ordered:
            ok, v = _safe_call(fn, x)
            if not ok:
                return {"property": prop, "input": x, "detail": f"crash: {v}"}
            if prev_v is not None and isinstance(v, (int, float)) and v < prev_v:
                return {"property": prop, "input": x,
                        "detail": f"f({x})={v} < f({prev_x})={prev_v}"}
            prev_x, prev_v = x, v
    elif prop == "bounded":
        for x in samples:
            ok, v = _safe_call(fn, x)
            if not ok:
                return {"property": prop, "input": x, "detail": f"crash: {v}"}
            if isinstance(v, (int, float)) and (math.isnan(v) or abs(v) > 1e12):
                return {"property": prop, "input": x, "detail": f"unbounded fn={v}"}
    elif prop == "order_invariant" and domain == "list_int":
        for x in (s for s in samples if s):
            ok1, v1 = _safe_call(fn, list(x))
            ok2, v2 = _safe_call(fn, list(reversed(x)))
            if not ok1 or not ok2:
                return {"property": prop, "input": x, "detail": "crash on permutation"}
            if v1 != v2:
                return {"property": prop, "input": x,
                        "detail": f"f({x})={v1!r} != f(reversed)={v2!r}"}
    elif prop == "length_preserving" and domain == "list_int":
        for x in samples:
            ok, v = _safe_call(fn, list(x))
            if not ok:
                return {"property": prop, "input": x, "detail": f"crash: {v}"}
            if not hasattr(v, "__len__") or len(v) != len(x):
                return {"property": prop, "input": x,
                        "detail": f"len(fn)={getattr(v, '__len__', lambda: '?')()} != {len(x)}"}
    return None


def _check_latent(fn: Callable, domain: str, relation: str) -> Optional[dict]:
    """探測隱含 metamorphic 關係（即使未宣告）。違反 → spec_gap 候選。"""
    if relation == "scaling" and domain == "int":
        for x in (1, 2, 3, 5, 10):
            ok1, v1 = _safe_call(fn, x)
            ok2, v2 = _safe_call(fn, 2 * x)
            if not ok1 or not ok2:
                return {"relation": relation, "input": x, "detail": "crash during metamorphic probe"}
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and v2 != 2 * v1:
                return {"relation": relation, "input": x,
                        "detail": f"f(2·{x})={v2} != 2·f({x})={2 * v1}"}
    elif relation == "order_invariant" and domain == "list_int":
        for x in (s for s in (_check_latent_lists()) if s):
            ok1, v1 = _safe_call(fn, list(x))
            ok2, v2 = _safe_call(fn, list(reversed(x)))
            if ok1 and ok2 and v1 != v2:
                return {"relation": relation, "input": x,
                        "detail": f"order-sensitive: {v1!r} != {v2!r}"}
    elif relation == "length_preserving" and domain == "list_int":
        for x in _check_latent_lists():
            ok, v = _safe_call(fn, list(x))
            if ok and hasattr(v, "__len__") and len(v) != len(x):
                return {"relation": relation, "input": x,
                        "detail": f"len changed {len(x)}→{len(v)}"}
    return None


def _check_latent_lists():
    return [list(t) for t in _LIST_SAMPLES]


def _fuzz(fn: Callable, domain: str) -> Optional[dict]:
    """型別感知邊界 fuzz：找 crash。"""
    if domain == "int":
        probes = [0, -(2 ** 63), 2 ** 63, -1]
    elif domain == "list_int":
        probes = [[], [0] * 256, [-(2 ** 40)], [2 ** 40]]
    else:
        probes = ["", "\x00", "𝕏" * 8, "a" * 4096, "\n\r\t"]
    for p in probes:
        ok, v = _safe_call(fn, p)
        if not ok:
            return {"attack_type": "fuzz", "input": p, "detail": f"crash: {v}"}
    return None


def _mutation_guided(target: Target) -> Optional[dict]:
    """弱 oracle 偵測：若程式對宣告性質「恆真」（連明顯反例都過），表示其行為
    可能與 oracle 脫節。v1 啟發式：若 fn 對所有樣本回傳常數，視為退化 oracle 風險。"""
    if not target.declared_properties:
        return None
    samples = _samples_for(target.domain)
    outs = []
    for x in samples:
        ok, v = _safe_call(target.fn, x)
        outs.append(v if ok else "<crash>")
    distinct = {repr(o) for o in outs}
    if len(distinct) == 1 and len(samples) > 2:
        return {"attack_type": "mutation_guided", "input": "<corpus>",
                "detail": f"degenerate constant output {next(iter(distinct))} — oracle 可能無效"}
    return None


def _run_once(target: Target) -> Tuple[List[dict], List[dict], int]:
    """跑一輪完整攻擊套件，回傳 (counterexamples, spec_gaps, attacks_run)。"""
    counters: List[dict] = []
    gaps: List[dict] = []
    attacks = 0

    # property_based：違反「已宣告」性質 → counterexample（runtime 缺陷）
    for prop in target.declared_properties:
        attacks += 1
        viol = _check_property(target.fn, target.domain, prop)
        if viol:
            viol["attack_type"] = "property_based"
            counters.append(viol)

    # fuzz：crash → counterexample
    attacks += 1
    fz = _fuzz(target.fn, target.domain)
    if fz:
        counters.append(fz)

    # mutation_guided：弱 oracle → counterexample（測試抓不到 bug）
    attacks += 1
    mg = _mutation_guided(target)
    if mg:
        counters.append(mg)

    # metamorphic latent：違反「未宣告」隱含關係 → spec_gap（AC 漏寫）
    for rel in target.latent_relations:
        attacks += 1
        lat = _check_latent(target.fn, target.domain, rel)
        if lat:
            # 若該關係已被宣告為 property，則違反屬 counterexample 而非 spec_gap
            if rel in target.declared_properties:
                lat["attack_type"] = "metamorphic"
                counters.append(lat)
            else:
                lat["attack_type"] = "metamorphic"
                gaps.append(lat)
    return counters, gaps, attacks


def _resolve(counters: List[dict], gaps: List[dict], rounds: int, attacks: int,
             *, flaky: bool = False) -> AdversarialResult:
    if flaky:
        return AdversarialResult("inconclusive", rounds, attacks,
                                 counterexamples=counters, spec_gaps=gaps, flaky=True)
    if counters:
        return AdversarialResult("counterexample", rounds, attacks,
                                 counterexamples=counters, spec_gaps=gaps)
    if gaps:
        return AdversarialResult("spec_gap", rounds, attacks,
                                 counterexamples=counters, spec_gaps=gaps)
    return AdversarialResult("robust", rounds, attacks)


def evaluate_target(
    target: Target,
    *,
    rounds: Optional[int] = None,
    hermetic_rerun: int = FLAKY_RERUN_N,
) -> AdversarialResult:
    """對 target 跑對抗評估，回傳 verdict。

    Rule 9.22.1：攻擊有界（rounds ≤ adversarial_rounds()）；去隨機 — 同套件
    重跑 hermetic_rerun 次取共識，verdict 不穩定（混合）→ inconclusive（flaky，
    隔離、不計分、不進 retry）。確定性程式必穩定。
    """
    n = rounds if rounds is not None else adversarial_rounds()
    n = max(_ROUNDS_MIN, min(_ROUNDS_MAX, n))

    verdicts: List[str] = []
    last_counters: List[dict] = []
    last_gaps: List[dict] = []
    total_attacks = 0
    for _ in range(max(1, hermetic_rerun)):
        counters: List[dict] = []
        gaps: List[dict] = []
        attacks = 0
        for _r in range(n):
            c, g, a = _run_once(target)
            attacks += a
            counters.extend(c)
            gaps.extend(g)
            if c or g:
                break  # 找到反例即停（有界，省輪數）
        res = _resolve(counters, gaps, n, attacks)
        verdicts.append(res.verdict)
        last_counters, last_gaps, total_attacks = counters, gaps, attacks

    if len(set(verdicts)) > 1:
        # 混合共識 → FLAKY，隔離
        return _resolve(last_counters, last_gaps, n, total_attacks, flaky=True)
    return _resolve(last_counters, last_gaps, n, total_attacks)


__all__ = [
    "ATTACK_TYPES", "ADVERSARIAL_PROFILE_VERSION", "FLAKY_RERUN_N",
    "adversarial_rounds", "Target", "AdversarialResult", "evaluate_target",
]
