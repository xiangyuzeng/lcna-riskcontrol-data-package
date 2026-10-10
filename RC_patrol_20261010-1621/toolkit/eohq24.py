#!/usr/bin/env python3
"""eohq24.py — aggregate-only evidence for a pre-online strategy (first written for strategy_eoHQ6Qs0FRqp, 2026-10-10; --sid is required).

Same machinery and rules as patrol24.py: statements are written to files, each passes shard_runner.guard(), covers
<= 16 shards, reads only the push scene, and returns grouped counts (never a phone number, IP, uid or hash: the phone
key `sharding_key` appears only inside GROUP BY / a correlated COUNT). Path A (default since 2026-10-10): `run` resolves
the gateway like patrol24 and lets patrol24's child process send the files; path B: send them one at a time with the
mcp-db-gateway query tool, save each reply verbatim as <file>.json, `gate`, then `collect`. Statements only leave between
NY 22:00 and 05:30 (production pull window).
Population: SMS rows (empty $.para.email) whose code is not 1 / 86 (dim) or is in codes_21.txt (phone, recount).
  emit --kind dim     --dim NAME  --utc 'A~B' [--hits-only]   NAME x pre-online hit x online hit x final result
  emit --kind phone   --utc 'A~B'                             requests per phone (buckets) x any hit of the strategy
  emit --kind recount --utc 'A~B'                             same-phone requests in the previous hour, recomputed in SQL
                                                              (not the engine's own counter value) x hits x NY/NJ flag
  emit --kind upush   --utc 'A~B'                             upush send log: sent / filled per window by code group
                                                              (each of the 21 codes, 1, 86, empty, other)
                                                              (user-approved 2026-10-10: COUNT/SUM only, never mobile)
  emit --kind upush_extra --table t_collect_verifycode --time-col C --time-index I --code-col A [--status-col S]
       [--tenant-col N] --utc 'A~B'                           other upush tables (user-approved 2026-10-10 ~08:00: column
                                                              names first, then COUNT grouped by window x code group
                                                              [x a bounded status value] only). Only t_collect_verifycode for
                                                              data (sms_sent_00NN / sms_receipt_00NN are 32 hash shards: names
                                                              only); personal-looking names refused; status columns allowlisted;
                                                              FORCE INDEX (I); the gate demands a range scan on I
  gate RUN_DIR                                                load check (s0a, s0b) and EXPLAIN (s0d) -> GO / WAIT / STOP
  collect RUN_DIR                                             checks each reply's window / shard range, sums -> results/eohq_*.csv
Like patrol24, emit exits 3 when another database run looks active (add --m1-active-ok only after the user agrees).
  run  (same options as emit) [--no-cli]                    path A: resolve the gateway, send through patrol24's child, collect
Windows: 'A~B' in UTC ('YYYY-MM-DD HH:MM:SS~YYYY-MM-DD HH:MM:SS'), cut into pieces of --chunk-h hours
(default 24; recount 23, because its second table reference spans the piece plus one hour and must stay <= 24 h).
"""
import argparse, csv, json, os, re, sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patrol24 as P  # noqa: E402
import shard_runner  # noqa: E402

PARA = ("CASE WHEN JSON_VALID(l.request_strategy_engine) AND JSON_VALID(l.request_strategy_engine->>'$.para') "
        "THEN CAST(l.request_strategy_engine->>'$.para' AS JSON) END")
PROV = f"JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.realIpProvince'))"
DIMS = {  # fixed, reviewed expressions only; every value is a code, a place name, a version or a bucket
    "cc": "TRIM(LEADING '+' FROM TRIM(l.country_code))",
    "ip_country": f"JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.realIpCountry'))",
    "phone_country": f"JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.phoneCountry'))",
    "ip_province": PROV,
    "province_flag": f"CASE COALESCE({PROV}, '') WHEN 'New York' THEN 'New York' WHEN 'New Jersey' THEN 'New Jersey' WHEN '' THEN 'none' ELSE 'other' END",
    "cid": f"JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.cid'))",
    "app_version": f"CONCAT(COALESCE(JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.app')), 'no_app'), ' ', COALESCE(JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.version')), 'no_version'))",
    "token": f"CASE WHEN JSON_EXTRACT({PARA}, '$.recaptchaV3Token') IS NULL THEN 'absent' "
             f"WHEN JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.recaptchaV3Token')) = '' THEN 'empty' ELSE 'present' END",
    "hour_utc": "DATE_FORMAT(l.create_time, '%Y-%m-%d %H')",
}
HIT = "IFNULL(LOCATE('{sid}', l.response_strategy_engine->>'$.re.{arr}'), 0) > 0"
EMAIL_EMPTY = f"COALESCE(JSON_UNQUOTE(JSON_EXTRACT({PARA}, '$.email')), '') IN ('', 'null')"   # = patrol24 / L1 SMS flag
CC = "TRIM(LEADING '+' FROM TRIM(COALESCE(l.country_code, '')))"
BOUNDS = "l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'"
TBL = "luckyus_iriskcontrolservice.{tbl}"

