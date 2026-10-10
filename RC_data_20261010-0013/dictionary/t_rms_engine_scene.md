# t_rms_engine_scene

- 角色：**配置（定义表）**
- 说明：场景；可全量导出（P2）
- 表注释：策略引擎场景表
- 规模（information_schema 估算）：22 行（单表），0.0 MB
- 建表：2026-09-02T09:37:13；最近写入（UPDATE_TIME）：2026-09-16T01:33:13
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `scene_id` | varchar(64) | NO | UNI |  | 场景ID |
| 3 | `scene_name` | varchar(64) | NO |  |  | 场景名称 |
| 4 | `access_id` | varchar(64) | NO |  |  | 接入方ID |
| 5 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 6 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 7 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 8 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 9 | `status` | int | NO |  | 0 | 场景开关状态1:开0:关 |
| 10 | `portrait_access_status` | tinyint | YES |  |  | 开启画像打标（0 关，1 开） |
| 11 | `global_strategy_block_status` | tinyint | YES |  |  | 全局策略开关 |
| 12 | `scene_block_status` | tinyint | YES |  |  | 场景熔断开关 |
| 13 | `mapping_status` | tinyint | NO |  | 0 | 流量映射开关，0关闭，1开启 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `uniq_scene_id` | 是 | scene_id |
