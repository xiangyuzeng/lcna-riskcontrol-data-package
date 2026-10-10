# 侦察（2026-10-10 02:51–02:56 纽约时间；只读）

| 文件 | 服务器 | 说明 |
|---|---|---|
| `r1_version.sql` / `.json` | aws-luckyus-iriskcontrolservice-rw | 回复原样 |
| `r2_grants.sql` | 同上 | 回复含账号名与来源主机通配，按提示词「只记权限名」**不原样保存**：权限 = `SELECT, PROCESS, EXECUTE`，范围 `*.*`，共 1 行 |
| `r3_clock.sql` / `.json` | 同上 | 回复原样；本机 `date -u` 在其后约 2 秒读到 `2026-10-10T06:53:04` |
| `u1_upush_version.sql` / `.json` | aws-luckyus-upush-rw | 回复原样 |
| `list_servers`（工具调用，无 SQL） | mcp-db-gateway | 只记计数与名字：MySQL 64、Redis 79、PostgreSQL 1；名字含 riskcontrol / upush / doris / ods / sms 的：MySQL `aws-luckyus-iriskcontrolservice-rw`、`aws-luckyus-upush-rw`、`aws-luckyus-iluckydorisops-rw`；Redis `luckyus-iriskcontrol`、`luckyus-iupush` |
| Redshift `list_clusters` | redshift | 返回错误（不可用） |
| 保留字 | aws-luckyus-iriskcontrolservice-rw | P0 的 KEYWORDS 查询返回 259 行，原样回复在本机 `_local_only/keywords.json`（不进包），词表在 `_local_only/reserved_words.txt` |

本机：`MCP_DB_GATEWAY_SSE` 未设置；Python 3.11.2，`zoneinfo` 可用。并发观察：`RC_data_20261010-0013/_local_only/.db_lock` 在 06:53:39 与 06:55:24 UTC 被重新创建（持锁进程不在本容器）；该包的 zip 与 `.sha256` 时间为 07:12:01 UTC。
