# t_rms_engine_block_strategy

- 角色：**配置（定义表）**
- 说明：熔断策略；导出（P2）
- 表注释：熔断策略表
- 规模（information_schema 估算）：24 行（单表），0.1 MB
- 建表：2025-12-18T02:17:24；最近写入（UPDATE_TIME）：2026-07-29T01:50:45
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `block_strategy_id` | varchar(64) | NO | UNI |  | 熔断策略ID |
| 3 | `strategy_period` | varchar(256) | YES |  |  | 指标计算周期 |
| 4 | `rules` | text | YES |  |  | 指标规则(JSON数组字符串) |
| 5 | `expression` | text | YES |  |  | 策略表达式 |
| 6 | `action` | tinyint | NO |  |  | 处置动作 1=发送告警 2=执行熔断并发送告警 |
| 7 | `status` | tinyint | NO |  |  | 策略状态 0=关闭 1=开启 |
| 8 | `strategy_type` | tinyint | NO | MUL |  | 熔断策略类型 1=场景 2=全局 3=策略 |
| 9 | `union_id` | varchar(128) | YES | MUL |  | 关联ID(场景:scene_id/策略:strategy_id) |
| 10 | `create_user` | varchar(64) | YES |  |  | 创建人 |
| 11 | `update_user` | varchar(64) | YES |  |  | 更新人 |
| 12 | `create_time` | datetime | NO |  |  | 创建时间 |
| 13 | `update_time` | datetime | NO |  |  | 更新时间 |
| 14 | `remark` | text | YES |  |  | 备注信息 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_strategy_type` | 否 | strategy_type |
| `idx_strategy_type_union` | 否 | strategy_type, union_id |
| `idx_union_id` | 否 | union_id |
| `uniq_block_strategy_id` | 是 | block_strategy_id |
