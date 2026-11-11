"""SelfImproving M 類（記憶）提案的記憶目錄解析與後像驗證（TCS-SelfImproving-P7 AC-SI-48-1、48-2、
48-4；PRD FR-SI-48）。

能力類別 `ro`：只讀記憶目錄與帳本，不寫任何檔。解析式與 SOP〈M 類旗標〉同式——
`transcript.transcript_dir(repo) / "memory"`（不自寫 slug 規則）；須為目錄且含 `MEMORY.md`。
`pending` 判「該 M 類提案本心跳是否有待 `sandbox`／`verify`／`promote`／`rollback` 的步驟」，
使已晉升、量測中、已關且無待回滾的 M 類不被解析（D-IMP-9 (d)）。
後像＝promote／rollback 成功後以同一 manifest 式重算記憶目錄並比對該 `app.*` 事件的
`post_sha256`；只回碼，不回滾（回滾是人的決定）。
"""

from __future__ import annotations

from pathlib import Path

from . import events as si_events
from . import manifest, transcript
from . import paths as si_paths

UNRESOLVED = "MEMORY-DIR-UNRESOLVED"
POSTIMAGE = "POSTIMAGE-MISMATCH"
_POST = ("promoted", "measuring", "closed")


def target(repo: Path) -> str:
    """記憶目錄的預期路徑（不檢查存在；供原因碼的細節顯示）。"""
    return str(transcript.transcript_dir(repo) / "memory")


def resolve(repo: Path) -> str | None:
    """可用的記憶目錄路徑；不是目錄或沒有 `MEMORY.md` 一律回 None。"""
    path = Path(target(repo))
    return str(path) if path.is_dir() and (path / "MEMORY.md").is_file() else None


def pending(p) -> bool:
    """M 類提案是否有待推進、且需要記憶目錄的動詞步驟。"""
    return p.cls == "M" and (
        p.state in ("approved", "sandboxed")
        or (p.state == "verified" and p.pending_promote is not None)
        or (p.state in _POST and p.pending_rollbacks >= 1))


def post_image_problems(repo: Path, events: list[dict], pid: str, mem: str) -> str | None:
    """該 PROP 最近一筆 `app.promote`／`app.rollback` 的 `post_sha256` 對記憶目錄現況：相符回
    None，不符（或量不到，fail-closed）回 `POSTIMAGE-MISMATCH`。"""
    app = next((e for e in reversed(events)
                if e["kind"] in ("app.promote", "app.rollback") and e.get("prop") == pid), None)
    if app is None:
        return POSTIMAGE
    try:
        patch = repo / si_events.PROPOSALS_REL / pid / f"r{app['rev']}.patch"
        touched = si_paths.touched_of(patch.read_bytes())
        now = manifest.paths_manifest(Path(mem), touched, strip="memory/")
    except OSError:
        return POSTIMAGE
    return None if now == app["post_sha256"] else POSTIMAGE
