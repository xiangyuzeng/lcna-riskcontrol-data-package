# t_rms_engine_access

- 角色：**配置（定义表）**
- 说明：接入方；可全量导出（P2）
- 表注释：策略引擎接入方表
- 规模（information_schema 估算）：6 行（单表），0.0 MB
- 建表：2025-05-29T05:36:04；最近写入（UPDATE_TIME）：2026-09-02T09:38:08
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `access_id` | varchar(64) | NO | UNI |  | 接入方ID |
| 3 | `access_name` | varchar(64) | NO |  |  | 接入方名称 |
| 4 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 5 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 6 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 7 | `remarks` | varchar(64) | NO |  |  | 备注 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `uniq_access_id` | 是 | access_id |
