# t_scene

- 角色：**遗留配置**
- 说明：旧版场景表（31 行）；只导出非个人字段（P2）
- 表注释：场景表
- 规模（information_schema 估算）：31 行（单表），0.0 MB
- 建表：2025-05-29T05:36:46；最近写入（UPDATE_TIME）：2026-07-28T08:15:29
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键id |
| 2 | `scene_type` | smallint | NO |  |  | 场景类型 |
| 3 | `async` | tinyint | NO |  | 0 | 是否异步执行规则: 0=否, 1=是 |
| 4 | `open` | tinyint | NO |  | 0 | 是否开启: 0=否, 1=是 |
| 5 | `online` | tinyint | NO |  | 0 | 是否在线: 0=否, 1=是 |
| 6 | `tenant` | varchar(20) | NO |  |  | 租户 |
| 7 | `deleted` | tinyint | NO |  | 0 | 逻辑删除: 0=未删除, 1=已删除 |
| 8 | `create_emp` | int | YES |  |  | 创建人 |
| 9 | `create_name` | varchar(32) | YES |  |  | 创建人名称 |
| 10 | `create_time` | datetime | NO |  | CURRENT_TIMESTAMP | 创建时间 |
| 11 | `modify_emp` | int | YES |  |  | 更新人 |
| 12 | `modify_name` | varchar(32) | YES |  |  | 更新人名称 |
| 13 | `modify_time` | datetime | NO |  | CURRENT_TIMESTAMP | 更新时间 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
