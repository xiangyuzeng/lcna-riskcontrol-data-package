#!/usr/bin/env python3
"""P7 packaging: write MANIFEST.md (every file except _local_only/, MANIFEST.md, RUN_LOG.md with size and sha256), then
zip the package with paths relative to the package folder (no top-level folder, _local_only/ excluded) and write
<zip>.sha256 next to it. Nothing is written inside the package after the zip.
  python3 toolkit/package.py --pkg RC_data_<stamp> --zip RC_data_package_<stamp>.zip --scan-report <report.md> \
      --meta "data mode=..." --meta "..."
"""
import argparse, hashlib, os, re, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

ap = argparse.ArgumentParser()
ap.add_argument("--pkg", required=True); ap.add_argument("--zip", required=True); ap.add_argument("--scan-report", required=True)
ap.add_argument("--meta", action="append", default=[])
a = ap.parse_args()
pkg = os.path.abspath(a.pkg)
skip_top = {"_local_only"}


def files():
    out = []
    for root, dirs, names in os.walk(pkg):
        rel_root = os.path.relpath(root, pkg)
        dirs[:] = sorted(d for d in dirs if not (rel_root == "." and d in skip_top) and d != "__pycache__")
        for n in sorted(names):
            rel = os.path.normpath(os.path.join(rel_root, n))
            out.append(rel)
    return out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


scan = open(a.scan_report, encoding="utf-8").read()
summ = [l for l in scan.splitlines() if l.startswith("- ")]
if not re.search(r"^- unresolved: 0$", scan, flags=re.M):
    raise SystemExit("privacy scan is not clean (unresolved != 0) — refusing to package")
fl = [f for f in files() if f not in ("MANIFEST.md", "RUN_LOG.md")]
L = [f"# MANIFEST — {os.path.basename(pkg)}", "",
     f"- 包名：`{os.path.basename(pkg)}`；zip：`{os.path.basename(a.zip)}`",
     f"- 生成时间（America/New_York）：{datetime.now(ZoneInfo('America/New_York')):%Y-%m-%d %H:%M}"] + [f"- {m}" for m in a.meta] + [
     "", "## 隐私扫描（`toolkit/privacy_scan.py`，附录 B 原文；报告本身留在本机 `_local_only/`）", ""] + summ + [
     "", f"## 文件（{len(fl):,} 个；不含 `_local_only/`、`MANIFEST.md`、`RUN_LOG.md`）", "",
     "- `RUN_LOG.md`：在包内，**不计算哈希**（运行日志最后一行写完后才生成本清单）。", "",
     "| 路径 | 大小 (KB) | sha256 |", "|---|---|---|"]
for f in fl:
    p = os.path.join(pkg, f)
    L.append(f"| `{f}` | {os.path.getsize(p) / 1024:.1f} | {sha(p)} |")
open(os.path.join(pkg, "MANIFEST.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
with zipfile.ZipFile(a.zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for f in files():
        z.write(os.path.join(pkg, f), arcname=f)
digest = sha(a.zip)
open(a.zip + ".sha256", "w").write(f"{digest}  {os.path.basename(a.zip)}\n")
with zipfile.ZipFile(a.zip) as z:
    names = z.namelist()
bad = [n for n in names if n.startswith("_local_only") or n.startswith(os.path.basename(pkg) + "/")]
print(f"MANIFEST: {len(fl)} files; zip entries: {len(names)}; bad entries: {len(bad)}; sha256 {digest}")
