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

DEF-200-275 第七輪 D31（Dev-W7，windows-compat-ci #220／#221 修復）— 根因（見鐵律三「Windows 檔案
鎖」列）：`_atomic_write_yaml` 的 `os.replace(tmp, path)` 在 Windows 上若另一行程正開著 `path`
讀（例如無鎖狀態下呼叫 `_load_ledger_doc(path)`，或 AV／索引器）會拋 `PermissionError`
（WinError 5／32）；此前這被 `append_ledger_entry` 的 `except OSError: return 0`（G4）吞掉、
該筆稽核 entry 靜默遺失（#220／#221 兩輪 CI 紅：`test_concurrent_writers_do_not_tear` 199≠200）。
修法三處：(1) `_atomic_write_yaml` 遇 `PermissionError` 時短退避重試（`_REPLACE_RETRY_ATTEMPTS`×
`_REPLACE_RETRY_INTERVAL_SEC`≈0.5s），重試耗盡才拋具名 `LedgerReplaceDenied`；(2)
`append_ledger_entry` 新增 `except LedgerReplaceDenied` 分支，與既有 `TimeoutError` 分支同型降級寫
`.append` sidecar（不再靜默丟）；(3) `_merge_sidecar_if_present` 先以 `os.replace` 把 sidecar
改名認領成 pid 專屬檔（`.append.merging.<pid>`）再讀取合併，讓「讀 sidecar → 合併 → unlink」這段
critical window 縮到只碰本行程獨占的認領檔——另一支 append 在認領後才 `open("a")` 只會建立全新
sidecar，不受影響，消除此前「讀取中被另一行程同時 append」的交錯遺失窗口。

DEF-200-275 第七輪 D31b（Dev-W7b，四方複審 REJECT D31 後再修；總架構師裁決，取代上一段 D31-1/-3）
——複審用真實檔案系統重現 D31 的認領改名（claim-rename）仍有兩個缺陷：C3（B 在 A 改名前已
`open("a")` 拿到 fd，A 完成 claim→read→merge→unlink 後 B 才寫入並 close，bytes 進了無目錄項的
inode，永久消失）、W-1（認領改名成功、`_atomic_write_yaml` 持久化前被砍＝孤兒認領檔，零清理
邏輯，比修前更糟）。根因是認領改名的本質仍是「共用可變檔」，只是把 critical window 從「讀取中
被 append」搬到「認領中被 unlink」。修法＝sidecar 徹底改成**每筆一檔、寫成即不可變**：
`_write_sidecar` 對 pid+時間戳+序號專屬暫存檔 `_replace_with_retry` 成同樣專屬的最終檔名
（`_sidecar_unique_suffix`），沒有任何行程會對同一個檔名重複開寫，C3 的 fd 窗口結構上消失；
`_merge_sidecar_if_present` 因此不再需要認領改名，只是「掃描目錄 → 逐檔讀 → 折進記憶體 doc」，
真正的持久化順序改成**先 `_atomic_write_yaml` 成功、才由 `_merge_locked` 呼叫
`_delete_sidecar_sources` 刪來源**——中途被砍最壞是「sidecar 檔還在，下次 tick 重讀」，W-1 的
「認領後被砍」情境隨認領步驟一起消失。這個新順序留下一個更窄的殘餘窗口：主檔已持久化、來源
還沒被刪就被砍 ⇒ 下次 tick 會重讀到同一個 sidecar 檔。用 `conversation_overhead.folded_sidecar_ids`
書籤（記錄 `f"{檔名}#{檔內序號}"`）擋下重複折算；書籤靠「對應來源檔是否還存在」自我裁剪，不會
無界成長。同輪也把 `_REPLACE_RETRY_*` 與 `file_lock.py` 的 `_UNLINK_RETRY_*` 一併下修（見各自
常數註解），並新增 `worst_case_ledger_budget_sec()` 顯式核對「取鎖等待 + 兩次 replace 重試 +
一次解鎖重試」的組合上界，不得逼近 `sdd_hook_router.py` 的 `HOOK_CHILD_TIMEOUT_SEC`（鏡射
`_CHILD_TIMEOUT["PostToolUse"]`；兩子專案不跨 import，一致性由測試斷言而非匯入依賴守住）——
這是 D31 遺留的另一個複審發現（W-2：四個常數分居三檔，無人把它們合起來斷言）。

