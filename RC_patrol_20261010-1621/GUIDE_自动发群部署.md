# 21 点短信巡检 · 自动发飞书群部署指南（cron + 飞书 webhook）

适用：`RC_patrol/autopost/autopost.py`（2026-10-10 版，`autopost.py verify` 4/4）。
目标：在一台**常开**的机器上用 cron 每晚自动取 21:00 那一段的巡检数，自己核对后发到飞书群；取不到就发一句固定的话。

---

## 0. 它每晚做什么

- 处理的是纽约日期 D 那天 21:00 截止的 24 小时。服务器时区、夏令时都不用管，程序按纽约时间自己算。
- cron 每小时 :05 和 :35 叫一次 `autopost.py cron`。只有纽约 22:03 到次日 00:40 之间才会做事，其余时间只写心跳。

| 纽约时间 | 动作 |
|---|---|
| 22:05 | 第 1 次：跑 `toolkit/patrol24.py run --date D --per-code`（就是运行卡 A 那条命令）。它说「可以发。」以后，autopost 再自己核一遍，过了就发群 |
| 22:35、23:05 | 上一次是可重试的失败（锁、服务器忙、网关连不上）才再试；两次尝试至少隔 24 分钟 |
| 23:35 | 最后一次。还不行，就发「暂时取不到」那句 |
| 23:40–00:39 | 不碰数据库。23:35 那句没发成的话，只补发那一句 |
| 00:40 以后 | 记 `gave_up`，不再管这一段 |

- 核对没过、查询报错、超时、隐私扫描没过、找不到网关：不再重试，**当场**发「暂时取不到」。
- 「暂时取不到」的原文（标题照常，没有数字）：
  ```
  北美短信例行巡检（纽约时间 M/D 21:00）
  今晚21点的巡检数暂时取不到，弄好后补发。
  ```
- 安全规则（程序里写死）：
  - 同一段绝不发两次（同一份 `RC_patrol/` 之内）。
  - 结果不确定（飞书没回，或返回 5xx）就不重发。
  - 有人手动跑过这一段，就不发（由你自己发）。
  - 每个群每天自动发送最多 3 次。
  - 不会带 `--m1-active-ok`、`--force`、`--outside-window-ok`。
  - 查库的时段（22:00–05:30）、负载检查、EXPLAIN、守卫、隐私扫描，都由 patrol24 自己管。

**整体步骤**：

1. 定用户、查机器
2. 放文件、校验
3. 网关配置
4. `init`
5. 建飞书机器人
6. 录地址
7. 网络检查
8. 测试消息
9. 离线演练
10. **停掉旧的运行方**
11. 装 cron
12. 测试群跑 2–3 晚
13. 切正式群

> 下面的命令都在**运行目录**（`RC_patrol/` 的上一级，例如 `/app`）里跑，先 `export PYTHONDONTWRITEBYTECODE=1`。

---

## 1. 定用户、查机器

**先定一个用户。** 从头到尾所有命令都用将来跑 cron 的那个用户执行：检查、`init`、`set-webhook`、`install-cron`、`status`，都直接登录该用户，或用 `sudo -u <用户> -H -i`。

不要混用 root 和别的账号，因为：

- `install-cron` 写的是**当前用户**的 crontab；
- `init` 记下的是当前用户的 HOME 和 python，网关配置就在这个 HOME 里找；
- `feishu.conf` 不属于跑 cron 的用户，每次都会被拒。

| 检查 | 命令 | 要看到 |
|---|---|---|
| 机器常开，不是跟着某个会话起停的容器 | `cat /proc/1/comm`；`uptime` | 1 号进程是 `systemd` / `init` / `cron` 这类，不是 `claude` 或一个 shell |
| 有 crontab | `command -v crontab` | 打印出路径 |
| cron 在跑 | `pgrep -x cron \|\| pgrep -x crond` | 打印出进程号 |
| Python ≥ 3.9 | `python3 -V` | 3.9 或更高 |
| 时区库等模块 | `python3 -c "from zoneinfo import ZoneInfo; ZoneInfo('America/New_York'); import fcntl, ssl; print('ok')"` | `ok`（报错多半是缺系统时区库，要装 tzdata） |
| 时钟准 | `date -u`；`TZ=America/New_York date` | 和手机时间一致（时区设成什么都行，时间本身要准；差 1 小时以上签名会失败） |
| 代理 | `env \| cut -d= -f1 \| grep -i proxy` | 只看变量名。cron 里的程序**不会**带上这些变量：连飞书要代理按第 7 步写代理文件；查库的子进程也不走代理，网关要能直连 |

