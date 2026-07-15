"""
PTY 包裝器（全平台唯一實作；R3 四方複審 Architect 發現原文檔誤稱「Windows PTY 包裝器」——
wexpect 於 pyproject.toml 已 scope 為 sys_platform == "win32"，macOS/Linux 上
_WEXPECT_AVAILABLE 恆為 False，一律走 subprocess + pipe fallback，並非真正的 POSIX pty；
本模組實為三平台共用的唯一實作，非 Windows 專屬）。
Windows 上優先使用 wexpect 模擬終端，讓 Claude Code 認為自己在 TTY 環境中執行；
若 wexpect 不可用（含所有非 Windows 平台），退回到 subprocess + NonBlockingStreamReader。
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..utils.logger import RawStreamLogger
from ..utils.trace_context import propagate_to_subprocess_env
from .stream_reader import NonBlockingStreamReader
from .text_utils import strip_ansi

logger = logging.getLogger("autoclaude.perception")

try:
    import wexpect  # type: ignore
    _WEXPECT_AVAILABLE = True
except ImportError:
    _WEXPECT_AVAILABLE = False
    logger.warning("wexpect 未安裝，改用 subprocess 模式（部分互動提示可能無法自動回應）")


def _resolve_command(command: str) -> list[str]:
    """解析啟動指令的可執行檔位置。

    npm 全域安裝的 CLI（如 claude）在 Windows 上 PATH 內實際是 `.cmd`/`.bat`
    批次檔 shim；Windows CreateProcess（subprocess/wexpect 底層）不會像
    cmd.exe 依 PATHEXT 自動嘗試副檔名，也無法直接執行批次檔（WinError 2）。
    解析到 .cmd/.bat 時回傳 `["cmd", "/c", resolved]`（呼叫端須改走
    `PtyWrapper._start_subprocess()` + `_build_cmd_shim_line()`，見其說明；
    `.cmd`/`.bat` 一律不透過 wexpect 啟動，見 `PtyWrapper.start()` 說明）；
    找不到則原樣回傳，讓錯誤自然浮現。
    """
    if sys.platform != "win32":
        return [command]
    resolved = shutil.which(command)
    if resolved and resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved or command]


def _is_cmd_shim(resolved: list[str]) -> bool:
    """判斷 `_resolve_command()` 的回傳值是否為 .cmd/.bat shim 解析結果。"""
    return len(resolved) == 3 and resolved[0] == "cmd" and resolved[1] == "/c"


def _quote_cmd_shim_argv(shim_path: str, args: list[str]) -> str:
    """對 .cmd/.bat shim 路徑 + args 依 MS 標準 argv 引號/跳脫規則
    （`subprocess.list2cmdline`）組成單一已跳脫字串（**不含** `cmd /d /s /c`
    前綴——該前綴由 `_build_cmd_shim_line()` 組裝）。僅供 `_start_subprocess()`
    使用；`.cmd`/`.bat` shim 一律不透過 wexpect 啟動（見 `PtyWrapper.start()`
    docstring：wexpect 自身的 `join_args()` 無法產生 cmd.exe `/C` 特例解析
    規則所需的單一整體外層引號結構，此函式的合併加引號技巧對 wexpect 路徑
    無效、四方複審 R2/R3 已證實）。

    四方複審 R1 QA 發現（`subprocess.list2cmdline` 實測重現）：若把
    `["cmd", "/c", shim_path] + args` 當一般 argv list 交給 Popen/wexpect，
    Python（或 wexpect）會對每個 token 個別加引號；一旦 shim_path 與 args
    都含空白（如 Windows 常見的 `C:\\Program Files\\...` 安裝路徑 + 多字
    prompt），命令列會出現超過兩個引號字元，觸發 cmd.exe `/C` 的舊式剝引號
    規則（見 `cmd /?`：僅在「命令列恰好含兩個引號字元」時才保留引號，否則
    剝掉第一個與最後一個引號、破壞中間內容）——導致執行檔路徑被腰斬。
    """
    return subprocess.list2cmdline([shim_path] + args)


def _build_cmd_shim_line(shim_path: str, args: list[str]) -> str:
    """組出透過 `cmd /d /s /c` 呼叫 .cmd/.bat shim 的**單一完整命令列字串**，
    供 `subprocess.Popen` 以「字串」（非 list）傳遞。

    解法比照 Node.js cross-spawn 對 npm .cmd shim 的標準處理：`_quote_cmd_shim_argv`
    正確加引號/跳脫後，整體再包一層引號、加 `/S` 讓 cmd.exe 改用一般解析
    （不觸發 `_quote_cmd_shim_argv` docstring 描述的舊式剝引號捷徑）。呼叫端
    必須把回傳字串直接當「單一字串」（非 list）傳給 Popen——Windows 上
    shell=False 時字串型 args 會原樣透傳給 CreateProcess，不會再被
    list2cmdline 二次加引號破壞這裡手動組好的命令列。
    """
    return f'cmd /d /s /c "{_quote_cmd_shim_argv(shim_path, args)}"'


class PtyWrapper:
    def __init__(
        self,
        command: str,
        args: list[str],
        auth_patterns: list[str],
        auth_response: str,
        raw_log_path: Path | None = None,
        encoding: str = "utf-8",
    ):
        self._command = command
        self._args = args
        self._auth_patterns = [re.compile(p, re.IGNORECASE) for p in auth_patterns]
        self._auth_response = auth_response
        self._encoding = encoding
        self._raw_logger = RawStreamLogger(raw_log_path) if raw_log_path else None
        self._child = None
        self._proc = None
        self._reader: NonBlockingStreamReader | None = None

    # ------------------------------------------------------------------
    # 啟動
    # ------------------------------------------------------------------
    def start(self) -> None:
        # .cmd/.bat shim（npm 全域安裝的 claude 在 Windows 上實際型態）一律走
        # subprocess 路徑，即使 wexpect 可用——四方複審 R1~R3 三輪教訓：wexpect
        # 內部（host.py 啟動 console-reader 輔助行程 + __main__.py 轉發）用自己
        # 天真的 `join_args()` 逐 token 加引號、經兩層轉發後再交給 `cmd /d /s /c`；
        # 但 cmd.exe 對 `/C` 之後的內容有非標準 CRT 的特例解析（見 `cmd /?`）：
        # 只有「命令列恰好含兩個引號字元」時才完整保留引號，否則一律剝除第一個
        # 與（不論在哪裡的）最後一個引號字元、放任中間孤兒引號原樣殘留。
        # shim_path 與 args 只要**同時**含空白（如 `C:\Program Files\...` 安裝
        # 路徑 + 多字 prompt），remainder 就會有 4 個以上引號字元，觸發此規則、
        # 把執行檔路徑腰斬——不論我們自己預先加不加引號，wexpect 逐 token加引號
        # 的機制都無法產生 cmd.exe 這個特例規則所需的「單一整體外層引號」結構
        # （list2cmdline+外層包一層引號才做得到，見 _build_cmd_shim_line；而
        # wexpect 的 join_args 無此機制、也無法繞過其兩層自動加引號去客製）。
        # 已對真實 wexpect==4.0.0 原始碼＋官方 cmd 文件＋Node.js 生態圈已知同類
        # bug 三方交叉驗證確認此為結構性限制，非本次可修正的實作疏漏；改走
        # subprocess（字串型 argv，已用 CPython _execute_child 原始碼驗證正確）
        # 是目前唯一確認可行的方案，代價是此情境下失去 PTY 模擬（互動提示仍可
        # 靠 _auto_respond 的 stdin pipe 機制正常運作，見 _readline_subprocess）。
        if _WEXPECT_AVAILABLE and not _is_cmd_shim(_resolve_command(self._command)):
            self._start_wexpect()
        else:
            self._start_subprocess()

    def _start_wexpect(self) -> None:
        # improving_72 DEF-72-001：原以 " ".join([command]+args) 把含反引號/換行/分號的
        # 多行 prompt 拼成單一 shell 字串傳 wexpect.spawn → 被 shell 解析搞爛（反引號當命令
        # 替換、換行斷句），claude 收到殘缺指令、raw log 0 bytes（pty-vs-sdk 真跑揭露：
        # 簡單 prompt 可擷取、複雜 prompt 全空）。改以 args=list 傳遞（wexpect.spawn 原生
        # 支援；零 token 探針證實 list 路徑 prompt 原樣抵達子程序），不再經 shell parsing。
        #
        # 不處理 .cmd/.bat shim：呼叫端（start()）已確保走到這裡時 self._command
        # 解析結果必為一般可執行檔（非 shim），shim 一律改走 _start_subprocess()。
        resolved = _resolve_command(self._command)
        exe = resolved[0]
        wexpect_args = list(self._args)
        self._child = wexpect.spawn(
            exe, args=wexpect_args, encoding=self._encoding
        )
        # improving_73 DEF-73-001：原以 self._child.logfile_read = _RawLogAdapter(...) 擷取 raw，
        # 但 wexpect 4.0.0 的 logfile_read callback 於 expect() 過程**完全不觸發**（零成本探針實證：
        # 簡單正確指令、child.after 確讀到全部行，logfile_read 仍捕獲 0 字元）→ raw log 0 bytes
        # 觀測缺口。改於 _readline_wexpect 讀到行時顯式寫 raw_logger（鏡像 subprocess 路徑），
        # 不再依賴從不觸發的 callback；因 callback 從不觸發故無雙重記錄之虞。
        logger.info("wexpect 模式啟動：%s args=%r", exe, wexpect_args)

    def _start_subprocess(self) -> None:
        resolved = _resolve_command(self._command)
        if _is_cmd_shim(resolved):
            # .cmd/.bat shim：見 _build_cmd_shim_line() 說明。傳「字串」而非 list——
            # Windows 上 shell=False 時 Popen 對字串型 args 直接透傳給 CreateProcess，
            # 不會再被 list2cmdline 二次加引號破壞我們手動組好的命令列。
            argv: list[str] | str = _build_cmd_shim_line(resolved[2], list(self._args))
        else:
            argv = resolved + self._args
        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=propagate_to_subprocess_env(dict(os.environ)),
        )
        self._reader = NonBlockingStreamReader(self._proc.stdout)
        logger.info("subprocess 模式啟動：%s", argv)

    # ------------------------------------------------------------------
    # 讀取一行（非阻塞）
    # ------------------------------------------------------------------
    def readline(self, timeout: float = 0.2) -> str | None:
        """回傳解碼後的一行，timeout 內無輸出回傳 ''，結束回傳 None。"""
        if _WEXPECT_AVAILABLE and self._child:
            return self._readline_wexpect(timeout)
        return self._readline_subprocess(timeout)

    def _readline_wexpect(self, timeout: float) -> str | None:
        try:
            index = self._child.expect(
                [r".+\r?\n", wexpect.TIMEOUT, wexpect.EOF],
                timeout=timeout,
            )
            if index == 0:
                line = self._child.after
                # DEF-73-001：顯式擷取 raw（wexpect logfile_read callback 不觸發），
                # 鏡像 subprocess 路徑
                if self._raw_logger and line:
                    self._raw_logger.write(line.encode(self._encoding, errors="replace"))
                self._auto_respond(line)
                return line
            if index == 2:
                # DEF-73-001：EOF 前若有未換行殘留 buffer（child.before），結束前顯式擷取，
                # 與 subprocess 路徑（iter readline 回傳 EOF 前最後一段未換行 chunk）對稱、
                # 避免尾段遺失。
                tail = getattr(self._child, "before", None)
                if self._raw_logger and tail:
                    self._raw_logger.write(tail.encode(self._encoding, errors="replace"))
                return None
            return ""
        except Exception as exc:
            logger.debug("wexpect readline 例外: %s", exc)
            return ""

    def _readline_subprocess(self, timeout: float) -> str | None:
        raw = self._reader.readline(timeout)
        if raw is None:
            return None
        if not raw:
            return ""
        line = raw.decode(self._encoding, errors="replace")
        if self._raw_logger:
            self._raw_logger.write(raw)
        self._auto_respond(line)
        return line

    # ------------------------------------------------------------------
    # 傳送指令
    # ------------------------------------------------------------------
    def send(self, text: str) -> None:
        if _WEXPECT_AVAILABLE and self._child:
            self._child.sendline(text)
        elif self._proc and self._proc.stdin:
            self._proc.stdin.write((text + "\n").encode(self._encoding))
            self._proc.stdin.flush()

    # ------------------------------------------------------------------
    # 內部：自動回應授權提示
    # ------------------------------------------------------------------
    def _auto_respond(self, line: str) -> None:
        clean = strip_ansi(line)
        for pattern in self._auth_patterns:
            if pattern.search(clean):
                logger.debug("偵測到授權提示，自動回應: %r", line.strip())
                self.send(self._auth_response.strip())
                break

    # ------------------------------------------------------------------
    # 關閉
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._child:
            try:
                self._child.close(force=True)
            except Exception:
                pass
        if self._proc:
            # .cmd/.bat shim（見 _build_cmd_shim_line）啟動的是外層 cmd.exe，
            # terminate()（Windows 對映 TerminateProcess）只殺這層直接子行程；
            # 其下真正執行 CLI 的孫行程會變孤兒繼續跑（P1，真實子行程重現：
            # 外層 cmd.exe terminate 後 poll()==1 已死，孫行程 PID 仍存活、
            # ParentProcessId 指向已死行程、繼續執行至逾時）。Windows 上先用
            # `taskkill /T /F` 遞迴終止整棵行程樹涵蓋此缺口，再呼叫
            # terminate() 作為既有防線（對已死行程安全，Popen.terminate()
            # 內部吞掉 ERROR_ACCESS_DENIED）。pid 須為真實整數才觸發——
            # 測試以 MagicMock 充當 self._proc，其 `.pid` 非 int，自然跳過、
            # 不會在單元測試中真的呼叫 taskkill。
            if sys.platform == "win32" and isinstance(self._proc.pid, int):
                try:
                    subprocess.run(
                        ["taskkill", "/T", "/F", "/PID", str(self._proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                except Exception:
                    pass
            self._proc.terminate()
        if self._reader:
            self._reader.close(timeout=1.0)
        if self._raw_logger:
            self._raw_logger.close()

    @property
    def is_alive(self) -> bool:
        if self._child:
            return self._child.isalive()
        if self._proc:
            return self._proc.poll() is None
        return False
