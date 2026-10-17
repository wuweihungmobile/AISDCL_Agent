"""規格檔摘要（ADR-XPLAT-016 §4.3／§6；F-6）：與 SDD CLI 的 `spec_doc_digests`、AutoClaude
adapter 的 `SddSpec.digest` **同一個演算法**的 Bridge 鏡像。

演算法＝`sha256` over **換行正規化後的 UTF-8 文字**：先 `\\r\\n`→`\\n`、再 `\\r`→`\\n`；BOM 不剝。
不是原始 bytes：Windows 編輯器存成 CRLF 是常態，用原始 bytes 會讓每次比對假紅（ADR §4.3）。
這與 adapter 的 `sha256(read_text(encoding="utf-8").encode("utf-8"))` 逐位元相同（`read_text` 的通
用換行轉換就是上面那兩步，且 `encoding="utf-8"` 不剝 BOM）。格式：`sha256:<64 位小寫 hex>`。

三處各持一份兩行實作（CLI、adapter、這裡），不得跨子專案 import（ADR-XPLAT-010 §2.1）；
一致性由 tests/test_sdd_integration_parity.py（F-6）與 tests/test_spec_digest.py 守。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: 單一規格檔大小上限（ADR §4.3：超過 16 MiB 拒絕，免得一次凍結／比對卡住）。
MAX_DOC_BYTES = 16 * 1024 * 1024


class DocTooLargeError(ValueError):
    """檔案超過 `MAX_DOC_BYTES`。"""


class DocNotUtf8Error(ValueError):
    """檔案不是合法 UTF-8（adapter 讀不了的檔不該被凍結或比對）。"""


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_newlines(text).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    """檔案的規格摘要。缺檔／目錄／讀取失敗＝OSError；過大＝DocTooLargeError；非 UTF-8＝
    DocNotUtf8Error。"""
    size = path.stat().st_size
    if size > MAX_DOC_BYTES:
        raise DocTooLargeError(f"{path.name}：{size} bytes 超過上限 {MAX_DOC_BYTES}")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")           # 嚴格解碼；"utf-8"（非 utf-8-sig）所以 BOM 留作 U+FEFF
    except UnicodeDecodeError as exc:
        raise DocNotUtf8Error(f"{path.name} 不是合法 UTF-8") from exc
    return text_digest(text)
