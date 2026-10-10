#!/usr/bin/env python3
"""shard_runner.py — read-only query runner for the NA risk-control source database.

Talks to the MCP server `mcp-db-gateway` (tools `mysql_query` / `postgres_query` / `list_servers`)
over MCP-over-SSE. The endpoint is read from the environment variable MCP_DB_GATEWAY_SSE at run
time and is never printed, logged or written anywhere. There is no default endpoint.

Every statement passes `guard()` before it is sent:
  * exactly one statement; starts with SELECT / SHOW / DESC / DESCRIBE / EXPLAIN
    (WITH is refused: use derived tables so the hint is guaranteed top-level);
  * no write / admin keyword (INSERT UPDATE DELETE REPLACE CREATE ALTER DROP TRUNCATE RENAME GRANT
    REVOKE SET ANALYZE OPTIMIZE FLUSH KILL LOCK UNLOCK CALL HANDLER DO LOAD PREPARE EXECUTE
    DEALLOCATE TEMPORARY INTO OUTFILE DUMPFILE, FOR UPDATE, LOCK IN SHARE MODE, SLEEP(, BENCHMARK(),
    no `REPLACE(` anywhere (the gateway rejects it), no call to a known stored routine;
  * no bare column alias that is a MySQL reserved word or built-in function name (list read live from
    information_schema.KEYWORDS into _local_only/reserved_words.txt; `AS utc_date` failed with 1064 on 2026-09-26);
  * MySQL SELECT: `/*+ MAX_EXECUTION_TIME(n) */` right after the first SELECT, n <= 10000;
  * any reference to a log table needs literal bounds `<time_col> >= '...' AND <time_col> < '...'`
    on the raw column, span <= 1 day (kind=agg) or <= 1 hour (kind=rows).

Sub-commands
  check  FILE [--kind agg|rows]                       guard a statement file, print OK / reason
  once   --name N --template F [--server S] [--kind]  one statement (metadata / config / small)
  run    --name N --template F [--shards SPEC] [--batch K] [--ny-days A:B | --utc 'A~B' | --windows-file F]
         [--chunk day|hour] [--kind agg|rows] [--local] [--param k=v ...]
                                                      shard template x time windows, sequential
  fleet  --name N --template F [--engine mysql|postgres]
                                                      one statement per gateway server (names only)

Template placeholders (only these are substituted; other braces are left alone):
  {tbl} {shard} {utc_start} {utc_end} {ny_date} {offset_h} {salt} and any --param key.
A shard template must select `'{shard}' AS shard` and read `luckyus_iriskcontrolservice.{tbl}`.

Output (package mode): sql/<name>.sql (template + run header), results/<name>.csv (merged; per-part files
results/<name>/<part>.csv only with --parts), results/explain/<name>_shard0.csv, results/_runlog.csv.
With --local everything row-level goes to _local_only/raw/<name>/ instead, never into the package.
In package mode the runner refuses to write values that look like hashes, emails, IP addresses or
phone numbers. The console only ever shows counts and timings.
"""
import argparse, csv, gzip, json, os, queue, re, secrets, sys, threading, time
import urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from ny_day_bounds import ny_day_bounds_utc  # noqa: E402

RISK_SERVER = "aws-luckyus-iriskcontrolservice-rw"
RISK_DB = "luckyus_iriskcontrolservice"
MAX_HINT_MS = 10000
PAUSE_S = 0.2
SLOW_S = 3.0
LOG_TABLES = {  # table regex -> raw time column
    r"t_access_log_\d{4}": "create_time",
    r"t_gateway_validate_log_\d{4}": "create_time",
    r"t_operation_log": "operation_time",
    r"t_oplog": "create_time",
    r"t_rule_count": "call_time",
    r"t_quota": "quota_time",
    r"t_gateway_count": "call_time",
    r"t_rms_strategyengine_middle_quota": "quota_time",
}
FORBIDDEN = (r"INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|RENAME|GRANT|REVOKE|SET|ANALYZE|"
             r"OPTIMIZE|FLUSH|KILL|LOCK|UNLOCK|CALL|HANDLER|DO|LOAD|PREPARE|EXECUTE|DEALLOCATE|"
             r"TEMPORARY|INTO|OUTFILE|DUMPFILE")