DEF-200-275 第七輪 D31c（Dev-W7c，windows-compat-ci #220／#221 複審 REJECT D31b 後再修；總架構師
裁決 D31c）——並行鏡（C1～C6）已 APPROVE，Windows 鏡揪出 D31b `_write_sidecar` 自己新增的一個
W-4（P0）：`try: … finally: tmp.unlink()` 的 `finally` 不分青紅皂白清掉 tmp——但 D31b 把 sidecar
改成「每筆一檔」之後，這個 tmp **就是該筆 entry 的唯一副本**；`_replace_with_retry(tmp, final)`
重試耗盡拋 `LedgerReplaceDenied` 時，`finally` 在例外往外傳之前已經把這份合法完整的 tmp 刪掉
⇒ 整筆稽核 entry 無聲消失、連殘檔都不留（比 D31b 修復前的「認領中被砍」還乾淨地丟資料）。
修法＝**只在成功路徑或「dump 本身尚未成功」時才清 tmp**：
- `yaml.dump` 寫入 tmp 失敗 ⇒ tmp 內容不是合法唯一副本（可能是空檔／半寫），照舊清掉。
- `_replace_with_retry` 成功 ⇒ tmp 已被 `os.replace` 搬到 `final`，原路徑本來就不存在，無需
  （也不能）再 unlink。
- `_replace_with_retry` 拋 `LedgerReplaceDenied` ⇒ **保留 tmp**，直接 return——不重試、不吞掉
  內容。這份 `.append.part.<suffix>` 殘留檔改由 `_iter_sidecar_sources` 在下一次 merge tick
  當一般 sidecar 來源折回（見該函式對 `.append.part.*` 的「來源 pid 已死、或 mtime 超過
  `_SIDECAR_PART_FOLD_AGE_SEC` 秒」判準——只有兩者之一成立才折，避免把另一行程正在寫入中的
  半成品當完整檔讀取，那會讀到截斷的 YAML）。

連帶修正 `cleanup_orphan_part_files`：此前對 `.append.part.*` 沿用「mtime 夠舊 + pid 已死即
unlink」的孤兒清理，在 W-4 修復後會變成**主動刪掉本該被折回的合法殘留副本**——两種孤兒的正確
歸宿不同：主檔／calibration 的 `.yaml.part.<pid>` 是**整本快照**（`_atomic_write_yaml` 的中途
產物），砍掉的行程留下的半寫檔案本來就該丟，下次寫入者會重新從主檔讀起，不會遺失任何 entry；
sidecar 的 `.append.part.<pid>.<ns>.<seq>` 卻是某一筆 entry 的**唯一副本**，需要交給
`_merge_sidecar_if_present` 讀出內容折回主檔（而非直接刪除，那等於資料遺失）。修法＝
`cleanup_orphan_part_files` 起單一收斂到只掃 `.yaml.part.*`，不再掃 `.append.part.*`——後者
一律不主動刪除，交由 merge 路徑處理。

`_merge_sidecar_if_present` 折回 `.append.part.*` 時若 YAML 解析失敗（半成品：另一行程尚未寫完
就被判定為「夠舊」，或磁碟本身損毀），與既有「損毀 sidecar 跳過不刪」的處置一致（見該函式既有
邏輯），額外印一行 ASCII stderr 警告（本檔含 hook 可能透過的入口點路徑，非 ASCII 字元在部分
locale 下會導致 print 本身 crash——鐵律三，故警告訊息刻意純英文）。

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
import itertools
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

