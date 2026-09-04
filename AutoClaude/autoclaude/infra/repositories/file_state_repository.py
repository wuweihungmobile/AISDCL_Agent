"""FileStateRepository — IQueryableStateRepository 的 File 後端（Phase 5 W1b）。

W1b（SD_03 §3.1）：移除對 CheckpointManager 的依賴，直接實作 atomic JSON 讀寫。
CheckpointManager 現在反向委派至本類別（薄包裝器）。
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from ...core.ports.state_repository import (
    CheckpointCorruptError,
    StateRepositoryError,
)
from ...utils.checkpoint_manager import (
    CHECKSUM_FIELD,
    PlaybookCheckpoint,
    checkpoint_digest,
)
from ...utils.logger import _sanitize_log_filename
from ...utils.resume_clock import seconds_until as resume_clock_seconds_until
from ._deprecation import warn_load_checkpoint_deprecated

logger = logging.getLogger("autoclaude.infra.file_state")

_SUFFIX = ".checkpoint.json"

# R100 P2-C（PRD §8-4 第 4 列）：「若 checksum 失敗 → 回退到 STATE_RETAIN_VERSIONS 中最近
# 的**有效**版本」。沒有這一層，②（CORRUPT 不再靜默回 None）的代價是「壞一份就整場停」——
# 而 fail-loud 的正解是**先退回上一個驗得過的版本**，不是停機，也不是靜默從 0 重跑。
# 值域 0..9；0＝不保留（合法，退化成純 fail-loud）。保留檔名＝`<原名>.v1`、`.v2`…（`.v1`
# 最新）。刻意不進 `*{_SUFFIX}` 的 glob 面 ⇒ list_recent_checkpoints 不會把它們當獨立條目。
# 出廠值 5＝PRD §6 區塊 12 字面（DEF-200-206 ①：鍵名前綴修憲、數值三方定案採 PRD）。
STATE_RETAIN_VERSIONS = max(0, min(9, int(
    os.environ.get("AUTOCLAUDE_STATE_RETAIN_VERSIONS", "5") or 0)))


#: DEF-200-226：`.tmp` 檔名自 DEF-200-043 起帶 pid+uuid4，寫入中途行程崩潰
#: （OOM／SIGKILL）留下的 tmp 不再被「下一次同 playbook_id 寫入」自然覆蓋清理，
#: 會逐次累積孤兒檔。正常寫入的 tmp 檔案齡是毫秒級，遠低於此門檻，故只清「夠舊」
#: 的檔不會誤刪正在進行中的併發寫入。
_STALE_TMP_SECONDS = 3600


#: `tmp_p` 的實際命名格式（見 `save_checkpoint`）：`{stem}.{pid}.{uuid4().hex}.tmp`。
#: pid 恆為十進位數字、`uuid4().hex` 恆為小寫十六進位字串——兩者的字元集皆不含 `.`，
#: 故以 `.` 分隔後可精確反解，不會與 `stem` 本身混淆。
_ORPHAN_TMP_SUFFIX_RE = r"\.\d+\.[0-9a-f]+\.tmp\Z"


#: DEF-200-229：Windows 上 CPython 開檔不帶 FILE_SHARE_DELETE ⇒ 任何讀者（本函式
#: 自己的 prev 讀取、load_latest_by_playbook、外部檢視器）持有目的檔把手的瞬間，
#: `os.replace` 會以 PermissionError（winerror=5）拒絕換名——POSIX 的 rename 對開著
#: 的檔恆成功，故本缺口只在 Windows 真機現形（首見＝pre-push 全套＋雙重負載下
#: DEF-200-043 的併發測試機率性紅）。讀者把手是毫秒級瞬態 ⇒ 有界重試等它放手
#: （預算 15×20ms=300ms），等不到再如實拋出、由呼叫端照舊收斂成 StateRepositoryError。
_REPLACE_RETRIES = 15
_REPLACE_RETRY_INTERVAL_S = 0.02


def _replace_waiting_out_readers(tmp_p: Path, p: Path) -> None:
    """`tmp_p.replace(p)`，容忍 Windows 讀者短暫持有 `p` 把手（見 `_REPLACE_RETRIES`）。"""
    for attempt in range(_REPLACE_RETRIES):
        try:
            tmp_p.replace(p)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(_REPLACE_RETRY_INTERVAL_S)


def _cleanup_orphan_tmp(p: Path) -> None:
    """清掉 `p` 這個 checkpoint 路徑遺留的孤兒 `.tmp` 檔（見 `_STALE_TMP_SECONDS`）。

    🔴 `glob(f"{p.stem}.*.tmp")` 本身是**前綴**匹配：若某個 playbook 的 sanitized
    stem 恰好是另一個 playbook stem 的前綴（例如 `nightly_run.checkpoint` 是
    `nightly_run.checkpoint.retry.checkpoint.json` 的前綴），寬鬆的 `*` 會連對方的
    孤兒 tmp 一併掃進來、進而誤刪——SD 已用兩個 playbook 實際重現。改用
    `re.fullmatch()` 精確比對 `p.stem` 之後緊接的 tmp 檔名格式（見 `_ORPHAN_TMP_SUFFIX_RE`），
    只有 stem 逐字相等的檔案才會被當成 `p` 自己的孤兒；glob 只用來縮小候選集合，
    不再是唯一的判準。
    """
    pattern = re.compile(re.escape(p.stem) + _ORPHAN_TMP_SUFFIX_RE)
    for orphan in p.parent.glob(f"{p.stem}.*.tmp"):
        if not pattern.fullmatch(orphan.name):
            continue
        with suppress(OSError):
            if time.time() - orphan.stat().st_mtime > _STALE_TMP_SECONDS:
                orphan.unlink()


def retained_paths(p: Path) -> list[Path]:
    # `.v1` 最新 ⇒ 依編號升冪就是「由新到舊」，回退時第一個驗得過的就是最近的有效版本。
    return sorted((q for q in p.parent.glob(p.name + ".v*") if q.is_file()),
                  key=lambda q: int(q.suffix[2:] or 0))


def _retain_previous(p: Path, prev: bytes | None, keep: int) -> None:
    """在 tmp → p 的原子換名**成功之後**才跑（R100 收尾 blocker；取證＝
    `docs/06_quality/CrossPlatform_R100_Scan_Findings.md` §E 那一輪，承接列 DEF-200-207）。

    修法前這裡是「先把現行 p 推成 .v1，**再** replace」。於是 replace 失敗（ENOSPC
    不需斷電就到得了）或在兩個換名之間斷電時，主檔的**目錄項不存在** ⇒
    `load_latest_by_playbook` 的 `not p.exists()` 判成「沒有 checkpoint」而回 None，
    呼叫端靜默從 step 0 重跑整份 playbook——旁邊那份有效的 `.v1` 一個字都沒被讀到。
    🔴 它打掉的正是同輪剛修好的「CORRUPT ≠ None」：那個修法讓「損壞」與「沒有」
    分家，這個順序缺陷讓「有效的舊版本」也變成「沒有」。

    誠實劃界（付出去的代價）：舊主檔改為先讀進記憶體、事後另寫一份，不再是零額外
    空間的換名 ⇒ 峰值多一份 checkpoint 檔的空間（原註解記載的「不多吃一份空間」
    正是為了磁碟滿）。這個交換是刻意的：**主檔的目錄項在任何瞬間都必須存在**，其
    優先序高於保留版本的空間效率；而保留這一段自己遇到 ENOSPC 時只降級、不失敗。
    """
    if keep <= 0 or prev is None:
        return
    # 刻意不叫 `.v*`：那個名字會落進 retained_paths 的 glob，而它的 int() 會當場炸。
    stage = p.with_name(f"{p.name}.prev.tmp")
    try:
        for n in range(keep, 0, -1):
            src, dst = p.with_name(f"{p.name}.v{n}"), p.with_name(f"{p.name}.v{n + 1}")
            if src.exists():
                if n == keep:
                    src.unlink()              # 超出保留份數 ⇒ 丟掉最舊的那一份
                else:
                    os.replace(src, dst)
        stage.write_bytes(prev)
        os.replace(stage, p.with_name(f"{p.name}.v1"))
    except OSError as exc:
        # 處置方向由**語意**決定：保留版本是主檔的補網、不是主線 ⇒ 輪替失敗**不得**讓
        # checkpoint 的儲存跟著失敗（此刻主檔已就位且內容已 fsync），但也不得靜默
        # （靜默的下場是「以為有退版可用」而其實沒有）。射程刻意是 OSError 而非只有
        # PermissionError：① 鐵律三「Windows 檔案鎖」那一列——目的檔被別的行程開著時
        # `os.replace` 回 WinError 5（POSIX 恆成功 ⇒ 開發機上重現不了）；② ENOSPC
        # ——本族的頭號成因，只捕 PermissionError 時它會穿出去把整次儲存拖紅。
        with suppress(OSError):
            stage.unlink(missing_ok=True)
        logger.warning("checkpoint 保留版本輪替失敗（%s）：本次不保留舊版，主檔已就位", exc)


class FileStateRepository:
    """File backend — atomic JSON read/write，不依賴 CheckpointManager。"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, playbook_id: str) -> Path:
        # DEF-101-384（R47）：playbook_id 經 canonical_playbook_id() 可能是
        # Path(playbook_path).stem（未過濾 Windows 禁用字元/保留裝置名），
        # 委派 SSOT `_sanitize_log_filename`（見 utils/logger.py 頂部說明），
        # 與 rtm_file_sink.py / translation_learning_sink.py / pty_executor.py 同一先例。
        return self._dir / f"{_sanitize_log_filename(playbook_id)}{_SUFFIX}"

    def state_bytes(self, playbook_id: str) -> int:
        """現存 state 檔的位元組數（檔不存在＝0）。供 PRD R-6.2-3 ② 的空間預估用。

        🔴 刻意是**公開方法**而不是讓呼叫端自己拼路徑：檔名經 `_sanitize_log_filename`
        正規化過（見 `_path`），把那段規則複製到呼叫端，下一次改規則就會靜默漂移到
        「量了一個不存在的檔」＝恆回 0 的假預估。`DEF-200-264`。
        """
        p = self._path(playbook_id)
        try:
            return p.stat().st_size
        except OSError:      # 不存在／無權限：預估用途下 0 是安全值（不是靜默降級）
            return 0

    def save_checkpoint(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        """符合 StateRepositoryPort 契約：回傳 None。"""
        try:
            p = self._path(playbook_id)
            _cleanup_orphan_tmp(p)
            checkpoint.saved_at = datetime.now().isoformat(timespec="seconds")
            payload = asdict(checkpoint)
            # 刻意**不**回寫 `checkpoint.checksum_sha256`：那是對呼叫端傳進來的物件
            # 動手腳，而 InMemory 後端沒有磁碟、結構上沒有這個值 ⇒ 回寫會讓 DAL 等價
            # 契約（tests/equivalence/test_sdd_checkpoint_equivalence.py）在**記憶體**
            # 這一側也失衡，而那道鎖守的是真的東西。值只住磁碟。
            payload[CHECKSUM_FIELD] = checkpoint_digest(payload)
            # DEF-200-043：純用 playbook_id 推導 tmp 檔名時，同一 playbook_id 的兩個
            # 行程／執行緒併發呼叫本函式會共用同一份 tmp 檔——兩邊的 `open("w")` 互相
            # truncate 對方尚未寫完的內容，其中一邊的 `replace()` 先把 tmp 檔換名走，
            # 另一邊隨後的 `replace()` 就會因 tmp 檔已不存在而 FileNotFoundError；更壞
            # 的是先失敗的那份反而可能是最後留在磁碟上的內容（見 R103 收尾重現實測）。round-label-ok
            # 加 pid + uuid4 讓每次呼叫的 tmp 檔名互不相同，同一 playbook_id 的併發寫入
            # 各自佔用獨立檔案，不再共用同一個 tmp 資源。
            tmp_p = p.with_suffix(f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
            # 舊主檔的內容先讀進記憶體：下一行的 replace 會原子覆蓋掉它，而保留版本
            # 只准在 replace **成功之後**才動（見 _retain_previous 的 docstring）。
            prev: bytes | None = None
            if STATE_RETAIN_VERSIONS > 0:
                with suppress(OSError):       # 第一次存（檔還不存在）也走這條
                    prev = p.read_bytes()
            try:
                with tmp_p.open("w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    # 🔴 R100 P2-C（PRD §8-4 ①）：`flush()` 只把資料交到 OS page cache。
                    # 斷電（正是本項要防的情境）時 rename 的目錄項可能先落地而內容沒有
                    # ⇒ 得到「檔在、內容截斷」的 checkpoint。R98 曾把「原子寫入已做」記為
                    # 完成，發現波駁回了那個判讀：`os.replace` 保證的是**換名原子**，
                    # 與**內容是否已落地**是兩件正交的事，缺 fsync 這一半沒有任何表徵。
                    f.flush()
                    os.fsync(f.fileno())
                _replace_waiting_out_readers(tmp_p, p)
            except Exception:
                tmp_p.unlink(missing_ok=True)
                raise
            _retain_previous(p, prev, STATE_RETAIN_VERSIONS)
            logger.info(
                "檢查點已儲存: %s | step_idx=%d [%s] token=%.1f%%",
                p, checkpoint.step_idx, checkpoint.step_id, checkpoint.peak_token_pct,
            )
        except OSError as exc:
            raise StateRepositoryError(f"save_checkpoint 失敗: {exc}") from exc

    def load_checkpoint(self, playbook_id: str) -> PlaybookCheckpoint | None:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook。

        env AUTOCLAUDE_DEPRECATION_WARN=1 時 emit DeprecationWarning。
        """
        warn_load_checkpoint_deprecated()
        return self.load_latest_by_playbook(playbook_id)

    def load_latest_by_playbook(
        self, playbook_id: str,
    ) -> PlaybookCheckpoint | None:
        """SD_06 W5-T5-7：載入指定 playbook_id 最新一筆 checkpoint。

        File backend 一個 playbook_id 對應一個檔案，自然就是 latest。
        """
        p = self._path(playbook_id)
        if not p.exists():
            return None                       # 「沒有 checkpoint」——唯一該回 None 的情形
        try:
            return self._read_verified(p)
        except CheckpointCorruptError as first:
            for older in retained_paths(p):
                try:
                    cp = self._read_verified(older)
                except CheckpointCorruptError:
                    continue
                # loud：退版是**降級**不是正常路徑，靜默退版會讓人以為讀到的是最新進度。
                logger.error("checkpoint 損毀（%s），已退回保留版本 %s（step_idx=%d）：%s",
                             p.name, older.name, cp.step_idx, first)
                return cp
            raise

    def _read_verified(self, p: Path) -> PlaybookCheckpoint:
        # 🔴 R100 P2-C（PRD §8-4 ②）：**檔在但讀不回來 ≠ 沒有 checkpoint**。
        # 修法前這裡是 `except Exception: return None`，於是一個截斷的 JSON 在呼叫端的
        # 外觀與「第一次跑」完全相同 ⇒ 靜默從 step 0 重跑一整份 playbook。
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            cp = PlaybookCheckpoint(**data)
        except Exception as exc:
            raise CheckpointCorruptError(
                f"checkpoint 檔存在但無法還原（{type(exc).__name__}: {exc}）：{p}。"
                "🔴 這**不是**「沒有 checkpoint」——不得靜默從 step 0 重跑；"
                "請人工檢視該檔（或用 --fresh 明確表示要放棄它）") from exc
        stored = data.get(CHECKSUM_FIELD) or ""
        if not stored:
            logger.warning(
                "檢查點無 %s 欄位（本工具 R100 之前寫的舊檔）：%s。"
                "完整性**無法驗證**——照載入，但這一格是誠實劃界不是通過",
                CHECKSUM_FIELD, p)
        elif stored != checkpoint_digest(data):
            raise CheckpointCorruptError(
                f"checkpoint checksum 不符：{p}（期望 {stored}，"
                f"實測 {checkpoint_digest(data)}）。內容在寫入後被改動或寫入未完成")
        logger.info(
            "已載入檢查點: step_idx=%d [%s]，儲存於 %s",
            cp.step_idx, cp.step_id, cp.saved_at,
        )
        return cp

    def load_by_run_id(self, run_id: str) -> PlaybookCheckpoint | None:
        """SD_06 W5-T5-7：遍歷 checkpoint 檔案找符合 run_id 的紀錄。

        File backend 不索引 run_id，效能 O(n)；用於 dev 環境。
        正式 production 環境請改用 PgStateRepository.load_by_run_id（indexed）。
        """
        if not run_id:
            return None
        for p in self._dir.glob(f"*{_SUFFIX}"):
            try:
                with p.open(encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("run_id") == run_id:
                    return PlaybookCheckpoint(**data)
            except Exception as exc:
                # R100 P2-C：由 debug 升為 warning。這條路徑是**跨 playbook 掃描**，
                # 一個壞檔不該中止整個查詢；但「跳過了一個壞檔」必須看得見——
                # debug 級在生產組態下等於沒有訊號。
                logger.warning("load_by_run_id | 跳過損毀檔案 %s: %s", p, exc)
                continue
        return None

    def clear_checkpoint(self, playbook_id: str) -> None:
        p = self._path(playbook_id)
        if p.exists():
            p.unlink()
            logger.info("檢查點已清除: %s", p)

    def schedule_resume(self, playbook_id: str, delay_minutes: int) -> datetime:
        resume_at = datetime.now() + timedelta(minutes=delay_minutes)
        cp = self.load_checkpoint(playbook_id) or PlaybookCheckpoint(
            playbook_path=playbook_id, step_idx=0, step_id="", total_steps=0,
        )
        cp.scheduled_resume_at = resume_at.isoformat(timespec="seconds")
        self.save_checkpoint(playbook_id, cp)
        return resume_at

    # R81（HLM-S1-02）：委派 SSOT。此處原本自帶一份只算得了 naive 的複本，
    # 與 PgStateRepository 產出的 aware 字串相減會拋 TypeError。
    @staticmethod
    def seconds_until_resume(checkpoint: PlaybookCheckpoint) -> float:
        return resume_clock_seconds_until(checkpoint.scheduled_resume_at)

    def list_recent_checkpoints(
        self, since: datetime | None = None, limit: int = 50
    ) -> list[PlaybookCheckpoint]:
        results: list[PlaybookCheckpoint] = []
        for p in self._dir.glob(f"*{_SUFFIX}"):
            playbook_id = p.stem.replace(".checkpoint", "")
            try:
                cp = self.load_checkpoint(playbook_id)
            except CheckpointCorruptError as exc:
                # 列舉面（診斷用）刻意不讓一個壞檔炸掉整張清單，但必須 loud：
                # 續作路徑（load_latest_by_playbook）那一側照樣 raise，兩者不同軸。
                logger.error("list_recent_checkpoints | 損毀的 checkpoint：%s", exc)
                continue
            if cp is None:
                continue
            if since:
                try:
                    saved = datetime.fromisoformat(cp.saved_at)
                    if saved < since:
                        continue
                except (ValueError, TypeError):
                    pass
            results.append(cp)
        results.sort(key=lambda c: c.saved_at, reverse=True)
        return results[:limit]
