#!/usr/bin/env python3
"""patrol24.py — 北美短信例行巡检：最近 24 小时的 4 个数（每晚纽约时间 21:00 那一段；09:00 同样可用）。

Window: [T-24h, T), T = the slot (default 21:00 America/New_York) converted to UTC. Always 86,400 s, also on the
DST days (2026-11-01, 2027-03-14), so the label then starts at 22:00 / 20:00 the day before.
Production pull window: database statements only between NY 22:00 and 05:30 (the team rule M1 recorded on 2026-10-08;
the user decided 2026-10-10 to query after 22:00 and post about 22:05; the window still ends at 21:00).
Frozen definitions (README_patrol24.md):
  1 短信请求总量            LKUS_push rows that are SMS: $.para.email empty, missing, JSON null or unreadable (the definition
                            of the 4th package's L1, which matched Doris l2_scene='1001' by UTC day, package DR-036(a))
  2 短信请求pass量          those with result = 'PASS' (the final result returned to the caller)
  3 非美国区号且非中国区号  PASS with a 1-4 digit code other than 1 and 86; empty and invalid codes are excluded
  4 区号在 21 个范围内      PASS with the code in codes_21.txt
Every statement is read-only, passes shard_runner.guard(), covers <= 16 shards and one 24-hour window, and returns
one row (per-code statements: one row per code). The same statement files serve both paths:
  path A (default since 2026-10-10, user-approved): `nightly` / `run` finds the mcp-db-gateway address in this machine's
          Claude MCP configuration (resolve_gateway), passes it only into a child process's environment (never printed,
          never written, never in argv), the child sends the files and `collect` checks and prints. `gateway-check`
          says where it was found (a fixed label), never the address.
  path B (fallback): `emit` writes the files; Claude sends them one at a time with the mcp-db-gateway query tool and
          saves each reply verbatim as <file>.json next to the .sql; `gate` says GO / WAIT; `collect` checks and prints.
Commands (run from anywhere; RC_patrol = the folder above toolkit/):
  nightly [--m1-active-ok] [--no-cli]                  path A, tonight's 21:00 window with the per-code check (one command)
  run     [same options as emit] [--no-cli]            path A for any window kind
  emit    [--date D] [--at HH:MM] [--per-code] [--validate-slot A:B|A,B | --validate-ny A:B|A,B,C | --validate-utc A:B |
           --backfill N] [--m1-active-ok]              path B: write statement files (offline; checks nothing on the server)
  gate    RUN_DIR | collect RUN_DIR [--path A|B]       path B: load / window / EXPLAIN check; collect, check, print
  gateway-check [--no-cli] | init | verify | shards RUN_DIR | seed-history | reserved REPLY.json
  doris-sql [--date D] [--at 09:00]                    (text for David; never executed here)
Testing outside the window (user decision 2026-10-10): `replay-test` runs the whole pipeline offline on saved replies, at
any time, without a database; `--outside-window-ok` on emit / run / nightly lets exactly one 21:00 window (kind slot, or a
one-day validate_slot) leave outside 22:00-05:30, but only on the New York date OUTSIDE_WINDOW_DAY. Each use outside the
window is logged in config/outside_window_log.csv (the command that wrote the files, then the child's send with its
statement count and NY times). eohq24.py has no such flag.
Exit codes: 0 ok · 2 too early, outside the production window, or usage · 3 another database run looks active ·
4 a check failed · 5 query failed · 6 privacy scan not clean · 7 server busy (wait and retry) · 8 no usable gateway (use B).
"""
import argparse, csv, glob, hashlib, json, os, re, shutil, subprocess, sys, time
from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                       # RC_patrol
RUN_FOLDER = os.path.dirname(PKG)                 # the run folder that also holds RC_data_* packages
sys.path.insert(0, HERE)
import shard_runner  # noqa: E402  (guard, Gateway, Lock; the 4th package's copy, with prod_window_ok and the empty-range EXPLAIN gate)

NY, UTC = ZoneInfo("America/New_York"), timezone.utc
FMT = "%Y-%m-%d %H:%M:%S"
SCENE = "LKUS_push"
BATCH = 16
RISK_SCHEMA = "luckyus_iriskcontrolservice"
METRICS = ["rows_all", "email_rows", "sms_total", "sms_pass", "sms_reject", "sms_review", "sms_other", "pass_1", "pass_86",
           "pass_empty", "pass_invalid", "pass_not_us_cn", "pass_21", "pass_not_21", "sms_cc_empty", "sms_cc_invalid",
           "sms_no_plus", "dup_rows"]
PROD_START, PROD_END = (22, 0), (5, 30)          # NY; same bounds as shard_runner.PROD_WINDOW in the 4th package
OUTSIDE_WINDOW_DAY = "2026-10-10"                 # user decision 2026-10-10: a live test outside the window, this NY date only
OUTSIDE_KINDS = ("slot", "validate_slot")         # only the short 21:00-window statements
GATEWAY = "mcp-db-gateway"
HIST_COLS = ["slot_ny", "window_start_utc", "window_end_utc", "label", "sms_total", "sms_pass", "pass_not_us_cn", "pass_21",
             "sms_reject", "sms_review", "pass_1", "pass_86", "pass_empty", "pass_invalid", "email_rows", "sms_no_plus",
             "lag_s", "kind", "path", "run_id", "collected_ny"]


class Fail(SystemExit):
    def __init__(self, code, msg):
        print(msg, file=sys.stderr)
        super().__init__(code)


# ----------------------------------------------------------------------------- production window
def window_open(now_utc, margin_min=0):
    """True inside NY 22:00 … (05:30 - margin)."""
    t = now_utc.astimezone(NY)
    hm = t.hour * 60 + t.minute
    return hm >= PROD_START[0] * 60 + PROD_START[1] or hm < PROD_END[0] * 60 + PROD_END[1] - margin_min


def window_msg(now_utc, kind=None):
    """The refusal text. Hints only for patrol24's own window kinds (kind given); eohq24 and P6 get the rule alone."""
    msg = _window_msg(now_utc)
    if kind is None:
        return msg
    msg += " 白天想试：`patrol24.py replay-test`（不连库，任何时间）"
    t = now_utc.astimezone(NY)
    if outside_window_allowed(now_utc, kind) and t.hour < 21:
        y = (t.date() - timedelta(days=1)).isoformat()
        msg += f"；今天（{OUTSIDE_WINDOW_DAY}）还可以真查一次：`patrol24.py run --validate-slot {y}:{y} --outside-window-ok`"
    return msg + "。"


def _window_msg(now_utc):
    t = now_utc.astimezone(NY)
    if t.hour < 12:
        return (f"现在纽约时间 {t:%H:%M}，已接近或过了生产库取数时段的结束（纽约 22:00–05:30）：今晚 22:00 以后再跑；"
                "要补昨晚那一段，在时段里跑 `patrol24.py run --date <那一晚的纽约日期> --per-code`。")
    return (f"现在纽约时间 {t:%H:%M}，不在生产库取数时段（纽约 22:00–05:30）：22:00 以后再跑；"
            "统计窗口不变，仍是到 21:00 为止的 24 小时。")


def outside_window_allowed(now_utc, kind, tool="patrol24"):
    """The user's one-day exception: patrol24 only, 21:00-window kinds only, on OUTSIDE_WINDOW_DAY (New York) only."""
    return tool == "patrol24" and kind in OUTSIDE_KINDS and now_utc.astimezone(NY).date().isoformat() == OUTSIDE_WINDOW_DAY


def man_outside_ok(man, now_utc):
    """Send-time repeat of emit's limits: flag set, exactly one window ending 21:00, allowed kind, tool and date."""
    if not (bool(man.get("outside_window_ok")) and man.get("at") == "21:00" and len(man.get("windows") or []) == 1
            and outside_window_allowed(now_utc, man.get("kind"), man.get("tool", "patrol24"))):
        return False
    try:                                   # only a window that has already ended (never a partial one in the daytime)
        end = datetime.strptime(man["windows"][0]["end"], FMT).replace(tzinfo=UTC)
    except (KeyError, TypeError, ValueError):
        return False
    return (now_utc - end).total_seconds() >= 120


def _hint_kind(man):
    return man.get("kind") if man and man.get("tool", "patrol24") == "patrol24" else None


def outside_msg(now_utc):
    return (f"--outside-window-ok 只在纽约日期 {OUTSIDE_WINDOW_DAY} 有效（用户 2026-10-10 决定：只今天，只限 21 点窗口的短语句）；"
            f"现在是 {now_utc.astimezone(NY):%Y-%m-%d %H:%M}。")


def log_outside(cmd, kind, rd, now_utc, note=None):
    p = os.path.join(PKG, "config", "outside_window_log.csv")
    new = not os.path.exists(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["ny_time", "command", "kind", "run_dir", "note"])
        w.writerow([now_utc.astimezone(NY).strftime("%Y-%m-%d %H:%M:%S"), cmd, kind, os.path.relpath(rd, PKG),
                    note or f"outside 22:00-05:30 by the user's decision for {OUTSIDE_WINDOW_DAY}"])


