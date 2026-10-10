# t_rms_engine_list_feature

- 角色：**配置（定义表）**
- 说明：名单特征定义（namelist_type 对应名单表 type）；导出（P2）
- 表注释：策略引擎名单特征表
- 规模（information_schema 估算）：28 行（单表），0.0 MB
- 建表：2026-09-02T09:37:12；最近写入（UPDATE_TIME）：2026-09-02T09:37:12
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint unsigned | NO | PRI |  | 主键ID |
| 2 | `feature_id` | varchar(32) | NO | UNI |  | 特征ID |
| 3 | `feature_name` | varchar(512) | NO |  |  | 特征名称 |
| 4 | `input_paras` | varchar(256) | NO |  |  | 输入参数参数 |
| 5 | `feature_valuetype` | int | NO |  |  | 特征值类型：string、int、float、boolean |
| 6 | `access_id` | varchar(64) | NO | MUL |  | 接入方ID |
| 7 | `operator` | varchar(64) | NO |  |  | 操作人员 |
| 8 | `update_time` | datetime | YES |  | CURRENT_TIMESTAMP | 修改时间 |
| 9 | `create_time` | datetime | YES |  | CURRENT_TIMESTAMP | 创建时间 |
| 10 | `remarks` | varchar(64) | NO |  |  | 备注 |
| 11 | `namelist_type` | int | NO |  | 0 | 名单类型 |
| 12 | `status` | int | NO |  | 0 | 开关状态 |
| 13 | `check_type` | int | NO |  | 0 | 检测类型1黑名单2白名单 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_access_feature_id` | 否 | access_id, feature_id |
| `uniq_feature_id` | 是 | feature_id |
