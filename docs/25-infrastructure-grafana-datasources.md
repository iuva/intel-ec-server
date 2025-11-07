# Grafana 数据源 Provisioning 配置

## 📋 说明

本目录包含 Grafana 数据源的自动配置文件（Provisioning）。

## ⚠️ 重要提示

**这些是 Grafana 的配置文件，不是 Prometheus 的配置文件！**

如果你的编辑器显示 YAML schema 验证错误（如 "属性 apiVersion 不被允许"），这是误报。编辑器错误地使用了 Prometheus 的 schema 来验证 Grafana 的配置文件。

## ✅ 配置文件说明

### prometheus.yml

这是 Grafana 数据源的 provisioning 配置文件，用于自动配置 Prometheus 数据源。

**文件格式**: Grafana Provisioning YAML  
**文档**: https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources

**配置结构**:
```yaml
apiVersion: 1  # Grafana provisioning API 版本

datasources:
  - name: Prometheus          # 数据源名称
    type: prometheus          # 数据源类型
    access: proxy             # 访问模式
    uid: prometheus           # 唯一标识符（重要！）
    url: http://...           # Prometheus 地址
    isDefault: true           # 是否为默认数据源
    editable: true            # 是否可编辑
    jsonData:                 # 额外配置
      httpMethod: POST
      timeInterval: 15s
      queryTimeout: 60s
      incrementalQuerying: true
```

## 🔧 配置验证

### 正确的验证方式

```bash
# 1. 检查 YAML 语法
yamllint infrastructure/grafana/provisioning/datasources/prometheus.yml

# 2. 启动 Grafana 并检查日志
docker-compose logs grafana | grep -i "provisioning"

# 3. 验证数据源是否正确加载
curl -u admin:***REMOVED*** http://localhost:3000/api/datasources
```

### 不要使用

❌ 不要使用 Prometheus 的 schema 验证这个文件  
❌ 不要使用通用的 YAML schema 验证  
✅ 使用 Grafana 的 provisioning 文档作为参考

## 📚 相关文档

- [Grafana Provisioning 文档](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Grafana 数据源配置](https://grafana.com/docs/grafana/latest/datasources/prometheus/)
- [Grafana API 文档](https://grafana.com/docs/grafana/latest/developers/http_api/data_source/)

## 🐛 常见问题

### Q: 编辑器显示 schema 验证错误
**A**: 这是误报，可以安全忽略。配置文件是正确的。

### Q: 如何禁用编辑器的 schema 验证？
**A**: 在文件顶部添加注释：
```yaml
# yaml-language-server: $schema=
```

### Q: 如何验证配置是否正确？
**A**: 启动 Grafana 并检查数据源是否正确加载：
```bash
docker-compose up -d grafana
sleep 10
curl -u admin:***REMOVED*** http://localhost:3000/api/datasources
```

## ✅ 配置检查清单

- [ ] `apiVersion: 1` 存在
- [ ] `datasources` 列表存在
- [ ] 每个数据源有 `name`, `type`, `url`
- [ ] Prometheus 数据源有 `uid: prometheus`
- [ ] `isDefault: true` 设置正确
- [ ] `jsonData` 配置合理

---

**最后更新**: 2025-10-11  
**配置状态**: ✅ 正确  
**Schema 警告**: ⚠️ 可忽略（误报）
