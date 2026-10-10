#!/usr/bin/env python3
"""Offline tests for autopost.py (no database, no network). Every test works on a copy inside a temp folder laid out as
<tmp>/run/RC_patrol/{toolkit,autopost}/; the toolkit files come from ../toolkit next to this file.
  PYTHONDONTWRITEBYTECODE=1 python3 -B RC_patrol/autopost/test_autopost.py
"""
import argparse, contextlib, csv, io, json, os, shutil, socket, subprocess, sys, tempfile, time, unittest
from datetime import date, datetime, timedelta, timezone

SRC = os.path.dirname(os.path.abspath(__file__))
TK_SRC = os.path.join(os.path.dirname(SRC), "toolkit")
UTC = timezone.utc
TK_NEEDED = ["patrol24.py", "shard_runner.py", "ny_day_bounds.py", "privacy_scan.py", "codes_21.txt"]


def make_copy():
    tmp = tempfile.mkdtemp(prefix="aptest_")
    pkg = os.path.join(tmp, "run", "RC_patrol")
    os.makedirs(os.path.join(pkg, "toolkit"))
    os.makedirs(os.path.join(pkg, "autopost"))
    for f in TK_NEEDED:
        shutil.copy2(os.path.join(TK_SRC, f), os.path.join(pkg, "toolkit"))
    shutil.copy2(os.path.join(SRC, "autopost.py"), os.path.join(pkg, "autopost"))
    return tmp, pkg


TMP, PKG = make_copy()
sys.path.insert(0, os.path.join(PKG, "autopost"))
import autopost as A  # noqa: E402  (the copy)


def _no_network(*a, **k):
    raise AssertionError("tests must not open network connections")


socket.create_connection = _no_network
HIST = ["slot_ny", "window_start_utc", "window_end_utc", "label", "sms_total", "sms_pass", "pass_not_us_cn", "pass_21",
        "sms_reject", "sms_review", "pass_1", "pass_86", "pass_empty", "pass_invalid", "email_rows", "sms_no_plus",
        "lag_s", "kind", "path", "run_id", "collected_ny"]
D = date(2026, 10, 11)


def ny(txt):
    return datetime.fromisoformat(txt).replace(tzinfo=A.NY).astimezone(UTC)


def fake_url(n=0):
    return "https://" + A.HOST + "/open-apis/bot/v2/hook/" + "-".join([f"{n:08x}", "a" * 4, "4" * 4, "b" * 4, "c" * 12])


FAKE_KEY = "k-" + "x" * 6 + "-not-real"


def codes():
    return A.codes21()


def post_text(d, nums):
    s, e = A.slot_window(d)
    return "\n".join([A.header(d), f"最近24小时内（纽约时间 {A.label(s, e)}）：", f"{A.LINE3}{nums[0]}", f"{A.LINE4}{nums[1]}",
                      f"{A.LINE5}{nums[2]}", "4. 区号在（" + ",".join("+" + c for c in codes()) + f"）范围内的短信pass量 {nums[3]}"]) + "\n"


RUN_SEQ = [0]


