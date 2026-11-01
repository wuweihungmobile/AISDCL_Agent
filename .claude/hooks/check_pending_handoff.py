#!/usr/bin/env python3
"""Stop hook：回合結束時把「決定／待辦」用散文留給掌舵者、本回合卻沒有給互動選項 ⇒ 推回一次。

立案（真實事故，掌舵者真機回報；sid 655d9777-cfd0-4478-b2b3-b8245313b24c）
----------------------------------------------------------------------
· 2026-10-31 03:45（line 12）掌舵者常態授權原文：「以上若需要我決策或沒有標註到，請依照最佳化,
  最理想, 最適當的解決方案(不需要顧慮成本)，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋,
  讓我互動選項決策」。
· 2026-11-01 02:18（line 8657）主控收尾句：「…本輪沒有未結工作，只剩前一則提到的兩件人工決定
  （OBS-SI-362 是否刪三份多餘稽核檔、V2 對話框停用的真機目視）。」⇒ 結束回合。
· 02:18～08:20 六小時：逐字稿**零**撞額度／API 中斷事件（額度 02:00 已重置；只有 03:15 一次閒置
  壓縮）、哨兵排程巡邏 rc 0 但「無撞線可續」⇒ 整套續航架構把「主控結束回合」當成「沒事可做」。
· 08:20（line 8687）掌舵者：「請問已經完成所有任務了嗎? 請查出停在這裡的根因, 徹底改善任務中斷
  沒法繼續完成的問題!」

架構缺口（為什麼既有三層都看不到它）
------------------------------------
續航協定（ADR-XPLAT-004）守的是三類停：撞額度（哨兵＋harness auto-continuation）、context 壓縮
（precompact_restart_point.py）、session 死亡（handback／`claude -r`）。第四類——**主控自認做完、
但決定還掛在人身上**——此前沒有任何觀測者：Stop 事件唯一的守衛 `check_claim_provenance.py`
只看數字出處，不看「有沒有東西被留給人」。被留給人的決定寫在散文裡，終端上沒有任何可按的東西，
掌舵者回來前它就靜靜躺著；而 AskUserQuestion 是 harness 裡唯一「人一回來一眼看到、一鍵就續」的
通道。本檔補的就是這個觀測者。

判準（純函式 `pending_handoff_hits()` ＋ `asked_this_turn()`）
----------------------------------------------------------------
最後一則 assistant 文字（payload `last_assistant_message`）裡有句子含交棒詞（`HANDOFF_RE`：
待掌舵者／留給您／需要您／請您／人工決定…；引號內的不算），且四類抑制都不成立——
  ① 否定緊鄰交棒詞前文（`NEGATION_RE` × `NEGATION_WINDOW`：「目前沒有任何事卡在等您」是正解；
     立案那一則句內另有「本輪沒有未結工作」卻必須紅，所以不看整句）；
  ② 權限核准（`PERMISSION_RE`：harness 權限牆是唯一通道，AskUserQuestion 幫不上）；
  ③ K=1 決定須掌舵者親打（`K1_RE`：SelfImproving 的 DEC 只認掌舵者真人發言，
     AskUserQuestion 不是 DEC 載體——2026-10-25 輪實測）；
  ④ 作者已寫明用了互動選項（`INTERACTIVE_RE`）；
且本回合（最後一則真人 role=user 訊息之後）**沒有任何** `AskUserQuestion` tool_use
⇒ stdout 送 `{"decision":"block","reason":…}`（Stop 事件的官方阻斷形態），把回合推回主控一次。

為什麼這一支可以 block（姊妹檔 `check_claim_provenance.py` 刻意只出聲、永不阻斷）
----------------------------------------------------------------------------------
那支治的是「話講得太滿」，推回去只會生出更多話；本檔治的是「工作沒做完」——缺的那一步
（問，或決）正是推回去之後主控會做的事。兩個夾具：`stop_hook_active` 為真（第二次 Stop）
一律放行 ⇒ 每個回合至多一個額外回合、不可能迴圈；`AUTOSDD_UNATTENDED` 有設時 no-op
（無人可答，推回只會燒額度）。假紅的代價＝一個短回合，且逃生口在句內（見下）。

真實面假紅普查（2026-11-01 現查；母體＝本機 `~/.claude/projects/<slug>/*.jsonl` 頂層 153 支、
195 個回合；重跑＝`python tools/probe/handoff_census.py`，判準向本檔借、不另寫第二份）
-------------------------------------------------------------------------------------------
  · 只用交棒詞表：命中 15／195（7.7%）。
  · 加四類抑制（否定整句判）：命中 8／195，逐筆判讀 6 真陽性、2 假陽性皆為 K=1 親打句型
    （「現在只等您兩句話」「請您打「晉升」」）——但整句否定把**立案那一則**也靜音了
    （句內有「本輪沒有未結工作」），所以否定改看交棒詞緊鄰前文。
  · 落地版（否定看前文 8 字、`K1_RE` 補 `打[「『]`／`句話`）：命中 **7／195（3.6%）**，逐筆判讀
    **7 真陽性、0 假陽性**——全部是把決定或待辦用散文留給掌舵者就收工：含本立案那一則、
    與 2026-10-25「perf_baseline 髒檔照慣例留給您」那一則（掌舵者事後下令「日後遇到請自動
    處理」，同一型）。🔴 誠實登記：那兩個 K=1 詞是在 8 筆上補的，屬登記的調參、不是量出來的
    鑑別力；母體只有 195 回合，數字是量測值不是常數。
  · 另有 6 個回合命中詞表但同回合有 AskUserQuestion ⇒ 正確靜音（可滿足性憑證：做對的人
    本來就會用那個通道）。

誠實劃界（本檔抓不到什麼）
------------------------
· 只認詞表：改寫成詞表外的說法（「這個之後再看」）看不見。
· 只看最後一則文字；AskUserQuestion 出現在本回合任一處即放行（不逐題對應「問的是不是那件事」）。
· 第二次 Stop 放行 ⇒ 主控仍可堅持散文交棒，本檔只保證「被提醒一次」。
· 逐字稿讀不到／超 byte cap／payload 退化／任何例外 ⇒ fail-open 靜默放行（P0：hook 崩潰
  不得演變成阻斷）。
· 詞表裡的「掌舵者」「您」是本 repo 的稱謂慣例；換稱謂就要改表。

逃生口
------
`AUTOSDD_HANDOFF_GUARD_OFF=1`（刻意不與其他守衛共用開關）；句內寫明「須掌舵者親打」等
K=1 詞（`K1_RE`）；`AUTOSDD_UNATTENDED` 下 no-op。
回歸鎖：`tools/tests/test_check_pending_handoff.py`。
"""
from __future__ import annotations

