#!/usr/bin/env python3
"""P6 mechanical checks (no DB):
 1. every `results/...` / `sql/...` / `dictionary/...` / `toolkit/...` path cited in the pages exists;
 2. every integer >= 100 written on README / 00-06 pages occurs in some results/*.csv (or cited .md) -> unmatched list;
 3. package contract (prompt section 6) files exist;
 4. the gateway host (read at run time from the environment, never printed) does not occur in any package file.
Writes results/p6_checks.csv (counts + unmatched numbers for manual review)."""
import glob, os, re, sys
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(PKG)
pages = ["README.md"] + sorted(glob.glob("0[0-6]_*.md")) + ["toolkit/README.md", "NEXT_RUN_改进建议.md"]
out = []
# 1 cited paths
missing = []
for p in pages:
    for m in re.findall(r"`((?:results|sql|dictionary|toolkit)/[^`\s]+)`", open(p, encoding="utf-8").read()):
        pat = m.replace("<", "*").replace(">", "*").replace("…", "*")
        pat = re.sub(r"\*+", "*", pat)
        if not glob.glob(pat) and not glob.glob(pat + "*"):
            missing.append(f"{p}: {m}")
out.append(("cited paths missing", len(missing), "; ".join(missing[:30])))
# 2 numbers
corpus = []
for f in glob.glob("results/**/*.csv", recursive=True) + glob.glob("results/**/*.md", recursive=True):
    corpus.append(open(f, encoding="utf-8", errors="replace").read())
corpus = "\n".join(corpus)
num_tokens = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", corpus))
unmatched = []
for p in pages:
    txt = open(p, encoding="utf-8").read()
    for n in re.findall(r"(?<![\w.\-_/])\d{1,3}(?:,\d{3})+(?![\d%])|(?<![\w.\-_/:])\d{3,}(?![\d%.:\-_])", txt):
        v = n.replace(",", "")
        if re.fullmatch(r"20[2-3]\d", v) or len(v) >= 8:
            continue
        if v not in num_tokens and v + ".0" not in num_tokens:
            unmatched.append(f"{p} → {n}")
out.append(("integers >= 100 not found verbatim in results/", len(unmatched), "; ".join(sorted(set(unmatched)))))
# 3 contract
need = ["README.md", "MANIFEST.md", "RUN_LOG.md", "NEXT_RUN_改进建议.md", "00_环境清单.md", "01_数据源与表清单.md", "02_线上配置导出.md",
        "04_数据问题结论.md", "05_取数手册与常见坑.md", "06_评估指标计算手册.md", "toolkit/README.md", "toolkit/privacy_scan.py",
        "toolkit/ny_day_bounds.py", "toolkit/shard_runner.py"]
miss = [f for f in need if not os.path.exists(f)] + ([] if glob.glob("03_近7日数据画像_*.md") else ["03_近7日数据画像_*.md"]) \
       + ([] if glob.glob("dictionary/*.md") else ["dictionary/"]) + ([] if glob.glob("sql/*.sql") else ["sql/"]) \
       + ([] if glob.glob("results/*.csv") else ["results/"]) + ([] if glob.glob("toolkit/*.sql") else ["toolkit/*.sql"])
out.append(("contract files missing", len(miss), "; ".join(miss)))
# 4 endpoint leak
url = os.environ.get("MCP_DB_GATEWAY_SSE", "")
host = re.sub(r"^\w+://", "", url).split("/")[0]
bits = [b for b in {url, host, host.split(":")[0]} if b]
hits = 0
for f in glob.glob("**/*", recursive=True):
    if os.path.isfile(f) and not f.startswith("_local_only"):
        t = open(f, "rb").read()
        hits += any(b.encode() in t for b in bits)
out.append(("files containing the gateway endpoint", hits if bits else -1, "endpoint not provided" if not bits else ""))
import csv
with open("results/p6_checks.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["check", "count", "detail"]); w.writerows(out)
for c, n, d in out:
    print(f"{c}: {n}" + (f"\n   {d[:1500]}" if d else ""))
