# Monitoring Support Templates

**狀態**: 🚧 待補充（預留目錄）

## 目錄用途

此目錄用於存放**監控與可觀測性**相關的文檔模板。

這些模板協助團隊設計和實作系統監控、日誌、追蹤等可觀測性機制。

## 預計包含的模板

- [ ] Monitoring_Strategy_Template.md - 監控策略文檔模板
- [ ] Dashboard_Design_Template.md - 儀表板設計模板
- [ ] Alert_Configuration_Template.md - 告警配置文檔模板
- [ ] Logging_Strategy_Template.md - 日誌策略文檔模板
- [ ] Tracing_Design_Template.md - 分散式追蹤設計模板
- [ ] SLI_SLO_SLA_Definition_Template.md - SLI/SLO/SLA 定義模板
- [ ] Health_Check_Specification_Template.md - 健康檢查規格模板

## 開發計劃

- **預計版本**: v0.01+
- **優先級**: P2 (Medium)
- **依賴**: Observability_Design_Guide.md 完善後再建立具體模板

## 可觀測性三大支柱

1. **Metrics (指標)**:
   - 系統效能指標 (CPU, Memory, Disk)
   - 應用程式指標 (Request Rate, Error Rate, Duration)
   - 業務指標 (DAU, Conversion Rate)

2. **Logs (日誌)**:
   - 結構化日誌格式
   - 日誌等級策略
   - 日誌保留政策

3. **Traces (追蹤)**:
   - 分散式追蹤設計
   - Span 設計原則
   - 追蹤取樣策略

## 相關資源

- **監控設計指南**: [guides/system/architecture/Observability_Design_Guide.md](../../../guides/system/architecture/Observability_Design_Guide.md)
- **DevOps 情境**: [scenarios/devops/](../../../scenarios/devops/)
- **效能測試模板**: [docs_template/core/tests/Performance_Test_Plan_Template.md](../../core/tests/Performance_Test_Plan_Template.md)

## 常用監控工具

- **Metrics**: Prometheus, Grafana, DataDog, New Relic
- **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana), Splunk
- **Traces**: Jaeger, Zipkin, AWS X-Ray, Google Cloud Trace
- **APM**: DataDog APM, New Relic APM, Dynatrace

---

**最後更新**: 2025-12-01
**版本**: v0.01
