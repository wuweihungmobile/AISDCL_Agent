package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Sink;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Subscription;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * 一個前端 SSE 連線（契約 §2.1、§2.3）。
 *
 * <ul>
 *   <li><b>送出佇列</b>容量固定（預設 1,000 個框架）：佇列滿＝伺服器<b>主動關閉</b>該連線，客戶端以 {@code Last-Event-ID} 重連即補齊
 *       （不丟事件）；發布端永遠不阻塞，不會被慢速訂閱者拖住；</li>
 *   <li><b>先註冊、再重播</b>：連線在計算重播內容<i>之前</i>就訂閱了事件樞紐，重播期間收到的即時框架先暫存，重播送完再依序接上
 *       並以 {@code (seq, sub)} 去重——快照與即時事件之間不漏、不亂序、不重複；</li>
 *   <li><b>keep-alive</b>：連續 {@code keepAlive} 沒有任何框架就送一行註解（任何框架都重置計時）。</li>
 * </ul>
 * 寫出一律由本連線自己的虛擬執行緒負責（{@link Sink} 不必是執行緒安全的）。
 */
final class StreamConnection implements RunEventHub.Listener, Subscription {

    private static final Logger LOG = LoggerFactory.getLogger(StreamConnection.class);

    /** 佇列裡的結束標記（NO_ID 的框架不會是它）。 */
    private static final Frame END = new Frame(null, 0, 0, "end", null);

    private final UUID runId;
    private final Kind kind;
    private final Sink sink;
    private final Duration keepAlive;
    private final RunEventHub hub;
    private final LinkedBlockingQueue<Frame> queue;
    private final List<Frame> pending = new ArrayList<>();
    private boolean replaying = true;
    private boolean endAfterReplay;
    private long enqueuedKey = -1;
    private volatile boolean closed;
    private Thread writer;

    /**
     * @param kind 這條連線是 {@code /logs} 還是 {@code /metrics}：事件樞紐把一個 run 的全部框架（兩種串流的）都發給每個訂閱者，
     *             連線只收自己那一種——否則兩條串流的 id 會互相撞號、被去重誤丟，客戶端也會收到不屬於這條串流的事件
     */
    StreamConnection(UUID runId, Kind kind, Sink sink, int capacity, Duration keepAlive, RunEventHub hub) {
        this.runId = runId;
        this.kind = kind;
        this.sink = sink;
        this.keepAlive = keepAlive;
        this.hub = hub;
        this.queue = new LinkedBlockingQueue<>(Math.max(1, capacity));
    }

    void startWriter() {
        writer = Thread.ofVirtual().name("sse-writer-" + runId.toString().substring(0, 8)).start(this::writeLoop);
    }

    /** 重播階段暫存即時框架；重播結束後直接入佇列。 */
    @Override
    public synchronized void accept(Frame frame) {
        if (closed || frame.kind() != kind) {
            return;
        }
        if (replaying) {
            pending.add(frame);
            return;
        }
        enqueue(frame);
    }

    @Override
    public synchronized void runEnded() {
        if (closed) {
            return;
        }
        if (replaying) {
            endAfterReplay = true;
        } else {
            offerEnd();
        }
    }

    /**
     * 送出重播框架，再接上重播期間暫存的即時框架（依 {@code (seq, sub)} 排序、去重）。
     *
     * @param closeAfter true＝重播完就結束連線（run 已終態）
     */
    synchronized void deliverReplay(List<Frame> replay, boolean closeAfter) {
        if (closed) {
            return;
        }
        replay.forEach(this::enqueue);
        replaying = false;
        List<Frame> live = new ArrayList<>(pending);
        pending.clear();
        live.sort(Comparator.comparingLong(Frame::order));
        live.forEach(this::enqueue);
        if (closeAfter || endAfterReplay) {
            offerEnd();
        }
    }

    private void enqueue(Frame frame) {
        if (frame.hasId() && frame.order() <= enqueuedKey) {
            return;
        }
        if (!queue.offer(frame)) {
            LOG.warn("SSE 連線（run={}）的送出佇列已滿（{} 個框架），伺服器主動關閉；客戶端以 Last-Event-ID 重連即補齊", runId,
                    queue.size());
            shutdown(true);
            return;
        }
        if (frame.hasId()) {
            enqueuedKey = frame.order();
        }
    }

    private void offerEnd() {
        if (!queue.offer(END)) {
            shutdown(true);
        }
    }

    private void writeLoop() {
        try {
            while (!closed) {
                Frame frame = queue.poll(keepAlive.toMillis(), TimeUnit.MILLISECONDS);
                if (closed) {
                    return;
                }
                if (frame == null) {
                    if (!sink.comment("keep-alive")) {
                        shutdown(false);
                        return;
                    }
                } else if (frame == END) {
                    shutdown(true);
                    return;
                } else if (!sink.send(frame)) {
                    shutdown(false);
                    return;
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /** 結束連線；{@code notifySink}＝由伺服器端主動關閉（要通知前端的 emitter 完成）。 */
    private void shutdown(boolean notifySink) {
        synchronized (this) {
            if (closed) {
                return;
            }
            closed = true;
        }
        hub.unsubscribe(runId, this);
        queue.clear();
        if (notifySink) {
            sink.close();
        }
        Thread thread = writer;
        if (thread != null && thread != Thread.currentThread()) {
            thread.interrupt();
        }
    }

    @Override
    public void close() {
        shutdown(false);
    }

    boolean isClosed() {
        return closed;
    }
}
