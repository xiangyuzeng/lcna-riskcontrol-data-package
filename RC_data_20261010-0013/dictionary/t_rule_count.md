# t_rule_count

- 角色：**统计（遗留）**
- 说明：旧版规则调用计数；call_time 有索引；最近写入 2026-08-18
- 表注释：规则调用计数表
- 规模（information_schema 估算）：7,900,095 行（单表），642.7 MB
- 建表：2025-05-29T08:46:49；最近写入（UPDATE_TIME）：2026-08-18T08:40:00
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键id |
| 2 | `rule_type` | smallint | NO |  |  | 规则类型 |
| 3 | `count_type` | tinyint | NO |  |  | 计数类型 1：pv 2：uv |
| 4 | `call_time` | datetime | NO | MUL |  | 调用时间 |
| 5 | `cid` | varchar(32) | NO |  |  | 终端编码 |
| 6 | `pass_number` | int | NO |  | 0 | PASS条数 |
| 7 | `review_number` | int | NO |  | 0 | REVIEW条数 |
| 8 | `reject_number` | int | NO |  | 0 | REJECT条数 |
| 9 | `tenant` | varchar(20) | NO |  |  | 租户 |
| 10 | `create_time` | datetime | NO |  | CURRENT_TIMESTAMP | 创建时间 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_call_time` | 否 | call_time |