_CHARS_PER_TOKEN = 4
_CAT_N_PREFIX_CHARS = 8  # "NNNN\t" padded + margin
# Overhead per Claude message (tool_use + tool_result JSON wrappers, system reminders).
# Empirical midpoint of the 100~500-token band documented in §E-05.
_CONVERSATION_OVERHEAD_PER_MESSAGE = 300
_DEFAULT_MERGE_EVERY = 10
_ORPHAN_PART_AGE_SEC = 600.0  # 10 分鐘（見〈孤兒 .part 清理〉docstring）
# D31-1 原訂 25 次 × 20ms ≈ 0.5s，係單獨對照 windows-compat-ci #220／#221 實測的瞬時
# PermissionError（WinError 5／32，另一行程短暫開著 path 讀／AV／索引器）訂的，未與
# file_lock.py 的解鎖重試、`_LOCK_TIMEOUT_SEC` 取鎖逾時合起來對照 router 的 8s child timeout——
# D31b-3（複審 W-2）：三者最壞情況疊加逼近 6s+，只剩不到 2s 給 stdin／measure。下修為
# 10 次 × 20ms ≈ 0.2s：仍覆蓋現場實測的毫秒級瞬時佔用，代價是理論上更長的持有窗口不會再被
# 蓋過——該殘餘風險由 `append_ledger_entry` 的降級寫 sidecar 路徑兜底（零遺失，只是慢一拍才
# 持久化），故縮短重試預算不等於縮短資料保護。見 `worst_case_ledger_budget_sec()`。
_REPLACE_RETRY_ATTEMPTS = 10
_REPLACE_RETRY_INTERVAL_SEC = 0.02
_REPLACE_RETRY_BUDGET_SEC = _REPLACE_RETRY_ATTEMPTS * _REPLACE_RETRY_INTERVAL_SEC

# D31b-3：鏡射 `.claude/hooks/sdd_hook_router.py` 的 `_CHILD_TIMEOUT["PostToolUse"]`。兩子專案
# 刻意不跨 import（AISDLC_SDD 與根層護欄層是獨立部署面），故用常數鏡射；一致性不靠匯入依賴，
# 而是靠 `worst_case_ledger_budget_sec()` 的呼叫端測試斷言（見 test_conversation_ledger.py）。
# post hook 在同一個 `ledger_lock` 臨界區內做 append + merge，各自最壞情況重試耗盡一次
# `_replace_with_retry`；這個天花板就是 router 砍掉子行程、hook fail-open 的那條線。
HOOK_CHILD_TIMEOUT_SEC = 8.0


class LedgerReplaceDenied(OSError):
    """`_atomic_write_yaml` 的 `os.replace` 在重試預算內仍被拒絕存取（D31-1）。

    刻意繼承 `OSError`（而非獨立基底）：既有的 `merge_conversation_overhead_into_ledger` 的
    `except OSError as exc: return {..., "io_error": repr(exc)}` 分支無需改動即可正確接住並回報，
    只有 `append_ledger_entry` 需要區分出這個子類、走 sidecar 降級而非靜默回 0（見 D31-2）。
    """


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


