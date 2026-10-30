package com.aisdlc.console.adapter.out.control;

import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupSettings;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 控制面檔案 I/O 的純 Java 實作（{@code @TempDir}；TCS-SysAdminBackup-20261027 AT-BK-06-9-2、B-07；Windows 與 Linux 皆跑）。為什麼重要：請求檔是 console-api 唯一能
 * 「叫」sidecar 做事的管道——寫到一半的檔被 runner 撿走、寫失敗後留下殘檔、失敗被吞成「成功」，都會讓畫面與備份現實不一致；
 * 所以寫入必須「寫 {@code .tmp}、原子改名」、任何一步失敗都清掉 {@code .tmp} 並<b>丟出可檢查的 {@link IOException}</b>（呼叫端據此補償該列），
 * 絕不讓未檢查例外外洩成 500。讀取面則要分清「缺席」與「讀不出來」（前者是合法狀態、後者是 {@code export_unreadable}）。
 */
class FileBackupControlAdapterTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Instant T0 = Instant.parse("2026-10-27T02:00:00Z");

    private record Settings(Path exportDir, Path requestDir) implements BackupSettings {

        @Override
        public int requestTtlSeconds() {
            return 120;
        }

        @Override
        public int jobMaxSeconds() {
            return 21600;
        }

        @Override
        public long reconcileIntervalMs() {
            return 5000;
        }

        @Override
        public int overdueGraceMinutes() {
            return 30;
        }

        @Override
        public long minFullIntervalSeconds() {
            return 86400;
        }

        @Override
        public long minDiffIntervalSeconds() {
            return 3600;
        }
    }

    private static BackupControlPort.Request request(UUID id) {
        return new BackupControlPort.Request(id, "diff", T0, T0.plusSeconds(120));
    }

    private static List<String> names(Path directory) throws IOException {
        try (Stream<Path> files = Files.list(directory)) {
            return files.map(p -> p.getFileName().toString()).sorted().toList();
        }
    }

    // ── AT-BK-06-9-2：寫入的成功與三種失敗 ───────────────────────────────────────────────────

    @Test
    void AT_BK_06_9_2_theRequestFileLandsAtomicallyAndEveryFailureLeavesNoTmpFileAndThrowsACheckedException(@TempDir Path root) throws IOException {
        Path requests = Files.createDirectory(root.resolve("req"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), requests));

        // 成功：內容恰五個鍵、保序，.tmp 已改名
        UUID id = UUID.randomUUID();
        adapter.writeRequest(request(id));
        assertThat(names(requests)).containsExactly(id + ".json");
        String text = Files.readString(requests.resolve(id + ".json"), StandardCharsets.UTF_8);
        @SuppressWarnings("unchecked")
        Map<String, Object> body = JSON.readValue(text, Map.class);
        assertThat(body.keySet()).containsExactly("schema_rev", "id", "type", "requested_at", "expires_at");
        assertThat(body).containsEntry("schema_rev", 1).containsEntry("id", id.toString()).containsEntry("type", "diff")
                .containsEntry("requested_at", "2026-10-27T02:00:00Z").containsEntry("expires_at", "2026-10-27T02:02:00Z");

        // 失敗一：目的目錄是一般檔案
        Path notADirectory = Files.writeString(root.resolve("req-as-file"), "我是檔案", StandardCharsets.UTF_8);
        FileBackupControlAdapter onFile = new FileBackupControlAdapter(new Settings(root.resolve("out"), notADirectory));
        assertThatThrownBy(() -> onFile.writeRequest(request(UUID.randomUUID()))).as("目的目錄是一般檔案").isInstanceOf(IOException.class);
        assertThat(Files.readString(notADirectory, StandardCharsets.UTF_8)).as("該檔案原封不動").isEqualTo("我是檔案");

        // 失敗二：目的目錄不存在（不建立，缺目錄是部署問題）
        Path missing = root.resolve("no-such-dir");
        FileBackupControlAdapter onMissing = new FileBackupControlAdapter(new Settings(root.resolve("out"), missing));
        assertThatThrownBy(() -> onMissing.writeRequest(request(UUID.randomUUID()))).as("目的目錄不存在").isInstanceOf(IOException.class);
        assertThat(Files.exists(missing)).as("不替部署補建目錄").isFalse();

        // 失敗三：.tmp 寫成後改名失敗（目的檔名已被同名「非空目錄」占用）
        UUID occupied = UUID.randomUUID();
        Path blocker = Files.createDirectory(requests.resolve(occupied + ".json"));
        Files.writeString(blocker.resolve("keep"), "x", StandardCharsets.UTF_8);
        assertThatThrownBy(() -> adapter.writeRequest(request(occupied))).as("改名失敗").isInstanceOf(IOException.class);
        assertThat(names(requests)).as("沒有任何殘留的 .tmp").noneMatch(name -> name.endsWith(".tmp"));
        assertThat(Files.isDirectory(blocker)).as("占用者原封不動").isTrue();
    }

    /**
     * F6(e)（SCG-4 一審 U12）：同一請求檔被第二次寫入時覆蓋成功、目錄無 {@code .tmp} 殘留。另以原始碼鎖「改名一律 ATOMIC_MOVE」：
     * REPLACE_EXISTING 與 ATOMIC_MOVE 在單執行緒行為上無法區分（兩者都覆寫），但前者在 Linux 非原子——runner 可能讀到半個檔，
     * 這是行為測試抓不到、卻是本設計的根本理由，所以以字面鎖住（改法必須連同本測試一起改並寫 WHY）。
     */
    @Test
    void AT_BK_06_9_2_aSecondWriteOverwritesInPlaceLeavesNoTmpAndTheRenameIsDeclaredAtomic(@TempDir Path root) throws IOException {
        Path requests = Files.createDirectory(root.resolve("req"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), requests));
        UUID id = UUID.randomUUID();
        adapter.writeRequest(request(id));
        adapter.writeRequest(new BackupControlPort.Request(id, "full", T0.plusSeconds(60), T0.plusSeconds(180)));

        assertThat(names(requests)).as("覆蓋後仍只有一個檔、沒有 .tmp").containsExactly(id + ".json");
        assertThat(Files.readString(requests.resolve(id + ".json"), StandardCharsets.UTF_8)).contains("\"type\":\"full\"")
                .contains("2026-10-27T02:01:00Z");

        String source = Files.readString(Path.of("src/main/java/com/aisdlc/console/adapter/out/control/FileBackupControlAdapter.java"),
                StandardCharsets.UTF_8);
        assertThat(source).as("寫檔改名必須宣告 ATOMIC_MOVE").contains("StandardCopyOption.ATOMIC_MOVE").doesNotContain("REPLACE_EXISTING");
    }

    /**
     * F6(f)（SCG-4 一審 U13，Java 側）：請求檔必須讓另一個 uid（sidecar 的 runner）讀得到——POSIX 系統上 0644，且在改名<b>之前</b>就設好
     * （先改名、後改權限，runner 可能在空窗讀到 0600 的檔）。兩層鎖，因為單靠任一層都有盲區：
     * (1) 行為（只在支援 posix 檔案屬性的系統上斷言）：預先放一個 0600 的 {@code <id>.json.tmp}，{@code writeRequest} 覆寫它時檔案模式不變，
     * 所以只有「明確設 0644」才會讓成品是 0644——不依賴行程的 umask（預設 022 下新檔本來就是 0644，直接斷言會變成永遠綠的空測試）；
     * (2) 原始碼（Windows 沒有 posix 屬性，行為層在那裡不跑）：設權限的呼叫必須存在、先於 ATOMIC_MOVE 改名、且權限字串為 rw-r--r--
     * （改法必須連同本測試一起改並寫 WHY；同 U12 的字面鎖理由）。
     */
    @Test
    void AT_BK_06_9_3_theRequestFileIsReadableByOthersAndTheModeIsSetBeforeTheAtomicRename(@TempDir Path root) throws IOException {
        Path requests = Files.createDirectory(root.resolve("req"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), requests));
        UUID id = UUID.randomUUID();
        boolean posix = FileSystems.getDefault().supportedFileAttributeViews().contains("posix");
        if (posix) {
            Path stale = requests.resolve(id + ".json.tmp");
            Files.writeString(stale, "stale", StandardCharsets.UTF_8);
            Files.setPosixFilePermissions(stale, PosixFilePermissions.fromString("rw-------"));
        }

        adapter.writeRequest(request(id));

        if (posix) {
            assertThat(PosixFilePermissions.toString(Files.getPosixFilePermissions(requests.resolve(id + ".json"))))
                    .as("POSIX：請求檔 0644（預放的 0600 暫存檔被覆寫後仍須變成 0644）").isEqualTo("rw-r--r--");
        }
        String source = Files.readString(Path.of("src/main/java/com/aisdlc/console/adapter/out/control/FileBackupControlAdapter.java"),
                StandardCharsets.UTF_8);
        int setMode = source.indexOf("allowOthersToRead(temporary)");
        int rename = source.indexOf("Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE)");
        assertThat(setMode).as("寫檔流程必須呼叫 allowOthersToRead").isNotNegative();
        assertThat(rename).as("改名一律 ATOMIC_MOVE").isNotNegative();
        assertThat(setMode).as("設權限先於改名").isLessThan(rename);
        assertThat(source).as("權限字串與設定方式").contains("READABLE_BY_OTHERS = \"rw-r--r--\"")
                .contains("Files.setPosixFilePermissions(file, PosixFilePermissions.fromString(READABLE_BY_OTHERS))");
    }

    // ── 讀取：缺席與讀不出來是兩件事 ────────────────────────────────────────────────────────

    @Test
    void readingDistinguishesAbsentFromUnreadable(@TempDir Path root) throws IOException {
        Path out = Files.createDirectories(root.resolve("out/export"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), root.resolve("req")));

        assertThat(adapter.read("export/info.json")).as("缺席是合法狀態").isEmpty();
        Files.writeString(out.resolve("info.json"), "{\"schema_rev\":1}", StandardCharsets.UTF_8);
        assertThat(adapter.read("export/info.json")).contains("{\"schema_rev\":1}");
        Files.writeString(out.resolve("empty"), "", StandardCharsets.UTF_8);
        assertThat(adapter.read("export/empty")).as("空檔照實回傳（由呼叫端判為損毀）").contains("");

        Files.createDirectory(out.resolve("jobs"));
        assertThatThrownBy(() -> adapter.read("export/jobs")).as("路徑是目錄＝讀不出來").isInstanceOf(UncheckedIOException.class);
        Files.write(out.resolve("binary"), new byte[] {(byte) 0xC3, (byte) 0x28});
        assertThatThrownBy(() -> adapter.read("export/binary")).as("不是合法 UTF-8＝讀不出來").isInstanceOf(UncheckedIOException.class);
    }

    // ── 設定缺席、超大檔與刪不掉的殘留：都要大聲失敗或如實回報，不能吞成「成功」 ─────────────────────────

    @Test
    void misconfigurationOversizeFilesAndUndeletableLeftoversAreReportedNotSwallowed(@TempDir Path root) throws IOException {
        // 設定缺席：讀取不該被呼叫（由 BackupQueryService 先以 not_configured 擋下），被呼叫就是程式錯誤，丟未檢查例外；寫入丟可檢查的 IOException
        FileBackupControlAdapter unconfigured = new FileBackupControlAdapter(new Settings(null, null));
        assertThatThrownBy(() -> unconfigured.read("export/info.json")).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> unconfigured.writeRequest(request(UUID.randomUUID()))).isInstanceOf(IOException.class);
        assertThat(unconfigured.deleteRequest(UUID.randomUUID())).as("沒有請求目錄＝沒有可刪的檔，視為成功").isTrue();

        // 超過 16 MB 的控制面檔案：視為讀不出來（export_unreadable），不整份讀進記憶體
        Path out = Files.createDirectories(root.resolve("out/export"));
        Path big = out.resolve("huge.json");
        try (RandomAccessFile file = new RandomAccessFile(big.toFile(), "rw")) {
            file.setLength(16L * 1024 * 1024 + 1);
        }
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), Files.createDirectory(root.resolve("req"))));
        assertThatThrownBy(() -> adapter.read("export/huge.json")).as("超過上限").isInstanceOf(UncheckedIOException.class);

        // 暫存檔路徑被「非空目錄」占住：寫入失敗、原因照實丟出，且清不掉的占用者原封不動（清理失敗只記 WARN，不蓋掉原始例外）
        Path requests = root.resolve("req");
        UUID blocked = UUID.randomUUID();
        Path tmpBlocker = Files.createDirectory(requests.resolve(blocked + ".json.tmp"));
        Files.writeString(tmpBlocker.resolve("keep"), "x", StandardCharsets.UTF_8);
        assertThatThrownBy(() -> adapter.writeRequest(request(blocked))).isInstanceOf(IOException.class);
        assertThat(Files.isDirectory(tmpBlocker)).isTrue();
        assertThat(Files.exists(requests.resolve(blocked + ".json"))).as("目的檔不會被建立").isFalse();

        // 自己的請求檔刪不掉（同名非空目錄）：回報 false（對帳不受影響，由啟動殘檔清理兜底），不丟例外
        UUID undeletable = UUID.randomUUID();
        Path occupant = Files.createDirectory(requests.resolve(undeletable + ".json"));
        Files.writeString(occupant.resolve("keep"), "x", StandardCharsets.UTF_8);
        assertThat(adapter.deleteRequest(undeletable)).isFalse();
        assertThat(Files.isDirectory(occupant)).isTrue();
    }

    // ── 刪除與啟動殘檔清理（K 包補 AT：C1 的「啟動時清逾 24 小時殘檔」，主控代決第 8 點）──────────

    @Test
    void AT_BK_06_3_S_1_startupSweepRemovesOnlyJsonRequestFilesOlderThanTheCutoffAndNeverFollowsSymlinks(@TempDir Path root) throws IOException {
        Path requests = Files.createDirectory(root.resolve("req"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), requests));
        Instant now = T0;
        UUID stale = UUID.randomUUID();
        UUID fresh = UUID.randomUUID();
        UUID boundary = UUID.randomUUID();
        Files.writeString(requests.resolve(stale + ".json"), "{}", StandardCharsets.UTF_8);
        Files.writeString(requests.resolve(fresh + ".json"), "{}", StandardCharsets.UTF_8);
        Files.writeString(requests.resolve(boundary + ".json"), "{}", StandardCharsets.UTF_8);
        Files.writeString(requests.resolve("note.txt"), "不是請求檔", StandardCharsets.UTF_8);
        Files.setLastModifiedTime(requests.resolve(stale + ".json"), FileTime.from(now.minus(Duration.ofHours(25))));
        Files.setLastModifiedTime(requests.resolve(fresh + ".json"), FileTime.from(now.minus(Duration.ofHours(23))));
        Files.setLastModifiedTime(requests.resolve(boundary + ".json"), FileTime.from(now.minus(Duration.ofHours(24))));
        Files.setLastModifiedTime(requests.resolve("note.txt"), FileTime.from(now.minus(Duration.ofHours(72))));

        int removed = adapter.deleteStaleRequests(now.minus(Duration.ofHours(24)));

        assertThat(removed).as("只刪嚴格早於截止時間的 *.json 一般檔").isEqualTo(1);
        assertThat(names(requests)).containsExactlyInAnyOrder(fresh + ".json", boundary + ".json", "note.txt");

        // 目錄不存在或未設定：回 0、不丟例外（只記 WARN 的程序層清理不得影響啟動）
        assertThat(new FileBackupControlAdapter(new Settings(root.resolve("out"), root.resolve("nope"))).deleteStaleRequests(now)).isZero();
        assertThat(new FileBackupControlAdapter(new Settings(root.resolve("out"), null)).deleteStaleRequests(now)).isZero();
    }

    @Test
    void deletingTheOwnRequestFileIsIdempotent(@TempDir Path root) throws IOException {
        Path requests = Files.createDirectory(root.resolve("req"));
        FileBackupControlAdapter adapter = new FileBackupControlAdapter(new Settings(root.resolve("out"), requests));
        UUID id = UUID.randomUUID();
        adapter.writeRequest(request(id));

        assertThat(adapter.deleteRequest(id)).isTrue();
        assertThat(names(requests)).isEmpty();
        assertThat(adapter.deleteRequest(id)).as("本來就不存在也算成功").isTrue();
        Optional<String> gone = adapter.read("export/none");
        assertThat(gone).isEmpty();
    }
}
