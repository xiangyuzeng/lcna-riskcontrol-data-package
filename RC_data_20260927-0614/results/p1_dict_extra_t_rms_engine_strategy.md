## 取值（2026-09-27 导出，`results/config_strategy.csv`）

- `status`：1 = 上线、2 = 预上线、0 = 下线（与命中元素里的 `ONLINE` / `PREONLINE` 对照核实，见 `02_线上配置导出.md` §3）。字段注释未写取值含义。
- 当前计数：IQA2 status=0 共 1 条；IQA2 status=2 共 24 条；LKUS status=0 共 35 条；LKUS status=1 共 65 条；LKUS status=2 共 44 条。
- `exec_priority` 越大越先执行；修改上线策略会把 `status` 打回 2（操作日志实证，见 `results/p2_oplog_timeline.csv`）。
