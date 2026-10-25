package com.aisdlc.console.support;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 「收完請求就掛斷」的假伺服器（綁 127.0.0.1 隨機埠）：讀完整個 HTTP 請求（標頭加 {@code Content-Length} 的本文）後<b>不回任何位元組就關連線</b>，
 * 讓客戶端得到「送出之後連線被重設或提前 EOF」——寫入結果不明的典型情境（TCS-SelfImprovingDecide-P2b AT-950-6-E-2）。迷你 Bridge 是真的 Spring MVC
 * 伺服器，沒辦法在回應之前掛斷，所以這個情境用裸 {@link ServerSocket}。
 */
public final class AbruptCloseServer implements AutoCloseable {

    private final ServerSocket server;
    private final AtomicInteger requests = new AtomicInteger();
    private final Thread acceptor;

    private AbruptCloseServer(ServerSocket server) {
        this.server = server;
        this.acceptor = new Thread(this::acceptLoop, "abrupt-close-server");
        this.acceptor.setDaemon(true);
    }

    public static AbruptCloseServer start() {
        try {
            AbruptCloseServer fake = new AbruptCloseServer(new ServerSocket(0, 50, InetAddress.getByName("127.0.0.1")));
            fake.acceptor.start();
            return fake;
        } catch (IOException e) {
            throw new IllegalStateException("無法啟動掛斷伺服器", e);
        }
    }

    public String url() {
        return "http://127.0.0.1:" + server.getLocalPort();
    }

    /** 已完整收到的請求數。 */
    public int requests() {
        return requests.get();
    }

    private void acceptLoop() {
        while (!server.isClosed()) {
            try (Socket socket = server.accept()) {
                if (consumeRequest(socket.getInputStream())) {
                    requests.incrementAndGet();
                }
                // 離開 try：不回任何位元組就關連線
            } catch (IOException e) {
                if (server.isClosed()) {
                    return;
                }
            }
        }
    }

    /** 讀完標頭與（若有）{@code Content-Length} 長度的本文；回是否讀到完整請求。 */
    private static boolean consumeRequest(InputStream in) throws IOException {
        ByteArrayOutputStream head = new ByteArrayOutputStream();
        int state = 0;                                           // 比對 \r\n\r\n
        while (state < 4) {
            int b = in.read();
            if (b < 0) {
                return false;
            }
            head.write(b);
            boolean expected = (state % 2 == 0) ? b == '\r' : b == '\n';
            state = expected ? state + 1 : (b == '\r' ? 1 : 0);
        }
        int length = 0;
        for (String line : head.toString(StandardCharsets.ISO_8859_1).split("\r\n")) {
            if (line.toLowerCase(Locale.ROOT).startsWith("content-length:")) {
                length = Integer.parseInt(line.substring("content-length:".length()).strip());
            }
        }
        in.readNBytes(length);
        return true;
    }

    @Override
    public void close() {
        try {
            server.close();
        } catch (IOException ignored) {
            // 測試收尾：關不掉也不影響結果
        }
    }
}