BRANCH = {
    "dim": ("(SELECT '{shard}' AS s, l.result AS r, {dim} AS d, " + HIT.replace("{arr}", "hitPreOnlineStrategy") + " AS hp, "
            + HIT.replace("{arr}", "hitStrategy") + " AS ho, " + CC + " IN ({codes}) AS k21 FROM " + TBL + " l WHERE " + BOUNDS
            + " AND " + EMAIL_EMPTY + " AND " + CC + " NOT IN ('', '1', '86'))"),
    "phone": ("(SELECT '{shard}' AS s, COUNT(*) AS q, SUM(l.result = 'PASS') AS pq, MAX(" + HIT.replace("{arr}", "hitPreOnlineStrategy")
              + " OR " + HIT.replace("{arr}", "hitStrategy") + ") AS h FROM " + TBL + " l WHERE " + BOUNDS + " AND " + EMAIL_EMPTY
              + " AND " + CC + " IN ({codes}) GROUP BY l.sharding_key)"),
    "recount": ("(SELECT '{shard}' AS s, l.result AS r, " + HIT.replace("{arr}", "hitPreOnlineStrategy") + " AS hp, "
                + HIT.replace("{arr}", "hitStrategy") + " AS ho, " + DIMS["province_flag"] + " AS pv, "
                "(SELECT COUNT(*) FROM " + TBL + " p WHERE p.create_time >= '{utc_prev}' AND p.create_time < '{utc_end}' "
                "AND p.scene_id = '{scene}' AND p.sharding_key = l.sharding_key AND p.create_time > l.create_time - INTERVAL 1 HOUR "
                "AND p.create_time <= l.create_time) AS q FROM " + TBL + " l WHERE " + BOUNDS + " AND " + EMAIL_EMPTY
                + " AND " + CC + " IN ({codes}))"),
}
H = "SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS window_start_utc, '{shard_range}' AS shard_range, "
OUTER = {
    "dim": H + "u.d AS dim_value, u.hp AS hit_pre, u.ho AS hit_on, u.r AS final_result, SUM(u.k21) AS in_21, COUNT(*) AS n "
               "FROM ({branches}) u {where}GROUP BY u.d, u.hp, u.ho, u.r",
    "phone": H + "CASE WHEN u.q = 1 THEN '1' WHEN u.q = 2 THEN '2' WHEN u.q <= 5 THEN '3-5' WHEN u.q <= 10 THEN '6-10' ELSE '11+' END "
                 "AS req_bucket, u.h AS any_hit, COUNT(*) AS phones, SUM(u.q) AS requests, SUM(u.pq) AS pass_requests "
                 "FROM ({branches}) u GROUP BY req_bucket, any_hit",
    "recount": H + "u.hp AS hit_pre, u.ho AS hit_on, u.pv AS province_flag, CASE WHEN u.q >= 5 THEN '5+' ELSE CAST(u.q AS CHAR) END "
                   "AS same_phone_1h, u.r AS final_result, COUNT(*) AS n FROM ({branches}) u "
                   "GROUP BY hit_pre, hit_on, province_flag, same_phone_1h, final_result",
}
AC = "TRIM(LEADING '+' FROM TRIM(COALESCE(s.area_code, '')))"
UPUSH = ("SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS window_start_utc, CASE WHEN " + AC + " IN ({codes}) THEN " + AC
         + " WHEN " + AC + " IN ('1', '86') THEN " + AC + " WHEN " + AC + " = '' THEN 'empty' ELSE 'other' END AS code_group, "
         "COUNT(*) AS sent, SUM(s.filled = 1) AS filled_n, SUM(s.filled IS NULL) AS filled_null FROM luckyus_iupushsms.t_sent_verifycode_sms s "
         "WHERE s.tenant = 'LKUS' AND s.deliver_time >= '{utc_start}' AND s.deliver_time < '{utc_end}' GROUP BY code_group")
