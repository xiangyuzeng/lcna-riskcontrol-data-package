# RUN_LOG — RC_data_20260926-1722

> 计划见会话计划（Step C 已批准）。时间为 America/New_York。

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-09-26 17:23 | P0 | start | — | setup + inventory |
| 2026-09-26 17:28 | P0 | end | DONE | primary, SELECT/PROCESS/EXECUTE only; 64 shards; runner = MCP direct 8/8; batch 16 (median 0.44 s); Doris/Redshift unreachable; Redis 13,150 keys |
| 2026-09-26 17:28 | P1 | start | — | sources, dictionary, live checks, fleet sweep |
| 2026-09-26 17:51 | P1 | end | DONE | 64 shards identical (51 cols / 3 indexes); JSON keys per scene; 7-day consistency; fleet sweep 64 MySQL + 1 PG (505 name hits); upush metadata |
| 2026-09-26 17:51 | P2 | start | — | config export (queries done; page pending) |
| 2026-09-26 17:52 | P3 | start | — | E1 extract (NY 09-18 warm-up .. 09-25, hourly, 16 shards/statement, local only) |
| 2026-09-26 17:54 | P2 | end | DONE | 17 definition tables exported (strategy_name 13 + rule free text masked; operator columns masked); list counts; op-log 195 ops → 299 field changes; status semantics verified; exception strategy_43NaEzJmiQFk |
| 2026-09-26 17:56 | P1 | page | DONE | 01 page + dictionary/ (20 pages + empty-table page; 5 comment contradictions flagged) written from this run's results |
| 2026-09-26 18:01 | P3 | extract | DONE | E1 768 hourly statements, 34,574 rows (NY 09-18 warm-up .. 09-25), local only |
| 2026-09-26 18:13 | P3 | end | DONE | profile computed locally; cross-checks vs pure SQL 3/3 with 0 mismatching cells; 03 page generated (regenerated after DR-010) |
| 2026-09-26 18:13 | P4 | start | — | DR queries running (daily series done) |
| 2026-09-26 18:38 | P4 | input | — | DATA_REQUESTS.md received from the user in chat (not in the run folder): DR list now = 待取数 DR-020..026 + 部分答复 DR-002/007/012 + standing DR-003/010/013/014/015 + P3 standing DR-016/017/018; new questions numbered from DR-027 |
| 2026-09-26 19:01 | P4 | end | DONE | 19 DR sections (DATA_REQUESTS.md list); dr007 query failed once on reserved alias utc_date (1064, no partial result), fixed and re-run; DR-002/DR-022 Doris side blocked (DR-020) |
| 2026-09-26 19:01 | P5 | end | DONE | tk01–tk09 each tested once (tk08/tk09 new); 43/43 checks equal (results/toolkit_tests/_test_summary.csv); tk06 re-check output 1/56 violation |
| 2026-09-26 19:01 | P6 | start | — | write-ups + mechanical checks |
| 2026-09-26 19:03 | P6 | end | DONE | 00–06, README, NEXT_RUN, toolkit/README regenerated from final results; mechanical checks results/p6_checks.csv (endpoint 0 files, absolute paths/hosts 0, README DR totals = 04 statuses; 71 unmatched integers = derived sums/IDs); stability 3/3 equal (results/p7_stability.csv); salt deleted |
| 2026-09-26 19:03 | P7 | start | — | privacy scan, MANIFEST, zip, hand-over repo |
| 2026-09-26 19:03 | P7 | end | DONE — MANIFEST and zip follow | privacy scan 3,822 files, unresolved 0 (allowlisted 1: Redis avg TTL); stability 3/3 equal; salt deleted |