ROUTINES = set()  # filled from _local_only/routines.txt if present (names of stored routines)
RESERVED = set()  # MySQL reserved words, filled from _local_only/reserved_words.txt (information_schema.KEYWORDS, RESERVED=1)
# built-in function names that fail as bare aliases even when not listed as reserved (2026-09-26: `AS utc_date` -> 1064)
BUILTIN_ALIAS_BAN = {"UTC_DATE", "UTC_TIME", "UTC_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP", "CURRENT_USER",
                     "LOCALTIME", "LOCALTIMESTAMP", "RANK", "ROW_NUMBER", "DENSE_RANK", "PERCENT_RANK", "CUME_DIST", "NTILE",
                     "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE", "GROUPING", "WINDOW", "ROWS", "GROUPS", "RANGE"}
CAST_TYPES = {"BINARY", "CHAR", "NCHAR", "JSON", "DECIMAL", "UNSIGNED", "SIGNED", "DATE", "DATETIME", "TIME", "DOUBLE", "FLOAT",
              "INTEGER", "INT", "YEAR", "REAL"}


class GuardError(Exception):
    pass


# ----------------------------------------------------------------------------- guard
def _strip(sql):
    """Remove comments (incl. optimizer hints) and string literals; keep structure."""
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    s = re.sub(r"(--\s|#)[^\n]*", " ", s)
    s = re.sub(r"'(?:[^'\\]|\\.|'')*'", "''", s)
    s = re.sub(r'"(?:[^"\\]|\\.|"")*"', '""', s)
    return s


def guard(sql, kind="agg", engine="mysql"):
    if "REPLACE(" in sql.upper().replace(" ", ""):
        raise GuardError("contains REPLACE( (gateway rejects it; use TRIM(LEADING ...))")
    s = _strip(sql).strip()
    body = s[:-1] if s.endswith(";") else s
    if ";" in body:
        raise GuardError("more than one statement")
    m = re.match(r"\s*(\w+)", body)
    first = m.group(1).upper() if m else ""
    if first not in ("SELECT", "SHOW", "DESC", "DESCRIBE", "EXPLAIN"):
        raise GuardError(f"statement must start with SELECT/SHOW/DESC/EXPLAIN, got {first or '?'}")
    up = re.sub(r"CHARACTER\s+SET|CHARSET", " ", body.upper())
    bad = re.search(r"\b(" + FORBIDDEN + r")\b", up)
    if bad:
        raise GuardError(f"forbidden keyword {bad.group(1)}")
    for pat in (r"FOR\s+UPDATE", r"LOCK\s+IN\s+SHARE\s+MODE", r"\bSLEEP\s*\(", r"\bBENCHMARK\s*\("):
        if re.search(pat, up):
            raise GuardError(f"forbidden construct {pat}")
    if re.search(r"SHOW\s+(FULL\s+)?PROCESSLIST", up):
        raise GuardError("SHOW PROCESSLIST exposes other sessions' SQL; use an aggregate on information_schema")
    for r in ROUTINES:
        if re.search(r"\b" + re.escape(r.upper()) + r"\s*\(", up):
            raise GuardError(f"calls stored routine {r}")
    for m in re.finditer(r"\bAS\s+([A-Za-z_][A-Za-z0-9_$]*)\b", s, flags=re.I):
        w = m.group(1).upper()
        if w in CAST_TYPES:
            continue                                  # CAST(x AS CHAR) / CONVERT: a type, not an alias
        if w in BUILTIN_ALIAS_BAN or w in RESERVED:
            raise GuardError(f"alias `{m.group(1)}` is a MySQL reserved word or built-in function name (quote-free aliases only)")
    if engine == "mysql" and first in ("SELECT", "EXPLAIN") and re.search(r"\bSELECT\b", up):
        nc = re.sub(r"/\*(?!\+).*?\*/", " ", sql, flags=re.S)
        nc = re.sub(r"(--\s|#)[^\n]*", " ", nc)
        h = re.search(r"\bSELECT\s*/\*\+\s*MAX_EXECUTION_TIME\((\d+)\)\s*\*/", nc, flags=re.I)
        first_sel = re.search(r"\bSELECT\b", nc, flags=re.I)
        if not h or h.start() != first_sel.start():
            raise GuardError("missing /*+ MAX_EXECUTION_TIME(n) */ right after the first SELECT")
        if int(h.group(1)) > MAX_HINT_MS:
            raise GuardError(f"MAX_EXECUTION_TIME above {MAX_HINT_MS} ms")
    # log tables need literal time bounds on the raw column
    for tpat, col in LOG_TABLES.items():
        refs = re.findall(r"\b(?:FROM|JOIN)\s+(?:\w+\.)?(" + tpat + r")\b", s, flags=re.I)
        refs = [r for r in refs if not re.search(r"information_schema", r, flags=re.I)]
        if not refs:
            continue
        colre = r"(?:(?<![\w(.])\w+\.|(?<![\w(.]))" + col
        lo = re.findall(colre + r"\s*>=\s*'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)'", sql)
        hi = re.findall(colre + r"\s*<\s*'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)'", sql)
        if len(lo) < len(refs) or len(hi) < len(refs):
            raise GuardError(f"{len(refs)} reference(s) to {tpat} but {len(lo)}/{len(hi)} literal bounds on {col}")
        limit = 3600 if kind == "rows" else 86400
        for a, b in zip(lo, hi):
            span = (datetime.strptime(b, "%Y-%m-%d %H:%M:%S") - datetime.strptime(a, "%Y-%m-%d %H:%M:%S")).total_seconds()
            if span <= 0 or span > limit:
                raise GuardError(f"time window {span:.0f}s outside (0, {limit}] for kind={kind}")
    return True


