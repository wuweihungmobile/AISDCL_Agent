"""SelfImproving 反事實回測的案例庫：常數、案例產生純函式、抽樣、批次讀取（FR-SI-46；P6）。

能力類別 `ro`：只讀兩份帳本與 git 歷史（git 事實一律經 `git.py` 的 `Git`），不寫任何檔；寫檔在
`btwrite.py`。案例＝已修好缺陷的「修復前快照」資料：症狀取自帳本指定欄、`changed_files` 取自修復
commit 的程式檔。確定性：同一帳本與同一 git 歷史重跑產生的 `cases[]` 位元組相同（AC-SI-46-1）。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from . import defs
from . import events as si_events
from . import refs, rows
from .git import Git

BT_DIR_REL = "docs/06_quality/SelfImproving_Backtest"
RESULTS_REL = BT_DIR_REL + "/results.jsonl"
SOP_REL = "docs/05_development/SelfImproving_Operations_SOP.md"
BT_FILES_MAX = 8
BT_K_DEFAULT = 5
BT_K_MAX = 10
BT_TOP = 5
BT_BUDGET = "至多 40 次工具呼叫、至多 15 分鐘牆鐘"
CODE_EXT = (".py", ".java", ".kt", ".ts", ".tsx", ".js", ".mjs", ".ps1", ".sh", ".sql", ".yml",
            ".yaml", ".gradle", ".kts")
EXCLUDE_REASONS = ("commit-missing", "merge", "no-code-file", "files-over", "symptom-empty",
                   "symptom-has-sha", "symptom-names-file")
CASE_KEYS = ("id", "source", "symptom", "fix_commit", "pre_commit", "changed_files")
PLACEHOLDERS = ("SNAP_ROOT", "CASE", "SYMPTOM", "NONCE", "TOP_N", "BUDGET")
CASES_RE = re.compile(r"^cases-v(\d+)\.json$")
BATCH_RE = re.compile(r"^BT-\d{3,6}$")
SLOT_RE = re.compile(r"^s(\d{1,2})$")
_FIXED_RE = re.compile(r"fixed@([0-9a-f]{7,40})")
_FULL_RE = re.compile(r"^[0-9a-f]{40}$")
_FENCE_RE = re.compile(r"^```[a-z]*[ \t]*$", re.MULTILINE)
_QUALITY = "docs/06_quality"
_LS_CHUNK = 50


class BtError(Exception):
    """回測動詞的拒收；`codes`＝[(碼, 說明), …]。"""

    def __init__(self, codes: list[tuple[str, str]]) -> None:
        super().__init__(", ".join(c for c, _ in codes))
        self.codes = codes


def now_iso() -> str:
    """帶 offset 的現在時刻（秒精度）；時鐘縫：測試以 `mock.patch.object` 換掉。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha_of(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def dumps(obj) -> str:
    """案例檔與批次檔的正規化序列化（縮排 2、鍵排序、非 ASCII 原樣、結尾一個 LF）。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def cases_dir(repo: Path) -> Path:
    return repo / BT_DIR_REL


def cases_path(repo: Path, version: int) -> Path:
    return cases_dir(repo) / f"cases-v{version}.json"


def versions(repo: Path) -> list[int]:
    d = cases_dir(repo)
    found = [int(m.group(1)) for p in d.glob("cases-v*.json") if (m := CASES_RE.match(p.name))
             ] if d.is_dir() else []
    return sorted(found)


def latest(repo: Path) -> tuple[int, Path] | None:
    vs = versions(repo)
    return (vs[-1], cases_path(repo, vs[-1])) if vs else None


def _ledger_files(repo: Path, names: list[str], glob: str, sisters: tuple[str, ...] = ()
                  ) -> list[Path]:
    q = repo / _QUALITY
    files = [q / n for n in names] + (sorted(q.glob(glob)) if q.is_dir() else [])
    files += [q / n for n in sisters]
    return [p for p in files if p.is_file()]


def obs_files(repo: Path) -> list[Path]:
    return _ledger_files(repo, ["SelfImproving_Observation_Ledger.md"],
                         "SelfImproving_Observation_Ledger_archive*.md")


def def_files(repo: Path) -> list[Path]:
    return _ledger_files(repo, [], "AutoSDD_Defect_Log*.md",
                         ("AutoSDD_External_Blocked_Log.md", "AutoSDD_Structural_Debt_Log.md"))


def ledgers_sha(repo: Path) -> dict[str, str]:
    """兩帳本家族的位元組 `sha256`（依檔名序串接各檔位元組；缺檔家族＝空位元組的雜湊）。"""
    def fam(files: list[Path]) -> str:
        return sha_of(b"".join(p.read_bytes() for p in files))
    return {"obs_sha256": fam(obs_files(repo)), "def_sha256": fam(def_files(repo))}


def raw_candidates(repo: Path) -> list[tuple[str, str, str, str]]:
    """（id, source, symptom, 修復 sha）：OBS 處置首詞為 `fixed@<sha>` 的列（症狀欄）與缺陷帳本
    狀態欄含 `fixed@<sha>` 的列（「現象與證據」欄；欄數與表頭不符的列略過；同號後列覆寫前列）。"""
    out: list[tuple[str, str, str, str]] = []
    for ident, row in sorted(refs.obs_rows(repo).items()):
        tok = rows.disp_token(row.cells[7])
        if tok and rows.FIXED_SHA_RE.match(tok):
            out.append((ident, "OBS", row.cells[3].replace("\\|", "|"), tok[len("fixed@"):]))
    by_def: dict[str, defs.DefRow] = {}
    for f in def_files(repo):
        by_def.update({r.ident: r for r in defs.load_rows(f) if r.arity_ok})
    for ident, r in sorted(by_def.items()):
        m = _FIXED_RE.search(r.status_text)
        if m:
            out.append((ident, "DEF", r.evidence.replace("\\|", "|"), m.group(1)))
    return out


def is_code_file(path: str) -> bool:
    low = path.replace("\\", "/").casefold()
    if not low.endswith(CODE_EXT) or low.startswith("docs/"):
        return False
    wrapped = "/" + low
    return not any(s in wrapped for s in ("/tests/", "/test/", "tests_pg/"))


def _stdout(cp) -> str | None:
    return cp.stdout if cp is not None and cp.returncode == 0 else None


def _resolve(git: Git, sha: str) -> tuple[str, list[str]] | None:
    """修復 commit 的完整 40 碼與 parent 清單；不是 commit＝None。"""
    got = _stdout(git.run("rev-list", "--parents", "-n", "1", sha))
    parts = got.split() if got else []
    return (parts[0], parts[1:]) if parts and _FULL_RE.match(parts[0]) else None


def _existing(git: Git, commit: str, paths: list[str]) -> set[str] | None:
    """`paths` 中存在於 `commit` 的樹者；git 不可用＝None。"""
    found: set[str] = set()
    for i in range(0, len(paths), _LS_CHUNK):
        got = _stdout(git.run("-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", "-z",
                              commit, "--", *paths[i:i + _LS_CHUNK]))
        if got is None:
            return None
        found |= {n for n in got.split("\0") if n}
    return found


def _changed_code_files(git: Git, fix: str, pre: str) -> list[str] | None:
    got = _stdout(git.run("-c", "core.quotepath=false", "show", "--name-only", "--format=", "-z",
                          fix))
    if got is None:
        return None
    code = sorted({n for n in got.split("\0") if n and is_code_file(n)})
    kept = _existing(git, pre, code) if code else set()
    return None if kept is None else sorted(kept)


def _case(git: Git, ident: str, source: str, symptom: str, sha: str):
    """回（案例 dict, None）或（None, 排除原因）；原因判定順序＝`EXCLUDE_REASONS`。"""
    got = _resolve(git, sha)
    if got is None:
        return None, "commit-missing"
    fix, parents = got
    if not parents:  # 根 commit 沒有 first parent：無從還原修復前快照（規格封閉集合內最貼近者）
        return None, "commit-missing"
    if len(parents) > 1:
        return None, "merge"
    files = _changed_code_files(git, fix, parents[0])
    if not files:
        return None, "no-code-file"
    if len(files) > BT_FILES_MAX:
        return None, "files-over"
    text = symptom.strip()
    if not text:
        return None, "symptom-empty"
    if fix[:7] in text.casefold():
        return None, "symptom-has-sha"
    flat = text.replace("\\", "/")
    if any(f in text or f in flat for f in files):
        return None, "symptom-names-file"
    return {"id": ident, "source": source, "symptom": text, "fix_commit": fix,
            "pre_commit": parents[0], "changed_files": files}, None


def build(repo: Path, git: Git) -> dict:
    """案例產生（唯讀）：回 `{cases, excluded, ledgers}`；`cases`／`excluded` 依 `id` 位元組序。"""
    cases, excluded = [], []
    for ident, source, symptom, sha in raw_candidates(repo):
        case, why = _case(git, ident, source, symptom, sha)
        if case is not None:
            cases.append(case)
        else:
            excluded.append({"id": ident, "reason": why})
    key = lambda d: d["id"].encode("utf-8")  # noqa: E731
    return {"cases": sorted(cases, key=key), "excluded": sorted(excluded, key=key),
            "ledgers": ledgers_sha(repo)}


def file_object(version: int, generated_at: str, head_sha: str, built: dict) -> dict:
    return {"schema_rev": 1, "version": version, "generated_at": generated_at,
            "head_sha": head_sha, **built}


def load(path: Path) -> tuple[dict | None, bytes]:
    """案例檔（解析後物件或 None, 原位元組）；讀不到＝（None, b""）。"""
    try:
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None, b""
    return (obj if isinstance(obj, dict) else None), raw


def format_problems(raw: bytes, obj: dict | None) -> list[tuple[str, str]]:
    """位元組須等於其正規化序列化、頂層與案例鍵集合齊全（`prepare` 與 `cases --check` 共用）。"""
    if obj is None:
        return [("BT-CASES-FORMAT", "案例檔不是 UTF-8 JSON 物件")]
    out: list[tuple[str, str]] = []
    if raw != dumps(obj).encode("utf-8"):
        out.append(("BT-CASES-FORMAT", "位元組不等於正規化序列化"))
    top = {"schema_rev", "version", "generated_at", "head_sha", "ledgers", "cases", "excluded"}
    if set(obj) != top or not isinstance(obj.get("cases"), list):
        return out + [("BT-CASES-FORMAT", "頂層鍵集合不符")]
    if any(not isinstance(c, dict) or set(c) != set(CASE_KEYS) for c in obj["cases"]):
        out.append(("BT-CASES-FORMAT", "案例鍵集合不符"))
    return out


def check_problems(raw: bytes, obj: dict | None, git: Git) -> list[tuple[str, str]]:
    """`cases --check`：格式（`format_problems`）加每案 `fix_commit`／`pre_commit` 可解析。"""
    out = format_problems(raw, obj)
    if out:
        return out
    for case in obj["cases"]:
        for k in ("fix_commit", "pre_commit"):
            val = case[k]
            if not (isinstance(val, str) and _FULL_RE.match(val) and git.is_commit(val)):
                out.append(("BT-CASES-FORMAT", f"{case['id']} 的 {k} 無法解析為 commit"))
    return out


def check_latest(repo: Path, git: Git) -> dict:
    """`cases --check`：最新案例檔通過 `check_problems` 時回摘要，否則拋 `BtError`。"""
    found = latest(repo)
    if found is None:
        raise BtError([("BT-CASES-MISSING", "沒有案例檔，先跑 backtest cases --build")])
    obj, raw = load(found[1])
    bad = check_problems(raw, obj, git)
    if bad:
        raise BtError(bad)
    return {"version": found[0], "cases": len(obj["cases"]), "excluded": len(obj["excluded"]),
            "sha256": sha_of(raw)}


def pick(cases: list[dict], seed: int, k: int) -> list[dict]:
    """可重現抽樣：`sha256(f"{seed}:{id}")` 十六進位升冪取前 `k`（不用亂數；跨平台同結果）。"""
    def rank(c: dict) -> str:
        return hashlib.sha256(f"{seed}:{c['id']}".encode()).hexdigest()
    return sorted(cases, key=rank)[:k]


def nonce_of(batch: str, case_id: str, seed: int) -> str:
    return hashlib.sha256(f"{batch}:{case_id}:{seed}".encode()).hexdigest()[:12]


def template_of(sop_text: str) -> str | None:
    """SOP〈反事實回測〉節標題之後的第一個程式碼圍欄內文；缺＝None。範本內文含 `## ` 標題，所以不以
    「下一個二級標題」截斷節（同 `patrolbrief.template_of`）；節順序（本節須在〈無人運轉任務書範本〉
    之前）由 SOP 判準守住。"""
    start = re.search(r"^## 反事實回測", sop_text.replace("\r\n", "\n"), re.MULTILINE)
    if start is None:
        return None
    rest = sop_text.replace("\r\n", "\n")[start.end():]
    marks = list(_FENCE_RE.finditer(rest))
    return rest[marks[0].end():marks[1].start()].strip("\n") + "\n" if len(marks) >= 2 else None


def render_task(template: str, values: dict[str, str]) -> str:
    """單趟占位符替換（症狀文字內即使含 `<NONCE>` 字面也不會被二次替換）。"""
    return re.sub(r"<([A-Z_]+)>", lambda m: values.get(m.group(1), m.group(0)), template)


def root_default() -> Path:
    return si_events.si_dir() / "backtest"


def batch_dir(root: Path | None, batch: str) -> Path:
    return (root or root_default()) / batch


def load_batch(root: Path | None, batch: str) -> dict:
    """`batch.json`；批號格式不符或檔不存在＝`BT-BATCH-UNKNOWN`。"""
    path = batch_dir(root, batch) / "batch.json"
    try:
        if not BATCH_RE.match(batch):
            raise ValueError(batch)
        obj = json.loads(path.read_bytes().decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError(batch)
        return obj
    except (OSError, ValueError) as exc:
        raise BtError([("BT-BATCH-UNKNOWN", f"找不到批次 {batch}（{path}）")]) from exc
