"""每案副作用快照（L3；RealVerify_SideEffect_Isolation DES §6，REQ-SE-40～42）。

WHY：L1／L2 擋的是「已知的洩漏路徑」；新型外洩第一次出現時沒人知道要擋。快照只做一件事——案例前後各拍
一次真環境的各個面，差異裡**含本案沙盒字樣**（沙盒根／sid／slug／run_id）者＝外洩，案例判 fail。
不含字樣的差異（掌舵者真主控、`AutoSDD_OpenItem_OI-*`、真哨兵同時在跑）只記 note，不判（D-9）。
全部**唯讀**；`~/.claude.json` 只取 `projects` 鍵名（不讀值、不寫，REQ-SE-51）。
偏離 D-9 的一處（WHY）：per-case 字樣不含泛用前綴 `AutoSDD_RV_sbx_`——別的 realverify 視窗（如 OpenItem
驅動器）同時在跑時，它們的沙盒必然含泛用前綴，會把本案誤判為洩漏；本案**自己**的根／sid／slug／run_id
已足以抓到本案的洩漏（外洩物必含其一）。
"""  # noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import sandbox, sched

MAX_READ = 1_000_000  # 變動檔讀內容找字樣的上限（位元組）
AUTOSDD_FIRST_LEVEL = ("handoff", "handback", "plans", "traces/park", "traces/keepwarm", "traces/watch")  # noqa: E501
S10_DIRS = ("context_feed", "selfimproving")
QUOTA_CACHE_NAME = "autosdd_quota.json"  # 額度快取預設住家目錄根（`quota_meter.CACHE_NAME`；本檔不 import 產品碼）  # noqa: E501
PROC_NAMES = ("claude", "node")


@dataclass(frozen=True)
class Locations:
    """被快照的真位置（測試換成 tmp 假家目錄）。"""
    autosdd: Path
    claude: Path
    claude_json: Path
    home: Path

    @staticmethod
    def real() -> Locations:
        home = sandbox.real_home()
        return Locations(sandbox.real_autosdd(), sandbox.claude_home(), home / ".claude.json", home)


def _names(path: Path) -> list[str]:
    try:
        return sorted(p.name for p in path.iterdir())
    except OSError:
        return []


def _stat_rows(path: Path) -> dict[str, list]:
    out: dict[str, list] = {}
    try:
        for p in path.iterdir():
            if p.is_file():
                st = p.stat()
                out[p.name] = [st.st_mtime_ns, st.st_size]
    except OSError:
        pass
    return out


def _sessions(path: Path) -> dict[str, list]:
    out: dict[str, list] = {}
    try:
        files = sorted(path.glob("*.json"))
    except OSError:
        return out
    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        out[p.name] = [d.get("sessionId") or d.get("sid"), d.get("cwd")] if isinstance(d, dict) else [None, None]  # noqa: E501
    return out


def _claude_json_keys(path: Path) -> list[str]:
    try:
        projects = json.loads(path.read_text(encoding="utf-8")).get("projects") or {}
    except (OSError, ValueError, AttributeError):
        return []
    return sorted(str(k) for k in projects) if isinstance(projects, dict) else []


def _sched_and_procs() -> tuple[dict[str, str], list[list]]:
    """排程（`AutoSDD_*` 名稱＋Action）與行程（名稱 `claude*`／`node*` 的 pid＋命令列）。非 Windows 只取
    行程（排程面無載具＝空）；讀不到一律回空（快照是量測，不得因量不到而擋案例）。"""  # noqa: E501
    from . import leases_undo  # noqa: PLC0415
    try:
        procs = [[pid, cmd] for pid, name, cmd in leases_undo.list_procs()
                 if name.lower().startswith(PROC_NAMES)]
        return sched.list_actions("AutoSDD_*"), procs
    except Exception:  # noqa: BLE001
        return {}, []


def take(loc: Locations | None = None, *, sched_procs=None) -> dict:
    """拍一次快照（JSON 可序列化）。`sched_procs() -> (排程表, 行程列)` 是縫（測試注入）。"""
    loc = loc or Locations.real()
    rows, procs = (sched_procs or _sched_and_procs)()
    traces = loc.autosdd / "traces"
    s10: dict[str, dict] = {d: _stat_rows(loc.autosdd / d) for d in S10_DIRS}
    try:
        st = (loc.home / QUOTA_CACHE_NAME).stat()
        s10["quota_cache"] = {QUOTA_CACHE_NAME: [st.st_mtime_ns, st.st_size]}
    except OSError:
        s10["quota_cache"] = {}
    return {
        "sched": rows,
        "dirs": {d: _names(loc.autosdd / d) for d in AUTOSDD_FIRST_LEVEL},
        "s10": s10,
        "jsonl": {p.name: p.stat().st_size for p in sorted(traces.glob("*.jsonl"))} if traces.is_dir() else {},  # noqa: E501
        "projects": _names(loc.claude / "projects"),
        "sessions": _sessions(loc.claude / "sessions"),
        "claude_json": _claude_json_keys(loc.claude_json),
        "procs": procs,
        "_loc": [str(loc.autosdd), str(loc.claude), str(loc.claude_json), str(loc.home)],
    }


