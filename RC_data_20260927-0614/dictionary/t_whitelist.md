# t_whitelist

- 角色：**名单（条目表）**
- 说明：白名单条目；content 为个人信息——只做 type×tenant×source×temp 计数
- 表注释：白名单表
- 规模（information_schema 估算）：164 行（单表），0.1 MB
- 建表：2025-05-29T08:46:50；最近写入（UPDATE_TIME）：2026-09-22T23:00:00
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键 |
| 2 | `type` | int | NO |  |  | 类型 |
| 3 | `content` | varchar(255) | NO | MUL |  | 白名单内容 |
| 4 | `remark` | varchar(500) | YES |  |  | 备注 |
| 5 | `source` | int | YES |  |  | 来源 |
| 6 | `create_time` | datetime | YES |  |  | 创建时间 |
| 7 | `modify_time` | datetime | YES |  |  | 更新时间 |
| 8 | `create_id` | int | YES |  |  | 创建人id |
| 9 | `create_name` | varchar(50) | YES |  |  | 创建人名称 |
| 10 | `modify_id` | int | YES |  |  | 更新人id |
| 11 | `modify_name` | varchar(50) | YES |  |  | 更新人名称 |
| 12 | `tenant` | varchar(20) | NO | MUL |  | 租户 |
| 13 | `temp` | int | YES |  | 0 | 临时保存：1临时，0永久 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_content` | 否 | content |
| `idx_content_type_tenant` | 否 | content, type, tenant |
| `idx_tenant` | 否 | tenant |
