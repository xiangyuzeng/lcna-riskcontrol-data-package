# t_rms_engine_strategy_relation

- 角色：**配置（定义表）**
- 说明：策略-规则映射；导出（P2）
- 表注释：策略规则映射表
- 规模（information_schema 估算）：571 行（单表），0.2 MB
- 建表：2025-05-29T08:46:46；最近写入（UPDATE_TIME）：2026-09-23T14:43:34
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `strategy_id` | varchar(32) | NO | MUL |  | 策略ID |
| 3 | `rule_id` | varchar(32) | NO |  |  | 规则ID |
| 4 | `status` | tinyint | YES |  |  | 是否启用 |
| 5 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 6 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 7 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 8 | `remarks` | text | YES |  |  | 备注 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_strategy_rule_id` | 否 | strategy_id, rule_id |
| `uniq_strategy_rule_id` | 是 | strategy_id, rule_id |
