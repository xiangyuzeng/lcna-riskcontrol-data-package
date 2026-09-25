# t_rms_engine_tool

- 角色：**配置（定义表）**
- 说明：特征工具（累计/Twilio/reCAPTCHA）；导出（P2）
- 表注释：策略引擎工具表
- 规模（information_schema 估算）：3 行（单表），0.0 MB
- 建表：2026-09-02T09:37:06；最近写入（UPDATE_TIME）：2026-09-02T09:37:06
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `tool_id` | varchar(32) | NO | MUL |  | 参数补全工具ID |
| 3 | `tool_name` | varchar(64) | NO |  |  | 参数补全工具名称 |
| 4 | `tool_classpath` | varchar(500) | NO |  |  | 参数补全工具实现类路径 |
| 5 | `tool_type` | tinyint | NO |  |  | 工具类型，1:参数补全工具，2:特征工具，3:累计特征工具 |
| 6 | `has_parm` | tinyint | NO |  |  | 工具是否有参数，0:无参，1:有参 |
| 7 | `input_paras` | text | YES |  |  | 输入参数 |
| 8 | `output_paras` | text | YES |  |  | 输出参数 |
| 9 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 10 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 11 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 12 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 13 | `status` | tinyint | YES |  | 1 | 开关状态 |
| 14 | `block_enabled` | tinyint | YES |  | 0 | 开启熔断配置，0关闭，1开启 |
| 15 | `period` | int | YES |  | 0 | 统计周期，单位秒 |
| 16 | `max_calls` | bigint | YES |  | 0 | 周期内最大调用次数 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_tool_id` | 否 | tool_id |
