#!/usr/bin/env python3
"""privacy_scan.py - scan outputs for phone numbers, emails, IPv4 addresses, long digit runs,
MD5-like hashes and connection secrets.

Usage:
  python3 privacy_scan.py PATH [PATH ...] [--allow ALLOWFILE] [--report OUT.md]

Scans .md .csv .tsv .sql .py .json .txt .log .yaml .yml .html .mmd files, the text of
.docx/.xlsx (stdlib zipfile) and .pdf (needs `pdftotext`). Images are not scanned.
Hits are never printed in full: the report shows file, line, category and a masked preview.

Flagged: phone numbers (US, CN mobile, dotted, +country-code forms), emails, public IPv4,
  8+ digit runs, MD5-like 32-hex tokens (an unsalted MD5 of a phone number or uid can be
  reversed), URLs with credentials, DSN/JDBC strings, password/token assignments, host:port.
Auto-exempt (counted, not flagged):
  - 8-digit dates YYYYMMDD (2020-2031), epoch seconds/milliseconds 2020-2031
  - digit runs inside sha1/sha256 hex digests and inside known IDs
    (strategy_ rule_ feature_ metric_ tool_ t_access_log_ trace_ request_)
  - fractional parts of decimals (e.g. an alert value 0.0123456789)
  - private / loopback IPv4 (10.x, 172.16-31.x, 192.168.x, 127.x, 0.0.0.0) and CIDR
    network ranges with prefix /24 or shorter (a range, not one address)
Allowlist: one line per reviewed hit: "<sha1 of the exact hit> <justification>".
The report file holds each hit's sha1 for allowlisting: keep it with the scanned files' owner,
never in a note that leaves the machine.
Exit code: 0 = no unresolved hits, 1 = unresolved hits, 2 = usage error (bad path or allowlist).
"""
import hashlib, os, re, shutil, subprocess, sys, zipfile
from datetime import datetime, timezone

TEXT_EXT = {'.md', '.csv', '.tsv', '.sql', '.py', '.json', '.txt', '.log', '.yaml', '.yml', '.html', '.mmd', '.sh'}
LO, HI = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp(), datetime(2031, 1, 1, tzinfo=timezone.utc).timestamp()
ID_PREFIX = re.compile(r'(strategy|rule|feature|metric|tool|t_access_log|trace|request)_[A-Za-z0-9_]*$', re.I)
PATTERNS = [
    ('credential-url', re.compile(r'[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@')),
    ('dsn', re.compile(r'\b(?:jdbc:[A-Za-z0-9]+|mysql|mariadb|postgres(?:ql)?|mongodb(?:\+srv)?|redis|sqlserver)://', re.I)),
    ('secret-assignment', re.compile(r'\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|MCP_DB_GATEWAY_SSE)\s*[=:]\s*(?![<$])[^\s,;`\'"]{4,}', re.I)),
    ('host:port', re.compile(r'(?<![\w.])(?:(?:\d{1,3}\.){3}\d{1,3}|(?=[\w.-]*[A-Za-z])[\w-]+(?:\.[\w-]+)+):\d{2,5}\b')),
    ('email', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
    ('md5-like', re.compile(r'(?<![0-9A-Fa-f])[0-9A-Fa-f]{32}(?![0-9A-Fa-f])')),
    ('ipv4', re.compile(r'(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])')),
    ('phone', re.compile(r'(?<![\d*])(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3,4}[\s.-]\d{4}(?![\d*])')),
    ('phone', re.compile(r'(?<![\d*])\+\d{1,3}(?:[\s.-]?\d){7,13}(?![\d*])')),
    ('digits8+', re.compile(r'(?<!\d)\d{8,}(?!\d)')),
]

def mask(s):
    return s if len(s) <= 4 else s[:2] + '*' * (len(s) - 4) + s[-2:]

def is_date8(s):
    try:
        return len(s) == 8 and 2020 <= int(s[:4]) <= 2031 and bool(datetime.strptime(s, '%Y%m%d'))
    except ValueError:
        return False

def exempt(cat, hit, line, start, end):
    if cat == 'secret-assignment':
        return '<' in hit or '${' in hit
    if cat == 'host:port':
        host = hit.rsplit(':', 1)[0]
        return 'x' in host and bool(re.fullmatch(r'(?:\d{1,3}|x)(?:\.(?:\d{1,3}|x)){3}', host))
    if cat == 'md5-like':
        return hit.isdigit() or not re.search(r'\d', hit) or not re.search(r'[A-Fa-f]', hit)
    if cat == 'ipv4':
        a, b = (int(x) for x in hit.split('.')[:2])
        cidr = re.match(r'\s*/\s*(\d{1,2})\b', line[end:])
        if cidr and int(cidr.group(1)) <= 24:
            return True
        return a in (0, 10, 127) or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)
    if cat == 'email':
        return hit.lower().endswith(('@example.com', '@anthropic.com'))
    if cat == 'digits8+':
        if is_date8(hit):
            return True
        if start >= 2 and line[start - 1] == '.' and line[start - 2].isdigit():
            return True
        n = int(hit)
        if len(hit) == 10 and LO <= n <= HI:
            return True
        if len(hit) == 13 and LO <= n / 1000 <= HI:
            return True
        m = re.search(r'[A-Za-z0-9_\-]*$', line[:start]); left = m.group(0) if m else ''
        m = re.match(r'[A-Za-z0-9_\-]*', line[end:]); right = m.group(0) if m else ''
        tok = left + hit + right
        if re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', tok):
            return True
        if ID_PREFIX.match(tok) or ID_PREFIX.match(left + hit):
            return True
    return False