class FakePatrol:
    """Stands in for `patrol24.py run --date D --per-code`: writes what collect writes and prints like it."""
    def __init__(self, d=D, rcs=(0,), nums=(2152, 1235, 214, 152), lag=40, mutate=None, hist_nums=None, err=""):
        self.d, self.rcs, self.nums, self.lag, self.mutate, self.hist_nums, self.err = d, list(rcs), nums, lag, mutate, hist_nums, err
        self.calls = []

    def __call__(self, argv, cwd, env, timeout):
        self.calls.append((argv, env))
        rc = self.rcs[min(len(self.calls) - 1, len(self.rcs) - 1)]
        if rc != 0:
            return rc, "", self.err or "refused", False
        d = self.d
        RUN_SEQ[0] += 1
        run_id = f"{d:%Y%m%d}-22{RUN_SEQ[0]:04d}"
        rd = os.path.join(A.PKG, "runs", run_id + "_slot")
        os.makedirs(rd)
        s, e = A.slot_window(d)
        json.dump({"tool": "patrol24", "run_id": run_id, "kind": "slot", "at": "21:00", "codes": codes(),
                   "windows": [{"id": "w01", "kind": "slot", "key": f"{d} 21:00", "label": A.label(s, e),
                                "start": s.strftime(A.FMT), "end": e.strftime(A.FMT)}]}, open(os.path.join(rd, "manifest.json"), "w"))
        text = post_text(d, self.nums)
        if self.mutate:
            text = self.mutate(text)
        os.makedirs(A.p("posts"), exist_ok=True)
        open(A.post_path(d), "w", encoding="utf-8").write(text)
        open(A.p("posts", f"巡检_{d:%Y%m%d}_2100_附加.txt"), "w", encoding="utf-8").write("附（自己看，不发群）：REJECT 900、REVIEW 17\n")
        hp = A.p("history", "patrol24_history.csv")
        rows = [r for r in A.read_hist() if r["window_end_utc"] != e.strftime(A.FMT)]
        hn = self.hist_nums or self.nums
        rows.append(dict(zip(HIST, [f"{d} 21:00", s.strftime(A.FMT), e.strftime(A.FMT), A.label(s, e), *hn, 900, 17, 1011, 10, 0, 0, 3,
                                    0, self.lag, "slot", "A", run_id, "2026-10-11 22:06"])))
        with open(hp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=HIST, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        out = (f"gateway：本地作用域（地址不显示）\n16 statement files in runs/{run_id}_slot/ (each checked by the guard).\n"
               f"- unresolved: 0\n\n----- 复制下面这段发群 -----\n{text}----- 到这里 -----\n\n附（自己看，不发群）：REJECT 900\n可以发。\n")
        return 0, out, "", False


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.bodies = list(responses) or [(200, '{"code":0,"msg":"success","data":{}}')], []

    def __call__(self, url, body):
        self.bodies.append((url, json.loads(body.decode("utf-8"))))
        r = self.responses[min(len(self.bodies) - 1, len(self.responses) - 1)]
        if isinstance(r, Exception):
            raise r
        return r[0], r[1], ""

    def texts(self):
        return [b["content"]["text"] for _, b in self.bodies]


def reset(mode="test", start="2026-10-11", conf=None, **cfg_extra):
    for sub in ("runs", "posts", "history", "config", "_local_only"):
        shutil.rmtree(A.p(sub), ignore_errors=True)
    A.ensure_dirs()
    cfg = {"schema": 1, "enabled": True, "mode": mode, "start_date": start, "skip_dates": [], "host_pin": A.host_pin(),
           "python": sys.executable, "child_path": "/usr/bin:/bin", "home": TMP, "lang": "C.UTF-8", "no_cli": True, "changes": []}
    cfg.update(cfg_extra)
    A.save_cfg(cfg)
    A.save_conf(conf if conf is not None else {"test": {"url": fake_url(1)}, "team": {"url": fake_url(2)}})


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def fire(times, runner, tr, d=D):
    return [quiet(A.cron_once, ny(f"{d} {t}") if " " not in t else ny(t), runner, tr) for t in times]


class Signing(unittest.TestCase):
    def test_vector_and_payload(self):
        self.assertEqual(A.sign("1599360473", "demo-" + "not-real"), "VY2z/sW8J1egbMe611uPHMymUKm/kIvkEXvE2vouHLw=")
        tr = FakeTransport()
        quiet(A.deliver, {"url": fake_url(1)}, "测试", ny("2026-10-11 22:05"), tr)
        body = tr.bodies[0][1]
        self.assertEqual(body, {"msg_type": "text", "content": {"text": "测试"}})
        quiet(A.deliver, {"url": fake_url(1), "sig_key": FAKE_KEY}, "测试", ny("2026-10-11 22:05"), tr)
        body = tr.bodies[1][1]
        self.assertEqual(body["timestamp"], str(int(ny("2026-10-11 22:05").timestamp())))
        self.assertEqual(body["sign"], A.sign(body["timestamp"], FAKE_KEY))

    def test_responses(self):
        self.assertEqual(A.classify_response(200, '{"code":0,"msg":"success","data":{}}'), ("ok", 0))
        self.assertEqual(A.classify_response(200, '{"StatusCode":0}'), ("ok", 0))
        self.assertEqual(A.classify_response(200, '{"code":19024,"msg":"Key Words Not Found"}'), ("rejected", 19024))
        self.assertEqual(A.classify_response(200, '{"code":11232}'), ("retry", 11232))
        self.assertEqual(A.classify_response(502, '{"code":1}')[0], "uncertain")
        self.assertEqual(A.classify_response(200, "<html>")[0], "uncertain")
        self.assertEqual(A.classify_response(503, "<html>")[0], "uncertain")
        self.assertEqual(A.classify_response(404, "<html>")[0], "rejected")

    def test_url_shape(self):
        self.assertTrue(A.URL_RE.match(fake_url(1)))
        for bad in (fake_url(1).replace("https", "http"), fake_url(1) + "?x=1", fake_url(1) + "/", " " + fake_url(1),
                    fake_url(1).replace(A.HOST, "open.larksuite.com"), fake_url(1).upper(), ""):
            self.assertFalse(A.URL_RE.match(bad), bad)


class Windows(unittest.TestCase):
    def test_same_as_patrol24(self):
        sys.path.insert(0, os.path.join(PKG, "toolkit"))
        import patrol24 as P
        for d in ("2026-10-10", "2026-10-11", "2026-11-01", "2026-11-02", "2027-03-14", "2027-03-15", "2026-12-31"):
            dd = date.fromisoformat(d)
            self.assertEqual(A.slot_window(dd), P.slot_window(dd), d)
            self.assertEqual(A.label(*A.slot_window(dd)), P.label(*P.slot_window(dd)), d)
            m = {"sms_total": 9, "sms_pass": 8, "pass_not_us_cn": 7, "pass_21": 6}
            s, e = P.slot_window(dd)
            self.assertEqual(post_text(dd, (9, 8, 7, 6)), P.post_text(m, {"label": P.label(s, e)}, P.codes21()), d)

    def test_window_date(self):
        self.assertIsNone(A.window_date(ny("2026-10-11 12:00")))
        self.assertIsNone(A.window_date(ny("2026-10-11 21:29")))
        self.assertEqual(A.window_date(ny("2026-10-11 21:30")), D)
        self.assertEqual(A.window_date(ny("2026-10-12 00:35")), D)
        self.assertEqual(A.window_date(ny("2026-10-12 05:29")), D)
        self.assertIsNone(A.window_date(ny("2026-10-12 05:30")))


class Flow(unittest.TestCase):
    def setUp(self):
        reset()

    def test_success_posts_once(self):
        run, tr = FakePatrol(), FakeTransport()
        r = fire(["22:05", "22:35", "23:05", "23:35", "23:45"], run, tr)
        self.assertEqual(r[0], "posted")
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(tr.texts(), [open(A.post_path(D), encoding="utf-8").read()[:-1]])
        self.assertEqual(tr.bodies[0][0], fake_url(1))                 # test mode → test group
        self.assertEqual(A.load_state(D)["status"], "posted")

    def test_nothing_before_2203_or_in_daytime(self):
        run, tr = FakePatrol(), FakeTransport()
        self.assertEqual(fire(["21:35", "21:59", "22:02"], run, tr), ["early"] * 3)
        self.assertEqual(quiet(A.cron_once, ny("2026-10-12 12:05"), run, tr), "idle")
        self.assertEqual(run.calls, [])

    def test_exit3_four_times_then_failline(self):
        run, tr = FakePatrol(rcs=(3,)), FakeTransport()
        fire(["22:05", "22:20", "22:35", "23:05"], run, tr)
        self.assertEqual(len(run.calls), 3)                            # 22:20 is too soon after 22:05
        self.assertEqual(tr.bodies, [])
        fire(["23:35", "23:45", "2026-10-12 00:05"], run, tr)
        self.assertEqual(len(run.calls), 4)
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])
        self.assertEqual(A.load_state(D)["status"], "failline_posted")

    def test_exit3_then_ok(self):
        run, tr = FakePatrol(rcs=(3, 0)), FakeTransport()
        fire(["22:05", "22:35", "23:35"], run, tr)
        self.assertEqual(len(tr.bodies), 1)
        self.assertTrue(tr.texts()[0].startswith(A.header(D)))
        self.assertNotIn(A.FAILLINE, tr.texts()[0])

    def test_busy_limit(self):
        run, tr = FakePatrol(rcs=(7,)), FakeTransport()
        fire(["22:05", "22:35"], run, tr)
        self.assertEqual(tr.bodies, [])
        fire(["23:05"], run, tr)                                        # third 7: no more retries
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])
        self.assertEqual(len(run.calls), 3)

    def test_gateway_connect_retries_other_5_does_not(self):
        run, tr = FakePatrol(rcs=(5, 0), err="query failed: gateway connect failed: URLError: x"), FakeTransport()
        fire(["22:05", "22:35"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "posted")
        reset()
        run, tr = FakePatrol(rcs=(5,), err="query failed: mysql_query: timeout"), FakeTransport()
        fire(["22:05", "22:35"], run, tr)
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])

    def test_terminal_codes(self):
        for rc in (4, 6, 8, 1, -9):
            reset()
            run, tr = FakePatrol(rcs=(rc,)), FakeTransport()
            fire(["22:05", "22:35"], run, tr)
            self.assertEqual(len(run.calls), 1, rc)
            self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE], rc)

    def test_exit2_not_counted(self):
        run, tr = FakePatrol(rcs=(2, 2, 2, 2, 2)), FakeTransport()
        fire(["22:05", "22:35", "23:05"], run, tr)
        self.assertEqual(A.counted(A.load_state(D)), 0)
        fire(["23:35"], run, tr)
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])

    def test_timeout_is_terminal(self):
        tr = FakeTransport()
        fire(["22:05"], lambda *a: (None, "", "", True), tr)
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])

    def test_child_argv_and_env(self):
        run, tr = FakePatrol(), FakeTransport()
        os.environ["MCP_DB_GATEWAY_SSE"] = "x"
        try:
            fire(["22:05"], run, tr)
        finally:
            os.environ.pop("MCP_DB_GATEWAY_SSE", None)
        argv, env = run.calls[0]
        self.assertEqual(argv[3:], ["run", "--date", "2026-10-11", "--per-code", "--no-cli"])
        self.assertFalse(any(x in argv for x in A.FORBIDDEN_ARGS))
        self.assertEqual(set(env), {"HOME", "PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "PYTHONUTF8", "PYTHONIOENCODING",
                                    "PYTHONUNBUFFERED"})


