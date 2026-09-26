-- name: p2_oplog_changes
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2 / DR-019 / DR-025: t_operation_log allow-listed before/after fields per change (ids, names, status, priority, counter definition); free text masked; operator masked
-- kind: agg; windows: 33 [2026-08-25 04:00:00 .. 2026-09-27 04:00:00) UTC
-- params: {}
-- run (NY): 2026-09-26 17:49

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.op_id, x.module, x.operation_type, x.operation_time, CASE WHEN x.operator IS NULL OR x.operator = '' THEN x.operator ELSE '<已屏蔽:操作人>' END AS operator, x.src,
  CASE WHEN x.description REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(x.description), '字符>') ELSE x.description END AS description,
  r.row_idx, r.featureId, CASE WHEN r.featureName REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(r.featureName), '字符>') ELSE r.featureName END AS featureName, r.toolId, r.thirdLabel,
  JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.hasCondition')) AS input_hasCondition,
  JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.period')) AS input_period,
  CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.conditionExpress')) REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.conditionExpress'))), '字符>') ELSE JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.conditionExpress')) END AS input_conditionExpress,
  CAST(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.dimension') AS CHAR) AS input_dimension,
  JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.counter')) AS input_counter,
  JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.countValue')) AS input_countValue,
  CASE WHEN CAST(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.conditions') AS CHAR) REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN '<已屏蔽>' ELSE CAST(JSON_EXTRACT(CASE WHEN JSON_TYPE(r.inputParas) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(r.inputParas)) THEN CAST(JSON_UNQUOTE(r.inputParas) AS JSON) ELSE r.inputParas END, '$.conditions') AS CHAR) END AS input_conditions,
  r.strategyId, CASE WHEN r.strategyName REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(r.strategyName), '字符>') ELSE r.strategyName END AS strategyName, r.status, r.resultName, r.execPriority, r.sceneId, r.ruleOperator,
  CASE WHEN r.strategyExpress REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(r.strategyExpress), '字符>') ELSE r.strategyExpress END AS strategyExpress, JSON_LENGTH(r.rulePoList) AS n_rules, CAST(JSON_EXTRACT(r.rulePoList, '$[*].ruleId') AS CHAR) AS rule_ids,
  r.ruleId, CASE WHEN r.ruleName REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(r.ruleName), '字符>') ELSE r.ruleName END AS ruleName, r.ruleFeatureId, r.conditionType, CASE WHEN r.conditionValue REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(r.conditionValue), '字符>') ELSE r.conditionValue END AS conditionValue,
  r.paraId, r.paraName, r.resultCode, r.priority, r.sceneName, r.globalStrategyBlockStatus, r.sceneBlockStatus,
  CASE WHEN r.updateTime REGEXP '^[0-9]{13}$' THEN DATE_FORMAT(FROM_UNIXTIME(r.updateTime / 1000), '%Y-%m-%d %H:%i:%s') ELSE r.updateTime END AS update_time_utc, r.vaild
FROM (SELECT id AS op_id, module, operation_type, operation_time, operator, description, 'before' AS src, CAST(before_data AS JSON) AS j
      FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(before_data)
      UNION ALL
      SELECT id, module, operation_type, operation_time, operator, description, 'after', CAST(after_data AS JSON)
      FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(after_data)) x,
  JSON_TABLE(JSON_EXTRACT(x.j, '$.rows'), '$[*]' COLUMNS (
    row_idx FOR ORDINALITY,
    featureId VARCHAR(64) PATH '$.featureId', featureName VARCHAR(512) PATH '$.featureName', toolId VARCHAR(64) PATH '$.toolId',
    thirdLabel VARCHAR(128) PATH '$.thirdLabel', inputParas JSON PATH '$.inputParas',
    strategyId VARCHAR(64) PATH '$.strategyId', strategyName VARCHAR(512) PATH '$.strategyName', status VARCHAR(16) PATH '$.status',
    resultName VARCHAR(64) PATH '$.resultName', execPriority VARCHAR(32) PATH '$.execPriority', sceneId VARCHAR(64) PATH '$.sceneId',
    ruleOperator VARCHAR(16) PATH '$.ruleOperator', strategyExpress VARCHAR(1024) PATH '$.strategyExpress', rulePoList JSON PATH '$.rulePoList',
    ruleId VARCHAR(64) PATH '$.ruleId', ruleName VARCHAR(512) PATH '$.ruleName', ruleFeatureId VARCHAR(64) PATH '$.featureId',
    conditionType VARCHAR(64) PATH '$.conditionType', conditionValue VARCHAR(4000) PATH '$.conditionValue',
    paraId VARCHAR(64) PATH '$.paraId', paraName VARCHAR(128) PATH '$.paraName', resultCode VARCHAR(32) PATH '$.resultCode',
    priority VARCHAR(32) PATH '$.priority', sceneName VARCHAR(128) PATH '$.sceneName',
    globalStrategyBlockStatus VARCHAR(16) PATH '$.globalStrategyBlockStatus', sceneBlockStatus VARCHAR(16) PATH '$.sceneBlockStatus',
    updateTime VARCHAR(32) PATH '$.updateTime', vaild VARCHAR(16) PATH '$.vaild')) r
ORDER BY x.operation_time, x.op_id, x.src, r.row_idx
