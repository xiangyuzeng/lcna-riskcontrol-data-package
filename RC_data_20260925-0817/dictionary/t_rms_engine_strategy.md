# t_rms_engine_strategy

- 角色：**配置（定义表）**
- 说明：策略；status/result_code/exec_priority；导出（P2）
- 表注释：策略表
- 规模（information_schema 估算）：169 行（单表），0.1 MB
- 建表：2026-09-02T09:37:08；最近写入（UPDATE_TIME）：2026-09-23T14:43:34
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `strategy_id` | varchar(32) | NO | UNI |  | 策略ID |
| 3 | `strategy_name` | varchar(512) | NO |  |  | 策略名称 |
| 4 | `status` | tinyint | YES |  |  | 策略状态 |
| 5 | `result_code` | varchar(32) | NO |  |  | 返回码 |
| 6 | `exec_priority` | int | NO |  |  | 策略执行优先级 |
| 7 | `access_id` | varchar(64) | NO | MUL |  | 接入方ID |
| 8 | `scene_id` | varchar(64) | NO |  |  | 场景ID |
| 9 | `breake_id` | int | NO |  | 0 | 熔断阈值 |
| 10 | `strategy_express` | varchar(512) | YES |  |  | 策略表达式 |
| 11 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 12 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 13 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 14 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 15 | `description` | text | YES |  |  | 策略返回描述 |
| 16 | `rule_operator` | int | NO |  | 0 | 规则关系运算符 |
| 17 | `strategy_type` | tinyint | YES |  | 1 | 策略用途，1:风险识别，2:黑用户评估，3:白用户评估 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_access_scene_strategy_id` | 否 | access_id, strategy_id |
| `uniq_strategy_id` | 是 | strategy_id |

## 取值说明（实测）

- `status`：1 = 上线（日志命中元素 `ONLINE`），2 = 预上线（`PREONLINE`，写入 `hitPreOnlineStrategy`），0 = 下线（从不出现在命中里）。依据 `results/config_status_vs_hits.csv`，见 `02_线上配置导出.md` §3。
- `exec_priority`：越大越先执行；优先级 100000 的 PASS 命中后引擎不再执行其它策略（DR-001）。
- 修改上线策略会被自动打回预上线（`results/p2_oplog_changes.csv`，2026-09-09 03:39 UTC 实例）。
