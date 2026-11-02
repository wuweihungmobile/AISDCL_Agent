package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchStreamUseCase;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchStreamSettings;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.research.ResearchViews.Event;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalLong;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 研究事件串流（API 契約 API-RP-05／06；ADR-003 D6）：事件來源是 append-only 事件帳 {@code console.research_events}（Bridge 是唯一寫入者），
 * <b>每個連線一條虛擬執行緒自己尾隨事件帳</b>——慢速訂閱者只拖住自己的寫出，不拖住發布端（沒有共用佇列，也就沒有「佇列滿」）。
 *
 * <p><b>起點與缺口</b>（AC-R2P-06-2；D-49）：沒有 {@code Last-Event-ID} 時從目前最大序號起（只送連線之後的新事件）。有 {@code Last-Event-ID} 時重播其後的事件，
 * 重播視窗＝事件帳最新的 {@code replay-window} 筆：視窗已逾期（可重播的第一筆比 {@code Last-Event-ID + 1} 大）就先送
 * {@code research.replay_gap}（{@code fromSeq}＝請求點加一、{@code toSeq}＝視窗內最舊序號減一）再續送可用事件；重播與尾隨過程中任何兩個相鄰事件的序號不連續
 * （缺 n 到 m）一樣在續送前送 {@code research.replay_gap}（{@code fromSeq}＝n、{@code toSeq}＝m）。缺口訊號是傳輸層訊號（無 {@code id:}、不佔 seq、不寫入事件帳）；
 * 客戶端收到即全量重抓（專案詳情、列表、REST {@code …/events?afterSeq=}）。連續 {@code heartbeat} 秒沒有任何框架就送 {@code heartbeat}。
 */
@Service
public class ResearchStreamService implements ResearchStreamUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(ResearchStreamService.class);
    /** 每次輪詢最多取的事件數；取滿就不睡、立刻再取（重播大量事件時不被輪詢間隔拖慢）。 */
    static final int BATCH = 200;
    /** 連續讀取失敗幾次後結束該連線（客戶端以 Last-Event-ID 重連；不在背景無限空轉）。 */
    static final int MAX_CONSECUTIVE_FAILURES = 20;

    private final ResearchProjectReadPort projects;
    private final ResearchStreamSettings settings;

    ResearchStreamService(ResearchProjectReadPort projects, ResearchStreamSettings settings) {
        this.projects = projects;
        this.settings = settings;
    }

    @Override
    public Subscription open(UUID researchId, String lastEventId, Sink sink) {
        if (!projects.exists(researchId)) {
            throw new NotFoundException("研究專案不存在：" + researchId, ErrorReasons.RESEARCH_NOT_FOUND, Map.of());
        }
        Long last = parse(lastEventId);
        long cursor;
        Frame gap = null;
        if (last == null) {
            cursor = projects.maxEventSeq(researchId);
        } else {
            long from = Math.min(last, projects.maxEventSeq(researchId));
            OptionalLong windowStart = projects.replayWindowStart(researchId, settings.replayWindow());
            if (windowStart.isPresent() && windowStart.getAsLong() > from + 1) {
                gap = gapFrame(from + 1, windowStart.getAsLong() - 1);
                cursor = windowStart.getAsLong() - 1;
            } else {
                cursor = from;
            }
        }
        Tail tail = new Tail(researchId, sink, cursor, gap);
        tail.start();
        return tail;
    }

    /** {@code Last-Event-ID}：非負整數才算；缺或格式不合視為沒有帶（不報錯：EventSource 會原樣回送它收到的最後一個 id）。 */
    private static Long parse(String lastEventId) {
        if (lastEventId == null || lastEventId.isBlank()) {
            return null;
        }
        try {
            long value = Long.parseLong(lastEventId.strip());
            return value < 0 ? null : value;
        } catch (NumberFormatException e) {
            return null;
        }
    }

    static Frame gapFrame(long fromSeq, long toSeq) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("fromSeq", fromSeq);
        data.put("toSeq", toSeq);
        return new Frame(null, "research.replay_gap", data);
    }

    /** 一個連線的尾隨執行緒。 */
    private final class Tail implements Subscription, Runnable {

        private final UUID id;
        private final Sink sink;
        private final Frame initialGap;
        private final AtomicBoolean closed = new AtomicBoolean(false);
        private long cursor;
        private long lastSentNanos = System.nanoTime();
        private Thread thread;

        Tail(UUID id, Sink sink, long cursor, Frame initialGap) {
            this.id = id;
            this.sink = sink;
            this.cursor = cursor;
            this.initialGap = initialGap;
        }

        void start() {
            thread = Thread.ofVirtual().name("research-sse-" + id).unstarted(this);
            thread.start();
        }

        @Override
        public void close() {
            if (closed.compareAndSet(false, true) && thread != null) {
                thread.interrupt();
            }
        }

        @Override
        public void run() {
            try {
                if (initialGap != null && !send(initialGap)) {
                    return;
                }
                int failures = 0;
                while (!closed.get()) {
                    List<Event> batch;
                    try {
                        batch = projects.eventsAfter(id, cursor, BATCH);
                        failures = 0;
                    } catch (RuntimeException e) {
                        LOG.debug("研究事件讀取失敗（{}，第 {} 次）：{}", id, failures + 1, e.toString());
                        if (++failures >= MAX_CONSECUTIVE_FAILURES) {
                            sink.close();
                            return;
                        }
                        Thread.sleep(settings.pollInterval());
                        continue;
                    }
                    for (Event event : batch) {
                        if (event.seq() > cursor + 1 && !send(gapFrame(cursor + 1, event.seq() - 1))) {
                            return;
                        }
                        if (!send(new Frame(event.seq(), event.eventType(), event))) {
                            return;
                        }
                        cursor = event.seq();
                    }
                    if (batch.size() >= BATCH) {
                        continue;
                    }
                    if (batch.isEmpty() && System.nanoTime() - lastSentNanos >= settings.heartbeat().toNanos()
                            && !send(new Frame(null, "heartbeat", Map.of()))) {
                        return;
                    }
                    Thread.sleep(settings.pollInterval());
                }
            } catch (InterruptedException e) {
                // close() 取消訂閱：正常結束
                Thread.currentThread().interrupt();
            } finally {
                closed.set(true);
            }
        }

        /** 寫出一個框架；客戶端已斷線（回 false）即結束該連線。 */
        private boolean send(Frame frame) {
            boolean ok = sink.send(frame);
            if (ok) {
                lastSentNanos = System.nanoTime();
            }
            return ok;
        }
    }
}
