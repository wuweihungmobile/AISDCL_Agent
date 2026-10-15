package com.aisdlc.console.support;

/**
 * 整合測試共用的三台假外部伺服器（JDK HttpServer，綁 {@code 127.0.0.1} 的隨機埠，整個 JVM 共用一組）：
 * 假的 Engine Bridge、假的 OpenAI 相容 chat-completions 端點、一個通用目標（例如「重導向的目的地」，用來證明請求數為 0）。
 * 每個測試前由 {@link AbstractOutboundIT} 清空 stub 與已收請求。
 */
public final class OutboundFakes {

    /** 路徑：OpenAI 相容 chat-completions（匯入路徑 B 與測試連線的探測都打這一條）。 */
    public static final String CHAT_PATH = "/v1/chat/completions";

    public static final FakeHttpServer BRIDGE = FakeHttpServer.start();
    public static final FakeHttpServer LLM = FakeHttpServer.start();
    public static final FakeHttpServer TARGET = FakeHttpServer.start();

    private OutboundFakes() {
    }

    public static void resetAll() {
        BRIDGE.reset();
        LLM.reset();
        TARGET.reset();
    }
}
