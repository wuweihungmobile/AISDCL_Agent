package com.aisdlc.console.application.port.in;

import java.util.UUID;

/**
 * 研究事件串流的用例（API 契約 §1.4 API-RP-05／06、§3；ADR-003 D6）：{@code GET /api/v1/stream/research/{id}}。事件來源是 append-only 事件帳
 * {@code console.research_events}（Bridge 是唯一寫入者）：<b>每個連線一條虛擬執行緒自己尾隨事件帳</b>——慢速訂閱者只拖住自己的寫出，不拖住發布端
 * （沒有共用佇列，也就沒有「佇列滿」）。{@code id}＝事件 seq、{@code event}＝事件型別、{@code data}＝ResearchEvent（camelCase）。
 *
 * <p><b>重播與缺口</b>：{@code Last-Event-ID} 之後的事件從事件帳重播（最多最新 {@code replay-window} 筆）；重播不完整——視窗已逾期（{@code Last-Event-ID} 之後的第一筆
 * 比 {@code Last-Event-ID + 1} 大），或事件序號中間有缺口——時，伺服器先送 {@code research.replay_gap}（{@code fromSeq}、{@code toSeq}；傳輸層訊號，無 {@code id:} 行、
 * 不佔 seq、不寫入事件帳）再續送可用事件，客戶端改以 REST {@code afterSeq} 回補（D-49、AC-R2P-06-2）。沒有 {@code Last-Event-ID} 時不重播，只送連線之後的新事件。
 * 連續 {@code heartbeat} 秒沒有任何框架就送一個 {@code heartbeat} 事件（{@code data} 為 {@code {}}、無 id）。
 */
public interface ResearchStreamUseCase {

    /**
     * 一個要送給前端的 SSE 框架。{@code seq} 非 null＝事件框架（{@code id:} 行取它，{@code data} 為 {@code ResearchViews.Event}）；{@code seq} 為 null＝傳輸層框架
     * （{@code research.replay_gap}、{@code heartbeat}：不帶 {@code id:}，{@code data} 為 Map）。
     */
    record Frame(Long seq, String event, Object data) {
    }

    /** 前端連線的寫出端（web 層以 {@code SseEmitter} 實作）。回傳 false＝客戶端已斷線，用例會結束該連線。 */
    interface Sink {

        boolean send(Frame frame);

        /** 正常結束串流。 */
        void close();
    }

    /** 開啟的連線；{@code close()} 取消訂閱、停止該連線的背景執行緒。 */
    interface Subscription extends AutoCloseable {

        @Override
        void close();
    }

    /**
     * 開啟串流：驗專案存在（否則 {@code NotFoundException}，reason {@code research_not_found}；已封存者仍可讀），決定起點與缺口後啟動尾隨執行緒。
     *
     * @param lastEventId 客戶端的 {@code Last-Event-ID}；格式不合（不是非負整數）視為沒有帶
     */
    Subscription open(UUID researchId, String lastEventId, Sink sink);
}
