# RUN_LOG — RC_data_20260925-0817

Plan: /home/claude/.claude/plans/ (approved 2026-09-25); data mode = script runner; DR-007 strict.

| time (America/New_York) | phase | event | status | note |
|---|---|---|---|---|
| 2026-09-25 08:17 | P0 | start | — | setup + inventory |
| 2026-09-25 08:28 | P0 | end | DONE | runner validated (9/9 identical), batch=16 (0.51 s/stmt heavy pattern), primary, SELECT/PROCESS/EXECUTE only, Doris unreachable |
| 2026-09-25 08:28 | P1 | start | — | locate + document |
| 2026-09-25 09:02 | P1 | end | DONE | fleet sweep 64 MySQL + 1 PG; 64 shards identical; sharding_key = CONCAT(country_code, phone); DR-002/007/014 evidence gathered; privacy scan unresolved 0 |
| 2026-09-25 09:02 | P2 | start | — | config export |
| 2026-09-25 09:20 | P2 | end | DONE | 17 definition tables exported (40 cells masked), lists counted, status semantics verified, op-log timeline; privacy scan unresolved 0 |
| 2026-09-25 09:20 | P3 | start | — | E1 extract + 7-day profile |
| 2026-09-25 10:20 | P3 | end | DONE | E1 37,408 rows (8 NY days incl. warm-up, 768 hourly statements); 03 page generated; E1 vs SQL cross-checks 0 mismatches |
| 2026-09-25 10:20 | P4 | start | — | DR write-up (DR data already pulled: DR-001/003/005/010 series, checkpoint) |
| 2026-09-25 10:25 | P4 | end | DONE | 15 DRs + 4 DR-NEW written (11 已答复 / 3 部分答复 / 0 无法用数据回答); checkpoint reproduced (+4 rows); privacy scan unresolved 0 |
| 2026-09-25 10:25 | P5 | start | — | toolkit templates + tests |
| 2026-09-25 10:42 | P5 | paused | PARTIAL | user asked to pause; tk01–tk06 tested and equal to P3/P4; tk07 blocked by UNION collation error 1271 (fix in _RESUME_续跑说明.md §3.1); toolkit/README.md not written. P6/P7 not started. Resume from _RESUME_续跑说明.md (deadline 2026-09-28) |
| 2026-09-25 11:55 | P5 | resume | — | resumed per approved plan |
| 2026-09-25 11:56 | P5 | end | DONE | tk01–tk07 each tested once, all equal to P3/P4 (results/toolkit_tests/_test_summary.csv); tk07 collation fixed; _runlog header normalized; toolkit/README.md written |
| 2026-09-25 11:56 | P6 | start | — | write-ups + checks |
| 2026-09-25 12:07 | P6 | end | DONE | 05/06/README/NEXT_RUN written; mechanical checks (results/p6_checks.csv: cited paths ok, endpoint in 0 files; 60 unmatched integers reviewed = derived sums/rounded/cited); reviewer agent: 25 items fixed incl. DR-012 → 部分答复 (totals now 10/4/0, supersedes P4 line); stability re-runs 4/4 equal (results/p7_stability.csv); salt deleted |
| 2026-09-25 12:07 | P7 | start | — | package |
| 2026-09-25 12:08 | P7 | end | DONE — MANIFEST and zip follow | stability 4/4 equal; privacy scan 3,272 files, unresolved 0; resume note removed (content in README/NEXT_RUN) |