---

## 2. 放文件、校验

1. 把整个 `RC_patrol/` 放到运行目录下。
   - **要在纽约 22:00–05:30 之外拷**。
   - 换机器时要一起拷：`toolkit/`、`config/`、`history/`、`_local_only/reserved_words.txt`。
   - 还要拷 `runs/`，至少一个存了**完整 21:00 窗口回复**的运行目录（第 9 步 `rehearse` 要用；没有它，演练会报「没找到保存了某个 21:00 窗口全部回复的运行目录」）。
   - **不要拷**：
     - `_local_only/feishu.conf`：到新机器上重新录；
     - `_local_only/.db_lock`：拷过去以后，每次都会退出码 3（锁文件还在），每晚发「暂时取不到」。
2. `chown -R <cron 用户> RC_patrol`。
3. 校验和离线测试（不连库、不联网）：
   ```
   export PYTHONDONTWRITEBYTECODE=1
   python3 RC_patrol/toolkit/patrol24.py verify          # toolkit sha256: 17/17 match
   python3 -B RC_patrol/autopost/autopost.py verify      # autopost sha256: 4/4 match
   python3 -B RC_patrol/autopost/test_autopost.py        # 最后是 OK（56 项）
   ```
   哪一项不对，就先别往下做。`autopost/` 只放代码，升级时整个目录换掉；`config/`、`history/`、`_local_only/` 要保留。

---

## 3. 网关配置（路 A 查库要用）

autopost 叫的子进程靠 Claude Code 的配置找数据库网关（`mcp-db-gateway`）。认可的位置有：

- **本地作用域**：`~/.claude.json` 里运行目录（或它所在 git 仓库根目录）那一项下的配置；
- **用户作用域**：`~/.claude.json` 顶层的配置；
- **项目 `.mcp.json`**：只有当 `~/.claude.json` 里该项目的 `enabledMcpjsonServers` 列出了 `mcp-db-gateway` 才算。用 `.claude/settings*.json` 批准的（例如 `enableAllProjectMcpServers`）**不算**；
- `claude mcp get` 兜底：只在**不加** `--no-cli` 时用。

不认的：环境变量 `MCP_DB_GATEWAY_SSE`（子进程的环境是固定的几项，不带它）。

条目要求：类型 sse，不需要 headers，地址里没有 `${…}` 变量。

1. 新机器上还没有，就用 cron 用户装好 Claude Code，在运行目录里加一条：
   ```
   claude mcp add --transport sse --scope user mcp-db-gateway <网关 SSE 地址>
   ```
   - `--scope user` 也可以换成本地作用域，在运行目录里加。
   - 网关地址找管理员私下要，不要贴进聊天、文档、工单、git；注意别留在 shell 历史里。
2. 用和 cron 一样的最小环境检查（不联网，只看配置在不在）：
   ```
   env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 $(command -v python3) -B RC_patrol/toolkit/patrol24.py gateway-check --no-cli; echo "exit $?"
   ```
   要看到 `exit 0`，说明里有「路 A 可用」。exit 8 就换不带 `--no-cli`、把 claude 和 node 所在目录加进 PATH 再试：
   ```
   env -i HOME="$HOME" PATH="$(dirname "$(command -v claude)"):$(dirname "$(command -v node)"):/usr/bin:/bin" LANG=C.UTF-8 \
     $(command -v python3) -B RC_patrol/toolkit/patrol24.py gateway-check; echo "exit $?"
   ```
   两种都不是 0，这台机器晚上没法自动查库，不要在这里装。记下是哪一种过的，第 4 步要用。
