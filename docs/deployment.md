# 单机私有 staging 部署

## 状态与边界

这套制品提供 **单台主机 + Docker Compose + Caddy + Basic Auth + 同域前后端 +
单 FastAPI worker** 的私有 staging。默认使用确定性 `synthetic` 数据，并设置
`CHAN_QUANT_REMOTE_NETWORK_ENABLED=false`。它不代表已经部署到外部服务器，也不授予
第三方行情的访问、生产使用或再分发权利。

本阶段不包含服务器购买或登录、域名、DNS、HTTPS、HSTS、ICP/公安备案、镜像推送、
自动部署、匿名公开访问、真实行情接入或公开负载测试。

## 前置条件

- Docker Engine 与 Docker Compose v2。
- 本地端口 `127.0.0.1:8080` 可用，或在私有环境文件中改用其他环回端口。
- 一组仅供该 staging 使用的私有用户名和密码。真实凭证不得提交到 Git。

前端生产构建固定使用容器内 **Node 22**；宿主机不需要安装 Node。后端镜像使用锁定的
`uv.lock` 和 Python 3.12，最终 API 容器以非 root 用户、单 worker 运行。

## 准备私有环境

复制示例文件后，在本机私下修改；`.env.production` 已被 Git 忽略：

```bash
cp .env.production.example .env.production
```

生成 Caddy 接受的密码散列。为避免把明文密码写进命令历史，可在交互式 shell 中读取：

```bash
read -s CHAN_QUANT_PRIVATE_PASSWORD
export CHAN_QUANT_PRIVATE_PASSWORD
docker run --rm caddy:2.10-alpine \
  caddy hash-password --plaintext "${CHAN_QUANT_PRIVATE_PASSWORD}"
unset CHAN_QUANT_PRIVATE_PASSWORD
```

把输出写入私有 `.env.production` 的 `CHAN_QUANT_BASIC_AUTH_HASH`，并替换
`CHAN_QUANT_BASIC_AUTH_USER`。同时把 `CHAN_QUANT_RELEASE_SHA` 设置为
`git rev-parse HEAD` 输出的当前完整提交 SHA；production 会拒绝 `development` 或其他非 Git
标识。示例中的 placeholder 不是可用配置。Compose 不会把明文密码传入容器；冒烟脚本才
临时读取 `CHAN_QUANT_BASIC_AUTH_PASSWORD`。

## 构建与启动

先验证解析后的配置，再构建并等待健康状态：

```bash
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d --wait
docker compose --env-file .env.production ps
```

浏览器打开 `http://127.0.0.1:8080/` 并使用私有凭证。宿主机只发布环回网关端口；
API 的 `8000` 仅存在于内部 Docker 网络。

## 健康、版本与日志

所有页面和运行接口都受网关认证保护：

```bash
curl --user '<user>:<password>' http://127.0.0.1:8080/healthz
curl --user '<user>:<password>' http://127.0.0.1:8080/readyz
curl --user '<user>:<password>' http://127.0.0.1:8080/version
curl --user '<user>:<password>' http://127.0.0.1:8080/api/v1/runtime-capabilities
docker compose --env-file .env.production logs --tail=200 api web
```

`/healthz` 只表达进程存活，不访问上游。`/readyz` 校验运行配置和 CSV/snapshot 必要文件，
错误时返回非 2xx，且不会回显宿主机绝对路径。第三方行情瞬时不可用不会让 readiness
失败。production 默认关闭 `/docs`、`/redoc` 和 `/openapi.json`。

## 离线能力合同

默认 capabilities 返回 `synthetic`、远端网络关闭、强制市场温度刷新关闭。前端在
capabilities 未返回或失败时同样按离线处理，不启动 Quote 轮询，不读取市场温度，也不
挂载证券搜索、指数表现或多标的远端比较请求。合成 Dashboard、数据方法页和静态研究
说明仍可使用。

`refresh=true` 不能绕过配置；当 `CHAN_QUANT_ALLOW_FORCE_REFRESH=false` 时，后端返回
结构化 `FORCE_REFRESH_DISABLED` 拒绝。

## CSV 与 snapshot 只读挂载

把仓库外目录通过 `CHAN_QUANT_DATA_MOUNT` 挂到容器内 `/market-data`。挂载始终只读，
运行配置必须使用容器内路径，不能写宿主机绝对路径：

```env
CHAN_QUANT_DATA_SOURCE=csv
CHAN_QUANT_DATA_MOUNT=/private/operator/data
CHAN_QUANT_CSV_PATH=/market-data/bars.csv
```

snapshot 示例：

```env
CHAN_QUANT_DATA_SOURCE=snapshot
CHAN_QUANT_DATA_MOUNT=/private/operator/data
CHAN_QUANT_DATA_PACKAGE_PATH=/market-data/snapshot
```

`manifest.json`、`bars.csv`、行情数据、授权材料和凭证均不得进入 Git。文件完整性只证明
本地制品与 manifest 一致，不证明数据许可、复权经济含义或策略有效性。

## 冒烟验证

在当前 shell 临时提供明文密码，只用于 `curl`，不进入容器或 Git：

```bash
export CHAN_QUANT_BASIC_AUTH_USER='<private-user>'
read -s CHAN_QUANT_BASIC_AUTH_PASSWORD
export CHAN_QUANT_BASIC_AUTH_PASSWORD
./deploy/smoke-test.sh
unset CHAN_QUANT_BASIC_AUTH_PASSWORD
```

脚本验证未认证请求为 401、认证后的首页与深层 SPA 路由、health/readiness/version，以及
默认强制刷新为 403。完整 CI 还检查 API 非 root、前端镜像不含 Node 开发树、API 端口
未发布、重启恢复、down/up 恢复和日志敏感内容。

## 升级、停止与回滚

升级前记录当前 Git SHA 和私有环境文件备份，然后在目标提交重新构建：

```bash
docker compose --env-file .env.production build --pull
docker compose --env-file .env.production up -d --wait
./deploy/smoke-test.sh
```

停止但保留 Caddy 状态卷：

```bash
docker compose --env-file .env.production down
```

回滚时切回已经验证的 Git 提交，使用同一私有环境重新 `build` 与 `up -d --wait`，再执行
冒烟。不要删除 Caddy volume 或外部数据目录作为普通回滚步骤。若配置合同或数据包变更，
应先恢复与旧提交匹配的私有配置和只读数据，再启动旧制品。

## 正式域名与 HTTPS 后续阶段

当前 Caddy 明确关闭自动 HTTPS，本地 HTTP staging 也不发送 HSTS。进入真实服务器阶段
后，需要单独确认服务器账户、防火墙、备份、正式 Host、DNS、证书持久化、80/443、
HSTS、外部可达性和适用备案要求。未经新的明确授权，不修改 Cloudflare、DNS、GitHub
Secrets、远端 deployment environment 或任何服务器状态。

## 本阶段未验证的事项

- 真实服务器进程、重启、磁盘与备份。
- 真实域名、DNS、HTTPS、证书续期与 HSTS。
- 中国大陆 ICP 或其他合规流程。
- 真实市场行情、供应商 SLA、商业使用与再分发授权。
- 匿名公开访问、应用级限流、多实例、共享缓存和公开负载测试。