def text_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXT:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    if ext in ('.docx', '.xlsx'):
        out = []
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith('.xml') and (n.startswith('word/') or n.startswith('xl/')):
                    xml = z.read(n).decode('utf-8', 'replace')
                    xml = re.sub(r'</w:p>|<w:br/>|</row>|</si>', '\n', xml)
                    xml = re.sub(r'</w:tc>|<w:tab/>|</c>|</v>|</t>|</is>', '\t', xml)
                    out.append(re.sub(r'<[^>]+>', '', xml))
        return '\n'.join(out)
    if ext == '.pdf':
        if not shutil.which('pdftotext'):
            return None
        return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout
    return ''

def main(argv):
    paths, allow_file, report = [], None, None
    it = iter(argv)
    for a in it:
        if a == '--allow': allow_file = next(it, None)
        elif a == '--report': report = next(it, None)
        else: paths.append(a)
    if not paths:
        print(__doc__); return 2
    allow = {}
    if allow_file and not os.path.exists(allow_file):
        print(f'allowlist not found: {allow_file}', file=sys.stderr); return 2
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print('path not found: ' + ', '.join(missing), file=sys.stderr); return 2
    if allow_file:
        for ln in open(allow_file, encoding='utf-8'):
            p = ln.strip().split(None, 1)
            if p and not p[0].startswith('#'):
                allow[p[0]] = p[1] if len(p) > 1 else ''
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '_local_only', '__pycache__')]
                files += [os.path.join(root, n) for n in sorted(names)]
        elif os.path.exists(p):
            files.append(p)
    scanned, skipped, auto, allowed, hits = 0, [], {}, 0, []
    for f in files:
        try:
            t = text_of(f)
        except Exception as e:
            skipped.append(f'{f} ({e.__class__.__name__})'); continue
        if t is None:
            skipped.append(f'{f} (pdftotext missing)'); continue
        if t == '':
            continue
        scanned += 1
        for i, line in enumerate(t.splitlines(), 1):
            taken = []
            for cat, rx in PATTERNS:
                for m in rx.finditer(line):
                    if any(m.start() < e and s < m.end() for s, e in taken):
                        continue
                    taken.append((m.start(), m.end()))
                    h = m.group(0)
                    if exempt(cat, h, line, m.start(), m.end()):
                        auto[cat] = auto.get(cat, 0) + 1; continue
                    if hashlib.sha1(h.encode()).hexdigest() in allow:
                        allowed += 1; continue
                    hits.append((f, i, cat, mask(h), hashlib.sha1(h.encode()).hexdigest()))
    lines = ['# Privacy scan', '',
             f'- time (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M}',
             f'- files scanned: {scanned}; skipped: {len(skipped)}',
             f'- auto-exempt: ' + (', '.join(f'{k} {v}' for k, v in sorted(auto.items())) or '0'),
             f'- allowlisted: {allowed}',
             f'- unresolved: {len(hits)}', '']
    if skipped:
        lines += ['## Skipped', ''] + [f'- {s}' for s in skipped] + ['']
    if hits:
        lines += ['## Unresolved hits (masked)', '', '| file | line | type | preview | sha1 |', '|---|---|---|---|---|']
        lines += [f'| {f} | {i} | {c} | `{p}` | {s[:12]} |' for f, i, c, p, s in hits]
    out = '\n'.join(lines) + '\n'
    if report:
        with open(report, 'w', encoding='utf-8') as fh: fh.write(out)
    print(out)
    return 1 if hits else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
