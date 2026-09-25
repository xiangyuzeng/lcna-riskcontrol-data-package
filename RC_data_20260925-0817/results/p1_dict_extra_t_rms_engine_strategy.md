## 取值说明（实测）

- `status`：1 = 上线（日志命中元素 `ONLINE`），2 = 预上线（`PREONLINE`，写入 `hitPreOnlineStrategy`），0 = 下线（从不出现在命中里）。依据 `results/config_status_vs_hits.csv`，见 `02_线上配置导出.md` §3。
- `exec_priority`：越大越先执行；优先级 100000 的 PASS 命中后引擎不再执行其它策略（DR-001）。
- 修改上线策略会被自动打回预上线（`results/p2_oplog_changes.csv`，2026-09-09 03:39 UTC 实例）。
