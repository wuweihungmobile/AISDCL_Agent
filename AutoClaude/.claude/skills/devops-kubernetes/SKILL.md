---
name: devops-k8s
description: 設計和部署 Kubernetes 應用，包含 Deployment、Service、Ingress 配置
user-invocable: true
disable-model-invocation: false
argument-hint: "<app_type: 應用類型 (web/api/worker/cronjob)> [environment: 目標環境 (dev/staging/production)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# DevOps Kubernetes Skill

基於 AISDLC DevOps 情境的 Kubernetes 部署技能。

---

## 觸發方式

```bash
/devops-k8s web production
/devops-k8s api staging
/devops-k8s --app_type=web --environment=production
```

---

## 執行流程

### 階段 1: 需求評估 🔴

**確認項目**:
- [ ] 應用類型 (Web/API/Worker/CronJob)
- [ ] 資源需求 (CPU/Memory)
- [ ] 副本數量
- [ ] 環境變數和 Secrets
- [ ] 健康檢查端點
- [ ] 對外暴露方式 (LoadBalancer/Ingress/ClusterIP)

🔴 **確認點**: 確認以上配置需求

---

### 階段 2: 核心資源配置

#### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{app_name}}
  labels:
    app: {{app_name}}
    environment: {{environment}}
spec:
  replicas: {{replicas}}
  selector:
    matchLabels:
      app: {{app_name}}
  template:
    metadata:
      labels:
        app: {{app_name}}
    spec:
      containers:
        - name: {{app_name}}
          image: {{image}}:{{tag}}
          ports:
            - containerPort: {{port}}
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: {{port}}
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: {{port}}
            initialDelaySeconds: 5
            periodSeconds: 5
          envFrom:
            - configMapRef:
                name: {{app_name}}-config
            - secretRef:
                name: {{app_name}}-secrets
```

#### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{app_name}}
spec:
  selector:
    app: {{app_name}}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {{port}}
  type: ClusterIP
```

#### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{app_name}}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - {{domain}}
      secretName: {{app_name}}-tls
  rules:
    - host: {{domain}}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{app_name}}
                port:
                  number: 80
```

---

### 階段 3: 配置管理

#### ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{app_name}}-config
data:
  NODE_ENV: "{{environment}}"
  LOG_LEVEL: "info"
  API_URL: "https://api.example.com"
```

#### Secret (使用 SealedSecret 或外部 Secret 管理)

```yaml
# k8s/secret.yaml (示例，實際應使用加密方案)
apiVersion: v1
kind: Secret
metadata:
  name: {{app_name}}-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://..."
  API_KEY: "..."
```

---

### 階段 4: 進階配置

#### HPA (Horizontal Pod Autoscaler)

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{app_name}}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{app_name}}
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

#### PodDisruptionBudget

```yaml
# k8s/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{app_name}}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: {{app_name}}
```

---

### 階段 5: 部署驗證

**部署命令**:
```bash
# 套用配置
kubectl apply -f k8s/

# 檢查部署狀態
kubectl rollout status deployment/{{app_name}}

# 查看 Pods
kubectl get pods -l app={{app_name}}

# 查看日誌
kubectl logs -l app={{app_name}} --tail=100
```

**驗證清單**:
- [ ] Deployment 正常運行
- [ ] 所有 Pods Ready
- [ ] Service 端點正常
- [ ] Ingress 路由正常
- [ ] 健康檢查通過

---

## 環境配置差異

| 配置 | Dev | Staging | Production |
|------|-----|---------|------------|
| Replicas | 1 | 2 | 3+ |
| Resources | 低 | 中 | 高 |
| HPA | 無 | 可選 | 必要 |
| PDB | 無 | 可選 | 必要 |
| TLS | 可選 | 必要 | 必要 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Deployment | `k8s/deployment.yaml` |
| Service | `k8s/service.yaml` |
| Ingress | `k8s/ingress.yaml` |
| ConfigMap | `k8s/configmap.yaml` |
| HPA | `k8s/hpa.yaml` (生產環境) |

---

## 相關 Skill

- `/devops-github` - CI/CD Pipeline
- `/performance` - 效能調校

---


## 相關檔案

- SOP 參考: `scenarios/devops/SOP_QuickRef.md`

**基於**: AISDLC v0.09 DevOps 情境