3. 可选：提前确认真能连上库。`gateway-check` 不测网络，所以在开始日期的**前一晚** 22:00–05:15 用同样的最小环境跑一次更早一段：
   ```
   env -i HOME="$HOME" PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 $(command -v python3) -B RC_patrol/toolkit/patrol24.py run --date <开始日期的前一天> --per-code --no-cli
   ```
   - 上面第 2 条是不带 `--no-cli` 那种过的：去掉 `--no-cli`，并用那一种的 PATH。
   - 这只会给那一段记一行，不影响自动发送的那一晚。

---

## 4. 初始化 `init`

```
python3 -B RC_patrol/autopost/autopost.py init --start-date 2026-10-11 --no-cli
```

- `--start-date`：第一个自动处理的纽约日期，也就是那天 21:00 截止的那一段。
- `--no-cli`：第 3 步是不带 CLI 那种过的就加；否则不加（`init` 会自动把 claude 和 node 所在目录加进子进程的 PATH）。
- 可选参数：
  - `--python`：默认是跑 `init` 的这个 python；
  - `--child-path`：子进程 PATH，默认 `/usr/local/bin:/usr/bin:/bin`；
  - `--lang`：默认 `C.UTF-8`。
- 写出 `config/autopost.json`：开关、模式 test、起始日期、本机标识，以及子进程用的 python / PATH / HOME。这一步会把 `_local_only/` 改成 700。
- **已经初始化过（例如拷来的配置）还要重来**：`init --reinit --start-date <D> [--no-cli] …`。它会整份重写：
  - 开关重新打开（之前 `disable` 过的也会被打开）；
  - 模式回到 test，跳过的日期清空；
  - 本机标识换成这台；
  - `--no-cli` / `--python` / `--child-path` / `--lang` 按这次给的参数重设，所以第一次带过的参数要再带一遍；
  - webhook 不受影响。
- **换了机器或容器，只在同时满足下面三条时，跑 `adopt-host` 就够了**（它只换本机标识）：
  - 路径、python、HOME 都没变；
  - 第 3 步的结论和原配置一致（原来是 `--no-cli`，这台也是不带 CLI 那种过的）；
  - 否则用上面的 `--reinit`。

  事后用 `dry-run`（第 9 步）看子进程命令是否带了你想要的 `--no-cli`。

---

## 5. 建飞书群机器人

测试群、正式群各建一个**自定义机器人**，两个地址不能相同。

1. 打开群 → 右上角「设置」→「群机器人」→「添加机器人」→「自定义机器人」→ 起个名字（例如「短信巡检」）。
2. 安全设置，任选其一或组合：
   - **自定义关键词**：填 `巡检`。推荐，最简单。程序发的三种消息（巡检结果、「暂时取不到」、测试消息）都含「巡检」两个字。
   - **签名校验**：打开后会给一个密钥，录地址时加 `--secret` 一起录。
   - **IP 白名单**：只在机器出口 IP 固定时用。
3. 复制 webhook 地址。格式是 `https://open.feishu.cn/open-apis/bot/v2/hook/` 后面跟一串 36 位小写标识；只支持 `open.feishu.cn`。

> 🔴 地址等于群的发言权：谁拿到都能往群里发消息。
> - 不要贴进任何聊天、文档、工单或 git。
> - 万一泄露：删掉这个机器人、重建一个（飞书改不了地址），再按第 6 步重录。

---

## 6. 录地址（cron 用户自己的交互终端）

```
python3 -B RC_patrol/autopost/autopost.py set-webhook --target test
python3 -B RC_patrol/autopost/autopost.py set-webhook --target team     # 正式群可以等到切换前再录
```

- 提示「… webhook 地址（输入不显示）：」时粘贴地址、回车。开了签名校验的，命令加 `--secret`，会再问一次密钥。
- 成功时显示「test：已保存（指纹 xxxxxxxx，签名：无）」。地址只存进 `_local_only/feishu.conf`（权限 600），任何输出、日志、打包里都不出现。
- 命令要求真终端（TTY）。在没有 TTY 的地方跑（脚本、`!` 前缀、管道）会被拒绝，这是故意的。
- 删除某个地址：`forget-webhook --target test|team`。
- 检查：
  ```
  python3 -B RC_patrol/autopost/autopost.py status            # webhook test：已设（指纹 …，签名 无）；feishu.conf 权限：正常；本机：一致
  stat -c '%U %a' RC_patrol/_local_only/feishu.conf            # <cron 用户> 600（macOS：stat -f '%Su %Lp' …）
  ```

