# BookPath 定时访问

Cloudflare Worker 每 10 分钟请求一次 Instabox 网站的 `/health`，检查服务并尝试避免空闲暂停。任务运行在 Cloudflare，电脑关机不影响已上线任务。

目标：`https://8180-agrazil7kddepuxpn3avhjqu6q.instabox.tech/health`。

已于北京时间 2026-11-24 16:51 发布到 Cloudflare，任务名称为 `bookpath-instabox-keepalive`。已从 Cloudflare API 回读确认定时设置、目标地址和运行日志配置；部署记录保存在 `deployment.json`。本地 Cloudflare 运行环境中的定时事件已成功请求到网站并返回 HTTP 200 / ok。

定时表达式：`*/10 * * * *`，即每小时的 0、10、20、30、40、50 分钟执行（UTC）。每天约 144 次请求。

Worker 仅有定时处理器，不发布 HTTP 入口；不保存用户密码、网站登录凭据或 Instabox API 密钥。请求禁用缓存，等待时间上限为 60 秒；失败记录在 Cloudflare Workers Logs 中。

## 部署

在本目录安装依赖并完成 Cloudflare 登录，然后运行：

```sh
npm ci
npx wrangler login
npm run check
npm run deploy
```

Cron 配置生效可能需要最多 15 分钟。可在 Cloudflare 控制台的 Workers & Pages 中打开 `bookpath-instabox-keepalive`，查看定时触发器和运行日志。

## 暂停定时访问

将 `wrangler.jsonc` 的 `triggers.crons` 改成空数组 `[]`，重新运行 `npm run deploy`。仅删除本地文件不会停止云端任务。

## 平台运行限制

Instabox 免费实例的空闲暂停时间固定为 30 分钟，访问公网地址可唤醒因空闲而暂停的实例。定时请求只能尝试避免空闲暂停，不能保证全天持续在线。

免费实例每轮起始最长运行 120 分钟，使用中可能延长，单轮最多 480 分钟。连续达到运行时限时，第一次冷却 5–20 分钟，第二次 60–75 分钟，第三次及以后 120–135 分钟；冷却期间无法唤醒。实际结束时间以平台的 `cooldownUntil` 为准。

连续次数会在无冷却欠额的暂停结束一轮时重置（例如正常空闲暂停），也会在冷却结束至少 2 小时后才开始下一轮时重置。Cloudflare 定时请求不能取消运行上限和冷却限制，冷却结束后还需等待下一次请求尝试唤醒。需要全天在线时，应使用支持常驻运行的实例方案。

- [Instabox 自动暂停与运行时限](https://instabox.sh/docs/machines/auto-pause)
- [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
