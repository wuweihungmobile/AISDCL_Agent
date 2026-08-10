"""AC6-3「OpenAPI 3.1 schema」的真斷言落點——門檻逐字＝**openapi == "3.1.0" + ≥ 15 欄位**。

指標登記於 `tests/contract/test_ac_matrix_scaffolding.py::AC_MATRIX["AC6-3"]`
（上游 [SD_Improving_06.md](../../docs/04_planning/SD_Improving_06.md) §6.5 該列
逐字指名本檔）。此前本檔不存在，於是 AC6-3 是一筆「指標指不到任何東西」的欠債。

🔴 誠實劃界（先講清楚，因為 SD_06 §6.5 那一列的量測命令會誤導）：
該列的量測命令逐字是 `curl http://localhost:8000/api/config/schema | jq '.openapi'`，
而**本 repo 沒有任何 HTTP server**（實查：`autoclaude/` 對 `fastapi`／`uvicorn` 零依賴，
`pyproject.toml` 亦無；命中的三處全是 docstring 在說「本工具相容 FastAPI 的 event loop」）。
⇒ 那條 curl 在今天的 repo 上跑不起來，不是因為沒人建測試，是因為那個端點還不存在。
本檔量的是**產生該回應的唯一生產程式碼**：`ConfigResolver.openapi_schema()`
（`autoclaude/utils/config_resolver.py`，其 docstring 逐字對應 AC6-3 / T5-18）。
HTTP 那一層（路由、序列化、狀態碼、RBAC）**不在本檔射程內**——它要等 SD_07 UI 那條
線真的落地才有東西可測；屆時本檔應加一支對真實端點的案例，而不是改寫本檔的斷言。
這個缺口刻意寫成散文而不是包成一個 skip：skip 只是把同一筆欠債換個地方掛著，
而本檔存在的理由正是清掉那種掛法。

WHY 這幾支有鑑別力（Rule 9）：`openapi_schema()` 是**手寫的 wrapper** 包住 Pydantic
自動產生的 model schema。手寫的那一半（版本字串、paths、`$ref` 指向）與自動的那一半
（`components.schemas.AppConfig` 的欄位）會各自漂移，而漂移的表徵是「文件看起來對、
但 `$ref` 指到空的地方」或「版本宣稱 3.1.0 而內容是 3.0 語意」。所以本檔的四支分別
釘住：版本字面、欄位數下限、**`$ref` 真的解析得到**、以及 wrapper 的欄位集合與
`AppConfig` 模型逐一相符（把「≥ 15」這個下限與模型綁在一起，而不是抄一個數字）。
"""
from __future__ import annotations

import json

from autoclaude.utils.config_resolver import AppConfig, ConfigResolver

#: AC6-3 門檻：OpenAPI 版本字面（3.1 起 JSON Schema 才是 draft 2020-12 完全相容）。
_REQUIRED_OPENAPI_VERSION = "3.1.0"

#: AC6-3 門檻：AppConfig 至少要曝出這麼多個可調欄位（UI 才有東西可畫）。
_MIN_FIELDS = 15

#: SD_06 §6.5 AC6-3 與 `openapi_schema()` docstring 共同指名的端點路徑。
_ENDPOINT = "/api/config/schema"


def _appconfig_component(schema: dict) -> dict:
    return schema["components"]["schemas"]["AppConfig"]


def test_schema_declares_openapi_31():
    """門檻前半：版本字面必須是 3.1.0（不是 3.0.x，也不是 `3.1`）。

    為何釘死字面值而不是「以 3.1 開頭」：3.0 與 3.1 對 schema 方言的規定不同
    （3.0 是 JSON Schema draft-04 的子集、3.1 才是 draft 2020-12），而本 wrapper
    直接塞的是 Pydantic v2 的 `model_json_schema()`＝draft 2020-12 ⇒ 宣稱 3.0
    就是在說謊，而消費端（UI／codegen）會照著那個謊選錯 validator。
    """
    assert ConfigResolver.openapi_schema()["openapi"] == _REQUIRED_OPENAPI_VERSION