---

## 7. 网络检查

```
python3 -B RC_patrol/autopost/autopost.py net-check
```

- 只和飞书做一次 TLS 握手，不发消息。正常时显示「TLS 握手：成功（TLSv1.3，… ms）；没有发任何消息。」
- 连不上，需要代理：自己写文件 `RC_patrol/_local_only/autopost/feishu_proxy`，内容一行 `https_proxy=http://代理主机:端口`。它只用于连飞书，不会给查库的子进程用。写好再跑一次 `net-check`。
- 证书校验失败：程序不会关掉校验。补装系统 CA 证书由你决定。

---

## 8. 发一条测试消息（只能发测试群）

```
python3 -B RC_patrol/autopost/autopost.py test-send --target test
```

内容固定：「北美短信例行巡检：自动发送测试（只发到测试群，不是巡检结果）。」

| 显示 | 意思 | 怎么办 |
|---|---|---|
| `测试消息：ok（已发）` | 成功 | 去群里看一眼 |
| `rejected（缺关键词）`（19024） | 关键词里没有「巡检」 | 机器人设置里加关键词「巡检」，或去掉关键词 |
| `rejected（签名不对或时间差超过1小时）`（19021） | 签名开关和录入不一致，或机器时钟差太多 | 用 / 不用 `--secret` 重录；校准时钟 |
| `rejected（IP 不在白名单）`（19022） | 出口 IP 不在白名单里 | 改白名单，或去掉 IP 限制 |
| `rejected（webhook 无效…）`（19001） | 地址错了，或机器人已删除 / 重建 | 重录地址 |
| `rejected（请求格式不对）`（9499） | 飞书判定请求有误（程序发的格式固定，一般不会出现） | 看 `_local_only/autopost/last_response.txt`（已脱敏） |
| `retry（retry）` | 没发出去：连不上飞书，或被限流（11232） | 看 `last_response.txt`（注意文件时间是不是刚才）：刚写的、含 11232 就过一会儿再试；没更新就是连接问题，回到第 7 步 |
| `uncertain（uncertain）` | 发出去了但没收到正常回复 | 先看群里有没有，再查网络 |

---

## 9. 离线演练（不连库、不发群）

```
python3 -B RC_patrol/autopost/autopost.py rehearse
python3 -B RC_patrol/autopost/autopost.py dry-run --at "2026-10-11 22:05"
python3 -B RC_patrol/autopost/autopost.py leakcheck
```

- **`rehearse`**：在临时目录里，用 `runs/` 里最近一次已存回复的 21:00 窗口，真跑一遍 patrol24 + autopost，发送是假的。
  - 要看到三件事：①发出的文字；②22:35 那次不重发；③另一晚连续 4 次退出码 3 后，23:35 发了「暂时取不到」。
  - 最后一行必须是 `rehearse: OK (offline; RC_patrol unchanged)`。
- **`dry-run`**：显示那一刻会跑的子进程命令。应为 `… patrol24.py run --date 2026-10-11 --per-code`，按第 4 步的选择带或不带 `--no-cli`；还会显示「发到：test」。
- **`leakcheck`**：在 `RC_patrol/` 和 crontab 里找地址或密钥，要 `0 处`。
  - 已知问题：机器上**没有 `crontab` 命令**时，它读 crontab 会报错退出。正常装了 cron 的机器不受影响。

---

## 10. 停掉旧的运行方（换机器时必做，装 cron 之前，最晚在开始日期 22:03 前）

「同一段只发一次」靠的是**同一份 `RC_patrol/`** 里的锁和状态文件，管不到另一份拷贝。如果别处还有一份 autopost 在跑（例如附录 B 的会话内定时），要先停掉它。