class Checks(unittest.TestCase):
    def setUp(self):
        reset()

    def failline_only(self, run):
        tr = FakeTransport()
        fire(["22:05"], run, tr)
        self.assertEqual(tr.texts(), [A.header(D) + "\n" + A.FAILLINE])

    def test_wrong_header(self):
        self.failline_only(FakePatrol(mutate=lambda t: t.replace("10/11 21:00）", "10/10 21:00）", 1)))

    def test_numbers_differ_from_history(self):
        self.failline_only(FakePatrol(hist_nums=(2152, 1235, 214, 151)))

    def test_private_line_or_at(self):
        self.failline_only(FakePatrol(mutate=lambda t: t + "附（自己看，不发群）：REJECT 900\n"))
        reset()
        self.failline_only(FakePatrol(mutate=lambda t: t.replace("1. 短信", "@所有人 1. 短信")))

    def test_bad_order(self):
        self.failline_only(FakePatrol(nums=(10, 20, 5, 1)))

    def test_quiet_evening_lag_does_not_block(self):
        run, tr = FakePatrol(lag=720), FakeTransport()              # nobody asked for a code in the last 12 minutes before 21:00
        fire(["22:05"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "posted")
        st = A.load_state(D)
        end = datetime.strptime(st["window_end_utc"], A.FMT).replace(tzinfo=UTC).timestamp()
        self.assertEqual(A.check_post_file(st, D, None, end + 600)[1], "lag")        # right after the cut-off it still counts
        self.assertTrue(A.check_post_file(st, D, None, end + 3600)[0])

    def test_manual_run_is_skipped(self):
        os.makedirs(A.p("posts"), exist_ok=True)
        open(A.post_path(D), "w", encoding="utf-8").write(post_text(D, (1, 1, 1, 1)))
        run, tr = FakePatrol(), FakeTransport()
        self.assertEqual(fire(["22:05"], run, tr), ["manual_skip"])
        self.assertEqual((run.calls, tr.bodies), ([], []))

    def test_manual_run_between_attempts(self):
        run, tr = FakePatrol(rcs=(3,)), FakeTransport()
        fire(["22:05"], run, tr)
        manual = FakePatrol(rcs=(0,))
        manual(["x"], None, None, None)                                # the user's own nightly writes run dir, post, history
        fire(["22:35", "23:35"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "manual_skip")
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(tr.bodies, [])


class Interrupted(unittest.TestCase):
    def setUp(self):
        reset()

    def crash_after(self, full):
        def runner(argv, cwd, env, timeout):
            out_base = A.load_state(D)["attempts"][-1]["out_base"]
            if full:
                out = FakePatrol()(argv, cwd, env, timeout)[1]
            else:
                rd = os.path.join(A.PKG, "runs", "20261011-220500_slot")
                os.makedirs(rd)
                s, e = A.slot_window(D)
                json.dump({"tool": "patrol24", "kind": "slot", "windows": [{"key": f"{D} 21:00", "start": s.strftime(A.FMT),
                                                                            "end": e.strftime(A.FMT)}]}, open(os.path.join(rd, "manifest.json"), "w"))
                out = "8 statement files in runs/20261011-220500_slot/ (each checked by the guard).\n"
            open(out_base + ".out", "w").write(out)                 # what the real runner's output file would hold
            raise KeyboardInterrupt("the cron process was killed")
        return runner

    def test_hand_run_after_a_killed_firing_is_not_adopted(self):
        with self.assertRaises(KeyboardInterrupt):
            quiet(A.cron_once, ny("2026-10-11 22:05"), self.crash_after(False), FakeTransport())
        time.sleep(1.1)
        FakePatrol()(["x"], None, None, None)                          # the user runs and posts this window by hand
        run, tr = FakePatrol(), FakeTransport()
        self.assertEqual(fire(["22:35"], run, tr), ["manual_skip"])
        self.assertEqual((run.calls, tr.bodies), ([], []))

    def test_killed_during_child_is_retried_not_manual(self):
        for full in (False, True):
            reset()
            with self.assertRaises(KeyboardInterrupt):
                quiet(A.cron_once, ny("2026-10-11 22:05"), self.crash_after(full), FakeTransport())
            self.assertEqual(A.load_state(D)["status"], "running")
            run, tr = FakePatrol(), FakeTransport()
            self.assertEqual(fire(["22:35"], run, tr), ["posted"], full)
            st = A.load_state(D)
            self.assertEqual([a["cls"] for a in st["attempts"]], ["interrupted", "ok"])
            self.assertEqual(len(tr.bodies), 1)

    def sleeper(self, *extra):
        return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *extra])

    def running_state(self, pid):
        st = A.load_state(D)
        st.update(status="running", target="test", attempts=[{"n": 1, "fired": ny("2026-10-11 22:05").timestamp(), "t0": time.time(),
                                                              "runs_before": [], "child_pid": pid}])
        A.save_state(st)

    def test_hand_run_right_after_a_kill_before_emit_is_not_adopted(self):
        def runner(argv, cwd, env, timeout):
            out_base = A.load_state(D)["attempts"][-1]["out_base"]
            open(out_base + ".out", "w").write("gateway：本地作用域（地址不显示）\n")      # killed before emit
            raise KeyboardInterrupt("killed")
        with self.assertRaises(KeyboardInterrupt):
            quiet(A.cron_once, ny("2026-10-11 22:05"), runner, FakeTransport())
        rd = os.path.join(A.PKG, "runs", "20261011-220630_slot")       # the user's own run 90 s later
        os.makedirs(rd)
        s_, e_ = A.slot_window(D)
        json.dump({"tool": "patrol24", "kind": "slot", "windows": [{"key": f"{D} 21:00", "start": s_.strftime(A.FMT),
                                                                    "end": e_.strftime(A.FMT)}]}, open(os.path.join(rd, "manifest.json"), "w"))
        run, tr = FakePatrol(), FakeTransport()
        self.assertEqual(fire(["22:35"], run, tr), ["manual_skip"])
        self.assertEqual((run.calls, tr.bodies), ([], []))

    def test_child_still_running(self):
        pr = self.sleeper("patrol24")                               # a live child whose command line names patrol24
        try:
            self.running_state(pr.pid)
            run, tr = FakePatrol(), FakeTransport()
            self.assertEqual(fire(["22:35"], run, tr), ["child_running"])
            self.assertEqual((run.calls, tr.bodies), ([], []))
        finally:
            pr.kill()
            pr.wait()

    def test_linux_cmdline_check(self):
        """With a /proc-style folder (emulated here, real on the Linux server): a live pid counts only if it is patrol24."""
        pr = self.sleeper()
        fake = tempfile.mkdtemp(prefix="proc_", dir=TMP)
        os.makedirs(os.path.join(fake, str(pr.pid)))
        old = A.PROC_DIR
        A.PROC_DIR = fake
        try:
            open(os.path.join(fake, str(pr.pid), "cmdline"), "wb").write(b"python3\0-B\0RC_patrol/toolkit/patrol24.py\0run\0")
            self.running_state(pr.pid)
            self.assertEqual(fire(["22:35"], FakePatrol(), FakeTransport()), ["child_running"])
            open(os.path.join(fake, str(pr.pid), "cmdline"), "wb").write(b"python3\0-c\0import time\0")   # the pid was reused
            self.assertEqual(fire(["22:40"], FakePatrol(), FakeTransport()), ["posted"])
        finally:
            A.PROC_DIR = old
            pr.kill()
            pr.wait()