import json
import os
import re
import sys

# `timezone.utc` 不用 `datetime.UTC`（py311+）：hook 鏈須在 mac 預設直譯器載入。
from datetime import datetime, timezone

# payload 讀取與 UTF-8 stdio 都住共用層 `tools/lib/platform_utils.py`，形態逐字對齊姊妹檔
# `check_claim_provenance.py`（同一個 shim、同一個 except 語意）。本檔不得自己碰 `sys.stdin`、
# 也不得自己 reconfigure（兩者各有 shrink-only 棘輪在守）。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import read_hook_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}

try:
    from platform_utils import init_utf8_streams  # type: ignore[import-not-found]

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 模組層崩潰會繞過 main() 的 fail-open，故必須吞掉
    pass

try:
    from endurance_env import trace_dir  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    trace_dir = None  # type: ignore[assignment]

#: 交棒詞：把決定／待辦留給掌舵者的說法。「掌舵者」「您」是本 repo 的稱謂慣例。
HANDOFF_RE = re.compile(
    r"(待掌舵者|留給掌舵者|請掌舵者|交給掌舵者|交由掌舵者|等掌舵者|掌舵者本人|"
    r"待您|留給您|請您|交給您|交由您|由您決定|您來決定|等您|需要您|需您|"
    r"人工決定|人工項|待人工|待裁決|待決定|待決策|您裁決)")

#: 抑制 ①：否定——「沒有任何事卡在等您」是正解（普查實測的假紅）。只看交棒詞前 `NEGATION_WINDOW`
#: 個字元（含詞本身）：整句判會把立案那一則（「本輪沒有未結工作，只剩…兩件人工決定」）一起靜音。
NEGATION_RE = re.compile(r"(沒有|不需|無需|不必|不用|不再|未有|無任何)")
NEGATION_WINDOW = 8
#: 同句抑制 ②：權限核准走 harness 權限牆，不是 AskUserQuestion（普查兩筆）。
PERMISSION_RE = re.compile(r"(權限|核准此|允許我|permission)")
#: 同句抑制 ③：K=1 決定須掌舵者親打（AskUserQuestion 不是 DEC 載體）。`打[「『]`、`句話`
#: 是在 8 筆普查上補的（檔頭已登記為調參）；`須掌舵者親打` 是給主控寫在句內的明示逃生口。
K1_RE = re.compile(
    r"(親打|親自輸入|逐字輸入|決定行|一則一|打字|再打|打一次|打[「『]|句話|須掌舵者親打)")