# ── diff ─────────────────────────────────────────────────────────────────────────────────

def _hit(text: str, tokens: list[str]) -> str:
    low = text.lower()
    return next((t for t in tokens if t and t.lower() in low), "")


def _read_text(path: Path, start: int = 0) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(start)
            return handle.read(MAX_READ).decode("utf-8", errors="replace")
    except OSError:
        return ""


def diff(before: dict, after: dict, tokens: list[str] | None = None) -> list[dict]:
    """差異清單 `[{face, item, change, token}]`；`token` 非空＝含本案字樣（洩漏）。無 `tokens`＝不判字樣
    （全列，token 一律空）。S10 與 traces jsonl 的字樣取自**現在磁碟上**的內容（新增或改動檔，≤1 MB）。"""  # noqa: E501
    toks = [t for t in (tokens or []) if t]
    loc = [Path(p) for p in (after.get("_loc") or before.get("_loc") or ["", "", "", ""])]
    out: list[dict] = []

    def add(face: str, item: str, change: str, text: str = "") -> None:
        out.append({"face": face, "item": item, "change": change,
                    "token": _hit(f"{item} {text}", toks) if toks else ""})

    for name, action in after["sched"].items():
        if name not in before["sched"]:
            add("sched", name, "added", action)
        elif before["sched"][name] != action:
            add("sched", name, "changed", action)
    for name in before["sched"]:
        if name not in after["sched"]:
            add("sched", name, "removed")
    for face in after["dirs"]:
        for name in sorted(set(after["dirs"][face]) - set(before["dirs"].get(face, []))):
            add(f"dir:{face}", name, "added")
    for face, rows in after["s10"].items():
        for name, sig in rows.items():
            if before["s10"].get(face, {}).get(name) != sig:
                base = loc[3] if face == "quota_cache" else loc[0] / face
                add(f"s10:{face}", name, "added" if name not in before["s10"].get(face, {}) else "changed",  # noqa: E501
                    _read_text(base / name))
    for name, size in after["jsonl"].items():
        old = before["jsonl"].get(name)
        if old is None or size != old:
            add("jsonl", name, "grew" if old is not None else "added", _read_text(loc[0] / "traces" / name, old or 0))  # noqa: E501
    for face in ("projects", "claude_json"):
        for name in sorted(set(after[face]) - set(before[face])):
            add(face, name, "added")
    for name, sig in after["sessions"].items():
        if before["sessions"].get(name) != sig:
            add("sessions", name, "added" if name not in before["sessions"] else "changed", " ".join(map(str, sig)))  # noqa: E501
    old_procs = {p[0] for p in before["procs"]}
    for pid, cmd in after["procs"]:
        if pid not in old_procs:
            add("procs", str(pid), "added", cmd)
    return out


def leaks(items: list[dict]) -> list[dict]:
    """洩漏＝含本案字樣的差異，或 `~/.claude.json` 新增鍵（一律，D-9／REQ-SE-41）。"""
    return [i for i in items if i["token"] or (i["face"] == "claude_json" and i["change"] == "added")]  # noqa: E501


def fmt(item: dict) -> str:
    tail = f"（字樣 {item['token']}）" if item["token"] else ""
    return f"{item['face']} {item['change']} {item['item']}{tail}"


def tokens_for(sandboxes, run_id: str) -> list[str]:
    """本案字樣：每個沙盒的根、家、根名、sid、slug＋run_id。見模組 docstring 對泛用前綴的取捨。"""
    out = [run_id]
    for sb in sandboxes:
        out += [str(sb.root), str(sb.home), Path(sb.home).name, sb.sid, sandbox.slug_of(sb.root),
                sandbox.slug_of(sb.home)]
    return list(dict.fromkeys(t for t in out if t))


def dump(snap: dict, path: Path | str) -> None:
    Path(path).write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")  # noqa: E501


def load(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_tokens(path: Path | str) -> list[str]:
    """`--tokens <檔>`：每行一個字樣（空行與 `#` 起頭略過）。"""
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
