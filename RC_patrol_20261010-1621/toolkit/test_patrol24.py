#!/usr/bin/env python3
"""Offline tests for patrol24.py (no database). Every test works on a copy of this toolkit inside a temp folder laid out
as <tmp>/run/RC_patrol/toolkit/, so nothing is written next to the real toolkit.
  PYTHONDONTWRITEBYTECODE=1 python3 toolkit/test_patrol24.py
"""
import argparse, contextlib, csv, io, json, os, shutil, subprocess, sys, tempfile, time, unittest
from datetime import date, datetime, timedelta, timezone

SRC = os.path.dirname(os.path.abspath(__file__))
UTC = timezone.utc
NEEDED = ["patrol24.py", "eohq24.py", "shard_runner.py", "ny_day_bounds.py", "privacy_scan.py", "codes_21.txt", "patrol24_branch.sql",
          "patrol24_outer.sql", "patrol24_percode.sql", "fixture_ny_0920_0926.csv", "fixture_doris_utc_0913_1008.csv",
          "fixture_slot2100_1003_1009.csv"]


def make_copy():
    tmp = tempfile.mkdtemp(prefix="p24test_")
    tk = os.path.join(tmp, "run", "RC_patrol", "toolkit")
    os.makedirs(tk)
    for f in NEEDED:
        shutil.copy2(os.path.join(SRC, f), tk)
    return tmp, tk


TMP, TK = make_copy()
sys.path.insert(0, TK)
import patrol24 as P  # noqa: E402  (the copy)
import shard_runner as SR  # noqa: E402
SR.RESERVED.update({"ORDER", "KEY", "GROUP", "ROWS", "RANGE"})   # stands in for information_schema.KEYWORDS
PKG = os.path.dirname(TK)
NOW = datetime(2026, 10, 11, 2, 5, tzinfo=UTC)          # 2026-10-10 22:05 New York: inside the production window


def ns(**kw):
    d = dict(date=None, at="21:00", codes=None, per_code=False, m1_active_ok=False, force=True, validate_ny=None, validate_slot=None,
             no_cli=True, allow_missing_shard=False, outside_window_ok=False,
             validate_utc=None, backfill=None, path="B", run_dir=None)
    d.update(kw)
    return argparse.Namespace(**d)


def write_shards(first="0000", last="0063"):
    os.makedirs(os.path.join(PKG, "config"), exist_ok=True)
    json.dump({"count": int(last) - int(first) + 1, "first": f"t_access_log_{first}", "last": f"t_access_log_{last}"},
              open(os.path.join(PKG, "config", "shards.json"), "w"))


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        out = fn(*a, **k)
    return out, buf.getvalue()


class Windows(unittest.TestCase):
    CASES = [  # (NY date, slot, expected UTC start, expected UTC end, expected label)
        ("2026-10-10", "21:00", "2026-10-10 01:00:00", "2026-10-11 01:00:00", "10/9 21:00 至 10/10 21:00"),
        ("2026-10-10", "09:00", "2026-10-09 13:00:00", "2026-10-10 13:00:00", "10/9 09:00 至 10/10 09:00"),
        ("2026-11-01", "21:00", "2026-11-01 02:00:00", "2026-11-02 02:00:00", "10/31 22:00 至 11/1 21:00，跨夏令时切换，按整24小时"),
        ("2026-11-01", "09:00", "2026-10-31 14:00:00", "2026-11-01 14:00:00", "10/31 10:00 至 11/1 09:00，跨夏令时切换，按整24小时"),
        ("2026-11-02", "21:00", "2026-11-02 02:00:00", "2026-11-03 02:00:00", "11/1 21:00 至 11/2 21:00"),
        ("2027-03-14", "21:00", "2027-03-14 01:00:00", "2027-03-15 01:00:00", "3/13 20:00 至 3/14 21:00，跨夏令时切换，按整24小时"),
        ("2027-03-14", "09:00", "2027-03-13 13:00:00", "2027-03-14 13:00:00", "3/13 08:00 至 3/14 09:00，跨夏令时切换，按整24小时"),
    ]

    def test_slots(self):
        for d, at, s, e, lab in self.CASES:
            ws, we = P.slot_window(date.fromisoformat(d), at)
            self.assertEqual(ws.strftime(P.FMT), s, (d, at))
            self.assertEqual(we.strftime(P.FMT), e, (d, at))
            self.assertEqual((we - ws).total_seconds(), 86400)
            self.assertEqual(P.label(ws, we), lab)
            # shard_runner splits an --utc span by whole days from the start: a 24 h slot must stay one window
            wins = SR.windows(argparse.Namespace(ny_days=None, windows_file=None, utc=f"{s}~{e}", chunk="day"))
            self.assertEqual(len(wins), 1)

    def test_latest_slot(self):
        def at(ny):
            return datetime.fromisoformat(ny).replace(tzinfo=P.NY).astimezone(UTC)
        self.assertEqual(P.latest_slot_date(at("2026-10-11 00:30")), date(2026, 10, 10))   # after midnight: previous evening
        self.assertEqual(P.latest_slot_date(at("2026-10-10 21:01")), date(2026, 10, 9))    # inside the 2-minute grace
        self.assertEqual(P.latest_slot_date(at("2026-10-10 21:03")), date(2026, 10, 10))
        self.assertEqual(P.latest_slot_date(at("2026-10-10 10:00"), "09:00"), date(2026, 10, 10))

    def test_no_date_before_the_slot(self):
        def at(ny):
            return datetime.fromisoformat(ny).replace(tzinfo=P.NY).astimezone(UTC)
        for t in ("2026-10-10 19:00", "2026-10-10 20:55", "2026-10-10 21:01"):
            with self.assertRaises(SystemExit, msg=t) as c:
                quiet(P.build_windows, ns(force=False), at(t))
            self.assertEqual(c.exception.code, 2)
        w = P.build_windows(ns(force=False), at("2026-10-11 00:30"))           # after midnight: the evening that just ended
        self.assertEqual(w[0]["key"], "2026-10-10 21:00")
        w = P.build_windows(ns(force=False), at("2026-10-10 21:03"))
        self.assertEqual(w[0]["key"], "2026-10-10 21:00")
        w = P.build_windows(ns(force=False, date="2026-10-10", backfill=3), at("2026-10-10 19:00"))
        self.assertEqual([x["key"] for x in w], ["2026-10-07 21:00", "2026-10-08 21:00", "2026-10-09 21:00"])
        w = P.build_windows(ns(force=False, date="2026-10-09"), at("2026-10-10 19:00"))   # an explicit past evening is fine
        self.assertEqual(w[0]["key"], "2026-10-09 21:00")

    def test_too_early_and_25h(self):
        now = datetime(2026, 10, 11, 0, 30, tzinfo=UTC)   # 20:30 NY on 10-10
        with self.assertRaises(SystemExit) as c:
            quiet(P.build_windows, ns(date="2026-10-10", force=False), now)
        self.assertEqual(c.exception.code, 2)
        with self.assertRaises(SystemExit) as c:
            quiet(P.build_windows, ns(validate_ny="2026-11-01:2026-11-01"), now)
        self.assertEqual(c.exception.code, 2)
        branch = open(os.path.join(TK, "patrol24_branch.sql")).read()
        sql = "SELECT /*+ MAX_EXECUTION_TIME(10000) */ COUNT(*) AS n FROM " + P.fill(branch, dict(
            tbl="t_access_log_0000", utc_start="2026-11-01 04:00:00", utc_end="2026-11-02 05:00:00", scene="LKUS_push")) + " b"
        with self.assertRaises(SR.GuardError):
            SR.guard(sql, "agg")