#: 同句抑制 ④：作者已寫明用了互動選項。
INTERACTIVE_RE = re.compile(r"(互動選項|AskUserQuestion)")

_SENTENCE_RE = re.compile(r"(?<=[。！？!?\n])")
#: 引號內的詞是**被談論的對象**，不是交棒（「不採信備忘錄裡的「待您處理」字樣」）。判「落在一對
#: 引號之間」而非「剛好被夾住」：被引述的常是整個片語，交棒詞只是其中一截。
_ASYMMETRIC_QUOTES = (("「", "」"), ("『", "』"), ("“", "”"), ("‘", "’"))
_SYMMETRIC_QUOTES = ('"', "'", "`")

#: 回合邊界：真人（或 SDK）打字的 role=user 訊息。值與 `check_claim_provenance.py` 的
#: `_OPERATOR_TURN_ORIGINS`／`_HARNESS_BODY_PREFIXES` 逐字相同，由回歸鎖對帳（同一份知識
#: 允許住兩個家的唯一條件就是有東西在對帳；本檔不 import 那支檔——import 期爆掉會破壞 fail-open）。
_OPERATOR_TURN_ORIGINS = ("human", "sdk")
_HARNESS_BODY_PREFIXES = ("<task-notification>", "<command-name>",
                          "<local-command-stdout>", "This session is being continued")
_USER_TOKENS = ('"type":"user"', '"type": "user"')
ASK_TOOL = "AskUserQuestion"
#: 逐字稿上限（防呆）：本機最大逐字稿 25 MB（本立案那一場）；超限一律 fail-open。
BYTE_CAP = 64 * 1024 * 1024
#: 痕跡檔名（與 `claim_freshness.jsonl` 同目錄、同「沒觸發＝檔不長大」語意）。
TRACE_NAME = "handoff_block.jsonl"


def _is_quoted(text: str, start: int, end: int) -> bool:
    """`text[start:end]` 落在同一對引號之間（＝它是被引述的片語的一部分，不是斷言）。"""
    for opener, closer in _ASYMMETRIC_QUOTES:
        opened = text.rfind(opener, 0, start)
        if opened >= 0 and text.find(closer, opened + 1, start) < 0 and text.find(closer, end) >= 0:
            return True
    return any(text.count(mark, 0, start) % 2 == 1 and text.find(mark, end) >= 0
               for mark in _SYMMETRIC_QUOTES)


def pending_handoff_hits(claim_text: str) -> list[dict]:
    """`claim_text` 裡「把決定／待辦留給掌舵者」的句子（`[]`＝沒有）。純函式，供 Stop 分支與
    `tools/probe/handoff_census.py` 共用同一份判準。"""
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(claim_text):
        if not sentence.strip():
            continue
        if any(rx.search(sentence) for rx in (PERMISSION_RE, K1_RE, INTERACTIVE_RE)):
            continue
        for match in HANDOFF_RE.finditer(sentence):
            if _is_quoted(sentence, match.start(), match.end()):
                continue
            # 否定只看交棒詞**緊鄰的前文**（含詞本身）：「沒有任何事卡在等您」靜音；
            # 「本輪沒有未結工作，只剩…兩件人工決定」是立案那一則，句內另有「沒有」也必須紅。
            window = sentence[max(0, match.start() - NEGATION_WINDOW):match.end()]
            if NEGATION_RE.search(window):
                continue
            hits.append({"word": match.group(0), "sentence": sentence.strip()[:200]})
    return hits