# ----------------------------------------------------------------------------- client
class Gateway:
    """Minimal MCP-over-SSE client (same protocol as the team's sms_attack/mcp_client.py)."""

    def __init__(self, timeout=120):
        url = os.environ.get("MCP_DB_GATEWAY_SSE")
        if not url:
            raise SystemExit("MCP_DB_GATEWAY_SSE is not set (point it at the mcp-db-gateway SSE endpoint)")
        self._url, self.timeout = url, timeout
        self._secret_bits = {url, urllib.parse.urlparse(url).hostname or url}
        self._events, self._next = queue.Queue(), 0

    def _redact(self, text):
        for b in self._secret_bits:
            text = text.replace(b, "<gateway>")
        return text

    def _reader(self):
        try:
            ev, data = None, []
            for raw in self._stream:
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line == "":
                    if data:
                        self._events.put((ev or "message", "\n".join(data)))
                    ev, data = None, []
                elif line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:"):
                    data.append(line[5:].lstrip())
        except Exception:
            pass

    def connect(self):
        try:
            req = urllib.request.Request(self._url, headers={"Accept": "text/event-stream"})
            self._stream = urllib.request.urlopen(req, timeout=self.timeout)
            threading.Thread(target=self._reader, daemon=True).start()
            ev, data = self._events.get(timeout=30)
            if ev != "endpoint":
                raise RuntimeError("unexpected first SSE event")
            base = self._url.rsplit("/sse", 1)[0]
            self._endpoint = urllib.parse.urljoin(base + "/", data.lstrip("/"))
            self._secret_bits.add(self._endpoint)
            self._request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                         "clientInfo": {"name": "rc-shard-runner", "version": "1.0"}})
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        except Exception as e:
            raise RuntimeError(self._redact(f"gateway connect failed: {e.__class__.__name__}: {e}")) from None
        return self

    def _post(self, payload):
        req = urllib.request.Request(self._endpoint, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=self.timeout).read()

    def _request(self, method, params):
        self._next += 1
        rid = self._next
        self._post({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            _, data = self._events.get(timeout=self.timeout)
            msg = json.loads(data)
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(self._redact(f"{method} failed: {msg['error']}"))
                return msg.get("result")

    def call(self, tool, args):
        try:
            res = self._request("tools/call", {"name": tool, "arguments": args})
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(self._redact(f"{tool}: {e.__class__.__name__}: {e}")) from None
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(self._redact(f"non-JSON reply from {tool}: {text[:300]}"))
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(self._redact(str(payload["error"])[:500]))
        return payload

    def query(self, server, sql, kind="agg", engine="mysql"):
        guard(sql, kind, engine)
        tool = "mysql_query" if engine == "mysql" else "postgres_query"
        t0 = time.time()
        payload = self.call(tool, {"server": server, "sql": sql})
        return payload.get("rows", []) if isinstance(payload, dict) else payload, time.time() - t0

    def close(self):
        try:
            self._stream.close()
        except Exception:
            pass


# ----------------------------------------------------------------------------- helpers
PLACE = re.compile(r"\{(\w+)\}")


def render(tpl, values):
    return PLACE.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), tpl)


