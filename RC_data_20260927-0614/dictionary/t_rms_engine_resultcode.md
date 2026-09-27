# t_rms_engine_resultcode

- 角色：**配置（定义表）**
- 说明：返回码与优先级；可全量导出（P2）
- 表注释：返回码表
- 规模（information_schema 估算）：14 行（单表），0.0 MB
- 建表：2025-05-29T05:36:11；最近写入（UPDATE_TIME）：2026-09-09T03:30:27
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `result_code` | varchar(32) | NO | MUL |  | 返回码ID |
| 3 | `result_name` | varchar(64) | NO |  |  | 返回码名称 |
| 4 | `priority` | int | YES |  |  | 优先级 |
| 5 | `access_id` | varchar(64) | NO |  |  | 接入方ID |
| 6 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 7 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 8 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 9 | `remarks` | varchar(64) | NO |  |  | 备注 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `uniq_access_result_id` | 是 | result_code, access_id |