- **新机器用的是另一份拷贝**（按第 2 步拷过去的）：
  1. 在旧的那份里跑 `python3 -B RC_patrol/autopost/autopost.py disable`，再看它的 `status`，要显示「自动发群：关」；
  2. 删掉旧的定时（会话内定时：在那个会话里删掉定时任务，或结束会话；旧机器的 cron：在旧机器上 `uninstall-cron`）。
  
  不停的话，两边每晚都会查一次库、各发一次群。
- **新运行方和旧的共用同一个目录**（同一份 `config/autopost.json`）：**不要** `disable`，否则新的也一起关了。只删旧的定时。新机器 `init` / `adopt-host` 以后，旧的触发只会记 `other_host`、什么都不做，所以这种情况下漏删也不会重发。

另外：换到另一台机器以后，patrol24 的「另一个查库任务在跑」（退出码 3）只看得到**本机**的数据包运行，看不到旧机器上的 RC_data 包。有计划在晚上跑包的那天，白天先 `skip --date D`，或者让包在同一台机器、同一个运行目录里跑。

---

## 11. 装 cron

```
python3 -B RC_patrol/autopost/autopost.py cron-line       # 先看一眼要装的那一行
python3 -B RC_patrol/autopost/autopost.py install-cron    # 装（cron 用户）
crontab -l | grep -c 'RC_patrol-autopost'                 # 应为 1
```

- 装上的那一行形如：
  ```
  5,35 * * * * cd <运行目录> && <python> -B <运行目录>/RC_patrol/autopost/autopost.py cron >> <运行目录>/RC_patrol/_local_only/autopost/cron.log 2>&1 # RC_patrol-autopost
  ```
- `install-cron` 只增删以 `# RC_patrol-autopost` 结尾的那一行，其他行一字不动。
  - 装之前会把原 crontab 备份到 `_local_only/autopost/crontab_backup_<时间>.txt`。
  - 装完会读回核对；不对就报错，并让你自己 `crontab -e` 看。
- 路径里有 `%` 会被拒绝，因为 cron 会把 `%` 当换行。
- 想手工装也可以：把 `cron-line` 打印的那一行原样加进 `crontab -e`。
- 装好以后，过了下一个 :05 或 :35，跑 `status`，应看到「cron：已装」和一个新的心跳。心跳括号里的说明：

  | 心跳里的说明 | 什么时候出现 |
  |---|---|
  | `idle` | 白天（纽约 05:30–21:30） |
  | `gated` | 夜里，但这一段早于起始日期，或已 `disable` / `skip` |
  | `<D> pending` 等 | 生效的那一晚，正在处理 |

  这三种都正常。cron 每半小时写一次心跳，**超过 40 分钟没更新就是 cron 没在跑**。

---

## 12. 测试期（2–3 晚）

- 每晚 22:06 左右，结果发到**测试群**。
- 这几晚**不要手动跑 `nightly` / `run`** 去取同一段：手动跑过，autopost 就不发了（状态 `manual_skip`）。
- 正式群照旧手动发：从测试群复制那段文字。
- 第二天白天跑 `status`，前一晚那一段应是 `posted`。不是的话看第 14、16 节。
- 某一晚想完全自己来：白天先 `skip --date <那天的纽约日期>`。

---

## 13. 切到正式群

白天做（纽约 21:30–次日 00:40 之间会被拒绝）：

```
python3 -B RC_patrol/autopost/autopost.py set-webhook --target team    # cron 用户自己的终端；没录过才需要
python3 -B RC_patrol/autopost/autopost.py set-mode team
```

- 要求测试群至少成功发过 2 晚（`posted`），否则拒绝。确有需要可加 `--force`，不推荐。
- 每一段第一次动作（22:03 以后）就定下发往哪个群，已经开始的那一段不跟着变。
- 切回测试群：`set-mode test`。

---

## 14. 日常怎么看

`status` 会显示：开关、模式、起始日期、跳过的日期；两个 webhook 是否已设（只显示指纹）；`feishu.conf` 权限；本机是否一致；心跳；cron 是否已装；最近 7 段的结果。

