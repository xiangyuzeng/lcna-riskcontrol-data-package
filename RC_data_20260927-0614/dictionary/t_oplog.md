# t_oplog

- 角色：**审计日志（遗留，条目表）**
- 说明：旧版黑白名单操作日志；content 为名单内容；无时间索引——只读元数据
- 表注释：操作日志
- 规模（information_schema 估算）：26,496 行（单表），3.5 MB
- 建表：2025-05-29T05:36:01；最近写入（UPDATE_TIME）：2026-08-27T08:13:09
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键 |
| 2 | `type` | int | YES |  |  | 数据类型.1:黑名单;2:白名单 |
| 3 | `content` | varchar(500) | YES |  |  | 数据内容 |
| 4 | `action` | int | YES |  |  | 操作类型 |
| 5 | `create_time` | datetime | YES |  |  | 操作时间 |
| 6 | `create_name` | varchar(50) | YES |  |  | 操作人名称 |
| 7 | `busi_type` | int | YES |  |  | 数据业务类型 |
| 8 | `remark` | varchar(500) | YES |  |  | 备注 |
| 9 | `tenant` | varchar(20) | YES |  |  | 租户 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