class Emit(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(os.path.join(PKG, "runs"), ignore_errors=True)
        write_shards()

    def test_slot_files_pass_guard(self):
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10", per_code=True), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual(man["files"][:4], ["s0a_processlist.sql", "s0b_threads.sql", "s0c_shards.sql", "s0d_explain.sql"])
        self.assertEqual([f for f in man["files"] if f.startswith("w01_s")], [f"w01_s{i}.sql" for i in range(1, 5)])
        self.assertEqual(len([f for f in man["files"] if f.startswith("w01_c")]), 4)
        self.assertEqual(man["windows"][0]["start"], "2026-10-10 01:00:00")
        for f in man["files"]:
            sql = open(os.path.join(rd, f)).read()
            SR.guard(sql, "agg")
            self.assertNotIn("{", sql.replace("{4}", ""), f)
            if f.startswith("w01_s"):
                self.assertEqual(sql.count("FROM luckyus_iriskcontrolservice.t_access_log_"), 16)
                self.assertEqual(sql.count("' AS s, id AS i, result AS r"), 16)
                self.assertEqual(sql.count("create_time >= '2026-10-10 01:00:00'"), 16)
                self.assertIn("'7', '92', '375'", sql)
                self.assertLess(len(sql), 12000)
        self.assertIn("t_access_log_0000", open(os.path.join(rd, "s0d_explain.sql")).read())
        self.assertNotIn("t_access_log_0001", open(os.path.join(rd, "s0d_explain.sql")).read())
        s4 = open(os.path.join(rd, "w01_s4.sql")).read()
        self.assertIn("'0048..0063' AS shard_range", s4)

    def test_validate_and_backfill(self):
        rd, _ = quiet(P.cmd_emit, ns(validate_ny="2026-09-20:2026-09-26"), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual(len(man["windows"]), 7)
        self.assertEqual(man["windows"][0]["start"], "2026-09-20 04:00:00")
        self.assertEqual(len([f for f in man["files"] if f.startswith("w")]), 28)
        rd, _ = quiet(P.cmd_emit, ns(validate_ny="2026-09-20,2026-09-23,2026-09-26"), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual([w["key"] for w in man["windows"]], ["2026-09-20", "2026-09-23", "2026-09-26"])
        self.assertEqual(len([f for f in man["files"] if f.startswith("w")]), 12)
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10", backfill=7), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual([w["key"] for w in man["windows"]][0], "2026-10-03 21:00")
        self.assertEqual([w["key"] for w in man["windows"]][-1], "2026-10-09 21:00")

    def test_discovery_first(self):
        os.remove(os.path.join(PKG, "config", "shards.json"))
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10"), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        self.assertEqual(json.load(open(os.path.join(rd, "manifest.json")))["files"], ["s0c_shards.sql"])
        self.assertTrue(rd.endswith("_discover"))
        json.dump({"rows": [{"shard_tables": 64, "first_table": "t_access_log_0000", "last_table": "t_access_log_0063"}]},
                  open(os.path.join(rd, "s0c_shards.json"), "w"))
        quiet(P.cmd_shards, ns(run_dir=rd))
        self.assertEqual(len(P.shard_names()), 64)


GROUPS = [("0000", "0015"), ("0016", "0031"), ("0032", "0047"), ("0048", "0063")]
# synthetic totals split over the four statements; ③ includes +852 (a code outside the 21), ④ only the 21
PARTS = [dict(rows_all=701, email_rows=1, sms_total=700, sms_pass=350, sms_reject=345, sms_review=2, sms_other=3, pass_1=180,
              pass_86=5, pass_empty=0, pass_invalid=0, pass_not_us_cn=165, pass_21=150, pass_not_21=15, sms_cc_empty=0,
              sms_cc_invalid=0, sms_no_plus=0, dup_rows=0, lag_s=4)
         for _ in GROUPS]


def save_replies(rd, man, parts=PARTS, as_strings=False, percode=None, busy=False):
    j = lambda n, rows: json.dump({"rows": rows}, open(os.path.join(rd, n + ".json"), "w"))
    j("s0a_processlist", [{"COMMAND": "Sleep", "n": 40, "max_time_s": 900}, {"COMMAND": "Query", "n": 1, "max_time_s": 30 if busy else 0}])
    j("s0b_threads", [{"Variable_name": "Threads_running", "Value": "2"}])
    j("s0c_shards", [{"shard_tables": 64, "first_table": "t_access_log_0000", "last_table": "t_access_log_0063"}])
    j("s0d_explain", [{"id": 1, "select_type": "PRIMARY", "table": "<derived2>", "type": "ALL", "key": None, "rows": 200},
                      {"id": 3, "select_type": "DERIVED", "table": "t_access_log_0000", "type": "range",
                       "key": "idx_create_time_sharding_key", "rows": 180}])
    for w in man["windows"]:
        for gi, (lo, hi) in enumerate(GROUPS, 1):
            r = dict(dict(shards_seen=16), **parts[gi - 1])
            r.update(window_start_utc=w["start"], window_end_utc=w["end"], shard_range=f"{lo}..{hi}",
                     shard_sum=sum(range(int(lo), int(hi) + 1)),
                     first_utc=w["start"][:-2] + "07",
                     last_utc=(datetime.strptime(w["end"], "%Y-%m-%d %H:%M:%S") - timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S"))
            if as_strings:
                r = {k: (str(v) if isinstance(v, int) else v) for k, v in r.items()}
            j(f"{w['id']}_s{gi}", [r])
            if percode is not None:
                j(f"{w['id']}_c{gi}", [dict(window_start_utc=w["start"], shard_range=f"{lo}..{hi}", cc=c, sms_pass=p, sms_requests=q)
                                       for c, p, q in percode])


class Collect(unittest.TestCase):
    def setUp(self):
        for d in ("runs", "posts", "history", "results"):
            shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
        write_shards()

    def emit(self, **kw):
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10", **kw), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        return rd, json.load(open(os.path.join(rd, "manifest.json")))

    def test_post_golden(self):
        rd, man = self.emit(per_code=True)
        # per group: ③ 165 = 92:100 + 7:50 + 852:10 + 62:5, ④ 150 = 92 + 7 (the per-code replies must add up to the totals)
        save_replies(rd, man, as_strings=True, percode=[("92", 100, 300), ("852", 10, 11), ("62", 5, 6), ("7", 50, 60)])
        self.assertEqual(P.gate(rd, NOW)[0], "GO")
        rows, out = quiet(P.cmd_collect, ns(run_dir=rd))
        golden = ("北美短信例行巡检（纽约时间 10/10 21:00）\n"
                  "最近24小时内（纽约时间 10/9 21:00 至 10/10 21:00）：\n"
                  "1. 短信请求总量 2800\n2. 短信请求pass量 1400\n3. 非美国区号且非中国区号的短信pass量 660\n"
                  "4. 区号在（+7,+92,+375,+386,+265,+856,+213,+264,+60,+220,+223,+992,+251,+254,+380,+233,+504,+258,+998,+255,+855）"
                  "范围内的短信pass量 600\n")
        self.assertIn("----- 复制下面这段发群 -----\n" + golden + "----- 到这里 -----", out)
        self.assertNotRegex(golden, r"\d,\d")
        post = open(os.path.join(PKG, "posts", "巡检_20261010_2100.txt"), encoding="utf-8").read()
        self.assertEqual(post, golden)
        extra = open(os.path.join(PKG, "posts", "巡检_20261010_2100_附加.txt"), encoding="utf-8").read()
        self.assertIn("+852：40", extra)          # 10 in each of the four shard groups
        self.assertIn("+62：20", extra)
        self.assertIn("per-code replies add up", out)
        self.assertNotIn("+92：", extra)
        hist = P.read_hist()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["sms_pass"], "1400")
        self.assertIn("可以发", out)

    def test_percode_mismatch_blocks(self):
        rd, man = self.emit(per_code=True)
        save_replies(rd, man, percode=[("92", 100, 300), ("852", 11, 12), ("62", 5, 6), ("7", 50, 60)])
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)
        self.assertFalse(os.path.exists(os.path.join(PKG, "posts", "巡检_20261010_2100.txt")))
        self.assertEqual(P.read_hist(), [])
        os.remove(os.path.join(rd, "w01_c3.json"))                       # a missing per-code reply also blocks
        save_replies(rd, man, percode=[("92", 100, 300), ("852", 10, 11), ("62", 5, 6), ("7", 50, 60)])
        os.remove(os.path.join(rd, "w01_c3.json"))
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)

    def test_item4_checksum_and_duplicates_and_missing_shard(self):
        for change in ({"pass_21": 130}, {"dup_rows": 17}, {"shards_seen": 15}, {"sms_other": 0}):
            rd, man = self.emit()
            parts = [dict(p) for p in PARTS]
            parts[1].update(change)
            save_replies(rd, man, parts=parts)
            if "shards_seen" in change:
                p = os.path.join(rd, "w01_s2.json"); d = json.load(open(p)); d["rows"][0]["shards_seen"] = 15; json.dump(d, open(p, "w"))
            with self.assertRaises(SystemExit, msg=str(change)) as c:
                quiet(P.cmd_collect, ns(run_dir=rd))
            self.assertEqual(c.exception.code, 4, str(change))

    def test_mistyped_reply_is_caught(self):
        rd, man = self.emit()
        bad = [dict(p) for p in PARTS]
        bad[2]["sms_pass"] = 351          # one digit off in one reply
        save_replies(rd, man, parts=bad)
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)
        self.assertFalse(os.path.exists(os.path.join(PKG, "posts", "巡检_20261010_2100.txt")))

    def test_wrong_window_reply(self):
        rd, man = self.emit()
        save_replies(rd, man)
        p = os.path.join(rd, "w01_s2.json")
        d = json.load(open(p)); d["rows"][0]["window_start_utc"] = "2026-10-09 01:00:00"; json.dump(d, open(p, "w"))
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)

    def test_mistyped_shard_or_bound(self):
        rd, man = self.emit()
        save_replies(rd, man)
        p = os.path.join(rd, "w01_s3.json")
        d = json.load(open(p)); d["rows"][0]["shard_sum"] = sum(range(32, 48)) + 1; json.dump(d, open(p, "w"))
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)
        save_replies(rd, man)
        d = json.load(open(p)); d["rows"][0]["first_utc"] = "2026-10-09 23:59:01"; json.dump(d, open(p, "w"))
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)

    def test_gate_stops_on_bad_s0(self):
        rd, man = self.emit()
        save_replies(rd, man)
        json.dump({"rows": []}, open(os.path.join(rd, "s0b_threads.json"), "w"))
        self.assertEqual(P.gate(rd, NOW)[0], "STOP")
        json.dump({"error": "x"}, open(os.path.join(rd, "s0a_processlist.json"), "w"))
        with self.assertRaises(SystemExit):
            P.gate(rd, NOW)

    def test_gate_wait(self):
        rd, man = self.emit()
        save_replies(rd, man, busy=True)
        self.assertEqual(P.gate(rd, NOW)[0], "WAIT")

    def test_columns_and_list_rows(self):
        rd, man = self.emit()
        save_replies(rd, man)
        p = os.path.join(rd, "w01_s1.json")
        r = json.load(open(p))["rows"][0]
        json.dump({"columns": list(r), "rows": [list(r.values())]}, open(p, "w"))
        rows, _ = quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(rows[0]["sms_total"], 2800)

    def test_validate_ny_fixture(self):
        rd, _ = quiet(P.cmd_emit, ns(validate_ny="2026-09-26:2026-09-26"), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        # the fixture row of 09-26 split as 3 empty statements + 1 statement with everything
        z = {k: 0 for k in P.METRICS}
        full = dict(z, rows_all=2792, email_rows=3, sms_total=2789, sms_pass=1328, sms_reject=1455, sms_review=6, pass_1=763,
                    pass_86=21, pass_not_us_cn=544, pass_21=512, pass_not_21=32, lag_s=1)
        save_replies(rd, man, parts=[dict(z, lag_s=1), dict(z, lag_s=1), dict(z, lag_s=1), full])
        rows, out = quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(rows[0]["fixture"], "match")
        full["pass_21"], full["pass_not_21"] = 511, 33
        save_replies(rd, man, parts=[dict(z, lag_s=1), dict(z, lag_s=1), dict(z, lag_s=1), full])
        with self.assertRaises(SystemExit):
            quiet(P.cmd_collect, ns(run_dir=rd))


class Concurrency(unittest.TestCase):
    def test_runner_process_pattern(self):
        self.assertTrue(P.is_runner("python3 toolkit/shard_runner.py run --name p3 --template x.sql"))
        self.assertTrue(P.is_runner("/usr/bin/python3.11 -u /x/RC_data_1/toolkit/shard_runner.py once --name a"))
        self.assertFalse(P.is_runner("/bin/zsh -c cp toolkit/shard_runner.py /tmp/x"))
        self.assertFalse(P.is_runner("python3 toolkit/test_guard.py"))
        self.assertFalse(P.is_runner("python3 toolkit/shard_runner.py check x.sql"))
        self.assertTrue(P.is_runner("/opt/homebrew/Cellar/python@3.14/3.14.0/Frameworks/Python.framework/Versions/3.14/Resources/"
                                    "Python.app/Contents/MacOS/Python toolkit/shard_runner.py run --name x"))
        self.assertTrue(P.is_runner("python3 -X utf8 toolkit/shard_runner.py run --name x"))
        self.assertTrue(P.is_runner("caffeinate -dims python3 toolkit/shard_runner.py once --name x"))
        self.assertFalse(P.is_runner("-zsh -c python3 toolkit/shard_runner.py run"))

    def test_signals(self):
        rf = os.path.dirname(PKG)
        pkg = os.path.join(rf, "RC_data_20261009-1200")
        os.makedirs(os.path.join(pkg, "_local_only"), exist_ok=True)
        lock = os.path.join(pkg, "_local_only", ".db_lock")
        open(lock, "w").write(str(os.getpid()))
        sig, stale = P.other_db_runs(rf)
        self.assertTrue(any(".db_lock" in s for s in sig))
        open(lock, "w").write("999999")
        sig, stale = P.other_db_runs(rf)
        self.assertTrue(any("another container" in s for s in sig))     # fresh lock whose holder is not visible: live
        old = time.time() - 31 * 60
        os.utime(lock, (old, old))
        sig, stale = P.other_db_runs(rf)
        self.assertTrue(stale and not any(".db_lock" in s for s in sig))
        self.assertTrue(os.path.exists(lock))          # never deleted
        os.remove(lock)
        open(os.path.join(pkg, "RUN_LOG.md"), "w").write("| P3 | 2026-10-10 20:40 | START |\n")
        sig, _ = P.other_db_runs(rf)
        self.assertTrue(any("RUN_LOG" in s for s in sig))
        write_shards()
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_emit, ns(date="2026-10-10", force=True), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        self.assertEqual(c.exception.code, 3)
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10", m1_active_ok=True), datetime(2026, 10, 11, 2, 0, tzinfo=UTC))
        self.assertTrue(json.load(open(os.path.join(rd, "manifest.json")))["m1_active_ok"])
        open(os.path.join(pkg, "RUN_LOG.md"), "a").write("| 20:58 | P1 | end | DONE |\n")      # a phase end is not the run end
        self.assertTrue(any("RUN_LOG" in s for s in P.other_db_runs(rf)[0]))
        open(os.path.join(pkg, "RUN_LOG.md"), "a").write("| 21:10 | P4 | paused |\n")
        self.assertEqual(P.other_db_runs(rf)[0], [])
        open(os.path.join(pkg, "RUN_LOG.md"), "a").write("| 22:00 | P5 | start |\n")
        self.assertTrue(P.other_db_runs(rf)[0])
        open(os.path.join(rf, "RC_data_package_20261009-1200.zip"), "w").write("x")
        open(os.path.join(rf, "RC_data_package_20261009-1200.zip.sha256"), "w").write("x")
        self.assertEqual(P.other_db_runs(rf)[0], [])                   # package zip + sha256 next to it: finished
        os.remove(os.path.join(rf, "RC_data_package_20261009-1200.zip")); os.remove(os.path.join(rf, "RC_data_package_20261009-1200.zip.sha256"))
        open(os.path.join(pkg, "RUN_LOG.md"), "a").write("| 23:00 | P7 | end | DONE |\n")
        self.assertEqual(P.other_db_runs(rf)[0], [])
        shutil.rmtree(pkg)


class EoHQ(unittest.TestCase):
    def setUp(self):
        write_shards()
        import eohq24
        self.E = eohq24

    def args(self, **kw):
        d = dict(kind="dim", dim="cc", sid="strategy_eoHQ6Qs0FRqp", utc="2026-10-09 04:00:00~2026-10-10 04:00:00", chunk_h=None,
                 hits_only=False, codes=None, m1_active_ok=False)
        d.update(kw)
        return argparse.Namespace(**d)

    def test_upush_extra(self):
        a = self.args(kind="upush_extra", sid=None, table="t_collect_verifycode", time_col="collect_time", time_index="idx_collect_time",
                      code_col="area_code", status_col="checked", tenant_col="tenant", utc="2026-10-02 00:00:00~2026-10-04 00:00:00")
        rd, _ = quiet(self.E.cmd_emit, a)
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual(man["files"], ["s0a_processlist.sql", "s0b_threads.sql", "s0d_explain.sql", "u01.sql", "u02.sql"])
        self.assertEqual(set(man["servers"].values()), {"aws-luckyus-upush-rw"})
        self.assertEqual(man["explain_keys"], ["idx_collect_time"])
        sql = open(os.path.join(rd, "u01.sql")).read()
        self.assertIn("x FORCE INDEX (idx_collect_time) WHERE x.collect_time >= '2026-10-02 00:00:00' AND x.collect_time < '2026-10-03 00:00:00'", sql)
        self.assertIn("AND x.tenant = 'LKUS'", sql)
        self.assertIn("ELSE 'other' END AS status_value", sql)          # the status value is bounded in SQL
        self.assertTrue(open(os.path.join(rd, "s0d_explain.sql")).read().startswith("EXPLAIN SELECT"))
        for f in ("u01.sql", "u02.sql", "s0d_explain.sql"):
            SR.guard(open(os.path.join(rd, f)).read(), "agg")
        runs_before = len(os.listdir(os.path.join(PKG, "runs")))
        for bad in (dict(table="sms_receipt_0001"), dict(table="sms_sent_bulk_lucky"), dict(table="t_verifycode_filled_mobile_statistics"),
                    dict(table="t_user"), dict(code_col="mobile"), dict(status_col="error_message"), dict(status_col="user_id"),
                    dict(status_col="remark"), dict(time_col="create_time; DROP"), dict(time_index=None), dict(code_col=None)):
            with self.assertRaises(SystemExit) as c:
                quiet(self.E.cmd_emit, self.args(**{**vars(a), **bad}))
            self.assertEqual(c.exception.code, 2, bad)
        self.assertEqual(len(os.listdir(os.path.join(PKG, "runs"))), runs_before)   # refused before any folder is made

    def test_upush_explain_gate(self):
        ok, _ = P.explain_ok_upush([{"table": "x", "type": "range", "key": "idx_collect_time", "rows": 900}], ["idx_collect_time"])
        self.assertTrue(ok)
        for row in ({"table": "x", "type": "ref", "key": "idx_collect_time", "rows": 9},
                    {"table": "x", "type": "range", "key": "idx_mobile", "rows": 9},
                    {"table": "x", "type": "ALL", "key": None, "rows": 9},
                    {"table": "x", "type": "range", "key": "idx_collect_time", "rows": 900001}):
            self.assertFalse(P.explain_ok_upush([row], ["idx_collect_time"])[0], row)

    def test_run_ids_unique_within_a_second(self):
        r1, _ = quiet(self.E.cmd_emit, self.args(kind="upush", sid=None))
        r2, _ = quiet(self.E.cmd_emit, self.args(kind="upush", sid=None))
        ids = [json.load(open(os.path.join(r, "manifest.json")))["run_id"] for r in (r1, r2)]
        self.assertNotEqual(ids[0], ids[1])

    def test_all_kinds_pass_guard(self):
        for kind, dim in [("dim", d) for d in self.E.DIMS] + [("phone", ""), ("recount", ""), ("upush", "")]:
            rd, _ = quiet(self.E.cmd_emit, self.args(kind=kind, dim=dim))
            man = json.load(open(os.path.join(rd, "manifest.json")))
            for f in man["files"]:
                sql = open(os.path.join(rd, f)).read()
                SR.guard(sql, "agg")
                self.assertNotRegex(sql, r"\{[a-z_]+\}", f)
                self.assertNotRegex(sql, r"\bmobile\b|\bmask_no\b|\bcontent\b", f)
                if kind != "upush" and not f.startswith("s0"):
                    self.assertNotIn("sharding_key AS", sql)
            if kind == "recount":
                self.assertEqual(len([f for f in man["files"] if f.startswith("w")]), 2 * 4)   # 23 h + 1 h pieces x 4 groups
            if kind == "upush":
                self.assertEqual(man["servers"]["u01.sql"], self.E.UPUSH_SERVER)
                self.assertEqual(man["servers"]["s0a_processlist.sql"], self.E.UPUSH_SERVER)
                self.assertIn("AS code_group", open(os.path.join(rd, "u01.sql")).read())

    def test_gate_and_reply_checks(self):
        rd, _ = quiet(self.E.cmd_emit, self.args(kind="dim", dim="cc", hits_only=True))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual(man["files"][:3], ["s0a_processlist.sql", "s0b_threads.sql", "s0d_explain.sql"])
        save_replies(rd, {"windows": []})                                  # s0 replies only
        quiet(self.E.cmd_gate, argparse.Namespace(run_dir=rd), NOW)
        for f in man["files"][3:]:
            m = __import__("re").match(r"w(\d+)_g(\d+)", f)
            lo, hi = man["groups"][int(m.group(2)) - 1]
            json.dump({"rows": [{"window_start_utc": man["windows"][int(m.group(1)) - 1][0], "shard_range": f"{lo}..{hi}",
                                 "dim_value": "92", "hit_pre": 1, "hit_on": 0, "final_result": "PASS", "in_21": 1, "n": 2}]},
                      open(os.path.join(rd, f[:-4] + ".json"), "w"))
        out, _ = quiet(self.E.cmd_collect, argparse.Namespace(run_dir=rd))
        self.assertEqual(out[0]["n"], 8)
        p = os.path.join(rd, "w01_g2.json"); d = json.load(open(p)); d["rows"][0]["shard_range"] = "0000..0015"; json.dump(d, open(p, "w"))
        with self.assertRaises(SystemExit):
            quiet(self.E.cmd_collect, argparse.Namespace(run_dir=rd))

    def test_eohq_concurrency(self):
        rf = os.path.dirname(PKG)
        pkg = os.path.join(rf, "RC_data_20261009-1300")
        os.makedirs(pkg, exist_ok=True)
        open(os.path.join(pkg, "RUN_LOG.md"), "w").write("| P3 | start |\n")
        with self.assertRaises(SystemExit) as c:
            quiet(self.E.cmd_emit, self.args())
        self.assertEqual(c.exception.code, 3)
        quiet(self.E.cmd_emit, self.args(m1_active_ok=True))
        shutil.rmtree(pkg)

    def test_sid_required_and_recount_limit(self):
        with self.assertRaises(SystemExit):
            quiet(self.E.cmd_emit, self.args(sid=None))
        with self.assertRaises(SystemExit):
            quiet(self.E.cmd_emit, self.args(kind="recount", chunk_h=24))
        with self.assertRaises(SR.GuardError):
            self.E.upush_guard("SELECT /*+ MAX_EXECUTION_TIME(10000) */ s.mobile FROM luckyus_iupushsms.t_sent_verifycode_sms s "
                               "WHERE s.deliver_time >= '2026-10-09 04:00:00' AND s.deliver_time < '2026-10-10 04:00:00'")
        with self.assertRaises(SR.GuardError):
            self.E.upush_guard("SELECT /*+ MAX_EXECUTION_TIME(10000) */ COUNT(*) AS n FROM luckyus_iupushsms.t_sent_verifycode_sms s "
                               "WHERE s.deliver_time >= '2026-10-08 04:00:00' AND s.deliver_time < '2026-10-10 04:00:00'")

    def test_collect_sums_groups(self):
        rd, _ = quiet(self.E.cmd_emit, self.args(kind="phone"))
        man = json.load(open(os.path.join(rd, "manifest.json")))
        for f in man["files"][3:]:
            gi = int(f.split("_g")[1][:-4])
            lo, hi = man["groups"][gi - 1]
            json.dump({"rows": [{"window_start_utc": "2026-10-09 04:00:00", "shard_range": f"{lo}..{hi}", "req_bucket": "3-5",
                                 "any_hit": 1, "phones": "2", "requests": 7, "pass_requests": 3}]}, open(os.path.join(rd, f[:-4] + ".json"), "w"))
        out, _ = quiet(self.E.cmd_collect, argparse.Namespace(run_dir=rd))
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["phones"], out[0]["requests"], out[0]["pass_requests"]), (8, 28, 12))


