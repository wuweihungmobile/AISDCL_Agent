"""tools/lib/dispatch_imbalance.py — DEF-200-274 第七輪：平行派工負載不均自動偵測。

WHY：第五、六輪的「頭重腳輕」熱點（`test_doc_loc_baseline_freshness_r60.py`／
`test_archive_defect_log.py`）都是靠人親自讀 `report_module_timings()` 印出的
耗時排行、自己心算「這個數字是不是不成比例」才發現的（見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第六輪〉
誠實劃界：「下一個新熱點出現時仍需人工重新發現與加白名單」）。本模組把這個
心算自動化：純函式讀 `parallel_shard.run_parallel()` 已經收集好的
`module_timings`，算出每個派工單位相對於「公平均分基準」（總耗時 / worker 數）
的倍率，倍率超過門檻的單位即為潛在新熱點，回傳給呼叫端印出可執行的建議
（比照白名單機制）。純偵測、不阻斷——效能觀測不應讓測試套件本身失敗；
false negative（漏抓）好過 false positive（把本來就吃重、已知不可再分割的
單一測試錯判成新問題）。

WHY 用「公平均分基準」而非「總 wall-clock」：`run_parallel()` 目前不記錄自己
的總 wall-clock（呼叫端 `run_with_floor()` 也沒有量），若為此另外加時間戳
是對既有函式的非必要改動（Rule 3 surgical changes）。而「單一派工單位耗時
是否遠超過總工作量平均分給每個 worker 的份額」本身就是「這個單位會不會變成
拖累全體的瓶頸」的直接判準——不管實際排程順序為何，一個耗時遠超公平份額的
單位，最終都會讓某個 worker 的完工時間被它獨佔拉長，其餘 worker 再快也沒用，
這正是「頭重腳輕」的定義本身。

WHY 分母用 `min(worker_count, len(module_timings))`（第七輪四方獨立複審
Architect/SA/SD/QA 共同點名並經 QA 合成場景實測證實）：`parallel_shard.
run_parallel()` 自己在 `n = min(worker_count(), len(modules_sorted)) or 1`
這一行就已經把「實際會啟動幾條 worker」cap 到派工單位數——單位數不夠時，
多出來的 worker 名額本來就用不到。若分母仍用未經 cap 的名目 `worker_count`，
當派工單位數 ≤ worker_count 時，`fair_share` 會被算得比「真正能達到的均分」
更小，導致**即使所有單位耗時完全相同**也會全數被誤判為不均（QA 實測：3 個
耗時皆為 20.0 的單位、worker_count=8 時，倍率恆為 2.67、全部 3 個都被標記）。
目前唯一的生產呼叫路徑（`tools/tests/` 全樹掃描，139 個派工單位 vs worker
上限 8）派工單位數遠大於 worker_count，不會踩到這個象限，但公式本身的正確性
不該依賴這個僥倖——修法直接讓分母不可能超過實際能用上的並行度。
"""
from __future__ import annotations

import os


def detect_imbalance(
    module_timings: dict[str, float],
    worker_count: int,
    ratio_threshold: float = 1.5,
) -> list[tuple[str, float, float]]:
    """回傳依「倍率」遞減排序的 `(派工鍵, 耗時秒數, 倍率)` 清單，只含倍率超過
    `ratio_threshold` 的單位。倍率 = 該單位耗時 / 公平均分基準（總耗時 /
    `min(worker_count, len(module_timings))`，理由見檔頭 WHY）。

    `module_timings` 為空、`worker_count <= 0`（未知/序列模式）皆回傳空清單——
    量測本身不可信時寧可不判，不誤報（fail-closed 但不 fail-loud：這是效能
    觀測，非正確性守門）。
    """
    if not module_timings or worker_count <= 0:
        return []
    effective_workers = min(worker_count, len(module_timings))
    fair_share = sum(module_timings.values()) / effective_workers
    if fair_share <= 0:
        return []
    flagged = [
        (key, elapsed, elapsed / fair_share)
        for key, elapsed in module_timings.items()
        if elapsed / fair_share > ratio_threshold
    ]
    flagged.sort(key=lambda item: item[2], reverse=True)
    return flagged


