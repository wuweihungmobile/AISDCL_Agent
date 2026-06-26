"""Phase K M-K2 / ACT-083 — Spec Debate Engine（規格辯證消歧）.

把「生成-評估分離」從 Phase J 的**生成碼**推到**規格詮釋**：對 AmbiguityScorer 落
near-threshold band 的 AC，啟兩條**隔離詮釋 pass**（pro=最大/inclusive 讀法、con=最小/
exclusive 讀法，彼此 oracle-blind），以 pattern_matcher 量化分歧。divergence ≥ 門檻 →
規格歧義確認（單視角 scorer 看不到第二種互斥詮釋）。

rule-based v1（零 LLM 成本，守 G/H/I/J 慣例；OPEN-K.2 採預設）。
- 有界 + 不自我放水（Rule 9.23.3）：輪數 clamp SDD_SPEC_DEBATE_ROUNDS[1,8] 預設 4；
  辯證強度凍結 SPEC_DEBATE_PROFILE_VERSION（變更須 bump，比照 ADVERSARIAL_PROFILE_VERSION）。
- advisory（Rule 9.23.4）：divergence 不自動阻塞/改寫 AC，只導 HUMAN_PENDING 澄清。
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from tools.fsm_runtime import pattern_matcher
from tools.fsm_runtime.file_lock import file_lock

SPEC_DEBATE_PROFILE_VERSION = "v1.0"   # 凍結；調整辯證強度須 bump（Rule 9.23.3）
DEFAULT_ROUNDS = 4
MIN_ROUNDS, MAX_ROUNDS = 1, 8
DIVERGENCE_THRESHOLD = 0.5             # ≥ → 分歧確認

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
DISAMBIG_DIR = FRAMEWORK_ROOT / "knowledge" / "disambiguation"
_DIS_ID_RE = re.compile(r"^DIS-(\d+)\.yaml$")

# 雙讀標記：marker -> (pro=inclusive/強讀法, con=exclusive/弱讀法)。
# 凍結於 SPEC_DEBATE_PROFILE_VERSION；兩隔離詮釋對同一 marker 給對立讀法。
AMBIGUITY_MARKERS = {
    "可疊加": ("同時疊加套用", "互斥僅取其一"),
    "和/或": ("兩者皆需", "兩者擇一"),
    "及/或": ("兩者皆需", "兩者擇一"),
    "等等": ("窮舉全部項目", "僅為示例列舉"),
    "酌情": ("一律啟用", "一律不啟用"),
    "視情況": ("總是套用", "從不套用"),
    "必要時": ("每次皆執行", "從不執行"),
    "盡可能": ("必須完全達成", "盡力即可"),
    "若有需要": ("總是提供", "可省略"),
    "and/or": ("and", "or"),
    "optionally": ("required", "omitted"),
    "as appropriate": ("always applied", "never applied"),
    "as needed": ("always", "never"),
}


def clamp_rounds(rounds: int | None) -> int:
    if rounds is None:
        rounds = int(os.environ.get("SDD_SPEC_DEBATE_ROUNDS", DEFAULT_ROUNDS))
    return max(MIN_ROUNDS, min(int(rounds), MAX_ROUNDS))


@dataclass
class DebateResult:
    ac_id: str
    verdict: str            # "consensus" | "divergence"
    divergence: float
    markers: List[str] = field(default_factory=list)
    interp_pro: str = ""
    interp_con: str = ""
    rounds: int = DEFAULT_ROUNDS
    profile_version: str = SPEC_DEBATE_PROFILE_VERSION


def _find_markers(text: str) -> List[str]:
    return [m for m in AMBIGUITY_MARKERS if m in text]


def _interpret(text: str, lens: int) -> str:
    """隔離詮釋 pass：lens=0 取 pro(強)讀法、lens=1 取 con(弱)讀法。"""
    out = text
    for m in _find_markers(text):
        out = out.replace(m, AMBIGUITY_MARKERS[m][lens])
    return out


def debate(ac_text: str, *, ac_id: str = "", rounds: int | None = None,
           profile_version: str = SPEC_DEBATE_PROFILE_VERSION) -> DebateResult:
    """兩隔離詮釋對 AC 提出對立讀法 → 量化 divergence → consensus / divergence。"""
    r = clamp_rounds(rounds)
    markers = _find_markers(ac_text)
    interp_pro = _interpret(ac_text, 0)   # 詮釋器 A（oracle-blind）
    interp_con = _interpret(ac_text, 1)   # 詮釋器 B（oracle-blind）
    if not markers:
        divergence = 0.0
    else:
        sim = pattern_matcher.similarity(interp_pro, interp_con)
        divergence = round(min(1.0, 0.6 * len(markers) + 0.4 * (1.0 - sim)), 4)
    verdict = "divergence" if divergence >= DIVERGENCE_THRESHOLD else "consensus"
    return DebateResult(
        ac_id=ac_id, verdict=verdict, divergence=divergence, markers=markers,
        interp_pro=interp_pro, interp_con=interp_con,
        rounds=r, profile_version=profile_version,
    )


def _next_dis_id(out_dir: Path) -> str:
    """掃描既有 DIS-*.yaml 取下一個編號（acyclic 不覆寫；新歧義對取新號）。"""
    nums = [0]
    if out_dir.exists():
        for p in out_dir.glob("DIS-*.yaml"):
            m = _DIS_ID_RE.match(p.name)
            if m:
                nums.append(int(m.group(1)))
    return f"DIS-{max(nums) + 1:03d}"


def persist_disambiguation(
    ac_id: str,
    interp_a: str,
    interp_b: str,
    divergence: float,
    *,
    verdict: Optional[str] = None,
    markers: Optional[List[str]] = None,
    profile_version: str = SPEC_DEBATE_PROFILE_VERSION,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> Path:
    """落盤歧義對 → knowledge/disambiguation/DIS-*.yaml（advisory、proposed、acyclic 不覆寫）.

    SPEC_DEBATE divergence → HUMAN_PENDING 路徑呼叫：把兩隔離詮釋 + 分歧證據存為
    AmbiguityScorer 校準語料（Rule 9.23.4/9.23.5 — 只建議不自動阻塞/改 spec）。
    maturity 恆為 proposed（禁自動 verified，比照 SPL/ADV，須人工 review 升級）。
    file_lock 保護並行寫；DIS 編號遞增不覆寫既有歧義對。
    """
    import yaml  # type: ignore
    target = out_dir or DISAMBIG_DIR
    target.mkdir(parents=True, exist_ok=True)
    lock = target / ".dis-id.lock"
    with file_lock(lock):
        dis_id = _next_dis_id(target)
        path = target / f"{dis_id}.yaml"
        doc = {
            "id": dis_id,
            "ac_id": ac_id,
            "interp_a": interp_a,
            "interp_b": interp_b,
            "divergence": round(float(divergence), 4),
            "markers": markers or [],
            "verdict": verdict,                 # None = 待人工裁決（Rule 9.23.4）
            "profile_version": profile_version,
            "provenance": {
                "source": "spec_debate (ACT-083/084)",
                "persisted_at": (today or _dt.datetime.now(_dt.timezone.utc)
                                 .isoformat(timespec="seconds")),
            },
            "maturity": "proposed",             # 強制 proposed（禁自動 verified）
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return path


def persist_from_result(result: "DebateResult", *, verdict: Optional[str] = None,
                        out_dir: Optional[Path] = None,
                        today: Optional[str] = None) -> Path:
    """便捷 adapter：直接落盤 DebateResult（divergence 出口用）。"""
    return persist_disambiguation(
        result.ac_id, result.interp_pro, result.interp_con, result.divergence,
        verdict=verdict, markers=result.markers,
        profile_version=result.profile_version, out_dir=out_dir, today=today,
    )


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print('用法：python -m tools.fsm_runtime.spec_debate "<AC 文字>"')
        return 2
    res = debate(argv[1], ac_id=argv[2] if len(argv) > 2 else "")
    print(f"verdict={res.verdict} divergence={res.divergence} markers={res.markers}")
    print(f"  pro: {res.interp_pro}")
    print(f"  con: {res.interp_con}")
    return 0 if res.verdict == "consensus" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
