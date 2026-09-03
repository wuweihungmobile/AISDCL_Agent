#!/usr/bin/env python3
"""職責⑥：skip **剖面鍵的文法**——這棵樹的鍵該有哪幾軸、怎麼拼、怎麼拆回去。

🔴 缺陷本體（DEF-200-183，R98 mac 收尾實測；兩份 census 逐字見
`docs/06_quality/CrossPlatform_R98_Mac_Closure_Evidence.md` §5）：同一個剖面鍵
`AutoClaude/tests@darwin+nopg+nested` 量到**兩個值**——本機 `.venv`（pg extras
PRESENT）`untagged=96`；乾淨 venv（ABSENT）`untagged=162`，差 66 支。鍵沒有編碼
「pg extras 裝了沒」這一軸 ⇒ 天花板任填一值必然「一邊零鑑別力、另一邊恆假紅」，
而那正是 `skip_group_policy._RUNTIME_SKIP_CEILING` 上方散文自己講的、剖面之所以
必要的理由。缺的不是一筆登記，是**一整條軸**。

為何獨立成模組而不是塞進職責⑤（`skip_group_policy`）：那支加完本段後 `count_loc`
會破 `guardrail_lib<=400`（落地當回合實測 362 ＋ 約 47）。同一情形的既定處置逐字
寫在職責⑤自己的檔頭——它當年就是這樣從職責①（`skip_tag_policy`）分出來的。

🔴 誠實劃界（本模組**不**宣稱 DEF-200-183 已修完）：鍵有兩個生產者——
· 根層 `tools/run_root_unittests.skip_census_profile()`：已改為消費本模組的 builder；
· `AutoClaude/tools/local_ci_gate._skip_profile()`：**尚未**帶上 pgextras 軸，
  而該檔不在本輪的持有面（鐵律七：常數／史料／消費端不同持有面時不得並行動）。
掌舵者裁決逐字是「先修剖面軸，修好前維持 advisory 不登記」⇒ `profile_axis_problems()`
只餵 advisory 通道（`skip_group_policy.skip_target_report` 與「剖面未登記」那一支），
**不接任何閘門的 rc**；`_RUNTIME_SKIP_CEILING` 兩張表本輪刻意零 re-key（見下方
`legacy_profile` 的 WHY：re-key 若先於生產者落地，AutoClaude 那一棵的天花板會整批
退回 advisory＝比今天更沒有牙）。
"""
from __future__ import annotations

#: 能力軸的軸名（鍵裡不出現軸名本身，只出現它的 token；軸名是給訊息與判準用的）。
AXIS_PG = "pg"
AXIS_NESTED = "nested"
AXIS_PGEXTRAS = "pgextras"

#: 軸名 → 該軸在鍵裡的合法 token（**token 字面即鍵的一段**）。
#: 🔴 `pgextras` 的兩個 token 刻意不寫成 `pg`／`nopg`：那會與 `AXIS_PG` 的 token 撞字面，
#: 而 `profile_axis_problems` 判「這個鍵帶了哪些軸」靠的就是 token 集合的成員判定
#: ——兩軸共用 token 時，`+nopg+nested` 會被誤讀成「pgextras 軸已經帶上了」，
#: 也就是這道判準會對它要抓的那一個缺陷恆綠。
_AXIS_TOKENS: dict[str, tuple[str, ...]] = {
    AXIS_PG: ("pg", "nopg"),
    AXIS_NESTED: ("nested", "solo"),
    AXIS_PGEXTRAS: ("pgext", "nopgext"),
}

#: 每棵樹的鍵**必須**帶哪些軸（順序即拼鍵順序）。空 tuple ＝該樹的 skip 集合不隨
#: 任何已知能力軸改變，那是**實查後的宣告**、不是還沒想過：
#: · `tools/tests`：全樹搜 `CLAUDECODE` 命中 0（`run_root_unittests.skip_census_profile`
#:   的 docstring 已逐字記載這條誠實劃界）；pg extras 亦零相依。
#: · `AISDLC_SDD/fsm_runtime`：census 尚未接上它的閘門（見
#:   `skip_group_policy._UNMEASURED_RUNNER_PROFILES` 同鍵那一列），故先宣告零軸；
#:   接上閘門那一輪必須回來重新問「這棵樹有哪些軸」。
_TREE_REQUIRED_AXES: dict[str, tuple[str, ...]] = {
    "AutoClaude/tests": (AXIS_PG, AXIS_NESTED, AXIS_PGEXTRAS),
    "tools/tests": (),
    "AISDLC_SDD/fsm_runtime": (),
}

