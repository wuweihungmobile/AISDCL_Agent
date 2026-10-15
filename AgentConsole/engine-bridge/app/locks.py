"""並發互斥（PRD §0.2.2）：同 project＋execution_path 同時只准一個 run。

鎖鍵＝`project || ':' || execution_path`（路徑先 normcase：Windows 不分大小寫，`C:\\Proj` 與
`c:\\proj` 必須撞鎖）。兩層：
  · 行程內鎖表（`LockTable`）：檔案模式的全部，DB 模式的第一道（同實例內即時互斥、可回報 holder）。
  · DB 模式再加 PostgreSQL session 級 advisory lock：`pg_try_advisory_lock(hashtext(key))`，
    **每把持有中的鎖獨佔一條專用連線**（session 鎖綁連線，連線關了鎖就沒了，所以不能走連線池）。
    連線設了 TCP keepalive，降低「閒置連線被中間設備砍掉、鎖無聲消失」的機率。
取不到＝`LockBusy`（呼叫端回 409）；DB 連不上＝`LockUnavailable`（呼叫端回 503，不退化成只有
行程內鎖——那會讓多實例部署在 DB 掛掉時悄悄失去互斥）。

同一個 run 對同一把鎖重取＝冪等（PAUSED 的 run 被 restore 就是這種：暫停期間它持著鎖）：專用連線
還在、PG 鎖還在它手上，所以不新開連線、不動登記。新連線去搶同一把 session 級鎖，只會被這個 run
自己的舊連線擋下；若失敗路徑再撤掉登記，舊連線就永遠沒人關、鎖洩漏到 Bridge 重啟為止（AR-01）。
失敗路徑只撤回「這次呼叫自己新增的」登記，絕不讓既有的持鎖連線脫離登記。
"""
from __future__ import annotations

import logging
import os
import threading
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NamedTuple

logger = logging.getLogger("bridge.locks")


class LockBusy(Exception):
    def __init__(self, key: str, holder_run_id: str | None):
        super().__init__(f"鎖已被持有：{key}（holder={holder_run_id}）")
        self.key = key
        self.holder_run_id = holder_run_id


class LockUnavailable(Exception):
    """鎖後端（DB）不可用：不能確認互斥，所以拒絕而不是放行。"""


@dataclass(frozen=True)
class LockInfo:
    key: str
    db_key: int | None = None       # hashtext(key)；檔案模式為 None


def make_lock_key(project: str, execution_path: str) -> str:
    # NFC：macOS 可能把同一個目錄回報成 NFD 形式，兩種寫法必須撞同一把鎖。
    path = unicodedata.normalize("NFC", os.path.normcase(execution_path))
    return f"{unicodedata.normalize('NFC', project)}:{path}"


class LockTable:
    """行程內的 key → holder_run_id 表（thread-safe）。"""

    def __init__(self) -> None:
        self._held: dict[str, str] = {}
        self._mutex = threading.Lock()

    def acquire(self, key: str, run_id: str) -> bool:
        """登記 key 給 run_id。回傳 True＝這次呼叫新登記的；False＝本來就是這個 run 持有
        （冪等重取）。別的 run 持有 → LockBusy，登記表原封不動。"""
        with self._mutex:
            holder = self._held.get(key)
            if holder is None:
                self._held[key] = run_id
                return True
            if holder != run_id:
                raise LockBusy(key, holder)
            return False

    def release(self, key: str, run_id: str) -> bool:
        """只有持有者能放；回傳是否真的放了。"""
        with self._mutex:
            if self._held.get(key) == run_id:
                del self._held[key]
                return True
            return False

    def holder(self, key: str) -> str | None:
        with self._mutex:
            return self._held.get(key)


class _PgHold(NamedTuple):
    """一把持有中的 PG advisory lock：獨佔的專用連線，加上它對應的 hashtext(key)。"""

    conn: Any
    db_key: int


def _conn_key(key: str, run_id: str) -> str:
    return f"{key}\0{run_id}"


class AdvisoryLock:
    """對外的鎖介面。`dsn=None`＝純檔案模式。"""

    def __init__(self, dsn: str | None = None, *,
                 holder_lookup: Callable[[int], str | None] | None = None):
        self._dsn = dsn
        self._table = LockTable()
        self._conns: dict[str, _PgHold] = {}          # _conn_key(key, run_id) → 專用連線
        self._conn_mutex = threading.Lock()
        self._holder_lookup = holder_lookup

    @property
    def db_mode(self) -> bool:
        return self._dsn is not None

    def acquire(self, project: str, execution_path: str, run_id: str) -> LockInfo:
        key = make_lock_key(project, execution_path)
        # 同實例：即時、可回報 holder。別的 run 持有 → LockBusy，登記表原封不動；
        # registered＝False 表示這個 run 本來就持有（重取），登記不是這次呼叫新增的。
        registered = self._table.acquire(key, run_id)
        if self._dsn is None:
            return LockInfo(key)
        with self._conn_mutex:
            held = self._conns.get(_conn_key(key, run_id))
        if held is not None:
            return LockInfo(key, held.db_key)         # 冪等：連線與 PG 鎖都還在它手上（見檔頭）
        try:
            return LockInfo(key, self._acquire_db(key, run_id))
        except BaseException:
            if registered:                            # DB 那層失敗：撤回這次新增的登記，不多撤
                self._table.release(key, run_id)
            raise

    def _acquire_db(self, key: str, run_id: str) -> int:
        import psycopg  # 延遲匯入：純檔案模式不需要 psycopg 可用

        try:
            conn = psycopg.connect(
                self._dsn, autocommit=True, connect_timeout=5,
                keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
        except psycopg.Error as exc:
            raise LockUnavailable(f"無法連線 PostgreSQL 取得 advisory lock：{exc}") from exc
        try:
            row = conn.execute(
                "SELECT pg_try_advisory_lock(hashtext(%s)), hashtext(%s)", (key, key)).fetchone()
        except psycopg.Error as exc:
            conn.close()
            raise LockUnavailable(f"advisory lock 查詢失敗：{exc}") from exc
        locked, db_key = bool(row[0]), int(row[1])
        if not locked:
            conn.close()
            holder = self._holder_lookup(db_key) if self._holder_lookup else None
            raise LockBusy(key, holder)               # 別的 Bridge 實例持有
        with self._conn_mutex:
            self._conns[_conn_key(key, run_id)] = _PgHold(conn, db_key)
        return db_key

    def release(self, key: str, run_id: str) -> None:
        self._table.release(key, run_id)              # 只有持有者能放；登記早已不在也不影響下面
        with self._conn_mutex:
            hold = self._conns.pop(_conn_key(key, run_id), None)
        if hold is not None:
            # 連線是 (key, run_id) 專屬的：登記表放沒放成都得收掉它，否則連線與 PG 鎖就洩漏了。
            try:
                hold.conn.execute("SELECT pg_advisory_unlock(hashtext(%s))", (key,))
            except Exception as exc:                  # noqa: BLE001 — 連線已死也等於鎖已釋放
                logger.warning("advisory unlock 失敗（連線關閉即釋放）：%s", exc)
            finally:
                try:
                    hold.conn.close()
                except Exception:                     # noqa: BLE001
                    pass

    def holder(self, key: str) -> str | None:
        return self._table.holder(key)

    def close(self) -> None:
        with self._conn_mutex:
            holds, self._conns = list(self._conns.values()), {}
        for hold in holds:
            try:
                hold.conn.close()
            except Exception:                         # noqa: BLE001
                pass
