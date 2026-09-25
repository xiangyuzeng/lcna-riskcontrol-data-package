# t_access_log_0000

- 角色：**日志（分片）**
- 说明：风控请求日志，64 张同构分片 t_access_log_0000…0063；分片键 sharding_key；create_time 为 UTC；只做带时间谓词的聚合
- 表注释：风控访问日志 （同结构分片 64 张，此页以 0000 为代表）
- 规模（information_schema 估算，64 张合计）：4,273,218 行，41744.8 MB；单表 534.9–730.0 MB
- 建表：2025-05-29T08:43:13；最近写入（UPDATE_TIME）：2026-09-25T11:52:07
- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）

## 字段

| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |
|---|---|---|---|---|---|---|
| 1 | `id` | bigint | NO | PRI |  | 主键id |
| 2 | `sharding_key` | varchar(64) | NO | MUL |  | Sharding-JDBC分片键 |
| 3 | `type` | int | YES |  |  | 日志类型 |
| 4 | `user_no` | varchar(255) | YES |  |  | 用户编号 |
| 5 | `phone` | varchar(30) | YES |  |  | 用户手机号 |
| 6 | `country_code` | varchar(20) | YES |  |  | 国际区号 |
| 7 | `ip` | varchar(20) | YES |  |  | ip |
| 8 | `ip_city` | varchar(20) | YES |  |  | ip所属城市 |
| 9 | `ip_province` | varchar(20) | YES |  |  | ip所属省份 |
| 10 | `device_type` | varchar(30) | YES |  |  | 设备类型 |
| 11 | `did` | varchar(100) | YES |  |  | 数盟设备号 |
| 12 | `device_id` | varchar(100) | YES |  |  | 数美设备号 |
| 13 | `black_box` | varchar(500) | YES |  |  | 同盾blackbox |
| 14 | `tongdun_device_id` | varchar(100) | YES |  |  | 同盾设备号 |
| 15 | `open_id` | varchar(100) | YES |  |  | openId |
| 16 | `qcell_core` | varchar(20) | YES |  |  | 手机号归属地 |
| 17 | `qcell_core_province` | varchar(20) | YES |  |  | 手机号归属省份 |
| 18 | `qcell_core_operator` | varchar(20) | YES |  |  | 手机号归属运营商 |
| 19 | `result` | varchar(10) | YES |  |  | 返回结果 |
| 20 | `longitude` | decimal(10,7) | YES |  |  | 经度信息 |
| 21 | `latitude` | decimal(10,7) | YES |  |  | 纬度信息 |
| 22 | `coordinate_city` | varchar(20) | YES |  |  | 坐标城市 |
| 23 | `coordinate_province` | varchar(20) | YES |  |  | 坐标省份 |
| 24 | `shop_city` | varchar(20) | YES |  |  | 门店城市 |
| 25 | `shop_province` | varchar(20) | YES |  |  | 门店省份 |
| 26 | `request` | text | YES |  |  | rpc输入 |
| 27 | `response` | text | YES |  |  | rpc返回 |
| 28 | `request_shumeng` | varchar(255) | YES |  |  | 数盟输入 |
| 29 | `response_shumeng` | varchar(500) | YES |  |  | 数盟返回 |
| 30 | `request_shumei` | text | YES |  |  | 数美输入 |
| 31 | `response_shumei` | varchar(2000) | YES |  |  | 数美返回 |
| 32 | `request_tongdun` | varchar(2000) | YES |  |  | 同盾输入 |
| 33 | `response_tongdun` | text | YES |  |  | 同盾返回 |
| 34 | `create_time` | datetime | NO | MUL | CURRENT_TIMESTAMP | 创建时间 |
| 35 | `tenant` | varchar(20) | NO |  |  | 租户 |
| 36 | `country` | varchar(20) | YES |  |  | 国家 |
| 37 | `province` | varchar(20) | YES |  |  | 省份 |
| 38 | `city` | varchar(20) | YES |  |  | 城市 |
| 39 | `district` | varchar(20) | YES |  |  | 区 |
| 40 | `email` | varchar(100) | YES |  |  | 邮箱 |
| 41 | `extend` | varchar(1000) | YES |  |  | 扩展信息 |
| 42 | `request_shumei_text_audit` | text | YES |  |  | 数美文本审核输入 |
| 43 | `response_shumei_text_audit` | text | YES |  |  | 数美文本审核返回 |
| 44 | `request_jiyan` | text | YES |  |  | 极验输入 |
| 45 | `response_jiyan` | text | YES |  |  | 极验返回 |
| 46 | `request_yongan_phone` | text | YES |  |  | 永安在线手机号输入 |
| 47 | `response_yongan_phone` | text | YES |  |  | 永安在线手机号返回 |
| 48 | `access_id` | varchar(64) | YES |  |  | 接入方id |
| 49 | `scene_id` | varchar(64) | YES |  |  | 场景id |
| 50 | `request_strategy_engine` | text | YES |  |  | 策略引擎输入 |
| 51 | `response_strategy_engine` | text | YES |  |  | 策略引擎返回 |

## 索引

| 索引 | 唯一 | 列（顺序） |
|---|---|---|
| `PRIMARY` | 是 | id |
| `idx_create_time_sharding_key` | 否 | create_time, sharding_key |
| `idx_sharding_key_create_time` | 否 | sharding_key, create_time |

## 时间列与时区（实测）

- `create_time` 为 UTC：最近 1 小时窗口内最新 `create_time` 与同一语句的 `UTC_TIMESTAMP()` 相差约 1 秒（`sql/p1_freshness.sql` → `results/p1_freshness.csv`）；服务器 `@@time_zone=UTC`（`results/p0_server_vars.csv`）。
- 取数一律 `create_time >= '<UTC>' AND create_time < '<UTC>'`，走 `idx_create_time_sharding_key`（EXPLAIN 见 `results/explain/`）。

