"""_sdd_frozen_gate — FSM 狀態檔選取、凍結判定與凍結摘要綁定（adapter tier ≤400 LOC）。

對應 ADR-XPLAT-016 §6（凍結綁內容，G-06）與 §7.1（以專案選檔，G-02／S-05）。
從 sdd_to_playbook_adapter 抽出：職責分離，且全為只讀的純函式群，可獨立單測。
出聲（IObservabilityPort）留給呼叫端；本檔只回傳判定結果或 raise。

為什麼要抽這一層（兩個 fail-open 的結構性成因）：
  1. 選檔：舊版取字母序第一份 `FSM-STATE-*.yaml`；同目錄多專案共處時，他專案已凍結即可放行
     未凍結的專案。新規則改以**專案鍵**選檔（建構子 fsm_project／環境 `SDD_PROJECT`），
     無鍵且多檔一律 fail-closed，找不到該專案的檔也**不再往上層目錄找**（會撞到別的專案）。
  2. 摘要：舊版只驗「有凍結」，不驗「凍結的就是這份」。凍結時（SDD CLI `spec-frozen --digest`）
     每份文件記一筆 `spec_doc_digests`，這裡在摘要存在時比對，不符即 SpecDigestMismatchError。

跨平台三點（根 CLAUDE.md 鐵律三）：
  - 路徑分隔符：摘要鍵是 POSIX 相對路徑；比對時以 `/` 拆段、`os.path.join` 組成本機路徑，兩邊各過
    `os.path.normcase`。🔴 不得對 `as_posix()` 字串直接 normcase——Windows 的 normcase 會把
    `/` 換成 `\\`，尾段比對將恆不成立（ADR §6.1 的原型第一版即因此全數誤判「不在清單」）。
  - 大小寫：normcase 只在 Windows 折疊；POSIX 維持區分大小寫。
  - 摘要演算法由生產端（SDD）與 adapter 的 `SddSpec.digest` 各持一份等價實作（不跨子專案 import）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from ...core.ports.spec_source import SpecDigestMismatchError, SpecNotFrozenError

#: adapter 讀的專案鍵環境變數（與 SDD 側 `state_loader.project_from_env` 同名）。
SDD_PROJECT_ENV = "SDD_PROJECT"
STATE_FILE_PREFIX = "FSM-STATE-"

# happy path 上 SPEC_FROZEN 及其後繼狀態（transition_rules._HAPPY_PATH 實況）。
# AUTOCLAUDE_DELEGATED：Bridge 在 spawn 前已 delegate-enter，引擎 PRE_RUN 讀到的 current_state
# 就是它；對「frozen_stages 為空、靠狀態判斷已凍結」的舊狀態檔，缺這一項會讓委派一啟動就被 veto。
POST_FROZEN_STATES = frozenset({
    "SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION", "AUTOCLAUDE_DELEGATED",
    "SANDBOX_HARDENING_GATE", "EXECUTION_EVALUATION", "ADVERSARIAL_EVALUATION",
    "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY", "RELEASE",
})

_LISTED_KEYS_CAP = 20  # 錯誤訊息列出的專案鍵上限（真實框架目錄現有 8 個）


def resolve_project_key(fsm_project: str | None) -> str:
    """建構子 `fsm_project` 的語意（ADR §7.1）：None＝讀環境 `SDD_PROJECT`；
    空字串＝**明確不指定、不讀環境**；其餘照用。回傳 strip 後字串，空字串＝無鍵。

    Bridge 行程內一律顯式傳值（含空字串）：開發機在 SDD session 匯出 `SDD_PROJECT` 再起 Bridge 是
    常態，Bridge 自己的環境不得左右它替各專案做的選檔。
    """
    raw = os.environ.get(SDD_PROJECT_ENV, "") if fsm_project is None else fsm_project
    return raw.strip()


def state_key(path: Path) -> str:
    """`FSM-STATE-<鍵>.yaml` 的鍵（＝淨化後的檔名幹）；檔名不合慣例時退回 stem。"""
    name = path.name
    if name.startswith(STATE_FILE_PREFIX) and name.endswith(".yaml"):
        return name[len(STATE_FILE_PREFIX):-len(".yaml")]
    return path.stem


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:  # 例如 NTFS 對含 ':' 的名稱當資料流語法：一律當「不存在」
        return False


def _illegal_key(key: str) -> bool:
    """防路徑穿越：含 `/`、`\\`、NUL、控制字元，或是 `.`／`..` 的鍵一律非法。"""
    return key in {".", ".."} or any(
        ch in "/\\" or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in key)


def _project_field(path: Path) -> object:
    """狀態檔內 `fsm_state.project`（原名，未淨化）；讀不出一律 None。"""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return None
    root = doc.get("fsm_state") if isinstance(doc, dict) else None
    return root.get("project") if isinstance(root, dict) else None


def _listed(files: list[Path]) -> str:
    keys = [state_key(p) for p in files]
    more = f"…（共 {len(keys)} 個）" if len(keys) > _LISTED_KEYS_CAP else ""
    return ", ".join(keys[:_LISTED_KEYS_CAP]) + more


def _pick(files: list[Path], fsm_dir: Path, key: str) -> Path:
    """在同一個 build/reports/fsm 目錄內依專案鍵選檔（ADR §7.1 判定表）。"""
    if not key:
        if len(files) == 1:
            return files[0]
        raise SpecNotFrozenError(
            f"{fsm_dir}: 狀態檔不唯一（{_listed(files)}），請設定 SDD_PROJECT 指定專案"
            "——fail-closed，不依字母序猜（他專案已凍結不得放行本專案）")
    exact = fsm_dir / f"{STATE_FILE_PREFIX}{key}.yaml"
    if _is_file(exact):
        return exact
    # 鍵是未淨化的原名（如含 ':'）時，檔名幹是淨化後的字串：改以檔內 project 欄位反查，
    # 且須恰有一個檔吻合（同專案的多軌檔 FSM-STATE-<專案>-<軌>.yaml 會讓它不唯一→拒絕）。
    hits = [p for p in files if _project_field(p) == key]
    if len(hits) == 1:
        return hits[0]
    raise SpecNotFrozenError(
        f"{fsm_dir}: 找不到專案 {key!r} 的 FSM 狀態檔（該目錄現有專案鍵：{_listed(files)}）"
        "——不往上層目錄找（會撞到別的專案）")


def find_fsm_state(
    spec_dir: Path, *, explicit_path: str | None = None, project_key: str = "",
) -> Path | None:
    """定位 FSM 狀態檔。回 None＝顯式路徑不存在，或祖先鏈上沒有任何含狀態檔的
    `build/reports/fsm`；其餘不合規定一律 raise SpecNotFrozenError（fail-closed）。

    顯式路徑（`fsm_state_path`）維持最優先、行為不變。否則自 spec_dir 向上找**第一個含
    `FSM-STATE-*.yaml` 的** `build/reports/fsm`，並只在該目錄內依專案鍵選檔。
    """
    if explicit_path:
        explicit = Path(explicit_path)
        return explicit if _is_file(explicit) else None
    if project_key and _illegal_key(project_key):
        raise SpecNotFrozenError(
            f"專案鍵 {project_key!r} 非法（含路徑分隔符／控制字元，或是 . ／ ..）"
            "——拒絕用它選 FSM 狀態檔")
    node = spec_dir.resolve()
    for candidate in (node, *node.parents):
        fsm_dir = candidate / "build" / "reports" / "fsm"
        if not fsm_dir.is_dir():
            continue
        files = [p for p in sorted(fsm_dir.glob(f"{STATE_FILE_PREFIX}*.yaml")) if p.is_file()]
        if files:
            return _pick(files, fsm_dir, project_key)
    return None


def read_frozen_stages(state_file: Path) -> list[dict[str, Any]]:
    """讀狀態檔並做凍結判定：`frozen_stages` 非空，或 `current_state` 已達 SPEC_FROZEN 之後狀態
    （POST_FROZEN_STATES）；否則 raise SpecNotFrozenError。回傳 frozen_stages（只含映射項）。

    狀態檔讀不出來（壞 YAML／非 UTF-8／不是映射）一律視為無法判定凍結 → fail-closed，
    而不是丟出與凍結無關的例外讓呼叫端各自處理。
    """
    try:
        doc = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise SpecNotFrozenError(
            f"{state_file}: FSM 狀態檔讀不出來（{type(exc).__name__}）"
            "——無法判定凍結，依 Spec-First Gate fail-closed 拒絕") from exc
    root = (doc.get("fsm_state") if isinstance(doc, dict) else None) or {}
    raw = root.get("frozen_stages") if isinstance(root, dict) else None
    stages = [s for s in raw if isinstance(s, dict)] if isinstance(raw, list) else []
    current = root.get("current_state") if isinstance(root, dict) else None
    if not stages and current not in POST_FROZEN_STATES:
        raise SpecNotFrozenError(
            f"{state_file}: frozen_stages 為空且 current_state={current!r} "
            "未達 SPEC_FROZEN 之後狀態")
    return stages


def _longest_matching_key(spec_file: Path, digests: dict[str, str]) -> str | None:
    """摘要鍵＝POSIX 相對專案根的路徑；以「規格檔絕對路徑的尾段等於鍵」比對，不依賴專案根的
    絕對路徑（Docker 與主機路徑不同也成立）。多個鍵吻合取最長者。"""
    me = os.path.normcase(str(spec_file.resolve()))
    best: tuple[int, str] | None = None
    for key in digests:
        local = os.path.normcase(os.path.join(*key.split("/")))
        if (me == local or me.endswith(os.sep + local)) and (best is None or len(local) > best[0]):
            best = (len(local), key)
    return best[1] if best else None


def check_digest(frozen_stages: list[dict[str, Any]], spec_file: Path, digest: str) -> str:
    """凍結摘要比對（ADR §6.2 判定表）。回 "verified"｜"absent"。

    取全部 `frozen_stages[*].spec_doc_digests` 的聯集（同鍵多階段出現時後一階段勝出＝以最近一次
    凍結為準）：
      - 聯集為空（舊狀態檔，或凍結時沒帶 --digest）→ "absent"，維持放行（呼叫端須出聲）；
      - 有摘要但規格檔不在任何階段的清單內 → SpecNotFrozenError；
      - 吻合 → "verified"；不吻合 → SpecDigestMismatchError（SpecNotFrozenError 的子類）。
    """
    union: dict[str, str] = {}
    for stage in frozen_stages:
        digests = stage.get("spec_doc_digests")
        if digests is None:
            continue
        if not isinstance(digests, dict):
            raise SpecNotFrozenError(
                f"frozen_stages 的 spec_doc_digests 不是映射（{type(digests).__name__}）"
                "——凍結摘要格式不合，無法比對，fail-closed")
        union.update({str(k): str(v) for k, v in digests.items()})
    if not union:
        return "absent"
    key = _longest_matching_key(spec_file, union)
    if key is None:
        raise SpecNotFrozenError(
            f"{spec_file}: 規格檔不在凍結清單（已凍結：{sorted(union)}）"
            "——凍結時未納入這份檔案，依 Spec-First Gate fail-closed 拒絕")
    if union[key] != digest:
        raise SpecDigestMismatchError(
            f"{spec_file}: 規格內容與凍結時不同（鍵 {key}）：凍結摘要 {union[key]} ≠ "
            f"現檔摘要 {digest}——凍結後改檔須重新核准凍結")
    return "verified"
