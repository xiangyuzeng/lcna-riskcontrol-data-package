#!/usr/bin/env python3
"""P0: run SHOW GRANTS and keep only the parsed privilege tokens (never user@host), and measure
SELECT 1 round-trip latency (5 calls) through the same guarded gateway client."""
import csv, os, re, sys, time
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PKG, "toolkit"))
from shard_runner import Gateway, RISK_SERVER  # noqa: E402

gw = Gateway().connect()
try:
    rows, _ = gw.query(RISK_SERVER, "SHOW GRANTS")
    out = []
    for r in rows:
        for g in r.values():
            m = re.match(r"GRANT (.+?) ON (\S+) TO ", str(g))
            if m:
                for p in m.group(1).split(","):
                    out.append({"privilege": p.strip(), "on_object": m.group(2).replace("`", "")})
            else:
                out.append({"privilege": "<unparsed grant line>", "on_object": ""})
    with open(os.path.join(PKG, "results", "p0_show_grants_parsed.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["privilege", "on_object"]); w.writeheader(); w.writerows(out)
    lat = []
    for i in range(5):
        t = time.time(); gw.query(RISK_SERVER, "SELECT /*+ MAX_EXECUTION_TIME(5000) */ 1 AS ok"); lat.append(time.time() - t)
        time.sleep(0.2)
    with open(os.path.join(PKG, "results", "p0_select1_latency.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["call", "seconds"]); [w.writerow([i + 1, round(x, 4)]) for i, x in enumerate(lat)]
    print(f"grants parsed: {len(out)} tokens; SELECT 1 latency min/median/max = "
          f"{min(lat):.3f}/{sorted(lat)[2]:.3f}/{max(lat):.3f} s")
finally:
    gw.close()
