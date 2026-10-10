# RUN_LOG — RC_patrol（每日 21:00 短信巡检设置）

运行目录：/app（与 RC_data_* 同级）。时间均为 America/New_York。数据库通道：路 B（mcp-db-gateway 查询工具，逐条发送、回复原样存 .json）。

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-10 02:56 | Step A–C | plan | DONE | 只读侦察（环境、只读权限、时钟、并发、已有包；回复见 runs/20261010-025100_recon/），4 个决策问题提交用户（回答在 06:24 才到，见下一行） |
| 2026-10-10 06:24 | Step C | approve | DONE | 用户回答（约 06:24，已过 22:00–06:00 取数窗口）：M1 重叠可加 --m1-active-ok（M1 已于 03:12 完成，不再需要）；21:02 巡检为常设例外；17 次截图不查消息时间、按 E1 按小时核对；追问后决定 P0–P3 现在跑（一次性例外）、P6 今晚 22:00 后续跑（全量）；随后计划获批 |
| 2026-10-10 06:32 | P0 | start | — | 新建 RC_patrol/（无已有目录，非续跑、非重装） |
| 2026-10-10 06:38 | P0 | end | DONE | 17/17 个文件 sha256 与清单一致（6 个从 RC_data_20260927-0614/toolkit 复制，11 个照抄写入，均一次通过）；verify 16/16；保留字 259 个；test_guard 27 拒绝 + 13 通过 0 失败；test_patrol24 29 项 OK；toolkit 隐私扫描 unresolved 0 |
| 2026-10-10 06:38 | P1 | start | — | 分表发现 + 纽约日核对（第三个包） |
| 2026-10-10 06:39 | P1 | note | — | 偏差（如实记录）：本次 s0a–s0d 四条在同一轮里一起发出（可能并发），违反「一次一条」；四条均为元数据 / EXPLAIN 小语句；此后严格一条一轮 |
| 2026-10-10 06:47 | P1 | validate 3 days | DONE | 纽约日 09-20 / 09-23 / 09-26 三天与第三个包逐格一致（fixture match ×3），dup_rows 全 0；分表 64（0000..0063）；runs/20261010-063839_validate_ny；其余 4 天放到 P2/P3 之后 |
| 2026-10-10 06:47 | P2 | start | — | UTC 日 10-07、10-08 与 Doris 对比 |
| 2026-10-10 06:52 | P2 | end | DONE | UTC 10-07：总量 3430 / PASS 2014，UTC 10-08：3051 / 1613，与 Doris 两天都差 +0 / +0；dup_rows 0；runs/20261010-064700_validate_utc |
| 2026-10-10 06:52 | P3 | start | — | 近 3 个 21:00 窗口（10-07 / 10-08 / 10-09） |
| 2026-10-10 07:00 | P3 | end | DONE | 3 个 21:00 窗口写入 history/patrol24_history.csv（10/7：3470/1990/888/841；10/8：3049/1612/491/464；10/9：2152/1235/214/152）；runs/20261010-065233_backfill |
| 2026-10-10 07:00 | P1 | validate other 4 days | — | 纽约日 09-21、09-22、09-24、09-25 |
| 2026-10-10 07:11 | P1 | end | DONE | 纽约日 09-20…09-26 七天全部与第三个包逐格一致（fixture match 7/7：①②REJECT/REVIEW/+1/+86/④/rows_all 全等，③=③+无效），dup_rows 全 0；另 4 天在 runs/20261010-070032_validate_ny |
| 2026-10-10 07:11 | P4 | start | — | Doris 写法（纯文本，不在此执行） |
| 2026-10-10 07:13 | P4 | end | DONE | doris/巡检_0900_Doris写法.sql（--at 09:00 --date 2026-10-11）与 doris/巡检_2100_对照.sql（--at 21:00 --date 2026-10-10），纯文本、未在 Doris 执行；说明 doris/README_给David.md（cc_odd_rows 读法） |
| 2026-10-10 07:13 | P5 | start | — | 纽约时间早于今天 21:02 |
| 2026-10-10 07:13 | P5 | end | PARTIAL | 本会话结束时仍早于 21:02：今晚的群消息由运行卡 RUN_CARD.md 在 21:02 后出（21:02 为用户批准的常设例外，见 README）；续跑时的判断：找 manifest.json 里 kind 为 "slot"、windows[0].key 为 "2026-10-10 21:00" 的运行目录（不是 20261010-063831_slot，那是分表发现），离线重跑 `patrol24.py collect <该目录>`，输出以「可以发」结束才把 P5 记 DONE；找不到这样的目录就先跑运行卡 |
| 2026-10-10 07:13 | P6 | start | — | 用户决定（06:24）：P6 今晚 22:00 后续跑（全量，按优先级），本会话只做不连库的准备 |
| 2026-10-10 07:13 | P6 | end | PARTIAL | 已准备：sql/e0_drafts/ 13 条 E0 草稿（5 条 information_schema 列名、策略行、规则、计数特征、预上线列表、4 天操作日志），全部通过 shard_runner check，未发送；E1–E5 未开始——等 22:00 后按 README「eoHQ」一节的顺序续跑 |
| 2026-10-10 07:36 | P7 | start | — | README（9 节）、NEXT_RUN、离线复核、隐私扫描、打包 |
| 2026-10-10 07:36 | P7 | review | DONE | 离线复核 workflow（3 个只读审阅 + 3 个复核，不连库、不读 _local_only）：确认 15 条（视角间有重复）全部改正；另采纳 4 条被驳回的建议（计划 / 批准分行、侦察回复存档 runs/20261010-025100_recon、今天 09:00 的 Doris 文件、截图与 21:48 标为转述）；E0 草稿的规则名 / 策略名 / 特征名加了同样的屏蔽；toolkit verify 16/16 |
| 2026-10-10 07:36 | P7 | end | PARTIAL — 设置阶段的包，MANIFEST 与 zip 随后生成 | 隐私扫描报告 _local_only/privacy_scan_20261010-0736.md；zip 为 RC_patrol_package_20261010-0736.zip（运行目录 /app）；P5 / P6 今晚续跑后再打最终包，因此本行不是 DONE |

