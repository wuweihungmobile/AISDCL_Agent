package com.aisdlc.console.support;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.function.Predicate;

/**
 * 測試用的假 HTTP 伺服器（JDK 內建 {@code com.sun.net.httpserver}，不加任何依賴），綁在 {@code 127.0.0.1} 的隨機埠：
 * 假的 OpenAI 相容 chat-completions 端點、假的 Bridge、會延遲／重導向／回錯誤碼的目標。
 *
 * <p>以「第一個符合的 stub」回應（依註冊順序）；沒有任何 stub 符合回 404；每個請求都被完整記錄（方法、路徑、標頭、本文），
 * 讓測試能驗「後端到底送了什麼」與「某個請求有沒有被送出」（例如 SSRF 被拒時請求數必須是 0）。
 */
public final class FakeHttpServer implements AutoCloseable {

    /** 收到的請求（標頭名稱小寫）。 */
    public record Received(String method, String path, Map<String, String> headers, String body) {
    }

    /** 回應：{@code delayMillis}＞0 時先睡再回（模擬慢速模型）。 */
    public record Response(int status, String body, Map<String, String> headers, long delayMillis) {

        public static Response json(int status, String body) {
            return new Response(status, body, Map.of("Content-Type", "application/json; charset=utf-8"), 0);
        }

        public static Response redirect(String location) {
            return new Response(302, "", Map.of("Location", location), 0);
        }

        public Response delayed(long millis) {
            return new Response(status, body, headers, millis);
        }
    }

    private record Stub(Predicate<Received> matcher, Response response) {
    }

    private final HttpServer server;
    private final List<Received> received = new CopyOnWriteArrayList<>();
    private final List<Stub> stubs = new CopyOnWriteArrayList<>();

    private FakeHttpServer(HttpServer server) {
        this.server = server;
    }

    public static FakeHttpServer start() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0), 0);
            FakeHttpServer fake = new FakeHttpServer(server);
            server.createContext("/", fake::handle);
            server.setExecutor(Executors.newCachedThreadPool());
            server.start();
            return fake;
        } catch (IOException e) {
            throw new IllegalStateException("無法啟動假 HTTP 伺服器", e);
        }
    }

    public int port() {
        return server.getAddress().getPort();
    }

    /** 以 {@code 127.0.0.1} 為 host 的完整 URL。 */
    public String url(String path) {
        return "http://127.0.0.1:" + port() + path;
    }

    /** 註冊 stub（先註冊先比對）。 */
    public FakeHttpServer on(Predicate<Received> matcher, Response response) {
        stubs.add(new Stub(matcher, response));
        return this;
    }

    /** 路徑完全相等且方法相等的便捷 stub。 */
    public FakeHttpServer on(String method, String path, Response response) {
        return on(r -> r.method().equals(method) && r.path().equals(path), response);
    }

    public List<Received> received() {
        return Collections.unmodifiableList(new ArrayList<>(received));
    }

    public List<Received> receivedAt(String path) {
        return received.stream().filter(r -> r.path().equals(path)).toList();
    }

    /** 清空 stub 與已收請求（每個測試前呼叫）。 */
    public void reset() {
        stubs.clear();
        received.clear();
    }

    private void handle(HttpExchange exchange) throws IOException {
        Map<String, String> headers = new LinkedHashMap<>();
        exchange.getRequestHeaders().forEach((name, values) -> headers.put(name.toLowerCase(), String.join(",", values)));
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        Received request = new Received(exchange.getRequestMethod(), exchange.getRequestURI().getPath(), headers, body);
        received.add(request);
        Response response = stubs.stream().filter(stub -> stub.matcher().test(request)).map(Stub::response)
                .findFirst().orElse(Response.json(404, "{\"error\":\"not found\"}"));
        try {
            if (response.delayMillis() > 0) {
                Thread.sleep(response.delayMillis());
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        byte[] bytes = response.body().getBytes(StandardCharsets.UTF_8);
        response.headers().forEach((k, v) -> exchange.getResponseHeaders().add(k, v));
        try {
            exchange.sendResponseHeaders(response.status(), bytes.length == 0 ? -1 : bytes.length);
            if (bytes.length > 0) {
                try (OutputStream out = exchange.getResponseBody()) {
                    out.write(bytes);
                }
            }
        } catch (IOException ignored) {
            // 客戶端已逾時斷線：測試故意製造的情形
        } finally {
            exchange.close();
        }
    }

    @Override
    public void close() {
        server.stop(0);
    }
}
