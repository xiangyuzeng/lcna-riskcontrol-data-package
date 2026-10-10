# 每晚短信巡检 · 运行卡（统计到 21:00 为止的 24 小时，22:00 以后跑）

给人看的：生产库只能在纽约时间 22:00–05:30 取数，所以 21 点那一段的数 22:00 以后查、大约 22:05 发；统计的仍是到 21:00 为止的 24 小时。

## A. 一条命令（默认）

在能连风控库的那台机器上，到放 `RC_patrol/` 的运行目录，22:00 以后跑：

```
PYTHONDONTWRITEBYTECODE=1 python3 RC_patrol/toolkit/patrol24.py nightly
```

最后屏幕上"复制下面这段发群"到"到这里"之间的文字，就是要发群的内容（同样的文字也在 `RC_patrol/posts/巡检_<日期>_2100.txt`），由你自己发。

| 退出码 | 意思 | 怎么办 |
|---|---|---|
| 0，最后一行"可以发。" | 正常 | 复制两条分隔线之间的文字发群 |
| 2 | 太早，或不在 22:00–05:30（05:15 以后也不再开始） | 按提示的时间再跑 |
| 3 | 另一个查库任务像是在跑，或 `RC_patrol/_local_only/.db_lock` 还在 | 看提示：说的是锁文件，先用 `ps` 确认没有 patrol24 在跑，再删这个锁文件重跑；说的是别的任务，确认没问题后加 `--m1-active-ok` 再跑 |
| 7 | 服务器忙 | 20 分钟后再试，最多两次 |
| 8 | 找不到可用的网关配置 | 用下面的 B |
| 5，提示里有 gateway connect failed | 一条语句也没发出去 | 用下面的 B |
| 5，其他（超时或报错） | 查询失败 | 不要发，也不要原样再跑；在群里说一句，第二天再看 |
| 4 / 6 | 核对没过 / 隐私扫描不干净 | 不要发；把提示留着给我看 |
| 其他（比如 1，或屏幕上是 Traceback） | 意外错误 | 不要发；用 B，或在群里说一句 |

过了午夜、05:15 以前跑上面那条命令，取的仍是前一晚 21:00 那一段。要补更早的某一晚：在 22:00–05:15 里跑 `PYTHONDONTWRITEBYTECODE=1 python3 RC_patrol/toolkit/patrol24.py run --date <那一晚的纽约日期> --per-code`。

如果当晚跑不了，群里只替自己说一句，例如：今晚21点的巡检数暂时取不到（原因），弄好后补发。

## B. 备用：在 Claude Code 会话里跑

在运行目录（`claude mcp list` 能看到 mcp-db-gateway 已连接的那个目录）用普通模式开 Claude Code（`claude`，不要 plan 模式），22:00 以后把下面整段粘贴进去。每条查库语句它会请你批准，大约 12 条。

---

This is the nightly run of the 21:00 New York SMS inspection that was set up in `RC_patrol/`, done through the MCP tool (path B). Do exactly the steps below and nothing else. Database access is read-only, only through the mcp-db-gateway query tool on server `aws-luckyus-iriskcontrolservice-rw`, one statement at a time, and only between 22:00 and 05:30 New York time. Never open MCP configuration files or look for the gateway address anywhere, never edit a statement or a reply by hand, never query anything not listed here, never post or send anything, never schedule anything.

1. Run `cd RC_patrol && export PYTHONDONTWRITEBYTECODE=1 && python3 toolkit/patrol24.py verify`. It must print `N/N match`. Otherwise stop and show me the output.
2. Run `python3 toolkit/patrol24.py emit --per-code`. If it prints a line starting with `note: 现在纽约时间`, tell me the time it shows and stop; send nothing.
   - Exit 2 ("还没到时间"): tell me the time it prints and stop. Never add `--date` or `--force` on your own; a past evening is posted only if I ask for it by date.
   - Exit 3 (another database run may be active): show me its reasons and ask me whether to continue. Only after I say yes, run it again with `--m1-active-ok` added.
   - It prints the run directory, for example `runs/20261010-220312_slot`. Use that directory below.
3. Send `s0a_processlist.sql`, `s0b_threads.sql`, `s0c_shards.sql` and `s0d_explain.sql`, in that order, one query-tool call at a time (wait until the reply is saved before sending the next). For each one, read the file and send its SQL exactly as written with the query tool, then save the tool's reply exactly as returned (the JSON text, unchanged) as a file with the same name and `.json` instead of `.sql`, in the same directory.
4. Run `python3 toolkit/patrol24.py gate <run dir>`.
   - GO: continue.
   - LATE (before 22:00, or 05:15 or later — no new database work starts after 05:15): tell me and stop.
   - WAIT: tell me (I'll try again about 20 minutes later, at most twice) and stop.
   - Anything else: stop and show me the output.
5. Send `w01_s1.sql` … `w01_s4.sql`, then `w01_c1.sql` … `w01_c4.sql`, the same way as in step 3 (one at a time, SQL exactly as written, replies saved unchanged as `.json`). All eight are required.
6. Run `python3 toolkit/patrol24.py collect <run dir>`.
   - If a check names a reply that does not match its statement (wrong window or shards, rows outside the window, a missing shard, rows read twice), or says the per-code replies do not add up, send the named statements again (for the per-code check: all of `w01_s*` and `w01_c*`), save the new replies over the old files, and run `collect` again — once.
   - If it still says 核对没过 (a check failed), or the privacy scan is not clean, do not change any file; show me the message and stop.
7. Show me the `collect` output unchanged, in one code block. Then one line: the run directory, the post file `RC_patrol/posts/巡检_<date>_2100.txt` (the text to copy is also in that file), and whether `collect` ended with 可以发.
