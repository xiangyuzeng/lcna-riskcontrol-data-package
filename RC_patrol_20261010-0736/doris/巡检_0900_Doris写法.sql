-- 北美短信例行巡检，Doris 写法（和 21 点那次同口径；没在 Doris 上执行过，第一次跑请对一下 cc_odd_rows 和 newest_utc）
-- 每天只改下面两处的日期（纽约时间 09:00 截止）；CONVERT_TZ 自己处理夏令时，窗口永远是整 24 小时。
-- 这一次：纽约时间 10/10 09:00 至 10/11 09:00 = UTC [2026-10-10 13:00:00, 2026-10-11 13:00:00)
SELECT COUNT(*) AS sms_total,
       SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) AS sms_pass,
       SUM(CASE WHEN result = 'PASS' AND country_code IS NOT NULL AND country_code NOT IN ('', '+1', '1', '+86', '86') THEN 1 ELSE 0 END) AS pass_not_us_cn,
       SUM(CASE WHEN result = 'PASS' AND country_code IN ('+7', '7', '+92', '92', '+375', '375', '+386', '386', '+265', '265', '+856', '856', '+213', '213', '+264', '264', '+60', '60', '+220', '220', '+223', '223', '+992', '992', '+251', '251', '+254', '254', '+380', '380', '+233', '233', '+504', '504', '+258', '258', '+998', '998', '+255', '255', '+855', '855') THEN 1 ELSE 0 END) AS pass_21,
       SUM(CASE WHEN country_code IS NULL OR country_code NOT LIKE '+%' THEN 1 ELSE 0 END) AS cc_odd_rows,
       MAX(access_time) AS newest_utc
FROM t_iriskcontrol_log
WHERE access_time >= DATE_SUB(CONVERT_TZ('2026-10-11 09:00:00', 'America/New_York', 'UTC'), INTERVAL 24 HOUR)
  AND access_time <  CONVERT_TZ('2026-10-11 09:00:00', 'America/New_York', 'UTC')
  AND l1_scene = '1000' AND l2_scene = '1001' AND tenant = 'LKUS';
-- 源库这边第 3 项还去掉了不是 1-4 位数字的区号（历来 0 条）；cc_odd_rows 不为 0 时两边第 3 项可能差这么多。