def report_dispatch_imbalance(result: object, worker_count: int) -> None:
    """第七輪：自動偵測新的「頭重腳輕」熱點，不需要人工重讀耗時排行心算比例。
    序列模式（無 `module_timings`）或無不均時不印。抽成本檔（而非留在
    `run_root_unittests.py`）的理由同 `dispatch_granularity.py` 檔頭 WHY——
    呼叫端受 LOC 分級政策 special-tier 行數棘輪管制，落地當輪已無餘裕。

    第八輪：在 CI 上（`GITHUB_ACTIONS=true`）額外逐筆印一行 GitHub Actions 原生
    `::warning::` annotation——這種格式的行會被 GitHub 直接抓進該次 run 的摘要
    頁面，不需要人工捲動冗長的 log 中段才看得到（本函式此前的輸出只是普通
    print，混在成百上千行 unittest 輸出裡）。非 CI 環境（環境變數未設）維持
    原本純 print 行為不變，不多印任何東西。

    第九輪 D3 新增兩段，皆刻意**新增區塊**而非調低既有 1.5 門檻（既有 11 支
    `DispatchImbalanceDetectionTest`／`ReportDispatchImbalanceTest` 逐字沿用）：
    ① 1.0~1.5 倍率帶——單一單位已超過公平份額但未到既有熱點門檻，排程救不了、
       只能靠細分，去重後只印一次；② 整體排程效率 `wall/ideal`——`result` 沒有
       `wall_clock` 屬性（序列模式／舊呼叫端）時 `getattr` 回 `None`、整段不印，
       零特判。
    """
    timings = getattr(result, "module_timings", None)
    if not timings:
        return
    on_ci = os.environ.get("GITHUB_ACTIONS") == "true"

    flagged = detect_imbalance(timings, worker_count)
    flagged_keys = {item[0] for item in flagged}
    if flagged:
        print(
            f"🚨 平行負載不均偵測：以下派工單位耗時遠超過公平均分基準"
            f"（worker={worker_count}）："
        )
        for key, elapsed, ratio in flagged:
            print(f"   - {key}: {elapsed:.1f}s（{ratio:.1f}x 公平均分基準）")
            if on_ci:
                print(
                    f"::warning::平行負載不均：{key} 耗時 {elapsed:.1f}s"
                    f"（{ratio:.1f}x 公平均分基準）"
                )
        print(
            "👉 建議：若為單一測試方法拖累整個模組，比照 "
            "tools/lib/dispatch_granularity.py 的 CLASS_LEVEL_DISPATCH_MODULES "
            "白名單機制細分派工鍵；若為多支測試普遍偏重，評估能否再細分或縮短該測試本身。"
        )

    over_share = [
        item for item in detect_imbalance(timings, worker_count, ratio_threshold=1.0)
        if item[0] not in flagged_keys
    ]
    if over_share:
        print("⚠️ 以下派工單位耗時超過公平份額（排程救不了，需細分才能再壓 makespan）：")
        for key, elapsed, ratio in over_share:
            print(f"   - {key}: {elapsed:.1f}s（{ratio:.1f}x 公平均分基準）")

    wall = getattr(result, "wall_clock", None)
    if wall:
        eff_workers = min(worker_count, len(timings)) if worker_count > 0 else 1
        ideal = max(sum(timings.values()) / max(eff_workers, 1), max(timings.values()))
        loss = wall / ideal if ideal > 0 else 1.0
        if loss > 1.15:
            finishes = getattr(result, "module_finish_times", None) or {}
            last = sorted(finishes.items(), key=lambda kv: -kv[1])[:5]
            print(f"🐢 整體排程效率：wall={wall:.1f}s ideal={ideal:.1f}s "
                  f"loss={loss:.2f}x（>1.15 門檻）")
            if last:
                print("   最後完工（可能是拖累 makespan 的尾端）：")
                for key, finish_at in last:
                    print(f"   - {key}: 第 {finish_at:.1f}s 完工")