RX_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RX_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
RX_IPV6 = re.compile(r"(?<![\w:])(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?![\w:])")
RX_HEX = re.compile(r"^[0-9a-fA-F]{16,}$")
RX_DIGITS = re.compile(r"\d{9,}")


def unsafe_cells(rows, numeric_ok=()):
    """Return a set of (column, reason) for values that must not enter the package."""
    bad = set()
    for r in rows:
        for k, v in r.items():
            if k.endswith("_h"):
                bad.add((k, "hash column")); continue
            if v is None:
                continue
            s = str(v)
            if isinstance(v, (int, float)):
                if k not in numeric_ok and abs(v) >= 1e8:
                    bad.add((k, "number >= 1e8"))
                continue
            if RX_HEX.match(s):
                bad.add((k, "hex >= 16")); continue
            if RX_EMAIL.search(s):
                bad.add((k, "email")); continue
            if RX_IPV4.search(s):
                bad.add((k, "ipv4")); continue
            m6 = RX_IPV6.search(s)
            if m6 and ("::" in m6.group(0) or re.search(r"[a-fA-F]", m6.group(0)) or m6.group(0).count(":") >= 4):
                bad.add((k, "ipv6")); continue
            if k not in numeric_ok and RX_DIGITS.search(s):
                bad.add((k, "9+ digit run")); continue
    return bad


def write_csv(path, rows, gz=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    op = gzip.open if gz else open
    with op(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                        for k, v in r.items()})
    return cols


RUNLOG_FIELDS = ["name", "finished_ny", "server", "statements", "rows", "seconds", "slow_statements", "local", "columns",
                 "shards", "batch", "failed", "error"]


def append_log(row):
    """Append one run to results/_runlog.csv with a fixed header (missing fields left blank)."""
    path = os.path.join(PKG, "results", "_runlog.csv")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RUNLOG_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in RUNLOG_FIELDS})


def log_timing(name, window_start, shards, batch, seconds, rows):
    path = os.path.join(PKG, "results", "timing.csv")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["name", "window_start_utc", "shards", "batch", "seconds", "rows"])
        w.writerow([name, window_start, shards, batch, round(seconds, 4), rows])


def ny_now():
    return datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))


def salt():
    p = os.path.join(PKG, "_local_only", ".run_salt")
    if not os.path.exists(p):
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, secrets.token_hex(16).encode())
        os.close(fd)
    return open(p).read().strip()


def shard_list(spec, all_shards):
    if spec == "all":
        return all_shards
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += [s for s in all_shards if int(a) <= int(s) <= int(b)]
        else:
            out += [s for s in all_shards if int(s) == int(part)]
    return out


