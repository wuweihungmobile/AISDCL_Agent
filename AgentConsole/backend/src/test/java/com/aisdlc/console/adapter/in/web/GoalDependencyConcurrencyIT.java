package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 並發下的防環不變式：兩個請求各自「單獨看」都不成環（A→B 與 B→A），合起來才成環。
 * 專案列的 SELECT … FOR UPDATE 把它們序列化，因此每一輪必然恰好一個成功、一個 400（依賴成環），
 * 最終圖永遠無環。若有人拿掉鎖，這個測試會（機率性地）出現「兩個都成功」而紅燈。
 */
class GoalDependencyConcurrencyIT extends AbstractApiIT {

    private static final int ROUNDS = 12;

    @Test
    void concurrentOppositeDependenciesNeverBothSucceed() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < ROUNDS; round++) {
                String project = createProject("Race " + round);
                String a = createGoal(project, "A");
                String b = createGoal(project, "B");
                CyclicBarrier startTogether = new CyclicBarrier(2);

                Callable<Resp> aDependsOnB = () -> {
                    startTogether.await(10, TimeUnit.SECONDS);
                    return api.put(operator(), "/api/v1/goals/" + a, Map.of("dependsOn", List.of(b)));
                };
                Callable<Resp> bDependsOnA = () -> {
                    startTogether.await(10, TimeUnit.SECONDS);
                    return api.put(operator(), "/api/v1/goals/" + b, Map.of("dependsOn", List.of(a)));
                };
                List<Future<Resp>> futures = new ArrayList<>(List.of(pool.submit(aDependsOnB), pool.submit(bDependsOnA)));
                List<Integer> statuses = new ArrayList<>();
                for (Future<Resp> future : futures) {
                    Resp resp = future.get(30, TimeUnit.SECONDS);
                    statuses.add(resp.status());
                    if (resp.status() == 400) {
                        assertThat(resp.<String>read("$.reason")).isEqualTo("依賴成環");
                    }
                }
                assertThat(statuses).as("第 %d 輪：恰好一個成功、一個成環被拒", round).containsExactlyInAnyOrder(200, 400);

                List<String> depsOfA = api.get(viewer(), "/api/v1/goals/" + a).read("$.data.dependsOn");
                List<String> depsOfB = api.get(viewer(), "/api/v1/goals/" + b).read("$.data.dependsOn");
                assertThat(depsOfA.size() + depsOfB.size()).as("最終只存在一條邊，圖無環").isEqualTo(1);
            }
        } finally {
            pool.shutdownNow();
        }
    }
}
