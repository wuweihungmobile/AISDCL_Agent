package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.EventPage;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/** {@code GET …/events} 的一頁（契約 API-RP-05）：{@code truncated} 為真時以 {@code nextSeq} 續抓（單頁上限 500）。 */
@Schema(name = "ResearchEventPage", description = "事件帳一頁：items 依 seq 遞增；nextSeq＝最後一筆的 seq（沒有事件時為請求的 afterSeq）；truncated＝後面還有")
public record ResearchEventPage(
        @NotNull List<ResearchEvent> items,
        @NotNull @Schema(format = "int64") long nextSeq,
        @NotNull boolean truncated) {

    public static ResearchEventPage from(EventPage page) {
        return new ResearchEventPage(page.items().stream().map(ResearchEvent::from).toList(), page.nextSeq(), page.truncated());
    }
}
