"""`spec-frozen --digest` 的純函式：換行正規化摘要、路徑正規化、超限判斷（ADR-XPLAT-016 §4.3）。

為什麼凍結要「綁內容」：`FSM-STATE-*.yaml` 的 `frozen_stages[*].spec_docs` 原本只記檔名字面，
凍結後改檔、換檔都看不出來；本模組讓 CLI 在凍結當下對每份規格檔算出摘要，寫進
`frozen_stages[-1].spec_doc_digests`，編譯與執行前再比對（AutoClaude adapter／Bridge 端），
改檔即 fail-closed。

摘要演算法（ADR §4.3，S4 定案；**正規化文字，不是原始 bytes**）：
  `sha256` over **換行正規化後的 UTF-8 bytes**——先 `\\r\\n`→`\\n`、再 `\\r`→`\\n`；BOM 不剝。
  這與 AutoClaude `sdd_to_playbook_adapter` 的 `SddSpec.digest`
  ＝`sha256(Path.read_text(encoding="utf-8").encode("utf-8"))` 逐位元相同（`read_text` 的通用換行
  轉換＋不剝 BOM）。Windows 上編輯器存成 CRLF 是常態，用原始 bytes 會讓每次比對假紅。
  檔案必須是合法 UTF-8（adapter 讀不了的檔不該被凍結），否則 `doc_not_utf8`。
  AutoClaude／Bridge 各自持有等價的兩行實作，一致性由對拍測試守；**本檔不得 import 其他子專案**
  （ADR-XPLAT-010 §2.1）。

路徑規則（ADR §4.3）：每個 `--doc` 可絕對或相對（相對＝相對 `root`）；`resolve()` 後必須落在
`root` 之下（跟隨 symlink，指向根外同樣 `doc_outside_root`，fail-closed），記成 **POSIX 相對於
root** 的字串。鍵取自 `resolve()` 後的路徑 ⇒ 鍵與實際被讀的內容一一對應（不會出現「鍵寫
`docs/x.md`、內容卻來自 symlink 另一端」）；POSIX 上等同 `--doc` 字面，Windows 上是磁碟實際的
大小寫（比對端以 `os.path.normcase` 兩邊折疊，見 adapter）。

錯誤一律拋 `SpecDocError`（`ValueError` 子類），`code` 即 CLI stdout JSON 的 `error` 欄：
`doc_not_found`／`doc_outside_root`／`doc_too_large`／`doc_not_utf8`（rc 4）。
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

#: 單一規格檔上限（16 MiB）：Bridge 的 `docs[]` 受白名單根限制、但檔案本身可能很大，
#: 不能讓一次凍結卡住。
MAX_DOC_BYTES = 16 * 1024 * 1024

#: 摘要值格式 `"sha256:<64 位小寫 hex>"`（與 adapter 的 `SddSpec.digest` 同形）。
DIGEST_PREFIX = "sha256:"

# 慣例狀態目錄的尾三段；`derive_root()` 靠它從 `state_dir()` 反推專案根。
_CONVENTIONAL_STATE_TAIL = ("build", "reports", "fsm")


class SpecDocError(ValueError):
    """某份 `--doc` 無法納入凍結摘要。`code` 是 CLI JSON 的 `error` 代碼。"""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def is_too_large(size: int) -> bool:
    """超過單檔上限（`size > MAX_DOC_BYTES`；恰好等於上限仍放行）。"""
    return size > MAX_DOC_BYTES


def normalize_newlines(raw: bytes) -> bytes:
    """`\\r\\n`→`\\n`、再 `\\r`→`\\n`（UTF-8 的多位元組序列不含 0x0D／0x0A，直接在 bytes 上換安全）。"""
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest_bytes(raw: bytes, *, label: str = "") -> str:
    """回 `"sha256:<hex>"`；`raw` 不是合法 UTF-8 ⇒ `SpecDocError("doc_not_utf8")`。"""
    try:
        raw.decode("utf-8")  # 嚴格解碼；BOM 不剝（與 read_text(encoding="utf-8") 一致）
    except UnicodeDecodeError as exc:
        raise SpecDocError(
            "doc_not_utf8", f"{label or 'document'} is not valid UTF-8 ({exc.reason})"
        ) from exc
    return DIGEST_PREFIX + hashlib.sha256(normalize_newlines(raw)).hexdigest()


def derive_root(state_directory: Path, fallback: Path) -> Path:
    """`--root` 省略時的專案根：狀態目錄以 `build/reports/fsm` 結尾 ⇒ 取其上三層，否則 `fallback`。

    大小寫比對走 `os.path.normcase`（Windows 折疊、POSIX 原樣；只對單一路徑段使用，不會碰到
    `/`→`\\` 的轉換問題）。自訂 `SDD_STATE_DIR` 落在慣例之外而未給 `--root` 時回 `fallback`
    （框架自身專案根），之後 `doc_not_found` 會大聲失敗，不會靜默算錯檔。
    """
    parts = state_directory.parts
    if len(parts) > 3 and tuple(os.path.normcase(p) for p in parts[-3:]) == _CONVENTIONAL_STATE_TAIL:
        return Path(*parts[:-3])
    return fallback


def normalize_doc(root: Path, doc: str) -> Tuple[Path, str]:
    """回 `(解析後的真實檔案路徑, POSIX 相對 root 的鍵)`。

    檢查順序（先擋根外、再看存在，不對根外路徑洩漏存在與否）：落在 root 之下 →
    `doc_outside_root`；是檔案 → `doc_not_found`（缺檔或是目錄）。
    """
    base = root.resolve()
    candidate = Path(doc)
    full = (candidate if candidate.is_absolute() else base / candidate).resolve()
    try:
        rel = full.relative_to(base)
    except ValueError:
        raise SpecDocError("doc_outside_root", f"{doc} resolves outside the root") from None
    key = rel.as_posix()
    if not full.is_file():
        raise SpecDocError("doc_not_found", f"{key} is missing or not a regular file")
    return full, key


def digest_doc(root: Path, doc: str) -> Tuple[str, str]:
    """回 `(鍵, 摘要)`；檔案以有界讀取（最多 `MAX_DOC_BYTES + 1` bytes）判斷超限。"""
    full, key = normalize_doc(root, doc)
    try:
        with full.open("rb") as fh:
            raw = fh.read(MAX_DOC_BYTES + 1)
    except OSError as exc:
        raise SpecDocError("doc_not_found", f"{key} cannot be read (errno={exc.errno})") from exc
    if is_too_large(len(raw)):
        raise SpecDocError("doc_too_large", f"{key} exceeds {MAX_DOC_BYTES} bytes")
    return key, digest_bytes(raw, label=key)


def digest_docs(root: Path, docs: Iterable[str]) -> Tuple[List[str], Dict[str, str]]:
    """對多份 `--doc` 一次做完：回 `(依首見順序去重的鍵清單, {鍵: 摘要})`。

    `spec_docs` 與摘要鍵必須是**同一組**正規化字串，所以呼叫端用回傳的鍵清單寫 `spec_docs`。
    兩個 `--doc` 解析到同一檔時只留一筆（凍結同一份檔兩次沒有意義）。
    """
    keys: List[str] = []
    digests: Dict[str, str] = {}
    for doc in docs:
        key, digest = digest_doc(root, doc)
        if key not in digests:
            keys.append(key)
        digests[key] = digest
    return keys, digests
