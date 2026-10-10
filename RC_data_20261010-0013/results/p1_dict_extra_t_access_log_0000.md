## 分片键（DR-014）

- `sharding_key` = `CONCAT(country_code, phone)`（带 `+` 的区号 + 手机号）：纽约日 2026-10-09 LKUS_push 2,129 行中 2,129 行成立（`results/dr014_sharding_key_by_scene_20261009.csv`）。
- 7 日（2026-10-03…2026-10-09）LKUS_push 20,210 行 `sharding_key = $.para.fullPhoneNo` 成立 20,210 行（`results/p1_chk_consistency.csv`）。
- 请求参数 `fullPhoneNo` 自纽约日 2026-08-18 起出现（2026-09-25 包实测，本包未复测）；分片键规则本身没有变：此前此后都等于区号 + 手机号。
- 其它场景按场景组分片（login / payment / 下单 / 取消 / 新人券 = `userNo`），本包的抽查见 `04_数据问题结论.md#dr-014`。

## JSON 列结构（只列键，不取值；纽约日 2026-10-09，LKUS_push，全部 64 分片）

| 来源 | 类型 | 键（出现行占比） |
|---|---|---|
| `request_strategy_engine` | 对象 | `accessid`(100.0%), `para`(100.0%), `sceneid`(100.0%) |
| `request_strategy_engine` → `$.para` | **JSON 字符串**（需 `CAST(JSON_UNQUOTE(...) AS JSON)`） | `cid`(100.0%), `countryCode`(100.0%), `fullPhoneNo`(100.0%), `phoneCountry`(100.0%), `phoneNo`(100.0%), `realIp`(100.0%), `realIpCity`(100.0%), `realIpCountry`(100.0%), `realIpProvince`(100.0%), `tenant`(100.0%), `uid`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(94.1%), `reviewRepeat`(94.1%), `recaptchaV3Action`(93.3%), `recaptchaV3Token`(93.3%), `app`(85.2%), `userNo`(4.6%), `email`(0.1%) |
| `response_strategy_engine` | 对象 | `errCode`(100.0%), `msg`(100.0%), `re`(100.0%), `status`(100.0%) |
| `response_strategy_engine` → `$.re` | 对象 | `accessId`(100.0%), `extern`(100.0%), `featureDetail`(100.0%), `hitBreakStrategy`(100.0%), `message`(100.0%), `requestId`(100.0%), `resultCode`(100.0%), `resultName`(100.0%), `ruleDetail`(100.0%), `sceneId`(100.0%), `zeusId`(100.0%), `bestPreOnlineStrategyId`(94.7%), `hitPreOnlineStrategy`(94.7%), `bestStrategyId`(45.9%), `hitStrategy`(45.9%) |
| `response`（返回调用方） | 对象 | `code`(100.0%), `detail`(100.0%), `message`(100.0%), `result`(100.0%), `model`(0.8%) |
| `request`（rpc 输入） | 对象 | `cid`(100.0%), `cidOriginEnum`(100.0%), `countryCode`(100.0%), `ip`(100.0%), `phone`(100.0%), `tenant`(100.0%), `uid`(100.0%), `uniqueKey`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(94.1%), `reviewRepeat`(94.1%), `recaptchaV3Action`(93.3%), `recaptchaV3Token`(93.3%), `app`(85.2%), `userNo`(4.6%), `email`(0.1%) |
| `$.re.featureDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `featureId`(100.0%), `name`(100.0%), `result`(100.0%), `type`(100.0%) |
| `$.re.hitStrategy[*]` | 字符串里装数组（CAST 后展开） | `execPriority`(45.9%), `resultName`(45.9%), `status`(45.9%), `strategyId`(45.9%), `strategyName`(45.9%), `strategyType`(45.9%), `vaild`(45.9%) |
| `$.re.hitPreOnlineStrategy[*]` | 字符串里装数组（CAST 后展开） | `execPriority`(94.7%), `resultName`(94.7%), `status`(94.7%), `strategyId`(94.7%), `strategyName`(94.7%), `strategyType`(94.7%), `vaild`(94.7%) |
| `$.re.ruleDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `name`(100.0%), `result`(100.0%), `ruleId`(100.0%), `type`(100.0%) |

- 数组类来源的占比是「带该键的行 / 场景行数」，一个行里有多个元素时仍按行计。`hitBreakStrategy` 当天没有任何元素（`results/p1_keys_hitBreakStrategy_elem.csv` 为空）。

## 体积（纽约日 2026-10-09，LKUS_push 2,129 行，`results/p1_payload_size.csv`）

- 平均每行：`response_strategy_engine` 28,729 B，其中 `featureDetail` 12,687 B、`ruleDetail` 14,524 B；`request_strategy_engine` 3,757 B。
- 永远不要 SELECT 整个 JSON 列：在服务端用 `JSON_TABLE` / `JSON_EXTRACT` 只取标量。

## 基础列的可用性（纽约日 2026-10-09，全部场景，`results/p1_scene_rows.csv`）

- `ip_city`、`ip_province`、`country`、`city` 基础列：全部场景 14,927 行中非空 0 行 → IP 地理只能取 `$.para.realIpCountry/realIpProvince/realIpCity`。
- 设备号：`LKUS_physical_order_create` did 858/5306、device_id 858/5306；`tongdun_device_id` 全部场景非空 0 行。LKUS_push 没有设备号。
- `country_code` 列与 `$.para.countryCode`：7 日 LKUS_push 20,210 行里带 `+` 的 20,210 行、二者相等 20,210 行。
- `result` 列 = `response.$.result`：7 日 20,210 / 20,210 行一致，即返回调用方的最终结果；引擎自己的结果是 `$.re.resultName`。