| 状态 | 意思 | 怎么办 |
|---|---|---|
| `posted` | 已自动发出 | 不用管 |
| `reposted` | 手动 `send-post` 补发成功 | 不用管（不会再发） |
| `failline_posted` | 发了「暂时取不到」 | 看 `_local_only/autopost/child/<D>_tryN.txt` 找原因；修好后按第 15 节补发 |
| `manual_skip` | 有人手动跑过这一段，没自动发 | 自己发（运行卡 A 那段文字） |
| `send_uncertain` | 发出去了但飞书没回话 | 先看群里有没有；确实没有，再 `send-post --date D --resend-uncertain` |
| `send_rejected` | 飞书拒收（原因见 `history/autopost_log.csv` 的说明） | 改机器人设置或重录地址，然后补发 |
| `gave_up` | 到 00:40 也没发出去 | 同 `failline_posted` |
| `manual_send_retry` | 手动 `send-post` 时飞书没连上 | 过一会儿再跑一次 `send-post` |

子进程（patrol24）的退出码，autopost 这样处理：

| 退出码 | 意思 | autopost 怎么做 |
|---|---|---|
| 0，最后一行「可以发。」 | 正常 | 自己再核一遍，过了就发 |
| 2 | 太早或不在时段 | 不算次数，下次再试 |
| 3 | 另一个查库任务在跑，或锁文件还在 | 下次再试；到 23:35 还不行就发「暂时取不到」 |
| 7 | 服务器忙 | 第 3 次还是 7 就停，发「暂时取不到」 |
| 5（gateway connect failed） | 一条也没发出去 | 下次再试 |
| 5（其他） | 查询失败 | 不再试，马上发「暂时取不到」 |
| 4 / 6 / 8 / 其他 / 超时 20 分钟 | 核对没过 / 隐私扫描不干净 / 找不到网关 / 意外 | 不再试，马上发「暂时取不到」 |

数据延迟：最后一条请求比截止时间早超过 10 分钟，只在截止后 30 分钟内跑的那次算「延迟」。最后整整一小时一条请求都没有，才当作日志源停了（重试，到 23:35 发「暂时取不到」）。

---

## 15. 常用操作

```
python3 -B RC_patrol/autopost/autopost.py skip --date 2026-10-12      # 这一晚不自动发；unskip 取消
python3 -B RC_patrol/autopost/autopost.py disable                     # 全部暂停；enable 恢复
python3 -B RC_patrol/autopost/autopost.py set-start --date 2026-10-15 # 改起始日期
python3 -B RC_patrol/autopost/autopost.py uninstall-cron              # 连 cron 行一起删（同样先备份）
```

**补发**（某晚是 `failline_posted` / `gave_up`，修好以后）：

1. 在纽约 22:00–05:15 跑：
   ```
   python3 RC_patrol/toolkit/patrol24.py run --date D --per-code [--no-cli]
   ```
   看到「可以发。」再往下。
2. 跑：
   ```
   python3 -B RC_patrol/autopost/autopost.py send-post --date D
   ```
   它会把文字给你看，要你输入「发送」确认。等你确认时不占锁，不挡自动发送。成功后状态变成 `reposted`。
3. 那一晚最后一小时完全没有请求时，它会报「数据延迟」。你确认数没问题，再加 `--accept-lag`。
4. 那一段还在自动处理中（纽约 21:30–次日 00:40，且还没有最终结果）时不能手动 `send-post`：等它有结果，或先 `skip` 这一天。

---

## 16. 故障排查

| 现象 | 看哪里 / 怎么办 |
|---|---|
| 心跳超过 40 分钟 | cron 没跑：`pgrep -x cron`、`crontab -l`（cron 用户）、`_local_only/autopost/cron.log` |
| 日志里 `other_host` | 换了机器或容器（本机标识 = 主机名 + machine-id）：确认这台就是要跑的机器，再按第 4 步 `adopt-host` 或 `--reinit` |
| 「feishu.conf 的权限不对」 | `chmod 600 RC_patrol/_local_only/feishu.conf`，而且文件要属于跑 cron 的用户 |
| 每晚都是退出码 3（锁文件还在） | 确认没有 patrol24 / shard_runner 在跑（`ps`），再删 `_local_only/.db_lock` |
| 每晚都是退出码 8 | 网关配置没找到：按第 3 步用最小环境重查 |
| `no_webhook` | 这个群没录地址：第 6 步 |
| `cap` | 当天自动发送已到 3 次上限 |
| `crash` | `_local_only/autopost/last_error.txt`（已脱敏） |
| `overlap` | 上一次还没跑完，这次没动（正常） |
| `child_running` | 上一次的 patrol24 子进程还在跑，这次没动（正常） |
| 飞书返回什么 | `_local_only/autopost/last_response.txt`（已脱敏） |