续跑（2026-10-10 晚）

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-10 10:41 | Step A–C | plan | DONE | 离线侦察：2026-10-10 21:00 的 slot 运行不存在（P5 未做）；RC_data_* 全部已完成、无锁、无查库进程；提示词 .md 不在 /app；用户 10:33 决定：现在只做 U（离线），22:00 后再粘贴同一提示词续跑 V/P5/P6/P7 |
| 2026-10-10 10:41 | U | start | — | 工具包与运行卡升级到 Part 2 版本 |
| 2026-10-10 10:41 | U | move | DONE | 旧 toolkit/ 与 RUN_CARD.md 移到 _superseded/round9_20261010-1041/；config/ history/ runs/ results/ posts/ doris/ sql/ _local_only/ 保留 |
| 2026-10-10 10:50 | U | files | DONE | 18/18 与 manifest_round9 一致（10 个按 sha 复制，tk11_patrol24_outer/percode 改名；8 个照 Part 2 写入，README_patrol24.md 与 RUN_CARD.md 由提示词原文块按字节取出）；toolkit/SHA256SUMS 17 行；`patrol24.py verify` 17/17；reserved_words.txt 259 行保留 |
| 2026-10-10 10:50 | U | tests | DONE | test_guard 27 拒 + 13 过、failures=0；test_patrol24 47 项 OK；privacy_scan toolkit unresolved 0；toolkit/__pycache__（verify 未设 PYTHONDONTWRITEBYTECODE 时生成）已删 |
| 2026-10-10 10:50 | U | history | DONE | 备份到 _local_only/history_before_upgrade.csv；seed-history 加 4 行（10/3–10/6，fixture_l1），早上 3 行 backfill 逐字未变，且与新 fixture 10/7–10/9 数值相同 |
| 2026-10-10 10:50 | U | drafts | DONE | sql/e0_drafts 13/13 过 `shard_runner.py check` |
| 2026-10-10 10:50 | U | gateway | DONE | `gateway-check`：在「本地作用域」找到（sse），路 A 可用（只记标签） |
| 2026-10-10 10:50 | U | end | DONE | 全程离线、无查库语句 |
| 2026-10-10 10:50 | V/P5/P6/P7 | pending | — | V/P5/P6/P7 待 22:00 后续跑（用户 10:33 决定）；21:02 例外已撤回，今晚 22:00 后查、约 22:05 发 |
| 2026-10-10 10:54 | P5 | refused | — | 用户手动运行 `patrol24.py nightly`：纽约 10:54 不在 22:00–05:30，脚本退出码 2，未建运行目录、未发任何语句；顺手删了 10:50 `--help`（未设 PYTHONDONTWRITEBYTECODE）留下的 toolkit/__pycache__，`verify` 仍 17/17 |

