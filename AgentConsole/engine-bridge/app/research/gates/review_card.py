"""審查者單維度輸出（模板 §6）與彙整卡（§7）的驗證，以及缺陷狀態的確定性轉移（§5.3）。

兩份 JSON 的契約 SSOT 是框架模板 `ADVERSARIAL-REVIEW-CARD-TEMPLATE.md`：

  · **單維度輸出**（`reviews/round-<k>/<dimension 小寫>.json`，審查者寫）：
    `validate_review_dimension` 以確定性程式檢查項目集合、整數分、加總、缺陷 code 與錨點文法、
    QA 補位欄位；不合＝該步 evaluator 失敗，重試一次仍不合即 `REVIEW_INVALID`（不寫輪列，D-55）。
    違規的 `rule` 取 `V1`～`V9`。
  · **彙整卡**（`review_card.json`，Bridge 渲染）：`validate_review_card` 驗形狀與 §7.3 四條不變量
    （渲染結果必須通過它，AT-960-12-5；範例對拍見 AT-960-12-E-1）。違規的 `rule` 取 `C1`～`C8`。

缺陷狀態由執行層依後續輪次的缺陷清單**確定性**判定（`plan_defect_transitions`）；`WAIVED` 只由
人工動作產生；合法轉移只有 OPEN→FIXED／WAIVED／SUPERSEDED、FIXED→REGRESSED、REGRESSED→FIXED
（資料庫以觸發器守住，寫入器是第一道、DB 是第二道）。
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ..db import DEFECT_TRANSITIONS
from .aggregate import CONDITION_KEYS, w100_of, weighted_total_of
from .prd_schema import PrecheckCheck
from .schemas import (
    DIMENSIONS,
    REVIEW_PARAMS,
    RUBRIC_ITEM_MAX,
    RUBRIC_REGISTRY,
    SCHEMA_REV,
    Violation,
    has_line_break,
    is_int,
    parse_offset_datetime,
)

SEVERITIES = ("P1", "P2", "P3", "P4")
DEFECT_STATUSES = tuple(DEFECT_TRANSITIONS)
NOTE_MAX_CHARS = 300
SUMMARY_MAX_CHARS = 600
CARD_VERDICTS = ("PASS", "REVISE", "ESCALATE")
FINAL_VERDICTS = ("IN_PROGRESS", "PASS", "ESCALATED")
PRECHECK_IDS = ("SLV-001", "SLV-002", "SLV-003", "AMBIGUITY")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^(ARCH|PROD|QA|SEC)-([A-Z][A-Z0-9_]{1,23})-([0-9]{2})$")
_ANCHOR_RE = re.compile(
    r"^§(?:[1-9]|1[0-4])(?:\.\d{1,2})?(?:/(?:F|US|AC|NFR|INV|EPIC)-[A-Za-z0-9-]+)?$")
_EVIDENCE_NO_RE = re.compile(r"^E-\d{3,4}$")
_DIM_KEYS = frozenset({"schema_rev", "round", "dimension", "agent_id", "prd_sha256", "rubric",
                       "score", "summary", "defects"})
_DEFECT_KEYS = frozenset({"code", "severity", "prd_anchor", "description", "suggestion",
                          "evidence_refs"})
_RUBRIC_KEYS = frozenset({"item", "score", "max", "note"})
_SLV_KEYS = frozenset({"ac_total", "ac_testable", "notes"})


# ══ 單維度輸出（§6.2）═══════════════════════════════════════════════════════════════════════
def validate_review_dimension(doc: Any, *, dimension: str, round_no: int, prd_sha256: str,
                              ac_total: int | None = None,
                              evidence_numbers: Iterable[str] | None = None) -> list[Violation]:
    """審查者單維度 JSON 的確定性驗證。`prd_sha256`、`round_no` 是任務書給的值（審查者原樣抄寫）；
    `ac_total` 是 PRD 5.2 節的機械計數（QA 維度的 `slv_manual_check.ac_total` 必須等於它）；
    `evidence_numbers` 是證據矩陣內存在的 `E-NNN`（缺陷的 `evidence_refs` 每個都須在其中）。"""
    out: list[Violation] = []

    def bad(rule: str, path: str, message: str) -> None:
        out.append(Violation(rule, path, message))

    if not isinstance(doc, Mapping):
        return [Violation("V1", "$", "審查者輸出整份檔案須只含一個 JSON 物件")]
    registry = RUBRIC_REGISTRY.get(dimension)
    if registry is None:
        return [Violation("V1", "dimension", f"不認得的維度 {dimension!r}")]
    expected = set(_DIM_KEYS) | ({"qa_extra"} if dimension == "QA" else set())
    for key in sorted(set(doc) - expected):
        bad("V1", key, f"多餘的欄位 {key}" + ("（只有 QA 維度可有 qa_extra）" if key == "qa_extra"
                                           else ""))
    for key in sorted(expected - set(doc)):
        bad("V1", key, f"缺必填欄位 {key}")
    _check_header(doc, dimension, round_no, prd_sha256, registry, bad)
    rubric_total = _check_rubric(doc.get("rubric"), registry, bad)
    score = doc.get("score")
    if not is_int(score) or not 0 <= score <= 100:
        bad("V3", "score", "score 須為 0～100 的整數")
    elif rubric_total is not None and score != rubric_total:
        bad("V3", "score", f"score 須等於 rubric 五項之和 {rubric_total}（收到 {score}）")
    summary = doc.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > SUMMARY_MAX_CHARS:
        bad("V1", "summary", f"summary 須為 1～{SUMMARY_MAX_CHARS} 字的非空字串")
    defects = doc.get("defects")
    refs_ok = None if evidence_numbers is None else set(evidence_numbers)
    if not isinstance(defects, list):
        bad("V1", "defects", "defects 須為陣列（可空）")
        defects = []
    for i, defect in enumerate(defects):
        _check_defect(defect, i, registry, refs_ok, bad)
    if dimension == "QA" and "qa_extra" in doc:
        _check_qa_extra(doc.get("qa_extra"), defects, ac_total, bad)
    for path, text in _walk_text(doc, "$"):
        if has_line_break(text):
            bad("V1", path, "文字欄位不得含換行")
    return out


def _check_header(doc: Mapping[str, Any], dimension: str, round_no: int, prd_sha256: str,
                  registry: Mapping[str, Any], bad: Any) -> None:
    if doc.get("schema_rev") != SCHEMA_REV or not is_int(doc.get("schema_rev")):
        bad("V1", "schema_rev", f"schema_rev 須為 {SCHEMA_REV}")
    if not is_int(doc.get("round")) or doc.get("round") != round_no:
        bad("V1", "round", f"round 須等於任務書指定的輪次 {round_no}")
    if doc.get("dimension") != dimension:
        bad("V1", "dimension", f"dimension 須為 {dimension}（檔名小寫須對應）")
    if doc.get("agent_id") != registry["agent_id"]:
        bad("V2", "agent_id", f"agent_id 須等於登錄表的 {registry['agent_id']}")
    sha = doc.get("prd_sha256")
    if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
        bad("V2", "prd_sha256", "prd_sha256 須為 64 位小寫 hex")
    elif sha != prd_sha256:
        bad("V2", "prd_sha256", "prd_sha256 須逐位元等於任務書給的值（原樣抄寫）")


def _check_rubric(rubric: Any, registry: Mapping[str, Any], bad: Any) -> int | None:
    """回五項分數之和（任一項不合法回 None，由呼叫端略過加總比對）。"""
    if not isinstance(rubric, list) or any(not isinstance(r, Mapping) for r in rubric):
        bad("V3", "rubric", "rubric 須為物件陣列")
        return None
    items = [r.get("item") for r in rubric]
    if sorted(map(str, items)) != sorted(registry["items"]) or len(items) != len(registry["items"]):
        bad("V3", "rubric", f"rubric 項目集合須恰為 {list(registry['items'])}，收到 {items}")
    total, clean = 0, True
    for i, row in enumerate(rubric):
        path = f"rubric[{i}]"
        for key in sorted(set(row) - _RUBRIC_KEYS):
            bad("V1", f"{path}.{key}", f"多餘的欄位 {key}")
        if row.get("max") != RUBRIC_ITEM_MAX or not is_int(row.get("max")):
            bad("V3", f"{path}.max", f"max 須為 {RUBRIC_ITEM_MAX}")
        value = row.get("score")
        if not is_int(value) or not 0 <= value <= RUBRIC_ITEM_MAX:
            bad("V3", f"{path}.score", f"score 須為 0～{RUBRIC_ITEM_MAX} 的整數：{value!r}")
            clean = False
            continue
        total += value
        note = row.get("note")
        if not isinstance(note, str) or not note.strip() or len(note) > NOTE_MAX_CHARS:
            bad("V3", f"{path}.note", f"note 須為 1～{NOTE_MAX_CHARS} 字的非空字串")
        elif value >= 18 and "§" not in note:
            bad("V3", f"{path}.note", "score ≥18 的項目，note 必須含至少一個 PRD 錨點（含 §）")
    return total if clean and len(rubric) == len(registry["items"]) else None


def _check_defect(defect: Any, index: int, registry: Mapping[str, Any],
                  evidence: set[str] | None, bad: Any) -> None:
    path = f"defects[{index}]"
    if not isinstance(defect, Mapping):
        bad("V4", path, "缺陷須為物件")
        return
    for key in sorted(set(defect) - _DEFECT_KEYS):
        bad("V1", f"{path}.{key}", f"多餘的欄位 {key}")
    for key in sorted(_DEFECT_KEYS - set(defect)):
        bad("V1", f"{path}.{key}", f"缺必填欄位 {key}")
    code = defect.get("code")
    match = _CODE_RE.match(code) if isinstance(code, str) else None
    if match is None:
        bad("V4", f"{path}.code", "code 須符合 ^(ARCH|PROD|QA|SEC)-[A-Z][A-Z0-9_]{1,23}-[0-9]{2}$")
    else:
        if match.group(1) != registry["defect_prefix"]:
            bad("V4", f"{path}.code", f"code 前綴須為 {registry['defect_prefix']}（對應維度）")
        if match.group(2).lower() not in registry["items"]:
            bad("V4", f"{path}.code", "code 的中段須是該維度某 rubric 項目 id 的大寫")
    if defect.get("severity") not in SEVERITIES:
        bad("V4", f"{path}.severity", f"severity 須為 {'｜'.join(SEVERITIES)}")
    anchor = defect.get("prd_anchor")
    if not isinstance(anchor, str) or not _ANCHOR_RE.match(anchor):
        bad("V4", f"{path}.prd_anchor", "prd_anchor 須為 §<章>[.<節>][/<ID>]（章為家規 14 章之一）")
    for key in ("description", "suggestion"):
        if not isinstance(defect.get(key), str) or not defect.get(key).strip():
            bad("V4", f"{path}.{key}", f"{key} 須為非空字串")
    refs = defect.get("evidence_refs")
    if not isinstance(refs, list) or any(
            not isinstance(r, str) or not _EVIDENCE_NO_RE.match(r) for r in refs):
        bad("V5", f"{path}.evidence_refs", "evidence_refs 須為 E-NNN 字串陣列（可空）")
    elif evidence is not None:
        for ref in refs:
            if ref not in evidence:
                bad("V5", f"{path}.evidence_refs", f"{ref} 不存在於證據矩陣")


def _check_qa_extra(extra: Any, defects: Sequence[Any], ac_total: int | None, bad: Any) -> None:
    if not isinstance(extra, Mapping) or set(extra) != {"slv_manual_check"}:
        bad("V6", "qa_extra", "qa_extra 只含 slv_manual_check")
        return
    check = extra["slv_manual_check"]
    if not isinstance(check, Mapping) or set(check) != _SLV_KEYS:
        bad("V6", "qa_extra.slv_manual_check", "須為 {ac_total, ac_testable, notes}")
        return
    total, testable = check.get("ac_total"), check.get("ac_testable")
    if not is_int(total) or total < 0:
        bad("V6", "qa_extra.slv_manual_check.ac_total", "ac_total 須為非負整數")
    elif ac_total is not None and total != ac_total:
        bad("V6", "qa_extra.slv_manual_check.ac_total",
            f"ac_total 須等於執行層對 PRD 5.2 節 AC 標題的機械計數 {ac_total}（收到 {total}）")
    if not is_int(testable) or testable < 0 or (is_int(total) and testable > total):
        bad("V6", "qa_extra.slv_manual_check.ac_testable", "須為 0～ac_total 的整數")
    elif is_int(total) and testable < total and not any(
            isinstance(d, Mapping) and d.get("severity") in ("P1", "P2") for d in defects):
        bad("V6", "qa_extra.slv_manual_check",
            "ac_testable < ac_total 而 defects 沒有對應的 P1 或 P2 缺陷（內部矛盾）")
    if not isinstance(check.get("notes"), str) or not check.get("notes").strip():
        bad("V6", "qa_extra.slv_manual_check.notes", "notes 須為非空字串")


def _walk_text(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, sub in value.items():
            yield from _walk_text(sub, f"{path}.{key}")
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            yield from _walk_text(sub, f"{path}[{index}]")


# ══ 彙整卡（§7）═════════════════════════════════════════════════════════════════════════════
_CARD_TOP = frozenset({"schema_rev", "research_id", "rounds", "retry_count", "final_verdict"})
_ROUND_KEYS = frozenset({"round", "prd_version", "prd_version_no", "prd_sha256", "params",
                         "precheck", "reviewers", "weighted_total", "min_dimension_score",
                         "conditions", "open_p1_count", "passed", "verdict", "defects", "fsm",
                         "started_at", "ended_at"})
_REVIEWER_KEYS = frozenset({"dimension", "weight", "agent", "agent_id", "agent_yaml_sha256",
                            "assist_agent_id", "assist_agent_yaml_sha256", "persona_sha256",
                            "score", "raw_file", "raw_sha256"})
_CARD_DEFECT_KEYS = frozenset({"id", "dimension", "severity", "code", "anchor", "finding",
                               "suggestion", "evidence_refs", "status", "resolved_in", "waiver"})


def validate_review_card(card: Any) -> list[Violation]:
    """彙整卡的形狀與 §7.3 不變量：公式、`passed` 為四條件之且、`verdict=PASS` ⇔ `passed`、有呼
    叫 `gate`
    的輪 `fsm.gate_result=PASS` ⇔ 通過（POST_HUMAN 通過輪兩鍵皆 null）、`prd_version_no` 不遞減
    且同號同版同雜湊。"""
    out: list[Violation] = []

    def bad(rule: str, path: str, message: str) -> None:
        out.append(Violation(rule, path, message))

    if not isinstance(card, Mapping):
        return [Violation("C1", "$", "彙整卡須為 JSON 物件")]
    for key in sorted(set(card) - _CARD_TOP):
        bad("C1", key, f"多餘的頂層欄位 {key}")
    for key in sorted(_CARD_TOP - set(card)):
        bad("C1", key, f"缺必填欄位 {key}")
    if card.get("schema_rev") != SCHEMA_REV:
        bad("C1", "schema_rev", f"schema_rev 須為 {SCHEMA_REV}")
    if card.get("final_verdict") not in FINAL_VERDICTS:
        bad("C1", "final_verdict", f"final_verdict 須為 {'｜'.join(FINAL_VERDICTS)}")
    rounds = card.get("rounds")
    if not isinstance(rounds, list):
        return out + [Violation("C1", "rounds", "rounds 須為陣列")]
    last_no, versions = 0, {}
    for index, rnd in enumerate(rounds):
        path = f"rounds[{index}]"
        if not isinstance(rnd, Mapping):
            bad("C1", path, "輪須為物件")
            continue
        _check_card_round(rnd, path, bad)
        number = rnd.get("prd_version_no")
        if not is_int(number) or number < 1:
            bad("C3", f"{path}.prd_version_no",
                "prd_version_no 須為 ≥1 的整數（模板 §7.1 的正式鍵）")
            continue
        if number < last_no:
            bad("C4", f"{path}.prd_version_no", f"prd_version_no 不得遞減（前一輪為 {last_no}）")
        last_no = max(last_no, number)
        pair = (rnd.get("prd_version"), rnd.get("prd_sha256"))
        if versions.setdefault(number, pair) != pair:
            bad("C4", f"{path}.prd_version_no",
                f"同一個 prd_version_no {number} 只能對應一組 prd_version 與 prd_sha256")
    return out


def _check_card_round(rnd: Mapping[str, Any], path: str, bad: Any) -> None:
    for key in sorted(set(rnd) - _ROUND_KEYS):
        bad("C1", f"{path}.{key}", f"多餘的欄位 {key}")
    for key in sorted(_ROUND_KEYS - set(rnd)):
        bad("C1", f"{path}.{key}", f"缺必填欄位 {key}")
    if rnd.get("params") != dict(REVIEW_PARAMS):
        bad("C1", f"{path}.params", "params 須為參數快照（weights／threshold／dimension_floor）")
    for key in ("prd_sha256",):
        if not isinstance(rnd.get(key), str) or not _SHA256_RE.fullmatch(rnd.get(key) or ""):
            bad("C1", f"{path}.{key}", f"{key} 須為 64 位小寫 hex")
    precheck = rnd.get("precheck")
    checks = precheck.get("checks") if isinstance(precheck, Mapping) else None
    check_ids = [c.get("id") for c in checks if isinstance(c, Mapping)] if isinstance(
        checks, list) else None
    if check_ids != list(PRECHECK_IDS):
        bad("C2", f"{path}.precheck", f"checks 的 id 須恰為 {list(PRECHECK_IDS)}")
    conditions = rnd.get("conditions")
    if not isinstance(conditions, Mapping) or set(conditions) != set(CONDITION_KEYS):
        bad("C2", f"{path}.conditions", f"conditions 須恰有 {list(CONDITION_KEYS)}")
        conditions = {}
    passed, verdict = rnd.get("passed"), rnd.get("verdict")
    if verdict not in CARD_VERDICTS:
        bad("C2", f"{path}.verdict", f"verdict 須為 {'｜'.join(CARD_VERDICTS)}")
    all_hold = all(bool(conditions.get(k)) for k in CONDITION_KEYS)
    if passed != all_hold or not isinstance(passed, bool):
        bad("C2", f"{path}.passed", "passed 須等於 conditions 四值之且")
    if (verdict == "PASS") != (passed is True):
        bad("C2", f"{path}.verdict", "verdict=PASS 若且唯若 passed=true")
    _check_scores(rnd, path, bad)
    fsm = rnd.get("fsm")
    if not isinstance(fsm, Mapping) or set(fsm) != {"gate_result", "retry_count"}:
        bad("C5", f"{path}.fsm", "fsm 須恰為 {gate_result, retry_count}")
    else:
        result = fsm.get("gate_result")
        if result not in ("PASS", "FAIL", None):
            bad("C5", f"{path}.fsm.gate_result", "gate_result 須為 PASS、FAIL 或 null")
        elif result is None and passed is not True:
            bad("C5", f"{path}.fsm",
                "沒有呼叫 gate 的輪只可能是 POST_HUMAN 通過輪（passed 須為 true）")
        elif result is not None and (result == "PASS") != (passed is True):
            bad("C5", f"{path}.fsm.gate_result",
                "有呼叫 gate 的輪：gate_result=PASS 若且唯若 passed=true")
    for key in ("started_at", "ended_at"):
        if parse_offset_datetime(rnd.get(key)) is None:
            bad("C1", f"{path}.{key}", f"{key} 須為帶時區 offset 的 ISO-8601")
    defects = rnd.get("defects")
    if not isinstance(defects, list):
        bad("C1", f"{path}.defects", "defects 須為陣列")
        return
    for i, defect in enumerate(defects):
        if not isinstance(defect, Mapping) or set(defect) != _CARD_DEFECT_KEYS:
            bad("C6", f"{path}.defects[{i}]", f"缺陷鍵須恰為 {sorted(_CARD_DEFECT_KEYS)}")
        elif defect.get("status") not in DEFECT_STATUSES:
            bad("C6", f"{path}.defects[{i}].status", f"status 須為 {'｜'.join(DEFECT_STATUSES)}")


def _check_scores(rnd: Mapping[str, Any], path: str, bad: Any) -> None:
    reviewers = rnd.get("reviewers")
    total, minimum = rnd.get("weighted_total"), rnd.get("min_dimension_score")
    if not isinstance(reviewers, list):
        bad("C1", f"{path}.reviewers", "reviewers 須為陣列")
        return
    if not reviewers:                      # 前置否決不過：不計分
        if total is not None or minimum is not None:
            bad("C7", f"{path}.reviewers",
                "reviewers 為空（前置否決不過）時 weighted_total 與 min_dimension_score 須為 null")
        return
    scores: dict[str, int] = {}
    for i, reviewer in enumerate(reviewers):
        where = f"{path}.reviewers[{i}]"
        if not isinstance(reviewer, Mapping) or set(reviewer) != _REVIEWER_KEYS:
            bad("C7", where, f"審查者鍵須恰為 {sorted(_REVIEWER_KEYS)}（不含 model）")
            continue
        dim = reviewer.get("dimension")
        if dim not in DIMENSIONS or not is_int(reviewer.get("score")):
            bad("C7", where, "dimension／score 不合")
            continue
        scores[dim] = reviewer["score"]
        reg = RUBRIC_REGISTRY[dim]
        if reviewer.get("agent_id") != reg["agent_id"] or reviewer.get(
                "assist_agent_id") != reg["assist_agent_id"]:
            bad("C7", where, "agent_id／assist_agent_id 須等於登錄表")
    if set(scores) != set(DIMENSIONS):
        bad("C7", f"{path}.reviewers", "四個維度各須恰一筆")
        return
    w100 = w100_of(scores)
    if total is None or Decimal(str(total)) != weighted_total_of(w100):
        bad("C7", f"{path}.weighted_total",
            f"weighted_total 須等於 W100／100＝{weighted_total_of(w100)}")
    if minimum != min(scores.values()):
        bad("C7", f"{path}.min_dimension_score", f"須等於四維最低分 {min(scores.values())}")


# ══ 缺陷狀態轉移（§5.3）═════════════════════════════════════════════════════════════════════
def is_allowed_transition(old: str, new: str) -> bool:
    """合法轉移：OPEN→FIXED／WAIVED／SUPERSEDED、FIXED→REGRESSED、REGRESSED→FIXED（其餘一律不合法，
    含任何回到 OPEN 者）。與 `db.DEFECT_TRANSITIONS` 同源。"""
    return new in DEFECT_TRANSITIONS.get(old, frozenset())


def next_defect_status(old: str, new: str, *, waived_by: str | None = None,
                       waiver_reason: str | None = None) -> str:
    """`old`→`new` 的轉移檢查（寫入器的第一道守衛）：不合法丟 `ValueError`；WAIVED 須有 `waived_by`
    與非空 `waiver_reason`（只由人工動作產生）。"""
    if not is_allowed_transition(old, new):
        raise ValueError(f"缺陷狀態 {old}→{new} 不是合法轉移")
    if new == "WAIVED" and not (waived_by and (waiver_reason or "").strip()):
        raise ValueError("WAIVED 須附 waived_by 與非空 waiver_reason")
    return new


@dataclass(frozen=True)
class DefectTransition:
    """要寫進資料庫的一筆缺陷狀態轉移。`fixed_in_version_no` 在 FIXED 時是被審的 PRD 版本號。"""

    defect_id: str
    defect_no: str
    new_status: str
    fixed_in_version_no: int | None = None


def anchor_target_gone(anchor: str, prd_text: str | None) -> bool:
    """缺陷的 `prd_anchor` 所指內容已從 PRD 消失（錨點帶 `/<ID>` 而該 ID 不再出現於全文）。"""
    if prd_text is None or "/" not in anchor:
        return False
    return anchor.split("/", 1)[1] not in prd_text


def plan_defect_transitions(previous: Sequence[Mapping[str, Any]],
                            raised: Iterable[tuple[str, str]], *, prd_version_no: int,
                            prd_text: str | None = None) -> list[DefectTransition]:
    """依本輪被提出的缺陷（`(code, anchor)`）確定性判定舊缺陷的新狀態。

    OPEN：本輪再度提出＝維持；其 anchor 所指內容已消失＝SUPERSEDED；否則＝FIXED（解決於本輪被審的
    PRD 版本）。FIXED：再度提出＝REGRESSED。REGRESSED：本輪沒提＝FIXED，再度提出＝維持。WAIVED 與
    SUPERSEDED 是終態，不動。`previous` 每列取 `id`、`defect_no`、`code`、`anchor`、`status`。"""
    again = set(raised)
    plan: list[DefectTransition] = []
    for row in previous:
        status, key = row["status"], (row["code"], row["anchor"])
        if status == "OPEN" and key not in again:
            gone = anchor_target_gone(str(row["anchor"]), prd_text)
            plan.append(DefectTransition(str(row["id"]), str(row["defect_no"]),
                                         "SUPERSEDED" if gone else "FIXED",
                                         None if gone else prd_version_no))
        elif status == "FIXED" and key in again:
            plan.append(DefectTransition(str(row["id"]), str(row["defect_no"]), "REGRESSED"))
        elif status == "REGRESSED" and key not in again:
            plan.append(DefectTransition(str(row["id"]), str(row["defect_no"]), "FIXED",
                                         prd_version_no))
    return plan


def precheck_to_detail(checks: Sequence[PrecheckCheck]) -> dict[str, Any]:
    """輪列 `precheck_detail`（JSONB）與卡上 `precheck` 的同一份形狀。"""
    return {"passed": all(c.passed for c in checks), "checks": [c.to_card() for c in checks]}