class Misc(unittest.TestCase):
    def test_doris_sql(self):
        _, out = quiet(P.cmd_doris, ns(date="2026-10-11", at="09:00"))
        self.assertIn("UTC [2026-10-10 13:00:00, 2026-10-11 13:00:00)", out)
        self.assertIn("DATE_SUB(CONVERT_TZ('2026-10-11 09:00:00', 'America/New_York', 'UTC'), INTERVAL 24 HOUR)", out)
        self.assertIn("'+92', '92'", out)
        self.assertEqual(out.count("'+"), 21 + 3)          # 21 codes, '+1', '+86', NOT LIKE '+%'
        self.assertIn("l2_scene = '1001'", out)

    def test_send_needs_env_and_run_needs_gateway(self):
        env = dict(os.environ); env.pop("MCP_DB_GATEWAY_SSE", None)
        r = subprocess.run([sys.executable, os.path.join(TK, "patrol24.py"), "_send", TMP], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("path B", r.stderr)
        home = tempfile.mkdtemp(prefix="home_", dir=TMP)
        old = os.environ.get("HOME"); os.environ["HOME"] = home
        old_gw = os.environ.pop("MCP_DB_GATEWAY_SSE", None)   # never let this test reach a real gateway
        try:
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_run, ns(date="2026-10-10", no_cli=True), NOW)
            self.assertEqual(c.exception.code, 8)
            with self.assertRaises(SystemExit) as c:              # no new work after 05:15
                quiet(P.cmd_run, ns(date="2026-10-10", no_cli=True), ny_at("2026-10-11 05:16"))
            self.assertEqual(c.exception.code, 2)
        finally:
            os.environ["HOME"] = old
            if old_gw is not None:
                os.environ["MCP_DB_GATEWAY_SSE"] = old_gw

    def test_verify(self):
        import hashlib
        with open(os.path.join(TK, "SHA256SUMS"), "w") as fh:
            for f in NEEDED:
                fh.write(hashlib.sha256(open(os.path.join(TK, f), "rb").read()).hexdigest() + "  " + f + "\n")
        quiet(P.cmd_verify)
        open(os.path.join(TK, "codes_21.txt"), "a").write("# x\n")
        with self.assertRaises(SystemExit):
            quiet(P.cmd_verify)
        shutil.copy2(os.path.join(SRC, "codes_21.txt"), TK)

    def test_reserved(self):
        p = os.path.join(TMP, "kw.json")
        json.dump({"rows": [{"WORD": w} for w in ["W%03d" % i for i in range(259)]]}, open(p, "w"))
        quiet(P.cmd_reserved, argparse.Namespace(reply=p))
        self.assertEqual(len(open(os.path.join(PKG, "_local_only", "reserved_words.txt")).read().split()), 259)
        json.dump({"rows": [{"w": "ACCESSIBLE ADD ALL"}]}, open(p, "w"))       # a GROUP_CONCAT-style single row is refused
        with self.assertRaises(SystemExit):
            quiet(P.cmd_reserved, argparse.Namespace(reply=p))

    def test_codes(self):
        self.assertEqual(len(P.codes21()), 21)
        self.assertEqual(P.codes21()[:3], ["7", "92", "375"])


