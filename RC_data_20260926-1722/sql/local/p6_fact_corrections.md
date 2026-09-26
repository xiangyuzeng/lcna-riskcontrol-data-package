| 原说法 | 数据显示 | 证据 |
|---|---|---|
| 提示词 §2.4「Sharding key: `CONCAT(country_code, phone)`」（未区分场景） | 只对 push / register / captcha 成立；login、payment、下单、取消、新人券的分片键是 `userNo`（三个抽查日均 100%） | DR-021，`results/dr021_best_candidate.csv` |
| 提示词 §2.3「App 不能 REVIEW；7 日到 09-24 所有 REVIEW 都来自 H5」 | 最近 7 日（09-19…09-25）仍然全部来自 H5；但 09-16/17 有 1.4.30 以上版本的 App 请求被引擎判 `REVIEW_15_NINE`、部分最终返回 REVIEW，08-25…09-02 的 `REVIEW_18_ICON` 全部来自 1.4.30 以下版本 | DR-024，`results/dr024_app_review_by_day.csv` |
| 提示词 §2.2「一个带条件的累计特征 11 天 PARAMS_ERROR」 | 已在 2026-09-24 07:24 UTC 修好（补上条件），此后该特征返回 SUCCESS / CONDITION_MISS；引用它的 `strategy_NrsClIxvGxWc` 从此开始命中 | DR-003、DR-025，`results/dr003_codes_daily_pivot.csv`、`results/dr025_hourly_summary.csv` |
| 附录 A DR-004「组合维度修好后重估」 | 2026-09-25 仍 100% `DIMENSION_EMPTY`，条件不满足 | DR-004 |
| `DATA_REQUESTS.md` DR-015 答复「名单只按租户计数」 | 名单表没有场景列；本轮经名单特征映射到场景：LKUS 只有手机号黑名单与 IP C 段白名单有条目，其余名单特征对应 0 条 | `results/p2_list_counts_by_scene.csv` |
| `DATA_REQUESTS.md` DR-007「汇总表最适合做误伤核对」 | 2026-09-21 起统计表只记下约 7% 的 +1 发送（此前约 92%），这些日子不能用来算回填率；09-20 以前可用 | DR-007，`results/dr007_daily_ccgroup.csv` |
| 上一轮包 `sql/p1_sk_transition_hourly.sql` 注释「分片键变化的小时」 | 2026-08-18 变化的是请求参数新增 `fullPhoneNo`，分片键规则没有变（本包的该 SQL 注释已改正） | `results/p1_sk_transition_hourly.csv` |
| 提示词 §2.4 `t_scene`「估算 31 行」 | 实际导出 32 行（information_schema 估算不精确） | `results/config_legacy_scene.csv`、`results/p0_schema_tables.csv` |
| 库内字段注释（`t_rms_engine_rule.rule_id`「特征ID」、`t_rms_engine_para.para_id/para_name`「场景ID/场景名称」、`t_rms_engine_tool.tool_type` 3=累计特征工具） | 与数据不符（仍未改） | `results/p1_comment_vs_data.csv` |
