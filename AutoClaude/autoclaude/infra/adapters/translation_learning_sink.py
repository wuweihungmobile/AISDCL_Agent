"""FileTranslationLearningSink — ITranslationLearningSink 檔案實作（improving_60, adapter ≤400）。

沿用 FileRtmFeedbackSource/FileRtmSink 先例（A 軌 File-only，無 PG 後端）：
  寫出：record_proposal → PROPOSALS-{project}.jsonl（append-only，跨 session 累積）
  讀回：list_proposals  ← PROPOSALS-{project}.jsonl（per-line fail-soft）

fail-soft 紀律（提議為輔助諮詢功能，絕不阻斷主流程）：
  目錄不存在自動建立；讀回時檔案不存在 / JSON 畸形 / 非 dict 一律回空、不 raise；
  read 採 per-line fail-soft（畸形行跳過，不丟整檔）。

project 基名消毒與 FileRtmFeedbackSource._sanitize 對稱，防 project 名挾帶路徑穿越
（../、絕對路徑）寫到 / 讀到 base_dir 外的檔。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ...core.ports.translation_learning import (
    ITranslationLearningSink,
    TranslationProposal,
)
from ...utils.logger import _sanitize_log_filename

logger = logging.getLogger("autoclaude.infra.translation_learning")


class FileTranslationLearningSink(ITranslationLearningSink):
    """轉譯策略提議落地（append-only JSONL；符合 ITranslationLearningSink Protocol）。"""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def _path(self, project: str) -> Path:
        return self._base / f"{_sanitize(f'PROPOSALS-{project}')}.jsonl"

    def record_proposal(self, project: str, proposal: TranslationProposal) -> None:
        """append 一筆 proposed 提議（fail-soft：寫入失敗僅 warn，不阻斷主流程）。"""
        target = self._path(project)
        try:
            self._base.mkdir(parents=True, exist_ok=True)
            line = json.dumps(
                {
                    "at_id": proposal.at_id,
                    "failing_runs": proposal.failing_runs,
                    "total_runs": proposal.total_runs,
                    "rationale": proposal.rationale,
                    "status": proposal.status,
                    "weak_runs": proposal.weak_runs,  # improving_61 W-61-3（additive）
                },
                ensure_ascii=False,
            )
            with target.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as exc:  # noqa: BLE001 — fail-soft（諮詢功能不得阻斷）
            logger.warning("record_proposal fail-soft for %s: %s", project, exc)

    def list_proposals(self, project: str) -> tuple[TranslationProposal, ...]:
        """讀回既有提議（最舊→最新）；fail-soft 回 ()。"""
        target = self._path(project)
        try:
            if not target.is_file():
                return ()
            out: list[TranslationProposal] = []
            for raw in target.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue  # per-line fail-soft：畸形行跳過，不丟整檔
                if not isinstance(doc, dict) or "at_id" not in doc:
                    continue
                out.append(TranslationProposal(
                    at_id=str(doc.get("at_id", "")),
                    failing_runs=int(doc.get("failing_runs", 0)),
                    total_runs=int(doc.get("total_runs", 0)),
                    rationale=str(doc.get("rationale", "")),
                    status=str(doc.get("status", "proposed")),
                    # improving_61：舊紀錄無 weak_runs → 讀回 0（向後相容）
                    weak_runs=int(doc.get("weak_runs", 0)),
                ))
            return tuple(out)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("list_proposals fail-soft for %s: %s", project, exc)
            return ()


def _sanitize(name: str) -> str:
    """委派 SSOT `_sanitize_log_filename`（DEF-101-343，R42 收斂），與
    `FileRtmFeedbackSource._sanitize` 對稱：報告基名消毒，防路徑穿越，並補齊
    Windows 保留裝置名防護（舊版獨立實作缺漏）。

    `.lstrip("._")` 對稱既有先例：`_sanitize_log_filename` 只 `rstrip` 尾端
    空白/句點，不清前導句點/底線，須補一層維持「不留字面 ``..`` 前綴」保證。

    本檔基名恆有固定前綴 `PROPOSALS-`，理論上不會空/dot-起頭，兜底為防禦冗餘。
    `_sanitize_log_filename` 對「淨化後整段為空」回傳 `"untitled"`；本模組既有
    對外行為為 `"proposals-report"`，委派後改寫回原字面值，維持既有可觀察行為
    不變。

    R42 二審修復（DEF-101-346 追記）：`.lstrip("._")` 會把 `_sanitize_log_filename`
    為保留裝置名（如 ``CON`` → ``_CON``）補上的前導底線逃逸字元一併剝除，導致
    ``CON`` 經 lstrip 後又變回裸 ``CON``——保留名防護被 wrapper 自己抵銷。故在
    lstrip 之後，對非 fallback 結果**再委派一次** `_sanitize_log_filename`，
    讓保留名偵測在 lstrip 之後重新執行、補回逃逸前綴。"""
    sanitized = _sanitize_log_filename(name)
    if sanitized == "untitled":
        return "proposals-report"
    result = sanitized.lstrip("._") or "proposals-report"
    if result == "proposals-report":
        return result
    return _sanitize_log_filename(result)


__all__ = ["FileTranslationLearningSink"]
