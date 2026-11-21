"""Windows 行程 handle 面（ctypes；DES §7.1「怎麼關」、§7 DEF-02 的 GetProcessTimes）。

WHY 獨立一檔：`procstop.terminate_tree_verified` 與 `oldwin` 的判準都是純邏輯（吃一個 `api` 物件），
會動真行程的原語集中在這裡，單元測試傳假 `api`、E2E 傳真的 `WinApi`。所有動作對 **handle**
做、不再用 pid——pid 被重用也砍不到別人（先在 handle 上驗建立時間）。
`created`／`procStart` 的單位＝FILETIME（1601 起算的 100ns 刻度，整數），與
`~/.claude/sessions/<pid>.json` 的 `procStart` 同一把尺（DES §7 DEF-02 當回合實測全等）。
非 Windows：`WinApi()` 可建立但每個方法回「量不到」（`None`／空），呼叫端因此不會動任何行程。
"""
from __future__ import annotations

import os
import sys

_TERMINATE, _QUERY_LIMITED, _SYNCHRONIZE = 0x0001, 0x1000, 0x00100000
_TH32_SNAPPROCESS, _WAIT_TIMEOUT = 0x2, 0x102
_EPOCH_DELTA_100NS = 116444736000000000  # 1601-01-01 → 1970-01-01


def epoch_to_filetime(epoch: float) -> int:
    """epoch 秒（微秒精度）→ FILETIME 整數；供 CIM 路徑（`CreationDate` 只到微秒）換算。"""
    return round(epoch * 1_000_000) * 10 + _EPOCH_DELTA_100NS


class WinApi:
    """handle 型行程原語；方法名即契約（假 api 照同名實作）。"""

    def __init__(self) -> None:
        self._k32 = None
        if sys.platform == "win32":
            import ctypes  # noqa: PLC0415 — Windows 專屬
            import ctypes.wintypes as wt  # noqa: PLC0415

            self._ct, self._wt = ctypes, wt
            self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._k32.OpenProcess.restype = wt.HANDLE
            self._k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
            self._k32.CloseHandle.argtypes = [wt.HANDLE]
            self._k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
            self._k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
            self._k32.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4
            self._k32.QueryFullProcessImageNameW.argtypes = [
                wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
            self._k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
            self._k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
            for name in ("Process32FirstW", "Process32NextW"):
                getattr(self._k32, name).argtypes = [wt.HANDLE, ctypes.c_void_p]

    # ---- handle 動作 ----
    def open(self, pid: int):
        """開 `TERMINATE|QUERY_LIMITED|SYNCHRONIZE` handle；開不了（無此行程／權限）回 `None`。"""
        if self._k32 is None or not isinstance(pid, int) or pid <= 0:
            return None
        handle = self._k32.OpenProcess(_TERMINATE | _QUERY_LIMITED | _SYNCHRONIZE, False, pid)
        return int(handle) if handle else None

    def created(self, handle) -> int | None:
        """handle 的 creation FILETIME；取不到回 `None`。"""
        if self._k32 is None or handle is None:
            return None
        cre, ext, kern, usr = (self._wt.FILETIME() for _ in range(4))
        ok = self._k32.GetProcessTimes(handle, *(self._ct.byref(t) for t in (cre, ext, kern, usr)))
        return (cre.dwHighDateTime << 32) | cre.dwLowDateTime if ok else None

    def image(self, handle) -> str:
        """映像檔名（小寫、含副檔名）；取不到回空字串。"""
        if self._k32 is None or handle is None:
            return ""
        size = self._wt.DWORD(1024)
        buf = self._ct.create_unicode_buffer(1024)
        ok = self._k32.QueryFullProcessImageNameW(handle, 0, buf, self._ct.byref(size))
        return os.path.basename(buf.value).lower() if ok else ""

    def terminate(self, handle) -> bool:
        return bool(self._k32 and handle is not None and self._k32.TerminateProcess(handle, 1))

    def running(self, handle) -> bool:
        """還沒結束（`WaitForSingleObject(h, 0)` 逾時）。"""
        return bool(self._k32 and handle is not None
                    and self._k32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT)

    def close(self, handle) -> None:
        if self._k32 is not None and handle is not None:
            self._k32.CloseHandle(handle)

    # ---- Toolhelp32 ----
    def snapshot(self) -> list[tuple[int, int]]:
        """全部行程的 `(pid, parent pid)`；快照失敗回空 list（呼叫端視為沒有子孫、不砍）。"""
        if self._k32 is None:
            return []
        ct, wt = self._ct, self._wt

        class _Entry(ct.Structure):
            _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                        ("th32DefaultHeapID", ct.c_size_t), ("th32ModuleID", wt.DWORD),
                        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                        ("pcPriClassBase", ct.c_long), ("dwFlags", wt.DWORD),
                        ("szExeFile", ct.c_wchar * 260)]

        snap = self._k32.CreateToolhelp32Snapshot(_TH32_SNAPPROCESS, 0)
        if not snap or int(snap) == ct.c_void_p(-1).value:
            return []
        rows: list[tuple[int, int]] = []
        try:
            entry = _Entry()
            entry.dwSize = ct.sizeof(_Entry)
            ok = self._k32.Process32FirstW(snap, ct.byref(entry))
            while ok:
                rows.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
                ok = self._k32.Process32NextW(snap, ct.byref(entry))
        finally:
            self._k32.CloseHandle(snap)
        return rows

    def ancestors(self, pid: int) -> set[int]:
        """`pid` 的祖先 pid 集合（沿 parent 往上，上限 64 層防環）。"""
        parent = dict(self.snapshot())
        out: set[int] = set()
        cur = parent.get(pid)
        while cur and cur not in out and len(out) < 64:
            out.add(cur)
            cur = parent.get(cur)
        return out
