package com.aisdlc.console.infrastructure.security;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * 對<b>真的 Tomcat</b>（RANDOM_PORT）連打未認證的登入請求，每個請求偽造一個不同的 {@code X-Forwarded-For}，回傳各次的狀態碼。
 * 用來驗 {@code RemoteIpValve} 信不信任這個測試 client（127.0.0.1）轉送的客戶端位址——MockMvc 沒有 Tomcat 的 Valve，看不到這件事。
 */
final class RemoteIpProbe {

    private RemoteIpProbe() {
    }

    /** 連打 {@code count} 次（錯誤帳密＝每次都是 401），第 i 次偽造 {@code X-Forwarded-For: 203.0.113.<i>}。 */
    static List<Integer> statusesWithDistinctForwardedFor(int port, int count) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        List<Integer> statuses = new ArrayList<>();
        for (int i = 1; i <= count; i++) {
            HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/v1/auth/login"))
                    .header("Content-Type", "application/json").header("X-Forwarded-For", "203.0.113." + i)
                    .POST(HttpRequest.BodyPublishers.ofString("{\"username\":\"nobody\",\"password\":\"wrong\"}")).build();
            statuses.add(client.send(request, HttpResponse.BodyHandlers.discarding()).statusCode());
        }
        return statuses;
    }
}
