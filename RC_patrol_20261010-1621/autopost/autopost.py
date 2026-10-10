#!/usr/bin/env python3
"""autopost.py — 每晚 21:00 短信巡检的飞书自动发群（用户 2026-10-10 决定）。

Runs from cron every half hour (`5,35 * * * *`); it acts only for the 21:00 window of New York date D:
  22:05-23:35 NY  up to 4 attempts, 30 minutes apart: `toolkit/patrol24.py run --date D --per-code` as a child process
                  (path A, the same command as run card A); a verified post goes to the webhook of the current target.
  at 23:35        if nothing could be posted, the fixed failure line goes to the same group (no numbers).
  23:40-00:39     no database; only a late failure line if the 23:35 one was missed or failed.
  from 00:40      gave_up (logged).
User decisions (2026-10-10): test group first, then the team group (`set-mode team`); failure line on failure; retries
until 23:35; no signing required (optional per target); no alert channel (local log and `status` only).

Never: database statements of its own (patrol24 does all of that, with its own 22:00-05:30 checks); --m1-active-ok,
--force or --outside-window-ok; posting a window twice; posting text it did not produce and check itself; the private
附加 lines; printing, logging or packaging a webhook (it lives only in RC_patrol/_local_only/feishu.conf, mode 600,
entered by the user with `set-webhook` in their own terminal).

Commands (from anywhere; RC_patrol = the folder above autopost/):
  cron                          the scheduled entry point (does nothing outside 22:03-00:40 NY)
  status                        mode, targets (yes/no + fingerprint), heartbeat, cron line, the last 7 windows
  set-webhook --target test|team [--secret]   TTY only; reads the address (and signing secret) without echo
  forget-webhook --target T | set-mode test|team [--force] | enable | disable
  skip --date D | unskip --date D | set-start --date D
  send-post --date D [--resend-uncertain]     manual 补发 of a checked post file (asks you to type 发送)
  test-send --target test       one fixed test line (never to team)
  dry-run [--at "YYYY-MM-DD HH:MM"]           what the next firing would do (no database, no network)
  rehearse [--date D]           offline: replays saved replies of one window through patrol24 + autopost in a temp copy
  net-check                     TLS handshake with the Feishu host only (no webhook)
  leakcheck                     looks for the configured webhook / secret anywhere outside feishu.conf
  cron-line | install-cron | uninstall-cron | init --start-date D [--no-cli] | adopt-host | verify
Exit codes: 0 ok · 2 refused / usage · 4 a check failed · 5 send failed.
"""
import argparse, base64, csv, fcntl, getpass, glob, hashlib, hmac, http.client, json, os, re, shutil, signal, socket, ssl
import subprocess, sys, tempfile, time, traceback
from datetime import date, datetime, time as dtime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                     # RC_patrol
RUN_FOLDER = os.path.dirname(PKG)
NY, UTC = ZoneInfo("America/New_York"), timezone.utc
FMT = "%Y-%m-%d %H:%M:%S"
HOST = "open.feishu.cn"
URL_RE = re.compile(r"^https://open\.feishu\.cn/open-apis/bot/v2/hook/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TAG = "# RC_patrol-autopost"
FIRST, LAST, NODB, CATCH = (22, 3), (23, 35), (23, 40), (0, 40)   # CATCH is on D+1
ACTIVE_FROM = (21, 30)
MAX_ATTEMPTS, MIN_GAP_S, MAX_BUSY, CHILD_TIMEOUT_S, DAILY_CAP, LAG_MAX_S = 4, 25 * 60, 3, 20 * 60, 3, 600
FINAL = {"posted", "failline_posted", "send_uncertain", "send_rejected", "manual_skip", "gave_up", "reposted", "manual_send_retry"}
LAG_STALL_S = 3600                              # no row at all in the last hour before the cut-off: the log source looks stalled
FORBIDDEN_ARGS = ("--m1-active-ok", "--force", "--outside-window-ok", "--allow-missing-shard")
FAILLINE = "今晚21点的巡检数暂时取不到，弄好后补发。"
TESTLINE = "北美短信例行巡检：自动发送测试（只发到测试群，不是巡检结果）。"
LINE3 = "1. 短信请求总量 "
LINE4 = "2. 短信请求pass量 "
LINE5 = "3. 非美国区号且非中国区号的短信pass量 "
DENY = ("附", "自己看", "REJECT", "REVIEW", "注意", "@", "<at", "http")
LOG_COLS = ["ny_time", "window", "event", "attempt", "exit", "class", "target", "result", "note"]
FEISHU_CODES = {19021: "签名不对或时间差超过1小时", 19022: "IP 不在白名单", 19024: "缺关键词", 9499: "请求格式不对",
                11232: "限流", 19001: "webhook 无效（未核实）"}
NOTES = {"timeout": "子进程超时，已中断", "lock_here": "本目录锁文件还在", "other_db_run": "另一个查库任务在跑",
         "busy": "服务器忙", "gw_connect": "网关连不上", "query_failed": "查询失败", "check_failed": "核对没过",
         "privacy": "隐私扫描没过", "no_gateway": "找不到网关配置", "lag": "数据延迟超过10分钟", "verify_fail": "自动核对没过",
         "unexpected": "意外错误", "not_counted": "还没到时间或不在时段", "toolkit_missing": "巡检工具不在", "ok": "正常",
         "busy_exhausted": "服务器忙，重试用完"}


def p(*parts):
    return os.path.join(PKG, *parts)


CONF = p("config", "autopost.json")
STATE_DIR = p("history", "autopost_state")
LOG = p("history", "autopost_log.csv")
SECRETS = p("_local_only", "feishu.conf")
LOCAL = p("_local_only", "autopost")
PATROL = p("toolkit", "patrol24.py")


class Refuse(SystemExit):
    def __init__(self, msg, code=2):
        print(msg, file=sys.stderr)
        super().__init__(code)


# ----------------------------------------------------------------------------- windows (own copy; tests compare with patrol24)
def slot_window(d):
    end = datetime.combine(d, dtime(21, 0), tzinfo=NY).astimezone(UTC)
    return end - timedelta(hours=24), end


def label(s, e):
    sl, el = s.astimezone(NY), e.astimezone(NY)
    txt = f"{sl.month}/{sl.day} {sl:%H:%M} 至 {el.month}/{el.day} {el:%H:%M}"
    if sl.utcoffset() != el.utcoffset():
        txt += "，跨夏令时切换，按整24小时"
    return txt


def header(d):
    e = slot_window(d)[1].astimezone(NY)
    return f"北美短信例行巡检（纽约时间 {e.month}/{e.day} 21:00）"


def at(d, hm, plus_days=0):
    return datetime.combine(d + timedelta(days=plus_days), dtime(*hm), tzinfo=NY).astimezone(UTC)


def window_date(now):
    """NY date of the 21:00 cut-off a firing works on: today from 21:30, yesterday before 05:30, else None."""
    t = now.astimezone(NY)
    if (t.hour, t.minute) >= ACTIVE_FROM:
        return t.date()
    if (t.hour, t.minute) < (5, 30):
        return t.date() - timedelta(days=1)
    return None


# ----------------------------------------------------------------------------- small helpers
def nyfmt(now):
    return now.astimezone(NY).strftime("%Y-%m-%d %H:%M:%S")


def atomic_write(path, text, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def ensure_dirs():
    for d in (p("config"), STATE_DIR, p("_local_only"), LOCAL, os.path.join(LOCAL, "child")):
        os.makedirs(d, exist_ok=True)
    for d in (p("_local_only"), LOCAL, os.path.join(LOCAL, "child")):
        os.chmod(d, 0o700)


def log(now, window, event, attempt="", exit_="", cls="", target="", result="", note=""):
    new = not os.path.exists(LOG)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(LOG_COLS)
        w.writerow([nyfmt(now), window, event, attempt, exit_, cls, target, result, note])


def host_pin():
    mid = ""
    for f in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            mid = open(f).read().strip()
            break
        except OSError:
            continue
    return hashlib.sha256(f"{socket.gethostname()}|{mid}".encode()).hexdigest()[:12]


def load_cfg():
    try:
        return json.load(open(CONF, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_cfg(cfg):
    atomic_write(CONF, json.dumps(cfg, ensure_ascii=False, indent=1) + "\n")


def need_cfg():
    cfg = load_cfg()
    if cfg is None:
        raise Refuse("还没初始化：先跑 `autopost.py init --start-date <纽约日期>`。")
    return cfg


def change(cfg, now, what):
    cfg.setdefault("changes", []).append({"ny": nyfmt(now), "what": what})
    save_cfg(cfg)


# ----------------------------------------------------------------------------- webhook store (never printed)
def load_conf():
    if not os.path.exists(SECRETS):
        return {}
    st = os.stat(SECRETS)
    if st.st_mode & 0o077 or st.st_uid != os.getuid():
        raise Refuse("_local_only/feishu.conf 的权限不对（应为 600、属于当前用户）：先 `chmod 600` 再跑。")
    try:
        data = json.load(open(SECRETS, encoding="utf-8"))
    except ValueError:
        raise Refuse("_local_only/feishu.conf 读不出（不是 JSON）：用 set-webhook 重新录。")
    return data if isinstance(data, dict) else {}


def save_conf(data):
    ensure_dirs()
    atomic_write(SECRETS, json.dumps(data) + "\n", 0o600)


def fp(entry):
    return hashlib.sha256(entry["url"].encode()).hexdigest()[:8] if entry and entry.get("url") else ""


def secret_bits(conf=None):
    conf = load_conf() if conf is None else conf
    bits = set()
    for e in conf.values():
        if not isinstance(e, dict):
            continue
        u = e.get("url") or ""
        if u:
            bits.update({u, u.rsplit("/", 1)[-1]})
        if e.get("sig_key"):
            bits.add(e["sig_key"])
    return {b for b in bits if len(b) >= 8}


def redact(text, bits):
    for b in sorted(bits, key=len, reverse=True):
        text = text.replace(b, "<redacted>")
    return re.sub(r"https?://\S+", "<url>", text)


def sign(ts, key):
    return base64.b64encode(hmac.new(f"{ts}\n{key}".encode("utf-8"), b"", hashlib.sha256).digest()).decode()


# ----------------------------------------------------------------------------- state per window
def state_path(d):
    return os.path.join(STATE_DIR, f"{d.isoformat()}.json")


def load_state(d):
    try:
        return json.load(open(state_path(d), encoding="utf-8"))
    except (OSError, ValueError):
        s, e = slot_window(d)
        return {"schema": 1, "window_date": d.isoformat(), "window_start_utc": s.strftime(FMT), "window_end_utc": e.strftime(FMT),
                "label": label(s, e), "target": None, "target_fp": "", "status": "pending", "busy": 0, "attempts": [],
                "own_runs": [], "verify": None, "sends": []}


def save_state(st):
    atomic_write(state_path(date.fromisoformat(st["window_date"])), json.dumps(st, ensure_ascii=False, indent=1) + "\n")


def counted(st):
    return sum(1 for a in st["attempts"] if a.get("counted"))


# ----------------------------------------------------------------------------- the child (patrol24, path A)
def child_argv(cfg, d):
    argv = [cfg.get("python") or sys.executable, "-B", PATROL, "run", "--date", d.isoformat(), "--per-code"]
    if cfg.get("no_cli"):
        argv.append("--no-cli")
    assert not any(a in argv for a in FORBIDDEN_ARGS)
    return argv


PROXY_FILE = os.path.join(LOCAL, "feishu_proxy")


def feishu_proxy():
    """The proxy for the Feishu connection only (one line `https_proxy=…` in _local_only/autopost/feishu_proxy); never
    given to the patrol24 child, whose database gateway connection stays as it is."""
    if os.path.exists(PROXY_FILE):
        for line in open(PROXY_FILE, encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and k.lower() == "https_proxy" and v:
                return v
    return None


def child_env(cfg):
    return {"HOME": cfg.get("home") or os.path.expanduser("~"), "PATH": cfg.get("child_path") or "/usr/local/bin:/usr/bin:/bin",
            "LANG": cfg.get("lang") or "C.UTF-8", "LC_ALL": cfg.get("lang") or "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}


PROC_DIR = "/proc"                              # Linux: the command line tells a reused pid from our patrol24 child


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    cmd = os.path.join(PROC_DIR, str(int(pid)), "cmdline")
    if os.path.exists(cmd):
        try:
            return b"patrol24" in open(cmd, "rb").read()
        except OSError:
            return True
    return True


def real_runner(argv, cwd, env, timeout, on_start=None, out_base=None):
    """(returncode, stdout, stderr, timed_out). Output goes to files (<out_base>.out / .err, mode 600), not pipes: if this
    process dies, the child can still finish, and a later firing can read what it printed. Own session; on timeout SIGINT
    to the group so patrol24's lock is released."""
    out_base = out_base or os.path.join(LOCAL, "child", f"run_{os.getpid()}")
    fo = os.fdopen(os.open(out_base + ".out", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w")
    fe = os.fdopen(os.open(out_base + ".err", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w")
    timed_out = False
    try:
        pr = subprocess.Popen(argv, cwd=cwd, env=env, stdout=fo, stderr=fe, start_new_session=True)
        if on_start:
            on_start(pr.pid)
        try:
            pr.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            for sig, wait in ((signal.SIGINT, 60), (signal.SIGKILL, None)):
                try:
                    os.killpg(pr.pid, sig)
                except ProcessLookupError:
                    pass
                try:
                    pr.wait(timeout=wait)
                    break
                except subprocess.TimeoutExpired:
                    continue
    finally:
        fo.close()
        fe.close()
    read = lambda f: open(f, encoding="utf-8", errors="replace").read() if os.path.exists(f) else ""
    return pr.returncode, read(out_base + ".out"), read(out_base + ".err"), timed_out


def last_line(out):
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def classify(rc, out, err, timed_out):
    """(class, kind, counted) with kind ok / retry / terminal."""
    if timed_out:
        return "timeout", "terminal", True
    if rc == 0:
        return ("ok", "ok", True) if last_line(out) == "可以发。" else ("unexpected", "terminal", True)
    if rc == 2:
        return "not_counted", "retry", False
    if rc == 3:
        return ("lock_here" if ".db_lock" in err else "other_db_run"), "retry", True
    if rc == 7:
        return "busy", "retry", True
    if rc == 5:
        if re.search(r"(?m)^query failed: gateway connect failed", err):
            return "gw_connect", "retry", True
        return "query_failed", "terminal", True
    return {4: "check_failed", 6: "privacy", 8: "no_gateway"}.get(rc, "unexpected"), "terminal", True


def list_runs():
    return sorted(os.path.basename(x) for x in glob.glob(p("runs", "*")) if os.path.isdir(x))


def read_hist():
    f = p("history", "patrol24_history.csv")
    return list(csv.DictReader(open(f, encoding="utf-8"))) if os.path.exists(f) else []


def post_path(d):
    return p("posts", f"巡检_{d:%Y%m%d}_2100.txt")


def codes21():
    return [l.strip() for l in open(p("toolkit", "codes_21.txt"), encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]


def manual_run(st, d):
    """True if someone ran this window by hand (anything autopost did not start)."""
    own = set(st.get("own_runs") or [])
    key = f"{d.isoformat()} 21:00"
    for rd in list_runs():
        if rd in own or not rd.endswith("_slot"):
            continue
        try:
            man = json.load(open(p("runs", rd, "manifest.json"), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if any(w.get("key") == key for w in man.get("windows", [])):
            return True
    own_ids = {r.rsplit("_", 1)[0] for r in own}
    if any(h.get("window_end_utc") == st["window_end_utc"] and h.get("run_id") not in own_ids for h in read_hist()):
        return True
    pp = post_path(d)
    if os.path.exists(pp):
        m = os.path.getmtime(pp)
        if not any(a.get("t0", 0) - 1 <= m <= a.get("t1", 0) + 1 for a in st["attempts"]):
            return True
    return False


def parse_post(text, d, codes):
    """The four numbers from a post that must look exactly like patrol24's, or raise ValueError."""
    s, e = slot_window(d)
    lines = text.split("\n")
    if len(lines) != 7 or lines[6] != "":
        raise ValueError("不是 6 行加结尾换行")
    if lines[0] != header(d) or lines[1] != f"最近24小时内（纽约时间 {label(s, e)}）：":
        raise ValueError("标题或时间窗不对")
    l6 = "4. 区号在（" + ",".join("+" + c for c in codes) + "）范围内的短信pass量 "
    nums = []
    for line, pre in zip(lines[2:6], (LINE3, LINE4, LINE5, l6)):
        if not line.startswith(pre) or not re.fullmatch(r"[0-9]+", line[len(pre):]):
            raise ValueError("数字行格式不对")
        nums.append(int(line[len(pre):]))
    if any(x in text for x in DENY) or len(text.encode("utf-8")) > 2048:
        raise ValueError("含不该发的字样或太长")
    a, b, c, dd = nums
    if not (a > 0 and a >= b >= c >= dd >= 0):
        raise ValueError("四个数的大小关系不对")
    return nums


def privacy_ok(path):
    scan = p("toolkit", "privacy_scan.py")
    r = subprocess.run([sys.executable, "-B", scan, path], capture_output=True, text=True)
    return r.returncode == 0 and "- unresolved: 0" in r.stdout


def check_post_file(st, d, run_id=None, started=None, accept_lag=False):
    """(ok, class, text, nums). The checks shared by the automatic post and the manual send-post. `started` = when the run
    began (epoch); the 10-minute lag check only means "data may be incomplete" for a run within 30 minutes of the cut-off.
    Later, a large lag_s just says nobody requested a code in the window's last minutes (quiet evenings); only a gap of
    more than an hour (LAG_STALL_S) still counts, as a sign that the log source stalled."""
    pp = post_path(d)
    if not os.path.exists(pp):
        return False, "verify_fail", None, None
    raw = open(pp, encoding="utf-8").read()
    try:
        codes = codes21()
        nums = parse_post(raw, d, codes)
    except (OSError, ValueError):
        return False, "verify_fail", None, None
    rows = [h for h in read_hist() if h.get("window_end_utc") == st["window_end_utc"]]
    if len(rows) != 1:
        return False, "verify_fail", None, None
    h = rows[0]
    if (run_id and h.get("run_id") != run_id) or h.get("kind") != "slot" or h.get("label") != st["label"]:
        return False, "verify_fail", None, None
    try:
        hn = [int(h[k]) for k in ("sms_total", "sms_pass", "pass_not_us_cn", "pass_21")]
    except (KeyError, ValueError):
        return False, "verify_fail", None, None
    if hn != nums:
        return False, "verify_fail", None, None
    try:
        lag = int(float(h.get("lag_s") or 0))
    except ValueError:
        lag = LAG_MAX_S + 1
    end = datetime.strptime(st["window_end_utc"], FMT).replace(tzinfo=UTC).timestamp()
    if not accept_lag and (lag > LAG_STALL_S or (lag > LAG_MAX_S and (started if started is not None else time.time()) - end < 1800)):
        return False, "lag", None, None
    extra = p("posts", f"巡检_{d:%Y%m%d}_2100_附加.txt")
    if os.path.exists(extra):
        for line in open(extra, encoding="utf-8"):
            if line.strip() and line.strip() in raw:
                return False, "verify_fail", None, None
    if not privacy_ok(pp):
        return False, "verify_fail", None, None
    return True, "ok", raw[:-1], nums


def verify_attempt(st, d, att, out, new_runs):
    """All checks on what this attempt produced; (ok, class, text, nums)."""
    if out.count("----- 复制下面这段发群 -----") != 1 or out.count("----- 到这里 -----") != 1:
        return False, "verify_fail", None, None
    block = out.split("----- 复制下面这段发群 -----\n", 1)[1].split("----- 到这里 -----", 1)[0]
    m = re.search(r" in (runs/\S+)/", out)
    rd = m.group(1).split("/", 1)[1] if m else None
    if not rd or rd not in new_runs:
        return False, "verify_fail", None, None
    try:
        man = json.load(open(p("runs", rd, "manifest.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return False, "verify_fail", None, None
    w = (man.get("windows") or [{}])
    if (man.get("tool") != "patrol24" or man.get("kind") != "slot" or len(w) != 1 or w[0].get("key") != f"{d.isoformat()} 21:00"
            or w[0].get("start") != st["window_start_utc"] or w[0].get("end") != st["window_end_utc"]
            or man.get("codes") != codes21()):
        return False, "verify_fail", None, None
    pp = post_path(d)
    if not os.path.exists(pp) or os.path.getmtime(pp) < att["t0"] - 1 or open(pp, encoding="utf-8").read() != block:
        return False, "verify_fail", None, None
    att["run_id"] = man.get("run_id")
    return check_post_file(st, d, man.get("run_id"), att["fired"])


# ----------------------------------------------------------------------------- sending
class SendError(Exception):
    def __init__(self, phase):
        super().__init__(phase)
        self.phase = phase              # "before" (nothing reached Feishu) or "after" (it may have)


def feishu_connect(host=HOST):
    """An open TLS connection to the Feishu host (certificate checks on), through _local_only/autopost/feishu_proxy if set."""
    ctx = ssl.create_default_context()
    proxy = feishu_proxy()
    if proxy:
        pu = urlparse(proxy if "://" in proxy else "http://" + proxy)
        conn = http.client.HTTPSConnection(pu.hostname, pu.port or 8080, timeout=15, context=ctx)
        hdr = {}
        if pu.username:
            hdr["Proxy-Authorization"] = "Basic " + base64.b64encode(f"{pu.username}:{pu.password or ''}".encode()).decode()
        conn.set_tunnel(host, 443, headers=hdr)
    else:
        conn = http.client.HTTPSConnection(host, 443, timeout=15, context=ctx)
    conn.connect()
    return conn


def real_transport(url, body):
    """(status, text, date header). Certificate checks on, no redirects."""
    u = urlparse(url)
    try:
        conn = feishu_connect(u.hostname)
    except Exception:
        raise SendError("before") from None
    try:
        conn.request("POST", u.path, body=body, headers={"Content-Type": "application/json; charset=utf-8",
                                                          "User-Agent": "rc-autopost/1"})
        r = conn.getresponse()
        text = r.read(65536).decode("utf-8", "replace")
        return r.status, text, r.getheader("Date") or ""
    except Exception:
        raise SendError("after") from None
    finally:
        conn.close()


def classify_response(status, text):
    """ok / retry (provably not delivered: rate limit 11232) / rejected (a configuration error) / uncertain (anything else,
    including every 5xx: it may have reached the group, so it is never resent automatically)."""
    try:
        j = json.loads(text)
    except ValueError:
        return ("uncertain", None) if status == 200 or status >= 500 else ("rejected", None)
    code = j.get("code") if isinstance(j, dict) and "code" in j else (j.get("StatusCode") if isinstance(j, dict) else None)
    if code == 0:
        return "ok", 0
    if code == 11232:
        return "retry", code
    if status >= 500:
        return "uncertain", code
    return "rejected", code


def sent_today(target, now):
    day, n = now.astimezone(NY).date().isoformat(), 0
    for f in glob.glob(os.path.join(STATE_DIR, "*.json")):
        try:
            st = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        n += sum(1 for s in st.get("sends", []) if s.get("target") == target and s.get("auto")
                 and s.get("claimed_ny", "")[:10] == day and s.get("result") in (None, "ok", "uncertain", "rejected"))
    return n


def deliver(entry, text, now, transport):
    """(result, http status, feishu code). result: ok / retry / rejected / uncertain."""
    body = {"msg_type": "text", "content": {"text": text}}
    if entry.get("sig_key"):
        ts = str(int(now.timestamp()))
        body.update(timestamp=ts, sign=sign(ts, entry["sig_key"]))
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    bits = secret_bits({"x": entry})
    try:
        status, text_, _ = (transport or real_transport)(entry["url"], data)
    except SendError as ex:
        return ("retry" if ex.phase == "before" else "uncertain"), None, None
    except Exception:
        return "uncertain", None, None
    res, code = classify_response(status, text_)
    try:
        atomic_write(os.path.join(LOCAL, "last_response.txt"), redact(f"{status} {text_[:300]}", bits) + "\n", 0o600)
    except OSError:
        pass
    return res, status, code


def send(kind, st, now, transport, auto=True):
    """kind post / failline. Writes the in-flight state first; an unknown outcome is never resent."""
    target = st["target"]
    entry = load_conf().get(target) if target else None
    d = date.fromisoformat(st["window_date"])
    if not entry or not entry.get("url"):
        log(now, st["window_date"], "no_webhook", target=target or "", note="这个目标没有录 webhook")
        return "no_webhook"
    if auto and sent_today(target, now) >= DAILY_CAP:
        log(now, st["window_date"], "cap", target=target, note="今天自动发送已到上限")
        return "cap"
    if kind == "post":
        text = st["verify"]["text"]
    else:
        text = header(d) + "\n" + FAILLINE
    st["status"] = "posting" if kind == "post" else "failline_posting"
    rec = {"kind": kind, "target": target, "fp": fp(entry), "claimed_ny": nyfmt(now), "auto": auto}
    st["sends"].append(rec)
    save_state(st)
    res, status, code = deliver(entry, text, now, transport)
    rec.update(result=res, http=status, code=code, done_ny=nyfmt(now))
    nxt = {("post", "ok"): "posted" if auto else "reposted", ("failline", "ok"): "failline_posted",
           ("post", "retry"): "send_retry" if auto else "manual_send_retry", ("failline", "retry"): "failline_retry"}
    st["status"] = nxt.get((kind, res), "send_rejected" if res == "rejected" else "send_uncertain")
    save_state(st)
    note = FEISHU_CODES.get(code, f"飞书返回 {code}") if res == "rejected" else {"ok": "已发", "retry": "没发出去，下次再试",
                                                                            "uncertain": "结果不确定，不重发"}[res]
    log(now, st["window_date"], f"{kind}_{res}", target=target, result=str(status or ""), note=note)
    print(f"{st['window_date']} 21:00 → {kind} {res}（{target}，{note}）")
    return res


# ----------------------------------------------------------------------------- one cron firing
def heartbeat(now, what):
    try:
        atomic_write(os.path.join(LOCAL, "heartbeat.json"), json.dumps({"ny": nyfmt(now), "what": what}, ensure_ascii=False) + "\n", 0o600)
    except OSError:
        pass


def own_from(out, new_runs):
    """The run dirs this child made: the ones it printed, plus a shard-discovery run."""
    named = {m.split("/", 1)[1] for m in re.findall(r"(runs/[^\s/]+)/", out or "")}
    return sorted(r for r in new_runs if r in named or r.endswith("_discover"))


def recover_interrupted(st, d, now):
    """A firing that died while its child ran (we hold the lock now, so that firing is gone). Returns 'child_running' if the
    child itself still runs; otherwise adopts the run dirs it made for this window and counts the attempt as interrupted."""
    att = next((a for a in reversed(st["attempts"]) if "t1" not in a), None)
    if att is None:
        st["status"] = "retry_wait"
        return "retry_wait"
    if att.get("child_pid") and pid_alive(att["child_pid"]):
        return "child_running"
    new = sorted(set(list_runs()) - set(att.get("runs_before") or []))
    outf = (att.get("out_base") or "") + ".out"
    printed = open(outf, encoding="utf-8", errors="replace").read() if att.get("out_base") and os.path.exists(outf) else ""
    adopted = own_from(printed, new)       # only what the dead child printed; anything else counts as a hand run (safe side)
    ids = {r.rsplit("_", 1)[0] for r in adopted}
    t1 = att.get("t0", time.time())
    for r in adopted:
        for f in glob.glob(p("runs", r, "*")):
            t1 = max(t1, os.path.getmtime(f))
    if any(h.get("window_end_utc") == st["window_end_utc"] and h.get("run_id") in ids for h in read_hist()):
        for f in (post_path(d), p("history", "patrol24_history.csv")):
            if os.path.exists(f):
                t1 = max(t1, os.path.getmtime(f))
    st["own_runs"] = sorted(set(st.get("own_runs") or []) | set(adopted))
    att.update(t1=t1, exit=None, cls="interrupted", counted=True, runs=adopted)
    st["status"] = "retry_wait"
    save_state(st)
    log(now, st["window_date"], "interrupted", att["n"], "", "interrupted", st.get("target") or "", "retry",
        "上一次尝试中途停了（进程没了），按一次失败算，接着重试")
    return "retry_wait"


def attempt(st, cfg, d, now, runner):
    n = len(st["attempts"]) + 1
    before = set(list_runs())
    att = {"n": n, "start_ny": nyfmt(now), "fired": now.timestamp(), "t0": time.time(), "runs_before": sorted(before),
           "out_base": os.path.join(LOCAL, "child", f"{d.isoformat()}_try{n}")}
    if not os.path.exists(PATROL):
        att.update(t1=time.time(), exit=None, cls="toolkit_missing", counted=False)
        st["attempts"].append(att)
        st["status"] = "retry_wait"
        save_state(st)
        log(now, st["window_date"], "attempt", n, "", "toolkit_missing", st["target"], "", NOTES["toolkit_missing"])
        return "retry"
    st["status"] = "running"
    att["parent_pid"] = os.getpid()
    st["attempts"].append(att)
    save_state(st)

    def started(pid):
        att["child_pid"] = pid
        save_state(st)
    if runner is None:
        rc, out, err, to = real_runner(child_argv(cfg, d), RUN_FOLDER, child_env(cfg), CHILD_TIMEOUT_S, started, att["out_base"])
    else:
        rc, out, err, to = runner(child_argv(cfg, d), RUN_FOLDER, child_env(cfg), CHILD_TIMEOUT_S)
    att["t1"] = time.time()
    new_runs = own_from(out, sorted(set(list_runs()) - before))
    st["own_runs"] = sorted(set(st.get("own_runs") or []) | set(new_runs))
    save_state(st)
    cls, kind, cnt = classify(rc, out, err, to)
    att.update(exit=rc, cls=cls, counted=cnt, runs=new_runs)
    try:
        lp = os.path.join(LOCAL, "child", f"{d.isoformat()}_try{n}.txt")
        atomic_write(lp, f"argv: {' '.join(child_argv(cfg, d))}\nexit: {rc} timeout: {to}\n--- stdout\n{out}\n--- stderr\n{err}\n", 0o600)
    except OSError:
        pass
    if kind == "ok":
        ok, vcls, text, nums = verify_attempt(st, d, att, out, new_runs)
        if ok:
            st["verify"] = {"text": text, "nums": nums, "sha256": hashlib.sha256((text + "\n").encode()).hexdigest(),
                            "run_id": att.get("run_id") or "", "fired": att["fired"]}
            st["status"] = "verified"
            att["cls"] = "ok"
        else:
            att["cls"], kind = vcls, ("retry" if vcls == "lag" else "terminal")
    if kind == "retry":
        if att["cls"] == "busy":
            st["busy"] = st.get("busy", 0) + 1
            if st["busy"] >= MAX_BUSY:
                att["cls"], kind = "busy_exhausted", "terminal"
    if kind == "retry":
        st["status"] = "retry_wait"
    elif kind == "terminal":
        st["status"] = "failline_due"
    save_state(st)
    log(now, st["window_date"], "attempt", n, rc, att["cls"], st["target"], kind, NOTES.get(att["cls"], ""))
    print(f"{st['window_date']} 21:00 → 第 {n} 次：退出码 {rc}，{NOTES.get(att['cls'], att['cls'])}")
    return kind


def resend_ok(st, d):
    """A stored post may be re-sent only if the file and the history row still say exactly the same."""
    v = st.get("verify") or {}
    ok, cls, text, nums = check_post_file(st, d, v.get("run_id"), v.get("fired"))
    return ok and text == v.get("text") and nums == v.get("nums")


def skip_manual(st, now):
    st["status"] = "manual_skip"
    save_state(st)
    log(now, st["window_date"], "manual_skip", target=st.get("target") or "", note="这一段已经有人手动跑过，自动发送不发")
    print(f"{st['window_date']} 21:00 → 已有人手动跑过，不发")
    return "manual_skip"


def cron_once(now=None, runner=None, transport=None):
    now = now or datetime.now(UTC)
    ensure_dirs()
    cfg = load_cfg()
    if cfg is None:
        heartbeat(now, "not_initialized")
        return "not_initialized"
    if cfg.get("host_pin") != host_pin():
        heartbeat(now, "other_host")
        log(now, "", "other_host", note="这台机器不是安装时那台：不动（换了机器用 adopt-host）")
        return "other_host"
    d = window_date(now)
    if d is None:
        heartbeat(now, "idle")
        return "idle"
    if not cfg.get("enabled") or d < date.fromisoformat(cfg["start_date"]) or d.isoformat() in cfg.get("skip_dates", []):
        heartbeat(now, "gated")
        return "gated"
    st = load_state(d)
    heartbeat(now, f"{d.isoformat()} {st['status']}")
    if st["status"] in FINAL:
        return st["status"]
    first, last, nodb, catch = at(d, FIRST), at(d, LAST), at(d, NODB), at(d, CATCH, 1)
    if now < first:
        return "early"
    if st["status"] in ("posting", "failline_posting"):          # a crash or kill in the middle of a send
        st["status"] = "send_uncertain"
        save_state(st)
        log(now, st["window_date"], "send_uncertain", target=st.get("target") or "", note="上次发送中断，结果不确定，不重发")
        return "send_uncertain"
    if st["status"] == "running":                                  # a previous firing died during the child
        if recover_interrupted(st, d, now) == "child_running":
            log(now, st["window_date"], "child_running", target=st.get("target") or "", note="上一次的子进程还在跑，这次不动")
            return "child_running"
    if now >= catch:
        st["status"] = "gave_up"
        save_state(st)
        log(now, st["window_date"], "gave_up", target=st.get("target") or "", note="到 00:40 也没发出去")
        return "gave_up"
    if not st.get("target"):
        st["target"] = cfg.get("mode", "test")
        st["target_fp"] = fp(load_conf().get(st["target"]))
        save_state(st)
    if now < nodb:
        if st["status"] in ("verified", "send_retry", "pending", "retry_wait") and manual_run(st, d):
            return skip_manual(st, now)
        if st["status"] in ("verified", "send_retry"):
            if resend_ok(st, d):
                if send("post", st, now, transport) == "ok":
                    return "posted"
            else:
                st["status"] = "failline_due"
                save_state(st)
                log(now, st["window_date"], "verify_fail", target=st["target"], note="发前复核：文件或历史变了")
        elif st["status"] in ("pending", "retry_wait"):
            starts = [a for a in st["attempts"] if a.get("fired")]
            due = counted(st) < MAX_ATTEMPTS and (not starts or now.timestamp() - starts[-1]["fired"] >= MIN_GAP_S - 60)
            if due:
                kind = attempt(st, cfg, d, now, runner)
                if kind == "ok":
                    if manual_run(st, d):                          # someone ran this window by hand meanwhile
                        return skip_manual(st, now)
                    if send("post", st, now, transport) == "ok":
                        return "posted"
        if st["status"] in ("retry_wait", "send_retry") and (now >= last or counted(st) >= MAX_ATTEMPTS):
            st["status"] = "failline_due"
            save_state(st)
        if st["status"] in ("failline_due", "failline_retry"):
            if manual_run(st, d):
                return skip_manual(st, now)
            send("failline", st, now, transport)
        return st["status"]
    # 23:40-00:39: no database; a late failure line only
    if st["status"] not in FINAL:
        if manual_run(st, d):
            return skip_manual(st, now)
        st["status"] = "failline_due" if st["status"] != "failline_retry" else st["status"]
        save_state(st)
        send("failline", st, now, transport)
    return st["status"]


def trim_cron_log():
    f = os.path.join(LOCAL, "cron.log")
    try:
        if os.path.getsize(f) > 1_000_000:
            data = open(f, "rb").read()[-200_000:]
            open(f, "wb").write(data)
    except OSError:
        pass


def cmd_cron(a, now=None, runner=None, transport=None):
    ensure_dirs()
    trim_cron_log()
    lk = open(os.path.join(LOCAL, ".autopost.lock"), "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log(now or datetime.now(UTC), "", "overlap", note="上一次还没跑完，这次不动")
        return "overlap"
    try:
        return cron_once(now, runner, transport)
    except SystemExit:
        raise
    except Exception:
        now = now or datetime.now(UTC)
        try:
            bits = secret_bits()
        except SystemExit:
            bits = set()
        atomic_write(os.path.join(LOCAL, "last_error.txt"), nyfmt(now) + "\n" + redact(traceback.format_exc(), bits), 0o600)
        log(now, "", "crash", note="自动发送程序出错，详情在 _local_only/autopost/last_error.txt")
        return "crash"
    finally:
        fcntl.flock(lk, fcntl.LOCK_UN)
        lk.close()


# ----------------------------------------------------------------------------- user commands
def tty_or_refuse():
    if not sys.stdin.isatty():
        raise Refuse("这个命令要在你自己的终端里跑（需要交互输入）；不要在 Claude 会话里跑。")


def cmd_set_webhook(a):
    tty_or_refuse()
    url = getpass.getpass(f"{a.target} 群机器人的 webhook 地址（输入不显示）：").strip()
    if not URL_RE.match(url):
        raise Refuse("格式不对：应该是 https://open.feishu.cn/open-apis/bot/v2/hook/ 后面跟一串 36 位的标识（小写）。没有保存。")
    conf = load_conf()
    other = conf.get("team" if a.target == "test" else "test") or {}
    if other.get("url") == url:
        raise Refuse("测试群和正式群用了同一个 webhook：没有保存。")
    entry = {"url": url}
    if a.secret:
        k = getpass.getpass("签名校验的密钥（输入不显示）：").strip()
        if not k:
            raise Refuse("密钥是空的：没有保存。")
        entry["sig_key"] = k
    conf[a.target] = entry
    save_conf(conf)
    print(f"{a.target}：已保存（指纹 {fp(entry)}，签名：{'有' if a.secret else '无'}）")


def cmd_forget_webhook(a):
    conf = load_conf()
    conf.pop(a.target, None)
    save_conf(conf)
    print(f"{a.target}：已删除")


def cmd_set_mode(a, now=None):
    now = now or datetime.now(UTC)
    cfg = need_cfg()
    t = now.astimezone(NY)
    if not a.force and ((t.hour, t.minute) >= ACTIVE_FROM or (t.hour, t.minute) < CATCH):
        raise Refuse("21:30 到次日 00:40 之间不切换（这一段正在进行）；白天再切，或加 --force。")
    if a.mode == "team":
        conf = load_conf()
        if not (conf.get("team") or {}).get("url"):
            raise Refuse("还没录正式群的 webhook：先 `set-webhook --target team`。")
        good = 0
        for f in glob.glob(os.path.join(STATE_DIR, "*.json")):
            try:
                st = json.load(open(f, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            good += st.get("status") == "posted" and st.get("target") == "test"
        if good < 2 and not a.force:
            raise Refuse(f"测试群只成功发过 {good} 晚（要 2 晚）：再等一两晚，或加 --force。")
    cfg["mode"] = a.mode
    change(cfg, now, f"set-mode {a.mode}")
    d = window_date(now) or now.astimezone(NY).date()
    print(f"模式：{a.mode}；从纽约 {d:%m/%d} 21:00 那一段起生效（已经开始的那一段不变）。")


def cmd_toggle(a, now=None):
    now = now or datetime.now(UTC)
    cfg = need_cfg()
    if a.cmd in ("enable", "disable"):
        cfg["enabled"] = a.cmd == "enable"
    elif a.cmd == "skip":
        cfg["skip_dates"] = sorted(set(cfg.get("skip_dates", [])) | {date.fromisoformat(a.date).isoformat()})
    elif a.cmd == "unskip":
        cfg["skip_dates"] = [x for x in cfg.get("skip_dates", []) if x != date.fromisoformat(a.date).isoformat()]
    elif a.cmd == "set-start":
        cfg["start_date"] = date.fromisoformat(a.date).isoformat()
    elif a.cmd == "adopt-host":
        cfg["host_pin"] = host_pin()
    change(cfg, now, a.cmd + (f" {a.date}" if getattr(a, "date", None) else ""))
    print(f"{a.cmd}：好了。")


def cmd_init(a, now=None):
    now = now or datetime.now(UTC)
    ensure_dirs()
    if load_cfg() and not a.reinit:
        raise Refuse("config/autopost.json 已经有了：要重来加 --reinit（webhook 不受影响）。")
    path = a.child_path or "/usr/local/bin:/usr/bin:/bin"
    if not a.no_cli:                          # resolve_gateway's last fallback runs `claude mcp get`, a node program
        for tool in ("node", "claude"):
            w = shutil.which(tool)
            if w and os.path.dirname(w) not in path.split(":"):
                path = os.path.dirname(w) + ":" + path
    cfg = {"schema": 1, "enabled": True, "mode": "test", "start_date": date.fromisoformat(a.start_date).isoformat(),
           "skip_dates": [], "host_pin": host_pin(), "python": a.python or sys.executable, "child_path": path,
           "home": os.path.expanduser("~"), "lang": a.lang, "no_cli": bool(a.no_cli), "changes": []}
    save_cfg(cfg)
    change(cfg, now, "init")
    print(f"config/autopost.json 写好：模式 test，从纽约 {cfg['start_date']} 起，no_cli={cfg['no_cli']}。")


def cmd_status(a, now=None):
    now = now or datetime.now(UTC)
    cfg = load_cfg()
    if not cfg:
        print("还没初始化（config/autopost.json 不存在）。")
        return 0
    print(f"自动发群：{'开' if cfg.get('enabled') else '关'}（模式 {cfg.get('mode')}，起始 {cfg.get('start_date')}，"
          f"跳过：{'、'.join(cfg.get('skip_dates', [])) or '无'}）")
    try:
        conf = load_conf()
        perm = "正常" if not os.path.exists(SECRETS) or not (os.stat(SECRETS).st_mode & 0o077) else "不对"
    except SystemExit:
        conf, perm = {}, "不对（先 chmod 600）"
    for t in ("test", "team"):
        e = conf.get(t)
        print(f"webhook {t}：" + (f"已设（指纹 {fp(e)}，签名 {'有' if e.get('sig_key') else '无'}）" if e and e.get("url") else "未设"))
    print(f"feishu.conf 权限：{perm}；本机：{'一致' if cfg.get('host_pin') == host_pin() else '不一致（换过机器？用 adopt-host）'}")
    try:
        hb = json.load(open(os.path.join(LOCAL, "heartbeat.json"), encoding="utf-8"))
        age = (now - datetime.fromisoformat(hb["ny"]).replace(tzinfo=NY)).total_seconds() / 60
        print(f"心跳：{hb['ny']}（{age:.0f} 分钟前，{hb.get('what', '')}）" + ("  ← 超过 40 分钟，cron 可能没在跑" if age > 40 else ""))
    except (OSError, ValueError, KeyError):
        print("心跳：还没有（cron 还没跑过）")
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        n = sum(1 for l in r.stdout.splitlines() if l.rstrip().endswith(TAG))
        print(f"cron：{'已装' if n == 1 else '没装' if n == 0 else f'有 {n} 行（应为 1）'}")
    except OSError:
        print("cron：这台机器没有 crontab 命令")
    print("最近的窗口：")
    for f in sorted(glob.glob(os.path.join(STATE_DIR, "*.json")))[-7:]:
        try:
            st = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        last = st["sends"][-1] if st.get("sends") else {}
        print(f"  {st['window_date']} 21:00 → {st['status']}（{st.get('target') or '-'}，尝试 {len(st['attempts'])} 次"
              + (f"，最后发送 {last.get('done_ny', last.get('claimed_ny', ''))[11:16]} {last.get('result', '')}" if last else "") + "）")
    return 0


def send_post_refusal(st, d, now, cfg, resend_uncertain):
    if st["status"] in ("posted", "reposted"):
        return f"{d} 21:00 那一段已经发过（{st['status']}），不重发。"
    last = st["sends"][-1] if st.get("sends") else None
    if (st["status"] == "send_uncertain" or (last and last.get("result") in (None, "uncertain"))) and not resend_uncertain:
        return "上次发送结果不确定：先看群里有没有；确实没有再加 --resend-uncertain。"
    if st["status"] in ("posting", "failline_posting", "running"):
        return "自动发送正在处理这一段，等它结束再说。"
    active = (cfg.get("enabled") and d >= date.fromisoformat(cfg["start_date"]) and d.isoformat() not in cfg.get("skip_dates", [])
              and at(d, ACTIVE_FROM) <= now < at(d, CATCH, 1) and st["status"] not in FINAL)
    if active:
        return "这一段自动发送还在进行（21:30 到次日 00:40）：等它结束，或先 `skip --date` 这一天。"
    return None


def _locked():
    ensure_dirs()
    lk = open(os.path.join(LOCAL, ".autopost.lock"), "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lk.close()
        raise Refuse("自动发送正在跑（锁被占着）：过几分钟再来。")
    return lk


def _unlock(lk):
    fcntl.flock(lk, fcntl.LOCK_UN)
    lk.close()


def _send_post_checks(d, now, cfg, a):
    """Under the lock: recover a state no firing will touch again, then every check. Returns (state, text, nums)."""
    st = load_state(d)
    if st["status"] in ("posting", "failline_posting"):
        st["status"] = "send_uncertain"
        save_state(st)
    if st["status"] == "running" and not (at(d, ACTIVE_FROM) <= now < at(d, CATCH, 1)):
        if recover_interrupted(st, d, now) == "child_running":
            raise Refuse("上一次的巡检子进程还在跑：等它结束再说。")
    why = send_post_refusal(st, d, now, cfg, a.resend_uncertain)
    if why:
        raise Refuse(why)
    ok, cls, text, nums = check_post_file(st, d, None, now.timestamp(), getattr(a, "accept_lag", False))
    if not ok:
        hint = ("；最后一小时完全没有请求时，确认过数据没问题再加 --accept-lag" if cls == "lag" else "")
        raise Refuse(f"posts/巡检_{d:%Y%m%d}_2100.txt 没过核对（{NOTES.get(cls, cls)}）：先在 22:00–05:15 跑 "
                     f"`patrol24.py run --date {d} --per-code`，看到「可以发。」再来{hint}。", 4)
    return st, text, nums


def cmd_send_post(a, now=None, transport=None):
    fixed = now is not None                                        # tests pass a clock; real use reads it again after the prompt
    now = now or datetime.now(UTC)
    cfg = need_cfg()
    d = date.fromisoformat(a.date)
    lk = _locked()
    try:
        st, text, nums = _send_post_checks(d, now, cfg, a)
    finally:
        _unlock(lk)
    tty_or_refuse()                                                # the prompt runs without the lock: cron is never blocked
    print(text)
    if input(f"\n发到 {st.get('target') or cfg.get('mode', 'test')} 群？输入 发送 确认：").strip() != "发送":
        raise Refuse("没发。")
    now = now if fixed else datetime.now(UTC)
    lk = _locked()
    try:
        st, text2, nums2 = _send_post_checks(d, now, cfg, a)      # state and file as they are now
        if text2 != text:
            raise Refuse("确认的时候帖子文件变了：没发，重新跑一次 send-post。")
        st["target"] = st.get("target") or cfg.get("mode", "test")
        st["verify"] = {"text": text, "nums": nums, "sha256": hashlib.sha256((text + "\n").encode()).hexdigest(), "run_id": ""}
        res = send("post", st, now, transport, auto=False)
        return 0 if res == "ok" else 5
    finally:
        _unlock(lk)


def cmd_test_send(a, now=None, transport=None):
    now = now or datetime.now(UTC)
    if a.target != "test":
        raise Refuse("测试消息只发到测试群。")
    entry = load_conf().get("test")
    if not entry:
        raise Refuse("还没录测试群的 webhook：先在自己的终端跑 `set-webhook --target test`。")
    res, status, code = deliver(entry, TESTLINE, now, transport)
    note = "已发" if res == "ok" else FEISHU_CODES.get(code, f"飞书返回 {code}") if res == "rejected" else res
    log(now, "", "test_send", target="test", result=str(status or ""), note=note)
    print(f"测试消息：{res}（{note}）")
    return 0 if res == "ok" else 5


def cmd_dry_run(a, now=None):
    now = datetime.fromisoformat(a.at).replace(tzinfo=NY).astimezone(UTC) if a.at else (now or datetime.now(UTC))
    cfg = need_cfg()
    d = window_date(now)
    print(f"假设现在是纽约 {nyfmt(now)}：")
    if d is None:
        print("  白天：什么都不做（只写心跳）。")
        return 0
    st = load_state(d)
    gated = (not cfg.get("enabled") or d < date.fromisoformat(cfg["start_date"]) or d.isoformat() in cfg.get("skip_dates", []))
    print(f"  窗口：{st['label']}（纽约 {d} 21:00）；状态 {st['status']}；{'被关掉/跳过/未到起始日' if gated else '会处理'}")
    print(f"  子进程：{' '.join(child_argv(cfg, d))}（工作目录 {RUN_FOLDER}）")
    tgt = st.get("target") or cfg.get("mode")
    try:
        e = load_conf().get(tgt)
    except SystemExit:
        e = None
    print(f"  发到：{tgt}（{'指纹 ' + fp(e) if e else '没录 webhook'}）")
    return 0


def cmd_net_check(a):
    t0 = time.time()
    try:
        conn = feishu_connect()
        ver = conn.sock.version() if conn.sock else "?"
        conn.close()
        print(f"TLS 握手：成功（{ver}，{(time.time() - t0) * 1000:.0f} ms{'，经代理' if feishu_proxy() else ''}）；没有发任何消息。")
    except ssl.SSLCertVerificationError:
        print("TLS 握手：证书校验失败（本机缺 CA 证书？）。不会关掉校验；装证书要你决定。")
        return 5
    except OSError as ex:
        print(f"TLS 握手：连不上（{ex.__class__.__name__}）。可能需要代理：在 _local_only/autopost/feishu_proxy 写一行 "
              "https_proxy=…（只用于飞书，不给查库的子进程）。")
        return 5
    return 0


def crontab_read(run=subprocess.run):
    r = run(["crontab", "-l"], capture_output=True, text=True)
    if r.returncode != 0:
        if "no crontab" in (r.stderr or "").lower():
            return ""
        raise Refuse("读 crontab 出错，没改：" + (r.stderr or "").strip()[:200])
    return r.stdout


def cron_line(cfg):
    py = cfg.get("python") or sys.executable
    me = os.path.abspath(__file__)
    return (f"5,35 * * * * cd {RUN_FOLDER} && {py} -B {me} cron >> {os.path.join(LOCAL, 'cron.log')} 2>&1 {TAG}")


def cmd_cron_line(a):
    print(cron_line(need_cfg()))


def cmd_install_cron(a, run=subprocess.run, now=None):
    now = now or datetime.now(UTC)
    cfg = need_cfg()
    line = cron_line(cfg)
    if "%" in line:
        raise Refuse("cron 行里不能有 %：路径里有 % 的话换个目录。")
    old = crontab_read(run)
    stamp = now.astimezone(NY).strftime("%Y%m%d-%H%M%S")
    atomic_write(os.path.join(LOCAL, f"crontab_backup_{stamp}.txt"), old, 0o600)
    keep = [l for l in old.splitlines() if not l.rstrip().endswith(TAG)]
    new = "\n".join(keep + ([] if a.cmd == "uninstall-cron" else [line])) + "\n"
    if new.strip() == "":
        r = run(["crontab", "-r"], capture_output=True, text=True)
    else:
        r = run(["crontab", "-"], input=new, capture_output=True, text=True)
    if r.returncode != 0:
        raise Refuse("写 crontab 出错（原来的备份在 _local_only/autopost/）：" + (r.stderr or "").strip()[:200])
    back = crontab_read(run)
    tagged = [l for l in back.splitlines() if l.rstrip().endswith(TAG)]
    others = [l for l in back.splitlines() if not l.rstrip().endswith(TAG)]
    if others != keep or len(tagged) != (0 if a.cmd == "uninstall-cron" else 1):
        raise Refuse("写完读回来不对（备份在 _local_only/autopost/）：请手动 `crontab -e` 看一下。", 4)
    change(cfg, now, a.cmd)
    print(("已删除" if a.cmd == "uninstall-cron" else "已装好") + f"（其他 {len(keep)} 行没动；备份 crontab_backup_{stamp}.txt）")
    return 0


def cmd_leakcheck(a, run=subprocess.run):
    bits = secret_bits()
    if not bits:
        print("没录 webhook，没什么可查。")
        return 0
    hits = []
    for root, dirs, files in os.walk(PKG):
        for f in files:
            fpath = os.path.join(root, f)
            if os.path.abspath(fpath) == os.path.abspath(SECRETS) or os.path.getsize(fpath) > 20_000_000:
                continue
            try:
                data = open(fpath, "rb").read().decode("utf-8", "replace")
            except OSError:
                continue
            if any(b in data for b in bits):
                hits.append(os.path.relpath(fpath, PKG))
    try:
        if any(b in crontab_read(run) for b in bits):
            hits.append("(crontab)")
    except SystemExit:
        pass
    print(f"leakcheck：{len(hits)} 处" + ("：" + "、".join(hits) if hits else "（只在 _local_only/feishu.conf 里）"))
    return 4 if hits else 0


def cmd_verify(a=None):
    f = os.path.join(HERE, "SHA256SUMS")
    if not os.path.exists(f):
        raise Refuse("autopost/SHA256SUMS 不在", 4)
    bad, n = [], 0
    for line in open(f, encoding="utf-8"):
        if not line.strip():
            continue
        want, name = line.split(None, 1)
        name = name.strip()
        fn = os.path.join(HERE, name)
        got = hashlib.sha256(open(fn, "rb").read()).hexdigest() if os.path.exists(fn) else "missing"
        n += 1
        if got != want:
            bad.append(name)
    print(f"autopost sha256: {n - len(bad)}/{n} match" + (f"; differ: {', '.join(bad)}" if bad else ""))
    if bad:
        raise SystemExit(4)
    return 0


# ----------------------------------------------------------------------------- rehearsal (offline)
def find_saved(key):
    for mf in sorted(glob.glob(p("runs", "*", "manifest.json")), reverse=True):
        try:
            man = json.load(open(mf, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if man.get("tool", "patrol24") != "patrol24" or not man.get("groups"):
            continue
        rd = os.path.dirname(mf)
        for w in man.get("windows", []):
            names = [f"{w['id']}_s{gi}" for gi in range(1, len(man["groups"]) + 1)] + ["s0a_processlist", "s0b_threads",
                                                                                      "s0c_shards", "s0d_explain"]
            if w.get("key") == key and all(os.path.exists(os.path.join(rd, n + ".json")) for n in names):
                return rd, w["id"], len(man["groups"])
    return None


def newest_saved():
    best = None
    for mf in glob.glob(p("runs", "*", "manifest.json")):
        try:
            man = json.load(open(mf, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for w in man.get("windows", []):
            k = w.get("key", "")
            if k.endswith(" 21:00") and find_saved(k) and (best is None or k > best):
                best = k
    return best[:10] if best else None


def cmd_rehearse(a):
    d = a.date or newest_saved()
    if not d:
        raise Refuse("没找到保存了某个 21:00 窗口全部回复的运行目录，离线演练没法做。", 4)
    src = find_saved(f"{d} 21:00")
    if not src:
        raise Refuse(f"没找到保存了 {d} 21:00 那一段全部回复的运行目录。", 4)
    tmp = tempfile.mkdtemp(prefix="autopost_rehearse_")
    try:
        rp = os.path.join(tmp, "RC_patrol")
        shutil.copytree(p("toolkit"), os.path.join(rp, "toolkit"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(HERE, os.path.join(rp, "autopost"), ignore=shutil.ignore_patterns("__pycache__"))
        for sub in ("config", "history"):
            if os.path.isdir(p(sub)):
                shutil.copytree(p(sub), os.path.join(rp, sub), ignore=shutil.ignore_patterns("autopost*"))
        os.makedirs(os.path.join(rp, "_local_only"))
        rw = p("_local_only", "reserved_words.txt")
        if os.path.exists(rw):
            shutil.copy2(rw, os.path.join(rp, "_local_only"))
        env = {k: v for k, v in os.environ.items() if k != "MCP_DB_GATEWAY_SSE"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["AUTOPOST_REHEARSAL"] = rp
        r = subprocess.run([sys.executable, "-B", os.path.join(rp, "autopost", "autopost.py"), "_rehearse_inner", d, src[0],
                            src[1], str(src[2])], env=env, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            print(r.stderr.strip()[-1500:])
            raise Refuse("离线演练没过（见上面）。", 4)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("rehearse: OK (offline; RC_patrol unchanged)")
    return 0


def cmd_rehearse_inner(a):
    """Runs inside the temp copy: real patrol24 offline on saved replies, a recording transport, fixed clocks."""
    if (os.environ.get("AUTOPOST_REHEARSAL") != PKG or not os.path.basename(os.path.dirname(PKG)).startswith("autopost_rehearse_")
            or not os.path.realpath(PKG).startswith(os.path.realpath(tempfile.gettempdir()))):
        raise Refuse("_rehearse_inner 只在 rehearse 建的临时目录里用。")
    d = date.fromisoformat(a.d)
    srd, wid, ng = a.src, a.wid, int(a.ng)
    ensure_dirs()
    fake_url = "https://" + HOST + "/open-apis/bot/v2/hook/" + "-".join(["0" * 8, "0" * 4, "4" * 4, "8" * 4, "0" * 12])
    save_conf({"test": {"url": fake_url}})
    cfg = {"schema": 1, "enabled": True, "mode": "test", "start_date": d.isoformat(), "skip_dates": [], "host_pin": host_pin(),
           "python": sys.executable, "child_path": os.environ.get("PATH", "/usr/bin:/bin"), "home": os.path.expanduser("~"),
           "lang": "C.UTF-8", "no_cli": True, "changes": []}
    save_cfg(cfg)
    sent = []

    def transport(url, body):
        sent.append(json.loads(body.decode("utf-8")))
        return 200, '{"code":0,"msg":"success","data":{}}', ""

    def replay(argv, cwd, env, timeout):
        assert argv[3:7] == ["run", "--date", d.isoformat(), "--per-code"] and not any(x in argv for x in FORBIDDEN_ARGS)
        py = [sys.executable, "-B", PATROL]
        e = dict(env, PATH=os.environ.get("PATH", "/usr/bin:/bin"))
        r1 = subprocess.run(py + ["emit", "--date", d.isoformat()], cwd=cwd, env=e, capture_output=True, text=True)
        m = re.search(r" in (runs/\S+)/", r1.stdout)
        if r1.returncode or not m:
            return r1.returncode or 1, r1.stdout, r1.stderr, False
        nrd = os.path.join(PKG, m.group(1))
        for n in ("s0a_processlist", "s0b_threads", "s0c_shards", "s0d_explain"):
            shutil.copy2(os.path.join(srd, n + ".json"), os.path.join(nrd, n + ".json"))
        for gi in range(1, ng + 1):
            shutil.copy2(os.path.join(srd, f"{wid}_s{gi}.json"), os.path.join(nrd, f"w01_s{gi}.json"))
        r2 = subprocess.run(py + ["collect", nrd, "--path", "A"], cwd=cwd, env=e, capture_output=True, text=True)
        return r2.returncode, r1.stdout + r2.stdout, r1.stderr + r2.stderr, False

    hp = p("history", "patrol24_history.csv")              # the copied history may hold this window (a backfill row): drop it
    if os.path.exists(hp):
        old = read_hist()
        if old:
            with open(hp, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(old[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(r for r in old if r.get("window_end_utc") != slot_window(d)[1].strftime(FMT))
    t1 = at(d, (22, 5))
    print(f"[1] 纽约 {d} 22:05：{cron_once(t1, replay, transport)}")
    if len(sent) != 1:
        raise SystemExit(f"expected one post, got {len(sent)}")
    text = sent[0]["content"]["text"]
    if text + "\n" != open(post_path(d), encoding="utf-8").read():
        raise SystemExit("the sent text differs from the post file")
    print("----- 发到测试群的文字 -----\n" + text + "\n----- 到这里 -----")
    print(f"[2] 纽约 {d} 22:35：{cron_once(at(d, (22, 35)), replay, transport)}（应为 posted，不再发）")
    if len(sent) != 1:
        raise SystemExit("a second post was sent")
    d2 = d + timedelta(days=1)
    cfg["start_date"] = d.isoformat()
    save_cfg(cfg)

    def busy(argv, cwd, env, timeout):
        return 3, "", "另一个查库任务可能正在跑（rehearsal）", False
    for hm in ((22, 5), (22, 35), (23, 5), (23, 35)):
        cron_once(at(d2, hm), busy, transport)
    if len(sent) != 2 or sent[1]["content"]["text"] != header(d2) + "\n" + FAILLINE:
        raise SystemExit("the failure line was not sent exactly once at 23:35")
    print(f"[3] 纽约 {d2} 每次都退出码 3：23:35 发了「暂时取不到」：\n" + sent[1]["content"]["text"])
    return 0


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("cron", "run", "status", "cron-line", "leakcheck", "verify", "net-check", "enable", "disable", "adopt-host"):
        sub.add_parser(nm)
    for nm in ("install-cron", "uninstall-cron"):
        sub.add_parser(nm)
    for nm in ("set-webhook", "forget-webhook"):
        x = sub.add_parser(nm); x.add_argument("--target", required=True, choices=["test", "team"])
        if nm == "set-webhook":
            x.add_argument("--secret", action="store_true", help="also read a signing secret (optional)")
    x = sub.add_parser("set-mode"); x.add_argument("mode", choices=["test", "team"]); x.add_argument("--force", action="store_true")
    for nm in ("skip", "unskip", "set-start"):
        x = sub.add_parser(nm); x.add_argument("--date", required=True)
    x = sub.add_parser("send-post"); x.add_argument("--date", required=True); x.add_argument("--resend-uncertain", action="store_true")
    x.add_argument("--accept-lag", action="store_true", help="the window's last hour had no request at all and you checked the numbers")
    x = sub.add_parser("test-send"); x.add_argument("--target", required=True)
    x = sub.add_parser("dry-run"); x.add_argument("--at")
    x = sub.add_parser("rehearse"); x.add_argument("--date")
    x = sub.add_parser("_rehearse_inner", help=argparse.SUPPRESS); [x.add_argument(k) for k in ("d", "src", "wid", "ng")]
    x = sub.add_parser("init"); x.add_argument("--start-date", required=True); x.add_argument("--no-cli", action="store_true")
    x.add_argument("--child-path"); x.add_argument("--python"); x.add_argument("--lang", default="C.UTF-8")
    x.add_argument("--reinit", action="store_true")
    a = ap.parse_args(argv)
    fn = {"cron": cmd_cron, "run": cmd_cron, "status": cmd_status, "set-webhook": cmd_set_webhook,
          "forget-webhook": cmd_forget_webhook, "set-mode": cmd_set_mode, "enable": cmd_toggle, "disable": cmd_toggle,
          "skip": cmd_toggle, "unskip": cmd_toggle, "set-start": cmd_toggle, "adopt-host": cmd_toggle,
          "send-post": cmd_send_post, "test-send": cmd_test_send, "dry-run": cmd_dry_run, "rehearse": cmd_rehearse,
          "_rehearse_inner": cmd_rehearse_inner, "net-check": cmd_net_check, "leakcheck": cmd_leakcheck,
          "cron-line": cmd_cron_line, "install-cron": cmd_install_cron, "uninstall-cron": cmd_install_cron,
          "init": cmd_init, "verify": cmd_verify}[a.cmd]
    r = fn(a)
    if a.cmd in ("cron", "run"):
        if r not in ("idle", "gated", "not_initialized", "early"):
            print(f"{nyfmt(datetime.now(UTC))} cron: {r}")
        return 0
    return r if isinstance(r, int) else 0


if __name__ == "__main__":
    sys.exit(main())