补丁（白天测试，2026-10-10）

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-10 13:34 | 1 Look | read-only | DONE | 旧版 verify 17/17；config/ 只有 shards.json（无 outside_window_log.csv）；RUN_LOG 无白天 V end DONE → 第 4 步可做；补丁 .md 不在 /app，本会话 transcript 里的原文 18/18 块 sha 与大小一致；回放源 runs/20261010-065233_backfill w03（10/9 21:00）回复齐全、各项与基准相同 |
| 2026-10-10 13:35 | 2 Install | start | — | 开始安装 round11 补丁 |
| 2026-10-10 13:36 | 2 Install | end | DONE | 旧 toolkit/ 与 RUN_CARD.md 移到 _superseded/round11_20261010-1335/；消息原文（本会话 transcript，与 .md 同文）存 _local_only/patch_round11_message.md，extract_patch.py：18 files written, mismatched: none；verify 17/17；test_guard failures=0；test_patrol24 60 项 OK；privacy_scan toolkit unresolved 0；无 __pycache__ |
| 2026-10-10 13:36 | 3 Replay | replay-test | DONE | 不连库；源 runs/20261010-065233_backfill w03；[validate] 10/8 21:00 至 10/9 21:00 ① 2152 ② 1235 ③ 214 ④ 152 \| ok \| match；[post] 打印群消息并以「可以发。」结束；replay-test: OK；runs/ 仍 6 个、history md5 未变、posts/ config/ 无新文件 |
| 2026-10-10 13:40 | 4 Live | run | DONE | 用户 13:39 明确同意；`patrol24.py run --validate-slot 2026-10-09:2026-10-09 --outside-window-ok --no-cli`（路 A，--no-cli 保证不走 claude mcp get）：GO（Threads_running=2，64 分表，EXPLAIN 走索引），8 条语句 NY 13:39:52–13:39:53；dup_rows 0；outside_window_log.csv 有 run 行 + _send 行（8 statements）；history 7 行，10/9 那行由工具改为 validate_slot（数不变），其余行未变 |
| 2026-10-10 13:40 | V | end | DONE | daytime live check (user exception 2026-10-10, logged in config/outside_window_log.csv), runs/20261010-133952_validate_slot, fixture match 2152/1235/214/152; replaces any earlier V line |
| 2026-10-10 13:40 | 5 End | summary | DONE | 补丁白天测试结束：未跑 eohq24 / nightly / P6；P5/P6/P7 待今晚续跑（V 已完成可跳过） |