def ny_at(txt):
    return datetime.fromisoformat(txt).replace(tzinfo=P.NY).astimezone(UTC)


class ProdWindow(unittest.TestCase):
    def test_bounds_match_the_runner(self):
        self.assertEqual(SR.PROD_WINDOW, ((22, 0), (5, 30)))
        for t, want in (("2026-10-10 21:59", False), ("2026-10-10 22:00", True), ("2026-10-11 05:29", True),
                        ("2026-10-11 05:30", False), ("2026-11-01 22:00", True), ("2026-10-10 12:00", False)):
            self.assertEqual(P.window_open(ny_at(t)), want, t)
            self.assertEqual(SR.prod_window_ok(ny_at(t)), want, t)
        self.assertFalse(P.window_open(ny_at("2026-10-11 05:20"), 15))
        self.assertIn("22:00", P.window_msg(ny_at("2026-10-10 21:30")))
        self.assertIn("21:00", P.window_msg(ny_at("2026-10-10 21:30")))

    def test_refusal_hints(self):
        import eohq24 as E
        day = ny_at("2026-10-10 12:30")
        for k in ("slot", "validate_slot"):
            self.assertIn("run --validate-slot 2026-10-09:2026-10-09 --outside-window-ok", P.window_msg(day, k))
        for t, k in ((day, None), (day, "backfill"), (day, "validate_ny"), (ny_at("2026-10-10 21:30"), "slot"),
                     (ny_at("2026-10-11 12:30"), "slot")):
            self.assertNotIn("--outside-window-ok", P.window_msg(t, k), (t, k))
        self.assertNotIn("replay-test", P.window_msg(day))
        self.assertIn("replay-test", P.window_msg(ny_at("2026-10-11 12:30"), "slot"))
        write_shards()
        rd, _ = quiet(E.cmd_emit, argparse.Namespace(kind="recount", dim="", sid="strategy_eoHQ6Qs0FRqp",
                                                     utc="2026-10-10 01:00:00~2026-10-10 04:00:00", chunk_h=None,
                                                     hits_only=False, codes=None, m1_active_ok=False), NOW)
        out = io.StringIO()
        with self.assertRaises(SystemExit) as c, contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            E.cmd_gate(argparse.Namespace(run_dir=rd), day)
        self.assertEqual(c.exception.code, 2)
        self.assertIn("LATE", out.getvalue())
        self.assertNotIn("outside-window-ok", out.getvalue())

    def test_gate_late_and_run_refused_outside(self):
        write_shards()
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10"), NOW)
        man = json.load(open(os.path.join(rd, "manifest.json")))
        save_replies(rd, man)
        self.assertEqual(P.gate(rd, ny_at("2026-10-10 21:40"))[0], "LATE")
        self.assertEqual(P.gate(rd, ny_at("2026-10-11 05:20"))[0], "LATE")
        self.assertEqual(P.gate(rd, NOW)[0], "GO")
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_run, ns(date="2026-10-10"), ny_at("2026-10-10 21:30"))
        self.assertEqual(c.exception.code, 2)

    def test_default_slot_after_22(self):
        self.assertEqual(P.build_windows(ns(force=False), NOW)[0]["key"], "2026-10-10 21:00")
        self.assertEqual(P.build_windows(ns(force=False), ny_at("2026-10-11 05:15"))[0]["key"], "2026-10-10 21:00")

    def test_explain_empty_range(self):
        self.assertTrue(P.explain_ok([{"id": 1, "type": None, "key": None, "Extra": "No matching min/max row"}])[0])
        self.assertTrue(P.explain_ok([{"type": "range", "key": "idx_create_time_sharding_key", "rows": 100}])[0])
        self.assertFalse(P.explain_ok([{"type": "ALL", "table": "t_access_log_0000", "key": None, "rows": 900000}])[0])