class Sending(unittest.TestCase):
    def setUp(self):
        reset()

    def test_send_retry_resends_without_query(self):
        run, tr = FakePatrol(), FakeTransport(A.SendError("before"), (200, '{"code":0}'))
        fire(["22:05"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "send_retry")
        fire(["22:35"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "posted")
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(tr.texts()[0], tr.texts()[1])

    def test_uncertain_is_never_resent(self):
        run, tr = FakePatrol(), FakeTransport(A.SendError("after"))
        fire(["22:05", "22:35", "23:35", "23:45"], run, tr)
        self.assertEqual(len(tr.bodies), 1)
        self.assertEqual(A.load_state(D)["status"], "send_uncertain")

    def test_crash_mid_send(self):
        st = A.load_state(D)
        st.update(status="posting", target="test")
        A.save_state(st)
        tr = FakeTransport()
        fire(["22:35"], FakePatrol(), tr)
        self.assertEqual(A.load_state(D)["status"], "send_uncertain")
        self.assertEqual(tr.bodies, [])

    def test_5xx_is_uncertain_and_no_failline_follows(self):
        run, tr = FakePatrol(rcs=(3, 3, 3, 0)), FakeTransport((502, "<html>bad gateway</html>"))
        fire(["22:05", "22:35", "23:05", "23:35", "23:45"], run, tr)
        self.assertEqual(len(tr.bodies), 1)
        self.assertEqual(A.load_state(D)["status"], "send_uncertain")

    def test_manual_run_while_send_retry(self):
        run, tr = FakePatrol(), FakeTransport(A.SendError("before"))
        fire(["22:05"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "send_retry")
        time.sleep(1.1)
        FakePatrol()(["x"], None, None, None)                          # the user's own run between two firings
        fire(["22:35", "23:35"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "manual_skip")
        self.assertEqual(len(tr.bodies), 1)                             # no failure line

    def test_cap_counts_only_delivered(self):
        run = FakePatrol()
        tr = FakeTransport(A.SendError("before"), A.SendError("before"), A.SendError("before"), (200, '{"code":0}'))
        fire(["22:05", "22:35", "23:05", "23:35"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "posted")
        self.assertEqual(len(run.calls), 1)

    def test_interrupted_send_after_0040_is_uncertain_not_gave_up(self):
        st = A.load_state(D)
        st.update(status="posting", target="test")
        A.save_state(st)
        self.assertEqual(quiet(A.cron_once, ny("2026-10-12 00:45"), FakePatrol(), FakeTransport()), "send_uncertain")

    def test_failline_not_sent_after_a_hand_run(self):
        run, tr = FakePatrol(rcs=(4,)), FakeTransport(A.SendError("before"))
        fire(["22:05"], run, tr)                                       # terminal; the failure line could not be sent
        self.assertEqual(A.load_state(D)["status"], "failline_retry")
        time.sleep(1.1)
        FakePatrol()(["x"], None, None, None)
        tr2 = FakeTransport()
        self.assertEqual(fire(["22:35"], run, tr2), ["manual_skip"])
        self.assertEqual(tr2.bodies, [])
        reset()
        fire(["22:05"], FakePatrol(rcs=(3,)), FakeTransport())
        time.sleep(1.1)
        FakePatrol()(["x"], None, None, None)
        tr3 = FakeTransport()
        self.assertEqual(fire(["23:45"], FakePatrol(), tr3), ["manual_skip"])      # the late branch checks too
        self.assertEqual(tr3.bodies, [])

    def test_stalled_source_is_retried(self):
        run, tr = FakePatrol(lag=4000), FakeTransport()
        fire(["22:05"], run, tr)
        self.assertEqual(A.load_state(D)["status"], "retry_wait")
        self.assertEqual(tr.bodies, [])

    def test_rejected(self):
        run, tr = FakePatrol(), FakeTransport((200, '{"code":19024,"msg":"Key Words Not Found"}'))
        fire(["22:05", "22:35", "23:35"], run, tr)
        self.assertEqual(len(tr.bodies), 1)
        self.assertEqual(A.load_state(D)["status"], "send_rejected")

    def test_post_file_changed_before_resend(self):
        run, tr = FakePatrol(), FakeTransport(A.SendError("before"), (200, '{"code":0}'))
        fire(["22:05"], run, tr)
        open(A.post_path(D), "a").write("x")
        fire(["22:35"], run, tr)
        self.assertEqual(tr.texts()[-1], A.header(D) + "\n" + A.FAILLINE)

    def test_late_failline_and_gave_up(self):
        tr = FakeTransport()
        self.assertEqual(quiet(A.cron_once, ny("2026-10-11 23:45"), FakePatrol(), tr), "failline_posted")
        reset()
        tr = FakeTransport(A.SendError("before"))
        quiet(A.cron_once, ny("2026-10-11 23:45"), FakePatrol(), tr)
        self.assertEqual(A.load_state(D)["status"], "failline_retry")
        self.assertEqual(quiet(A.cron_once, ny("2026-10-12 00:45"), FakePatrol(), tr), "gave_up")

    def test_target_captured_per_window(self):
        run, tr = FakePatrol(rcs=(3, 0)), FakeTransport()
        fire(["22:05"], run, tr)
        cfg = A.load_cfg()
        cfg["mode"] = "team"
        A.save_cfg(cfg)
        fire(["22:35"], run, tr)
        self.assertEqual(tr.bodies[0][0], fake_url(1))                  # still the test group for this window

    def test_team_mode_and_daily_cap(self):
        reset(mode="team")
        run, tr = FakePatrol(), FakeTransport()
        fire(["22:05"], run, tr)
        self.assertEqual(tr.bodies[0][0], fake_url(2))
        self.assertEqual(A.sent_today("team", ny("2026-10-11 23:00")), 1)


class Gating(unittest.TestCase):
    def test_start_skip_disabled_host(self):
        run, tr = FakePatrol(d=date(2026, 10, 10)), FakeTransport()
        reset()
        self.assertEqual(quiet(A.cron_once, ny("2026-10-10 22:05"), run, tr), "gated")         # before start
        reset(skip_dates=["2026-10-11"])
        self.assertEqual(quiet(A.cron_once, ny("2026-10-11 22:05"), run, tr), "gated")
        reset(enabled=False)
        self.assertEqual(quiet(A.cron_once, ny("2026-10-11 22:05"), run, tr), "gated")
        reset(host_pin="not-this-host")
        self.assertEqual(quiet(A.cron_once, ny("2026-10-11 22:05"), run, tr), "other_host")
        self.assertEqual((run.calls, tr.bodies), ([], []))

    def test_no_config(self):
        reset()
        os.remove(A.CONF)
        self.assertEqual(quiet(A.cron_once, ny("2026-10-11 22:05"), FakePatrol(), FakeTransport()), "not_initialized")


class Secrets(unittest.TestCase):
    def test_conf_permissions(self):
        reset()
        os.chmod(A.SECRETS, 0o644)
        with self.assertRaises(SystemExit):
            quiet(A.load_conf)
        os.chmod(A.SECRETS, 0o600)

    def test_set_webhook_needs_a_terminal(self):
        reset()
        old = sys.stdin
        sys.stdin = io.StringIO(fake_url(5) + "\n")                    # not a terminal, even when the tests run in one
        try:
            with self.assertRaises(SystemExit) as c:
                quiet(A.cmd_set_webhook, argparse.Namespace(**{"target": "test", "secret": False}))
        finally:
            sys.stdin = old
        self.assertEqual(c.exception.code, 2)
        self.assertNotIn(fake_url(5), open(A.SECRETS).read())

    def test_webhook_never_leaves_the_conf(self):
        reset(conf={"test": {"url": fake_url(7), "sig_key": FAKE_KEY}})
        tok_ = fake_url(7).rsplit("/", 1)[1]

        class Leaky:
            def __call__(self, url, body):
                raise RuntimeError(f"boom {url} {FAKE_KEY}")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            A.cron_once(ny("2026-10-11 22:05"), FakePatrol(), Leaky())
            A.cron_once(ny("2026-10-11 22:35"), FakePatrol(rcs=(3,)), Leaky())
            A.cmd_status(argparse.Namespace(), ny("2026-10-11 22:40"))
            A.cmd_dry_run(argparse.Namespace(at="2026-10-11 22:50"))
            A.cmd_cron(argparse.Namespace(), ny("2026-10-11 23:45"), FakePatrol(), Leaky())
        blobs = [out.getvalue(), err.getvalue()]
        for root, _, files in os.walk(PKG):
            for f in files:
                fp_ = os.path.join(root, f)
                if os.path.abspath(fp_) != os.path.abspath(A.SECRETS):
                    blobs.append(open(fp_, "rb").read().decode("utf-8", "replace"))
        for b in blobs:
            for s in (fake_url(7), tok_, FAKE_KEY):
                self.assertNotIn(s, b)
        self.assertIn("指纹", out.getvalue())
        self.assertEqual(quiet(A.cmd_leakcheck, argparse.Namespace(), lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "")), 0)
        open(A.p("history", "planted.txt"), "w").write(tok_)
        self.assertEqual(quiet(A.cmd_leakcheck, argparse.Namespace(), lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "")), 4)

    def test_mode_switch_rules(self):
        reset()
        with self.assertRaises(SystemExit):
            quiet(A.cmd_set_mode, argparse.Namespace(mode="team", force=False), ny("2026-10-12 12:00"))   # 0 good test nights
        with self.assertRaises(SystemExit):
            quiet(A.cmd_set_mode, argparse.Namespace(mode="test", force=False), ny("2026-10-11 22:00"))   # not mid-window
        quiet(A.cmd_set_mode, argparse.Namespace(mode="team", force=True), ny("2026-10-12 12:00"))
        self.assertEqual(A.load_cfg()["mode"], "team")
        reset(conf={"test": {"url": fake_url(1)}})
        with self.assertRaises(SystemExit):
            quiet(A.cmd_set_mode, argparse.Namespace(mode="team", force=True), ny("2026-10-12 12:00"))   # no team webhook


class Commands(unittest.TestCase):
    def test_cron_line_and_install(self):
        reset()
        line = A.cron_line(A.load_cfg())
        self.assertTrue(line.startswith("5,35 * * * * cd ") and line.endswith(A.TAG) and "%" not in line)
        self.assertNotIn("hook", line)
        tab = {"text": "MAILTO=\"\"\n0 3 * * * /usr/bin/true\n" + "5,35 * * * * old " + A.TAG + "\n"}

        def run(argv, input=None, capture_output=True, text=True):
            if argv[1] == "-l":
                return subprocess.CompletedProcess(argv, 0, tab["text"], "")
            tab["text"] = input
            return subprocess.CompletedProcess(argv, 0, "", "")
        quiet(A.cmd_install_cron, argparse.Namespace(cmd="install-cron"), run, ny("2026-10-11 12:00"))
        lines = tab["text"].splitlines()
        self.assertEqual(lines[:2], ["MAILTO=\"\"", "0 3 * * * /usr/bin/true"])
        self.assertEqual(lines[2:], [line])
        self.assertTrue(any(f.startswith("crontab_backup_") for f in os.listdir(A.LOCAL)))
        quiet(A.cmd_install_cron, argparse.Namespace(cmd="uninstall-cron"), run, ny("2026-10-11 12:05"))
        self.assertEqual(tab["text"].splitlines(), ["MAILTO=\"\"", "0 3 * * * /usr/bin/true"])

    def test_test_send_only_to_test(self):
        reset()
        with self.assertRaises(SystemExit):
            quiet(A.cmd_test_send, argparse.Namespace(target="team"), ny("2026-10-11 12:00"), FakeTransport())
        tr = FakeTransport()
        self.assertEqual(quiet(A.cmd_test_send, argparse.Namespace(target="test"), ny("2026-10-11 12:00"), tr), 0)
        self.assertEqual(tr.texts(), [A.TESTLINE])

    def test_send_post_guards(self):
        reset()
        fire(["22:05"], FakePatrol(rcs=(3,)), FakeTransport())
        with self.assertRaises(SystemExit):                             # this window is still being handled
            quiet(A.cmd_send_post, argparse.Namespace(date="2026-10-11", resend_uncertain=False, accept_lag=False), ny("2026-10-11 22:20"), FakeTransport())
        lk = open(os.path.join(A.LOCAL, ".autopost.lock"), "w")
        A.fcntl.flock(lk, A.fcntl.LOCK_EX | A.fcntl.LOCK_NB)
        try:
            with self.assertRaises(SystemExit):                         # a cron firing holds the lock
                quiet(A.cmd_send_post, argparse.Namespace(date="2026-10-10", resend_uncertain=False, accept_lag=False), ny("2026-10-12 12:00"), FakeTransport())
        finally:
            A.fcntl.flock(lk, A.fcntl.LOCK_UN)
            lk.close()
        st = A.load_state(D)
        st.update(status="failline_posted", sends=[{"kind": "failline", "result": None}])
        A.save_state(st)
        with self.assertRaises(SystemExit):                             # last send has no result: uncertain
            quiet(A.cmd_send_post, argparse.Namespace(date="2026-10-11", resend_uncertain=False, accept_lag=False), ny("2026-10-12 12:00"), FakeTransport())

    def test_proxy_is_for_feishu_only(self):
        reset()
        open(A.PROXY_FILE, "w").write("https_proxy=proxy.invalid\n")
        self.assertEqual(A.feishu_proxy(), "proxy.invalid")
        self.assertNotIn("https_proxy", A.child_env(A.load_cfg()))
        os.remove(A.PROXY_FILE)

    def test_rehearse_inner_only_in_its_temp_copy(self):
        reset()
        before = open(A.SECRETS).read()
        with self.assertRaises(SystemExit):
            quiet(A.main, ["_rehearse_inner", "2026-10-09", "x", "w01", "4"])
        self.assertEqual(open(A.SECRETS).read(), before)

    def manual_send(self, d, now, tr, answer_hook=None, **kw):
        old_tty, old_input = A.tty_or_refuse, A.__builtins__["input"] if isinstance(A.__builtins__, dict) else None
        A.tty_or_refuse = lambda: None
        import builtins
        real_input = builtins.input

        def fake_input(prompt=""):
            if answer_hook:
                answer_hook()
            return "发送"
        builtins.input = fake_input
        try:
            return quiet(A.cmd_send_post, argparse.Namespace(date=d, resend_uncertain=False, accept_lag=False, **kw), now, tr)
        finally:
            builtins.input = real_input
            A.tty_or_refuse = old_tty

    def test_send_post_does_not_block_cron_and_manual_retry_is_final(self):
        reset()
        fire(["22:05", "22:35", "23:05", "23:35"], FakePatrol(rcs=(3,)), FakeTransport())
        self.assertEqual(A.load_state(D)["status"], "failline_posted")
        FakePatrol()(["x"], None, None, None)                          # the user's 补发 run
        seen = []
        tr = FakeTransport(A.SendError("before"))
        rc = self.manual_send("2026-10-11", ny("2026-10-12 01:00"), tr,
                              answer_hook=lambda: seen.append(quiet(A.cmd_cron, argparse.Namespace(), ny("2026-10-12 01:00"),
                                                                    FakePatrol(), FakeTransport())))
        self.assertNotEqual(seen, ["overlap"])                         # the prompt holds no lock
        self.assertEqual(rc, 5)
        self.assertEqual(A.load_state(D)["status"], "manual_send_retry")
        tr2 = FakeTransport()
        self.assertEqual(self.manual_send("2026-10-11", ny("2026-10-12 01:05"), tr2), 0)
        self.assertEqual(A.load_state(D)["status"], "reposted")

    def test_send_post_recovers_a_stuck_running_state(self):
        reset(skip_dates=["2026-10-11"])
        FakePatrol()(["x"], None, None, None)
        st = A.load_state(D)
        st.update(status="running", target="test", attempts=[{"n": 1, "fired": 0, "t0": 0, "runs_before": [], "child_pid": None}])
        A.save_state(st)
        tr = FakeTransport()
        self.assertEqual(self.manual_send("2026-10-11", ny("2026-10-12 09:00"), tr), 0)
        self.assertEqual(len(tr.bodies), 1)

    def test_send_post_refused_when_posted(self):
        reset()
        fire(["22:05"], FakePatrol(), FakeTransport())
        with self.assertRaises(SystemExit):
            quiet(A.cmd_send_post, argparse.Namespace(date="2026-10-11", resend_uncertain=False, accept_lag=False), ny("2026-10-12 09:00"), FakeTransport())

    def test_privacy_of_written_files(self):
        reset(conf={"test": {"url": fake_url(3)}})
        fire(["22:05"], FakePatrol(rcs=(3,)), FakeTransport())
        fire(["22:35"], FakePatrol(), FakeTransport())
        files = [A.LOG, A.CONF] + [os.path.join(A.STATE_DIR, f) for f in os.listdir(A.STATE_DIR)]
        r = subprocess.run([sys.executable, "-B", os.path.join(PKG, "toolkit", "privacy_scan.py")] + files, capture_output=True, text=True)
        self.assertIn("- unresolved: 0", r.stdout, r.stdout[-800:])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
