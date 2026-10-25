"""SelfImproving 稽核檔落地（TCS-SelfImprovingDecide-P2b W2；PRD §9.5 ADR-SI-03′）。

Console 的決定與帳本寫入**不直接寫帳本**：backend 簽好稽核 JSON（HMAC），Bridge 只負責把這份
位元組原樣落在 `BRIDGE_SI_AUDIT_DIR/<audit_ref>.json`，再由主機端根層 CLI（`--carrier console`）驗簽
入帳。本檔是整個 `app/` **唯一**以寫入形態開啟 SI 路徑的模組，且路徑只能源自參數 `audit_dir`；
tests/test_si_readonly_lock.py 的 AST 鎖鎖的就是這兩件事（不得有字面路徑、`Path.home()`、環境變數
讀取）。

  · 檔名只源自已驗過的 `audit_ref`（整串為小寫正規 UUID，否則 `ValueError`；路由層先擋成 422）。
  · `os.open(O_WRONLY|O_CREAT|O_EXCL`，Windows 加 `O_BINARY`）獨佔建檔 → 寫入全部位元組 → `fsync` →
    關閉。同名已存在＝409 `si_audit_exists`（不覆寫）；其他 `OSError`（目錄不存在或不可寫、磁碟
    滿…）＝503 `si_unavailable`（cause `audit_write_failed`，detail 只有 errno 與例外類名、不含任何
    路徑），寫到一半失敗會刪除半成品。
  · 不建立 `audit_dir`（缺席＝部署問題，要明確失敗）；不使用 `os.replace`／`rename`／`move`
    （根層目錄項原語站點普查不增站點）。

跨平台：Windows 行為＝`O_BINARY` 避免 CRLF 轉換（以 `getattr(os, "O_BINARY", 0)` 取，POSIX 為 0）；
`O_EXCL` 在兩個平台語意相同。並行讀者可能讀到半成品——主機端 CLI 以 `audit_sha256` 與 mac 驗證，
半成品必拒，檔寫完後可重試入帳（TCS 已知邊界 12）。
"""
from __future__ import annotations

import errno
import logging
import os
import re
from pathlib import Path

from .errors import ApiError

logger = logging.getLogger("bridge.si_audit")

#: 小寫正規 UUID（8-4-4-4-4-12）；`fullmatch` 使結尾換行、前後空白、`.json` 尾綴一律不合。
_AUDIT_REF = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def is_audit_ref(value: object) -> bool:
    """整串為小寫正規 UUID（W2、W3）；非字串一律 False。"""
    return isinstance(value, str) and _AUDIT_REF.fullmatch(value) is not None


def _write_failed(exc: OSError) -> ApiError:
    """503 `si_unavailable`：detail 只含 errno 與例外類名——不含 `exc.filename`／訊息，因為那裡
    有絕對路徑。日誌同樣只記這兩項。"""
    name = type(exc).__name__
    logger.warning("si 稽核檔寫入失敗：errno=%s type=%s", exc.errno, name)
    return ApiError(503, "si_unavailable", cause="audit_write_failed",
                    detail=f"errno={exc.errno}; {name}")


def store_audit(audit_dir: Path, audit_ref: str, raw: bytes) -> None:
    """把 `raw` 原樣寫成 `audit_dir/<audit_ref>.json`（獨佔建檔、不覆寫、不回傳路徑）。

    `audit_ref` 非小寫正規 UUID＝`ValueError`（呼叫端的 bug；路由層已先擋）；同名已存在＝
    `ApiError(409, "si_audit_exists")`；其餘 `OSError`＝`ApiError(503, "si_unavailable")`。"""
    if not is_audit_ref(audit_ref):
        raise ValueError("audit_ref 須整串為小寫正規 UUID")
    target = audit_dir / f"{audit_ref}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(target, flags, 0o644)
    except FileExistsError:
        raise ApiError(409, "si_audit_exists") from None
    except OSError as exc:
        raise _write_failed(exc) from None
    try:
        try:
            view = memoryview(raw)
            while view:
                written = os.write(fd, view)
                if written <= 0:                    # 不該發生；免得無窮迴圈
                    raise OSError(errno.EIO, "os.write 回報寫入 0 位元組")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        # 寫到一半失敗：刪除自己剛建的半成品（路徑與開檔同源，AST 鎖看得到）；刪不掉就留日誌，
        # 不遮蓋原本的失敗。
        try:
            os.unlink(target)
        except OSError as cleanup:
            logger.warning("si 稽核檔半成品清除失敗：errno=%s type=%s", cleanup.errno,
                           type(cleanup).__name__)
        raise _write_failed(exc) from None
