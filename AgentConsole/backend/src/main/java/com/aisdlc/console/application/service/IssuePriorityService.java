package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.IssuePriorityUseCase;
import com.aisdlc.console.application.port.out.IssuePriorityRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.issue.IssuePriority;
import com.aisdlc.console.domain.model.issue.IssuePriorityGates;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 議題優先順序的寫入（TCS-IssueCenter-20261027 R-IC-54～R-IC-57、R-IC-60、D-C4）。Console 在議題中心唯一的寫入：不是帳本決定，所以<b>不要求</b>
 * {@code console.si.deciders} 名單；呼叫者的角色（僅 ADMIN）由安全層把關。
 *
 * <p>PUT 的順序（先中者定案，任一前序失敗都零寫入）：輸入閘（{@link IssuePriorityGates}，422，Bridge 零呼叫）→<b>先取該議題</b>
 * （{@link IssueQueryService#fetchOne}：Bridge 失敗沿唯讀端點 503／502／504、查無 404 {@code si_not_found}）→{@code rankable} 為 false 則 409
 * {@code issue_not_rankable}（{@code details.id}、{@code details.status}）→UPSERT。DELETE：輸入閘（只驗 {@code id} 格式）→刪列；<b>不呼叫 Bridge</b>、冪等，
 * 所以議題已結案或已不存在時仍清得掉遺留的列。
 *
 * <p>設定時間取伺服器時鐘（帶 offset）；備註原樣存入（不去空白）；並發 PUT 同一議題由資料庫的單列 UPSERT 保證恰留一列、值完整。
 */
@Service
public class IssuePriorityService implements IssuePriorityUseCase {

    /** 409 {@link ErrorReasons#ISSUE_NOT_RANKABLE} 的中文訊息（與契約表、前端 {@code ISSUE_REASONS} 逐字相同；雙向鎖住）。 */
    public static final String NOT_RANKABLE_MESSAGE = "此議題目前的狀態不能設定優先順序";

    private final IssueQueryService query;
    private final IssuePriorityRepository repository;
    private final Clock clock;

    IssuePriorityService(IssueQueryService query, IssuePriorityRepository repository, Clock clock) {
        this.query = query;
        this.repository = repository;
        this.clock = clock;
    }

    @Override
    public IssuePriority set(String user, String id, Map<String, Object> body) {
        IssuePriorityGates.Command command = IssuePriorityGates.set(id, body);
        Map<String, Object> issue = firstItem(id);
        if (!Boolean.TRUE.equals(issue.get("rankable"))) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("id", id);
            if (issue.get("status") instanceof String status) {
                details.put("status", status);
            }
            throw new ConflictException(NOT_RANKABLE_MESSAGE, ErrorReasons.ISSUE_NOT_RANKABLE, details);
        }
        IssuePriority row = new IssuePriority(id, command.rank(), command.note(), user, OffsetDateTime.now(clock));
        repository.upsert(row);
        return row;
    }

    @Override
    public void clear(String id) {
        IssuePriorityGates.checkId(id);
        repository.delete(id);
    }

    /** 單筆議題（Bridge 的 {@code items} 恰一筆；空＝查無，同 Bridge 的 404 {@code si_not_found}、訊息「查無此議題」）。 */
    @SuppressWarnings("unchecked")
    private Map<String, Object> firstItem(String id) {
        Object items = query.fetchOne(id).raw().get("items");
        if (items instanceof List<?> list && !list.isEmpty() && list.get(0) instanceof Map<?, ?> first) {
            return (Map<String, Object>) first;
        }
        throw new NotFoundException("查無此議題", ErrorReasons.SI_NOT_FOUND, Map.of("id", id));
    }
}
