package com.aisdlc.console.adapter.out.bridge;

import org.springframework.http.client.ClientHttpRequestFactory;

import java.time.Duration;

/**
 * 依「連線／讀取逾時」組出 HTTP 請求工廠（契約 §3.1 每個 Bridge 呼叫各有逾時：健康探測 2s／3s、approve 2s／10s、
 * compile 2s／15s、decompose 2s／{@code model.timeout}＋15s）。
 *
 * <p>回 {@code null}＝「不覆寫，沿用 {@code RestClient.Builder} 自己的工廠」——測試以此讓
 * {@code MockRestServiceServer}（綁在 Builder 上）接手所有請求。
 */
@FunctionalInterface
public interface RequestFactoryProvider {

    ClientHttpRequestFactory create(Duration connectTimeout, Duration readTimeout);
}
