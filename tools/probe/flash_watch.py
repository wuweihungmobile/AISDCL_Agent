#!/usr/bin/env python3
"""可見視窗層級的黑框偵測器（Windows）——DEF-200-417。

WHY —— 為什麼行程建立事件不夠，要另外量「視窗」
-------------------------------------------------------------
`tools/probe/console_spawn_watch.py` 量的是**行程建立**（WMI `__InstanceCreationEvent`）。
那支量測器有一個結構性盲區：`CREATE_NO_WINDOW` 之下 Windows 一樣會建立一支 `conhost.exe`
（只是帶著隱形視窗站台旗標 `0x4`），行程建立事件因此**量不出「使用者到底看不看得到」**——
一支隱形 conhost 與一支真的彈出來的黑框，在行程建立這個層次上是同一種事件。

真機實測（DEF-200-417）：Windows 11 下從無 console 的父行程（`pythonw.exe`）spawn
`powershell.exe` 且**不帶** `CREATE_NO_WINDOW` 時，使用者看到的是 `WindowsTerminal.exe`
（class `CASCADIA_HOSTING_WINDOW_CLASS`，事件序 CREATE→FOREGROUND→SHOW）＋ powershell
自己的 `PseudoConsoleWindow`——不是傳統的 `conhost.exe`。帶 `CREATE_NO_WINDOW` 時則只有
一支 `conhost.exe 0x4`（隱形）被建立，從頭到尾不會有任何視窗變成可見。⇒「誰承載了黑框」
與「誰建立了 console 子系統行程」在 Win11 上是兩個不同的答案，量測器必須量對層次。

為什麼選 `SetWinEventHook`（而不是輪詢 `EnumWindows`）
-------------------------------------------------------------
`EnumWindows` 只看得到呼叫瞬間還活著的視窗；本 repo 要抓的正是**只存活一個 frame**
就消失的黑框（使用者形容成「閃一下」），輪詢間隔再短也可能整段錯過。`SetWinEventHook`
是作業系統在視窗狀態改變當下**主動推播**的事件——連只活一個 frame 的視窗，建立與變成
可見那兩個瞬間都會各發一次事件，不靠輪詢去「剛好問到」。

🔴 誠實劃界
-------------------------------------------------------------
· 只看得到**本使用者桌面**的視窗（另一個 session／另一個使用者的視窗看不到，這與
  `console_spawn_watch.py` 對行程可見度的權限劃界同一條紀律）。
· `SetWinEventHook` 要求呼叫執行緒**有訊息迴圈**在抽 `PeekMessage`／`GetMessage`；沒有
  訊息迴圈的話 hook 裝得上但事件永遠收不到（本檔 `main()` 因此自己跑一個輪詢式訊息迴圈，
  不能只是 `time.sleep`）。
· 本檔用 `WINEVENT_OUTOFCONTEXT`（不需把 DLL 注入到目標行程），代價是事件**可能延遲
  數十毫秒**才送達；比目標視窗真正消失的時間晚到不算錯誤，只代表 `at` 時間戳與真實
  視窗生滅時間有這個量級的落差。
· 本檔量的是「視窗變成可見」，不是「這支行程是誰生的」——那個問題仍由
  `console_spawn_watch.py` 回答；兩者一起看才是完整的因果鏈（父行程 → console 子系統
  行程 → 承載視窗 → 使用者看到）。

用法
-------------------------------------------------------------
    python tools/probe/flash_watch.py --seconds 300 --out %TEMP%\\flash.jsonl
    python tools/probe/flash_watch.py --report %TEMP%\\flash.jsonl

非 Windows：`SetWinEventHook` 是 Windows 概念，本檔刻意不假裝支援——`main()` 在非
`--report` 模式下印一句並回 rc=0（沒有東西好量，不是失敗）。`ctypes.WinDLL`／
`ctypes.WINFUNCTYPE` 等 Windows 專屬 symbol 全數收在 `if sys.platform == "win32":`
作用域內（鐵律三；`tools/tests/test_platform_neutral_paths.py::TestForeignPlatformApiIsGuarded`
守著）。

回歸鎖：`tools/tests/test_context_budget_guard.py`（`FlashWatchReportTest` 一類；
`report()` 是純函式、不碰 ctypes，任何平台都能對一份合成 jsonl 跑）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: 「這是使用者真的看得到的 console 承載者視窗」的 class 白名單（DEF-200-417 真機實測）：
#: `CASCADIA_HOSTING_WINDOW_CLASS`＝Windows Terminal、`ConsoleWindowClass`＝傳統 conhost
#: 視窗、`PseudoConsoleWindow`＝ConPTY 自己的視窗。與 `console_spawn_watch.CONSOLE_IMAGES`
#: 刻意分開維護：一支是**行程**層級的映像名，一支是**視窗**層級的 class 名，兩個不同的
#: 量測面硬併成一份反而會把「量到了行程」跟「量到了可見視窗」混淆。
VISIBLE_CONSOLE_CLASSES = frozenset(
    {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS", "PseudoConsoleWindow"})


if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wt
    import time
    from datetime import datetime

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _EVENT_OBJECT_CREATE = 0x8000
    _EVENT_OBJECT_SHOW = 0x8002
    _EVENT_SYSTEM_FOREGROUND = 0x0003
    _WINEVENT_OUTOFCONTEXT = 0x0000
    _WINEVENT_SKIPOWNPROCESS = 0x0002
    _OBJID_WINDOW = 0
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _GA_ROOT = 2
    _PM_REMOVE = 1
    _TH32CS_SNAPPROCESS = 0x2

    _WinEventProcType = ctypes.WINFUNCTYPE(
        None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD)

    user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
    user32.GetAncestor.restype = wt.HWND
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]

    def _now_iso(timespec: str = "seconds") -> str:
        """帶 offset 的本地時間字串（鐵律三 naive 時間戳判準；純顯示／記錄用途，
        跨 DST 讀回不靜默錯 3600 秒）。"""
        return datetime.now().astimezone().isoformat(timespec=timespec)

    class _Pe32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", wt.LONG),
                    ("dwFlags", wt.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    def exe_of(pid: int, cache: dict[int, str]) -> str:
        """行程完整路徑（`QueryFullProcessImageNameW`）。查不到回 `"?"`。"""
        if pid in cache:
            return cache[pid]
        name = "?"
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            buf = ctypes.create_unicode_buffer(1024)
            size = wt.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                name = buf.value
            kernel32.CloseHandle(handle)
        cache[pid] = name
        return name

    def parent_of(pid: int) -> int:
        """用 Toolhelp 快照找父 PID（純 ctypes，不 spawn 任何行程）。"""
        snap = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if snap == wt.HANDLE(-1).value:
            return -1
        entry = _Pe32()
        entry.dwSize = ctypes.sizeof(_Pe32)
        ppid = -1
        if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                if entry.th32ProcessID == pid:
                    ppid = entry.th32ParentProcessID
                    break
                if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                    break
        kernel32.CloseHandle(snap)
        return ppid

    class _Watcher:
        """封裝一次量測窗的可變狀態（out handle／已見去重集合／事件計數）。

        設計成物件而非模組層全域：`SetWinEventHook` 的 callback 是 C 呼叫慣例，接受不了
        額外的使用者資料指標，唯一能帶狀態進去的方式是綁定方法（bound method）的閉包。
        """

        def __init__(self, out_path: Path) -> None:
            self.out_fh = out_path.open("a", encoding="utf-8")
            self.seen: set[tuple[int, int]] = set()
            self.exe_cache: dict[int, str] = {}
            self.count = 0

        def callback(self, hook, event, hwnd, id_object, id_child, thread, ms) -> None:
            del hook, id_child, thread, ms  # C callback 簽章固定，用不到的位置參數
            if id_object != _OBJID_WINDOW or not hwnd:
                return
            if user32.GetAncestor(hwnd, _GA_ROOT) != hwnd:  # 只看頂層視窗
                return
            key = (int(hwnd), event)
            if key in self.seen and event != _EVENT_SYSTEM_FOREGROUND:
                return
            self.seen.add(key)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            pid = wt.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            ppid = parent_of(pid.value)
            rec = {
                "at": _now_iso("milliseconds"),
                "event": {_EVENT_OBJECT_CREATE: "CREATE", _EVENT_OBJECT_SHOW: "SHOW",
                          _EVENT_SYSTEM_FOREGROUND: "FOREGROUND"}.get(event, hex(event)),
                "hwnd": int(hwnd), "class": cls.value, "title": title.value,
                "visible": bool(user32.IsWindowVisible(hwnd)),
                "pid": pid.value, "exe": exe_of(pid.value, self.exe_cache),
                "ppid": ppid, "pexe": exe_of(ppid, self.exe_cache) if ppid > 0 else "?",
            }
            self.out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.out_fh.flush()
            self.count += 1

        def close(self) -> None:
            self.out_fh.close()

    def watch(seconds: float, out: Path) -> int:
        """跑一次量測窗（純 ctypes，零 spawn；量測器自己不成為它要量的現象的來源）。"""
        watcher = _Watcher(out)
        proc = _WinEventProcType(watcher.callback)
        hooks: list[int] = []
        try:
            for event in (_EVENT_OBJECT_CREATE, _EVENT_OBJECT_SHOW, _EVENT_SYSTEM_FOREGROUND):
                hook = user32.SetWinEventHook(
                    event, event, None, proc, 0, 0,
                    _WINEVENT_OUTOFCONTEXT | _WINEVENT_SKIPOWNPROCESS)
                if not hook:
                    print(f"❌ SetWinEventHook 失敗（{hex(event)}）："
                          f"{ctypes.get_last_error()}", file=sys.stderr)
                    return 2
                hooks.append(hook)
            print(f"flash_watch armed {_now_iso()} for {seconds}s → {out}")
            sys.stdout.flush()
            msg = wt.MSG()
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, _PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.01)
        finally:
            for hook in hooks:
                user32.UnhookWinEvent(hook)
            watcher.close()
        print(f"flash_watch done {_now_iso()} events={watcher.count}")
        return 0

else:
    def watch(seconds: float, out: Path) -> int:
        """非 Windows 上不成立（`SetWinEventHook` 是 Windows 概念）。"""
        del seconds, out  # 簽章對齊 Windows 版，供未來呼叫端一致呼叫
        print("flash_watch 只在 Windows 成立（SetWinEventHook 是 Windows 概念）；"
              "mac/Linux 沒有對等 API，本檔刻意不假裝支援。", file=sys.stderr)
        return 1


def report(path: Path) -> int:
    """讀一份 `flash_watch` 事件 jsonl：印出 `visible=True` 且 class 屬於
    `VISIBLE_CONSOLE_CLASSES` 的事件（附 pid／exe／pexe／時間），並統計。

    純函式、不碰 ctypes ⇒ 任何平台都能對一份既有 jsonl 跑報表（測試不需要 Windows）。
    """
    if not path.is_file():
        print(f"❌ 事件檔不存在：{path}（沒有量到 ≠ 沒有發生）", file=sys.stderr)
        return 1
    total = 0
    hits: list[dict] = []
    class_counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        total += 1
        cls = str(record.get("class") or "")
        class_counts[cls] = class_counts.get(cls, 0) + 1
        if record.get("visible") and cls in VISIBLE_CONSOLE_CLASSES:
            hits.append(record)
    print(f"事件檔 {path}　總視窗事件 {total} 筆，可見 console 承載者視窗事件 {len(hits)} 筆")
    for record in hits:
        print(f"   {record.get('at')}  {record.get('event')}  class={record.get('class')}"
              f"  pid={record.get('pid')} exe={record.get('exe')}"
              f"  ppid={record.get('ppid')} pexe={record.get('pexe')}")
    if class_counts:
        print("\n逐 class 事件數：")
        for cls, count in sorted(class_counts.items(), key=lambda kv: -kv[1]):
            print(f"   x{count:<4d} {cls or '(空)'}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="可見視窗層級的黑框偵測器（SetWinEventHook）")
    parser.add_argument("--seconds", type=float, default=300.0)
    parser.add_argument("--out", default="", help="事件 jsonl 落點（非 --report 模式必填）")
    parser.add_argument("--report", default="", help="只讀既有 jsonl 印可見視窗報表")
    args = parser.parse_args(argv)

    if args.report:
        return report(Path(args.report))
    if sys.platform != "win32":
        print("flash_watch 只在 Windows 成立（SetWinEventHook 是 Windows 概念）；"
              "mac/Linux 沒有對等 API，本檔刻意不假裝支援。", file=sys.stderr)
        return 0
    if not args.out:
        print("❌ --out 為必填（--report 模式除外）", file=sys.stderr)
        return 1
    return watch(args.seconds, Path(args.out))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