def _is_operator_turn(rec: dict) -> bool:
    """這筆記錄是真人（或 SDK）打字的一輪發言（回合邊界），不是 tool_result 中繼或 harness 代筆。"""
    if rec.get("type") != "user" or rec.get("isMeta") is True or rec.get("isCompactSummary"):
        return False
    for key in ("origin", "turnOrigin"):
        value = rec.get(key)
        kind = value.get("kind") if isinstance(value, dict) else value
        if kind is not None:
            return str(kind) in _OPERATOR_TURN_ORIGINS
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        if all(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return False
        text = "".join(c.get("text", "") for c in content
                       if isinstance(c, dict) and c.get("type") == "text")
    elif isinstance(content, str):
        text = content
    else:
        return False
    return not text.lstrip().startswith(_HARNESS_BODY_PREFIXES)


def _asks_user(rec: dict) -> bool:
    if rec.get("type") != "assistant" or rec.get("isSidechain"):
        return False
    content = (rec.get("message") or {}).get("content")
    return isinstance(content, list) and any(
        isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == ASK_TOOL
        for c in content)


def asked_this_turn(transcript_path: str, byte_cap: int = BYTE_CAP) -> bool:
    """本回合（最後一則真人 role=user 訊息之後）有沒有任何 `AskUserQuestion` tool_use。

    🔴 讀不到／超上限一律 **raise**，讓 `main()` 走 fail-open 靜默放行；絕不可回 False——
    「證據面拿不到」與「本回合沒問」必須分開，否則逐字稿壞掉就會把每一則收尾都推回。
    """
    if os.path.getsize(transcript_path) > byte_cap:  # OSError ⇒ 交給 main() fail-open
        raise ValueError("transcript exceeds byte cap")
    asked = False
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            is_user = any(token in line for token in _USER_TOKENS)
            if not is_user and ASK_TOOL not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            if _is_operator_turn(rec):
                asked = False
            elif _asks_user(rec):
                asked = True
    return asked


def block_message(hits: list[dict]) -> str:
    """推回主控的那一句：說清楚兩條出路與 K=1 的逃生口（可滿足性是設計約束不是客氣）。"""
    words = "／".join(sorted({str(h.get("word")) for h in hits}))
    return (f"🔴 這一則把決定或待辦用散文留給掌舵者（命中：{words}），而本回合沒有用 "
            "AskUserQuestion。掌舵者 2026-10-31 常態授權（sid 655d9777 line 12）：能代決的依"
            "最適方案代決並把 WHY 寫進帳本或 commit；真需要掌舵者的，在這一回合用 "
            "AskUserQuestion 給互動選項（最簡單解釋、建議選項排第一）。若這是只能由掌舵者親打的 "
            "K=1 決定，請在回覆寫明「須掌舵者親打」再結束。（判準："
            ".claude/hooks/check_pending_handoff.py；關閉：AUTOSDD_HANDOFF_GUARD_OFF=1）")


def _trace(hits: list[dict], session_id: str) -> None:
    """落一列痕跡（「沒觸發＝檔不長大」）。任何 I/O 失敗吞掉：痕跡不得反過來變成守衛的故障源。"""
    if trace_dir is None:
        return
    try:
        path = os.path.join(str(trace_dir()), TRACE_NAME)
        row = {"ts": datetime.now(timezone.utc).isoformat(), "session_id": session_id,
               "words": sorted({str(h.get("word")) for h in hits})}
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    except Exception:  # noqa: BLE001 — 見 docstring
        pass


def main() -> int:
    try:
        if os.environ.get("AUTOSDD_HANDOFF_GUARD_OFF") or os.environ.get("AUTOSDD_UNATTENDED"):
            return 0
        payload = read_hook_payload()
        # 🔴 迴圈煞車：CC 只在「這一回合是 Stop hook 造成的續跑」時才給 True ⇒ 第二次一律放行。
        if payload.get("stop_hook_active"):
            return 0
        claim = str(payload.get("last_assistant_message") or "")
        transcript = str(payload.get("transcript_path") or "")
        if not claim or not transcript:
            return 0
        hits = pending_handoff_hits(claim)
        if not hits or asked_this_turn(transcript):
            return 0
        _trace(hits, str(payload.get("session_id") or ""))
        doc = {"decision": "block", "reason": block_message(hits),
               "systemMessage": ("⏸ check_pending_handoff：收尾把決定留給掌舵者卻沒給互動選項，"
                                 "已推回主控一次（第二次 Stop 放行）。")}
        sys.stdout.write(json.dumps(doc, ensure_ascii=True) + "\n")
        sys.stdout.flush()
        return 0
    except Exception:  # noqa: BLE001 — fail-open（P0：hook 崩潰不得演變成阻斷）
        return 0


if __name__ == "__main__":
    sys.exit(main())
