"""單筆提案 `items[0].detail` 的白名單過濾（TCS-SiFlowVisibility-20261111 W-F4、C-3、NFR-FV-4）。

SelfImproving 根層 `export --kind proposals --id` 會在 `items[0].detail` 帶出提案詳情（diff、本文、
來源觀察、評估集摘要、沙盒、驗證、下一步、時間線）。本模組是 Console 側「評估集內容與其他未列欄位
永不外送」的**真防線**：只放行契約（C-3）列出的鍵，其餘一律丟棄；值逐值不動、鍵序保留。

純函式：不開檔、不啟動子行程、不讀環境，輸入什麼就只回過濾後的新結構（不改動輸入）。

保守處理（fail-closed）：
  · 白名單內的**純量鍵**若值是物件或陣列＝形狀不符，丟棄該鍵（避免把容器當純量夾帶未列內容）；
  · 預期為物件／陣列的區塊，若型別不符（且不是 null）＝丟棄該區塊；陣列中非物件的元素丟棄；
  · `detail` 本身不是物件＝視為缺席（呼叫端移除 `detail` 鍵）；`detail` 缺席則原樣缺席。
"""
from __future__ import annotations

from typing import Any

#: 區塊規格：`(型別, 純量鍵集合, 子區塊規格)`；型別 `obj`＝物件、`list`＝物件陣列。
_Spec = tuple[str, frozenset[str], "dict[str, _Spec]"]

_TEXT_BLOCK: _Spec = ("obj", frozenset({"rel", "bytes", "text", "truncated"}), {})
_REASONS: _Spec = ("list", frozenset({"code", "text"}), {})

#: `detail` 八欄；與根層 TCS-P7 §2.1 與 Console TCS C-3 逐鍵一致。
DETAIL_SPEC: dict[str, _Spec] = {
    "patch": _TEXT_BLOCK,
    "body": _TEXT_BLOCK,
    # 缺列形態只有 `id` 與 `missing` 兩鍵（C-3 正式契約句）
    "sourceObs": ("list", frozenset(
        {"id", "context", "symptom", "severity", "disposition", "missing"}), {}),
    "heldout": ("obj", frozenset(
        {"frozen", "seq", "n", "min", "belowMin", "frozenBy", "digest8", "neNote"}), {}),
    "sandbox": ("obj", frozenset(
        {"seq", "id", "applied", "touchedOk", "rollbackOk", "failCode", "failText"}), {}),
    "verify": ("obj", frozenset(
        {"seq", "id", "verdict", "baselineRed", "patchedGreen", "mutatedRed", "probesN",
         "carrierProof"}), {"reasons": _REASONS}),
    "next": ("obj", frozenset({"code", "who", "text"}), {}),
    "timeline": ("list", frozenset({"seq", "t", "by", "kind", "action"}), {}),
}

_CONTAINERS = (dict, list)


def _filter_object(obj: dict[str, Any], leaves: frozenset[str],
                   children: dict[str, _Spec]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in obj.items():
        if key in leaves:
            if not isinstance(value, _CONTAINERS):
                out[key] = value
        elif key in children:
            kept = _filter_block(value, children[key])
            if kept is not _DROP:
                out[key] = kept
    return out


class _Drop:
    """哨兵：該鍵形狀不符、不放行（與 None 區分，null 是合法值）。"""


_DROP = _Drop()


def _filter_block(value: Any, spec: _Spec) -> Any:
    kind, leaves, children = spec
    if value is None:
        return None
    if kind == "obj":
        return _filter_object(value, leaves, children) if isinstance(value, dict) else _DROP
    if not isinstance(value, list):
        return _DROP
    return [_filter_object(item, leaves, children) for item in value if isinstance(item, dict)]


def filter_detail(detail: Any) -> dict[str, Any] | None:
    """回只含契約鍵的新 `detail`；`detail` 不是物件則回 None（呼叫端視為缺席）。"""
    if not isinstance(detail, dict):
        return None
    out: dict[str, Any] = {}
    for key, value in detail.items():
        spec = DETAIL_SPEC.get(key)
        if spec is None:
            continue
        kept = _filter_block(value, spec)
        if kept is not _DROP:
            out[key] = kept
    return out


def sanitize_single_proposal(export_obj: dict[str, Any]) -> dict[str, Any]:
    """對單筆提案的 export 物件，只處理 `items[0].detail`：合格者換成過濾後的新物件（原位置、鍵序不
    變），非物件者移除該鍵，缺席者不動；其餘頂層鍵與 `items[0]` 的其他鍵完全不碰。"""
    items = export_obj.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict) and "detail" in items[0]:
        filtered = filter_detail(items[0]["detail"])
        if filtered is None:
            del items[0]["detail"]
        else:
            items[0]["detail"] = filtered
    return export_obj
