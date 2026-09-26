## 分片键（DR-014）

- `sharding_key` = `CONCAT(country_code, phone)`（带 `+` 的区号 + 手机号）：纽约日 2026-09-25 LKUS_push 2,742 行中 2,742 行成立（`results/p1_sk_concat_check_20260925.csv`）。
- 7 日（2026-09-19…2026-09-25）LKUS_push 29,482 行 `sharding_key = $.para.fullPhoneNo` 成立 29,482 行（`results/p1_chk_consistency.csv`）。
- 请求参数 `fullPhoneNo` 在纽约日 2026-08-18 首次出现：UTC 08:00 这一小时 7 行中 6 行还没有该键，09:00 起全部带（`results/p1_sk_transition_hourly.csv`）。分片键规则本身没有变：此前此后都等于区号 + 手机号。
- 其它场景的分片键见 DR-021（`04_数据问题结论.md#dr-021`）。

## JSON 列结构（只列键，不取值；纽约日 2026-09-25，LKUS_push，全部 64 分片）

| 来源 | 类型 | 键（出现行占比） |
|---|---|---|
| `request_strategy_engine` | 对象 | `accessid`(100.0%), `para`(100.0%), `sceneid`(100.0%) |
| `request_strategy_engine` → `$.para` | **JSON 字符串**（需 `CAST(JSON_UNQUOTE(...) AS JSON)`） | `cid`(100.0%), `countryCode`(100.0%), `fullPhoneNo`(100.0%), `phoneCountry`(100.0%), `phoneNo`(100.0%), `realIp`(100.0%), `realIpCity`(100.0%), `realIpCountry`(100.0%), `realIpProvince`(100.0%), `tenant`(100.0%), `uid`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(92.7%), `reviewRepeat`(92.7%), `recaptchaV3Action`(91.9%), `recaptchaV3Token`(91.9%), `app`(81.1%), `userNo`(4.4%), `email`(0.3%) |
| `response_strategy_engine` | 对象 | `errCode`(100.0%), `msg`(100.0%), `re`(100.0%), `status`(100.0%) |
| `response_strategy_engine` → `$.re` | 对象 | `accessId`(100.0%), `extern`(100.0%), `featureDetail`(100.0%), `hitBreakStrategy`(100.0%), `message`(100.0%), `requestId`(100.0%), `resultCode`(100.0%), `resultName`(100.0%), `ruleDetail`(100.0%), `sceneId`(100.0%), `zeusId`(100.0%), `bestPreOnlineStrategyId`(95.8%), `hitPreOnlineStrategy`(95.8%), `bestStrategyId`(48.3%), `hitStrategy`(48.3%) |
| `response`（返回调用方） | 对象 | `code`(100.0%), `detail`(100.0%), `message`(100.0%), `result`(100.0%), `model`(0.9%) |
| `request`（rpc 输入） | 对象 | `cid`(100.0%), `cidOriginEnum`(100.0%), `countryCode`(100.0%), `ip`(100.0%), `phone`(100.0%), `tenant`(100.0%), `uid`(100.0%), `uniqueKey`(100.0%), `userAgent`(100.0%), `version`(100.0%), `recaptchaV3Enabled`(92.7%), `reviewRepeat`(92.7%), `recaptchaV3Action`(91.9%), `recaptchaV3Token`(91.9%), `app`(81.1%), `userNo`(4.4%), `email`(0.3%) |
| `$.re.featureDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `featureId`(100.0%), `name`(100.0%), `result`(100.0%), `type`(100.0%) |
| `$.re.featureDetail[*].comments` | 对象 | `apiResp`(100.0%) |
| `$.re.hitStrategy[*]` | 字符串里装数组（CAST 后展开） | `execPriority`(48.3%), `resultName`(48.3%), `status`(48.3%), `strategyId`(48.3%), `strategyName`(48.3%), `strategyType`(48.3%), `vaild`(48.3%) |
| `$.re.hitPreOnlineStrategy[*]` | 字符串里装数组（CAST 后展开） | `execPriority`(95.8%), `resultName`(95.8%), `status`(95.8%), `strategyId`(95.8%), `strategyName`(95.8%), `strategyType`(95.8%), `vaild`(95.8%) |
| `$.re.ruleDetail[*]` | 原生数组 | `code`(100.0%), `comments`(100.0%), `name`(100.0%), `result`(100.0%), `ruleId`(100.0%), `type`(100.0%) |

- 数组类来源的占比是「带该键的行 / 场景行数」，一个行里有多个元素时仍按行计。`hitBreakStrategy` 当天没有任何元素（`results/p1_keys_hitBreakStrategy_elem.csv` 为空）。

## 体积（纽约日 2026-09-25，LKUS_push 2,742 行，`results/p1_payload_size.csv`）

- 平均每行：`response_strategy_engine` 27,144 B，其中 `featureDetail` 11,795 B、`ruleDetail` 13,798 B；`request_strategy_engine` 3,696 B。
- 永远不要 SELECT 整个 JSON 列：在服务端用 `JSON_TABLE` / `JSON_EXTRACT` 只取标量。

## 基础列的可用性（纽约日 2026-09-25，全部场景，`results/p1_scene_rows.csv`）

- `ip_city`、`ip_province`、`country`、`city` 基础列：全部场景 15,444 行中非空 0 行 → IP 地理只能取 `$.para.realIpCountry/realIpProvince/realIpCity`。
- 设备号：`LKUS_physical_order_create` did 809/5280、device_id 809/5280；`tongdun_device_id` 全部场景非空 0 行。LKUS_push 没有设备号。
- `country_code` 列与 `$.para.countryCode`：7 日 LKUS_push 29,482 行里带 `+` 的 29,482 行、二者相等 29,482 行。
- `result` 列 = `response.$.result`：7 日 29,482 / 29,482 行一致，即返回调用方的最终结果；引擎自己的结果是 `$.re.resultName`。