UPUSH_SERVER = "aws-luckyus-upush-rw"
UPUSH_SCHEMA = "luckyus_iupushsms"
EXTRA_TABLE = re.compile(r"^t_collect_verifycode$")   # sms_sent_00NN / sms_receipt_00NN are 32 hash shards each: metadata only
STATUS_OK = re.compile(r"^(checked|filled|status|state|result|send_status|receipt_status|deliver_status|err_code|error_code)$|_(status|state)$")
UPUSH_KEYS = ["idx_tenant_time_area", "idx_deliver_time"]
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
PERSONAL = re.compile(r"(mobile|phone|msisdn|^tel|_tel|user|uid|member|customer|account|content|text|body|mask|token|email|device|"
                      r"sms_id|msg|message|sid$|^ip$|^ip_|_ip$|address|name|openid|card|receiv|recipient|^to_|dest|remark|reason|"
                      r"desc|verify|trace|callback|err_?msg)", re.I)


def extra_sql(a, s, e, qc):
    """One aggregate statement on an approved upush table (validated names only; see upush_extra_check)."""
    t, tc, cc = a.table, a.time_col, a.code_col
    ac = f"TRIM(LEADING '+' FROM TRIM(COALESCE(CAST(x.{cc} AS CHAR), '')))"
    sv = f"CAST(x.{a.status_col} AS CHAR)"
    st = (f", CASE WHEN x.{a.status_col} IS NULL THEN 'null' WHEN CHAR_LENGTH({sv}) <= 16 AND {sv} NOT REGEXP '[0-9]{{5,}}' "
          f"AND {sv} NOT REGEXP '[@+]' THEN {sv} ELSE 'other' END AS status_value") if a.status_col else ""
    sg = ", status_value" if a.status_col else ""
    tn = f" AND x.{a.tenant_col} = 'LKUS'" if a.tenant_col else ""
    return (f"SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{s}' AS window_start_utc, CASE WHEN {ac} IN ({qc}) THEN {ac} "
            f"WHEN {ac} IN ('1', '86') THEN {ac} WHEN {ac} = '' THEN 'empty' ELSE 'other' END AS code_group{st}, COUNT(*) AS n "
            f"FROM {UPUSH_SCHEMA}.{t} x FORCE INDEX ({a.time_index}) WHERE x.{tc} >= '{s}' AND x.{tc} < '{e}'{tn} GROUP BY code_group{sg}\n")


def upush_extra_check(a, sql=None):
    """Names must be plain identifiers, the table one of the approved ones, no column may look personal; the statement
    must carry exactly one literal range <= 24 h on the time column and pass shard_runner.guard()."""
    if not (a.table and EXTRA_TABLE.match(a.table)):
        raise P.Fail(2, "--table must be t_collect_verifycode. sms_sent_00NN / sms_receipt_00NN are 32 hash shards each (no "
                        "shard mode yet: names, row estimates and indexes only); *mobile* tables and everything else: names only")
    if a.status_col and not STATUS_OK.match(a.status_col):
        raise P.Fail(2, f"--status-col {a.status_col!r}: only plain status / flag columns (checked, filled, status, *_status …)")
    if not (getattr(a, "time_index", None) and IDENT.match(a.time_index)):
        raise P.Fail(2, "--time-index is required: the index whose first column is --time-col (from information_schema.STATISTICS)")
    for k in ("time_col", "code_col", "status_col", "tenant_col"):
        v = getattr(a, k, None)
        if v and (not IDENT.match(v) or PERSONAL.search(v)):
            raise P.Fail(2, f"--{k.replace('_', '-')} {v!r}: not a plain column name, or it looks personal")
    if not (a.time_col and a.code_col):
        raise P.Fail(2, "--time-col and --code-col are required (take them from information_schema.COLUMNS first)")
    if sql is None:
        return
    shard_runner.guard(sql, "agg")
    lo = re.findall(rf"x\.{a.time_col}\s*>=\s*'([^']+)'", sql)
    hi = re.findall(rf"x\.{a.time_col}\s*<\s*'([^']+)'", sql)
    if len(lo) != 1 or len(hi) != 1:
        raise shard_runner.GuardError("upush_extra statement needs one literal time range")
    span = (datetime.strptime(hi[0], P.FMT) - datetime.strptime(lo[0], P.FMT)).total_seconds()
    if not 0 < span <= 86400:
        raise shard_runner.GuardError(f"upush_extra window {span:.0f}s outside (0, 86400]")


