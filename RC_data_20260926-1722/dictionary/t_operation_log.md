# t_operation_log

- 角色：**审计日志**
- 说明：策略引擎操作日志（2026-09-02 起）；只取模块/操作类型/时间计数与白名单 JSON 路径
- 表注释：策略引擎操作日志表
- 规模（information_schema 估算）：150 行（单表），2.6 MB
- 建表：2026-09-02T09:37:57；最近写入（UPDATE_TIME）：2026-09-24T07:26:12
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `module` | varchar(50) | YES | MUL |  | 模块名称 |
| 3 | `operation_type` | varchar(20) | YES |  |  | 操作类型 |
| 4 | `description` | varchar(255) | YES |  |  | 操作描述 |
| 5 | `operator` | varchar(50) | YES | MUL |  | 操作人 |
| 6 | `operation_time` | datetime | YES | MUL |  | 操作时间 |
| 7 | `request_url` | varchar(255) | YES |  |  | 请求URL |
| 8 | `request_params` | text | YES |  |  | 请求参数 |
| 9 | `response_data` | text | YES |  |  | 响应数据 |
| 10 | `before_data` | text | YES |  |  | 操作前数据 |
| 11 | `after_data` | text | YES |  |  | 操作后数据 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_module_type` | 否 | module, operation_type |
| `idx_operation_time` | 否 | operation_time |
| `idx_operator` | 否 | operator |