文件位置：

| 位置 | 内容 |
|---|---|
| `history/autopost_log.csv` | 流水：每次尝试、发送、跳过，固定说法，不含地址 |
| `history/autopost_state/<D>.json` | 每一段的状态：尝试次数、退出码、发了什么 |
| `_local_only/autopost/child/` | 每次子进程的完整输出 |
| `_local_only/autopost/cron.log` | cron 的输出（超过 1MB 自动截短） |
| `_local_only/autopost/heartbeat.json` | 心跳 |

---

## 附录 A：机器是 Docker 时

- 会话式容器不行：如果容器的 1 号进程是 Claude 会话或一个交互 shell，会话一关容器就停，cron 和后台程序都跟着停。
- 另外，这类容器常常没有 cron，也没有 root 权限去装。

两个可行的做法：

1. **宿主机 cron 调一个常驻容器**：
   ```
   5,35 * * * * docker exec -u <uid> -w /app <常驻容器名> /usr/bin/python3 -B /app/RC_patrol/autopost/autopost.py cron >> <宿主机上的日志文件> 2>&1
   ```
   - 那个容器要一直开着，且不重建，否则本机标识会变。
   - 容器里要能通过第 3 步的网关检查。
2. **单独一个常驻容器，不用宿主机 cron**：用同一个镜像，`restart: unless-stopped`，1 号进程是一个「每到 :05 / :35 就跑一次 `autopost.py cron`」的循环脚本。
   - 固定 `hostname:`：没有 machine-id 时，本机标识只靠主机名。
   - `init: true`。
   - 用户与文件属主一致（同一个 uid）。
   - `/app` 挂同一个目录。
   - 让容器里的 `~/.claude.json` 带有网关配置（例如只读挂进去），并在容器里确认第 3 步的检查 exit 0。
   - 起来后在容器里跑一次 `adopt-host`（条件见第 4 步）。

   循环脚本示例：
   ```bash
   #!/bin/bash
   # 每到 :05 和 :35 跑一次 autopost.py cron（与 cron 行相同）
   cd /app || exit 1
   while true; do
     now=$(date +%s); m=$(( now / 60 % 60 )); s=$(( now % 60 ))
     if   (( m < 5 ));  then w=$(( (5 - m) * 60 - s ))
     elif (( m < 35 )); then w=$(( (35 - m) * 60 - s ))
     else                    w=$(( (65 - m) * 60 - s )); fi
     sleep "$w"
     /usr/bin/python3 -B /app/RC_patrol/autopost/autopost.py cron >> /app/RC_patrol/_local_only/autopost/cron.log 2>&1
   done
   ```

## 附录 B：现在在用的「会话内定时」（2026-10-10 起，过渡用）

- 在装 autopost 的那个 Claude 会话里，建了一个定时任务：`5,35 2-5 * * *`，会话时区是 UTC，盖住纽约 22:03–00:40。
- 每次只跑 `RC_patrol/_local_only/autopost/fire.sh`：它用和 cron 行一样的最小环境，脱离会话启动一次 `autopost.py cron`，结果进 `cron.log`。
- 限制：
  - 会话一退出（或终端关掉）就没了；
  - 只在会话空闲时触发；
  - 7 天后自动过期（10-17）；
  - 只在夜里触发，所以白天 `status` 的心跳超过 40 分钟是正常的。
- 换成真正的 cron 时，按**第 10 节**处理：
  - 新机器用的是另一份拷贝：必须先删掉这个定时任务（或结束会话），并在这里 `disable`；
  - 共用同一个 `/app` 目录：只删定时任务，不要 `disable`。
