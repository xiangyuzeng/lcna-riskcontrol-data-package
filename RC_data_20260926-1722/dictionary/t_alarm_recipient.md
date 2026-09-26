# t_alarm_recipient

- 角色：**告警配置（条目表）**
- 说明：告警收件人（姓名/手机号/邮箱）——只计数，不导出
- 表注释：告警收件人表
- 规模（information_schema 估算）：2 行（单表），0.0 MB
- 建表：2025-05-29T05:33:57；最近写入（UPDATE_TIME）：—
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键id |
| 2 | `name` | varchar(32) | NO |  |  | 姓名 |
| 3 | `emp_no` | varchar(32) | NO |  |  | 员工工号 |
| 4 | `mobile` | varchar(32) | NO |  |  | 手机号 |
| 5 | `email` | varchar(64) | NO |  |  | 邮箱 |
| 6 | `ent_email` | varchar(64) | NO |  |  | 企业邮箱 |
| 7 | `remark` | varchar(256) | YES |  |  | 备注 |
| 8 | `tenant` | varchar(20) | NO |  |  | 租户 |
| 9 | `deleted` | tinyint | NO |  | 0 | 逻辑删除: 0=未删除, 1=已删除 |
| 10 | `create_emp` | int | YES |  |  | 创建人 |
| 11 | `create_name` | varchar(32) | YES |  |  | 创建人名称 |
| 12 | `create_time` | datetime | NO |  | CURRENT_TIMESTAMP | 创建时间 |
| 13 | `modify_emp` | int | YES |  |  | 更新人 |
| 14 | `modify_name` | varchar(32) | YES |  |  | 更新人名称 |
| 15 | `modify_time` | datetime | NO |  | CURRENT_TIMESTAMP | 更新时间 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