## 分片键（DR-014）

- `sharding_key` = `CONCAT(country_code, phone)`，即带 `+` 的区号+手机号；2026-06-01、2026-08-17、2026-09-24 三个纽约日 LKUS_push 100% 成立（`results/p1_sk_concat_check_*.csv`）。
- 2026-08-18 约 08–09 时（UTC）起请求参数新增 `fullPhoneNo`，此后 `sharding_key = fullPhoneNo` 100% 成立（`results/p1_sk_transition_hourly.csv`、`results/p1_chk_consistency.csv`）；此前 `fullPhoneNo` 键不存在。
- 同一手机号只落在一个分片：按分片 `COUNT(DISTINCT sharding_key)` 相加即全局去重手机号数；`uid` 不是分片键，跨分片不可直接相加。

## JSON 列结构（只列键，不取值；2026-09-24 纽约日，全部 64 分片）

来源：`sql/p1_keys_*.sql` → `results/p1_keys_*.csv`，汇总 `results/p1_json_keys_summary.csv`（`sql/local/p1_structure.py`）。

| 位置 | 类型 | LKUS_push 中出现的键（出现行占比） |
|---|---|---|
| `request_strategy_engine` | 对象 | `accessid`(100.0%), `para`(100.0%), `sceneid`(100.0%) |
| `request_strategy_engine` → `$.para` | **JSON 字符串**（需 `CAST(JSON_UNQUOTE(...) AS JSON)`） | `cid`(100.0%), `countryCode`(100.0%), `fullPhoneNo`(100.0%), `phoneCountry`(100.0%), `phoneNo`(100.0%), `realIp`(100.0%), `realIpCity`(100.0%), `realIpCountry`(100.0%), `realIpProvince`(100.0%), `tenant`(100.0%), `uid`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(90.7%), `reviewRepeat`(90.7%), `recaptchaV3Action`(90.1%), `recaptchaV3Token`(90.1%), `app`(84.1%), `userNo`(3.5%), `email`(0.4%) |
| `response_strategy_engine` | 对象 | `errCode`(100.0%), `msg`(100.0%), `re`(100.0%), `status`(100.0%) |
| `response_strategy_engine` → `$.re` | 对象 | `accessId`(100.0%), `extern`(100.0%), `featureDetail`(100.0%), `hitBreakStrategy`(100.0%), `message`(100.0%), `requestId`(100.0%), `resultCode`(100.0%), `resultName`(100.0%), `ruleDetail`(100.0%), `sceneId`(100.0%), `zeusId`(100.0%), `bestPreOnlineStrategyId`(96.1%), `hitPreOnlineStrategy`(96.1%), `bestStrategyId`(49.4%), `hitStrategy`(49.4%) |
| `response`（返回调用方） | 对象 | `code`(100.0%), `detail`(100.0%), `message`(100.0%), `result`(100.0%), `model`(0.5%) |
| `request`（rpc 输入） | 对象 | `cid`(100.0%), `cidOriginEnum`(100.0%), `countryCode`(100.0%), `ip`(100.0%), `phone`(100.0%), `tenant`(100.0%), `uid`(100.0%), `uniqueKey`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(90.7%), `reviewRepeat`(90.7%), `recaptchaV3Action`(90.1%), `recaptchaV3Token`(90.1%), `app`(84.1%), `userNo`(3.5%), `email`(0.4%) |
| `$.re.featureDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `featureId`(100.0%), `name`(100.0%), `result`(100.0%), `type`(100.0%) |
| `$.re.featureDetail[*].comments` | 对象 | `apiResp`(100.0%) |
| `$.re.hitStrategy[*]` | **JSON 字符串**里的数组 | `execPriority`(49.4%), `resultName`(49.4%), `status`(49.4%), `strategyId`(49.4%), `strategyName`(49.4%), `strategyType`(49.4%), `vaild`(49.4%) |
| `$.re.hitPreOnlineStrategy[*]` | **JSON 字符串**里的数组 | `execPriority`(96.1%), `resultName`(96.1%), `status`(96.1%), `strategyId`(96.1%), `strategyName`(96.1%), `strategyType`(96.1%), `vaild`(96.1%) |
| `$.re.ruleDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `name`(100.0%), `result`(100.0%), `ruleId`(100.0%), `type`(100.0%) |
| `extend` | LKUS_push 为空 | — |
| `$.re.hitBreakStrategy[*]` | JSON 字符串里的数组 | 当天所有场景均为空数组（未命中熔断） |

## 体积（2026-09-24，LKUS_push 3,225 行，`results/p1_payload_size.csv`）

- 平均每行：`response_strategy_engine` 27,304 B，其中 `featureDetail` 11,911 B、`ruleDetail` 13,852 B；`request_strategy_engine` 3,792 B。
- 永远不要 SELECT 整个 JSON 列：服务端用 `JSON_TABLE` / `JSON_EXTRACT` 只取标量。

## 基础列的可用性（2026-09-24，`results/p1_scene_rows.csv`）

- `ip_city`、`ip_province`、`country`、`province`、`city`：所有场景 0 行非空 → IP 地理只能取 `$.para.realIpCountry/realIpProvince/realIpCity`。
- `did`、`device_id`：只有 LKUS_physical_order_create 有值（876/6,184）；`tongdun_device_id`：全空。LKUS_push 无设备号。
- `country_code` 列与 `$.para.countryCode` 一律带 `+`，两者 100% 相等（7 日 31,832 行，`results/p1_chk_consistency.csv`）。
- `result` 列 = `response.$.result`（100%），即返回调用方的最终结果。