续跑（2026-10-10 晚）

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-10 13:40 | Step A–C | plan | DONE | 离线侦察（13:35–13:40）：补丁会话当时在另一容器运行；已装 toolkit 与本提示词 Part 2 清单 18/18 一致；无 2026-10-10 21:00 slot 运行；RC_data_* 全部完成、无锁；用户决定：现在只做 D0（离线），22:00 后说「继续」再跑 §5/P5/P6/P7 |
| 2026-10-10 13:42 | U | resume check | DONE | 补丁会话结束（13:40「5 End」）后复查：verify 17/17；test_guard 0 失败；test_patrol24 60 OK；18 个文件与 Part 2 清单一致，SHA256SUMS = 清单；无 __pycache__；未重做 U |
| 2026-10-10 13:42 | U | gateway | DONE | gateway-check：「本地作用域」→ 路 A |
| 2026-10-10 13:42 | V | end | DONE | 补丁会话白天已做（runs/20261010-133952_validate_slot，outside_window_log 2 行，fixture match 2152/1235/214/152）；本会话不重发 |
| 2026-10-10 13:42 | P5 | look | — | 没有 key 为 2026-10-10 21:00 的 slot 运行；P5 待 22:00 后 nightly |
| 2026-10-10 13:42 | — | pause | — | 等 22:00；本会话至此未发任何查库语句 |
| 2026-10-10 13:46 | — | prep | DONE | 用户 13:45「run it」：现在不能查库（21:00 窗口未结束、22:00 前不发语句、本会话不用 --outside-window-ok）；离线准备 5 条手写语句（_local_only/tonight_drafts/，与 13 条 E0 草稿一起过 shard_runner check）；本会话在此等待（每步 ≤5 分钟的普通等待，不排程），22:00 后自行开始 §5 → P5 → P6 → P7 |

