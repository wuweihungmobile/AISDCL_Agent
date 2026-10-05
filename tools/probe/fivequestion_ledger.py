"""②′ 協定狀態與輪帳本（`audit_session.py --protocol-status` 的實作面）：只印不擋，rc 恆 0。

三件事：① 協定 manifest 雜湊＋輪帳本窗口評估；② 完整性閘（輪帳本最新一列對照缺陷帳本：該輪窗口內
P1／P2 的缺陷是否都登記在 `new_p_le2`／`excluded_p_le2`）；③ Q4′ 證據讀判（各台主機落在
`trace_dir()` 的 `session_gate_acceptance_*.json`，九格）。

🔴 邊界：量測器碼不入協定 manifest，判準常數一律住協定目錄的 `params.json`（改它＝改協定＝重置
窗口），本檔只讀 `prm`、不內建閾值。與 `audit_session.py` 同一條紀律：只能當量測器、不得接成閘門；
量不到（缺檔／缺鍵／git 失敗）一律印「量不到」，絕不印成通過。純函式與取數分開，供單元測試注入。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

#: 輪帳本列的選填欄（主控追加）：有就原樣印出，沒有不印（缺欄位不是錯）。
OPTIONAL_FIELDS = ("q1a", "q1b", "q1c", "q2", "q3", "q4_win", "q4_mac", "symptom_streak")
_DEFECT_LOG = "AutoSDD_Defect_Log.md"
_MARK = {True: "✓", False: "✗", None: "?"}


def manifest_sha(protocol_dir: Path) -> tuple[str, int]:
    """manifest＝每檔（相對路徑, sha256(CRLF 先正規化為 LF 的內容)）依路徑排序；
    回（整份雜湊, 檔數）。"""
    man = sorted((p.relative_to(protocol_dir).as_posix(),
                  hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
                 for p in protocol_dir.rglob("*") if p.is_file() and p.name[0] != ".")
    digest = hashlib.sha256(json.dumps(man, ensure_ascii=False).encode("utf-8")).hexdigest()
    return digest, len(man)


def window_len(rows: list[dict]) -> int:
    """窗口＝輪帳本尾端連續同 `protocol_sha256` 的列數，遇 `window_reset` 即止（該列計入）。"""
    run = 0
    for row in reversed(rows):
        if row["protocol_sha256"] != rows[-1]["protocol_sha256"]:
            break
        run += 1
        if row.get("window_reset"):
            break
    return run


def p12_defects(log_text: str) -> list[tuple[str, str]]:
    """缺陷帳本裡嚴重度 P1／P2 的列：`[(DEF 編號, 日期)]`。
    嚴重度以「某格恰為 P1／P2」認，不綁欄位位置。"""
    out = []
    for line in log_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if (len(cells) > 4 and re.fullmatch(r"DEF-\d+-\d+", cells[0])
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[1])
                and any(re.fullmatch(r"P[12]", c) for c in cells[2:])):
            out.append((cells[0], cells[1]))
    return out


def completeness_gap(rows: list[dict], log_text: str) -> list[str] | None:
    """最新一列的完整性閘：回「窗口內 P1／P2、卻沒登記」的 DEF 編號（空＝通過；`None`＝量不到）。

    窗口＝（上一列日期, 本列日期]；與上一列同日（含首列）時退為「同日、且前列都沒登記過」——日期
    解析度只有一天，同日多輪若只認開區間，後一輪的新缺陷會掉進空窗口。登記＝`new_p_le2`／`excluded_p_le2`。
    """
    if not rows or not rows[-1].get("date"):
        return None
    last, hi = rows[-1], rows[-1]["date"]
    lo = rows[-2].get("date") if len(rows) > 1 else None
    earlier = {d for r in rows[:-1] for d in (*r["new_p_le2"], *r["excluded_p_le2"])}
    mine = {*last["new_p_le2"], *last["excluded_p_le2"]}
    return sorted(d for d, day in p12_defects(log_text)
                  if day <= hi and (day > lo if lo and lo < hi else day == hi)
                  and d not in earlier and d not in mine)


def is_ancestor(repo_root: Path, sha: object) -> bool | None:
    """`git merge-base --is-ancestor <sha> HEAD`：rc 0＝True、1＝False；其餘（非 sha／無此 commit／
    git 失敗／逾時）＝None——量不到不是通過。"""
    if not (isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{7,40}", sha)):
        return None
    cmd = ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", sha, "HEAD"]
    try:
        rc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=20).returncode
    except (OSError, subprocess.SubprocessError):
        return None
    return {0: True, 1: False}.get(rc)


def q4_cells(doc: dict, now: datetime, ancestor: bool | None,
             max_age_days: float) -> dict[str, bool | None]:
    """丙案 JSON 的九格：True／False／None（量不到）。缺鍵、型別不符一律 None，絕不當通過。"""
    def at(*path: str) -> object:
        cur: object = doc
        for key in path:
            cur = cur.get(key) if isinstance(cur, dict) else None
        return cur

    def flag(*path: str) -> bool | None:
        value = at(*path)
        return value if isinstance(value, bool) else None

    plat, rc = at("platform"), at("check", "rc")
    try:
        stamp = datetime.fromisoformat(str(at("generated_at")))
        age = abs((now - stamp).total_seconds()) / 86400
    except (TypeError, ValueError):
        age = None
    return {
        "platform": plat in ("win32", "darwin") if isinstance(plat, str) else None,
        "statusline.installed": flag("statusline", "installed"),
        "statusline.matches_current_checkout": flag("statusline", "matches_current_checkout"),
        "hook_carrier.exists": flag("hook_carrier", "exists"),
        "verify_hint.default_push_location": flag("verify_hint", "default_push_location"),
        "verify_hint.default_lastexitcode": flag("verify_hint", "default_lastexitcode"),
        "check.rc==0": rc == 0 if isinstance(rc, int) and not isinstance(rc, bool) else None,
        f"generated_at<={max_age_days:g}d": None if age is None else age <= max_age_days,
        "repo_head_is_ancestor_of_HEAD": ancestor,
    }


def q4_lines(trace_dir: Path, now: datetime, ancestor: Callable[[object], bool | None],
             max_age_days: float) -> list[str]:
    """逐台主機的丙案 JSON 印九格判定（全 ✓＝PASS、任一 ✗＝FAIL、其餘＝量不到）。"""
    files = sorted(trace_dir.glob("session_gate_acceptance_*.json")) if trace_dir.is_dir() else []
    if not files:
        return [f"  Q4′ 證據：{trace_dir} 下無 session_gate_acceptance_*.json（量不到，不是 PASS）"]
    out = []
    for path in files:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            cells = q4_cells(doc, now, ancestor(doc.get("repo_head")), max_age_days)
        except (OSError, ValueError, AttributeError):
            out.append(f"  Q4′ {path.name}  讀不進（量不到，不是 PASS）")
            continue
        values = list(cells.values())
        state = ("PASS" if all(v is True for v in values) else "FAIL" if False in values
                 else f"NOT-EVALUABLE（{values.count(None)} 格量不到）")
        marks = " ".join(f"{k}{_MARK[v]}" for k, v in cells.items())
        out.append(f"  Q4′ {path.name}（{doc.get('platform')}）  {state}  {marks}")
    return out


_REPO = Path(__file__).resolve().parents[2]


def _default_trace_dir() -> Path:
    sys.path.insert(0, str(_REPO / "tools" / "lib"))
    import endurance_env  # noqa: PLC0415 — 延遲 import：只有本旗標才需要
    return endurance_env.trace_dir()


def protocol_status(prm: dict, protocol_dir: Path, ledger: Path, repo_root: Path, *,
                    trace_dir: Path | None = None, now: datetime | None = None,
                    ancestor: Callable[[object], bool | None] | None = None) -> int:
    """`--protocol-status` 本體：協定雜湊＋窗口評估＋選填欄＋完整性閘＋Q4′ 九格。rc 恆 0。"""
    sha, n_files = manifest_sha(protocol_dir)
    lines = ledger.read_text(encoding="utf-8").splitlines() if ledger.is_file() else []
    rows = [json.loads(ln) for ln in lines if ln.strip()]
    need, run = prm["rounds_required"], window_len(rows)
    ok = (run >= need and sum(len(r["new_p_le2"]) for r in rows[-need:]) <= 2
          and sum(r["p1"] for r in rows[-need:]) == 0 and not rows[-1]["new_p_le2"])
    verdict = ("PROTOCOL-CHANGED（需新列帶 window_reset:true＋理由）"
               if rows and rows[-1]["protocol_sha256"] != sha
               else f"NOT-EVALUABLE({run}/{need})" if run < need else "PASS" if ok else "FAIL")
    print(f"### ②′ 協定狀態\n  protocol_sha256={sha}（manifest {n_files} 檔）")
    print(f"  輪帳本 {len(rows)} 列；window_len={run}；評估: {verdict}")
    print("  （評估僅含家族計數與 p1；Q1′～Q4′ 不在內，見 --five-question 與下列各行）")
    win = rows[-run:] if run else []  # 純加印（ARCH-196-04）：不參與上面的判定
    n_new, n_exc = (sum(len(r[k]) for r in win) for k in ("new_p_le2", "excluded_p_le2"))
    print(f"  窗口內登記 raw={n_new + n_exc}（new {n_new}＋excluded {n_exc}）｜"
          f"公式可見={n_new}（excluded 不入評估式；raw>可見＝有 P≤2 以排除承擔，"
          "查 excluded_reason／window_reset）")
    for row in rows:
        extra = {k: row[k] for k in OPTIONAL_FIELDS if k in row}
        if extra:
            shown = json.dumps(extra, ensure_ascii=False)
            print(f"  輪帳本 round={row.get('round')} 選填欄 {shown}")
    log = ledger.parent / _DEFECT_LOG
    gap = completeness_gap(rows, log.read_text(encoding="utf-8")) if log.is_file() else None
    print("  完整性閘 " + ("?（量不到：缺輪帳本／缺陷帳本，或最新列缺 date）" if gap is None
                          else "✓" if not gap else f"✗ 漏列：{', '.join(gap)}"))
    try:
        tdir = trace_dir if trace_dir is not None else _default_trace_dir()
    except Exception as exc:  # noqa: BLE001 — 量測器 fail-open：取不到＝量不到，不崩潰
        print(f"  Q4′ 證據：trace_dir 取不到（{type(exc).__name__}）（量不到，不是 PASS）")
        return 0
    check = ancestor or (lambda sha_: is_ancestor(repo_root, sha_))
    for text in q4_lines(tdir, now or datetime.now().astimezone(), check, prm["q4_max_age_days"]):
        print(text)
    return 0
