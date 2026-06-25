"""
Windows PTY 包裝器。
使用 wexpect 模擬終端，讓 Claude Code 認為自己在 TTY 環境中執行。
若 wexpect 不可用，退回到 subprocess + NonBlockingStreamReader。
"""
from __future__ import annotations
import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional

from .stream_reader import NonBlockingStreamReader
from .text_utils import strip_ansi
from ..utils.logger import RawStreamLogger
from ..utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger("autoclaude.perception")

try:
    import wexpect  # type: ignore
    _WEXPECT_AVAILABLE = True
except ImportError:
    _WEXPECT_AVAILABLE = False
    logger.warning("wexpect 未安裝，改用 subprocess 模式（部分互動提示可能無法自動回應）")


class PtyWrapper:
    def __init__(
        self,
        command: str,
        args: list[str],
        auth_patterns: list[str],
        auth_response: str,
        raw_log_path: Optional[Path] = None,
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
        self._reader: Optional[NonBlockingStreamReader] = None

    # ------------------------------------------------------------------
    # 啟動
    # ------------------------------------------------------------------
    def start(self) -> None:
        if _WEXPECT_AVAILABLE:
            self._start_wexpect()
        else:
            self._start_subprocess()

    def _start_wexpect(self) -> None:
        # improving_72 DEF-72-001：原以 " ".join([command]+args) 把含反引號/換行/分號的
        # 多行 prompt 拼成單一 shell 字串傳 wexpect.spawn → 被 shell 解析搞爛（反引號當命令
        # 替換、換行斷句），claude 收到殘缺指令、raw log 0 bytes（pty-vs-sdk 真跑揭露：
        # 簡單 prompt 可擷取、複雜 prompt 全空）。改以 args=list 傳遞（wexpect.spawn 原生
        # 支援；零 token 探針證實 list 路徑 prompt 原樣抵達子程序），不再經 shell parsing。
        self._child = wexpect.spawn(
            self._command, args=list(self._args), encoding=self._encoding
        )
        if self._raw_logger:
            self._child.logfile_read = _RawLogAdapter(self._raw_logger, self._encoding)
        logger.info("wexpect 模式啟動：%s args=%r", self._command, self._args)

    def _start_subprocess(self) -> None:
        self._proc = subprocess.Popen(
            [self._command] + self._args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=propagate_to_subprocess_env(dict(os.environ)),
        )
        self._reader = NonBlockingStreamReader(self._proc.stdout)
        logger.info("subprocess 模式啟動：%s", [self._command] + self._args)

    # ------------------------------------------------------------------
    # 讀取一行（非阻塞）
    # ------------------------------------------------------------------
    def readline(self, timeout: float = 0.2) -> Optional[str]:
        """回傳解碼後的一行，timeout 內無輸出回傳 ''，結束回傳 None。"""
        if _WEXPECT_AVAILABLE and self._child:
            return self._readline_wexpect(timeout)
        return self._readline_subprocess(timeout)

    def _readline_wexpect(self, timeout: float) -> Optional[str]:
        try:
            index = self._child.expect(
                [r".+\r?\n", wexpect.TIMEOUT, wexpect.EOF],
                timeout=timeout,
            )
            if index == 0:
                line = self._child.after
                self._auto_respond(line)
                return line
            if index == 2:
                return None
            return ""
        except Exception as exc:
            logger.debug("wexpect readline 例外: %s", exc)
            return ""

    def _readline_subprocess(self, timeout: float) -> Optional[str]:
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


class _RawLogAdapter:
    """將 wexpect logfile_read 的字串寫入 RawStreamLogger。"""

    def __init__(self, raw_logger: RawStreamLogger, encoding: str):
        self._raw = raw_logger
        self._enc = encoding

    def write(self, s: str) -> None:
        self._raw.write(s.encode(self._enc, errors="replace"))

    def flush(self) -> None:
        pass
