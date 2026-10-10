# 21 点巡检自动发群（autopost.py）

用户 2026-10-10 决定：每晚 21 点那一段的巡检数由机器自动发到飞书群。先发测试群两三晚，没问题再切到正式群；取不到数就发一句固定的话；重试到 23:35；不要求签名；不另设提醒群。

## 怎么工作

- cron 每小时 :05 和 :35 叫一次 `autopost.py cron`。它按纽约时间自己判断要不要做事，所以跟服务器的时区、夏令时都没关系。
- 处理的是纽约日期 D 那天 21:00 截止的 24 小时（21:30 以后是当天，凌晨是前一天）。
- 22:05、22:35、23:05、23:35 最多试 4 次，每次跑一遍运行卡 A 的同一件事：`toolkit/patrol24.py run --date D --per-code`（路 A，子进程；patrol24 自己管 22:00–05:30 的时段、负载检查、核对和隐私扫描）。
- 子进程说「可以发。」以后，autopost 再自己核一遍才发：
  - 帖子文件是这次跑出来的，和屏幕上那段一字不差；
  - 标题、时间窗是按 D 重新算出来的；
  - 区号清单等于 `codes_21.txt`；
  - 四个数等于历史表那一行；
  - 大小关系对；
  - 隐私扫描干净；
  - 不含「附」、REJECT、REVIEW、@ 这些只给自己看的东西。
- 没发出去时：锁、服务器忙、网关连不上会再试，到 23:35 还不行才发下面这句；核对没过、查询报错、超时、隐私扫描没过、找不到网关不再试，当场就发：
  ```
  北美短信例行巡检（纽约时间 M/D 21:00）
  今晚21点的巡检数暂时取不到，弄好后补发。
  ```
- 23:40–00:39 不碰数据库，只补发上面这句（如果 23:35 那次没发成）；00:40 以后记 gave_up。
- 同一段绝不发两次：一把文件锁（`send-post` 也用它）；每段一个状态文件；先记「正在发」再发；结果不确定（飞书没回、飞书返回 5xx）就不重发；有人手动跑过这一段就不发（你自己发），每次发之前都再看一遍。
- cron 进程在子进程跑到一半时没了（重启、被杀）：子进程的输出写在文件里（`_local_only/autopost/child/`），下一次先看子进程还在不在，在就等；不在就只把它输出里写到的那个目录认作自己的，按失败一次算，接着重试。这中间你手动跑过，它照样算手动、不发。
- 发「暂时取不到」之前也先看一眼有没有人手动跑过。
- 截止前最后十分钟没人请求（安静的晚上）不算数据不全：只有在截止后半小时内跑时才把它当「数据延迟」。最后一整小时一条都没有，才当成日志源可能停了（重试，到 23:35 发「暂时取不到」）。

## 文件

| 位置 | 内容 |
|---|---|
| `RC_patrol/autopost/` | `autopost.py`、`test_autopost.py`、本文件、`SHA256SUMS`（只放代码，升级时可以整个换掉） |
| `RC_patrol/config/autopost.json` | 开关、模式（test/team）、起始日期、跳过的日期、本机标识、子进程用的 python / PATH / HOME |
| `RC_patrol/history/autopost_state/<D>.json` | 每一段的状态：试了几次、退出码、发了什么、结果 |
| `RC_patrol/history/autopost_log.csv` | 流水（固定的说法，不含地址） |
| `RC_patrol/_local_only/feishu.conf` | 两个 webhook（权限 600，只有 `set-webhook` 写，任何输出里都不出现；打包时不带） |
| `RC_patrol/_local_only/autopost/` | 心跳、cron.log、每次子进程的输出、最后一次错误、crontab 备份；需要代理才连得上飞书时，自己写一个 `feishu_proxy`（一行 `https_proxy=…`，只用于飞书，不给查库的子进程） |

## 常用命令（在运行目录 `/app`）

```
python3 -B RC_patrol/autopost/autopost.py status                 # 看现在的状态
python3 -B RC_patrol/autopost/autopost.py set-webhook --target test   # 在你自己的终端里录地址（不显示）
python3 -B RC_patrol/autopost/autopost.py set-mode team          # 测试群发过两晚以后切到正式群（白天切）
python3 -B RC_patrol/autopost/autopost.py skip --date 2026-10-12  # 某一晚不自动发（你自己发）
python3 -B RC_patrol/autopost/autopost.py disable                # 全部停掉；enable 再开
python3 -B RC_patrol/autopost/autopost.py send-post --date D     # 补发：先在 22:00–05:15 跑 patrol24.py run --date D --per-code
```

- 自动发的那几晚，不要再手动跑 `nightly`：手动跑过的那一段它就不发了（状态 manual_skip），要你自己发。
- 「结果不确定」（send_uncertain）：先看群里有没有。确实没有，再跑 `send-post --date D --resend-uncertain`。
- 换了机器或容器：`adopt-host`。

## 已知的限制

- 没有提醒群（用户 10-10 决定）：出问题只在 `status`、`history/autopost_log.csv` 和 `_local_only/autopost/` 里看得到。
- 地址不签名（用户 10-10 决定）：知道地址的人都能往群里发消息。要加签名：在飞书机器人设置里打开「签名校验」，再跑一次 `set-webhook --target … --secret`。
- 只认 `open.feishu.cn` 的地址。
- cron 停了不会有人知道：`status` 里的心跳超过 40 分钟就是没在跑。
- patrol24「附」那一行里的「最新一条比截止时间早 10 分钟以上……晚几分钟再跑一次」在 22 点以后跑时只是说最后十分钟没人请求，不用重跑（下次工具更新时改这句提示）。

## 测试

`PYTHONDONTWRITEBYTECODE=1 python3 -B RC_patrol/autopost/test_autopost.py`（不连库、不联网）。

`python3 -B RC_patrol/autopost/autopost.py rehearse` 在临时目录里用保存过的某一段回复真跑一遍 patrol24 + autopost（发送是假的），`RC_patrol/` 不变。
