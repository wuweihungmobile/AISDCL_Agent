"""名冊的兩個「持久小狀態」：killed 通知的增量全掃（DEF-01）與殘局退役帳（REQ-WP-43）。

DES §7。判準與讀寫住這裡、`roster.py` 只呼叫（roster 的 LOC 已貼天花板）。
· killed 增量掃：擁有者主逐字稿動輒數十 MB，被 TaskStop 的代理其 `<status>killed</status>` 通知
  若被後續記錄擠出「尾端 256 KB」就漏判（真機 05d1b770 的 ab573c773ef06f035 擠到檔尾前 300 KB）。
  改成快取 `trace_dir()/roster/<owner>.killed.json`（`size`／`offset`／`ids`）：每次只讀 `offset`
  之後的新位元組、只解析含 `<task-notification>` 的行；檔案變小（被改寫）⇒ 從頭重掃。`offset` 只
  推進到最後一個換行，半截尾行留給下次（不會把寫到一半的通知吃掉）。
· 退役帳 `trace_dir()/roster/retired.jsonl`：殘局滿壽命寫一行、之後只顯示計數；**不刪任何逐字稿**。
讀取量（位元組）記在 `last_read_bytes`，供測試斷言「第二次只讀新增」。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import endurance_env

_KILLED_RE = re.compile(r"<task-id>([A-Za-z0-9_-]{1,80})</task-id>.{0,600}?<status>killed</status>",
                        re.DOTALL)
_MARK = b"<task-notification>"
last_read_bytes = 0  # 最近一次 `killed_ids` 實際讀進來的位元組數（測試用的量測面）


def _dir(write: bool) -> Path:
    base = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return base / "roster"


def _notification_text(rec: dict) -> str | None:
    """只認 harness 自己寫的記錄型別（`queue-operation` 的 `content`、`attachment` 的 `prompt`）；
    人貼的文字是 `user` 記錄，不算。"""
    kind, att = rec.get("type"), rec.get("attachment")
    text = (rec.get("content") if kind == "queue-operation" else
            att.get("prompt") if kind == "attachment" and isinstance(att, dict) else None)
    return text if isinstance(text, str) and text.startswith("<task-notification>") else None


def killed_ids(main: Path | None, owner: str) -> set[str]:
    """擁有者主逐字稿 `main` 內全部被 TaskStop 的代理 id（增量全掃；`main` 缺＝空集合）。"""
    global last_read_bytes  # noqa: PLW0603 — 測試量測面，見模組說明
    last_read_bytes = 0
    if main is None:
        return set()
    cache = _dir(False) / f"{owner}.killed.json"
    try:
        size = main.stat().st_size
    except OSError:
        return set()
    ids: set[str] = set()
    offset = 0
    try:
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if (saved.get("path") == str(main) and size >= int(saved["size"])
                and size >= int(saved["offset"])):  # 換檔或變小（被改寫）⇒ 重掃
            offset, ids = int(saved["offset"]), {str(i) for i in saved["ids"]}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        with main.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
    except OSError:
        return ids
    last_read_bytes = len(chunk)
    end = chunk.rfind(b"\n") + 1  # 只消化到最後一個換行；半截尾行下次再讀
    for line in chunk[:end].splitlines():
        if _MARK not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        text = _notification_text(rec) if isinstance(rec, dict) else None
        if text:
            ids.update(_KILLED_RE.findall(text))
    try:
        cache_dir = _dir(True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{owner}.killed.json").write_text(
            json.dumps({"path": str(main), "size": size, "offset": offset + end,
                        "ids": sorted(ids)}),
            encoding="utf-8", newline="\n")
    except OSError:
        pass  # 快取寫不進去只是下次多讀一點，不影響結果
    return ids


def retired_ids() -> set[str]:
    """退役帳內全部代理 id。"""
    found: set[str] = set()
    try:
        for line in (_dir(False) / "retired.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("id"):
                found.add(str(rec["id"]))
    except OSError:
        pass
    return found


def retire(agent_id: str, owner: str, last_at: str | None, now: datetime) -> None:
    """殘局滿壽命：寫一行退役帳（同一 id 只寫一次）。寫不進去不拋（退役是整理、不是判準）。"""
    if agent_id in retired_ids():
        return
    try:
        folder = _dir(True)
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "retired.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"event": "residue_retired", "id": agent_id, "owner_sid": owner,
                                     "last_at": last_at, "retired_at": now.isoformat()},
                                    ensure_ascii=False) + "\n")
    except OSError:
        pass