FX = os.path.join(SRC, "fixture_slot2100_1003_1009.csv")


class SlotFixture(unittest.TestCase):
    def test_fixture_rows(self):
        rows = list(csv.DictReader(open(FX, encoding="utf-8")))
        self.assertEqual(len(rows), 7)
        for r in rows:
            v = {k: int(r[k]) for k in r if k not in ("slot_ny", "window_start_utc", "window_end_utc")}
            s = datetime.strptime(r["window_start_utc"], P.FMT).replace(tzinfo=UTC)
            e = datetime.strptime(r["window_end_utc"], P.FMT).replace(tzinfo=UTC)
            self.assertEqual((e - s).total_seconds(), 86400)
            self.assertEqual(e.astimezone(P.NY).strftime("%H:%M"), "21:00")
            self.assertEqual(v["rows_all"], v["email_rows"] + v["sms_total"])
            self.assertEqual(v["sms_total"], v["sms_pass"] + v["sms_reject"] + v["sms_review"] + v["sms_other"])
            self.assertEqual(v["sms_pass"], v["pass_1"] + v["pass_86"] + v["pass_empty"] + v["pass_invalid"] + v["pass_not_us_cn"])
            self.assertEqual(v["pass_not_us_cn"], v["pass_21"] + v["pass_not_21"])
        first, last = rows[0], rows[-1]
        self.assertEqual([first[k] for k in ("sms_total", "sms_pass", "pass_not_us_cn", "pass_21")], ["3319", "2352", "941", "822"])
        self.assertEqual([last[k] for k in ("sms_total", "sms_pass", "pass_not_us_cn", "pass_21")], ["2152", "1235", "214", "152"])

    def test_validate_slot_round_trip_and_history(self):
        for d in ("runs", "history", "results", "posts"):
            shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
        write_shards()
        rd, _ = quiet(P.cmd_emit, ns(validate_slot="2026-10-08,2026-10-09"), NOW)
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertEqual([w["key"] for w in man["windows"]], ["2026-10-08 21:00", "2026-10-09 21:00"])
        fx = {r["slot_ny"]: r for r in csv.DictReader(open(FX, encoding="utf-8"))}
        def put(off_by=0):
            save_replies(rd, {"windows": []})
            for w in man["windows"]:
                r = fx[w["key"]]
                full = {k: int(r[k]) for k in r if k not in ("slot_ny", "window_start_utc", "window_end_utc")}
                full.update(sms_cc_empty=0, sms_cc_invalid=0, sms_no_plus=0, dup_rows=0, lag_s=3)
                if off_by:
                    full["pass_21"] += off_by; full["pass_not_21"] -= off_by
                z = {k: 0 for k in P.METRICS}
                for gi, (lo, hi) in enumerate(GROUPS, 1):
                    part = dict(full if gi == 4 else dict(z, lag_s=3))
                    part.update(window_start_utc=w["start"], window_end_utc=w["end"], shard_range=f"{lo}..{hi}", shards_seen=16,
                                shard_sum=sum(range(int(lo), int(hi) + 1)), first_utc=w["start"],
                                last_utc=(datetime.strptime(w["end"], P.FMT) - timedelta(seconds=1)).strftime(P.FMT))
                    if gi != 4:
                        part.update(rows_all=1, email_rows=1)                  # every group has rows (one email row each)
                    json.dump({"rows": [part]}, open(os.path.join(rd, f"{w['id']}_s{gi}.json"), "w"))
                f4 = os.path.join(rd, f"{w['id']}_s4.json"); d4 = json.load(open(f4))
                d4["rows"][0]["rows_all"] -= 3; d4["rows"][0]["email_rows"] -= 3; json.dump(d4, open(f4, "w"))
        put()
        rows, out = quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual([r["fixture"] for r in rows], ["match", "match"])
        hist = P.read_hist()
        self.assertEqual(sorted(h["kind"] for h in hist), ["validate_slot", "validate_slot"])
        os.remove(os.path.join(PKG, "history", "patrol24_history.csv"))
        put(off_by=1)
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_collect, ns(run_dir=rd))
        self.assertEqual(c.exception.code, 4)
        self.assertEqual(P.read_hist(), [])

    def test_seed_history_keeps_run_rows(self):
        shutil.rmtree(os.path.join(PKG, "history"), ignore_errors=True)
        P.write_hist([dict(slot_ny="2026-10-09 21:00", window_start_utc="2026-10-09 01:00:00", window_end_utc="2026-10-10 01:00:00",
                           sms_total="1", kind="validate_slot")])
        quiet(P.cmd_seed_history, None)
        hist = P.read_hist()
        self.assertEqual(len(hist), 7)
        self.assertEqual([h["kind"] for h in hist if h["window_end_utc"] == "2026-10-10 01:00:00"], ["validate_slot"])