#: DEF-200-183 之後才加進鍵文法的軸。`legacy_profile()` 用它把新鍵映回 re-key 前的
#: 舊鍵，讓方向鎖不會因為 re-key 而整批失去射程（見該函式 WHY）。
_POST_HOC_AXES: tuple[str, ...] = (AXIS_PGEXTRAS,)


def known_trees() -> tuple[str, ...]:
    """有軸宣告的樹（給判準當分母用；順序穩定以利訊息可 diff）。"""
    return tuple(_TREE_REQUIRED_AXES)


def required_axes(tree: str) -> tuple[str, ...] | None:
    """`tree` 的鍵必須帶哪些軸；未宣告的樹回 `None`（**不是** `()`——「沒有軸」與
    「沒人宣告過軸」在型別上就必須分得開，同 `skip_group_policy.declared_skipped`
    對「量不到 vs 量到零」的既有紀律）。"""
    return _TREE_REQUIRED_AXES.get(tree)


def axis_tokens(axis: str) -> tuple[str, ...]:
    """`axis` 的合法 token。未登記的軸回 `()`。"""
    return _AXIS_TOKENS.get(axis, ())


def profile_parts(profile: str) -> tuple[str, str, tuple[str, ...]]:
    """`<樹>@<平台>[+<token>…]` → `(樹, 平台, token tuple)`。

    沒有 `@` 時整串當樹、平台為空字串（合成剖面在別的測試裡真的長這樣，例如
    `brand/new@profile`／`no-at-sign`；解析器對它們必須不拋例外，判斷交給判準）。
    """
    tree, _, rest = profile.partition("@")
    platform, *tokens = rest.split("+") if rest else [""]
    return tree, platform, tuple(tokens)


def platform_of(profile: str) -> str:
    """剖面鍵的平台段（`skip_group_policy._platform_of` 的實作家，同一份文法只一個家）。"""
    return profile_parts(profile)[1]


def census_profile(tree: str, platform: str, **axes: str) -> str:
    """鍵的**唯一產生器**：軸值照 `_TREE_REQUIRED_AXES` 宣告的順序拼成鍵。

    軸給少了／給多了／給了不合法的 token 一律 `ValueError`——鍵的字面不得靠各生產者
    自己字串拼接（那正是 pgextras 這一軸能漏掉而沒有任何東西出聲的機制：文法住在
    生產者裡，判準在另一個檔，兩邊沒有共同的家可以對帳）。
    """
    wanted = required_axes(tree)
    if wanted is None:
        raise ValueError(
            f"未宣告的樹 `{tree}`：請先在 skip_profile_key._TREE_REQUIRED_AXES 登記"
            f"它的能力軸（已宣告的樹＝{list(known_trees())}）")
    if set(axes) != set(wanted):
        raise ValueError(
            f"樹 `{tree}` 的能力軸必須恰為 {list(wanted)}，收到 {sorted(axes)}")
    tokens: list[str] = []
    for axis in wanted:
        value = axes[axis]
        if value not in _AXIS_TOKENS[axis]:
            raise ValueError(
                f"軸 `{axis}` 的值只能是 {list(_AXIS_TOKENS[axis])}，收到 {value!r}")
        tokens.append(value)
    return "+".join([f"{tree}@{platform}", *tokens])


def missing_axes(profile: str) -> tuple[str, ...] | None:
    """`profile` 少了本樹宣告的哪幾軸；樹未宣告時回 `None`（不可求值 ≠ 沒缺）。"""
    tree, _, tokens = profile_parts(profile)
    wanted = required_axes(tree)
    if wanted is None:
        return None
    got = set(tokens)
    return tuple(a for a in wanted if not got & set(_AXIS_TOKENS[a]))


