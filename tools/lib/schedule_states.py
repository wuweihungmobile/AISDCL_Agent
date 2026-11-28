"""排程工作物件狀態的**唯讀**列舉（WP-SW REQ-CTL-58；DES §24.5）：`job_states(prefix)`。

`schedule_backend.list_jobs` 只回名稱，判不了「還在跑嗎／多久沒跑／上次結果」；舊哨兵殘骸 GC 與 ack 摘要需要
排程器**自報**的 `State`／`LastRunTime`／`LastTaskResult`／`NextRunTime`。三個後端各掛同一個 mixin（類別宣告
行改 `(StatesMixin)`、`schedule_backend.py` 零增行：該檔 tier 餘裕只有 2 行，DES §24.10 預先指示「逼近上限就抽到
同目錄新檔」）。

回 `list[dict] | None`（`None`＝量不到，與 `list_jobs` 同義）；每筆 `{name, state, last_run, last_result,
next_run}`，量不到的欄位為 `None`（空 `NextRunTime` 回 `""`＝排程器自報「沒有下次」）：
· Windows：`Get-ScheduledTask`＋`Get-ScheduledTaskInfo`，經 `planner.run_powershell`（不開新 console）；
  `LastRunTime` 年份 ≤ 2000 ＝從未執行（Windows 回 1999-11-30 哨兵）⇒ `""`。
· launchd：沒有 LastRunTime／下次時刻的概念 ⇒ `last_run`／`next_run` 回 `None`（呼叫端「讀不到 ⇒ 不拆」，
  macOS 上 GC 因此誠實地不動作）。
· 無載具平台：`[]`（量到了、真的沒有工作）。
唯讀：不 Register／Unregister、不寫任何檔。
"""
from __future__ import annotations

_PS = (
    "Get-ScheduledTask | Where-Object {{ $_.TaskName -like '{pat}*' }} | ForEach-Object {{ "
    "$i = $_ | Get-ScheduledTaskInfo; "
    "$lr = if ($i.LastRunTime -and $i.LastRunTime.Year -gt 2000) {{ $i.LastRunTime.ToString('o') }} else {{ '' }}; "
    "$nr = if ($i.NextRunTime) {{ $i.NextRunTime.ToString('o') }} else {{ '' }}; "
    "(($_.TaskName, $_.State, $lr, $i.LastTaskResult, $nr) -join [char]9) }}\n"
)


def parse_rows(stdout: str, prefix: str) -> list[dict]:
    """解 Windows 列舉輸出（Tab 分欄）；壞行跳過、名稱必須以 `prefix` 開頭。"""
    rows = []
    for line in str(stdout).splitlines():
        parts = line.rstrip("\r\n").split("\t")
        if len(parts) != 5 or not parts[0].strip().startswith(prefix):
            continue
        name, state, last_run, result, next_run = (p.strip() for p in parts)
        try:
            last_result = int(result) if result else None
        except ValueError:
            last_result = None
        rows.append({"name": name, "state": state or None, "last_run": last_run,
                     "last_result": last_result, "next_run": next_run})
    return rows


def states_for(backend, prefix: str) -> list[dict] | None:
    name = getattr(backend, "name", "")
    if name == "none":
        return []
    if name == "launchd":
        names = backend.list_jobs(prefix)
        return None if names is None else [
            {"name": n, "state": None, "last_run": None, "last_result": None, "next_run": None}
            for n in names]
    import schedule_backend  # noqa: PLC0415 — lazy：避免與 schedule_backend 互相頂層 import

    planner = schedule_backend._planner()  # noqa: SLF001
    if planner is None:
        return None
    proc = planner.run_powershell(_PS.format(pat=planner._ps_single_quote(prefix)))  # noqa: SLF001
    return None if proc.returncode != 0 else parse_rows(proc.stdout, prefix)


class StatesMixin:
    """三個後端共用的唯讀 `job_states`（判斷全在本檔）。"""

    def job_states(self, prefix: str) -> list[dict] | None:
        return states_for(self, prefix)
