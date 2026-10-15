package com.aisdlc.console.support;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.function.Predicate;
import java.util.stream.Stream;

/**
 * 測試用 SSE 客戶端：對<b>真的 HTTP 伺服器</b>（RANDOM_PORT）開一條串流，逐行解析 {@code id／event／data／retry} 與註解行，
 * 供斷言「解析後的欄位」（契約 §2.1、AR-03：不比對位元組字面）。讀取在自己的執行緒；非 200 的回應把本文收進 {@link #rawBody()}。
 */
public final class SseProbe implements AutoCloseable {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    /** 一個框架（以空行結尾）：事件、註解（keep-alive）或只有 {@code retry}。 */
    public record Frame(String id, String event, String data, String comment, Integer retry) {

        public boolean isEvent() {
            return event != null;
        }

        public boolean isComment() {
            return comment != null && event == null;
        }

        public JsonNode json() {
            return JSON.readTree(data);
        }

        /** id 的 {@code (seq, n)}；沒有 id 回 null。 */
        public long[] order() {
            if (id == null) {
                return null;
            }
            String[] parts = id.split("\\.");
            return new long[] {Long.parseLong(parts[0]), parts.length > 1 ? Long.parseLong(parts[1]) : 0L};
        }
    }

    private final List<Frame> frames = new CopyOnWriteArrayList<>();
    private final List<String> raw = new CopyOnWriteArrayList<>();
    private final CountDownLatch responded = new CountDownLatch(1);
    private final CountDownLatch ended = new CountDownLatch(1);
    private final Thread reader;
    private volatile HttpResponse<Stream<String>> response;
    private volatile Throwable failure;

    private SseProbe(String url, Map<String, String> headers) {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(url)).GET()
                .header("Accept", "text/event-stream");
        headers.forEach(request::header);
        reader = Thread.ofVirtual().name("sse-probe").unstarted(() -> read(client, request.build()));
        reader.start();
    }

    /** 開一條串流並等到回應標頭（逾時 10 秒）。 */
    public static SseProbe open(String url, Map<String, String> headers) {
        SseProbe probe = new SseProbe(url, headers);
        try {
            if (!probe.responded.await(10, TimeUnit.SECONDS)) {
                throw new IllegalStateException("SSE 連線 10 秒內沒有回應標頭：" + url);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
        if (probe.failure != null) {
            throw new IllegalStateException("SSE 連線失敗：" + probe.failure, probe.failure);
        }
        return probe;
    }

    private void read(HttpClient client, HttpRequest request) {
        try {
            HttpResponse<Stream<String>> res = client.send(request, HttpResponse.BodyHandlers.ofLines());
            response = res;
            if (res.statusCode() != 200) {
                // 錯誤回應的本文很短：先讀完再通知「已回應」，呼叫端拿到 status 時 rawBody() 就已完整
                res.body().forEach(raw::add);
                responded.countDown();
                return;
            }
            responded.countDown();
            String id = null;
            String event = null;
            String comment = null;
            Integer retry = null;
            StringBuilder data = null;
            for (String line : (Iterable<String>) res.body()::iterator) {
                if (line.isEmpty()) {
                    if (id != null || event != null || data != null || comment != null || retry != null) {
                        frames.add(new Frame(id, event, data == null ? null : data.toString(), comment, retry));
                    }
                    id = null;
                    event = null;
                    comment = null;
                    retry = null;
                    data = null;
                } else if (line.startsWith(":")) {
                    comment = stripOneSpace(line.substring(1));
                } else {
                    int colon = line.indexOf(':');
                    String name = colon < 0 ? line : line.substring(0, colon);
                    String value = colon < 0 ? "" : stripOneSpace(line.substring(colon + 1));
                    switch (name) {
                        case "id" -> id = value;
                        case "event" -> event = value;
                        case "data" -> {
                            if (data == null) {
                                data = new StringBuilder(value);
                            } else {
                                data.append('\n').append(value);
                            }
                        }
                        case "retry" -> retry = Integer.parseInt(value);
                        default -> { }
                    }
                }
            }
        } catch (IOException e) {
            failure = e;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (RuntimeException e) {
            // 連線被我們自己關掉時，Stream 會丟 UncheckedIOException：不是測試失敗
            if (!(e.getCause() instanceof IOException)) {
                failure = e;
            }
        } finally {
            responded.countDown();
            ended.countDown();
        }
    }

    private static String stripOneSpace(String value) {
        return value.startsWith(" ") ? value.substring(1) : value;
    }

    // ── 觀測 ────────────────────────────────────────────────────────────────────

    public int status() {
        return response == null ? -1 : response.statusCode();
    }

    public String header(String name) {
        return response == null ? null : response.headers().firstValue(name).orElse(null);
    }

    public List<String> headerValues(String name) {
        return response == null ? List.of() : response.headers().allValues(name);
    }

    /** 非 200 回應的本文（例：401／404 的 JSON）。 */
    public String rawBody() {
        return String.join("\n", raw);
    }

    public List<Frame> frames() {
        return List.copyOf(frames);
    }

    /** 全部事件框架（不含註解與 retry）。 */
    public List<Frame> events() {
        return frames.stream().filter(Frame::isEvent).toList();
    }

    public List<Frame> events(String name) {
        return frames.stream().filter(f -> name.equals(f.event())).toList();
    }

    public List<Frame> comments() {
        return frames.stream().filter(Frame::isComment).toList();
    }

    /** 等到出現第一個符合條件的框架（依到達順序；逾時回 null）。 */
    public Frame await(Predicate<Frame> predicate, Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (System.nanoTime() < deadline) {
            for (Frame frame : frames) {
                if (predicate.test(frame)) {
                    return frame;
                }
            }
            if (ended.getCount() == 0) {
                for (Frame frame : frames) {
                    if (predicate.test(frame)) {
                        return frame;
                    }
                }
                return null;
            }
            sleep(20);
        }
        return null;
    }

    public Frame awaitEvent(String event, Duration timeout) {
        return await(f -> event.equals(f.event()), timeout);
    }

    /** 等到串流結束（伺服器關閉連線）；逾時回 false。 */
    public boolean awaitEnd(Duration timeout) {
        try {
            return ended.await(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    public boolean isEnded() {
        return ended.getCount() == 0;
    }

    /** 事件 id 是否依 {@code (seq, n)} 嚴格遞增（沒有 id 的框架略過）。 */
    public static boolean strictlyIncreasing(List<Frame> events) {
        long[] last = null;
        for (Frame frame : events) {
            long[] current = frame.order();
            if (current == null) {
                continue;
            }
            if (last != null && (current[0] < last[0] || (current[0] == last[0] && current[1] <= last[1]))) {
                return false;
            }
            last = current;
        }
        return true;
    }

    /** 事件名稱序列（含重複，依到達順序）。 */
    public List<String> eventNames() {
        List<String> names = new ArrayList<>();
        events().forEach(f -> names.add(f.event()));
        return names;
    }

    @Override
    public void close() {
        HttpResponse<Stream<String>> res = response;
        if (res != null) {
            res.body().close();
        }
        reader.interrupt();
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
