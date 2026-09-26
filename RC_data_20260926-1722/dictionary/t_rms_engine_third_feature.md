# t_rms_engine_third_feature

- 角色：**配置（定义表）**
- 说明：第三方/累计特征定义；input_paras 只导出键与白名单路径（P2）
- 表注释：策略引擎第三方特征表
- 规模（information_schema 估算）：50 行（单表），0.1 MB
- 建表：2026-09-02T09:37:11；最近写入（UPDATE_TIME）：2026-09-24T07:26:12
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `feature_id` | varchar(32) | NO | UNI |  | 特征ID |
| 3 | `feature_name` | varchar(512) | NO |  |  | 特征名称 |
| 4 | `tool_id` | varchar(32) | NO |  |  | 第三方特征工具ID |
| 5 | `third_label` | varchar(64) | NO |  |  | 第三方标签 |
| 6 | `input_paras` | text | YES |  |  | 输入参数 |
| 7 | `feature_valuetype` | int | YES |  |  | 特征值java类型 |
| 8 | `access_id` | varchar(64) | NO | MUL |  | 接入方ID |
| 9 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 10 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 11 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 12 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 13 | `status` | int | NO |  | 0 | 开关状态 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_access_feature_id` | 否 | access_id, feature_id |
| `uniq_feature_id` | 是 | feature_id |
