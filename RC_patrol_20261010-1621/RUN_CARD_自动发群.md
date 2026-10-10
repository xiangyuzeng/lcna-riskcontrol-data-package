# 每晚短信巡检 · 运行卡 C：自动发群（2026-10-11 起）

给人看的：装好以后每晚不用再跑命令。22:05 左右机器自己取数、自己核对，然后发到群里（先发测试群，切换以后发正式群）。取不到数就在 23:35 发一句「暂时取不到」。运行卡 A、B 仍然有效，留着补发和出问题时用。

## 每天看一眼（可选）

```
python3 -B RC_patrol/autopost/autopost.py status
```

心跳在 40 分钟以内，说明 cron 在跑；「最近的窗口」里昨晚是 posted，就是发出去了。

## 状态是什么意思

| 状态 | 意思 | 怎么办 |
|---|---|---|
| posted | 已发 | 不用管 |
| failline_posted | 发了「暂时取不到」 | 看 `_local_only/autopost/child/` 里那晚的输出找原因；修好后在 22:00–05:15 补发（下面） |
| manual_skip | 有人手动跑过这一段，自动发送没发 | 你自己发（运行卡 A 那段文字） |
| send_uncertain | 发出去了但飞书没回话，不知道到没到 | 先看群里；确实没有再 `send-post --date D --resend-uncertain` |
| send_rejected | 飞书拒收（看 `history/autopost_log.csv` 的说明，比如缺关键词） | 改机器人设置或重新录地址，然后补发 |
| gave_up | 到 00:40 也没发出去 | 同 failline_posted |
| manual_send_retry | 你手动 send-post 时飞书没连上 | 过一会儿再跑一次 send-post；自动发送不会再管这一段 |

## 子进程的退出码，自动发群怎么处理

| 退出码 | 意思 | 自动发群 |
|---|---|---|
| 0，最后一行「可以发。」 | 正常 | 自己再核一遍，过了就发 |
| 2 | 太早或不在时段 | 不算次数，下次再试 |
| 3 | 另一个查库任务在跑，或锁文件还在 | 下次再试；到 23:35 还不行就发「暂时取不到」 |
| 7 | 服务器忙 | 最多再试两次 |
| 5，gateway connect failed | 一条也没发出去 | 下次再试 |
| 5，其他 | 查询失败 | 不再试，马上发「暂时取不到」 |
| 4 / 6 / 8 / 其他 | 核对没过 / 隐私扫描不干净 / 找不到网关 / 意外 | 不再试，马上发「暂时取不到」 |

## 常用操作

- 某一晚想自己发：白天先 `autopost.py skip --date <那天的纽约日期>`。
- 补发：在 22:00–05:15 跑 `PYTHONDONTWRITEBYTECODE=1 python3 RC_patrol/toolkit/patrol24.py run --date D --per-code`，看到「可以发。」以后跑 `python3 -B RC_patrol/autopost/autopost.py send-post --date D`（会让你输入「发送」确认；等你确认的时候不占锁，不挡自动发送）。飞书没连上（manual_send_retry）就过一会儿再跑一次 send-post。那一晚最后一小时一条请求都没有时，它会说「数据延迟」，你确认数没问题再加 `--accept-lag`。
- 测试群发了两晚都对：白天跑 `autopost.py set-mode team`，下一晚起发正式群。
- 全部停掉：`autopost.py disable`（再开 `enable`）；连 cron 一起删：`autopost.py uninstall-cron`。
- 录或换地址：在你自己的终端里跑 `autopost.py set-webhook --target test|team`，不要贴进任何聊天。
