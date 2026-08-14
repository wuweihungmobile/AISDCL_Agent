#!/usr/bin/env python3
"""因果宣稱判準的**真實面假紅普查**（母體＝本機逐字稿，不是 tracked 檔）。

WHY 這支檔存在
--------------
判準若是 hook，它的真實輸入面就是逐字稿裡的 assistant 文字——照 tracked 面（repo 內
寫死的散文）判會把「只出現在描述它的文件裡」的命中讀成假紅，因而否決一個好判準
（`CLAUDE.md` 鐵律五對此有逐字判例，同輪 R84 實測）。本檔把 R89 那次普查做成**可重跑**
的產物：`DEF-200-046` 判過「普查沒有留下可重跑的產物 ⇒ 交棒書要後人用同樣方法複驗，
結構上做不到，而『假陽性 N 筆』這個關鍵驗收條件也無法複驗」。

三種形狀都在這裡，因為**被否決的那兩種也是交件的一部分**
--------------------------------------------------------
  `--shape g`（預設，＝上線的那一個）「錯誤字面被當成機制結論」。判準本體**向 hook 借**
      （`.claude/hooks/check_claim_provenance.py::error_literal_mechanism_hits`），依賴方向
      與 `audit_session.py` 同：probe 借 hook，hook 不 import 任何 repo 模組。
  `--shape a` 「因果宣稱裡的具名量在本場觀測值全同」＝把「常數不可能是變因」直接寫成
      判準。**已被本檔證偽**：它只知道識別字出現在句子裡，不知道它是不是被當成原因。
  `--shape b` 「具名量在本場沒有兩個相異觀測值」（含 0 次觀測）。**已被本檔證偽**：命中
      的幾乎都是程式符號（`step_id`／`rule_id`…），那些根本不是「量」。
逐筆判讀結論與數字見 `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md` §DEF-200-123；
本檔刻意不複寫那些數字（同一份知識住兩個家、而只有一個家會被改，是本 repo 反覆的病）。

用法
----
    python tools/probe/causal_form_census.py                  # 全部 slug，印摘要＋逐筆
    python tools/probe/causal_form_census.py --shape a --jsonl out.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
_TRANSCRIPT_HOME = Path.home() / ".claude" / "projects"

#: shape a/b 用：反引號內的 snake_case 識別字＝本 repo 散文指認「量」的主要形態。
_IDENT_RE = re.compile(r"`([a-z][a-z0-9]{2,}(?:_[a-z0-9]+)+)`")
#: 時間欄位排除：`"measured_at": "2026-..."` 會讓值域抓到 `2026` 而自製假紅（實測）。
_DATEISH_RE = re.compile(r"(?i)(_at|_time|date|ts)$")


def _load_hook():
    spec = importlib.util.spec_from_file_location("_claim_guard", _HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observations(corpus: str, ident: str) -> list[str]:
    """`ident` 在工具輸出裡的數值觀測（JSON 欄位／`k=v`／`k N%` 三種形態）。"""
    escaped = re.escape(ident)
    found: list[str] = []
    number = r"(-?\d+(?:\.\d+)?)"
    for pattern in ('"' + escaped + r'"\s*:\s*' + number + r"\s*[,}\n]",
                    r"\b" + escaped + r"\s*=\s*" + number + r"\b",
                    r"\b" + escaped + r"\s+" + number + r"\s*%"):
        found.extend(re.findall(pattern, corpus))
    return found


def _tool_text(block: dict) -> str:
    inner = block.get("content")
    if isinstance(inner, str):
        return inner
    if isinstance(inner, list):
        return " ".join(str(x.get("text") or "") for x in inner if isinstance(x, dict))
    return ""


def walk(path: Path, guard, shape: str, stats: Counter) -> list[dict]:
    """單支逐字稿：**前綴累積**工具輸出，逐則 assistant 文字套判準。

    前綴累積是刻意的——hook 在 Stop 那一刻看得到的證據面就是「到此為止」的工具輸出，
    拿整場（含之後才跑出來的）當證據面會低估命中，那是假綠方向。
    """
    corpus: list[str] = []
    hits: list[dict] = []
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        message = record.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                corpus.append(_tool_text(block))
            elif message.get("role") == "assistant" and block.get("type") == "text":
                joined = None
                text = str(block.get("text") or "")
                if shape == "g":
                    stats["sentences"] += sum(
                        1 for s in guard._SENTENCE_RE.split(text) if s.strip())
                    for s in guard._SENTENCE_RE.split(text):
                        if guard.MECHANISM_RE.search(s):
                            stats["mechanism_sentences"] += 1
                            if guard.CONTRAST_RE.search(s):
                                stats["suppressed_by_contrast"] += 1
                    joined = "\n".join(corpus)
                    for hit in guard.error_literal_mechanism_hits(text, joined):
                        hits.append({"file": path.name, **hit})
                    continue
                for s in guard._SENTENCE_RE.split(text):
                    s = s.strip()
                    if not s:
                        continue
                    stats["sentences"] += 1
                    if not guard.MECHANISM_RE.search(s):
                        continue
                    stats["mechanism_sentences"] += 1
                    if guard.CONTRAST_RE.search(s):
                        stats["suppressed_by_contrast"] += 1
                        continue
                    for ident in sorted(set(_IDENT_RE.findall(s))):
                        if _DATEISH_RE.search(ident):
                            continue
                        if joined is None:
                            joined = "\n".join(corpus)
                        values = observations(joined, ident)
                        distinct = sorted(set(values))
                        flagged = (len(values) >= 3 and len(distinct) == 1) if shape == "a" \
                            else len(distinct) < 2
                        if flagged:
                            hits.append({"file": path.name, "ident": ident,
                                         "n_obs": len(values), "distinct": distinct[:4],
                                         "sentence": s[:220]})
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", choices=("g", "a", "b"), default="g")
    parser.add_argument("--home", default=str(_TRANSCRIPT_HOME),
                        help="逐字稿家目錄（預設 ~/.claude/projects）")
    parser.add_argument("--jsonl", help="把逐筆命中寫成可 diff 的 .jsonl")
    args = parser.parse_args(argv)

    home = Path(args.home)
    if not home.is_dir():
        print(f"逐字稿家目錄不存在：{home}", file=sys.stderr)
        return 2
    guard = _load_hook()
    stats: Counter = Counter()
    hits: list[dict] = []
    # 🔴 `rglob` 不是 `glob("*/*.jsonl")`：subagent 的逐字稿住在
    # `<slug>/<session>/subagents/` 下**再深一層**，而它們佔本機母體的絕大多數
    # （實測 1,038 支裡有 978 支在那裡）。只掃頂層會把母體縮到 6%，
    # 那正是「假紅率看起來很低」最容易發生的地方。
    files = sorted(home.rglob("*.jsonl"))
    for path in files:
        hits.extend(walk(path, guard, args.shape, stats))

    print(f"母體：逐字稿 {len(files)} 支｜assistant 句 {stats['sentences']}｜"
          f"機制結論句 {stats['mechanism_sentences']}｜"
          f"對照詞抑制 {stats['suppressed_by_contrast']}")
    print(f"shape={args.shape} 命中 {len(hits)} 筆（逐筆判讀請人做，本檔不替你判）")
    for hit in hits:
        head = hit.get("literal") or f"{hit.get('ident')} n={hit.get('n_obs')} " \
                                     f"vals={hit.get('distinct')}"
        print(f"  [{hit['file'][:8]}] {head}\n      :: {hit['sentence']}")
    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as handle:
            for hit in hits:
                handle.write(json.dumps(hit, ensure_ascii=False) + "\n")
        print(f"逐筆已寫入 {args.jsonl}")
    return 0


if __name__ == "__main__":
    # UTF-8 stdio 保護：本檔的輸出全是中文，非 UTF-8 locale 下 stdout 會直接
    # UnicodeEncodeError、stderr 印成 \uXXXX（DEF-101-789 逐字重現）。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main())
