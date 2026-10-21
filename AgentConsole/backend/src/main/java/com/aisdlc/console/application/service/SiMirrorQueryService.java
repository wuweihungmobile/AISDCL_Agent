package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiMirrorUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.si.SiExport;
import org.springframework.stereotype.Service;

/**
 * SelfImproving 唯讀鏡像（TCS-SelfImprovingMirror-P1b R7～R9）：每個請求恰一次 Bridge 呼叫（{@code AgentBridge.siExport}，連線 2 秒、
 * 讀取 20 秒、不重試）、<b>不快取</b>、<b>不重算</b>；回的就是 Bridge 的 export 物件原樣。console-api 對 SelfImproving 零寫入：
 * 本類別沒有任何寫入路徑，{@code AgentBridge} 上名稱以 {@code si} 起頭的方法也只有 {@code siExport}（ArchUnit 鎖住）。
 *
 * <p>輸入驗證只做 backend 自己能確定的：{@code since} 須 ≥0、{@code limit} 須 ≥1（不合＝400，且不會觸及 Bridge）。
 * {@code limit} 的上限住根層協定參數檔、不在這裡複製（超過時 Bridge 的 CLI 回非 0，經 Bridge 變成 503）；{@code id} 的格式
 * 單一真相在 Bridge，這裡原樣轉出（⚖ 29）。
 */
@Service
public class SiMirrorQueryService implements SiMirrorUseCase {

    private final AgentBridge bridge;

    public SiMirrorQueryService(AgentBridge bridge) {
        this.bridge = bridge;
    }

    @Override
    public SiExport status() {
        return fetch("status", null, null, null);
    }

    @Override
    public SiExport observations(Integer since, Integer limit) {
        return fetch("observations", since, limit, null);
    }

    @Override
    public SiExport events(Integer since, Integer limit) {
        return fetch("events", since, limit, null);
    }

    @Override
    public SiExport proposals(Integer since, Integer limit) {
        return fetch("proposals", since, limit, null);
    }

    @Override
    public SiExport proposal(String id) {
        if (id == null || id.isEmpty()) {
            throw ValidationException.of("id", "id 不可為空");
        }
        return fetch("proposals", null, null, id);
    }

    @Override
    public SiExport runs(Integer since, Integer limit) {
        return fetch("runs", since, limit, null);
    }

    private SiExport fetch(String kind, Integer since, Integer limit, String id) {
        if (since != null && since < 0) {
            throw ValidationException.of("since", "since 須為 0 以上的整數");
        }
        if (limit != null && limit < 1) {
            throw ValidationException.of("limit", "limit 須為 1 以上的整數");
        }
        try {
            return bridge.siExport(kind, since, limit, id);
        } catch (BridgeRejectedException e) {
            throw SiBridgeErrors.map(e);
        }
    }
}