def test_appconfig_component_exposes_at_least_fifteen_fields():
    """門檻後半：`components.schemas.AppConfig` 至少 15 個 property。"""
    props = _appconfig_component(ConfigResolver.openapi_schema()).get("properties", {})
    assert len(props) >= _MIN_FIELDS, (
        f"AppConfig 只曝出 {len(props)} 個欄位（{sorted(props)}），"
        f"低於 AC6-3 的 ≥ {_MIN_FIELDS} 門檻"
    )


def test_the_field_set_is_the_model_itself_not_a_hand_kept_copy():
    """欄位集合必須**等於** `AppConfig.model_fields`——一個都不能多、不能少。

    WHY（本檔最有牙的一支）：上一支的「≥ 15」對**漏欄**幾乎無感——17 個欄位掉到 15 個
    仍然過關，而掉掉的那兩個就是 UI 上永遠調不到的設定。把下限與模型綁在一起之後，
    任何「wrapper 自己維護一份欄位清單」或「schema 產生器被換成過濾版」的退化都會
    當場紅，且訊息直接印出差集。反方向也守：wrapper 憑空多出一個模型沒有的欄位
    （例如把內部欄位誤曝給 UI）同樣紅。
    """
    props = set(_appconfig_component(ConfigResolver.openapi_schema()).get("properties", {}))
    model = set(AppConfig.model_fields)
    assert props == model, (
        f"schema 與模型欄位不一致｜schema 多出：{sorted(props - model)}｜"
        f"schema 缺少：{sorted(model - props)}"
    )
    assert len(model) >= _MIN_FIELDS, (
        f"AppConfig 模型本身只有 {len(model)} 個欄位，已低於 AC6-3 的 ≥ {_MIN_FIELDS} 門檻"
        "——這一步先於 schema：模型都沒有的欄位，schema 不可能曝出來"
    )


def test_the_documented_endpoint_carries_a_resolvable_ref():
    """手寫 wrapper 那一半：端點宣告存在，且 200 回應的 `$ref` 真的解析得到。

    意圖：`$ref` 是這份文件裡唯一「宣稱」與「內容」分家的地方——路徑寫對、
    components 卻空著（或 key 拼錯）時，文件在瀏覽器裡看起來完全正常，只有真的
    去解析它的 codegen 會炸。本支就照著 JSON Pointer 走一遍那個指標。
    """
    schema = ConfigResolver.openapi_schema()
    get_op = schema["paths"][_ENDPOINT]["get"]
    ref = get_op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.startswith("#/"), f"只支援本文件內的 JSON Pointer，實得 {ref!r}"

    node: object = schema
    for token in ref.removeprefix("#/").split("/"):
        assert isinstance(node, dict) and token in node, (
            f"`$ref` {ref!r} 解析不到：在 {token!r} 這一段斷掉"
        )
        node = node[token]
    assert isinstance(node, dict) and node.get("properties"), (
        f"`$ref` {ref!r} 解析到了，但指向的 schema 沒有任何 property（空殼文件）"
    )


def test_the_whole_document_is_json_serialisable():
    """整份文件必須能被 `json.dumps` 吐出來——不能序列化就送不出去。

    意圖：wrapper 塞進去的是 Pydantic 產生的樹，其中 default 值可能帶非 JSON 原生
    型別（`Path`／`tuple`／`Enum`）。這種缺陷在單元層完全看不到（dict 建得起來、
    斷言也讀得到值），只有在真的要序列化時才炸——而那一刻是在 HTTP handler 裡。
    """
    payload = json.dumps(ConfigResolver.openapi_schema(), ensure_ascii=False)
    assert json.loads(payload)["openapi"] == _REQUIRED_OPENAPI_VERSION
