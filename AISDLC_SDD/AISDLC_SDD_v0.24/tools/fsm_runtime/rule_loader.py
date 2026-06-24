"""Phase H M3 / ACT-051~052 + M5 / ACT-054 — Rule Registry loader.

落實 SDD_improving_Automation_08.md §4.1 / §G4：把 Rule 9 治理規則從 CLAUDE.md
散文巨表抽成「可查詢的結構化規則庫」governance/rules/*.yaml，並提供：
  - load_for_state(): 狀態感知載入（只載 trigger_states 命中的規則 → 漸進式揭露）
  - Scaffold ROI（§5.1 / ACT-054）：fire_count / catch_count / false_positive
  - Rule Graduation：active → audit-only → deprecated（提案，須人工 review 生效）

規則檔結構（governance/rules/R-9.N-*.yaml）：
  id, title, trigger_states[], severity, maturity(active|audit-only|deprecated),
  spec, test_ref, scaffold_roi{fire_count,catch_count,false_positive_count}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .file_lock import file_lock

_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DIR = _ROOT / "governance"
RULES_DIR = GOVERNANCE_DIR / "rules"

MATURITY_LEVELS = ("active", "audit-only", "deprecated")

# Rule Graduation 門檻（§5.1）：fire 多次但從未 catch → 提議降級
GRADUATION_MIN_FIRES = 1000        # 觀察窗（fire_count）
GRADUATION_DEMOTE_TO_AUDIT = "active"      # active → audit-only
GRADUATION_DEMOTE_TO_DEPRECATED = "audit-only"  # audit-only → deprecated


class RuleOverwriteProtected(RuntimeError):
    """禁止自動覆寫 active 安全規則的 maturity（須人工 review，沿用 slv_generator 精神）。"""


@dataclass
class Rule:
    id: str
    title: str
    trigger_states: List[str] = field(default_factory=list)
    severity: str = "medium"
    maturity: str = "active"
    spec: str = ""
    test_ref: str = ""
    # W-54-1（守門機制分類 SSOT，improving_55）：規則「自描述」其守門機制類別，取值
    # escalation|hook|lint_tlc|meta_loop|manual（W-39-1 五分類機讀化）。空＝未分類→
    # enforcement_mechanism_lint fail-closed 報錯（每條 active 規則必分類）。供
    # comprehensive_governance_coverage 逐類靜態驗證「宣稱守門機制是否真實在位」。
    enforcement_mechanism: str = ""
    # W-19-1（catch 側契約）：規則「自描述」其守望的失敗模式。空＝未定義→不參與 catch
    # 自動歸因（fail-closed）。這是 catch 三要件之一（見 record_state_catches）。
    failure_mode: str = ""
    scaffold_roi: Dict[str, int] = field(default_factory=lambda: {
        "fire_count": 0, "catch_count": 0, "false_positive_count": 0,
    })
    _path: Optional[Path] = None

    def roi(self) -> float:
        fires = int(self.scaffold_roi.get("fire_count", 0))
        if fires <= 0:
            return 1.0  # 未觸發 → 不評斷（中性）
        return round(int(self.scaffold_roi.get("catch_count", 0)) / fires, 4)


def _load_rule_file(path: Path) -> Optional[Rule]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict) or "id" not in data:
        return None
    roi = data.get("scaffold_roi") or {}
    return Rule(
        id=str(data["id"]),
        title=str(data.get("title", "")),
        trigger_states=list(data.get("trigger_states", []) or []),
        severity=str(data.get("severity", "medium")),
        maturity=str(data.get("maturity", "active")),
        spec=str(data.get("spec", "")),
        test_ref=str(data.get("test_ref", "")),
        enforcement_mechanism=str(data.get("enforcement_mechanism", "")),  # W-54-1：optional，舊規則缺＝""
        failure_mode=str(data.get("failure_mode", "")),  # W-19-1：optional，舊規則缺＝""
        scaffold_roi={
            "fire_count": int(roi.get("fire_count", 0)),
            "catch_count": int(roi.get("catch_count", 0)),
            "false_positive_count": int(roi.get("false_positive_count", 0)),
        },
        _path=path,
    )


def load_all(rules_dir: Optional[Path] = None) -> List[Rule]:
    d = rules_dir or RULES_DIR
    if not d.exists():
        return []
    out: List[Rule] = []
    for p in sorted(d.glob("R-*.yaml")):
        r = _load_rule_file(p)
        if r is not None:
            out.append(r)
    return out


def load_for_state(state: str, *, rules_dir: Optional[Path] = None,
                   include_deprecated: bool = False) -> List[Rule]:
    """狀態感知載入：只回傳 trigger_states 命中當前 FSM state 的規則（漸進式揭露）。

    deprecated 規則預設不載入（已退役）。trigger_states 含 "*" 視為全域規則。
    """
    out: List[Rule] = []
    for r in load_all(rules_dir):
        if r.maturity == "deprecated" and not include_deprecated:
            continue
        if "*" in r.trigger_states or state in r.trigger_states:
            out.append(r)
    return out


def _write_rule(rule: Rule) -> None:
    if rule._path is None:
        raise ValueError(f"rule {rule.id} has no backing path")
    payload = {
        "id": rule.id,
        "title": rule.title,
        "trigger_states": rule.trigger_states,
        "severity": rule.severity,
        "maturity": rule.maturity,
        "spec": rule.spec,
        "test_ref": rule.test_ref,
    }
    # W-54-1 持久化潔淨度（同 failure_mode 模式）：enforcement_mechanism 為 optional，
    # **只在非空時寫回**，排在 test_ref 後、failure_mode 前，避免 round-trip 對未分類舊規則
    # 注入空欄污染凍結本體（DEF-11-002 家族）。
    if rule.enforcement_mechanism:
        payload["enforcement_mechanism"] = rule.enforcement_mechanism
    # W-19-1 持久化潔淨度：failure_mode 為 optional，**只在非空時寫回**。否則
    # record_state_fires/catches round-trip 重寫 YAML 時會對全部舊規則插入空 failure_mode，
    # 污染凍結本體（DEF-11-002 家族潔淨度）；且非空時排在 test_ref 後、scaffold_roi 前以維持可讀性。
    if rule.failure_mode:
        payload["failure_mode"] = rule.failure_mode
    payload["scaffold_roi"] = rule.scaffold_roi
    # file_lock sentinel 必須是「獨立 .lock 檔」，不可用資源檔本身
    # （資源檔已存在 → O_EXCL 立即 FileExistsError → timeout）。
    lock = rule._path.with_suffix(rule._path.suffix + ".lock")
    with file_lock(lock):
        tmp = rule._path.with_suffix(rule._path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        tmp.replace(rule._path)


def record_fire(rule_id: str, *, caught: bool, false_positive: bool = False,
                rules_dir: Optional[Path] = None) -> Optional[Rule]:
    """ACT-054：記帳一次規則觸發。caught=True 代表真攔到問題。"""
    for r in load_all(rules_dir):
        if r.id != rule_id:
            continue
        r.scaffold_roi["fire_count"] += 1
        if caught:
            r.scaffold_roi["catch_count"] += 1
        if false_positive:
            r.scaffold_roi["false_positive_count"] += 1
        _write_rule(r)
        return r
    return None


def record_state_fires(state: str, *, caught: bool = False,
                       rules_dir: Optional[Path] = None) -> List[str]:
    """W-18-1：批次記帳「進入 state 時 load_for_state(state) 命中的規則各 fire 一次」。

    「fire（命中）」語意＝FSM 經 transition() 進入狀態 state 時，該狀態 lazy-load 命中的
    每條規則被「行使（on-watch）」一次（與框架既有「規則依狀態 lazy-load」模型同構）。
    預設 caught=False（純守望計數；catch 側語意未定義，見 DEF-18-001）。

    比 per-rule 迴圈呼 record_fire（每次重 load_all＝O(N²)）高效：單次 load_all、對命中
    規則一次性增量、各寫一次。回傳本次記帳的 rule_id 清單（命中且已遞增者）。
    deprecated 規則不記（已退役，與 load_for_state 一致）。
    """
    fired: List[str] = []
    for r in load_all(rules_dir):
        if r.maturity == "deprecated":
            continue
        if "*" not in r.trigger_states and state not in r.trigger_states:
            continue
        r.scaffold_roi["fire_count"] += 1
        if caught:
            r.scaffold_roi["catch_count"] += 1
        _write_rule(r)
        fired.append(r.id)
    return fired


def record_state_catches(attributed_rule_ids: List[str], *,
                         rules_dir: Optional[Path] = None) -> List[str]:
    """W-19-2（catch 側契約對偶 record_state_fires）：對「明確歸因 + failure_mode 已定義」的
    規則各記一次 catch（scaffold_roi.catch_count += 1）。回傳實際記 catch 的 rule_id 清單。

    **catch 語意（W-19 契約，閉合 DEF-18-001）**＝三要件齊備才 catch+1：
      ① 規則自描述其守望的失敗模式（`failure_mode` 非空）；
      ② 對應的攔截事件（ESCALATION / MONITOR_VIOLATION）真實發生（由呼叫點觸發本函式）；
      ③ 該攔截事件結構化攜帶此 rule_id 作 attribution（呼叫端明確傳入 attributed_rule_ids）。

    **fail-closed（寧缺勿濫，守 DEF-18-001「擅自映射比不做更糟」）**：attributed_rule_ids 空、
    或規則無 failure_mode、或非 attributed 子集 → 一律不記。無確定證據絕不污染 ROI 信號——
    刻意「不靠時序鄰近猜歸因」（時序鄰近 ≠ 因果歸因）。deprecated 規則不記（與 fire 側一致）。

    **紅線**：只增 catch_count 計數、**永不呼叫 set_maturity**（active 規則退役仍 🔴 人工，
    R-9.20 #11）；catch_count>0 正是 propose_graduation 保護有用規則不被誤退役的依據。
    """
    if not attributed_rule_ids:
        return []
    wanted = set(attributed_rule_ids)
    caught: List[str] = []
    for r in load_all(rules_dir):
        if r.maturity == "deprecated":
            continue
        if r.id not in wanted:
            continue
        if not r.failure_mode:  # 要件①缺：未自描述 failure_mode → fail-closed 不記
            continue
        r.scaffold_roi["catch_count"] += 1
        _write_rule(r)
        caught.append(r.id)
    return caught


def propose_graduation(rule: Rule) -> Optional[str]:
    """回傳建議的新 maturity（不寫入），或 None（無須降級）。

    規則：fire_count ≥ GRADUATION_MIN_FIRES 且 catch_count == 0 →
      active → audit-only；audit-only → deprecated。deprecated 不再降。
    """
    fires = int(rule.scaffold_roi.get("fire_count", 0))
    catches = int(rule.scaffold_roi.get("catch_count", 0))
    if fires < GRADUATION_MIN_FIRES or catches > 0:
        return None
    if rule.maturity == "active":
        return "audit-only"
    if rule.maturity == "audit-only":
        return "deprecated"
    return None


# Phase I M3 / ACT-066：反向 graduation 門檻（合成代謝）。catch/fire ROI 高且穩定
# 的 scaffold 可被「提議固化為技能」（仍經人工 set_maturity / SPL verified gate）。
PROMOTION_MIN_FIRES = 50         # 觀察窗
PROMOTION_MIN_ROI = 0.8          # catch/fire ≥ 0.8 視為高價值穩定


def propose_promotion(rule: Rule) -> Optional[str]:
    """反向 graduation（補 §5.2 雙向代謝的合成面）：回傳建議的固化說明，或 None。

    與 propose_graduation（單向退化）對稱：fire_count ≥ PROMOTION_MIN_FIRES 且
    ROI ≥ PROMOTION_MIN_ROI → 提議把此規則固化為可複用技能（SPL）。
    僅「提議」——禁自動套用（須人工經 set_maturity(reviewed_by=) / SPL verified gate）。
    """
    fires = int(rule.scaffold_roi.get("fire_count", 0))
    if fires < PROMOTION_MIN_FIRES:
        return None
    if rule.roi() < PROMOTION_MIN_ROI:
        return None
    return (
        f"規則 {rule.id} 觸發 {fires} 次、ROI={rule.roi()}（≥{PROMOTION_MIN_ROI}）— "
        f"穩定高價值，提議固化為可複用技能（SPL）。須人工 review 升 verified。"
    )


# Phase J / ACT-076：能力驅動退役判據。當對應能力的 benchmark 連續滿分
# （capability_surpassed=True）且該鷹架近乎從不 catch（fire 多 / catch 0），代表
# 「底層模型已超出此鷹架」——比 propose_graduation 的純 fire-count 門檻更早觸發。
# 仍只「提議」，退役必經 set_maturity(reviewed_by=) 人工 gate（Rule 9.22.3）。
CAPABILITY_GRADUATION_MIN_FIRES = 50  # 較 GRADUATION_MIN_FIRES(1000) 寬，因有能力證據佐證


def propose_graduation_capability(rule: Rule, *, capability_surpassed: bool) -> Optional[str]:
    """能力驅動退役提案（不寫入）。回傳建議的新 maturity，或 None。

    條件：capability_surpassed=True 且 fire_count ≥ CAPABILITY_GRADUATION_MIN_FIRES
    且 catch_count == 0。active→audit-only；audit-only→deprecated；deprecated 不再降。
    """
    if not capability_surpassed:
        return None
    fires = int(rule.scaffold_roi.get("fire_count", 0))
    catches = int(rule.scaffold_roi.get("catch_count", 0))
    if fires < CAPABILITY_GRADUATION_MIN_FIRES or catches > 0:
        return None
    if rule.maturity == "active":
        return "audit-only"
    if rule.maturity == "audit-only":
        return "deprecated"
    return None


def set_maturity(rule_id: str, new_maturity: str, *, reviewed_by: str,
                 rules_dir: Optional[Path] = None) -> Rule:
    """套用 maturity 變更——**必填 reviewed_by**（人工 review gate）。

    退役/降級永不自動發生；本函式代表「人工已 review 並核准」。
    """
    if new_maturity not in MATURITY_LEVELS:
        raise ValueError(f"invalid maturity={new_maturity!r}; expected {MATURITY_LEVELS}")
    if not reviewed_by or not str(reviewed_by).strip():
        raise RuleOverwriteProtected(
            "set_maturity 需要 reviewed_by（人工 review signoff）——禁止自動退役規則"
        )
    for r in load_all(rules_dir):
        if r.id == rule_id:
            prior_maturity = r.maturity
            r.maturity = new_maturity
            _write_rule(r)
            # Phase L M-L1 / ACT-090 / Rule 9.24.1：退役方向（active/audit-only →
            # audit-only/deprecated）落一筆 retire 至 meta-loop ledger，供 META_FSM
            # ChurnBounded/GraduationRatchet 追蹤。退役只記帳、不 raise（縮小規則集
            # 永遠安全）；記帳失敗只記 warning，絕不破壞既有 set_maturity 契約。
            if _is_retire_direction(prior_maturity, new_maturity):
                _record_rule_retirement(r)
            return r
    raise KeyError(f"rule not found: {rule_id}")


# 退役方向序（越後越「退」）：active < audit-only < deprecated。
_RETIRE_ORDER = {"active": 0, "audit-only": 1, "deprecated": 2}


def _is_retire_direction(prior: str, new: str) -> bool:
    """是否為退役方向的 maturity 變更（成熟度往退役端移動）。"""
    return _RETIRE_ORDER.get(new, 0) > _RETIRE_ORDER.get(prior, 0)


def _record_rule_retirement(rule: "Rule") -> None:
    """把一次規則退役落入 meta-loop ledger（不 raise；對既有測試環境穩健）。"""
    try:
        from .meta_halt import meta_halt_monitor as _mh
        from .meta_halt import meta_ledger as _ml
        # 語意指紋排除 id（與採納端一致：換皮重學收斂同指紋）。
        fp_src = " ".join(str(x) for x in (rule.title, rule.spec) if x).strip() or rule.id
        fingerprint = _ml.fingerprint_of(fp_src)
        cap = int(rule.scaffold_roi.get("capability_level", 0) or 0)
        _mh.record_rule_retire(
            rule.id, fingerprint, cap,
            source="scaffold_gc", note=f"set_maturity→{rule.maturity}",
        )
    except Exception:  # noqa: BLE001 — 記帳是 advisory 審計鏈，失敗不得破壞退役契約
        pass
