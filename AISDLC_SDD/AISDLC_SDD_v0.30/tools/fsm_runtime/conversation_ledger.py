"""Conversation overhead estimator + ledger calibration (ACT-024, Phase E M2).

The pre/post hooks count tokens for file I/O (Read/Write/Edit/Bash), but the
real conversation context also carries:

- `cat -n` prefix on Read results (~8 chars per line)
- Bash stdout/stderr bytes (captured by post hook already)
- Tool-use / tool-result JSON overhead per exchange
- System reminders, additionalContext strings, assistant prose

This module provides:

1. `estimate_read_tokens(path)` — size + line-count-aware Read estimate
2. `estimate_bash_command_tokens(cmd)` — command-only pre estimate
3. `estimate_conversation_overhead(n)` — per-message JSON overhead
4. `merge_conversation_overhead_into_ledger()` — tick conversation cost into
   today's CONTEXT-LEDGER every N tool calls
5. `record_calibration_sample()` — persist estimated vs. observed delta so we
   can tune the multiplier over time

Design goals (per SDD_improving_Automation_04.md §ACT-024):

- < 10% drift on a full Stage (~50 tool calls)
- Never break on missing file / missing PyYAML (best-effort, silent fallback)

DEF-200-275 第四輪（2026-09-10）— 本檔的估算值自此**只是稽核／校準紀錄，零決策權**：
hook 的 gating 分子改讀逐字稿 API usage（`context_window.scan_transcript`）。本檔同輪修掉兩個
真實缺陷：
- 根因 A：pre/post hook 各自的 `_read_modify_write` 重寫整份 doc 時只留三鍵，丟掉
  `conversation_overhead.last_merge_entry_index` ⇒ 每次 PostToolUse 都從 0 重新合併全部
  entries（O(n²)，活帳本實測單筆 +30000 且每次 +300）。修法＝`append_ledger_entry()` 以既有
  doc 為底只更新三鍵、其餘鍵原樣保留；`merge_…` 對書籤缺失／非整數 rebaseline 到
  `len(entries)` 而不是 0。
- 根因 A-2（撕裂寫入）：所有寫入者共用同一個 `.tmp` 檔名，兩支並行 hook 的 `os.replace`
  會互相搬走對方半寫的檔 ⇒ 活帳本出現半截 `t: null` 行、後續 hook 全數 crash → fail-open。
  修法＝tmp 一律 pid 專屬（`.part.<pid>`）、merge 也進 advisory lock、`yaml` 解析失敗時把
  損毀檔 rotate 成 `.corrupt-<ts>.yaml` 重開新檔（保留現場、不吞例外）。

DEF-200-275 第五輪（2026-09-11，Dev-C 效能修復）— 根因 C（見 profiling）：帳本沒有上限，
`append_ledger_entry`／`merge_conversation_overhead_into_ledger` 各自對今日整份帳本做一次完整
read-modify-write；成本幾乎全部落在 PyYAML **純 Python** `safe_load`/`safe_dump` 解析/序列化
`entries` 列表（實測 400KB／1500 筆：safe_load 0.41s＋safe_dump 0.24s；cProfile 顯示 >95% 時間在
`yaml/scanner.py`／`yaml/composer.py`／`yaml/serializer.py` 的純 Python 逐 token 掃描），隨帳本增長
線性變慢、單次呼叫終究撞上 `sdd_hook_router.py` 的 8s child timeout（現場已多次收到
`[SDD-ROUTER][WARN] context_ledger_post.py 逾 8.0s 未回應`）。鎖等待與 merge 邏輯本身耗時可忽略
（同規模量測 <1ms）。修法＝改用 libyaml 綁定的 `yaml.CSafeLoader`/`yaml.CSafeDumper`（`_yaml_loader`/
`_yaml_dumper`；同規模量測 CSafeLoader 0.06s／CSafeDumper 0.05s，約 6~7 倍加速，1500 筆規模下單次
`append_ledger_entry` 從 0.66s 降到 <0.15s）——純粹換一個更快的實作，帳本檔案格式、鍵結構、
`entries`／`conversation_overhead` 語意完全不變（C dumper 輸出與純 Python dumper 逐位元組相同，
純 Python `yaml.safe_load` 仍可讀回 C dumper 寫出的檔案），對 `fsm_runtime.py:_reset_today_ledger`
這類直接呼叫 `_load_ledger_doc`/`_atomic_write_yaml` 的既有讀寫者零侵入。libyaml 不可用時
`getattr(yaml, "CSafeLoader", yaml.SafeLoader)` 退化回純 Python，正確性優先於速度。

同輪也清掉 router 砍 child 留下的孤兒 `.part.<pid>` 暫存檔（現場實測同目錄殘留 7 個、0～530KB
不等）：`cleanup_orphan_part_files()` 在 `append_ledger_entry` 啟動時清掉 mtime > 10 分鐘**且**來源
pid 已不存在（`os.kill(pid, 0)` 判活；Windows 語意不同，改用 `psutil.pid_exists()` 若可用、否則只依
mtime 保守跳過）的殘檔；仍在寫入中或剛砍不久的檔案一律留著，避免誤刪。
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

_CHARS_PER_TOKEN = 4
_CAT_N_PREFIX_CHARS = 8  # "NNNN\t" padded + margin
# Overhead per Claude message (tool_use + tool_result JSON wrappers, system reminders).
# Empirical midpoint of the 100~500-token band documented in §E-05.
_CONVERSATION_OVERHEAD_PER_MESSAGE = 300
_DEFAULT_MERGE_EVERY = 10
_ORPHAN_PART_AGE_SEC = 600.0  # 10 分鐘（見〈孤兒 .part 清理〉docstring）


def _yaml_loader():
    """libyaml 綁定的 C loader（約 6~7 倍於純 Python）；不可用時退化回 `SafeLoader`（正確性優先）。"""
    import yaml  # type: ignore

    return getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _yaml_dumper():
    """同上，dumper 版本。"""
    import yaml  # type: ignore

    return getattr(yaml, "CSafeDumper", yaml.SafeDumper)


def estimate_read_tokens(file_path: Optional[str]) -> int:
    """Return size + line-count-aware estimate for a Read call.

    Adds the cat -n prefix overhead (~8 chars per line). Falls back to the
    plain size/4 estimate if the file is unreadable.
    """
    if not file_path:
        return 0
    path = Path(file_path)
    try:
        if not path.exists() or not path.is_file():
            return 0
        size = path.stat().st_size
        try:
            with path.open("rb") as f:
                line_count = sum(1 for _ in f)
        except Exception:  # noqa: BLE001
            line_count = 0
        total_chars = size + line_count * _CAT_N_PREFIX_CHARS
        return max(1, total_chars // _CHARS_PER_TOKEN)
    except Exception:  # noqa: BLE001
        return 0


def estimate_bash_command_tokens(command: Optional[str]) -> int:
    """Pre-hook estimate for a Bash call — command text only.

    The post hook captures stdout/stderr size via tool_response.
    """
    if not command:
        return 0
    return max(1, len(command) // _CHARS_PER_TOKEN)


def estimate_conversation_overhead(message_count: int) -> int:
    """Per-message JSON / system-reminder overhead estimate.

    `message_count` = number of tool-use/tool-result pairs since last merge.
    """
    if message_count <= 0:
        return 0
    return int(message_count) * _CONVERSATION_OVERHEAD_PER_MESSAGE


def _ledger_path(ledger_dir: Path) -> Path:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    return ledger_dir / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"


_LOCK_TIMEOUT_SEC = 5.0


def _ledger_lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


@contextlib.contextmanager
def ledger_lock(ledger_dir: Path, *, timeout: float = _LOCK_TIMEOUT_SEC) -> Iterator[None]:
    """同一把 advisory lock 的公開入口——post hook 用它把 append＋merge 包在同一個臨界區。
    `file_lock` 不可 import 時退化為無鎖（與既有 hook 行為相同）；逾時原樣拋 `TimeoutError`
    讓呼叫端決定降級路徑。"""
    try:
        from tools.fsm_runtime.file_lock import file_lock  # type: ignore
    except Exception:  # noqa: BLE001
        yield
        return
    with file_lock(_ledger_lock_path(_ledger_path(ledger_dir)), timeout=timeout):
        yield


def _atomic_write_yaml(path: Path, doc: Dict[str, Any]) -> None:
    """pid 專屬暫存檔 + os.replace（A-2：並行 hook 共用同名 .tmp 會互相搬走對方半寫的檔）。
    刻意不用 `.tmp` 後綴：arch_fitness FF-3 把 `build/reports/fsm/*.tmp` 判為孤兒。
    第五輪：dumper 改用 `_yaml_dumper()`（libyaml C 綁定，格式與純 Python `safe_dump` 逐位元組相同）。"""
    import yaml  # type: ignore

    tmp = path.with_name(path.name + f".part.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            yaml.dump(doc, f, Dumper=_yaml_dumper(), allow_unicode=True, sort_keys=False)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _load_ledger_doc(path: Path) -> Dict[str, Any]:
    """讀今日帳本；解析失敗（A-2 撕裂寫入留下的半截行）⇒ rotate 成 `.corrupt-<UTC ts>.yaml`
    保留現場、stderr 一行、回空 doc 重開。回傳值保證是 dict。"""
    import yaml  # type: ignore

    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.load(f, Loader=_yaml_loader()) or {}
        if isinstance(doc, dict):
            return doc
        reason = f"top-level is {type(doc).__name__}, not mapping"
    except yaml.YAMLError as exc:
        reason = f"{type(exc).__name__}"
    except OSError:
        # G4（SD-R2-03，第 2 輪審查）：讀不到 ≠ 空帳本。此前回 `{}` 會讓寫入者拿空 doc `_atomic_write_yaml`
        # 整本覆寫（歷史／書籤／其餘鍵全滅，還回報成功）；Windows AV／索引器暫時持檔的 PermissionError 是
        # 本 repo 實證事件（file_lock.py R60 A-02）。原樣拋出，寫入者「該次不寫」；hook 端的帳本 I/O
        # 例外由 `append_ledger_entry`／`merge_*`／`_reset_today_ledger` 自己接住，永不到 main()。
        # 損毀（YAMLError／非 dict）才走下方 rotate 重開。
        raise
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    rotated = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
    try:
        os.replace(path, rotated)
        print(
            f"[SDD-CTX][LEDGER] 帳本損毀（{reason}），已改名保留：{rotated.name}；重開新帳本",
            file=sys.stderr,
        )
    except OSError:
        pass
    return {}


def _sidecar_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".append")


def _write_sidecar(path: Path, entry: Dict[str, Any]) -> None:
    """advisory lock 逾時的降級路徑：純追加寫 `.append` sidecar、**零取鎖**（下次 merge 折回主檔並
    持久化——G3：折回後即使未達 conv-overhead 門檻也寫檔，否則 unlink 掉的 sidecar 內容只活在記憶體）。

    WHY 獨立成函式（DEF-200-275 第四輪 F2，SD-01／ARCH-02）：post hook 在 `ledger_lock` 逾時（5s）後
    若退回 `append_ledger_entry()`，它會**再**取一次同一把鎖再等 5s ⇒ 最壞 10s > `sdd_hook_router.py`
    的 Pre/Post child timeout 8s ⇒ router 砍子行程、hook fail-open、稽核 entry 全丟（實測 10.07s）。
    降級路徑只准做這一件事。寫失敗吞掉：sidecar 是 best-effort，帳本零決策權。
    """
    try:
        import yaml  # type: ignore

        with _sidecar_path(path).open("a", encoding="utf-8") as f:
            yaml.dump([entry], f, Dumper=_yaml_dumper(), allow_unicode=True, sort_keys=False)
    except Exception:  # noqa: BLE001
        pass


def write_sidecar(ledger_dir: Path, entry: Dict[str, Any]) -> None:
    """hook 用的公開入口：`ledger_lock` 逾時後直接落 sidecar（不取鎖）。"""
    _write_sidecar(_ledger_path(ledger_dir), entry)


def _is_pid_alive(pid: int) -> bool:
    """判斷 `.part.<pid>` 的來源行程是否還活著。

    POSIX：`os.kill(pid, 0)` 不送訊號只查存在性——`ProcessLookupError`＝不存在（可清），
    `PermissionError`＝存在但無權限送訊號（仍算活著，不清，例如不同使用者的行程）。
    Windows：`os.kill` 語意不同（鐵律三），改用 `psutil.pid_exists()` 若可用；
    `psutil` 不可用時保守回傳 True（只靠呼叫端的 mtime 門檻兜底，寧可少清也不誤刪還在寫的檔）。
    """
    if sys.platform == "win32":
        try:
            import psutil  # type: ignore
        except Exception:  # noqa: BLE001
            return True
        try:
            return bool(psutil.pid_exists(pid))
        except Exception:  # noqa: BLE001
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def cleanup_orphan_part_files(ledger_dir: Path) -> int:
    """清掉本目錄下 mtime > 10 分鐘**且**來源 pid 已不存在的孤兒 `CONTEXT-LEDGER-*.yaml.part.<pid>`
    暫存檔（`sdd_hook_router.py` 砍 child 於 `_atomic_write_yaml` 寫到一半時留下）。回傳清掉的數量。

    判準刻意保守（兩個條件都要成立才清）：mtime 太新可能仍在寫入中；pid 還活著也可能仍在寫入中——
    只有「夠舊」+「來源行程已死」同時成立才能確定是孤兒。best-effort：任何錯誤吞掉、永不 raise
    （帳本零決策權，清理失敗不得影響正常寫入路徑）。
    """
    removed = 0
    try:
        if not ledger_dir.exists():
            return 0
        now = time.time()
        for p in ledger_dir.glob("CONTEXT-LEDGER-*.yaml.part.*"):
            try:
                pid = int(p.name.rsplit(".part.", 1)[-1])
            except ValueError:
                continue
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            if age <= _ORPHAN_PART_AGE_SEC:
                continue
            if _is_pid_alive(pid):
                continue
            try:
                p.unlink()
                removed += 1
            except FileNotFoundError:
                pass
            except OSError:
                pass
    except Exception:  # noqa: BLE001
        pass
    return removed


def _read_modify_write(path: Path, entry: Dict[str, Any]) -> int:
    """根因 A 的修法：以既有 doc 為底，只更新 date／cumulative_tokens／entries，其餘鍵
    （尤其 `conversation_overhead` 書籤）原樣保留。"""
    doc = _load_ledger_doc(path)
    entries = doc.get("entries") or []
    if not isinstance(entries, list):
        entries = []
    entries.append(entry)
    try:
        cumulative = int(doc.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0) or 0)
    except (TypeError, ValueError):
        cumulative = int(entry.get("tokens", 0) or 0)
    doc["date"] = _dt.date.today().isoformat()
    doc["cumulative_tokens"] = cumulative
    doc["entries"] = entries
    _atomic_write_yaml(path, doc)
    return cumulative


def append_ledger_entry(ledger_dir: Path, entry: Dict[str, Any], *, lock_held: bool = False) -> int:
    """追加一筆稽核 entry 到今日帳本，回新的 cumulative_tokens（估算值，僅稽核用）。

    合併自 pre/post 兩支 hook 各自的 `_append*`（此前逐字重複、且皆帶根因 A）。advisory lock
    逾時 ⇒ 降級寫 `.append` sidecar（下次 merge 折回主檔並持久化，見 `_merge_locked` G3）。
    `lock_held=True`＝呼叫端已持有 `ledger_lock()`，不重複取鎖。
    G4：帳本讀不到（OSError）⇒ 回 0、不寫、不 raise——讀不到 ≠ 空帳本，不得以空 doc 覆寫。

    寫入端啟動時順手清掉孤兒 `.part.<pid>`（見 `cleanup_orphan_part_files`）；best-effort，
    清理失敗不影響本次 append。
    """
    try:
        import yaml  # type: ignore  # noqa: F401
    except Exception:  # noqa: BLE001
        return 0
    try:
        cleanup_orphan_part_files(ledger_dir)
    except Exception:  # noqa: BLE001
        pass
    path = _ledger_path(ledger_dir)
    try:
        if lock_held:
            return _read_modify_write(path, entry)
        with ledger_lock(ledger_dir):
            return _read_modify_write(path, entry)
    except TimeoutError:  # 必須排在 OSError 前：TimeoutError 是 OSError 的子類
        _write_sidecar(path, entry)
        try:
            doc = _load_ledger_doc(path)
            return int(doc.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            return int(entry.get("tokens", 0) or 0)
    except OSError:
        # G4：讀不到／寫不進 ⇒ 該次不寫（帳本零決策權），不讓例外到 hook。
        return 0


def _merge_sidecar_if_present(path: Path, doc: Dict[str, Any]) -> int:
    """Fold a `.append` sidecar back into the main ledger document.

    QA Round-3 P2-07: when `file_lock` timed out during pre/post hook writes,
    entries are staged into `{ledger}.append` instead of the primary ledger.
    If we skip reconciliation, `last_merge_entry_index` counts only the
    primary's `entries`, which silently undercounts tool calls and
    over-merges conversation overhead on the next tick. This helper appends
    sidecar entries into ``doc['entries']`` and bumps cumulative tokens,
    then removes the sidecar. Returns the number of entries merged.
    """
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return 0
    sidecar = _sidecar_path(path)
    if not sidecar.exists():
        return 0
    merged = 0
    try:
        with sidecar.open("r", encoding="utf-8") as f:
            raw = yaml.load_all(f, Loader=_yaml_loader())
            for chunk in raw:
                if not chunk:
                    continue
                # Each YAML document in the sidecar is a list[dict] per
                # context_ledger_pre.py's degraded-fallback path.
                if isinstance(chunk, list):
                    for item in chunk:
                        if isinstance(item, dict):
                            doc.setdefault("entries", []).append(item)
                            doc["cumulative_tokens"] = int(doc.get("cumulative_tokens", 0)) + int(item.get("tokens", 0))
                            merged += 1
                elif isinstance(chunk, dict):
                    doc.setdefault("entries", []).append(chunk)
                    doc["cumulative_tokens"] = int(doc.get("cumulative_tokens", 0)) + int(chunk.get("tokens", 0))
                    merged += 1
    except Exception:  # noqa: BLE001 — sidecar is best-effort
        return merged
    if merged > 0:
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass
    return merged


def merge_conversation_overhead_into_ledger(
    ledger_dir: Path,
    *,
    merge_every: int = _DEFAULT_MERGE_EVERY,
    entries_per_call: int = 2,
    clock=None,
    lock_held: bool = False,
) -> Dict[str, Any]:
    """Tick conversation overhead into the daily ledger.

    Counts entries since last merge; translates them into tool calls using
    `entries_per_call` (default 2 — pre-hook + post-hook each append an entry,
    so 2 entries = 1 real tool call). When `delta_calls` reaches `merge_every`
    appends one `phase=conv-overhead` entry per tool call and bumps
    cumulative_tokens.

    P1-06 fix (§CLAUDE.md Rule 9.8.2): before this patch we merged every 10
    ledger *entries*, which was in fact every 5 tool calls — overcounting
    conversation overhead by 2×. The new `entries_per_call` parameter keeps
    the "every 10 tool calls" guarantee promised in Rule 9.8.2.

    DEF-200-275 第四輪：(1) 進同一把 advisory lock（此前無鎖的 read-modify-write 是 A-2 撕裂
    寫入的另一個站點；`lock_held=True` 表示呼叫端已持鎖）；(2) 書籤缺失／非整數 ⇒ **rebaseline**
    到 `len(entries)` 且本 tick 不合併——從 0 起算會把全部 entries 再合併一次（實測每次呼叫
    +30000、單調遞增）；帳本只是稽核紀錄，漏合併一 tick 的代價遠小於灌水。

    Returns a dict summarising action taken:
      {"merged": bool, "added_tokens": int, "cumulative": int}
    """
    try:
        import yaml  # type: ignore  # noqa: F401
    except Exception:  # noqa: BLE001
        return {"merged": False, "added_tokens": 0, "cumulative": 0}

    if entries_per_call < 1:
        entries_per_call = 1

    path = _ledger_path(ledger_dir)
    if not path.exists():
        return {"merged": False, "added_tokens": 0, "cumulative": 0}
    try:
        if lock_held:
            return _merge_locked(path, merge_every=merge_every, entries_per_call=entries_per_call, clock=clock)
        with ledger_lock(ledger_dir):
            return _merge_locked(path, merge_every=merge_every, entries_per_call=entries_per_call, clock=clock)
    except TimeoutError:  # 必須排在 OSError 前：TimeoutError 是 OSError 的子類
        return {"merged": False, "added_tokens": 0, "cumulative": 0, "lock_timeout": True}
    except OSError as exc:
        # G4：帳本讀不到 ⇒ 本 tick 不合併、不寫（不得以空 doc 覆寫），誠實回報。
        return {"merged": False, "added_tokens": 0, "cumulative": 0, "io_error": repr(exc)}


def _merge_locked(path: Path, *, merge_every: int, entries_per_call: int, clock) -> Dict[str, Any]:
    doc = _load_ledger_doc(path)
    # QA Round-3 P2-07: fold any pending sidecar (degraded-fallback writes
    # from pre/post hooks under lock contention) into the primary ledger
    # before computing delta_entries. Without this, entries stuck in the
    # sidecar would not count toward the 10-call conv-overhead tick and
    # we'd overmerge on the next cycle.
    sidecar_merged = _merge_sidecar_if_present(path, doc)
    entries = doc.get("entries") or []
    if not entries:
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0))}

    conv_meta = doc.get("conversation_overhead")
    if not isinstance(conv_meta, dict):
        conv_meta = {}
        doc["conversation_overhead"] = conv_meta
    raw_idx = conv_meta.get("last_merge_entry_index")
    # SD-05：負整數書籤（手改／壞寫入）與缺失同罪——`len(entries) - (-k)` 會多算 k 筆再灌水。
    bookmark_missing = isinstance(raw_idx, bool) or not isinstance(raw_idx, int) or raw_idx < 0
    if bookmark_missing and raw_idx is None and not any(
        isinstance(e, dict) and e.get("phase") == "conv-overhead" for e in entries
    ):
        # 全新帳本：從未合併過、也沒有任何 conv-overhead 列 ⇒ 書籤本來就不存在，從 0 起算
        # （既有語意）。「遺失」的判準是：帳本裡**已有** conv-overhead 列卻沒有書籤——那只可能是
        # 某個寫入者把鍵吃掉（根因 A 的形狀），此時才 rebaseline。
        raw_idx = 0
        bookmark_missing = False
    if bookmark_missing:
        # 書籤遺失／非整數：rebaseline 到 len(entries)，本 tick 不合併（WHY 見 docstring）。
        conv_meta["last_merge_entry_index"] = len(entries)
        conv_meta["rebaselined_at"] = (clock or (
            lambda: _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")))()
        doc["entries"] = entries
        _atomic_write_yaml(path, doc)
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0)),
                "rebaselined": True}
    last_merged_at_idx = raw_idx
    delta_entries = max(0, len(entries) - last_merged_at_idx)
    delta_calls = delta_entries // entries_per_call
    if delta_calls < merge_every:
        # G3（SD-R2-01，第 2 輪審查；HEAD 既有）：sidecar 已被 `_merge_sidecar_if_present` 併進記憶體 doc
        # 並 unlink，這裡早退若不寫檔，折回的 entries 就永久消失（預設門檻下 20 個 tick 只有 1 個真的持久化）。
        # 只在真的折回了東西才寫，避免每 tick 多一次寫入。
        if sidecar_merged:
            _atomic_write_yaml(path, doc)
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0)),
                "sidecar_merged": sidecar_merged}

    add = estimate_conversation_overhead(delta_calls)
    now_fn = clock or (lambda: _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))
    entries.append({
        "ts": now_fn(),
        "phase": "conv-overhead",
        "tool": "ConversationLedger",
        "target": None,
        "tokens": add,
        "messages_counted": delta_calls,
        "entries_counted": delta_entries,
    })
    doc["entries"] = entries
    cumulative = int(doc.get("cumulative_tokens", 0)) + add
    doc["cumulative_tokens"] = cumulative
    # Advance index by the *consumed* entry count, not raw len(entries), so
    # any tail entry that didn't form a complete pair carries over to the
    # next merge. The newly-appended conv-overhead entry is metadata only
    # and must not be counted as a real tool-call entry.
    conv_meta["last_merge_entry_index"] = last_merged_at_idx + delta_calls * entries_per_call
    conv_meta["last_merged_at"] = now_fn()
    conv_meta["total_conv_overhead_tokens"] = int(conv_meta.get("total_conv_overhead_tokens", 0)) + add

    _atomic_write_yaml(path, doc)
    return {
        "merged": True,
        "added_tokens": add,
        "cumulative": cumulative,
        "sidecar_merged": sidecar_merged,
    }


def record_calibration_sample(
    ledger_dir: Path,
    *,
    estimated: int,
    observed: int,
    source: str = "manual",
) -> Path:
    """Persist an estimated-vs-observed sample for drift analysis.

    Writes/updates `build/reports/fsm/LEDGER-CALIBRATION-{date}.yaml` with a
    running list of samples. Tests and future tuning scripts consume this.
    """
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return Path()

    ledger_dir.mkdir(parents=True, exist_ok=True)
    date = _dt.date.today().isoformat()
    path = ledger_dir / f"LEDGER-CALIBRATION-{date}.yaml"
    doc: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.load(f, Loader=_yaml_loader()) or {}
    samples = doc.get("samples") or []
    delta = observed - estimated
    drift_pct = (abs(delta) / observed * 100) if observed > 0 else 0.0
    samples.append({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "estimated": int(estimated),
        "observed": int(observed),
        "delta": int(delta),
        "drift_pct": round(drift_pct, 2),
        "source": source,
    })
    doc["samples"] = samples
    doc["date"] = date
    doc["latest_drift_pct"] = round(drift_pct, 2)
    # Rolling average of last 10 samples
    recent = samples[-10:]
    if recent:
        avg = sum(s.get("drift_pct", 0.0) for s in recent) / len(recent)
        doc["rolling_avg_drift_pct_last10"] = round(avg, 2)

    _atomic_write_yaml(path, doc)
    return path


def estimate_tool_tokens(tool: str, tool_input: Dict[str, Any]) -> int:
    """Unified entry used by context_ledger_pre.py after ACT-024.

    Delegates to the specific estimators above. Kept stateless; all calibration
    bookkeeping lives in the ledger file on disk.
    """
    try:
        if tool == "Read":
            return estimate_read_tokens(tool_input.get("file_path"))
        if tool in {"Write", "Edit"}:
            text = tool_input.get("content") or tool_input.get("new_string") or ""
            return max(1, len(text) // _CHARS_PER_TOKEN) if text else 0
        if tool == "Bash":
            return estimate_bash_command_tokens(tool_input.get("command"))
        if tool == "NotebookEdit":
            text = tool_input.get("new_source") or tool_input.get("content") or ""
            return max(1, len(text) // _CHARS_PER_TOKEN) if text else 0
        if tool == "Task":
            # Each Task spawns a subagent — count one conversation overhead unit
            # (subagent system prompt / tool registry / wrapper) on top of the
            # caller-visible prompt. Post hook adds agent output later.
            prompt = tool_input.get("prompt") or ""
            prompt_tokens = max(1, len(prompt) // _CHARS_PER_TOKEN) if prompt else 0
            return prompt_tokens + estimate_conversation_overhead(1)
    except Exception:  # noqa: BLE001
        return 0
    return 0
