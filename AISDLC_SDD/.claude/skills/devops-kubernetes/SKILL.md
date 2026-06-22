---
name: devops-kubernetes
description: Kubernetes 部署配置，規格對應 SRD 部署架構，資源限制對應 NFR 量化，SCG-2 後執行
user-invocable: true
disable-model-invocation: false
argument-hint: "<app_type: web|api|worker|cronjob> [environment: dev|staging|production]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# DevOps Kubernetes Skill（SDD 原生）

K8s 部署配置是 SDD 部署架構規格的實作。本 Skill 在 SCG-2 架構凍結後執行，所有資源配置（CPU/Memory 限制、副本數、HPA 閾值）必須對應 SRD 的 NFR 章節，部署策略需有 ADR 支撐。

---

## 觸發方式

```bash
/devops-kubernetes api production
/devops-kubernetes web staging
/devops-kubernetes worker production
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-2 通過 | 架構凍結，K8s 部署策略確定 | `docs/02_architecture/SRD-{System}.md` 第 8 章 |
| NFR 量化 | CPU/Memory/可用性需求已定義 | `docs/01_requirements/FRD-{System}.md` NFR 章節 |
| Docker Image 就緒 | `/devops-docker` 已執行 | `Dockerfile` 存在 |

---

## 執行流程

### 階段 1：讀取 SRD 部署架構與 NFR

讀取 `docs/02_architecture/SRD-{System}.md`，確認：
- K8s 部署策略（Rolling Update / Blue-Green / Canary）
- 服務拓撲（Ingress → Service → Deployment）
- 環境差異（Dev/Staging/Production 差異）

讀取 NFR，確認量化值：
- `NFR-XXX`：可用性 SLA（影響副本數 / PDB 設定）
- `NFR-XXX`：回應時間（影響 HPA CPU 目標值）
- `NFR-XXX`：容量規劃（影響資源 requests/limits）

---

### 階段 2：K8s ADR 補充（若策略未記錄）

若 SRD 未記錄 K8s 部署策略，呼叫 `/adr-generate "K8s 部署策略"`：

```markdown
# ADR-{NNN}: Kubernetes 部署策略

## Decision
使用 Rolling Update + HPA + PDB 策略

## Rationale
- Rolling Update：零停機部署（NFR-XXX 可用性要求）
- HPA：依 CPU 自動擴縮（容量規劃 NFR-XXX）
- PDB：確保升級過程中最少 N 個 Pod 可用
```

---

### 階段 3：核心資源配置產出

**Deployment（資源值對應 NFR）**：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  labels:
    app: {app_name}
    sdd-version: "{SRD 版本}"  # 追溯 SRD 版本
spec:
  replicas: {副本數（對應 NFR 可用性 SLA）}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0          # 零停機（NFR-XXX）
  selector:
    matchLabels:
      app: {app_name}
  template:
    spec:
      containers:
        - name: {app_name}
          image: {registry}/{app_name}:{tag}
          ports:
            - containerPort: {port}
          resources:
            requests:
              cpu: "{CPU requests（對應 NFR 基準）}"
              memory: "{Memory requests}"
            limits:
              cpu: "{CPU limits（對應 NFR 峰值）}"
              memory: "{Memory limits}"
          # 健康檢查端點（對應 Contract 定義的 /health）
          livenessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 5
          envFrom:
            - configMapRef:
                name: {app_name}-config
            - secretRef:
                name: {app_name}-secrets
```

**HPA（閾值對應 NFR 效能目標）**：

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {app_name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {app_name}
  minReplicas: {最小副本（NFR 可用性）}
  maxReplicas: {最大副本（容量規劃 NFR-XXX）}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {CPU 目標（對應 NFR 效能閾值）}
```

**PDB（確保可用性 SLA）**：

```yaml
# k8s/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {app_name}
spec:
  minAvailable: {最少可用數（NFR 可用性 SLA）}
  selector:
    matchLabels:
      app: {app_name}
```

---

### 階段 4：環境差異矩陣（對應 SRD 環境差異說明）

| 配置 | Dev | Staging | Production |
|------|-----|---------|------------|
| Replicas | 1 | 2 | ≥ 3（NFR 決定） |
| CPU limits | 低 | 中 | 高（NFR 決定） |
| HPA | 無 | 可選 | 必要 |
| PDB | 無 | 可選 | 必要 |
| TLS | 可選 | 必要 | 必要 |

---

### 階段 5：RTM 更新與規格確認 🔴

```bash
/rtm-generate update    # 更新部署相關 TC（若有部署驗收測試）
/spec-compliance-check docs/02_architecture/SRD-{System}.md
```

🔴 確認點：資源配置值（CPU/Memory/replicas）與 FRD NFR 數字一致。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Deployment | `k8s/deployment.yaml` | SCG-2 後 |
| Service + Ingress | `k8s/service.yaml`, `k8s/ingress.yaml` | SCG-2 後 |
| HPA | `k8s/hpa.yaml` | SCG-2 後 |
| PDB | `k8s/pdb.yaml` | SCG-2 後 |
| K8s 部署 ADR | `docs/02_architecture/adr/ADR-{NNN}-k8s-deployment.md` | SCG-2 |

---

## 後置動作

```
/devops-github-actions    # 在 CI/CD Pipeline 加入 K8s 部署 Step
/devops-monitoring        # 設定 K8s 指標監控（對應 NFR）
/sdd-gate SCG-4           # 部署配置完成後 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-2 後（部署架構凍結的實作）

---

## 相關 Skill

- `/sd-architect` — SRD 部署架構（K8s 設計的規格依據）
- `/devops-docker` — Docker Image（K8s 部署前置）
- `/devops-monitoring` — K8s 指標監控（NFR 驗證）
- `/adr-generate` — K8s 部署策略 ADR

---

**基於**: AISDLC-SDD v0.01
**對應架構規格**: `docs/02_architecture/SRD-{System}.md` 第 8 章