def fake_url():
    return "http" + "://" + "gw" + "." + "invalid" + ":" + str(4000 + 1) + "/" + "sse"


class PathA(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="home_", dir=TMP)
        self.saved = {k: os.environ.get(k) for k in ("HOME", "MCP_DB_GATEWAY_SSE", "PATH")}
        os.environ["HOME"] = self.home
        os.environ.pop("MCP_DB_GATEWAY_SSE", None)

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def write_claude_json(self, obj, raw=None):
        with open(os.path.join(self.home, ".claude.json"), "w") as fh:
            fh.write(raw if raw is not None else json.dumps(obj))

    def test_resolver_precedence_and_rejections(self):
        rf = P.RUN_FOLDER
        u = fake_url()
        self.write_claude_json({"mcpServers": {"mcp-db-gateway": {"type": "sse", "url": u + "?user"}},
                                "projects": {rf: {"mcpServers": {"mcp-db-gateway": {"type": "sse", "url": u}}}}})
        url, where, note = P.resolve_gateway(use_cli=False)
        self.assertEqual((url, where), (u, "本地作用域"))
        self.write_claude_json({"mcpServers": {"mcp-db-gateway": {"type": "sse", "url": u}}})
        self.assertEqual(P.resolve_gateway(use_cli=False)[1], "用户作用域")
        for bad in ({"type": "http", "url": u}, {"type": "sse", "url": u, "headers": {"x": "y"}}, {"type": "sse", "url": "${GW}"},
                    {"type": "stdio", "command": "x"}):
            self.write_claude_json({"mcpServers": {"mcp-db-gateway": bad}})
            url, where, note = P.resolve_gateway(use_cli=False)
            self.assertIsNone(url, bad)
            self.assertNotIn("gw.", note)
        self.write_claude_json(None, raw="{not json")
        self.assertIsNone(P.resolve_gateway(use_cli=False)[0])
        os.environ["MCP_DB_GATEWAY_SSE"] = u
        self.assertEqual(P.resolve_gateway(use_cli=False)[1], "环境变量")
        os.environ.pop("MCP_DB_GATEWAY_SSE")

    def test_project_mcp_json_needs_approval_and_cli_fallback(self):
        rf = P.RUN_FOLDER
        u = fake_url()
        json.dump({"mcpServers": {"mcp-db-gateway": {"type": "sse", "url": u}}}, open(os.path.join(rf, ".mcp.json"), "w"))
        try:
            self.write_claude_json({})
            self.assertIsNone(P.resolve_gateway(use_cli=False)[0])
            self.write_claude_json({"projects": {rf: {"enabledMcpjsonServers": ["mcp-db-gateway"]}}})
            self.assertEqual(P.resolve_gateway(use_cli=False)[1], "项目 .mcp.json")
        finally:
            os.remove(os.path.join(rf, ".mcp.json"))
        self.write_claude_json({})
        bindir = tempfile.mkdtemp(prefix="bin_", dir=TMP)
        with open(os.path.join(bindir, "claude"), "w") as fh:
            fh.write("#!/bin/sh\necho 'mcp-db-gateway:'\necho '  Type: sse'\necho '  URL: " + u + "'\n")
        os.chmod(os.path.join(bindir, "claude"), 0o755)
        os.environ["PATH"] = bindir + os.pathsep + self.saved["PATH"]
        url, where, _ = P.resolve_gateway(use_cli=True)
        self.assertEqual((url, where), (u, "claude mcp get"))
        _, out = quiet(P.cmd_gateway_check, argparse.Namespace(no_cli=False))
        self.assertIn("claude mcp get", out)
        self.assertNotIn("invalid", out)
        self.assertNotIn("4001", out)

    def test_parent_passes_url_only_in_env(self):
        for d in ("runs", "history", "results", "posts"):
            shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
        write_shards()
        u = fake_url()
        self.write_claude_json({"mcpServers": {"mcp-db-gateway": {"type": "sse", "url": u}}})
        seen = {}
        def runner(argv, env=None, **kw):
            seen["argv"], seen["env"] = list(argv), env
            rd = argv[-1]
            man = json.load(open(os.path.join(rd, "manifest.json")))
            save_replies(rd, man, percode=[("92", 100, 300), ("852", 10, 11), ("62", 5, 6), ("7", 50, 60)])
            return argparse.Namespace(returncode=0)
        sh_old = os.path.join(TK, "SHA256SUMS")
        if os.path.exists(sh_old):
            os.rename(sh_old, sh_old + ".bak")
        try:
            buf_out, buf_err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                P.cmd_nightly(argparse.Namespace(m1_active_ok=False, no_cli=True), NOW, runner)
        finally:
            if os.path.exists(sh_old + ".bak"):
                os.rename(sh_old + ".bak", sh_old)
        self.assertNotIn(u, " ".join(seen["argv"]))
        self.assertEqual(seen["env"]["MCP_DB_GATEWAY_SSE"], u)
        self.assertIn("_send", seen["argv"])
        self.assertNotIn("gw.", buf_out.getvalue() + buf_err.getvalue())
        self.assertIn("可以发", buf_out.getvalue())


