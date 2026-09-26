# t_rms_engine_block_metric

- 角色：**配置（定义表）**
- 说明：熔断指标；metricql 只导出键/屏蔽后文本（P2）
- 表注释：熔断指标表
- 规模（information_schema 估算）：6 行（单表），0.1 MB
- 建表：2025-12-18T02:17:23；最近写入（UPDATE_TIME）：—
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `metric_id` | varchar(64) | NO | UNI |  | 指标ID |
| 3 | `metric_name` | varchar(256) | NO |  |  | 指标名称 |
| 4 | `metric_period` | int | NO |  |  | 指标计算周期(秒) |
| 5 | `access_type` | tinyint | NO | MUL |  | 指标作用范围 1=风控场景 2=风控策略 |
| 6 | `source` | tinyint | NO |  |  | 数据来源 1=Prometheus 2=其他 |
| 7 | `metricql` | text | YES |  |  | 指标抽取SQL/PromQL |
| 8 | `status` | tinyint | NO | MUL | 1 | 指标状态 0=关闭 1=开启 |
| 9 | `create_user` | varchar(64) | YES |  |  | 创建人 |
| 10 | `update_user` | varchar(64) | YES |  |  | 更新人 |
| 11 | `create_time` | datetime | NO |  |  | 创建时间 |
| 12 | `update_time` | datetime | NO |  |  | 更新时间 |
| 13 | `remarks` | text | YES |  |  | 备注信息 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_access_type` | 否 | access_type |
| `idx_status` | 否 | status |
| `uniq_metric_id` | 是 | metric_id |
