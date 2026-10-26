package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.IssueQueryUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.IssuePriorityRepository;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.issue.IssuePriority;
import com.aisdlc.console.domain.model.si.SiExport;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 議題中心的唯讀查詢（TCS-IssueCenter-20261027 R-IC-49、R-IC-50、D-C3）：每個請求恰一次 Bridge 呼叫（{@code AgentBridge.siExport("issues", …)}，連線 2 秒、
 * 讀取 20 秒、不重試）加<b>一次</b>順位表讀取（以本頁項目的編號集合；頁內沒有任何編號時不查詢），<b>不快取</b>、<b>不重算</b>。議題中心的 {@code Issue*} 類別
 * 呼叫 {@code AgentBridge} 的方法只有 {@code siExport}（ArchUnit 鎖住）；本類別是對 Bridge 的<b>唯一</b>讀取通道（{@link IssuePriorityService} 的
 * 「先取該議題」也經 {@link #fetchOne}）。
 *
 * <p>合併規則：Bridge 的每筆議題<b>最後</b>多兩個鍵——{@code priority}（整數）、{@code priority_note}（字串，可為空字串）：僅當該筆 {@code rankable} 為真且順位表
 * 有它的列才有值，其餘一律 {@code null}（遺留列不顯示、不參與排序）；鍵名在回應邊界經 {@code SiKeyNames} 轉成 {@code priorityNote}。
 * 順位表讀取失敗＝整個請求失敗（資料存取例外原樣往上丟、無 {@code data}）：不回缺 priority 的清單，以免把「量不到」顯示成「未排」。
 *
 * <p>Bridge 失敗對映沿 SelfImproving 唯讀端點（{@link SiBridgeErrors#map}：503 {@code si_unavailable} 逐字轉出 {@code cause}、{@code detail}；422 為「引擎拒絕此請求」；
 * 其餘 4xx 當作上游故障），唯一的差別是 404 {@code si_not_found} 的訊息為「查無此議題」（SI 端點的訊息是「查無此提案」）。連線失敗、5xx、逾時在介面卡
 * 已轉成 502／504。任何失敗都沒有部分資料。
 */
@Service
public class IssueQueryService implements IssueQueryUseCase {

    private final AgentBridge bridge;
    private final IssuePriorityRepository priorities;

    IssueQueryService(AgentBridge bridge, IssuePriorityRepository priorities) {
        this.bridge = bridge;
        this.priorities = priorities;
    }

    @Override
    public SiExport list(Integer since, Integer limit, String status, String source) {
        if (since != null && since < 0) {
            throw ValidationException.of("since", "since 須為 0 以上的整數");
        }
        if (limit != null && limit < 1) {
            throw ValidationException.of("limit", "limit 須為 1 以上的整數");
        }
        return withPriorities(fetch(since, limit, null, status, source));
    }

    @Override
    public SiExport one(String id) {
        return withPriorities(fetchOne(id));
    }

    /**
     * 單筆（Bridge 原樣、<b>未</b>合併順位）。{@code id} 的格式單一真相在 Bridge（不合為 422，合法而查無為 404），這裡只驗非空。
     * 同一包的 {@link IssuePriorityService} 用它做 PUT 的「先取該議題」。
     */
    SiExport fetchOne(String id) {
        if (id == null || id.isEmpty()) {
            throw ValidationException.of("id", "id 不可為空");
        }
        return fetch(null, null, id, null, null);
    }

    private SiExport fetch(Integer since, Integer limit, String id, String status, String source) {
        try {
            return bridge.siExport("issues", since, limit, id, status, source);
        } catch (BridgeRejectedException e) {
            throw map(e);
        }
    }

    private static DomainException map(BridgeRejectedException e) {
        DomainException mapped = SiBridgeErrors.map(e);
        if (mapped instanceof NotFoundException notFound && ErrorReasons.SI_NOT_FOUND.equals(notFound.reason())) {
            return new NotFoundException("查無此議題", ErrorReasons.SI_NOT_FOUND, notFound.details());
        }
        return mapped;
    }

    @SuppressWarnings("unchecked")
    private SiExport withPriorities(SiExport export) {
        Map<String, Object> raw = new LinkedHashMap<>(export.raw());
        if (!(raw.get("items") instanceof List<?> items)) {
            return export;
        }
        Set<String> ids = new LinkedHashSet<>();
        for (Object item : items) {
            if (item instanceof Map<?, ?> map && map.get("id") instanceof String id) {
                ids.add(id);
            }
        }
        Map<String, IssuePriority> found = priorities.findByIssueIds(ids);
        List<Object> merged = new ArrayList<>(items.size());
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> map)) {
                merged.add(item);
                continue;
            }
            Map<String, Object> copy = new LinkedHashMap<>((Map<String, Object>) map);
            IssuePriority row = Boolean.TRUE.equals(copy.get("rankable")) && copy.get("id") instanceof String id
                    ? found.get(id) : null;
            copy.put("priority", row == null ? null : row.rank());
            copy.put("priority_note", row == null ? null : row.note());
            merged.add(copy);
        }
        raw.put("items", merged);
        return new SiExport(raw);
    }
}