def pieces(spec, chunk_h):
    a, b = (datetime.strptime(x.strip().replace("T", " ")[:19], P.FMT) for x in spec.split("~"))
    out = []
    while a < b:
        e = min(a + timedelta(hours=chunk_h), b)
        out.append((a, e))
        a = e
    return out


def upush_guard(sql):
    """shard_runner.guard() does not know the upush log table: also demand literal deliver_time bounds <= 24 h."""
    shard_runner.guard(sql, "agg")
    import re
    lo = re.findall(r"deliver_time\s*>=\s*'([^']+)'", sql)
    hi = re.findall(r"deliver_time\s*<\s*'([^']+)'", sql)
    if len(lo) != 1 or len(hi) != 1:
        raise shard_runner.GuardError("upush statement needs one literal deliver_time range")
    span = (datetime.strptime(hi[0], P.FMT) - datetime.strptime(lo[0], P.FMT)).total_seconds()
    if not 0 < span <= 86400:
        raise shard_runner.GuardError(f"upush window {span:.0f}s outside (0, 86400]")
    if re.search(r"\b(mobile|mask_no|content|user_id|sms_id)\b", sql, flags=re.I):
        raise shard_runner.GuardError("upush statement names a personal-data column")


def cmd_emit(a, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    P.cmd_init()
    P.load_reserved()
    sig, stale = P.other_db_runs()
    if sig and not a.m1_active_ok:
        raise P.Fail(3, "另一个查库任务可能正在跑（" + "；".join(sig) + "）。eoHQ 这几组语句比巡检大得多：先问用户，"
                        "同意后加 --m1-active-ok 再跑，并且只做提示词里写的精简范围。")
    codes = P.codes21(a.codes)
    if a.kind == "upush_extra":
        upush_extra_check(a)          # before any folder is created
    chunk = a.chunk_h or (23 if a.kind == "recount" else 24)
    if a.kind == "recount" and chunk > 23:
        raise P.Fail(2, "recount pieces must be <= 23 h (the correlated reference spans the piece plus one hour)")
    wins = pieces(a.utc, chunk)
    run_id = datetime.now(timezone.utc).astimezone(P.NY).strftime("%Y%m%d-%H%M%S")
    tag = f"{a.kind}_{a.dim}" if a.kind == "dim" else f"{a.kind}_{a.table}" if a.kind == "upush_extra" else a.kind
    base, n = run_id, 1
    rd = os.path.join(P.PKG, "runs", f"{run_id}_eohq_{tag}")
    while os.path.exists(rd) or any(os.path.basename(x).startswith(run_id + "_") for x in os.listdir(os.path.join(P.PKG, "runs"))):
        n += 1
        run_id = f"{base}-{n}"            # unique id, so two runs in the same second never share a results file
        rd = os.path.join(P.PKG, "runs", f"{run_id}_eohq_{tag}")
    os.makedirs(rd)
    files, servers = [], {}
    qc = ", ".join(f"'{c}'" for c in codes)
    if a.kind not in ("upush", "upush_extra") and not (a.sid and a.sid.startswith("strategy_") and a.sid.replace("_", "").isalnum()):
        raise P.Fail(2, "--sid strategy_<id> is required (take it from the live config, not from memory)")
    srv = UPUSH_SERVER if a.kind in ("upush", "upush_extra") else shard_runner.RISK_SERVER
    for name, sql in (("s0a_processlist.sql", P.S0A), ("s0b_threads.sql", P.S0B)):
        P.check(sql)
        open(os.path.join(rd, name), "w").write(sql)
        files.append(name); servers[name] = srv
    if a.kind in ("upush", "upush_extra"):
        for i, (s, e) in enumerate(wins, 1):
            if a.kind == "upush":
                sql = P.fill(UPUSH, dict(utc_start=s.strftime(P.FMT), utc_end=e.strftime(P.FMT), codes=qc)) + "\n"
                upush_guard(sql)
            else:
                sql = extra_sql(a, s.strftime(P.FMT), e.strftime(P.FMT), qc)
                upush_extra_check(a, sql)
            name = f"u{i:02d}.sql"
            open(os.path.join(rd, name), "w").write(sql)
            files.append(name); servers[name] = UPUSH_SERVER
        sql = "EXPLAIN " + open(os.path.join(rd, "u01.sql")).read()
        shard_runner.guard(sql, "agg")
        open(os.path.join(rd, "s0d_explain.sql"), "w").write(sql)
        files.insert(2, "s0d_explain.sql"); servers["s0d_explain.sql"] = UPUSH_SERVER
    else:
        shards = P.shard_names()
        if shards is None:
            raise P.Fail(2, "config/shards.json missing: run the patrol24 discovery first")
        if a.kind == "dim" and a.dim not in DIMS:
            raise P.Fail(2, f"--dim must be one of {', '.join(DIMS)}")
        groups = [shards[i:i + P.BATCH] for i in range(0, len(shards), P.BATCH)]
        branch, outer = BRANCH[a.kind], OUTER[a.kind]
        where = "WHERE u.hp OR u.ho " if a.hits_only else ""
        for i, (s, e) in enumerate(wins, 1):
            for gi, g in enumerate(groups, 1):
                brs = [P.fill(branch, dict(shard=sh, tbl=f"t_access_log_{sh}", utc_start=s.strftime(P.FMT), utc_end=e.strftime(P.FMT),
                                           utc_prev=(s - timedelta(hours=1)).strftime(P.FMT), scene=P.SCENE, sid=a.sid, codes=qc,
                                           dim=DIMS.get(a.dim, ""))) for sh in g]
                sql = P.fill(outer, dict(utc_start=s.strftime(P.FMT), shard_range=f"{g[0]}..{g[-1]}", where=where,
                                         branches=" UNION ALL ".join(brs))) + "\n"
                P.check(sql)
                name = f"w{i:02d}_g{gi}.sql"
                open(os.path.join(rd, name), "w").write(sql)
                files.append(name); servers[name] = shard_runner.RISK_SERVER
        sql = "EXPLAIN " + open(os.path.join(rd, "w01_g1.sql")).read()
        P.check(sql)
        open(os.path.join(rd, "s0d_explain.sql"), "w").write(sql)
        files.insert(2, "s0d_explain.sql"); servers["s0d_explain.sql"] = shard_runner.RISK_SERVER
    groups = [] if a.kind in ("upush", "upush_extra") else [[g[0], g[-1]] for g in [P.shard_names()[i:i + P.BATCH] for i in range(0, len(P.shard_names()), P.BATCH)]]
    json.dump({"tool": "eohq24", "run_id": run_id, "kind": a.kind, "dim": a.dim, "table": getattr(a, "table", None),
               "explain_keys": UPUSH_KEYS if a.kind == "upush" else [a.time_index] if a.kind == "upush_extra" else None, "sid": a.sid, "hits_only": a.hits_only, "files": files,
               "servers": servers, "groups": groups, "m1_active_ok": bool(a.m1_active_ok), "m1_signals": sig,
               "windows": [[s.strftime(P.FMT), e.strftime(P.FMT)] for s, e in wins]},
              open(os.path.join(rd, "manifest.json"), "w"), indent=1)
    rel = os.path.relpath(rd, P.PKG)
    print(f"{len(files)} files in {rel}/ (guard-checked). Send s0a, s0b, s0d (server per file in manifest.json), run "
          f"`eohq24.py gate {rel}`; if GO, send the rest one at a time, save each reply verbatim as <name>.json, then "
          f"`eohq24.py collect {rel}`.")
    if not P.window_open(now_utc, 15):
        print("note: " + P.window_msg(now_utc) + "（文件已写好，发送前再看时间。）")
    return rd


def cmd_gate(a, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    if not P.window_open(now_utc, 15):
        print("LATE: " + P.window_msg(now_utc)); raise SystemExit(2)
    rd = a.run_dir.rstrip("/")
    pl, tr, ex = (P.reply(rd, n) for n in ("s0a_processlist", "s0b_threads", "s0d_explain"))
    if None in (pl, tr, ex):
        print("STOP: save the s0a, s0b and s0d replies first"); raise SystemExit(4)
    verdict, why = P.load_check(pl, tr)
    if verdict == "GO":
        man = json.load(open(os.path.join(rd, "manifest.json")))
        ok, txt = (P.explain_ok_upush(ex, man.get("explain_keys")) if man.get("kind") in ("upush", "upush_extra")
                   else P.explain_ok(ex))
        verdict, why = ("GO", why + "; EXPLAIN uses an index") if ok else ("STOP", "EXPLAIN gate failed: " + txt)
    print(f"{verdict}: {why}")
    if verdict != "GO":
        raise SystemExit(7 if verdict == "WAIT" else 4)


def cmd_collect(a):
    import re
    rd = a.run_dir.rstrip("/")
    man = json.load(open(os.path.join(rd, "manifest.json")))
    total, cols_key, cols_num = {}, None, None
    for f in man["files"]:
        if f.startswith("s0"):
            continue
        rows = P.reply(rd, f[:-4])
        if rows is None:
            raise P.Fail(4, f"{f}: reply missing")
        m = re.match(r"[wu](\d+)(?:_g(\d+))?\.sql$", f)
        want_ws = man["windows"][int(m.group(1)) - 1][0]
        want_rg = "{}..{}".format(*man["groups"][int(m.group(2)) - 1]) if m.group(2) else None
        for r in rows:
            if str(r.get("window_start_utc", "")).replace("T", " ")[:19] != want_ws or (want_rg and r.get("shard_range") != want_rg):
                raise P.Fail(4, f"{f}: reply is for window {r.get('window_start_utc')} / shards {r.get('shard_range')}, expected "
                                f"{want_ws} / {want_rg} — wrong file saved or statement mistyped; send it again")
            r = {k: v for k, v in r.items() if k not in ("shard_range",)}
            if cols_key is None:
                cols_num = [k for k in r if k in ("n", "in_21", "phones", "requests", "pass_requests", "sent", "filled_n", "filled_null")]
                cols_key = [k for k in r if k not in cols_num]
            key = tuple("" if r.get(k) is None else str(r.get(k)) for k in cols_key)
            acc = total.setdefault(key, [0] * len(cols_num))
            for i, k in enumerate(cols_num):
                acc[i] += P.num(r.get(k))
    out = [dict(zip(cols_key, k), **dict(zip(cols_num, v))) for k, v in sorted(total.items())]
    tag = (f"{man['kind']}_{man['dim']}" if man["kind"] == "dim" else f"{man['kind']}_{man.get('table')}" if man["kind"] == "upush_extra"
           else man["kind"])
    res = os.path.join(P.PKG, "results", f"eohq_{tag}_{man['run_id']}.csv")
    shard_runner.write_csv(res, out)
    print("\n".join(P.privacy([res])))
    print(f"{len(out)} rows -> {os.path.relpath(res, P.PKG)}")
    return out


def cmd_run(a, now_utc=None, runner=None):
    """Path A: window check, gateway, emit, patrol24's child sends (gate inside), collect."""
    import subprocess
    now_utc = now_utc or datetime.now(timezone.utc)
    P.require_window(now_utc, 15)
    url, where, note = P.resolve_gateway(use_cli=not getattr(a, "no_cli", False))
    if not url:
        raise P.Fail(8, f"没找到可用的 {P.GATEWAY} 地址（{note}）：用路 B。")
    print(f"gateway：{where}（地址不显示）")
    rd = cmd_emit(a, now_utc)
    P._child(rd, url, runner or subprocess.run)
    return cmd_collect(argparse.Namespace(run_dir=rd))


def extra_args(p):
    for k in ("--table", "--time-col", "--time-index", "--code-col", "--status-col", "--tenant-col"):
        p.add_argument(k)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit")
    p.add_argument("--kind", required=True, choices=["dim", "phone", "recount", "upush", "upush_extra"])
    extra_args(p)
    p.add_argument("--dim", default=""); p.add_argument("--sid", help="strategy ID, confirmed in the live config first (E0)")
    p.add_argument("--utc", required=True); p.add_argument("--chunk-h", type=int); p.add_argument("--hits-only", action="store_true")
    p.add_argument("--codes"); p.add_argument("--m1-active-ok", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("--kind", required=True, choices=["dim", "phone", "recount", "upush", "upush_extra"])
    extra_args(p)
    p.add_argument("--dim", default=""); p.add_argument("--sid"); p.add_argument("--utc", required=True)
    p.add_argument("--chunk-h", type=int); p.add_argument("--hits-only", action="store_true"); p.add_argument("--codes")
    p.add_argument("--m1-active-ok", action="store_true"); p.add_argument("--no-cli", action="store_true")
    p = sub.add_parser("gate"); p.add_argument("run_dir")
    p = sub.add_parser("collect"); p.add_argument("run_dir")
    a = ap.parse_args(argv)
    {"emit": cmd_emit, "run": cmd_run, "gate": cmd_gate, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    main()