class FakeGateway:
    """Answers like the gateway, from the statement text alone (window and shard-range literals)."""
    def __init__(self, busy=False):
        self.calls, self.busy = [], busy

    def query(self, server, sql, kind="agg", engine="mysql"):
        SR.guard(sql, kind, engine)
        import re as _re
        self.calls.append(sql[:80])
        if "PROCESSLIST" in sql:
            return [{"COMMAND": "Query", "n": 1, "max_time_s": 0}], 0.01
        if "Threads_running" in sql:
            return [{"Variable_name": "Threads_running", "Value": "40" if self.busy else "2"}], 0.01
        if "information_schema.TABLES" in sql:
            return [{"shard_tables": 64, "first_table": "t_access_log_0000", "last_table": "t_access_log_0063"}], 0.01
        if sql.startswith("EXPLAIN"):
            return [{"id": 1, "table": "t_access_log_0000", "type": "range", "key": "idx_create_time_sharding_key", "rows": 99}], 0.01
        ws = _re.search(r"'([0-9-]+ [0-9:]+)' AS window_start_utc", sql).group(1)
        we = _re.search(r"'([0-9-]+ [0-9:]+)' AS window_end_utc", sql)
        rg = _re.search(r"'([0-9]{4}\.\.[0-9]{4})' AS shard_range", sql).group(1)
        lo, hi = rg.split("..")
        if "AS cc" in sql:
            return [dict(window_start_utc=ws, shard_range=rg, cc=c, shards_seen=16, sms_pass=p, sms_requests=q)
                    for c, p, q in (("92", 100, 300), ("852", 10, 11), ("62", 5, 6), ("7", 50, 60))], 0.01
        last = (datetime.strptime(we.group(1), P.FMT) - timedelta(seconds=2)).strftime(P.FMT)
        return [dict(PARTS[0], window_start_utc=ws, window_end_utc=we.group(1), shard_range=rg, shards_seen=16,
                     shard_sum=sum(range(int(lo), int(hi) + 1)), first_utc=ws, last_utc=last)], 0.01

    def close(self):
        pass


class RunnerGateway(SR.Gateway):
    """The runner's own query() (guard + prod_window_ok) in front of FakeGateway's answers; only call() is replaced."""
    def __init__(self):                       # no address, no network (connect() is never called for a passed-in gateway)
        self._secret_bits, self.fake, self.sent = set(), FakeGateway(), []

    def call(self, tool, args):
        self.sent.append(args["sql"][:80])
        return {"rows": self.fake.query(args["server"], args["sql"])[0]}


@contextlib.contextmanager
def runner_clock(ny):
    """The real prod_window_ok, evaluated at a fixed NY time (deterministic whatever the wall clock)."""
    real = SR.prod_window_ok
    SR.prod_window_ok = lambda now=None: real(now or ny_at(ny))
    try:
        yield
    finally:
        SR.prod_window_ok = real


def log_rows():
    p = os.path.join(PKG, "config", "outside_window_log.csv")
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


class Child(unittest.TestCase):
    def setUp(self):
        for d in ("runs", "history", "results", "posts"):
            shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
        write_shards()
        self.rd, _ = quiet(P.cmd_emit, ns(date="2026-10-10", per_code=True), NOW)

    def test_order_and_collect(self):
        gw = FakeGateway()
        quiet(P.cmd_send, argparse.Namespace(run_dir=self.rd), lambda: NOW, gw)
        self.assertTrue(gw.calls[0].startswith("SELECT /*+ MAX_EXECUTION_TIME(5000) */ COMMAND"))
        self.assertTrue(gw.calls[3].startswith("EXPLAIN"))
        self.assertEqual(len(gw.calls), 12)
        rows, out = quiet(P.cmd_collect, ns(run_dir=self.rd, path="A"))
        self.assertIn("可以发", out)

    def test_busy_and_late(self):
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_send, argparse.Namespace(run_dir=self.rd), lambda: NOW, FakeGateway(busy=True))
        self.assertEqual(c.exception.code, 7)
        ticks = iter([NOW] * 6 + [ny_at("2026-10-11 05:31")] * 20)
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_send, argparse.Namespace(run_dir=self.rd), lambda: next(ticks), FakeGateway())
        self.assertEqual(c.exception.code, 2)


    def test_stale_lock_is_exit_3(self):
        lock = os.path.join(SR.PKG, "_local_only", ".db_lock")
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        open(lock, "w").write("999999")
        try:
            err = io.StringIO()
            with self.assertRaises(SystemExit) as c, contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                P.cmd_send(argparse.Namespace(run_dir=self.rd), lambda: NOW, FakeGateway())
            self.assertEqual(c.exception.code, 3)
            self.assertIn("db_lock", err.getvalue())
            self.assertIn("进程已不在", err.getvalue())
        finally:
            os.remove(lock)

    def test_connect_failure_is_exit_5(self):
        class Down:
            def connect(self):
                raise RuntimeError("gateway connect failed: URLError")
        old_gw, old_cls = os.environ.get("MCP_DB_GATEWAY_SSE"), SR.Gateway
        os.environ["MCP_DB_GATEWAY_SSE"] = "x"
        SR.Gateway = Down
        try:
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_send, argparse.Namespace(run_dir=self.rd), lambda: NOW)
            self.assertEqual(c.exception.code, 5)
            self.assertFalse(os.path.exists(os.path.join(SR.PKG, "_local_only", ".db_lock")))
        finally:
            SR.Gateway = old_cls
            if old_gw is None:
                os.environ.pop("MCP_DB_GATEWAY_SSE", None)
            else:
                os.environ["MCP_DB_GATEWAY_SSE"] = old_gw