def profile_axis_problems(profile: str) -> list[str]:
    """判準（純函式）：這個鍵有沒有把本樹**所有已知會動 census 的軸**都編碼進去。

    回空 list ＝這個鍵指得動唯一一個母體。🔴 未宣告的樹刻意回 **空 list 而不是問題**：
    合成剖面（別包測試裡的 `brand/new@profile` 之類）不該因為本判準而多出一行 advisory，
    而「這棵樹沒人宣告過軸」那一向由 `skip_group_policy.ci_platform_coverage_problems()`
    的分母帳負責——同一件事不開第二個家。
    """
    missing = missing_axes(profile)
    if not missing:
        return []
    return [
        f"剖面 `{profile}` 的鍵缺 {list(missing)} 軸（本樹宣告的軸＝"
        f"{list(required_axes(profile_parts(profile)[0]) or ())}）——同一鍵會在不同"
        "環境量到不同值（DEF-200-183 實測：pg extras PRESENT 時 untagged=96、ABSENT "
        "時 162，差 66 支），任填一值必然一邊零鑑別力、另一邊恆假紅。掌舵者裁決"
        "「先修剖面軸，修好前維持 advisory 不登記」⇒ 本行只出聲、不接任何閘門的 rc"
    ]


#: 🔴 DEF-200-183 的 **re-key 完成度棘輪**（只准降）：今天判準各表裡還有幾個鍵沒帶滿
#: 本樹宣告的軸。生產者（`AutoClaude/tools/local_ci_gate._skip_profile`，不在立這道鎖
#: 這一輪的持有面）補上 pgextras 那一刻，這些鍵**必須同一次變更全部 re-key**；而「同一次
#: 變更」在本 repo 的歷史裡反覆靠人記得而漏掉（R115 red-4 漏補第四層是同型 round-label-ok
#: ——該輪號是**已發生的史料引述**，不是本批的自稱，故具名豁免）。寫成
#: shrink-only 計數之後：re-key 一個就降一個，而**新增一個缺軸的鍵當場紅**——後者才是
#: 這道鎖平時真正在守的方向（缺陷未修完期間，帳面不得再長出新的歧義鍵）。
PRE_AXIS_KEY_DEBT_MAX = 5


def keys_missing_axes(*tables: object) -> list[str]:
    """`tables`（各判準表，任何可迭代出鍵的映射）裡「鍵還沒帶滿本樹宣告軸」的那些。

    刻意收參數而不直接讀 `skip_group_policy` 的表：那會是循環 import，而純函式讓
    反事實測試能餵合成表驗紅（同本模組其餘判準的既有形狀）。
    """
    out: set[str] = set()
    for table in tables:
        out |= {k for k in table if missing_axes(k)}  # type: ignore[union-attr]
    return sorted(out)


def legacy_profile(profile: str) -> str:
    """剝掉 `_POST_HOC_AXES` 的 token，回 re-key **之前**的同一個剖面鍵。

    🔴 為何非有不可（本輪實測的方向鎖破洞）：
    `test_skip_ceiling_ratchet_direction.ceiling_max_direction_problems()` 逐鍵拿
    `live.get(profile)`，取不到就 `continue`。而 re-key（每個鍵多一段 token）會讓凍結
    快照裡**每一個**鍵都取不到 ⇒ 整張凍結表被跳過、方向鎖零違規＝一次改名就把「天花板
    只准降」這道鎖整片關掉，而表徵與「本來就沒有違規」完全相同。把 live 鍵先映回舊鍵
    再比對，re-key 就不再是繞道；而 re-key 造成的「一鍵裂成多鍵」也必須**每一個後代**
    都受同一個凍結值約束（裂鍵不得成為加大額度的手段）。
    """
    tree, platform, tokens = profile_parts(profile)
    late = {t for axis in _POST_HOC_AXES for t in _AXIS_TOKENS[axis]}
    kept = [t for t in tokens if t not in late]
    return "+".join([f"{tree}@{platform}", *kept]) if "@" in profile else profile
