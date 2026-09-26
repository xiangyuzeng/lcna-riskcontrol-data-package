# Grafana「北美风控巡检大盘」短信面板 SQL（原文，只读取自 MCP server `grafana-lucky` 的 get_dashboard_property）

- 读取时间：2026-09-26 17:27 (NY)；dashboard 版本 6，最后修改 2026-09-18（UTC）
- 数据源：Grafana datasource `Doris-iriskcontrol`（type mysql，database `ods_luckyus_iriskcontrol`）；本会话无法经 MCP 执行这些 SQL（DR-020）
- 面板：`${tenant}-短信调用趋势`、`${tenant}-（非当地区号）短信调用趋势`、`${tenant}-（非当地区号）短信PASS比例趋势`（另有注册/登录/下单行）

```sql
-- 面板 23：短信调用趋势
SELECT UNIX_TIMESTAMP(CONVERT_TZ(DATE_TRUNC(CONVERT_TZ(access_time, 'UTC', 'America/New_York'), 'day'), 'America/New_York', 'UTC')) AS time,
    COUNT(CASE WHEN result = 'PASS' THEN 1 END) AS PASS,
    COUNT(CASE WHEN result = 'REJECT' THEN 1 END) AS REJECT,
    COUNT(CASE WHEN result = 'REVIEW' THEN 1 END) AS REVIEW
FROM t_iriskcontrol_log
WHERE $__timeFilter(access_time) AND l1_scene = '1000' AND l2_scene = '1001'
  AND (CASE WHEN '${tenant}' = '' THEN TRUE ELSE tenant = '${tenant}' END)
GROUP BY DATE_TRUNC(CONVERT_TZ(access_time, 'UTC', 'America/New_York'), 'day')
ORDER BY DATE_TRUNC(CONVERT_TZ(access_time, 'UTC', 'America/New_York'), 'day');

-- 面板 24：（非当地区号）短信调用趋势 = 面板 23 + 条件
--   AND (CASE WHEN '${tenant}' = 'LKUS' THEN country_code <> '+1' ELSE 1 = 1 END)

-- 面板 25：（非当地区号）短信PASS比例趋势 = PASS 中 country_code <> '+1' 的占比（LKUS）
--   ... AND result = 'PASS'；rate = COUNT(CASE WHEN ('${tenant}'='LKUS' AND country_code <> '+1') OR ('${tenant}' NOT IN ('LKUS')) THEN 1 END) / COUNT(*)
```

要点（供 DR-002 / DR-013 / 巡检口径对齐）：
1. 大盘按纽约自然日分桶（`CONVERT_TZ(access_time,'UTC','America/New_York')`），与本包口径一致。
2. 短信 = `l1_scene='1000' AND l2_scene='1001'`：数仓里现成的列，大盘不做派生；源库没有该列，本包用 `$.para.email` 为空作短信口径（DR-002）。
3. Doris `country_code` 以 `'+1'` 形式比较，说明数仓侧也带 `+`（与提示词 §2.4 一致）。若某行写成 `'1'`，会被大盘算进「非当地区号」。
