"""AutoClaude `SddToPlaybookAdapter` 的呼叫接縫（ADR-XPLAT-016 §6.2、§7.1、§8.3、§11.1）。

三處共用同一條路——`POST /sdd/compile`、`POST /autoclaude/runs`（含 `sdd`）的預檢、`:resume`／
`:restore` 的重驗——所以「怎麼建構 adapter、怎麼把例外對映成 HTTP」只在這裡定義一次：

  · 建構子 `fsm_project`：Bridge 行程內呼叫**一律顯式傳值、含空字串**，不得讓 adapter 去讀 Bridge
    自己的環境（開發機匯出 `SDD_PROJECT` 是常態；空字串＝明確「不指定」、不讀環境）。
  · `load_spec(spec_dir, spec_file=None)`：有 `spec_file` 時 adapter **只讀這一份**，不做目錄內選
    檔；`spec_file` 以絕對路徑傳入（呼叫端已驗證在 `spec_dir` 之下）。
  · 例外對映（§6.3）：`SpecDigestMismatchError`（`SpecNotFrozenError` 的子類，**必須先接**）→ 409
    `spec_digest_changed`；其餘 `SpecNotFrozenError`→422 `spec_not_frozen`；`SpecTaintedError`→422
    `spec_tainted`；`SpecFormatVersionError`→422 `spec_format_version_unsupported`；
    `FileNotFoundError`→422 `spec_not_found`；`ValueError`→422 `spec_ambiguous`。

autoclaude 一律在函式內才 import：Bridge 在 AutoClaude 匯入失敗時仍要能啟動（`/health` 以
`engines.autoclaude.ok=false` 回報），不能讓這個接縫在模組載入時就把整個 app 拉垮。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ApiError, spec_digest_changed


def _adapter_class() -> Any:
    from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter

    return SddToPlaybookAdapter


def build_adapter(fsm_project: str) -> Any:
    """建構 adapter，**顯式**傳入 FSM 專案鍵（已過 `fsm_component`；空字串＝不指定）。"""
    return _adapter_class()(fsm_project=fsm_project)


def load_spec(adapter: Any, spec_dir: Path, spec_file: Path | None = None) -> Any:
    """`adapter.load_spec`；`spec_file` 以**絕對路徑**傳入（呼叫端已驗證在 `spec_dir` 之下）。"""
    if spec_file is None:
        return adapter.load_spec(str(spec_dir))
    return adapter.load_spec(str(spec_dir), spec_file=str(spec_file))


def is_digest_mismatch(exc: Exception) -> bool:
    """`exc` 是不是「凍結後規格內容已變更」（`SpecDigestMismatchError`；它是 `SpecNotFrozenError` 的
    子類，所以呼叫端要先問這個、再交給 `raise_for_spec_error`）。"""
    from autoclaude.core.ports.spec_source import SpecDigestMismatchError

    return isinstance(exc, SpecDigestMismatchError)


def raise_for_spec_error(exc: Exception) -> None:
    """把 adapter 的例外對映成 ApiError 並丟出（不是 adapter 認得的例外＝原樣再丟）。"""
    from autoclaude.core.ports.spec_source import (
        SpecDigestMismatchError,
        SpecFormatVersionError,
        SpecNotFrozenError,
        SpecTaintedError,
    )

    if isinstance(exc, SpecDigestMismatchError):
        raise spec_digest_changed("frozen_vs_file", message=str(exc)) from exc
    if isinstance(exc, SpecNotFrozenError):
        raise ApiError(422, "spec_not_frozen", detail=str(exc)) from exc
    if isinstance(exc, SpecTaintedError):
        raise ApiError(422, "spec_tainted", detail=str(exc)) from exc
    if isinstance(exc, SpecFormatVersionError):
        raise ApiError(422, "spec_format_version_unsupported", detail=str(exc)) from exc
    if isinstance(exc, FileNotFoundError):
        raise ApiError(422, "spec_not_found", detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise ApiError(422, "spec_ambiguous", detail=str(exc)) from exc
    raise exc


def frozen_digest_status(spec: Any) -> str:
    """`SddSpec.frozen_digest_status`（`verified`｜`absent`）；缺欄或不認得的值一律 `absent`
    （保守：沒有證據就不宣稱已驗證）。"""
    value = getattr(spec, "frozen_digest_status", None)
    return value if value in ("verified", "absent") else "absent"
