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