class OutsideWindow(unittest.TestCase):
    """The user's one-day exception (2026-10-10): 21:00-window kinds only, patrol24 only, logged."""
    def setUp(self):
        for d in ("runs", "history", "results", "posts"):
            shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
        log = os.path.join(PKG, "config", "outside_window_log.csv")
        if os.path.exists(log):
            os.remove(log)
        write_shards()

    def test_allowed_today_and_logged(self):
        day = ny_at("2026-10-10 10:54")
        rd, out = quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), day)
        man = json.load(open(os.path.join(rd, "manifest.json")))
        self.assertTrue(man["outside_window_ok"])
        self.assertIn("outside_window_log.csv", out)
        self.assertEqual(len(list(csv.DictReader(open(os.path.join(PKG, "config", "outside_window_log.csv"))))), 1)
        self.assertEqual(P.gate(rd, day)[0], "STOP")              # not LATE: only the missing s0 replies stop it
        gw = FakeGateway()
        orig = SR.prod_window_ok
        quiet(P.cmd_send, argparse.Namespace(run_dir=rd), lambda: day, gw)
        self.assertEqual(len(gw.calls), 8)
        self.assertIs(SR.prod_window_ok, orig)                     # the runner's own check is back after the send
        rows = log_rows()
        self.assertEqual([r["command"] for r in rows], ["emit", "_send"])
        self.assertTrue(rows[1]["note"].startswith("8 statements sent, NY 10:54:00-10:54:00"))

    def test_refused_other_days_kinds_and_without_flag(self):
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), ny_at("2026-10-11 10:54"))
        self.assertEqual(c.exception.code, 2)
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_emit, ns(backfill=2, outside_window_ok=True), ny_at("2026-10-10 10:54"))
        self.assertEqual(c.exception.code, 2)
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-09"), ny_at("2026-10-10 10:54"))      # no flag: emit is offline, gate says LATE
        self.assertEqual(P.gate(rd, ny_at("2026-10-10 10:54"))[0], "LATE")
        rd2, _ = quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), ny_at("2026-10-10 23:59"))
        self.assertEqual(P.gate(rd2, ny_at("2026-10-11 10:00"))[0], "LATE")             # the flag dies with the date
        self.assertEqual(log_rows(), [])                            # inside 22:00-05:30 nothing is logged as an exception
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_run, ns(date="2026-10-09", outside_window_ok=True, no_cli=True), ny_at("2026-10-11 10:54"))
        self.assertEqual(c.exception.code, 2)
        self.assertFalse(P.outside_window_allowed(ny_at("2026-10-10 10:54"), "slot", tool="eohq24"))

    def test_run_passes_the_clock_today(self):
        home = tempfile.mkdtemp(prefix="home_", dir=TMP)
        old, old_gw = os.environ.get("HOME"), os.environ.pop("MCP_DB_GATEWAY_SSE", None)
        os.environ["HOME"] = home
        try:
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_run, ns(date="2026-10-09", outside_window_ok=True, no_cli=True), ny_at("2026-10-10 10:54"))
            self.assertEqual(c.exception.code, 8)                   # past the clock, stopped only by the missing gateway
        finally:
            os.environ["HOME"] = old
            if old_gw is not None:
                os.environ["MCP_DB_GATEWAY_SSE"] = old_gw

    def test_runner_override_only_when_called(self):
        orig = SR.prod_window_ok
        try:
            self.assertFalse(SR.prod_window_ok(ny_at("2026-10-10 10:54")))
            P.allow_runner_outside()
            self.assertTrue(SR.prod_window_ok(ny_at("2026-10-10 10:54")))
        finally:
            SR.prod_window_ok = orig

    def test_replay_without_saved_window(self):
        before = sorted(os.listdir(PKG))
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_replay_test, argparse.Namespace(date="2026-10-09", at="21:00"))
        self.assertEqual(c.exception.code, 4)
        self.assertEqual(sorted(os.listdir(PKG)), before)


    def test_one_window_ending_2100_only(self):
        day = ny_at("2026-10-10 12:30")
        for kw in (dict(validate_slot="2026-10-08:2026-10-09"), dict(validate_slot="2026-01-01:2026-10-09"),
                   dict(date="2026-10-10", at="09:00"), dict(date="2026-10-09", at="09:00")):
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_emit, ns(outside_window_ok=True, **kw), day)
            self.assertEqual(c.exception.code, 2, kw)
        self.assertFalse(os.path.exists(os.path.join(PKG, "runs")) and os.listdir(os.path.join(PKG, "runs")))
        rd, _ = quiet(P.cmd_emit, ns(validate_slot="2026-10-09:2026-10-09", outside_window_ok=True), day)
        self.assertEqual(P.gate(rd, day)[0], "STOP")                # allowed: only the missing s0 replies stop it
        mp = os.path.join(rd, "manifest.json")
        man = json.load(open(mp))
        for forged in (dict(man, at="09:00"), dict(man, windows=man["windows"] * 2)):
            json.dump(forged, open(mp, "w"))
            self.assertEqual(P.gate(rd, day)[0], "LATE")            # a hand-edited manifest does not pass at send time
            self.assertFalse(P.man_outside_ok(forged, day))

    def test_only_a_window_that_has_ended(self):
        day = ny_at("2026-10-10 12:30")
        for kw in (dict(validate_slot="2026-10-10:2026-10-10"), dict(date="2026-10-10", force=True)):
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_emit, ns(outside_window_ok=True, **kw), day)
            self.assertEqual(c.exception.code, 2, kw)
        self.assertFalse(os.path.exists(os.path.join(PKG, "runs")) and os.listdir(os.path.join(PKG, "runs")))
        rd, _ = quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), day)
        mp = os.path.join(rd, "manifest.json")
        man = json.load(open(mp))
        man["windows"][0].update(start="2026-10-10 01:00:00", end="2026-10-11 01:00:00")      # forged: tonight's window
        json.dump(man, open(mp, "w"))
        self.assertEqual(P.gate(rd, day)[0], "LATE")

    def test_failed_statement_is_still_logged(self):
        class Failing(RunnerGateway):
            def call(self, tool, args):
                self.sent.append(args["sql"][:80])
                raise RuntimeError("mysql_query: reply timeout")
        day = ny_at("2026-10-10 15:00")
        with runner_clock("2026-10-10 15:00"):
            rd, _ = quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), day)
            gw = Failing()
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_send, argparse.Namespace(run_dir=rd), lambda: day, gw)
            self.assertEqual(c.exception.code, 5)
        rows = log_rows()
        self.assertEqual(rows[-1]["command"], "_send")
        self.assertTrue(rows[-1]["note"].startswith("1 statements sent"))

    def test_flag_refused_for_other_kinds(self):
        day = ny_at("2026-10-10 12:30")
        for kw in (dict(validate_ny="2026-10-09:2026-10-09"), dict(validate_utc="2026-10-09:2026-10-09"), dict(backfill=1)):
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_emit, ns(outside_window_ok=True, **kw), day)
            self.assertEqual(c.exception.code, 2, kw)
        os.remove(os.path.join(PKG, "config", "shards.json"))       # first run: discover
        with self.assertRaises(SystemExit) as c:
            quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), day)
        self.assertEqual(c.exception.code, 2)
        self.assertFalse(os.path.exists(os.path.join(PKG, "runs")) and os.listdir(os.path.join(PKG, "runs")))
        self.assertEqual(log_rows(), [])

    def test_runner_check_runs_and_override_is_one_send(self):
        day = ny_at("2026-10-10 15:00")
        with runner_clock("2026-10-10 15:00"):
            self.assertFalse(SR.prod_window_ok())
            rd, _ = quiet(P.cmd_emit, ns(date="2026-10-09", outside_window_ok=True), day)
            gw = RunnerGateway()
            quiet(P.cmd_send, argparse.Namespace(run_dir=rd), lambda: day, gw)
            self.assertEqual(len(gw.sent), 8)                       # the real query() ran, the override let them through
            self.assertFalse(SR.prod_window_ok())                   # and is gone after the send
        with runner_clock("2026-10-11 15:00"):
            gw = RunnerGateway()
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_send, argparse.Namespace(run_dir=rd), lambda: ny_at("2026-10-11 15:00"), gw)
            self.assertEqual(c.exception.code, 2)
            self.assertEqual(gw.sent, [])
        rd3, _ = quiet(P.cmd_emit, ns(date="2026-10-09"), NOW)      # no flag
        with runner_clock("2026-10-10 15:00"):
            gw = RunnerGateway()
            with self.assertRaises(SystemExit) as c:                # patrol24 thinks it is 22:05; the runner's own clock says 15:00
                quiet(P.cmd_send, argparse.Namespace(run_dir=rd3), lambda: NOW, gw)
            self.assertEqual(c.exception.code, 2)
            self.assertEqual(gw.sent, [])

    def test_eohq_manifest_with_forged_flag_sends_nothing(self):
        import eohq24 as E
        rd, _ = quiet(E.cmd_emit, argparse.Namespace(kind="recount", dim="", sid="strategy_eoHQ6Qs0FRqp",
                                                     utc="2026-10-10 01:00:00~2026-10-10 04:00:00", chunk_h=None,
                                                     hits_only=False, codes=None, m1_active_ok=False), NOW)
        mp = os.path.join(rd, "manifest.json")
        man = json.load(open(mp))
        man.update(outside_window_ok=True, at="21:00", windows=(man.get("windows") or [{}])[:1])
        json.dump(man, open(mp, "w"))
        day = ny_at("2026-10-10 15:00")
        with runner_clock("2026-10-10 15:00"):
            gw = RunnerGateway()
            with self.assertRaises(SystemExit) as c:
                quiet(P.cmd_send, argparse.Namespace(run_dir=rd), lambda: day, gw)
            self.assertEqual(c.exception.code, 2)
            self.assertEqual(gw.sent, [])

    def test_nightly_with_flag_before_2102_names_the_run_form(self):
        old = os.environ.get("MCP_DB_GATEWAY_SSE")
        os.environ["MCP_DB_GATEWAY_SSE"] = fake_url()

        def never(*a, **k):
            raise AssertionError("no child may start")
        err = io.StringIO()
        try:
            with self.assertRaises(SystemExit) as c, contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                P.cmd_nightly(argparse.Namespace(m1_active_ok=False, no_cli=True, outside_window_ok=True),
                              ny_at("2026-10-10 12:30"), runner=never)
        finally:
            if old is None:
                os.environ.pop("MCP_DB_GATEWAY_SSE", None)
            else:
                os.environ["MCP_DB_GATEWAY_SSE"] = old
        self.assertEqual(c.exception.code, 2)
        self.assertIn("还没到时间", err.getvalue())
        self.assertIn("run --validate-slot 2026-10-09:2026-10-09 --outside-window-ok", err.getvalue())
        self.assertNotIn("要补前一晚的数，加 --date", err.getvalue())
        self.assertFalse(os.path.exists(os.path.join(PKG, "runs")) and os.listdir(os.path.join(PKG, "runs")))


class EoHQWindow(unittest.TestCase):
    def test_gate_late_and_json_valid(self):
        import eohq24 as E
        write_shards()
        rd, _ = quiet(E.cmd_emit, argparse.Namespace(kind="recount", dim="", sid="strategy_eoHQ6Qs0FRqp",
                                                     utc="2026-10-10 01:00:00~2026-10-10 04:00:00", chunk_h=None,
                                                     hits_only=False, codes=None, m1_active_ok=False), NOW)
        sql = open(os.path.join(rd, "w01_g1.sql")).read()
        self.assertIn("JSON_VALID(l.request_strategy_engine)", sql)
        self.assertIn("IN ('', 'null')", sql)
        with self.assertRaises(SystemExit) as c:
            quiet(E.cmd_gate, argparse.Namespace(run_dir=rd), ny_at("2026-10-10 21:30"))
        self.assertEqual(c.exception.code, 2)
        self.assertEqual(json.load(open(os.path.join(rd, "manifest.json")))["tool"], "eohq24")



if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