def require_window(now_utc, margin_min, kind=None):
    if not window_open(now_utc, margin_min):
        raise Fail(2, window_msg(now_utc, kind))


# ----------------------------------------------------------------------------- windows
def codes21(path=None):
    path = path or os.path.join(HERE, "codes_21.txt")
    out = [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    if not out or any(not re.fullmatch(r"[0-9]{1,4}", c) for c in out) or len(set(out)) != len(out):
        raise Fail(2, f"codes file {path}: expected unique 1-4 digit codes, one per line")
    return out


def slot_window(d, at="21:00"):
    """(start_utc, end_utc) of the 24 hours that end at local time `at` on NY date d."""
    hh, mm = (int(x) for x in at.split(":"))
    end = datetime.combine(d, dtime(hh, mm), tzinfo=NY).astimezone(UTC)
    return end - timedelta(hours=24), end


def latest_slot_date(now_utc, at="21:00", grace_s=120):
    """NY date of the latest slot whose end + grace is not after now (a run at 00:30 takes the previous evening)."""
    d = now_utc.astimezone(NY).date()
    for k in range(0, 3):
        s, e = slot_window(d - timedelta(days=k), at)
        if (now_utc - e).total_seconds() >= grace_s:
            return d - timedelta(days=k)
    raise Fail(2, "no slot in the last 3 days")


def label(s, e):
    sl, el = s.astimezone(NY), e.astimezone(NY)
    txt = f"{sl.month}/{sl.day} {sl:%H:%M} 至 {el.month}/{el.day} {el:%H:%M}"
    if sl.utcoffset() != el.utcoffset():
        txt += "，跨夏令时切换，按整24小时"
    return txt


def ny_day_window(d):
    s = datetime.combine(d, dtime(0), tzinfo=NY).astimezone(UTC)
    e = datetime.combine(d + timedelta(days=1), dtime(0), tzinfo=NY).astimezone(UTC)
    return s, e


def daterange(spec):
    """'A:B' (inclusive range) or 'A,B,C' (a list of dates)."""
    if "," in spec:
        return [date.fromisoformat(x.strip()) for x in spec.split(",") if x.strip()]
    a, b = (date.fromisoformat(x) for x in spec.split(":"))
    out = []
    while a <= b:
        out.append(a)
        a += timedelta(days=1)
    return out


def build_windows(a, now_utc):
    """List of dicts: id, kind, start, end (aware UTC), label, key (ny date / utc date / slot)."""
    wins = []
    if getattr(a, "validate_slot", None):
        for d in daterange(a.validate_slot):
            s, e = slot_window(d, a.at)
            wins.append(dict(kind="validate_slot", key=f"{d.isoformat()} {a.at}", start=s, end=e, label=label(s, e)))
    elif a.validate_ny:
        for d in daterange(a.validate_ny):
            s, e = ny_day_window(d)
            wins.append(dict(kind="validate_ny", key=d.isoformat(), start=s, end=e, label=f"纽约日 {d.isoformat()}"))
    elif a.validate_utc:
        for d in daterange(a.validate_utc):
            s = datetime.combine(d, dtime(0), tzinfo=UTC)
            wins.append(dict(kind="validate_utc", key=d.isoformat(), start=s, end=s + timedelta(days=1), label=f"UTC 日 {d.isoformat()}"))
    else:
        if a.date:
            d = date.fromisoformat(a.date)
        else:
            today = now_utc.astimezone(NY).date()
            _, et = slot_window(today, a.at)
            wait = (et + timedelta(minutes=2) - now_utc).total_seconds()
            if not a.force and not a.backfill and 0 < wait <= 12 * 3600:
                el = (et + timedelta(minutes=2)).astimezone(NY)
                y = (today - timedelta(days=1)).isoformat()
                if getattr(a, "cmd", None) == "nightly":
                    msg = (f"还没到时间：纽约时间 {el:%m-%d %H:%M} 以后再跑（今天 {a.at} 这一段还没结束）。nightly 只取今天这一段，"
                           f"不能加 --date。要补前一晚：在 22:00–05:15 里跑 `patrol24.py run --date {y} --per-code`")
                    if getattr(a, "outside_window_ok", False) and outside_window_allowed(now_utc, "slot"):
                        msg += (f"；今天白天要真查一次：`patrol24.py run --validate-slot {y}:{y} --outside-window-ok`"
                                f"（或 `run --date {y} --per-code --outside-window-ok`）")
                    raise Fail(2, msg)
                raise Fail(2, f"还没到时间：纽约时间 {el:%m-%d %H:%M} 以后再跑（今天 {a.at} 这一段还没结束）。"
                              f"要补前一晚的数，加 --date <那一晚的纽约日期>")
            d = latest_slot_date(now_utc, a.at)
        s, e = slot_window(d, a.at)
        if not a.force and not a.backfill and (now_utc - e).total_seconds() < 120:
            el = (e + timedelta(minutes=2)).astimezone(NY)
            raise Fail(2, f"还没到时间：纽约时间 {el:%m-%d %H:%M} 以后再跑（这一段的数要到 {a.at} 才完整）")
        if a.backfill:
            for k in range(a.backfill, 0, -1):
                dk = d - timedelta(days=k)
                sk, ek = slot_window(dk, a.at)
                wins.append(dict(kind="backfill", key=f"{dk.isoformat()} {a.at}", start=sk, end=ek, label=label(sk, ek)))
        else:
            wins.append(dict(kind="slot", key=f"{d.isoformat()} {a.at}", start=s, end=e, label=label(s, e)))
    for i, w in enumerate(wins, 1):
        w["id"] = f"w{i:02d}"
        span = (w["end"] - w["start"]).total_seconds()
        if span <= 0 or span > 86400:
            raise Fail(2, f"{w['label']}: window is {span:.0f} s; a statement may cover at most 86,400 s "
                          f"(NY day 2026-11-01 is 25 h: split it, or use the slot window)")
    return wins


# ----------------------------------------------------------------------------- statements
def tpl(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read().strip().rstrip(";")


def fill(text, values):
    return re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def shard_names():
    p = os.path.join(PKG, "config", "shards.json")
    if not os.path.exists(p):
        return None
    c = json.load(open(p, encoding="utf-8"))
    lo, hi = int(c["first"][-4:]), int(c["last"][-4:])
    if c["count"] != hi - lo + 1:
        raise Fail(4, "config/shards.json: shard tables are not contiguous; run the discovery statement again")
    return [f"{i:04d}" for i in range(lo, hi + 1)]


def statement(kind, shards, w, codes):
    branch = tpl("patrol24_branch.sql")
    s, e = w["start"].strftime(FMT), w["end"].strftime(FMT)
    brs = [fill(branch, dict(tbl=f"t_access_log_{sh}", shard=sh, utc_start=s, utc_end=e, scene=SCENE)) for sh in shards]
    outer = tpl("patrol24_outer.sql" if kind == "metrics" else "patrol24_percode.sql")
    return fill(outer, dict(utc_start=s, utc_end=e, shard_range=f"{shards[0]}..{shards[-1]}",
                            codes=", ".join(f"'{c}'" for c in codes), branches=" UNION ALL ".join(brs))) + "\n"


S0A = ("SELECT /*+ MAX_EXECUTION_TIME(5000) */ COMMAND, COUNT(*) AS n, MAX(TIME) AS max_time_s "
       "FROM information_schema.PROCESSLIST GROUP BY COMMAND\n")
S0B = "SHOW GLOBAL STATUS LIKE 'Threads_running'\n"
S0C = (f"SELECT /*+ MAX_EXECUTION_TIME(5000) */ COUNT(*) AS shard_tables, MIN(TABLE_NAME) AS first_table, "
       f"MAX(TABLE_NAME) AS last_table FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{RISK_SCHEMA}' "
       "AND TABLE_NAME REGEXP '^t_access_log_[0-9][0-9][0-9][0-9]$'\n")


def load_reserved():
    shard_runner.PKG = PKG
    shard_runner.load_routines()


def check(sql):
    try:
        shard_runner.guard(sql, "agg")
    except shard_runner.GuardError as ex:
        raise Fail(4, f"statement refused by the guard: {ex}")


# ----------------------------------------------------------------------------- concurrency
def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


RUNNER = re.compile(r"(?i)(^|[\s/])shard_runner\.py\s+(run|once|fleet)\b")
SHELLS = {"sh", "bash", "zsh", "dash", "fish", "-sh", "-bash", "-zsh"}


def is_runner(args):
    """A process executing shard_runner.py run/once/fleet (python, Python, python3.x, behind caffeinate ...), but not a
    shell whose command line merely mentions the file."""
    first = args.split(None, 1)[0] if args.strip() else ""
    if os.path.basename(first).lower() in SHELLS:
        return False
    return bool(RUNNER.search(args))


def m1_state(pkg_dir):
    """'finished' (P7 end logged, or the package zip + .sha256 exist next to the folder), 'paused', or 'open'."""
    stamp = os.path.basename(pkg_dir)[len("RC_data_"):]
    z = os.path.join(os.path.dirname(pkg_dir), f"RC_data_package_{stamp}.zip")
    if os.path.exists(z) and os.path.exists(z + ".sha256"):
        return "finished"
    rl = os.path.join(pkg_dir, "RUN_LOG.md")
    lines = [l for l in open(rl, encoding="utf-8", errors="replace").read().splitlines() if l.strip()] if os.path.exists(rl) else []
    last = lines[-1] if lines else ""
    if re.search(r"\|\s*P7\s*\|\s*end\s*\|", last, flags=re.I):
        return "finished"
    if re.search(r"paused|暂停", last, flags=re.I):
        return "paused"
    return "open"


LOCK_FRESH_S = 30 * 60


def other_db_runs(run_folder=None):
    """Signals that another database run (an M1 package run) may be querying now. Never deletes anything."""
    rf = run_folder or RUN_FOLDER
    sig, stale = [], []
    for lock in sorted(glob.glob(os.path.join(rf, "RC_data_*", "_local_only", ".db_lock"))):
        try:
            pid = int(open(lock).read().strip() or 0)
        except (OSError, ValueError):
            pid = 0
        try:
            age = time.time() - os.path.getmtime(lock)
        except OSError:
            age = 1e9
        rel = os.path.relpath(lock, rf)
        if pid and pid_alive(pid):
            sig.append(rel)
        elif age < LOCK_FRESH_S:     # the holder may run in another container (seen 2026-10-10): treat a fresh lock as live
            sig.append(f"{rel} (created {int(age // 60)} min ago; its process is not visible here, maybe another container)")
        else:
            stale.append(rel)
    try:
        ps = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        ps = ""
    for line in ps.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and is_runner(parts[1]) and int(parts[0]) != os.getpid() and PKG not in parts[1]:
            sig.append("a shard_runner.py process is running")
            break
    for rl in sorted(glob.glob(os.path.join(rf, "RC_data_*", "RUN_LOG.md"))):
        st = m1_state(os.path.dirname(rl))
        if st == "open" and time.time() - os.path.getmtime(rl) < 12 * 3600:
            sig.append(f"{os.path.relpath(rl, rf)} written within 12 h, run not finished (no P7 end, no package zip)")
        elif st == "open":
            stale.append(f"{os.path.relpath(rl, rf)} (unfinished, but untouched for 12 h or more)")
    return sig, stale


# ----------------------------------------------------------------------------- emit / gate / collect
def cmd_init(a=None):
    for d in ("config", "runs", "posts", "history", "results", "sql", "doris", "_local_only"):
        os.makedirs(os.path.join(PKG, d), exist_ok=True)
    print(f"folders ready under {os.path.basename(PKG)}/")


def kind_of(a):
    return ("validate_slot" if getattr(a, "validate_slot", None) else "validate_ny" if getattr(a, "validate_ny", None) else
            "validate_utc" if getattr(a, "validate_utc", None) else "backfill" if getattr(a, "backfill", None) else "slot")


def cmd_emit(a, now_utc=None):
    now_utc = now_utc or datetime.now(UTC)
    cmd_init()
    load_reserved()
    sig, stale = other_db_runs()
    for s in stale:
        print(f"note: stale lock {s} (its process is gone). Not touched; clear it yourself after checking `ps`.")
    if sig and not a.m1_active_ok:
        raise Fail(3, "另一个查库任务可能正在跑（" + "；".join(sig) + "）。按 2026-10-10 用户批准的例外，确认后加 "
                      "--m1-active-ok 再跑：只发几条短语句，而且先过负载检查（s0a/s0b）。")
    codes = codes21(a.codes)
    shards = shard_names()
    run_id = now_utc.astimezone(NY).strftime("%Y%m%d-%H%M%S")
    kind = "discover" if shards is None else kind_of(a)
    ow = bool(getattr(a, "outside_window_ok", False))
    if ow and not outside_window_allowed(now_utc, kind):
        raise Fail(2, outside_msg(now_utc) + f" 这次的种类是 {kind}，不在允许范围（只限 {', '.join(OUTSIDE_KINDS)}）。"
                   if now_utc.astimezone(NY).date().isoformat() == OUTSIDE_WINDOW_DAY else outside_msg(now_utc))
    wins = build_windows(a, now_utc) if shards is not None else []      # before the run dir: a refusal leaves nothing behind
    if ow and (len(wins) != 1 or a.at != "21:00"):
        y = (now_utc.astimezone(NY).date() - timedelta(days=1)).isoformat()
        raise Fail(2, f"--outside-window-ok 只限一个到 21:00 为止的窗口（用户 {OUTSIDE_WINDOW_DAY} 的例外）：这次是 {len(wins)} 个窗口、"
                      f"截止 {a.at}。白天真查一次用 `patrol24.py run --validate-slot {y}:{y} --outside-window-ok`。")
    if ow and (now_utc - wins[0]["end"]).total_seconds() < 120:
        y = (now_utc.astimezone(NY).date() - timedelta(days=1)).isoformat()
        raise Fail(2, f"--outside-window-ok 只查已经结束的 21 点窗口：{wins[0]['label']} 这一段还没结束。"
                      f"白天真查一次用 `patrol24.py run --validate-slot {y}:{y} --outside-window-ok`。")
    base, n = run_id, 1
    rd = os.path.join(PKG, "runs", f"{run_id}_{kind}")
    while os.path.exists(rd) or glob.glob(os.path.join(PKG, "runs", f"{run_id}_*")):
        n += 1
        run_id = f"{base}-{n}"            # the suffix goes into the id, so results files and history stay unique
        rd = os.path.join(PKG, "runs", f"{run_id}_{kind}")
    os.makedirs(rd)
    files = []

    def put(name, sql):
        check(sql)
        open(os.path.join(rd, name), "w", encoding="utf-8").write(sql)
        files.append(name)

    if shards is None:
        put("s0c_shards.sql", S0C)
        json.dump({"tool": "patrol24", "run_id": run_id, "kind": "discover", "files": files},
                  open(os.path.join(rd, "manifest.json"), "w"), indent=1)
        print(f"first run: send {os.path.relpath(rd, PKG)}/s0c_shards.sql, save the reply as s0c_shards.json, then\n"
              f"  python3 toolkit/patrol24.py shards {os.path.relpath(rd, PKG)}   and emit again")
        return rd
    groups = [shards[i:i + BATCH] for i in range(0, len(shards), BATCH)]
    put("s0a_processlist.sql", S0A)
    put("s0b_threads.sql", S0B)
    put("s0c_shards.sql", S0C)
    put("s0d_explain.sql", "EXPLAIN " + statement("metrics", groups[0][:1], wins[0], codes))
    for w in wins:
        for gi, g in enumerate(groups, 1):
            put(f"{w['id']}_s{gi}.sql", statement("metrics", g, w, codes))
        if a.per_code and kind in ("slot", "backfill"):
            for gi, g in enumerate(groups, 1):
                put(f"{w['id']}_c{gi}.sql", statement("percode", g, w, codes))
    man = {"tool": "patrol24", "run_id": run_id, "kind": kind, "at": a.at, "codes": codes, "shards": [shards[0], shards[-1], len(shards)],
           "groups": [[g[0], g[-1]] for g in groups], "files": files, "m1_active_ok": bool(a.m1_active_ok), "m1_signals": sig,
           "outside_window_ok": ow,
           "windows": [dict(id=w["id"], kind=w["kind"], key=w["key"], label=w["label"], start=w["start"].strftime(FMT),
                            end=w["end"].strftime(FMT)) for w in wins]}
    json.dump(man, open(os.path.join(rd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rel = os.path.relpath(rd, PKG)
    print(f"{len(files)} statement files in {rel}/ (each checked by the guard). Window(s): "
          + "; ".join(f"{w['id']} {w['label']} = UTC [{w['start']:%m-%d %H:%M}, {w['end']:%m-%d %H:%M})" for w in wins))
    print("Path B order: s0a, s0b, s0c, s0d → `patrol24.py gate " + rel + "` → if GO: every w*_s*.sql (then w*_c*.sql) one at "
          "a time → `patrol24.py collect " + rel + "`. Save each reply verbatim as <same name>.json.")
    if not window_open(now_utc, 15):
        if ow:
            log_outside(getattr(a, "cmd", None) or "emit", kind, rd, now_utc)
            print(f"note: 用户 {OUTSIDE_WINDOW_DAY} 的例外：这一个 21 点窗口的语句可以在 22:00–05:30 以外发出（已记进 config/outside_window_log.csv）。")
        else:
            print("note: " + window_msg(now_utc, kind) + "（文件已写好，发送前再看时间。）")
    return rd


def rows_of(path):
    """Rows from a saved reply: MCP JSON ({"rows": [...]}, a list, or {"data": ...}) or a CSV file."""
    if path.endswith(".csv"):
        return list(csv.DictReader(open(path, encoding="utf-8")))
    txt = open(path, encoding="utf-8").read().strip()
    obj = json.loads(txt)
    if isinstance(obj, dict) and obj.get("error"):
        raise Fail(4, f"{os.path.basename(path)}: the tool returned an error instead of rows (see the file); fix the cause, "
                      "send the statement again")
    while isinstance(obj, dict):
        for k in ("rows", "data", "result", "results"):
            if k in obj:
                obj = obj[k]
                break
        else:
            return [obj]
    if isinstance(obj, list) and obj and isinstance(obj[0], list):
        top = json.loads(txt)
        cols = top.get("columns") if isinstance(top, dict) else None
        if not cols:
            raise Fail(4, f"{os.path.basename(path)}: rows without column names; save the reply exactly as the tool returned it")
        cols = [c if isinstance(c, str) else c.get("name") for c in cols]
        return [dict(zip(cols, r)) for r in obj]
    return obj or []


def num(v):
    if v is None or v == "":
        return 0
    f = float(v)
    if f != int(f):
        raise Fail(4, f"non-integer count {v!r}")
    return int(f)


def reply(rd, name):
    for ext in (".json", ".csv"):
        p = os.path.join(rd, name + ext)
        if os.path.exists(p):
            return rows_of(p)
    return None


def cmd_shards(a):
    rows = reply(a.run_dir, "s0c_shards")
    if not rows:
        raise Fail(4, "s0c_shards.json missing")
    r = rows[0]
    c = {"count": num(r["shard_tables"]), "first": r["first_table"], "last": r["last_table"]}
    if c["count"] != int(c["last"][-4:]) - int(c["first"][-4:]) + 1:
        raise Fail(4, f"shard tables not contiguous: {c}")
    os.makedirs(os.path.join(PKG, "config"), exist_ok=True)
    json.dump(c, open(os.path.join(PKG, "config", "shards.json"), "w"), indent=1)
    print(f"config/shards.json: {c['count']} shards {c['first'][-4:]}..{c['last'][-4:]}")


def load_check(pl, tr):
    """(verdict, why) from the s0a PROCESSLIST summary and the s0b Threads_running row (shard_runner.processlist_ok rules)."""
    if not pl or any("COMMAND" not in r or "max_time_s" not in r for r in pl):
        return "STOP", "s0a reply is not the PROCESSLIST summary (COMMAND / max_time_s rows): send s0a again"
    if len(tr) != 1 or str(tr[0].get("Variable_name", "")).lower() != "threads_running" or tr[0].get("Value") in (None, ""):
        return "STOP", "s0b reply is not the Threads_running row: send s0b again"
    busy = [r for r in pl if str(r.get("COMMAND")) not in ("Sleep", "Daemon", "Binlog Dump", "Binlog Dump GTID")
            and num(r.get("max_time_s")) > 10]
    running = num(tr[0].get("Value"))
    if busy or running > 10:
        return "WAIT", f"server busy (Threads_running={running}, long statements={len(busy)}): wait 20 minutes and emit again"
    return "GO", f"load ok (Threads_running={running})"


def explain_ok(ex):
    """Same rule as the 4th package's shard_runner.explain_gate: indexed access, or an empty range (nothing to read);
    a full scan of a large table is refused."""
    ok_key = any(r.get("key") and r.get("type") in ("range", "ref", "const", "eq_ref") for r in ex)
    empty = any(re.search(r"No matching min/max row|Impossible WHERE|no matching row in const table", str(r.get("Extra") or ""), re.I)
                for r in ex)
    big = [r for r in ex if r.get("type") == "ALL" and not str(r.get("table", "")).startswith("<") and num(r.get("rows")) > 20000]
    return (ok_key or empty) and not big, f"indexed access={ok_key}, empty range={empty and not ok_key}, large full scans={len(big)}"


def explain_ok_upush(ex, keys, cap=500000):
    """Stricter gate for the upush log tables (2026-10-10 review): every real table row must be a range scan on one of the
    expected indexes, with an estimate under the cap; an empty range (nothing to read) is fine."""
    empty = any(re.search(r"No matching min/max row|Impossible WHERE|no matching row in const table", str(r.get("Extra") or ""), re.I)
                for r in ex)
    real = [r for r in ex if r.get("table") and not str(r.get("table")).startswith("<")]
    bad = [r for r in real if r.get("type") != "range" or r.get("key") not in (keys or []) or num(r.get("rows")) > cap]
    ok = (bool(real) and not bad) or (empty and not [r for r in real if r.get("type") == "ALL"])
    return ok, (f"range on {'/'.join(keys or [])}: {len(real) - len(bad)}/{len(real)} rows ok"
                + (f"; refused: type={bad[0].get('type')} key={bad[0].get('key')} rows={bad[0].get('rows')}" if bad else "")
                + ("; empty range" if empty else ""))


def gate(rd, now_utc=None):
    """GO / WAIT / LATE / STOP from the clock and the s0 replies (same rules as shard_runner.processlist_ok and explain_gate)."""
    now_utc = now_utc or datetime.now(UTC)
    try:
        man = json.load(open(os.path.join(rd, "manifest.json"), encoding="utf-8"))
    except (OSError, ValueError):
        man = {}
    if not window_open(now_utc, 15) and not man_outside_ok(man, now_utc):
        return "LATE", window_msg(now_utc, _hint_kind(man))
    pl, tr, sh, ex = (reply(rd, n) for n in ("s0a_processlist", "s0b_threads", "s0c_shards", "s0d_explain"))
    if None in (pl, tr, sh, ex):
        return "STOP", "save all four s0 replies first (s0a, s0b, s0c, s0d)"
    verdict, why = load_check(pl, tr)
    if verdict != "GO":
        return verdict, why
    c = json.load(open(os.path.join(PKG, "config", "shards.json")))
    got = {"count": num(sh[0]["shard_tables"]), "first": sh[0]["first_table"], "last": sh[0]["last_table"]}
    if got != c:
        return "STOP", f"shard tables changed ({got} vs config {c}): run `patrol24.py shards {rd}` and emit again"
    ok, txt = explain_ok(ex)
    if not ok:
        return "STOP", f"EXPLAIN gate failed: {txt}"
    return "GO", f"{why}; {c['count']} shards; EXPLAIN uses an index"


def cmd_gate(a):
    verdict, why = gate(a.run_dir)
    print(f"{verdict}: {why}")
    if verdict != "GO":
        raise SystemExit({"WAIT": 7, "LATE": 2}.get(verdict, 4))


def metrics_for(rd, man, w, allow_missing=False):
    tot = {k: 0 for k in METRICS}
    lag = None
    for gi, (lo, hi) in enumerate(man["groups"], 1):
        rows = reply(rd, f"{w['id']}_s{gi}")
        if rows is None:
            raise Fail(4, f"{w['id']}_s{gi}: reply missing")
        if len(rows) != 1:
            raise Fail(4, f"{w['id']}_s{gi}: expected one row, got {len(rows)}")
        r = rows[0]
        if r.get("window_start_utc") != w["start"] or r.get("window_end_utc") != w["end"] or r.get("shard_range") != f"{lo}..{hi}":
            raise Fail(4, f"{w['id']}_s{gi}: reply is for window {r.get('window_start_utc')} / shards {r.get('shard_range')}, "
                          f"expected {w['start']} / {lo}..{hi} — wrong file saved?")
        size, want_sum = int(hi) - int(lo) + 1, sum(range(int(lo), int(hi) + 1))
        seen, ssum = num(r.get("shards_seen")), num(r.get("shard_sum"))
        if seen == size and ssum != want_sum:
            raise Fail(4, f"{w['id']}_s{gi}: shard numbers in the reply add up to {ssum}, expected {want_sum} — a branch read the "
                          "wrong table (statement mistyped?); send the file again exactly as written")
        if seen < size:
            msg = (f"{w['id']}_s{gi}: only {seen} of {size} shards returned rows. At about 50 SMS rows per shard per day this "
                   "means a branch was dropped or mistyped; send the file again exactly as written")
            if not allow_missing:
                raise Fail(4, msg + " (only if a shard really had no rows: collect --allow-missing-shard)")
            print("note: " + msg)
        first = str(r.get("first_utc") or "")[:19].replace("T", " ")
        last = str(r.get("last_utc") or "")[:19].replace("T", " ")
        if num(r.get("rows_all")) and not (w["start"] <= first and last < w["end"]):
            raise Fail(4, f"{w['id']}_s{gi}: rows from {first} to {last} fall outside the window [{w['start']}, {w['end']}) — "
                          "a time bound was mistyped; send the file again exactly as written")
        for k in METRICS:
            tot[k] += num(r.get(k))
        if r.get("lag_s") not in (None, ""):
            lag = num(r["lag_s"]) if lag is None else min(lag, num(r["lag_s"]))
    tot["lag_s"] = lag
    return tot


def verify_metrics(m):
    """Identities that catch a mistyped reply; returns a list of failures."""
    bad = []
    if m["rows_all"] != m["email_rows"] + m["sms_total"]:
        bad.append("rows_all != email_rows + sms_total")
    if m["sms_total"] != m["sms_pass"] + m["sms_reject"] + m["sms_review"] + m["sms_other"]:
        bad.append("sms_total != pass + reject + review + other")
    if m["pass_not_us_cn"] != m["pass_21"] + m["pass_not_21"]:
        bad.append("③ != ④ + (codes outside the 21)")
    if m["dup_rows"] != 0:
        bad.append(f"{m['dup_rows']} rows were read twice (a branch repeated a table)")
    if m["sms_pass"] != m["pass_1"] + m["pass_86"] + m["pass_empty"] + m["pass_invalid"] + m["pass_not_us_cn"]:
        bad.append("pass != pass_1 + pass_86 + empty + invalid + not_us_cn")
    if not (0 <= m["pass_21"] <= m["pass_not_us_cn"] <= m["sms_pass"] <= m["sms_total"]) or m["sms_total"] <= 0:
        bad.append("expected 0 <= ④ <= ③ <= ② <= ① and ① > 0")
    return bad


def post_text(m, w, codes):
    return "\n".join([
        f"北美短信例行巡检（纽约时间 {w['label'].split(' 至 ')[1].split('，')[0]}）",
        f"最近24小时内（纽约时间 {w['label']}）：",
        f"1. 短信请求总量 {m['sms_total']}",
        f"2. 短信请求pass量 {m['sms_pass']}",
        f"3. 非美国区号且非中国区号的短信pass量 {m['pass_not_us_cn']}",
        "4. 区号在（" + ",".join("+" + c for c in codes) + f"）范围内的短信pass量 {m['pass_21']}",
    ]) + "\n"


def percode_for(rd, man, w):
    out = {}
    for gi, (lo, hi) in enumerate(man["groups"], 1):
        rows = reply(rd, f"{w['id']}_c{gi}")
        if rows is None:
            return None
        for r in rows:
            if r.get("window_start_utc") != w["start"] or r.get("shard_range") != f"{lo}..{hi}":
                raise Fail(4, f"{w['id']}_c{gi}: reply is for another window or shard range")
            p, q = out.get(r["cc"], (0, 0))
            out[r["cc"]] = (p + num(r["sms_pass"]), q + num(r["sms_requests"]))
    return out


def read_hist():
    p = os.path.join(PKG, "history", "patrol24_history.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def write_hist(rows):
    p = os.path.join(PKG, "history", "patrol24_history.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=HIST_COLS)
        wr.writeheader()
        for r in sorted(rows, key=lambda r: r["window_end_utc"]):
            wr.writerow({k: r.get(k, "") for k in HIST_COLS})


def extra_lines(m, w, pc, codes, hist, cc_hist=()):
    L = [f"附（自己看，不发群）：REJECT {m['sms_reject']}、REVIEW {m['sms_review']}；+86 的 pass {m['pass_86']}；"
         f"区号为空 {m['sms_cc_empty']}、格式不对 {m['sms_cc_invalid']}、不带+号 {m['sms_no_plus']}；"
         f"最新一条比截止时间早 {m['lag_s']} 秒"]
    if m["lag_s"] is not None and m["lag_s"] > 600:
        L.append("注意：最新一条数据比截止时间早 10 分钟以上，数可能不全，晚几分钟再跑一次再发")
    if pc is not None:
        others = sorted(((c, p) for c, (p, q) in pc.items() if c not in codes and p > 0 and c not in ("empty", "invalid")),
                        key=lambda x: -x[1])
        if others:
            L.append("21个区号以外、非美非中的 pass：" + "、".join(f"+{c}：{p}" for c, p in others[:12])
                     + f"（共 {len(others)} 个区号 {sum(p for _, p in others)} 条）")
        else:
            L.append("21个区号以外、非美非中的 pass：0")
        earlier = [r for r in cc_hist if r["window_end_utc"] < w["end"]]
        if len({r["window_end_utc"] for r in earlier}) >= 3:
            seen = {r["cc"] for r in earlier if num(r["sms_requests"]) > 0}
            new = sorted(c for c, (p, q) in pc.items() if q > 0 and c not in seen and c not in ("empty", "invalid"))
            if new:
                L.append("前几次巡检里没出现过、这次有请求的区号：" + "、".join(f"+{c}：请求 {pc[c][1]}，pass {pc[c][0]}" for c in new))
    prev = [r for r in hist if r["window_end_utc"] < w["end"] and r.get("slot_ny", "").endswith(w["key"][-5:])][-7:]
    if prev:
        def med(k):
            v = sorted(int(r[k]) for r in prev)
            return v[len(v) // 2]
        L.append("跟前几天同一时段比（中位数，" + str(len(prev)) + " 天）：①" + f"{med('sms_total')}→{m['sms_total']}，②"
                 f"{med('sms_pass')}→{m['sms_pass']}，③{med('pass_not_us_cn')}→{m['pass_not_us_cn']}，④{med('pass_21')}→{m['pass_21']}")
        for k, n in (("sms_pass", "②"), ("pass_not_us_cn", "③"), ("pass_21", "④")):
            if med(k) > 0 and m[k] > 1.5 * med(k):
                L.append(f"{n} 比前几天中位数高 50% 以上：考虑在群里单独 @ 一下")
    return "\n".join(L) + "\n"


def privacy(paths):
    scan = os.path.join(HERE, "privacy_scan.py")
    r = subprocess.run([sys.executable, scan] + paths, capture_output=True, text=True)
    summ = [l for l in r.stdout.splitlines() if l.startswith("- ")]
    if r.returncode != 0:
        raise Fail(6, "privacy scan is not clean — don't post:\n" + "\n".join(summ))
    return summ


def cmd_collect(a):
    rd = a.run_dir.rstrip("/")
    man = json.load(open(os.path.join(rd, "manifest.json"), encoding="utf-8"))
    codes = man["codes"]
    out_rows, problems = [], []
    hist = read_hist()
    now_ny = datetime.now(UTC).astimezone(NY).strftime("%Y-%m-%d %H:%M")
    for w in man["windows"]:
        m = metrics_for(rd, man, w, getattr(a, "allow_missing_shard", False))
        bad = verify_metrics(m)
        w["_pc"] = None
        if w["kind"] == "slot" and any(f.startswith(f"{w['id']}_c") for f in man["files"]):
            pc = percode_for(rd, man, w)
            if pc is None:
                bad.append("per-code replies missing: send every w01_c* file and save its reply")
            else:
                got3 = sum(p for c, (p, q) in pc.items() if c not in ("empty", "invalid"))
                got4 = sum(p for c, (p, q) in pc.items() if c in codes)
                if (got3, got4, pc.get("empty", (0, 0))[0], pc.get("invalid", (0, 0))[0]) != (
                        m["pass_not_us_cn"], m["pass_21"], m["pass_empty"], m["pass_invalid"]):
                    bad.append(f"the per-code replies add up to ③ {got3} / ④ {got4}, the totals say ③ {m['pass_not_us_cn']} / "
                               f"④ {m['pass_21']}: one of the s or c replies was mistyped; send w01_s* and w01_c* again")
                else:
                    print("per-code replies add up to ③ and ④ exactly")
                    w["_pc"] = pc
        row = dict(window=w["key"], label=w["label"], window_start_utc=w["start"], window_end_utc=w["end"], **m,
                   checks="ok" if not bad else "；".join(bad))
        if bad:
            problems.append(f"{w['label']}: " + "；".join(bad))
        if w["kind"] == "validate_ny":
            fx = {r["ny_date"]: r for r in csv.DictReader(open(os.path.join(HERE, "fixture_ny_0920_0926.csv")))}.get(w["key"])
            if fx:
                diff = [k for k in ("sms_total", "sms_pass", "sms_reject", "sms_review", "pass_1", "pass_86", "pass_21", "rows_all")
                        if int(fx[k]) != m[k]]
                if int(fx["pass_not_us_cn"]) != m["pass_not_us_cn"] + m["pass_invalid"]:
                    diff.append("pass_not_us_cn")
                row["fixture"] = "match" if not diff else "MISMATCH " + ",".join(f"{k}:{fx[k]}" for k in diff)
                if diff:
                    problems.append(f"{w['label']} 和第三个包对不上：{row['fixture']}")
            else:
                row["fixture"] = "no fixture row"
        if w["kind"] == "validate_slot":
            fx = {r["slot_ny"]: r for r in csv.DictReader(open(os.path.join(HERE, "fixture_slot2100_1003_1009.csv"), encoding="utf-8"))}.get(w["key"])
            if fx:
                keys = ("rows_all", "email_rows", "sms_total", "sms_pass", "sms_reject", "sms_review", "sms_other", "pass_1",
                        "pass_86", "pass_empty", "pass_invalid", "pass_not_us_cn", "pass_21", "pass_not_21")
                diff = [k for k in keys if int(fx[k]) != m[k]]
                if fx["window_start_utc"] != w["start"] or fx["window_end_utc"] != w["end"]:
                    diff.append("window")
                row["fixture"] = "match" if not diff else "MISMATCH " + ",".join(f"{k}:{fx.get(k)}" for k in diff)
                if diff:
                    problems.append(f"{w['label']} 和第四个包按小时算的数对不上：{row['fixture']}")
                    bad.append("fixture mismatch")
            else:
                row["fixture"] = "no fixture row"
        if w["kind"] == "validate_utc":
            fx = {r["utc_date"]: r for r in csv.DictReader(open(os.path.join(HERE, "fixture_doris_utc_0913_1008.csv")))}.get(w["key"])
            if fx:
                dt, dp = m["sms_total"] - int(fx["doris_total"]), m["sms_pass"] - int(fx["doris_pass"])
                row["fixture"] = f"Doris total {fx['doris_total']} (diff {dt:+d}), PASS {fx['doris_pass']} (diff {dp:+d})"
            else:
                row["fixture"] = "no Doris row"
        out_rows.append(row)
        if w["kind"] in ("slot", "backfill", "validate_slot") and not bad:
            hist = [h for h in hist if h["window_end_utc"] != w["end"]]
            hist.append(dict(slot_ny=w["key"], window_start_utc=w["start"], window_end_utc=w["end"], label=w["label"],
                             lag_s=m["lag_s"], kind=w["kind"], path=a.path, run_id=man["run_id"], collected_ny=now_ny,
                             **{k: m[k] for k in METRICS if k in HIST_COLS}))
    res = os.path.join(PKG, "results", f"p24_{man['run_id']}_{man['kind']}.csv")
    os.makedirs(os.path.dirname(res), exist_ok=True)
    shard_runner.write_csv(res, out_rows)
    for r in out_rows:
        print(f"{r['label']}: ① {r['sms_total']} ② {r['sms_pass']} ③ {r['pass_not_us_cn']} ④ {r['pass_21']} | REJECT {r['sms_reject']} "
              f"REVIEW {r['sms_review']} +86 {r['pass_86']} 空 {r['pass_empty']} 无效 {r['pass_invalid']} | {r['checks']}"
              + (f" | {r['fixture']}" if r.get("fixture") else ""))
    scanned = [res]
    if any(w["kind"] in ("slot", "backfill", "validate_slot") for w in man["windows"]):
        write_hist(hist)
        scanned.append(os.path.join(PKG, "history", "patrol24_history.csv"))
    if problems:
        raise Fail(4, "核对没过，不要发：\n" + "\n".join(problems))
    if man["kind"] == "slot":
        w = man["windows"][0]
        m = {k: v for k, v in out_rows[0].items()}
        pc = w["_pc"]
        stamp = w["key"].replace("-", "").replace(" ", "_").replace(":", "")
        pp = os.path.join(PKG, "posts", f"巡检_{stamp}.txt")
        xp = os.path.join(PKG, "posts", f"巡检_{stamp}_附加.txt")
        os.makedirs(os.path.dirname(pp), exist_ok=True)
        text = post_text(m, w, codes)
        open(pp, "w", encoding="utf-8").write(text)
        cp = os.path.join(PKG, "history", "patrol24_cc_pass.csv")
        old = list(csv.DictReader(open(cp, encoding="utf-8"))) if os.path.exists(cp) else []
        open(xp, "w", encoding="utf-8").write(extra_lines(m, w, pc, codes, [h for h in hist if h["window_end_utc"] != w["end"]], old))
        if pc is not None:
            old = [r for r in old if r["window_end_utc"] != w["end"]] + [
                dict(window_end_utc=w["end"], cc=c, sms_pass=p, sms_requests=q) for c, (p, q) in sorted(pc.items())]
            shard_runner.write_csv(cp, old)
            scanned.append(cp)
        scanned += [pp, xp]
        summ = privacy(scanned)
        print("\n".join(summ))
        print("\n----- 复制下面这段发群 -----\n" + text + "----- 到这里 -----\n")
        print(open(xp, encoding="utf-8").read())
        print("可以发。")
    else:
        print("\n".join(privacy(scanned)))
    return out_rows


# ----------------------------------------------------------------------------- path A
def _usable(entry):
    """(url, why-not) for one mcpServers entry; never returns or prints anything else from it."""
    if not isinstance(entry, dict):
        return None, "格式不对"
    kind = str(entry.get("type") or "sse").lower()
    url = entry.get("url") or ""
    if kind != "sse":
        return None, f"类型 {kind}，不是 sse"
    if entry.get("headers"):
        return None, "需要 headers"
    if not isinstance(url, str) or not url or "${" in url:
        return None, "没有地址或地址里有变量"
    if not re.match(r"https?://", url):
        return None, "不是 http(s) 地址"
    return url, ""


def _git_root(folder):
    try:
        r = subprocess.run(["git", "-C", folder, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        return os.path.abspath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def resolve_gateway(run_folder=None, use_cli=True, home=None):
    """(url | None, where, note). Looks only at the mcp-db-gateway entry; `where` is a fixed label. The URL is returned to
    the caller (who puts it into a child's environment) and is never printed, logged or written."""
    rf = os.path.abspath(run_folder or RUN_FOLDER)
    home = home or os.path.expanduser("~")
    tried = []
    if os.environ.get("MCP_DB_GATEWAY_SSE"):
        return os.environ["MCP_DB_GATEWAY_SSE"], "环境变量", ""
    data = None
    cj = os.path.join(home, ".claude.json")
    if os.path.exists(cj):
        try:
            data = json.load(open(cj, encoding="utf-8"))
        except Exception:
            tried.append("用户配置文件读不出")
    projects = (data.get("projects") or {}) if isinstance(data, dict) else {}
    keys = [rf] + [k for k in [_git_root(rf)] if k and k != rf]
    for k in keys:
        e = ((projects.get(k) or {}).get("mcpServers") or {}).get(GATEWAY)
        if e is not None:
            url, why = _usable(e)
            if url:
                return url, "本地作用域", ""
            tried.append("本地作用域：" + why)
    if isinstance(data, dict):
        e = (data.get("mcpServers") or {}).get(GATEWAY)
        if e is not None:
            url, why = _usable(e)
            if url:
                return url, "用户作用域", ""
            tried.append("用户作用域：" + why)
    for k in keys:
        pj = os.path.join(k, ".mcp.json")
        if os.path.exists(pj):
            try:
                e = (json.load(open(pj, encoding="utf-8")).get("mcpServers") or {}).get(GATEWAY)
            except Exception:
                tried.append("项目 .mcp.json 读不出")
                continue
            if e is None:
                continue
            approved = GATEWAY in ((projects.get(k) or {}).get("enabledMcpjsonServers") or [])
            url, why = _usable(e)
            if url and approved:
                return url, "项目 .mcp.json", ""
            tried.append("项目 .mcp.json：" + (why or "没有批准过"))
    if use_cli and shutil.which("claude"):
        try:
            r = subprocess.run(["claude", "mcp", "get", GATEWAY], cwd=rf, capture_output=True, text=True, timeout=30)
            text = (r.stdout or "") + "\n" + (r.stderr or "")
            mu = re.search(r"(?im)^\s*URL:\s*(\S+)", text)
            mt = re.search(r"(?im)^\s*Type:\s*(\S+)", text)
            if mu and (not mt or mt.group(1).lower() == "sse") and "${" not in mu.group(1) and re.match(r"https?://", mu.group(1)):
                return mu.group(1), "claude mcp get", ""
            tried.append("claude mcp get：没有可用的 sse 地址")
        except Exception:
            tried.append("claude mcp get：没跑成")
    return None, "", "；".join(tried) or "没有找到 mcp-db-gateway 的配置"


def cmd_gateway_check(a):
    url, where, note = resolve_gateway(use_cli=not getattr(a, "no_cli", False))
    if url:
        print(f"{GATEWAY}：在「{where}」找到（类型 sse）；地址不显示、不写文件；路 A 可用。")
        return 0
    print(f"没找到可用的 {GATEWAY} 配置（{note}）：用路 B（运行卡 B）。")
    raise SystemExit(8)


def _send_files(rd, names, gw, servers, now_fn, man=None, sent=None):
    for n in names:
        if not window_open(now_fn(), 0) and not man_outside_ok(man or {}, now_fn()):
            raise Fail(2, window_msg(now_fn(), _hint_kind(man)) + "（已发的回复保留在运行目录里。）")
        sql = open(os.path.join(rd, n), encoding="utf-8").read()
        t0 = now_fn()
        try:
            rows, el = gw.query(servers.get(n, shard_runner.RISK_SERVER), sql)
        except SystemExit as ex:                     # the 4th package's runner refuses outside 22:00-05:30 (nothing sent)
            if "production pull window" in str(ex):
                raise Fail(2, window_msg(now_fn(), _hint_kind(man)))
            raise
        except RuntimeError:                         # it left: a server error or a reply timeout still counts as sent
            if sent is not None:
                sent.append(t0)
            raise
        json.dump({"rows": rows}, open(os.path.join(rd, n[:-4] + ".json"), "w"), default=str)
        if sent is not None:
            sent.append(t0)
        time.sleep(shard_runner.PAUSE_S)


def cmd_send(a, now_fn=None, gateway=None):
    """Hidden child of `run`: needs MCP_DB_GATEWAY_SSE in its own environment (set by the parent, never printed)."""
    now_fn = now_fn or (lambda: datetime.now(UTC))
    if gateway is None and not os.environ.get("MCP_DB_GATEWAY_SSE"):
        raise Fail(2, "no gateway address in this process: run `patrol24.py run` / `nightly`, or use path B")
    rd = a.run_dir.rstrip("/")
    man = json.load(open(os.path.join(rd, "manifest.json"), encoding="utf-8"))
    servers = man.get("servers") or {}
    lk = _lock()
    gw = None
    orig_window_check = shard_runner.prod_window_ok
    ow = man_outside_ok(man, now_fn())
    sent = []
    if ow:
        allow_runner_outside()        # this send only (restored below); the runner file is not changed
    try:
        try:
            gw = gateway or shard_runner.Gateway().connect()
            if man.get("kind") == "discover":
                _send_files(rd, man["files"], gw, servers, now_fn, man, sent)
                return 0
            s0 = [f for f in man["files"] if f.startswith("s0")]
            _send_files(rd, s0, gw, servers, now_fn, man, sent)
            if man.get("tool") == "eohq24":
                pl, tr, ex = (reply(rd, n) for n in ("s0a_processlist", "s0b_threads", "s0d_explain"))
                verdict, why = load_check(pl or [], tr or [])
                if verdict == "GO":
                    ok, txt = (explain_ok_upush(ex or [], man.get("explain_keys")) if man.get("kind") in ("upush", "upush_extra")
                               else explain_ok(ex or []))
                    verdict, why = ("GO", why) if ok else ("STOP", "EXPLAIN gate failed: " + txt)
                if not window_open(now_fn(), 15):
                    verdict, why = "LATE", window_msg(now_fn())
            else:
                verdict, why = gate(rd, now_fn())
            print(f"{verdict}: {why}")
            if verdict != "GO":
                raise SystemExit({"WAIT": 7, "LATE": 2}.get(verdict, 4))
            _send_files(rd, [f for f in man["files"] if not f.startswith("s0")], gw, servers, now_fn, man, sent)
        except RuntimeError as ex:
            raise Fail(5, f"query failed: {ex}")
    finally:
        shard_runner.prod_window_ok = orig_window_check
        if ow and sent and not all(window_open(t) for t in sent):
            log_outside("_send", man.get("kind"), rd, sent[-1],
                        f"{len(sent)} statements sent, NY {sent[0].astimezone(NY):%H:%M:%S}-{sent[-1].astimezone(NY):%H:%M:%S}; "
                        f"outside 22:00-05:30 under the user's decision for {OUTSIDE_WINDOW_DAY}")
        if gateway is None and gw is not None:
            gw.close()
        lk.__exit__(None, None, None)
    return 0


def allow_runner_outside():
    """The user's one-day exception reaches the 4th package's runner, which checks prod_window_ok() in Gateway.query:
    replace that check for this (child) process only. Called only when man_outside_ok() holds."""
    shard_runner.prod_window_ok = lambda now=None: True


def _lock():
    """This run folder's own DB lock (shard_runner.Lock); a held or stale lock is exit 3 with a readable reason."""
    try:
        return shard_runner.Lock().__enter__()
    except SystemExit:
        p = os.path.join(shard_runner.PKG, "_local_only", ".db_lock")
        try:
            pid = int(open(p).read().strip() or 0)
        except (OSError, ValueError):
            pid = 0
        state = "进程还在" if pid and pid_alive(pid) else "进程已不在，像是上次中断留下的"
        raise Fail(3, f"RC_patrol/_local_only/.db_lock 已存在（PID {pid or '?'}，{state}）。先用 ps 看有没有 patrol24 / "
                      "shard_runner 还在跑；确认没有，再删掉这个锁文件重跑。")


def _child(rd, url, runner=subprocess.run):
    env = dict(os.environ)
    env["MCP_DB_GATEWAY_SSE"] = url
    r = runner([sys.executable, os.path.abspath(__file__), "_send", rd], env=env)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def cmd_run(a, now_utc=None, runner=subprocess.run):
    """Path A: resolve the gateway, emit, let a child process send, collect."""
    now_utc = now_utc or datetime.now(UTC)
    if getattr(a, "outside_window_ok", False):
        if now_utc.astimezone(NY).date().isoformat() != OUTSIDE_WINDOW_DAY:
            raise Fail(2, outside_msg(now_utc))
    else:
        require_window(now_utc, 15, kind_of(a))
    if os.path.exists(os.path.join(HERE, "SHA256SUMS")):
        cmd_verify()
    url, where, note = resolve_gateway(use_cli=not getattr(a, "no_cli", False))
    if not url:
        raise Fail(8, f"没找到可用的 {GATEWAY} 地址（{note}）：用路 B（运行卡 B）。")
    print(f"gateway：{where}（地址不显示）")
    rd = cmd_emit(a, now_utc)
    man = json.load(open(os.path.join(rd, "manifest.json"), encoding="utf-8"))
    if man.get("kind") == "discover":
        _child(rd, url, runner)
        cmd_shards(argparse.Namespace(run_dir=rd))
        rd = cmd_emit(a, now_utc)
    _child(rd, url, runner)
    a.run_dir, a.path = rd, "A"
    return cmd_collect(a)


def cmd_nightly(a, now_utc=None, runner=subprocess.run):
    """The one evening command: tonight's 21:00 window with the per-code check, path A."""
    ns = argparse.Namespace(date=None, at="21:00", codes=None, per_code=True, m1_active_ok=a.m1_active_ok, force=False,
                            validate_slot=None, validate_ny=None, validate_utc=None, backfill=None, path="A",
                            no_cli=getattr(a, "no_cli", False), allow_missing_shard=False,
                            outside_window_ok=getattr(a, "outside_window_ok", False), cmd="nightly")
    return cmd_run(ns, now_utc, runner)


def find_saved_window(key):
    """(run dir, window id, groups) of a saved patrol24 run that holds every reply for the window `key` ('YYYY-MM-DD HH:MM')."""
    for mf in sorted(glob.glob(os.path.join(PKG, "runs", "*", "manifest.json"))):
        try:
            man = json.load(open(mf, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if man.get("tool", "patrol24") != "patrol24" or not man.get("groups"):
            continue
        rd = os.path.dirname(mf)
        for w in man.get("windows", []):
            names = [f"{w['id']}_s{gi}" for gi in range(1, len(man["groups"]) + 1)]
            names += ["s0a_processlist", "s0b_threads", "s0c_shards", "s0d_explain"]
            if w.get("key") == key and all(os.path.exists(os.path.join(rd, n + ".json")) for n in names):
                return rd, w["id"], len(man["groups"])
    return None


def cmd_replay_test(a):
    """Offline, any time, no database: replay saved replies of one 21:00 window through emit / collect in a temporary copy.
    (a) validate-slot must report `match` against the fixture; (b) the slot run must print the post and end with 可以发.
    Nothing in RC_patrol/ changes."""
    import tempfile
    d = a.date or "2026-10-09"
    src = find_saved_window(f"{d} {a.at}")
    if not src:
        raise Fail(4, f"没找到保存了 {d} {a.at} 那一段全部回复的运行目录（runs/*/manifest.json）；离线回放没法做。")
    srd, wid, ng = src
    print(f"replay source: {os.path.relpath(srd, PKG)} window {wid} ({d} {a.at}); no database is contacted")
    tmp = tempfile.mkdtemp(prefix="p24replay_")
    ok = True
    try:
        rp = os.path.join(tmp, "RC_patrol")
        shutil.copytree(HERE, os.path.join(rp, "toolkit"), ignore=shutil.ignore_patterns("__pycache__"))
        for sub in ("config", "history"):
            if os.path.isdir(os.path.join(PKG, sub)):
                shutil.copytree(os.path.join(PKG, sub), os.path.join(rp, sub))
        os.makedirs(os.path.join(rp, "_local_only"))
        rw = os.path.join(PKG, "_local_only", "reserved_words.txt")
        if os.path.exists(rw):
            shutil.copy2(rw, os.path.join(rp, "_local_only"))
        env = dict(os.environ)
        env.pop("MCP_DB_GATEWAY_SSE", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        py = [sys.executable, os.path.join(rp, "toolkit", "patrol24.py")]
        for mode, args in (("validate", ["emit", "--validate-slot", f"{d}:{d}", "--at", a.at]),
                           ("post", ["emit", "--date", d, "--at", a.at])):
            r = subprocess.run(py + args, env=env, capture_output=True, text=True, cwd=rp)
            m = re.search(r" in (runs/\S+)/", r.stdout)
            if r.returncode or not m:
                print(f"[{mode}] emit failed (exit {r.returncode}): {r.stderr.strip()[-300:]}")
                ok = False
                continue
            nrd = os.path.join(rp, m.group(1))
            for n in ("s0a_processlist", "s0b_threads", "s0c_shards", "s0d_explain"):
                shutil.copy2(os.path.join(srd, n + ".json"), os.path.join(nrd, n + ".json"))
            for gi in range(1, ng + 1):
                shutil.copy2(os.path.join(srd, f"{wid}_s{gi}.json"), os.path.join(nrd, f"w01_s{gi}.json"))
            r = subprocess.run(py + ["collect", nrd], env=env, capture_output=True, text=True, cwd=rp)
            good = r.returncode == 0 and (("| match" in r.stdout) if mode == "validate" else ("可以发。" in r.stdout))
            ok = ok and good
            print(f"\n[{mode}] collect exit {r.returncode} -> {'OK' if good else 'FAILED'}")
            print(r.stdout.strip() if good else (r.stdout.strip() + "\n" + r.stderr.strip())[-2000:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not ok:
        raise Fail(4, "离线回放没过（见上面的输出）。")
    print("\nreplay-test: OK (offline; RC_patrol/ unchanged)")
    return 0


def cmd_seed_history(a):
    """Path B fallback only: put the 4th package's 21:00 windows (fixture_slot…csv) into history when no validate-slot
    run could be done. Never overwrites a row that came from a run."""
    hist = read_hist()
    have = {h["window_end_utc"] for h in hist}
    added = 0
    for r in csv.DictReader(open(os.path.join(HERE, "fixture_slot2100_1003_1009.csv"), encoding="utf-8")):
        if r["window_end_utc"] in have:
            continue
        s = datetime.strptime(r["window_start_utc"], FMT).replace(tzinfo=UTC)
        e = datetime.strptime(r["window_end_utc"], FMT).replace(tzinfo=UTC)
        hist.append(dict(slot_ny=r["slot_ny"], window_start_utc=r["window_start_utc"], window_end_utc=r["window_end_utc"],
                         label=label(s, e), kind="fixture_l1", path="-", run_id="第四个包", collected_ny="",
                         **{k: r[k] for k in HIST_COLS if k in r and k not in ("slot_ny", "window_start_utc", "window_end_utc")}))
        added += 1
    write_hist(hist)
    print(f"history: {added} rows added from the 4th package's hourly series (kind fixture_l1)")


# ----------------------------------------------------------------------------- misc
def cmd_doris(a):
    codes = codes21(a.codes)
    d = date.fromisoformat(a.date) if a.date else latest_slot_date(datetime.now(UTC), a.at)
    s, e = slot_window(d, a.at)
    both = ", ".join(f"'+{c}', '{c}'" for c in codes)
    t = f"{d.isoformat()} {a.at}:00"
    print(f"""-- 北美短信例行巡检，Doris 写法（和 21 点那次同口径；没在 Doris 上执行过，第一次跑请对一下 cc_odd_rows 和 newest_utc）
-- 每天只改下面两处的日期（纽约时间 {a.at} 截止）；CONVERT_TZ 自己处理夏令时，窗口永远是整 24 小时。
-- 这一次：纽约时间 {label(s, e)} = UTC [{s:%Y-%m-%d %H:%M:%S}, {e:%Y-%m-%d %H:%M:%S})
SELECT COUNT(*) AS sms_total,
       SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) AS sms_pass,
       SUM(CASE WHEN result = 'PASS' AND country_code IS NOT NULL AND country_code NOT IN ('', '+1', '1', '+86', '86') THEN 1 ELSE 0 END) AS pass_not_us_cn,
       SUM(CASE WHEN result = 'PASS' AND country_code IN ({both}) THEN 1 ELSE 0 END) AS pass_21,
       SUM(CASE WHEN country_code IS NULL OR country_code NOT LIKE '+%' THEN 1 ELSE 0 END) AS cc_odd_rows,
       MAX(access_time) AS newest_utc
FROM t_iriskcontrol_log
WHERE access_time >= DATE_SUB(CONVERT_TZ('{t}', 'America/New_York', 'UTC'), INTERVAL 24 HOUR)
  AND access_time <  CONVERT_TZ('{t}', 'America/New_York', 'UTC')
  AND l1_scene = '1000' AND l2_scene = '1001' AND tenant = 'LKUS';
-- 源库这边第 3 项还去掉了不是 1-4 位数字的区号（核过的窗口里一直是 0 条），这里没有；cc_odd_rows 只看区号带不带加号，量不出这个差。""")


def cmd_reserved(a):
    """Save the KEYWORDS reply (one row per reserved word) as _local_only/reserved_words.txt and check the count."""
    rows = rows_of(a.reply)
    words = [str(r.get("WORD") or r.get("word") or r.get("w") or "").strip() for r in rows]
    words = [w for w in words if w]
    if len(words) != len(rows) or len(words) < 200 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", w) for w in words):
        raise Fail(4, f"reply has {len(rows)} rows, {len(words)} usable words: expected one word per row (about 260)")
    os.makedirs(os.path.join(PKG, "_local_only"), exist_ok=True)
    open(os.path.join(PKG, "_local_only", "reserved_words.txt"), "w").write("\n".join(sorted(set(words))) + "\n")
    print(f"_local_only/reserved_words.txt: {len(set(words))} reserved words")


def cmd_verify(a=None):
    p = os.path.join(HERE, "SHA256SUMS")
    if not os.path.exists(p):
        raise Fail(4, "toolkit/SHA256SUMS missing")
    bad, n = [], 0
    for line in open(p, encoding="utf-8"):
        if not line.strip():
            continue
        want, name = line.split(None, 1)
        name = name.strip()
        f = os.path.join(HERE, name)
        got = hashlib.sha256(open(f, "rb").read()).hexdigest() if os.path.exists(f) else "missing"
        n += 1
        if got != want:
            bad.append(name)
    print(f"toolkit sha256: {n - len(bad)}/{n} match" + (f"; differ: {', '.join(bad)}" if bad else ""))
    if bad:
        raise SystemExit(4)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("emit", "run"):
        p = sub.add_parser(nm)
        p.add_argument("--date"); p.add_argument("--at", default="21:00"); p.add_argument("--codes")
        p.add_argument("--per-code", action="store_true"); p.add_argument("--m1-active-ok", action="store_true")
        p.add_argument("--force", action="store_true", help="tests only: skip the too-early check (never the production window)")
        g = p.add_mutually_exclusive_group()
        g.add_argument("--validate-slot"); g.add_argument("--validate-ny"); g.add_argument("--validate-utc")
        g.add_argument("--backfill", type=int)
        p.add_argument("--path", default="A"); p.add_argument("--no-cli", action="store_true")
        p.add_argument("--outside-window-ok", action="store_true",
                       help=f"user decision 2026-10-10: exactly one window ending 21:00 (slot / one-day validate_slot) outside "
                            f"22:00-05:30, on {OUTSIDE_WINDOW_DAY} only; logged when used outside the window")
    p = sub.add_parser("nightly"); p.add_argument("--m1-active-ok", action="store_true"); p.add_argument("--no-cli", action="store_true")
    p.add_argument("--outside-window-ok", action="store_true", help=f"see emit; {OUTSIDE_WINDOW_DAY} only")
    p = sub.add_parser("replay-test"); p.add_argument("--date"); p.add_argument("--at", default="21:00")
    p = sub.add_parser("gateway-check"); p.add_argument("--no-cli", action="store_true")
    p = sub.add_parser("_send"); p.add_argument("run_dir")
    sub.add_parser("seed-history")
    for nm in ("gate", "collect", "shards"):
        p = sub.add_parser(nm); p.add_argument("run_dir")
        if nm == "collect":
            p.add_argument("--path", default="B", choices=["A", "B"])
            p.add_argument("--allow-missing-shard", action="store_true",
                           help="only when a shard really returned no rows in the window (checked by hand)")
    p = sub.add_parser("doris-sql"); p.add_argument("--date"); p.add_argument("--at", default="09:00"); p.add_argument("--codes")
    p = sub.add_parser("reserved"); p.add_argument("reply", help="saved reply of the KEYWORDS statement (json)")
    sub.add_parser("verify"); sub.add_parser("init")
    a = ap.parse_args(argv)
    {"emit": cmd_emit, "run": cmd_run, "nightly": cmd_nightly, "gate": cmd_gate, "collect": cmd_collect,
     "shards": cmd_shards, "gateway-check": cmd_gateway_check, "_send": cmd_send, "seed-history": cmd_seed_history,
     "doris-sql": cmd_doris, "reserved": cmd_reserved, "verify": cmd_verify, "init": cmd_init,
     "replay-test": cmd_replay_test}[a.cmd](a)


if __name__ == "__main__":
    main()
