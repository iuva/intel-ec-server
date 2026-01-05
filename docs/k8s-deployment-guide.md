# Kubernetes (K8s) 部署指南

本指南将指导您如何在 Kubernetes 集群中部署 Intel EC Microservices。

## 📋 目录

- [前提条件](#前提条件)
- [镜像准备](#镜像准备)
- [部署步骤](#部署步骤)
- [验证部署](#验证部署)
- [访问服务](#访问服务)
- [清理资源](#清理资源)

---

## 前提条件

1.  **Kubernetes 集群**：
    -   本地开发：推荐使用 [Minikube](https://minikube.sigs.k8s.io/) 或 [Kind](https://kind.sigs.k8s.io/)。
    -   或者任何标准的 K8s 集群。
2.  **kubectl 命令行工具**：已安装并配置好连接到急群。

---

## 镜像准备

Kubernetes 需要能够拉取到服务镜像。如果您使用的是本地集群（如 Minikube 或 Kind），需要将镜像加载到集群中，或者推送到镜像仓库。

### 1. 构建镜像

```bash
# 在项目根目录执行
docker-compose build
```

### 2. 加载镜像到本地集群（以 Kind 为例）

如果您使用的是 Kind：

```bash
kind load docker-image intel-cw-ms/gateway-service:latest
kind load docker-image intel-cw-ms/auth-service:latest
kind load docker-image intel-cw-ms/host-service:latest
```

如果您使用的是 Minikube：

```bash
minikube image load intel-cw-ms/gateway-service:latest
minikube image load intel-cw-ms/auth-service:latest
minikube image load intel-cw-ms/host-service:latest
```

> **注意**：如果不加载镜像，K8s 将尝试从 Docker Hub 拉取，导致 `ErrImagePull` 错误（因为这些是本地构建的私有镜像）。我们在 Deployment 中设置了 `imagePullPolicy: IfNotPresent`，所以只要本地有镜像即可。

---

## 部署步骤

所有 K8s 配置文件都位于 `deploy/k8s/` 目录下。

### 1. 创建命名空间

```bash
kubectl apply -f deploy/k8s/namespace.yaml
```

### 2. 应用配置和密钥

```bash
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml
```

> **⚠️ 关于 PYTHONPATH**：
> `configmap.yaml` 中包含了一个关键配置 `PYTHONPATH: "/install/lib/python3.8/site-packages:/app"`。
> 这是为了解决 Docker 镜像中 "No module named uvicorn" 的问题。请勿随意修改此配置。

### 3. 部署服务

```bash
# 部署 Gateway Service
kubectl apply -f deploy/k8s/gateway-deployment.yaml

# 部署 Auth Service
kubectl apply -f deploy/k8s/auth-deployment.yaml

# 部署 Host Service
kubectl apply -f deploy/k8s/host-deployment.yaml
```

---

## 验证部署

查看 Pod 状态及其运行情况：

```bash
# 查看所有 Pod
kubectl get pods -n intel-ec-ms

# 查看服务日志
kubectl logs -f -l app=gateway-service -n intel-ec-ms
kubectl logs -f -l app=auth-service -n intel-ec-ms
```

确保所有 Pod 的状态均为 `Running`。

---

## 访问服务

Gateway Service 被配置为 `NodePort` 类型，固定端口 `30000`。

### 本地访问方式

1.  **直接访问（Minikube）**：
    ```bash
    # 获取 Minikube IP
    minikube ip
    # 访问地址: http://<minikube-ip>:30000
    ```

2.  **端口转发（通用方式）**：
    如果无法直接访问 NodePort，可以使用 `port-forward`：
    ```bash
    kubectl port-forward service/gateway-service 8000:8000 -n intel-ec-ms
    # 访问地址: http://localhost:8000
    ```

3.  **验证接口**：
    ```bash
    curl http://localhost:8000/health
    ```

---

## 配置持久化存储

Host Service 需要从 ConfigMap/Secret 加载配置，并且需要一个持久卷（PVC）来存储上传的文件。

在 `host-deployment.yaml` 中，我们定义了一个 `PersistentVolumeClaim`，名为 `host-upload-pvc`。在大多数标准 K8s 集群（包括 Minikube/Kind）中，会有默认的 StorageClass 自动提供存储。如果您的 Pod 处在 `Pending` 状态且原因是 PVC 未绑定，请检查集群的存储类配置。

---

## 清理资源

要删除所有部署的资源：

```bash
kubectl delete namespace intel-ec-ms
```