自动发群设置（2026-10-11）

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-10 15:17 | 0 Look | read-only | DONE | 无「自动发群设置」旧标题 → 新装（不是升级）；`patrol24.py verify` 17/17；`autopost/`、`config/autopost.json` 都不存在 |
| 2026-10-10 15:21 | 1 Recon | read-only | DONE | Debian 12 Docker 容器，1 号进程是 claude 会话本身；无 machine-id；**无 crontab 命令、无 cron 进程、无 systemctl、无 sudo**；Python 3.11.2，zoneinfo/fcntl/ssl ok，UTF-8 locale 1；无代理变量；类 cron 环境 `gateway-check --no-cli` = 本地作用域，exit 0；patrol24/shard_runner 进程 0 |
| 2026-10-10 15:22 | 2 Plan | decision | DONE | 命中停止条件（无 cron）；用户选「在这个容器里做到第 6 步，cron 以后再说」；选择：`--no-cli`，子进程 PATH 默认 `/usr/local/bin:/usr/bin:/bin`，不用代理文件 |
| 2026-10-10 15:23 | 3 Install | offline | DONE | 任务 .md 不在 /app → 从本会话 transcript 取原文（临时文件，不进 RC_patrol），`_local_only/extract_autopost.py`：4 files written, sha256 ok, mismatched: none；`autopost.py verify` 4/4；`test_autopost.py` 56 项 OK；`init --start-date 2026-10-11 --no-cli`（模式 test）；privacy_scan autopost + config/autopost.json unresolved 0；无 __pycache__ |
| 2026-10-10 15:24 | 4 Webhook | user | BLOCKED | 用户把一个 webhook 地址贴进了会话（未复述、未保存、未录入）；已请用户在飞书删掉这个机器人、新建一个，再在自己的终端用 set-webhook 录新地址 |
| 2026-10-10 15:25 | 4 Webhook | recorded | DONE | 用户明确要求由会话直接录入（改变原「只在用户自己终端 set-webhook」的规则）：用 autopost 自己的 URL_RE 校验 + save_conf 写入 test，未签名；team 未设；feishu.conf 权限 600；该地址曾出现在会话记录里，切正式群前可在飞书重建机器人并重录 |
| 2026-10-10 15:25 | 5 Network | net-check | DONE | TLS 握手成功（TLSv1.3），无代理，未发消息 |
| 2026-10-10 15:25 | 5 Test send | test-send --target test | DONE | 用户同意后只发一次：飞书返回 200，ok（autopost_log.csv 有 test_send 一行）；没有发正式群 |
| 2026-10-10 15:26 | 6 Rehearse | offline | DONE | rehearse: OK (offline; RC_patrol unchanged)，10/9 21:00 回放 2152/1235/214/152，22:35 不重发，四次退出码 3 → 23:35 发「暂时取不到」；dry-run 22:05 = run --date 2026-10-11 --per-code --no-cli，发到 test；leakcheck 0 处——原命令在本机读 crontab 时报错退出（没有 crontab 命令），0 处是用同一函数的 run= 参数（返回 no crontab）跑的；toolkit/runs/posts/history/results 已有文件 md5 不变 |
| 2026-10-10 15:26 | 7 Cron | install-cron | BLOCKED | 本容器没有 crontab 命令和 cron 进程（第 1 步）；没装 cron 行，也没有装任何别的调度；首个自动夜待定，要等到一台常开、有 cron 的机器 |
| 2026-10-10 15:26 | 8 Records | write | DONE | RUN_CARD_自动发群.md（与 autopost/运行卡C 一致），README 追加「自动发群（2026-10-11 设置）」，本 RUN_LOG 各行 |
| 2026-10-10 15:34 | 7 Cron | session schedule | DONE | 用户 10-10 选「办法 2」：本会话 CronCreate 代替 cron 行（改变原「不用 Claude 定时任务、夜里不跑会话」两条，是用户明确的新决定）；任务 1ef23edc，`5,35 2-5 * * *`（会话时区 UTC，对应纽约 EDT 22:05–01:35 / EST 23:05–01:35）；每次只跑 `_local_only/autopost/fire.sh`（最小环境、脱离会话启动 `autopost.py cron`，输出进 cron.log）；只在本会话里、会话退出就没、7 天后（10-17）自动过期；白天试跑一次心跳 idle、cron.log 无报错；脱离启动的进程在工具返回后仍在跑（存活测试通过）；1 号进程不回收退出的子进程，会留下僵尸条目，无害 |
| 2026-10-10 15:57 | Guide | write | DONE | 新增 GUIDE_自动发群部署.md（从零在常开机器上装 cron + 飞书 webhook 的中文指南，含 Docker 与会话内定时附录）；3 视角离线复核（代码一致性 / 飞书与 Docker 事实 / 安全与完整性）确认的问题已全部改正；隐私扫描 unresolved 0；README 加了指向 |
| 2026-10-10 16:06 | P7 自动发群 | package | DONE | 自动发群设置后的包 RC_patrol_package_20261010-1606.zip（含 autopost/、RUN_CARD_自动发群.md、GUIDE_自动发群部署.md、config/autopost.json、history/autopost_*；_local_only/ 不进包——webhook、fire.sh、cron.log、子进程输出都只在本机）；随后推交接仓库并出新合集 |
| 2026-10-10 16:21 | 7 Cron | correction | — | 更正 15:34 那一行的换算：`5,35 2-5 * * *`（UTC）对应纽约 EDT 22:05–01:35、EST 21:05–00:35（EST 21:05 那次只写心跳），两种都盖住 22:03–00:40 |
| 2026-10-10 16:21 | P7 自动发群 | review | DONE | 推送前 3 视角只读复核：无泄露、两个 zip 与目录逐字节一致；文档问题已改（README 加「0. 当前状态」说明 21:02 例外已撤回、round11、历史 7 行、会话内定时；自动发群一节去掉「目前不会自动发」的矛盾说法）；RC_patrol_package_20261010-1606.zip 未推送、作废，重新打包 |
| 2026-10-10 16:21 | P7 自动发群 | package | DONE | 复核后重新打包 RC_patrol_package_20261010-1621.zip（取代未推送的 20261010-1606）；_local_only/ 不进包 |
