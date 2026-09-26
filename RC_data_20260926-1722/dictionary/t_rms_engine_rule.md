# t_rms_engine_rule

- 角色：**配置（定义表）**
- 说明：规则；condition_value 等自由文本在 SQL 里整值屏蔽疑似个人信息后导出（P2）
- 表注释：规则表
- 规模（information_schema 估算）：154 行（单表），0.1 MB
- 建表：2026-09-02T09:37:09；最近写入（UPDATE_TIME）：2026-09-22T15:31:37
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `rule_id` | varchar(32) | NO | UNI |  | 特征ID |
| 3 | `rule_name` | varchar(512) | NO |  |  | 规则名称 |
| 4 | `access_id` | varchar(64) | NO | MUL |  | 接入方ID |
| 5 | `status` | int | NO |  |  | 策略状态1开0关 |
| 6 | `feature_type` | tinyint | YES |  |  | 特征类型 |
| 7 | `feature_id` | varchar(32) | NO |  |  | 特征ID |
| 8 | `condition_type` | varchar(32) | NO |  |  | 规则匹配类型 |
| 9 | `condition_value` | text | YES |  |  | 匹配值 |
| 10 | `rule_express` | varchar(512) | YES |  |  | 规则表达式 |
| 11 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 12 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 13 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 14 | `remarks` | varchar(64) | NO |  |  | 备注 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_access_rule_id` | 否 | access_id, rule_id |
| `uniq_rule_id` | 是 | rule_id |

## 字段注释与数据不符（2026-09-26 核对，`results/p1_comment_vs_data.csv`）

| 字段 | 库内注释 | 数据显示 |
|---|---|---|
| `rule_id` | 特征ID | 值全部是 `rule_` 前缀（154/154）：是规则 ID，不是特征 ID（特征 ID 在 `feature_id` 列） |
| `status` | 策略状态1开0关 | 这是规则表的开关，注释写成「策略状态」；取值 1:154 |