def windows(args):
    """List of (utc_start, utc_end, ny_date, offset_h)."""
    out = []
    if args.ny_days:
        a, b = [datetime.strptime(x, "%Y-%m-%d").date() for x in args.ny_days.split(":")]
        d = a
        while d <= b:
            s, e, off = ny_day_bounds_utc(d)
            if args.chunk == "hour":
                t, te = datetime.strptime(s, "%Y-%m-%d %H:%M:%S"), datetime.strptime(e, "%Y-%m-%d %H:%M:%S")
                while t < te:
                    u = min(t + timedelta(hours=1), te)
                    out.append((t.strftime("%Y-%m-%d %H:%M:%S"), u.strftime("%Y-%m-%d %H:%M:%S"), str(d), off))
                    t = u
            else:
                out.append((s, e, str(d), off))
            d += timedelta(days=1)
    elif getattr(args, "windows_file", None):
        for ln in open(args.windows_file, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                a_, b_ = ln.split("~")
                out.append((a_.strip(), b_.strip(), "", ""))
    elif args.utc:
        a, b = [datetime.strptime(x, "%Y-%m-%d %H:%M:%S") for x in args.utc.split("~")]
        step = timedelta(hours=1) if args.chunk == "hour" else timedelta(days=1)
        t = a
        while t < b:
            u = min(t + step, b)
            out.append((t.strftime("%Y-%m-%d %H:%M:%S"), u.strftime("%Y-%m-%d %H:%M:%S"), "", ""))
            t = u
    else:
        out.append(("", "", "", ""))
    return out


class Lock:
    def __init__(self):
        self.p = os.path.join(PKG, "_local_only", ".db_lock")

    def __enter__(self):
        try:
            fd = os.open(self.p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise SystemExit("another DB run holds _local_only/.db_lock — refusing to run concurrently")
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        return self

    def __exit__(self, *a):
        try:
            os.remove(self.p)
        except FileNotFoundError:
            pass


def load_routines():
    p = os.path.join(PKG, "_local_only", "routines.txt")
    if os.path.exists(p):
        ROUTINES.update(x.strip() for x in open(p) if x.strip())
    k = os.path.join(PKG, "_local_only", "reserved_words.txt")
    if os.path.exists(k):
        RESERVED.update(x.strip().upper() for x in open(k) if x.strip())


def save_sql(name, tpl, header):
    path = os.path.join(PKG, "sql", name + ".sql")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("-- " + "\n-- ".join(header) + "\n\n" + tpl.strip() + "\n")


def processlist_ok(gw, server):
    sql = ("SELECT /*+ MAX_EXECUTION_TIME(5000) */ COMMAND, COUNT(*) AS n, MAX(TIME) AS max_time_s "
           "FROM information_schema.PROCESSLIST GROUP BY COMMAND")
    for attempt in range(5):
        rows, _ = gw.query(server, sql)
        busy = [r for r in rows if r["COMMAND"] not in ("Sleep", "Daemon", "Binlog Dump", "Binlog Dump GTID")
                and (r["max_time_s"] or 0) > 10]
        tr, _ = gw.query(server, "SHOW GLOBAL STATUS LIKE 'Threads_running'")
        running = int(tr[0]["Value"]) if tr else 0
        rec = {"time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "server": server,
               "threads_running": running, "busy_commands": len(busy),
               "max_nonsleep_s": max([r["max_time_s"] or 0 for r in rows if r["COMMAND"] not in ("Sleep", "Daemon")] or [0])}
        p = os.path.join(PKG, "results", "processlist_checks.csv")
        new = not os.path.exists(p)
        with open(p, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rec)); new and w.writeheader(); w.writerow(rec)
        if not busy and running <= 10:
            return True
        print(f"  server busy (threads_running={running}, long queries={len(busy)}), waiting 30s", flush=True)
        time.sleep(30)
    raise SystemExit("server stayed busy; aborting this run")


def explain_gate(gw, server, name, sql_branch):
    rows, _ = gw.query(server, "EXPLAIN " + sql_branch)
    write_csv(os.path.join(PKG, "results", "explain", f"{name}_shard0.csv"), rows)
    ok_key = any((r.get("key") and r.get("type") in ("range", "ref", "const", "eq_ref")) for r in rows)
    big_scan = [r for r in rows if r.get("type") == "ALL" and not str(r.get("table", "")).startswith("<")
                and (r.get("rows") or 0) > 20000]
    if not ok_key or big_scan:
        raise SystemExit(f"EXPLAIN gate failed for {name}: indexed access={ok_key}, large full scans={len(big_scan)}")


# ----------------------------------------------------------------------------- commands
def cmd_check(a):
    load_routines()
    try:
        guard(open(a.file, encoding="utf-8").read(), a.kind, a.engine)
        print("OK")
    except GuardError as e:
        print(f"REFUSED: {e}"); sys.exit(1)


def _finish(a, name, rows_by_part, header_extra, t_start, n_stmt, slow):
    local = a.local
    base = os.path.join(PKG, "_local_only", "raw") if local else os.path.join(PKG, "results")
    all_rows = [r for part in rows_by_part.values() for r in part]
    if not local:
        bad = unsafe_cells(all_rows, set((a.numeric_ok or "").split(",")))
        if bad:
            raise SystemExit(f"REFUSED to write {name}: " + ", ".join(sorted(f"{c}:{w}" for c, w in bad))
                             + " — rerun with --local or fix the SQL")
    if len(rows_by_part) > 1 and (local or getattr(a, "parts", False)):
        for part, rows in rows_by_part.items():
            write_csv(os.path.join(base, name, f"{part}.csv" + (".gz" if local else "")), rows, gz=local)
    cols = write_csv(os.path.join(base, f"{name}.csv" + (".gz" if local else "")), all_rows, gz=local)
    append_log({"name": name, "finished_ny": ny_now().strftime("%Y-%m-%d %H:%M:%S"), "server": a.server,
                "statements": n_stmt, "rows": len(all_rows), "seconds": round(time.time() - t_start, 1),
                "slow_statements": slow, "local": int(local), "columns": len(cols), **header_extra})
    print(f"{name}: {n_stmt} statement(s), {len(all_rows)} rows, {time.time() - t_start:.1f}s, slow={slow}"
          + (" [local]" if local else ""))


def cmd_once(a):
    load_routines()
    tpl = open(a.template, encoding="utf-8").read()
    params = dict(p.split("=", 1) for p in (a.param or []))
    wins = windows(a)
    save_sql(a.name, tpl, [f"name: {a.name}", f"server: {a.server} (via MCP server mcp-db-gateway)",
                           f"purpose: {a.desc}", f"kind: {a.kind}; windows: {len(wins)}"
                           + (f" [{wins[0][0]} .. {wins[-1][1]}) UTC" if wins[0][0] else ""),
                           f"params: {json.dumps(params, ensure_ascii=False)}", f"run (NY): {ny_now():%Y-%m-%d %H:%M}"])
    with Lock():
        gw = Gateway().connect()
        try:
            t0, parts, slow, n = time.time(), {}, 0, 0
            for (s, e, d, off) in wins:
                vals = dict(params, utc_start=s, utc_end=e, ny_date=d, offset_h=off)
                if "{salt}" in tpl:
                    vals["salt"] = salt()
                rows, el = gw.query(a.server, render(tpl, vals), a.kind, a.engine)
                n += 1; slow += el > SLOW_S
                parts[d or s or "all"] = rows
                time.sleep(PAUSE_S)
            _finish(a, a.name, parts, {"shards": "", "batch": ""}, t0, n, slow)
        finally:
            gw.close()


def cmd_run(a):
    load_routines()
    tpl = open(a.template, encoding="utf-8").read()
    if "'{shard}' AS shard" not in tpl or "{tbl}" not in tpl:
        raise SystemExit("shard template must select '{shard}' AS shard and read {tbl}")
    params = dict(p.split("=", 1) for p in (a.param or []))
    wins = windows(a)
    with Lock():
        gw = Gateway().connect()
        try:
            rows, _ = gw.query(a.server, "SELECT /*+ MAX_EXECUTION_TIME(5000) */ TABLE_NAME FROM information_schema.TABLES "
                                         f"WHERE TABLE_SCHEMA='{RISK_DB}' AND TABLE_NAME REGEXP '^t_access_log_[0-9]{{4}}$' "
                                         "ORDER BY TABLE_NAME")
            all_shards = [r["TABLE_NAME"][-4:] for r in rows]
            shards = shard_list(a.shards, all_shards)
            save_sql(a.name, tpl, [f"name: {a.name}", f"server: {a.server} (via MCP server mcp-db-gateway)",
                                   f"purpose: {a.desc}", f"kind: {a.kind}; shards: {len(shards)} ({shards[0]}..{shards[-1]}); "
                                   f"batch: {a.batch}; windows: {len(wins)} [{wins[0][0]} .. {wins[-1][1]}) UTC, chunk={a.chunk}",
                                   f"params: {json.dumps(params, ensure_ascii=False)}",
                                   "merge: rows from every shard/window are concatenated; aggregate locally (sum counts)",
                                   f"run (NY): {ny_now():%Y-%m-%d %H:%M}"])
            processlist_ok(gw, a.server)
            vals0 = dict(params, tbl=f"t_access_log_{shards[0]}", shard=shards[0], utc_start=wins[0][0],
                         utc_end=wins[0][1], ny_date=wins[0][2], offset_h=wins[0][3])
            if "{salt}" in tpl:
                vals0["salt"] = salt()
            if not a.no_explain_gate:
                explain_gate(gw, a.server, a.name, render(tpl, vals0))
            t0, parts, slow, n, batch = time.time(), {}, 0, 0, a.batch
            for wi, (s, e, d, off) in enumerate(wins):
                i = 0
                while i < len(shards):
                    grp = shards[i:i + batch]
                    branches = []
                    for sh in grp:
                        v = dict(params, tbl=f"t_access_log_{sh}", shard=sh, utc_start=s, utc_end=e, ny_date=d, offset_h=off)
                        if "{salt}" in tpl:
                            v["salt"] = salt()
                        branches.append(render(tpl, v).strip().rstrip(";"))
                    sql = branches[0] if len(branches) == 1 else (
                        f"SELECT /*+ MAX_EXECUTION_TIME({MAX_HINT_MS}) */ u.* FROM ("
                        + " UNION ALL ".join(f"({b})" for b in branches) + ") u")
                    try:
                        rows, el = gw.query(a.server, sql, a.kind)
                    except RuntimeError as ex:
                        msg = str(ex)
                        append_log({"name": a.name, "finished_ny": ny_now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "server": a.server, "statements": n, "rows": -1, "seconds": 0, "slow_statements": slow,
                                    "local": int(a.local), "columns": 0, "shards": ",".join(grp), "batch": batch,
                                    "error": msg[:200]})
                        raise SystemExit(f"{a.name}: statement failed at window {s} shards {grp[0]}..{grp[-1]}: {msg[:300]}")
                    n += 1
                    log_timing(a.name, s, f"{grp[0]}..{grp[-1]}", len(grp), el, len(rows))
                    for r in rows:
                        parts.setdefault(r.get("shard", "?"), []).append(r)
                    if el > SLOW_S:
                        slow += 1
                        if batch > 1:
                            batch = max(1, batch // 2)
                            print(f"  slow statement ({el:.1f}s): batch halved to {batch}", flush=True)
                    i += len(grp)
                    time.sleep(PAUSE_S)
                if (wi + 1) % max(1, len(wins) // 10) == 0:
                    print(f"  window {wi + 1}/{len(wins)}  statements={n}  {time.time() - t0:.0f}s", flush=True)
            _finish(a, a.name, parts, {"shards": f"{shards[0]}..{shards[-1]}", "batch": a.batch}, t0, n, slow)
        finally:
            gw.close()


def cmd_fleet(a):
    load_routines()
    tpl = open(a.template, encoding="utf-8").read()
    save_sql(a.name, tpl, [f"name: {a.name}", "servers: every gateway server of the engine (via MCP server mcp-db-gateway)",
                           f"purpose: {a.desc}", f"run (NY): {ny_now():%Y-%m-%d %H:%M}"])
    with Lock():
        gw = Gateway().connect()
        try:
            servers = gw.call("list_servers", {}).get(a.engine, [])
            t0, parts, n, failed = time.time(), {}, 0, []
            for srv in servers:
                try:
                    rows, _ = gw.query(srv, render(tpl, {"server": srv}), "agg", a.engine)
                    parts[srv] = [dict(server=srv, **r) for r in rows]
                except RuntimeError as ex:
                    failed.append(srv)
                    parts[srv] = [{"server": srv, "error": str(ex)[:150]}]
                n += 1
                time.sleep(PAUSE_S)
            a.server = f"{len(servers)} {a.engine} servers"
            _finish(a, a.name, parts, {"shards": "", "batch": "", "failed": len(failed)}, t0, n, 0)
        finally:
            gw.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("file"); c.add_argument("--kind", default="agg"); c.add_argument("--engine", default="mysql")
    for nm in ("once", "run", "fleet"):
        p = sub.add_parser(nm)
        p.add_argument("--name", required=True); p.add_argument("--template", required=True)
        p.add_argument("--desc", default=""); p.add_argument("--server", default=RISK_SERVER)
        p.add_argument("--engine", default="mysql"); p.add_argument("--kind", default="agg", choices=["agg", "rows"])
        p.add_argument("--local", action="store_true"); p.add_argument("--param", action="append")
        p.add_argument("--numeric-ok", default="")
        p.add_argument("--ny-days"); p.add_argument("--utc"); p.add_argument("--chunk", default="day", choices=["day", "hour"])
        p.add_argument("--windows-file", help="explicit UTC windows, one 'YYYY-MM-DD HH:MM:SS~YYYY-MM-DD HH:MM:SS' per line")
        p.add_argument("--shards", default="all"); p.add_argument("--batch", type=int, default=16)
        p.add_argument("--no-explain-gate", action="store_true")
        p.add_argument("--parts", action="store_true", help="also keep results/<name>/<part>.csv (default for aggregates: merged file only, i.e. --no-parts)")
        p.add_argument("--no-parts", dest="parts", action="store_false")
    a = ap.parse_args()
    if a.cmd != "check" and getattr(a, "kind", "") == "rows" and not a.local:
        raise SystemExit("--kind rows (row-level extract) requires --local")
    {"check": cmd_check, "once": cmd_once, "run": cmd_run, "fleet": cmd_fleet}[a.cmd](a)


if __name__ == "__main__":
    main()
