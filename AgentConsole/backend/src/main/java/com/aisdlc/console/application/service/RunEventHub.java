package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 事件扇出的樞紐：{@code RunEventProcessor} 處理完一則事件（交易已提交）後把框架 {@link #publish}，所有訂閱該 run 的前端連線
 * （{@code StreamConnection}）各自收到一份；終態處理完後 {@link #complete} 通知它們關閉。
 * 訂閱者的回呼必須<b>不阻塞</b>（連線自己有佇列），發布端才不會被慢速訂閱者拖住（契約 §2.1「慢速訂閱者」）。
 */
@Component
public class RunEventHub {

    /** 訂閱者：只接受框架與關閉通知。 */
    public interface Listener {

        void accept(Frame frame);

        /** 該 run 進入終態且所有框架都已送出：連線應在送完佇列後關閉。 */
        void runEnded();
    }

    private final Map<UUID, List<Listener>> listeners = new ConcurrentHashMap<>();

    /** 訂閱與取消訂閱都在 {@code compute} 內完成（同一個 run 的並發操作不會彼此漏掉）；最後一個訂閱者離開就移除該 run 的項目，不累積空清單。 */
    public void subscribe(UUID runId, Listener listener) {
        listeners.compute(runId, (id, list) -> {
            List<Listener> next = list == null ? new CopyOnWriteArrayList<>() : list;
            next.add(listener);
            return next;
        });
    }

    public void unsubscribe(UUID runId, Listener listener) {
        listeners.computeIfPresent(runId, (id, list) -> {
            list.remove(listener);
            return list.isEmpty() ? null : list;
        });
    }

    public void publish(UUID runId, List<Frame> frames) {
        List<Listener> list = listeners.get(runId);
        if (list == null || frames.isEmpty()) {
            return;
        }
        for (Listener listener : list) {
            for (Frame frame : frames) {
                listener.accept(frame);
            }
        }
    }

    public void complete(UUID runId) {
        List<Listener> list = listeners.get(runId);
        if (list != null) {
            list.forEach(Listener::runEnded);
        }
    }

    public int subscriberCount(UUID runId) {
        List<Listener> list = listeners.get(runId);
        return list == null ? 0 : list.size();
    }
}
