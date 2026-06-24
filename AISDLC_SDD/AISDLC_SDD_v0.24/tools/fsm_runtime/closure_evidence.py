"""closure_evidence.py — improving_21 / DEF-20-001 結案證據強制重推導

把「反幻覺紀律」（pytest passed / commit hash / push / tag 等結案宣稱只能來自
真實 repo 狀態，不可編造）由「agent 跨 session 自律」升級為「框架機械可驗」。

兩層驗證（對齊計畫書 §4 W-21-1 / W-21-2）：
  廉價層（git 事實，永遠真重推導，fail-closed 硬核）：
      claimed_commits 真存在（git cat-file -e）∧ 在當前 HEAD 歷史（merge-base
      --is-ancestor）；claimed_tag 真存在（git rev-parse --verify）。任一無法
      重推導 → FAIL（直擊「編造 commit/push/tag」幻覺事故核心）。
  昂貴層（pytest passed / ci-gate floors，不在 hook budget 內重跑）：
      不重跑，改驗「綁定當前 HEAD 的 rederive 證書」。證書由本模組 --rederive
      模式產生時 stamp 當前 HEAD（天然綁定 sha，不依賴 / 不改 ci-gate.sh）。
      契約 base_sha != HEAD 或證書缺失/數字不符 → INCONCLUSIVE（fail-closed
      不綠勾，比照框架 embodied_grounding 零觀測 inconclusive 語意，絕不假綠）。

被 .claude/hooks/closure_evidence_verify.py（thin git post-commit hook，advisory
永不阻擋 commit）import。純函式、無隱式狀態，測試友善（同 drift_monitor 慣例）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml

# 輸入消毒白名單（claimed hash / tag 入 subprocess 前必過，不合法即拒絕非靜默放行）
_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")
_TAG_RE = re.compile(r"^[\w][\w.\-/]{0,99}$")
# improving_NN.md 內嵌 ```yaml ... closure-evidence: ... ``` fenced block
_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


# ─────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────


@dataclass
class FactResult:
    kind: str          # "commit" | "tag"
    target: str        # 宣稱的 hash / tag
    status: str        # "PASS" | "FAIL"
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClaimResult:
    key: str           # "autoclaude_pytest_passed" | "ci_gate_floors" | ...
    claimed: object
    observed: object
    status: str        # "VERIFIED" | "INCONCLUSIVE" | "FAIL"
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClosureVerdict:
    iteration: object = None
    verdict: str = "INCONCLUSIVE"   # "VERIFIED" | "INCONCLUSIVE" | "FAIL"
    facts: List[FactResult] = field(default_factory=list)
    claims: List[ClaimResult] = field(default_factory=list)
    head_sha: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["facts"] = [f.to_dict() for f in self.facts]
        d["claims"] = [c.to_dict() for c in self.claims]
        return d


# ─────────────────────────────────────────────────────────────
# git helpers（list-form argv，shell=False，不可注入）
# ─────────────────────────────────────────────────────────────


def _run_git(args: List[str], repo_root: Path) -> "tuple[int, str]":
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        return 1, str(exc)


def repo_root_from(start: Optional[Path] = None) -> Path:
    """以 git toplevel 定位 monorepo 根（hook 在版本目錄但結案 commit 在根）。

    fallback：找不到 git 時回 start（或本檔 parents[2]＝版本目錄）。
    """
    base = start or Path(__file__).resolve().parents[2]
    rc, out = _run_git(["rev-parse", "--show-toplevel"], base)
    if rc == 0 and out:
        return Path(out)
    return base


# ─────────────────────────────────────────────────────────────
# 契約解析
# ─────────────────────────────────────────────────────────────


def parse_closure_evidence(md_text: str) -> Optional[dict]:
    """從 improving_NN.md 抽取 closure-evidence 契約 dict（無區塊回 None）。

    DEF-21-001：improving_NN.md 可同時含「schema 範例」（§4 說明）與「真實結案契約」
    （文件末尾）兩個 closure-evidence 區塊。取 **last-match**（真實契約慣例放末尾），
    對齊框架既有 last-match 紀律（DEF-02-002 tlc_runner parse_tlc_summary 用 findall[-1]）。
    """
    found: Optional[dict] = None
    for m in _FENCE_RE.finditer(md_text):
        try:
            data = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and "closure-evidence" in data:
            ev = data["closure-evidence"]
            if isinstance(ev, dict):
                found = ev  # 持續覆蓋 → 留最後一個
    return found


def find_latest_iteration_doc(repo_root: Path) -> Optional[Path]:
    """根層 docs/04_planning/AutoSDD_improving_NN.md 取最大 NN。"""
    d = repo_root / "docs" / "04_planning"
    if not d.exists():
        return None
    best: Optional[tuple] = None
    for p in d.glob("AutoSDD_improving_*.md"):
        mm = re.search(r"AutoSDD_improving_(\d+)\.md$", p.name)
        if mm:
            n = int(mm.group(1))
            if best is None or n > best[0]:
                best = (n, p)
    return best[1] if best else None


# ─────────────────────────────────────────────────────────────
# 廉價層：git 事實重推導（fail-closed）
# ─────────────────────────────────────────────────────────────


def verify_git_facts(evidence: dict, repo_root: Path) -> List[FactResult]:
    results: List[FactResult] = []
    for h in evidence.get("claimed_commits") or []:
        h = str(h).strip()
        if not _HASH_RE.match(h):
            results.append(FactResult("commit", h, "FAIL", "hash 不合法（白名單拒絕，疑造假/注入）"))
            continue
        rc, _ = _run_git(["cat-file", "-e", f"{h}^{{commit}}"], repo_root)
        if rc != 0:
            results.append(FactResult("commit", h, "FAIL", "commit 不存在於 repo（編造）"))
            continue
        rc2, _ = _run_git(["merge-base", "--is-ancestor", h, "HEAD"], repo_root)
        if rc2 != 0:
            results.append(FactResult("commit", h, "FAIL", "commit 非當前 HEAD 之祖先（不在歷史）"))
            continue
        results.append(FactResult("commit", h, "PASS", "存在且為 HEAD 祖先"))

    tag = evidence.get("claimed_tag")
    if tag:
        tag = str(tag).strip()
        if not _TAG_RE.match(tag):
            results.append(FactResult("tag", tag, "FAIL", "tag 名不合法（白名單拒絕）"))
        else:
            rc, _ = _run_git(["rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"], repo_root)
            results.append(
                FactResult("tag", tag, "PASS" if rc == 0 else "FAIL",
                           "tag 存在" if rc == 0 else "tag 不存在（編造）")
            )
    return results


# ─────────────────────────────────────────────────────────────
# 昂貴層：pytest passed / floors（不重跑，驗綁定 HEAD 的 rederive 證書）
# ─────────────────────────────────────────────────────────────

_EXPENSIVE_KEYS = ("autoclaude_pytest_passed", "ci_gate_floors", "lint_imports")


def _rederive_cert_path(repo_root: Path, head_sha: str) -> Path:
    return repo_root / "build" / "reports" / "closure" / f"REDERIVE-{head_sha[:12]}.yaml"


def verify_expensive_claims(evidence: dict, repo_root: Path) -> List[ClaimResult]:
    results: List[ClaimResult] = []
    rc, head = _run_git(["rev-parse", "HEAD"], repo_root)
    head = head if rc == 0 else ""
    base = str(evidence.get("base_sha") or "").strip()

    if not base or not head or base != head:
        for k in _EXPENSIVE_KEYS:
            if k in evidence:
                results.append(ClaimResult(k, evidence.get(k), None, "INCONCLUSIVE",
                                           f"契約 base_sha({base[:12]}) != HEAD({head[:12]})；證據過期，需 --rederive"))
        return results

    cert_path = _rederive_cert_path(repo_root, head)
    cert: Optional[dict] = None
    if cert_path.exists():
        try:
            cert = yaml.safe_load(cert_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            cert = None
    if not cert or str(cert.get("base_sha") or "") != head:
        for k in _EXPENSIVE_KEYS:
            if k in evidence:
                results.append(ClaimResult(k, evidence.get(k), None, "INCONCLUSIVE",
                                           "缺綁定 HEAD 的 rederive 證書（跑 closure_evidence.py --rederive 產生）"))
        return results

    observed = cert.get("observed") or {}
    for k in _EXPENSIVE_KEYS:
        if k not in evidence:
            continue
        claimed_v, obs_v = evidence.get(k), observed.get(k)
        if obs_v is None:
            results.append(ClaimResult(k, claimed_v, None, "INCONCLUSIVE", "證書未含該項實測"))
        elif claimed_v == obs_v:
            results.append(ClaimResult(k, claimed_v, obs_v, "VERIFIED", "契約宣稱 == 綁定 HEAD 之實測"))
        else:
            results.append(ClaimResult(k, claimed_v, obs_v, "FAIL", "契約宣稱 != 實測（數字造假/過期）"))
    return results


# ─────────────────────────────────────────────────────────────
# verdict 合成 + 持久化
# ─────────────────────────────────────────────────────────────


def synthesize_verdict(
    evidence: dict,
    facts: List[FactResult],
    claims: List[ClaimResult],
    head_sha: str = "",
) -> ClosureVerdict:
    if any(f.status == "FAIL" for f in facts) or any(c.status == "FAIL" for c in claims):
        verdict = "FAIL"
    elif any(c.status == "INCONCLUSIVE" for c in claims):
        verdict = "INCONCLUSIVE"
    elif facts or claims:
        verdict = "VERIFIED"
    else:
        verdict = "INCONCLUSIVE"
    return ClosureVerdict(
        iteration=evidence.get("iteration"),
        verdict=verdict,
        facts=facts,
        claims=claims,
        head_sha=head_sha,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def write_verdict_report(verdict: ClosureVerdict, repo_root: Path) -> Path:
    out_dir = repo_root / "build" / "reports" / "closure"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"VERDICT-{(verdict.head_sha or 'unknown')[:12]}.yaml"
    p.write_text(yaml.safe_dump(verdict.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def evaluate_closure(repo_root: Path, md_text: Optional[str] = None) -> ClosureVerdict:
    """端到端：解析契約 → 廉價層 git 事實 → 昂貴層 → 合成 verdict。"""
    if md_text is None:
        doc = find_latest_iteration_doc(repo_root)
        md_text = doc.read_text(encoding="utf-8", errors="ignore") if doc else ""
    evidence = parse_closure_evidence(md_text or "")
    rc, head = _run_git(["rev-parse", "HEAD"], repo_root)
    head = head if rc == 0 else ""
    if not evidence:
        return ClosureVerdict(verdict="INCONCLUSIVE", head_sha=head,
                              timestamp=datetime.now(timezone.utc).isoformat())
    facts = verify_git_facts(evidence, repo_root)
    claims = verify_expensive_claims(evidence, repo_root)
    return synthesize_verdict(evidence, facts, claims, head_sha=head)


def write_rederive_cert(repo_root: Path, observed: dict) -> Path:
    """--rederive：stamp 當前 HEAD + 實測數字，產生綁定 sha 的證書。"""
    rc, head = _run_git(["rev-parse", "HEAD"], repo_root)
    head = head if rc == 0 else "unknown"
    cert = {
        "base_sha": head,
        "observed": observed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    p = _rederive_cert_path(repo_root, head)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(cert, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────
# CLI 入口（顯式由人/CI 跑，非 hook budget 內；hook INCONCLUSIVE 訊息引導至此）
# ─────────────────────────────────────────────────────────────


def _main(argv: List[str], repo_root: Optional[Path] = None) -> int:
    """`--rederive --observed '<json>'` 由獨立驗證者就 repo 真實狀態跑出數字後 stamp 當前
    HEAD 落盤證書；無參數＝evaluate 最新 improving_NN.md 契約並印 verdict。
    repo_root 預設以 git toplevel 定位（測試可注入）。
    """
    if repo_root is None:
        repo_root = repo_root_from()
    if "--rederive" in argv:
        observed: dict = {}
        if "--observed" in argv:
            raw = argv[argv.index("--observed") + 1]
            try:
                observed = json.loads(raw)
            except (json.JSONDecodeError, IndexError):
                print("[closure] --observed 需合法 JSON，例：'{\"autoclaude_pytest_passed\":3112}'")
                return 2
        p = write_rederive_cert(repo_root, observed)
        print(f"[closure] rederive 證書已落盤（stamp 當前 HEAD）：{p}")
        return 0
    verdict = evaluate_closure(repo_root)
    print(f"[closure] verdict={verdict.verdict} head={verdict.head_sha[:12]}")
    for f in verdict.facts:
        print(f"  fact  {f.kind}:{f.target[:12]} {f.status} — {f.detail}")
    for c in verdict.claims:
        print(f"  claim {c.key} {c.status} — {c.detail}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
