package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.port.in.SettingsUseCase.ExportedItem;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.PayloadTooLargeException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UnsupportedFormatException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 設定匯入檔的檔案層檢查（契約 §1.5.10）：大小 ≤ 1MB（否則 413）、副檔名 {@code .json} 且內容型別不是明顯的非 JSON
 * （否則 415）、內容是 {@code version=1} 的物件且 {@code configs} 為陣列（否則 400 {@code 設定檔格式錯誤}，
 * {@code details.problem} ∈ {@code invalid_json|missing_configs|unsupported_version}）。
 * 逐筆驗證與套用由用例負責。
 */
final class SettingsFileReader {

    static final int MAX_BYTES = 1_048_576;
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private SettingsFileReader() {
    }

    static List<ExportedItem> read(MultipartFile file) {
        String name = file.getOriginalFilename() == null ? "" : file.getOriginalFilename().toLowerCase(Locale.ROOT);
        String contentType = file.getContentType() == null ? "" : file.getContentType().toLowerCase(Locale.ROOT);
        boolean jsonish = contentType.isEmpty() || contentType.contains("json")
                || contentType.startsWith("application/octet-stream");
        if (!name.endsWith(".json") || !jsonish) {
            throw new UnsupportedFormatException("只接受 JSON 設定檔（.json）", ErrorReasons.SETTINGS_FILE_TYPE,
                    Map.of());
        }
        byte[] content;
        try {
            content = file.getBytes();
        } catch (IOException e) {
            throw new UnprocessableException("檔案已損毀，無法讀取", ErrorReasons.FILE_CORRUPT, Map.of());
        }
        if (content.length > MAX_BYTES) {
            throw new PayloadTooLargeException("設定檔超過 1MB 上限", ErrorReasons.SETTINGS_FILE_TOO_LARGE,
                    Map.of("limitBytes", MAX_BYTES));
        }
        Map<String, Object> document;
        try {
            document = JSON.readValue(content, OBJECT);
        } catch (JacksonException e) {
            throw formatError("invalid_json", "設定檔不是合法的 JSON 物件");
        }
        Object version = document.get("version");
        if (!(version instanceof Number number) || number.intValue() != 1 || number.doubleValue() != 1.0) {
            throw formatError("unsupported_version", "設定檔的 version 必須是 1");
        }
        if (!(document.get("configs") instanceof List<?> configs)) {
            throw formatError("missing_configs", "設定檔缺少 configs 陣列");
        }
        List<ExportedItem> items = new ArrayList<>();
        for (Object entry : configs) {
            if (!(entry instanceof Map<?, ?> map) || !(map.get("category") instanceof String category)
                    || !(map.get("key") instanceof String key) || map.get("value") == null
                    || map.get("value") instanceof Map<?, ?> || map.get("value") instanceof List<?>) {
                throw formatError("missing_configs", "configs 的每一項都必須是 {category, key, value}");
            }
            items.add(new ExportedItem(category, key, String.valueOf(map.get("value"))));
        }
        return items;
    }

    private static ValidationException formatError(String problem, String message) {
        return new ValidationException(message, ErrorReasons.SETTINGS_FILE_FORMAT,
                List.of(new Violation("file", message)), Map.of("problem", problem));
    }
}
