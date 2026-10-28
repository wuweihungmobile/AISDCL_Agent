package com.aisdlc.console.support;

import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * 假 runner（TCS-SysAdminBackup-20261027 §5.2）：在測試裡扮演 sidecar 的控制面，另附控制面檔案的建構器（§5.1 的「其餘檔的建構器」）。
 *
 * <p><b>行為</b>：背景執行緒（20 毫秒輪詢）掃請求目錄；對每個尚無 {@code results/<id>.json} 的請求依「行為」寫 results——{@link Behavior#SUCCEED}、
 * {@link Behavior#FAIL}、{@link Behavior#BUSY}、{@link Behavior#REJECT_INVALID}、{@link Behavior#HOLD}（寫 running 後停住，直到 {@link #release()}）、
 * {@link Behavior#PAUSED}（不處理，工作停在 QUEUED）；並以 {@link MutableClock}（專屬時鐘）的當下時間每輪寫 {@code export/heartbeat}
 * （{@code {schema_rev:1, ts, lock_held}}；可 {@link #pauseHeartbeat()}、{@link #lockHeld(boolean)}）。每個測試後 {@link #stop()}。
 *
 * <p><b>建構器</b>：靜態方法產生 §C1 形狀的檔案內容（值皆為假）；{@link #write} 以「寫 .tmp 後改名」落到輸出目錄，與 sidecar 同一套原子寫法。
 */
public final class FakeBackupRunner {

    /** 假 runner 對請求的處理方式。 */
    public enum Behavior { PAUSED, SUCCEED, FAIL, BUSY, REJECT_INVALID, HOLD }

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Pattern UUID_FILE = Pattern.compile("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.json");

    /** §5.1 的 repos：repo1 posix、repo2 本機 MinIO（local:true）。 */
    public static final String REPOS_BOTH_LOCAL = "[{\"repo\":1,\"type\":\"posix\",\"endpoint_host\":null,\"local\":true},"
            + "{\"repo\":2,\"type\":\"s3\",\"endpoint_host\":\"minio\",\"local\":true}]";
    /** §C1 的 retention 範例。 */
    public static final String RETENTION_DEFAULT = "{\"repo1\":{\"full\":4,\"diff\":7},\"repo2\":{\"full\":4,\"diff\":null},\"logical_days\":28}";

    private final Path exportDir;
    private final Path requestDir;
    private final MutableClock clock;
    private final Set<UUID> held = ConcurrentHashMap.newKeySet();
    private volatile Behavior behavior = Behavior.PAUSED;
    private volatile boolean heartbeatPaused;
    private volatile boolean lockHeld;
    private volatile int failRc = 1;
    private volatile Thread thread;

    public FakeBackupRunner(Path exportDir, Path requestDir, MutableClock clock) {
        this.exportDir = exportDir;
        this.requestDir = requestDir;
        this.clock = clock;
    }

    // ── 行為控制 ──────────────────────────────────────────────────────────────────────────────

    public FakeBackupRunner behavior(Behavior value) {
        this.behavior = value;
        return this;
    }

    public FakeBackupRunner failRc(int rc) {
        this.failRc = rc;
        return this;
    }

    public void pauseHeartbeat() {
        heartbeatPaused = true;
    }

    public void resumeHeartbeat() {
        heartbeatPaused = false;
    }

    public void lockHeld(boolean value) {
        this.lockHeld = value;
    }

    /** 放行所有 HOLD 住的工作：寫終態 succeeded（rc 0）。 */
    public void release() {
        for (UUID id : Set.copyOf(held)) {
            writeResult(id, "succeeded", null, 0, "stub done");
            held.remove(id);
        }
    }

    /** 以目前設定的行為啟動背景執行緒（先停掉舊的；不重設行為旗標）。 */
    public void start() {
        halt();
        Thread worker = new Thread(this::loop, "fake-backup-runner");
        worker.setDaemon(true);
        thread = worker;
        worker.start();
    }

    /** 停止背景執行緒、清空 HOLD 名單並把行為旗標重設為預設（不刪檔；測試的 @BeforeEach 自己清目錄）。 */
    public void stop() {
        halt();
        behavior = Behavior.PAUSED;
        heartbeatPaused = false;
        lockHeld = false;
        failRc = 1;
    }

    private void halt() {
        Thread worker = thread;
        thread = null;
        if (worker != null) {
            worker.interrupt();
            try {
                worker.join(2000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        held.clear();
    }

    private void loop() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                if (!heartbeatPaused) {
                    writeHeartbeat(clock.instant(), lockHeld || !held.isEmpty());
                }
                processRequests();
            } catch (IOException | RuntimeException ignored) {
                // 檔案正被讀取或目錄暫時被換掉（故障注入）：下一輪再試
            }
            try {
                Thread.sleep(20);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    private static String typeOf(Path requestFile) throws IOException {
        Map<?, ?> body = JSON.readValue(Files.readString(requestFile, StandardCharsets.UTF_8), Map.class);
        return String.valueOf(body.get("type"));
    }

    private void processRequests() throws IOException {
        if (behavior == Behavior.PAUSED || !Files.isDirectory(requestDir)) {
            return;
        }
        try (DirectoryStream<Path> files = Files.newDirectoryStream(requestDir, "*.json")) {
            for (Path file : files) {
                if (!UUID_FILE.matcher(file.getFileName().toString()).matches()) {
                    continue;
                }
                UUID id = UUID.fromString(file.getFileName().toString().replace(".json", ""));
                if (Files.exists(exportDir.resolve("results").resolve(id + ".json"))) {
                    continue;
                }
                handle(id, typeOf(file));
            }
        }
    }

    private void handle(UUID id, String type) throws IOException {
        switch (behavior) {
            case SUCCEED -> writeResult(id, type, "succeeded", null, 0, "stub " + type + " done");
            case FAIL -> writeResult(id, type, "failed", "script_failed", failRc, "stub failed");
            case BUSY -> {
                writeResult(id, type, "running", null, null, "");
                writeResult(id, type, "rejected", "busy", null, "");
            }
            case REJECT_INVALID -> writeResult(id, type, "rejected", "rejected_invalid", null, "");
            case HOLD -> {
                writeResult(id, type, "running", null, null, "");
                held.add(id);
            }
            default -> { }
        }
    }

    // ── results ───────────────────────────────────────────────────────────────────────────────

    /** HOLD 住的工作的終態寫入（type 取自請求檔）。 */
    private void writeResult(UUID id, String status, String reason, Integer rc, String tail) {
        try {
            writeResult(id, typeOf(requestDir.resolve(id + ".json")), status, reason, rc, tail);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** 寫一份 results（§C1；started_at＝現在、終態另有 finished_at）。 */
    public void writeResult(UUID id, String type, String status, String reason, Integer rc, String tail) {
        try {
            write("results/" + id + ".json", resultJson(id.toString(), type, status, reason, rc,
                    clock.instant().toString(), "running".equals(status) ? null : clock.instant().toString(), tail));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public static String resultJson(String id, String type, String status, String reason, Integer rc, String startedAt,
                                    String finishedAt, String tail) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schema_rev", 1);
        body.put("id", id);
        body.put("type", type);
        body.put("status", status);
        body.put("reason", reason);
        body.put("rc", rc);
        body.put("started_at", startedAt);
        body.put("finished_at", finishedAt);
        body.put("detail_tail", tail);
        return JSON.writeValueAsString(body);
    }

    // ── 輸出目錄上的檔案 ──────────────────────────────────────────────────────────────────────

    /** 原子寫（同目錄 .tmp → 改名）到輸出目錄的相對路徑；父目錄不存在則建立。 */
    public void write(String relativePath, String content) throws IOException {
        writeTo(exportDir, relativePath, content);
    }

    public static void writeTo(Path root, String relativePath, String content) throws IOException {
        Path target = root.resolve(relativePath);
        Files.createDirectories(target.getParent());
        Path temporary = target.resolveSibling(target.getFileName() + "." + UUID.randomUUID() + ".tmp");
        Files.writeString(temporary, content, StandardCharsets.UTF_8);
        Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE);
    }

    public void writeHeartbeat(Instant ts, boolean lockHeldValue) throws IOException {
        write("export/heartbeat", heartbeat(ts, lockHeldValue));
    }

    /** 清空輸出目錄與請求目錄的內容（保留目錄本身）。 */
    public void clearDirectories() throws IOException {
        for (Path directory : new Path[] {exportDir, requestDir}) {
            if (Files.isRegularFile(directory)) {
                Files.delete(directory);
                Files.createDirectories(directory);
            }
            if (!Files.isDirectory(directory)) {
                Files.createDirectories(directory);
            }
            try (Stream<Path> walk = Files.walk(directory)) {
                for (Path path : walk.sorted(Comparator.reverseOrder()).toList()) {
                    if (!path.equals(directory)) {
                        Files.delete(path);
                    }
                }
            }
        }
    }

    // ── 控制面檔案的建構器（§C1、§5.1；值皆為假）────────────────────────────────────────────

    /** 夾具單一來源檔的內容（相對 backend 專案目錄的 docker/pgbackrest/tests/fixtures）。 */
    public static String fixture(String name) {
        try {
            return Files.readString(Path.of("..", "docker", "pgbackrest", "tests", "fixtures", name), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("讀不到共用夾具 " + name, e);
        }
    }

    /** {@code info.json}（ok:true）：{@code infoArray}、{@code retention}、{@code repos} 為原樣 JSON 文字。 */
    public static String infoJson(String generatedAt, String infoArray, String retention, String repos) {
        return "{\"schema_rev\":1,\"generated_at\":\"" + generatedAt + "\",\"ok\":true,\"info\":" + infoArray + ",\"retention\":"
                + retention + ",\"repos\":" + repos + "}";
    }

    public static String infoFailedJson(String generatedAt) {
        return "{\"schema_rev\":1,\"generated_at\":\"" + generatedAt + "\",\"ok\":false}";
    }

    /** {@code logical.json}（ok:true）；{@code objects} 為原樣 JSON 陣列文字。 */
    public static String logicalJson(String generatedAt, String objects) {
        return "{\"schema_rev\":1,\"generated_at\":\"" + generatedAt + "\",\"ok\":true,\"objects\":" + objects + "}";
    }

    public static String logicalFailedJson(String generatedAt) {
        return "{\"schema_rev\":1,\"generated_at\":\"" + generatedAt + "\",\"ok\":false}";
    }

    /** §5.1 的 {@code schedule6(tz)}：六條 cron。 */
    public static String scheduleJson(String tz) {
        return "{\"schema_rev\":1,\"tz\":\"" + tz + "\",\"entries\":[{\"job\":\"full\",\"cron\":\"0 2 * * 0\"},"
                + "{\"job\":\"diff\",\"cron\":\"0 2 * * 1-6\"},{\"job\":\"dump\",\"cron\":\"30 2 * * *\"},"
                + "{\"job\":\"verify\",\"cron\":\"0 4 * * 3\"},{\"job\":\"expire\",\"cron\":\"0 3 * * *\"},"
                + "{\"job\":\"wal_clean\",\"cron\":\"30 3 * * *\"}]}";
    }

    public static String heartbeat(Instant ts, boolean lockHeld) {
        return "{\"schema_rev\":1,\"ts\":\"" + ts + "\",\"lock_held\":" + lockHeld + "}";
    }

    /** {@code jobs/<job>.json}：{@code last} 與 {@code last_success_at}（字串或 null；時間為 ISO Z）。 */
    public static String jobJson(String job, String trigger, String status, Integer rc, String reason, String startedAt,
                                 String finishedAt, String tail, String lastSuccessAt) {
        Map<String, Object> last = new LinkedHashMap<>();
        last.put("trigger", trigger);
        last.put("status", status);
        last.put("rc", rc);
        last.put("reason", reason);
        last.put("started_at", startedAt);
        last.put("finished_at", finishedAt);
        last.put("detail_tail", tail);
        last.put("note", null);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schema_rev", 1);
        body.put("job", job);
        body.put("last", last);
        body.put("last_success_at", lastSuccessAt);
        return JSON.writeValueAsString(body);
    }

    /** 成功的一份狀態檔（last_success_at＝finishedAt）。 */
    public static String jobOk(String job, String trigger, String startedAt, String finishedAt) {
        return jobJson(job, trigger, "succeeded", 0, null, startedAt, finishedAt, "ok", finishedAt);
    }

    public static String jobRunning(String job, String trigger, String startedAt, String lastSuccessAt) {
        return jobJson(job, trigger, "running", null, null, startedAt, null, "", lastSuccessAt);
    }
}
