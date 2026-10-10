#!/usr/bin/env python3
"""Offline tests for patrol24.py (no database). Every test works on a copy of this toolkit inside a temp folder laid out
as <tmp>/run/RC_patrol/toolkit/, so nothing is written next to the real toolkit.
  PYTHONDONTWRITEBYTECODE=1 python3 toolkit/test_patrol24.py
"""
import argparse, contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from datetime import date, datetime, timedelta, timezone

SRC = os.path.dirname(os.path.abspath(__file__))
UTC = timezone.utc
NEEDED = ["patrol24.py", "eohq24.py", "shard_runner.py", "ny_day_bounds.py", "privacy_scan.py", "codes_21.txt", "tk11_patrol24_branch.sql",
          "tk11_patrol24_outer.sql", "tk11_patrol24_percode.sql", "fixture_ny_0920_0926.csv", "fixture_doris_utc_0913_1008.csv"]


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


def ns(**kw):
    d = dict(date=None, at="21:00", codes=None, per_code=False, m1_active_ok=False, force=True, validate_ny=None,
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
        branch = open(os.path.join(TK, "tk11_patrol24_branch.sql")).read()
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
        self.assertEqual(P.gate(rd)[0], "GO")
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
        self.assertEqual(P.gate(rd)[0], "STOP")
        json.dump({"error": "x"}, open(os.path.join(rd, "s0a_processlist.json"), "w"))
        with self.assertRaises(SystemExit):
            P.gate(rd)

    def test_gate_wait(self):
        rd, man = self.emit()
        save_replies(rd, man, busy=True)
        self.assertEqual(P.gate(rd)[0], "WAIT")

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
        d = dict(kind="dim", dim="cc", sid="strategy_eoHQ6QsOFRqp", utc="2026-10-09 04:00:00~2026-10-10 04:00:00", chunk_h=None,
                 hits_only=False, codes=None, m1_active_ok=False)
        d.update(kw)
        return argparse.Namespace(**d)

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
        quiet(self.E.cmd_gate, argparse.Namespace(run_dir=rd))
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

    def test_path_a_needs_env(self):
        env = dict(os.environ); env.pop("MCP_DB_GATEWAY_SSE", None)
        r = subprocess.run([sys.executable, os.path.join(TK, "patrol24.py"), "run", "--date", "2026-10-10"], env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("path B", r.stderr)

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


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
