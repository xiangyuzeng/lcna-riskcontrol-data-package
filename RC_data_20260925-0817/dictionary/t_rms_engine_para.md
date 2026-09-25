# t_rms_engine_para

- 角色：**配置（定义表）**
- 说明：场景参数定义；可全量导出（P2）
- 表注释：策略引擎参数表
- 规模（information_schema 估算）：603 行（单表），0.2 MB
- 建表：2025-05-29T08:46:42；最近写入（UPDATE_TIME）：2026-09-21T08:41:37
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `para_id` | varchar(32) | NO | MUL |  | 场景ID |
| 3 | `para_name` | varchar(64) | NO |  |  | 场景名称 |
| 4 | `scene_id` | varchar(64) | NO |  |  | 场景ID |
| 5 | `access_id` | varchar(64) | NO | MUL |  | 接入方ID |
| 6 | `para_type` | tinyint | NO |  |  | 参数类型 0:原始参数 1:补全参数 |
| 7 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 8 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 9 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 10 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 11 | `para_java_type` | int | NO |  | 0 | 字段值的java数据类型 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_para_id` | 否 | para_id |
| `uniq_access_scene_para_id` | 是 | access_id, scene_id, para_id |
