# 每日 21:00 短信巡检 · 运行卡（每晚粘贴一次）

给人看的：在能连风控库的那台机器上，到放 `RC_patrol/` 的运行目录（`claude mcp list` 能看到 mcp-db-gateway 已连接的那个目录），用普通模式开 Claude Code（`claude`，不要 plan 模式），纽约时间 21:02 以后把下面整段粘贴进去。每条查库语句它会请你批准，大约 5 分钟。最后屏幕上"复制下面这段发群"到"到这里"之间的文字，就是要发群的内容，由你自己发。

如果当晚跑不了，群里只替自己说一句，例如：今晚21点的巡检数暂时取不到（原因），弄好后补发。

---

This is the nightly run of the 21:00 New York SMS inspection that was set up in `RC_patrol/`. Do exactly the steps below and nothing else. Database access is read-only, only through the mcp-db-gateway query tool on server `aws-luckyus-iriskcontrolservice-rw`, one statement at a time. Never look for the gateway address anywhere, never edit a statement or a reply by hand, never query anything not listed here, never post or send anything, never schedule anything.

1. Run `cd RC_patrol && export PYTHONDONTWRITEBYTECODE=1 && python3 toolkit/patrol24.py verify`. It must print `N/N match`. Otherwise stop and show me the output.
2. Run `python3 toolkit/patrol24.py emit --per-code`.
   - Exit 2 ("还没到时间", before today's 21:02): tell me the time it prints and stop. Never add `--date` or `--force` on your own; a past evening is posted only if I ask for it by date.
   - Exit 3 (another database run may be active): show me its reasons and ask me whether to continue. Only after I say yes, run it again with `--m1-active-ok` added.
   - It prints the run directory, for example `runs/20261010-210312_slot`. Use that directory below.
3. Send `s0a_processlist.sql`, `s0b_threads.sql`, `s0c_shards.sql` and `s0d_explain.sql`, in that order. For each one, read the file and send its SQL exactly as written with the query tool, then save the tool's reply exactly as returned (the JSON text, unchanged) as a file with the same name and `.json` instead of `.sql`, in the same directory.
4. Run `python3 toolkit/patrol24.py gate <run dir>`.
   - GO: continue.
   - WAIT: tell me (I'll try again at 21:20, then 21:40) and stop.
   - Anything else: stop and show me the output.
5. Send `w01_s1.sql` … `w01_s4.sql`, then `w01_c1.sql` … `w01_c4.sql`, the same way as in step 3 (one at a time, SQL exactly as written, replies saved unchanged as `.json`). All eight are required.
6. Run `python3 toolkit/patrol24.py collect <run dir>`.
   - If a check names a reply that does not match its statement (wrong window or shards, rows outside the window, a missing shard, rows read twice), or says the per-code replies do not add up, send the named statements again (for the per-code check: all of `w01_s*` and `w01_c*`), save the new replies over the old files, and run `collect` again — once.
   - If it still says 核对没过 (a check failed), or the privacy scan is not clean, do not change any file; show me the message and stop.
7. Show me the `collect` output unchanged, in one code block. Then one line: the run directory, the post file `RC_patrol/posts/巡检_<date>_2100.txt` (the text to copy is also in that file), and whether `collect` ended with 可以发.
