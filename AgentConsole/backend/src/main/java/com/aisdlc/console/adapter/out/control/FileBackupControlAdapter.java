package com.aisdlc.console.adapter.out.control;

import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupSettings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 控制面檔案 I/O（TCS-SysAdminBackup-20261027 §C1；純 Java 檔案 I/O，<b>Windows 與 Linux 皆可跑</b>）。console-api 對 sidecar 只有這一種介面：
 * 讀輸出卷（唯讀掛載）、寫請求卷；沒有行程啟動、沒有網路呼叫。
 *
 * <p>請求檔的寫入是「寫同目錄的 {@code <id>.json.tmp}、{@code ATOMIC_MOVE} 改名」：sidecar 的 runner 永遠看不到寫到一半的檔；任何一步失敗都先刪
 * {@code .tmp}（不留殘檔）再丟 {@link IOException}（呼叫端以條件式 UPDATE 補償該列）。目錄不存在或不是目錄時<b>不建立</b>（卷由映像與 compose 定義，
 * 缺目錄是部署問題，應該看得見）。Windows 行為＝與 Linux 相同（POSIX 權限位只在支援 posix 檔案屬性的系統上設，且失敗不致命）。
 */
@Component
class FileBackupControlAdapter implements BackupControlPort {

    private static final Logger LOG = LoggerFactory.getLogger(FileBackupControlAdapter.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    /** 單檔讀取上限（info.json 內含 pgBackRest 的完整備份清單，數百份備份也遠低於此）；超過視為不可讀。 */
    private static final long MAX_BYTES = 16L * 1024 * 1024;
    private static final String READABLE_BY_OTHERS = "rw-r--r--";

    private final BackupSettings settings;

    FileBackupControlAdapter(BackupSettings settings) {
        this.settings = settings;
    }

    @Override
    public Optional<String> read(String relativePath) {
        Path root = settings.exportDir();
        if (root == null) {
            throw new IllegalStateException("console.backup.export-dir 未設定，不該呼叫讀取");
        }
        Path file = root.resolve(relativePath);
        try {
            if (Files.size(file) > MAX_BYTES) {
                throw new IOException("控制面檔案超過 " + MAX_BYTES + " 位元組上限：" + relativePath);
            }
            return Optional.of(Files.readString(file, StandardCharsets.UTF_8));
        } catch (NoSuchFileException e) {
            return Optional.empty();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Override
    public void writeRequest(Request request) throws IOException {
        Path directory = settings.requestDir();
        if (directory == null) {
            throw new IOException("console.backup.request-dir 未設定");
        }
        Path temporary = directory.resolve(request.id() + ".json.tmp");
        Path target = directory.resolve(request.id() + ".json");
        try {
            Files.writeString(temporary, content(request), StandardCharsets.UTF_8);
            allowOthersToRead(temporary);
            Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException | RuntimeException e) {
            removeQuietly(temporary);
            throw e instanceof IOException io ? io : new IOException("請求檔寫入失敗：" + e, e);
        }
    }

    /** 請求檔內容：恰五個鍵、保序、時間為 UTC 帶 Z 的 ISO-8601（秒精度）。 */
    private static String content(Request request) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schema_rev", 1);
        body.put("id", request.id().toString());
        body.put("type", request.type());
        body.put("requested_at", request.requestedAt().truncatedTo(ChronoUnit.SECONDS).toString());
        body.put("expires_at", request.expiresAt().truncatedTo(ChronoUnit.SECONDS).toString());
        return JSON.writeValueAsString(body) + "\n";
    }

    /** 檔 0644（讀取端 sidecar 是另一個 uid）；非 POSIX 檔案系統略過。 */
    private static void allowOthersToRead(Path file) throws IOException {
        if (FileSystems.getDefault().supportedFileAttributeViews().contains("posix")) {
            Files.setPosixFilePermissions(file, PosixFilePermissions.fromString(READABLE_BY_OTHERS));
        }
    }

    private static void removeQuietly(Path file) {
        try {
            Files.deleteIfExists(file);
        } catch (IOException e) {
            LOG.warn("殘留的暫存檔刪除失敗：{}", e.toString());
        }
    }

    @Override
    public boolean deleteRequest(UUID id) {
        Path directory = settings.requestDir();
        if (directory == null) {
            return true;
        }
        try {
            Files.deleteIfExists(directory.resolve(id + ".json"));
            return true;
        } catch (IOException e) {
            LOG.warn("請求檔刪除失敗（不影響對帳）：{}.json：{}", id, e.toString());
            return false;
        }
    }

    @Override
    public int deleteStaleRequests(Instant olderThan) {
        Path directory = settings.requestDir();
        if (directory == null || !Files.isDirectory(directory)) {
            return 0;
        }
        int removed = 0;
        try (DirectoryStream<Path> files = Files.newDirectoryStream(directory, "*.json")) {
            for (Path file : files) {
                try {
                    boolean regular = Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS);
                    if (regular && Files.getLastModifiedTime(file, LinkOption.NOFOLLOW_LINKS).toInstant().isBefore(olderThan)) {
                        Files.delete(file);
                        removed++;
                    }
                } catch (IOException e) {
                    LOG.warn("殘留請求檔刪除失敗：{}", e.toString());
                }
            }
        } catch (IOException e) {
            LOG.warn("請求卷目錄無法列舉，略過殘檔清理：{}", e.toString());
        }
        return removed;
    }
}
