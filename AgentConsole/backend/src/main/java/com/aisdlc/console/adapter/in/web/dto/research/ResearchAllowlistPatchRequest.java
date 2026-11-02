package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 停用／啟用 allowlist 條目的請求本文（契約 API-RP-22；僅 ADMIN）：<b>只准 {@code enabled} 一鍵</b>。這個型別只用來文件化（OpenAPI）：端點實際以
 * {@code Map} 接本文，好讓「多帶任何其他鍵（含 {@code minIntervalSeconds}）→ 422 {@code invalid_request}、條目不變」可判——{@code minIntervalSeconds}
 * 建立時決定、建立後不可改（要調整＝停用該條目後重建）。停用人一律取 JWT subject。
 */
@Schema(name = "ResearchAllowlistPatch", description = "停用／啟用條目：只准 enabled；本文含其他鍵一律 422 invalid_request（條目不變）")
public record ResearchAllowlistPatchRequest(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) Boolean enabled) {
}
