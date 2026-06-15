# C4 Container — OrderSystem

```mermaid
flowchart LR
  Component(OrderService, "Order Service", "FastAPI", "處理訂單建立/查詢/取消")
  Component(PaymentGateway, "Payment Gateway", "External", "Stripe 介接")
  OrderService --> PaymentGateway
```
