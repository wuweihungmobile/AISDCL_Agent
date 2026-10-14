package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.constraints.NotBlank;

public record RefreshRequest(
        @NotBlank(message = "refreshToken 不能為空") String refreshToken) {
}