def _replace_with_retry(tmp: Path, path: Path) -> None:
    """D31-1：`os.replace` 遇 `PermissionError` 短退避重試 `_REPLACE_RETRY_ATTEMPTS` 次
    （windows-compat-ci #220／#221 實測 WinError 5／32，見鐵律三「Windows 檔案鎖」列）；
    重試耗盡仍失敗 ⇒ 拋 `LedgerReplaceDenied`，交由呼叫端決定降級路徑（不得吞掉靜默丟資料）。"""
    last_exc: Optional[OSError] = None
    for attempt in range(_REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:
            last_exc = exc
            if attempt + 1 < _REPLACE_RETRY_ATTEMPTS:
                time.sleep(_REPLACE_RETRY_INTERVAL_SEC)
    raise LedgerReplaceDenied(
        f"os.replace 對 {path.name} 的覆寫在 {_REPLACE_RETRY_ATTEMPTS} 次重試"
        f"（約 {_REPLACE_RETRY_ATTEMPTS * _REPLACE_RETRY_INTERVAL_SEC:.2g}s）後仍被拒絕存取"
    ) from last_exc


def worst_case_ledger_budget_sec() -> float:
    """D31b-3（解 W-2）：post hook 在同一個 `ledger_lock()` 臨界區內做 append + merge，最壞情況＝
    取鎖等待滿 `_LOCK_TIMEOUT_SEC` ＋兩次（append 一次、merge 一次）重試耗盡的 `_replace_with_retry`
    ＋離開臨界區時 `file_lock.py` 的一次 `_try_unlink` 重試耗盡。這個組合上界必須留給
    `sdd_hook_router.py` 的 `HOOK_CHILD_TIMEOUT_SEC` 足夠餘裕（見呼叫端測試斷言），否則重試預算
    本身就會把 hook 逼近被 router 砍掉子行程的那條線——W-2 正是「四個常數分居三檔，無人合起來
    斷言」的複審發現。`file_lock` 不可 import 時退化用 D31-4 定的預算常數估計（0.1s），與該模組
    docstring 的設計意圖一致，不影響本函式在無鎖環境（如某些單元測試）下仍可呼叫。"""
    try:
        from tools.fsm_runtime.file_lock import (  # type: ignore
            _UNLINK_RETRY_ATTEMPTS,
            _UNLINK_RETRY_INTERVAL_SEC,
        )

        unlink_budget = _UNLINK_RETRY_ATTEMPTS * _UNLINK_RETRY_INTERVAL_SEC
    except Exception:  # noqa: BLE001
        unlink_budget = 0.1
    return _LOCK_TIMEOUT_SEC + 2 * _REPLACE_RETRY_BUDGET_SEC + unlink_budget


def _atomic_write_yaml(path: Path, doc: Dict[str, Any]) -> None:
    """pid 專屬暫存檔 + os.replace（A-2：並行 hook 共用同名 .tmp 會互相搬走對方半寫的檔）。
    刻意不用 `.tmp` 後綴：arch_fitness FF-3 把 `build/reports/fsm/*.tmp` 判為孤兒。
    第五輪：dumper 改用 `_yaml_dumper()`（libyaml C 綁定，格式與純 Python `safe_dump` 逐位元組相同）。
    D31-1：`os.replace` 拒絕存取時透過 `_replace_with_retry` 短退避重試，見該函式 docstring。"""
    import yaml  # type: ignore

    tmp = path.with_name(path.name + f".part.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            yaml.dump(doc, f, Dumper=_yaml_dumper(), allow_unicode=True, sort_keys=False)
        _replace_with_retry(tmp, path)
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
    """D31b 之前（含）的共用 sidecar 單檔名。D31b 起新寫入改成每筆一檔（見 `_write_sidecar`），
    這個名字只保留作為「舊格式相容來源」讓 `_iter_sidecar_sources` 認得、折回一輪後可清掉。"""
    return path.with_suffix(path.suffix + ".append")


_SIDECAR_SEQ = itertools.count()


def _sidecar_unique_suffix() -> str:
    """`<pid>.<ns 時間戳>.<行程內序號>`——三者疊加確保同一行程同一奈秒內連續呼叫也不撞名
    （時間戳本身在多數平台已是奈秒級唯一，`_SIDECAR_SEQ` 是最後一道保險）。"""
    return f"{os.getpid()}.{time.time_ns()}.{next(_SIDECAR_SEQ)}"


def _write_sidecar(path: Path, entry: Dict[str, Any]) -> None:
    """advisory lock 逾時／`LedgerReplaceDenied` 的降級路徑：**每筆一檔、寫成即不可變**
    （D31b-1，取代第一棒 D31-3 的「共用檔＋認領改名」，見模組 docstring D31b 段的 WHY）。
    **零取鎖**（呼叫端已逾時／被拒絕）；下次 merge 折回主檔並持久化——G3：折回後即使未達
    conv-overhead 門檻也寫檔，否則刪掉的 sidecar 內容只活在記憶體。

    pid+時間戳+序號 tmp 檔 → `_replace_with_retry` 成同名去掉 `.part.` 的最終檔。

    D31c-1（解複審 W-4）：此前 `finally: tmp.unlink()` 對「dump 成功、replace 被拒」這個情境會
    刪掉合法完整的唯一副本（見模組 docstring D31c 段）。改成分階段處理：
    - dump 到 tmp 本身失敗 ⇒ tmp 不是合法副本，清掉即可，直接 return。
    - `_replace_with_retry` 成功 ⇒ tmp 已被搬走，原路徑天然不存在，無需再清。
    - `_replace_with_retry` 拋 `LedgerReplaceDenied` ⇒ **保留 tmp**、直接 return——它會被
      `_iter_sidecar_sources` 當一般 sidecar 來源在下一次 merge tick 折回（見該函式判準）。

    寫失敗（含 tmp 寫入本身、含 replace 重試耗盡）一律吞掉：sidecar 是 best-effort，帳本零決策權。

    WHY 獨立成函式（DEF-200-275 第四輪 F2，SD-01／ARCH-02）：post hook 在 `ledger_lock` 逾時（5s）後
    若退回 `append_ledger_entry()`，它會**再**取一次同一把鎖再等 5s ⇒ 最壞 10s > `sdd_hook_router.py`
    的 Pre/Post child timeout 8s ⇒ router 砍子行程、hook fail-open、稽核 entry 全丟（實測 10.07s）。
    降級路徑只准做這一件事。
    """
    try:
        import yaml  # type: ignore

        suffix = _sidecar_unique_suffix()
        tmp = path.with_name(f"{path.name}.append.part.{suffix}")
        final = path.with_name(f"{path.name}.append.{suffix}")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                yaml.dump([entry], f, Dumper=_yaml_dumper(), allow_unicode=True, sort_keys=False)
        except Exception:
            # dump 本身失敗：tmp 可能是空檔或半寫，不是「合法唯一副本」，可安全清掉。
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass
            return
        try:
            _replace_with_retry(tmp, final)
        except LedgerReplaceDenied:
            # D31c-1：tmp 此刻是這筆 entry 的唯一合法副本（dump 已成功寫完整 YAML）——
            # 不 unlink、不重試，留給下一次 merge tick 折回（見 `_iter_sidecar_sources`）。
            return
        # 成功：tmp 已被 os.replace 搬到 final，原路徑天然不存在，無需（也不能）再 unlink。
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
    """清掉本目錄下 mtime > 10 分鐘**且**來源 pid 已不存在的孤兒 `.part.` 暫存檔（`sdd_hook_router.py`
    砍 child 於原子寫入寫到一半時留下）。回傳清掉的數量。

    只掃**一種**命名：主檔／calibration 的整本快照 `CONTEXT-LEDGER-*.yaml.part.<pid>`
    （`_atomic_write_yaml`，pid 是唯一段）——這種孤兒可以直接刪：下次寫入者會重新從主檔
    `_load_ledger_doc` 讀起，半寫的快照丟了不影響任何一筆 entry。

    D31c-1（解複審 W-4）：**刻意不掃** `CONTEXT-LEDGER-*.yaml.append.part.*`（D31b 起的
    sidecar 每筆一檔暫存/殘留檔）。兩者孤兒的正確歸宿不同——`.yaml.part.<pid>` 是可再生的整本
    快照，`.append.part.<pid>.<ns>.<seq>` 卻可能是 `_write_sidecar` 在 `LedgerReplaceDenied`
    後刻意保留的**某一筆 entry 的唯一副本**（見該函式與模組 docstring D31c 段）；用同一套
    「夠舊 + pid 已死即 unlink」邏輯去清它，等於主動丟掉本該被折回的資料。這一類一律交給
    `_merge_sidecar_if_present`／`_iter_sidecar_sources` 讀出內容折回主檔後才刪除來源
    （持久化優先於清理）。

    判準刻意保守（兩個條件都要成立才清）：mtime 太新可能仍在寫入中；pid 還活著也可能仍在寫入中——
    只有「夠舊」+「來源行程已死」同時成立才能確定是孤兒。best-effort：任何錯誤吞掉、永不 raise
    （帳本零決策權，清理失敗不得影響正常寫入路徑）。
    """
    removed = 0
    try:
        if not ledger_dir.exists():
            return 0
        now = time.time()
        candidates = list(ledger_dir.glob("CONTEXT-LEDGER-*.yaml.part.*"))
        for p in candidates:
            pid_segment = p.name.rsplit(".part.", 1)[-1].split(".", 1)[0]
            try:
                pid = int(pid_segment)
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
    except (TimeoutError, LedgerReplaceDenied):
        # 必須排在 OSError 前：兩者皆是 OSError 的子類。TimeoutError＝取鎖逾時；
        # LedgerReplaceDenied＝D31-1 重試耗盡仍被拒絕覆寫主檔——與取鎖逾時同型降級，
        # 寫 sidecar 而不是被下方 `except OSError` 靜默吞成 0（此前 windows-compat-ci
        # #220／#221 的遺失根因）。
        _write_sidecar(path, entry)
        try:
            doc = _load_ledger_doc(path)
            return int(doc.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            return int(entry.get("tokens", 0) or 0)
    except OSError:
        # G4：讀不到（`_load_ledger_doc` 的 OSError）⇒ 該次不寫、不建 sidecar（帳本零決策權），
        # 不讓例外到 hook。`LedgerReplaceDenied` 已在上一分支攔截，不會落到這裡。
        return 0


# D31c-1：`.append.part.*` 折回門檻——「來源 pid 已死」或「mtime 超過此秒數」兩者之一成立才
# 折，避免把另一行程正在寫入中的半成品（`_write_sidecar` 的 dump 階段）當完整檔讀取。
_SIDECAR_PART_FOLD_AGE_SEC = 30.0


def _sidecar_part_source_pid(name: str, prefix: str) -> Optional[int]:
    """從 `<prefix><pid>.<ns 時間戳>.<序號>` 檔名擷取 pid 段；解析失敗回 `None`（呼叫端視為
    不可折，保守起見寧可晚一輪也不誤讀半成品）。"""
    tail = name[len(prefix):]
    pid_segment = tail.split(".", 1)[0]
    try:
        return int(pid_segment)
    except ValueError:
        return None


def _iter_sidecar_sources(path: Path) -> List[Path]:
    """列舉待折回主檔的 sidecar 來源檔，涵蓋四種格式（內容形態相同：每個 YAML document 都是
    `list[dict]`，由 `_read_sidecar_entries` 統一解析）：
    - D31b 起每筆一檔、正常路徑已持久化：`<ledger>.append.<pid>.<ns>.<seq>`（`_write_sidecar`
      的 `_replace_with_retry` 成功後的最終檔名）。
    - D31b 之前的共用單檔：`<ledger>.append`（部署當天可能還有殘留，折回一輪後可移除）。
    - 第一棒 D31 的認領檔孤兒：`<ledger>.append.merging.<pid>`（該行程認領後被砍、零清理邏輯
      留下的殘檔，見複審 W-1；本輪起沒有新的認領動作，只做相容折回）。
    - D31c-1 起：`<ledger>.append.part.<pid>.<ns>.<seq>`——`_write_sidecar` 的
      `_replace_with_retry` 重試耗盡（`LedgerReplaceDenied`）時保留下來的**唯一合法副本**
      （見該函式與模組 docstring D31c 段的 W-4 修法）。**只有**來源 pid 已死、或 mtime 超過
      `_SIDECAR_PART_FOLD_AGE_SEC` 秒才視為可折——兩者皆不成立時可能是另一行程仍在
      `tmp.open("w")` 階段的半成品，跳過（留給下一次 merge tick 重新判斷，不會遺失）。
    """
    legacy = _sidecar_path(path)
    sources: List[Path] = [legacy] if legacy.exists() else []
    part_prefix = path.name + ".append.part."
    now = time.time()
    for p in sorted(path.parent.glob(path.name + ".append.*")):
        if p.name.startswith(part_prefix):
            pid = _sidecar_part_source_pid(p.name, part_prefix)
            if pid is None:
                continue
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            if age <= _SIDECAR_PART_FOLD_AGE_SEC and _is_pid_alive(pid):
                continue  # 可能仍在寫入中，本輪不折
            sources.append(p)
            continue
        sources.append(p)
    return sources


def _read_sidecar_entries(file_path: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """把一份 sidecar 檔解析成 `(去重用 id, entry)` 列表。id＝`<檔名>#<檔內序號>`，同時涵蓋
    「每筆一檔」（單一 YAML document、序號恆 0）與舊格式「多筆共用一檔」（`open('a')` 疊加出的
    多個 YAML document，各自可能是 list 或單一 dict）兩種形態，讓 `_merge_sidecar_if_present`
    的去重書籤不必關心格式差異。"""
    import yaml  # type: ignore

    pairs: List[Tuple[str, Dict[str, Any]]] = []
    idx = 0
    with file_path.open("r", encoding="utf-8") as f:
        for chunk in yaml.load_all(f, Loader=_yaml_loader()):
            if not chunk:
                continue
            items = chunk if isinstance(chunk, list) else [chunk]
            for item in items:
                if isinstance(item, dict):
                    pairs.append((f"{file_path.name}#{idx}", item))
                    idx += 1
    return pairs


def _merge_sidecar_if_present(path: Path, doc: Dict[str, Any]) -> Tuple[int, List[Path]]:
    """把所有待折回的 sidecar 來源（見 `_iter_sidecar_sources`）折進 `doc`，回傳
    `(新折回筆數, 可安全刪除的來源檔清單)`——**不在本函式內刪除任何檔案**。

    🔴 前提：呼叫端必須已持有 `ledger_lock()`（`_merge_locked` 是唯一呼叫端），本函式只改
    記憶體中的 `doc`。

    D31b-2（取代第一棒 D31-3 的認領改名；解複審 W-1）：**刪除時機延後到主檔持久化成功之後**——
    `_merge_locked` 必須先把本函式回傳的清單交給 `_atomic_write_yaml(path, doc)` 成功之後，才呼叫
    `_delete_sidecar_sources`。這讓「中途被砍」的最壞情況變成「sidecar 檔還在，下次 merge 重新
    讀到」而不是資料遺失；但也因此需要去重，否則「主檔已持久化、來源還沒被刪就被砍」這個更窄的
    殘餘窗口會讓同一筆下次再折一次。去重用 `doc['conversation_overhead']['folded_sidecar_ids']`
    書籤（每筆 entry 的 `f'{檔名}#{序號}'`），書籤本身靠「對應檔案是否還存在」自我裁剪——已被
    `_delete_sidecar_sources` 刪除的來源，其 id 下次呼叫時被濾掉，不會無界成長。

    QA Round-3 P2-07（HEAD 既有 WHY）：when `file_lock` timed out during pre/post hook writes,
    entries are staged into a sidecar instead of the primary ledger. If we skip reconciliation,
    `last_merge_entry_index` counts only the primary's `entries`, silently undercounting tool
    calls and over-merging conversation overhead on the next tick.
    """
    try:
        import yaml  # type: ignore  # noqa: F401
    except Exception:  # noqa: BLE001
        return 0, []

    sources = _iter_sidecar_sources(path)
    if not sources:
        return 0, []

    conv_meta = doc.get("conversation_overhead")
    if not isinstance(conv_meta, dict):
        conv_meta = {}
        doc["conversation_overhead"] = conv_meta
    raw_ids = conv_meta.get("folded_sidecar_ids")
    folded_ids = {
        i for i in raw_ids
        if isinstance(i, str) and (path.parent / i.rsplit("#", 1)[0]).exists()
    } if isinstance(raw_ids, list) else set()

    merged = 0
    safe_to_delete: List[Path] = []
    for file_path in sources:
        try:
            pairs = _read_sidecar_entries(file_path)
        except Exception as exc:  # noqa: BLE001 — sidecar is best-effort；損毀不是「別人在寫」而是
            # 內容損壞（含 D31c-1 起 `.append.part.*` 半成品：另一行程尚未寫完就被判定為「夠舊」），
            # 仍不 raise（帳本零決策權），但檔案留著不刪，供事後查驗。ASCII-only：本檔可能被非 UTF-8
            # locale 的 hook 子行程 import（鐵律三），中文字元在該情境下會讓 print 本身 crash。
            print(
                f"[SDD-CTX][LEDGER] sidecar file failed to parse, skipping (not deleted): "
                f"{file_path.name}: {type(exc).__name__}",
                file=sys.stderr,
            )
            continue
        for sidecar_id, item in pairs:
            if sidecar_id in folded_ids:
                continue  # 主檔已持久化、來源檔尚未被刪就重讀到——不得重複計入（D31b-2 去重）
            doc.setdefault("entries", []).append(item)
            doc["cumulative_tokens"] = int(doc.get("cumulative_tokens", 0)) + int(item.get("tokens", 0) or 0)
            folded_ids.add(sidecar_id)
            merged += 1
        safe_to_delete.append(file_path)

    conv_meta["folded_sidecar_ids"] = sorted(folded_ids)
    return merged, safe_to_delete


def _delete_sidecar_sources(files: List[Path]) -> None:
    """`_merge_locked` 只在 `_atomic_write_yaml` 成功之後才呼叫——刪除順序本身就是 D31b-2 的
    正確性保證（先持久化，再刪來源）。best-effort：刪不掉就留著，`folded_sidecar_ids` 書籤已經
    防止它被重複折算，下次 tick 再試即可，不影響帳本正確性，只影響殘檔何時真正消失。"""
    for f in files:
        try:
            f.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


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
    # D31b-2：`sidecar_files` 是「可安全刪除」清單，但刪除必須晚於本函式下方任何一個成功的
    # `_atomic_write_yaml` 呼叫——見 `_merge_sidecar_if_present` docstring 的正確性保證。
    sidecar_merged, sidecar_files = _merge_sidecar_if_present(path, doc)
    entries = doc.get("entries") or []
    if not entries:
        # D31b-2：帳本目前沒有真的 entries，但可能仍有 sidecar 來源需要持久化書籤／刪除
        # （例如主檔剛被 rotate 成 .corrupt-* 後重開）。
        if sidecar_files:
            _atomic_write_yaml(path, doc)
            _delete_sidecar_sources(sidecar_files)
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
        _delete_sidecar_sources(sidecar_files)
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0)),
                "rebaselined": True}
    last_merged_at_idx = raw_idx
    delta_entries = max(0, len(entries) - last_merged_at_idx)
    delta_calls = delta_entries // entries_per_call
    if delta_calls < merge_every:
        # G3（SD-R2-01，第 2 輪審查；HEAD 既有）：sidecar 已被 `_merge_sidecar_if_present` 併進記憶體
        # doc，這裡早退若不寫檔，折回的 entries 就永久消失（預設門檻下 20 個 tick 只有 1 個真的
        # 持久化）。只在真的處理了 sidecar（新折回或確認重複）才多寫一次；`sidecar_files` 非空即
        # 代表有來源檔待刪，即使 `sidecar_merged==0`（全是 D31b-2 去重後的重複）也要持久化書籤
        # 並清掉來源，否則殘檔永遠留在磁碟上。
        if sidecar_merged or sidecar_files:
            _atomic_write_yaml(path, doc)
            _delete_sidecar_sources(sidecar_files)
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
    _delete_sidecar_sources(sidecar_files)
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
