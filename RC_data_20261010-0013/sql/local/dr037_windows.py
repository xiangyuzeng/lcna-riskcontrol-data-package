#!/usr/bin/env python3
"""Month windows (UTC, <= 1 month each) for the DR-037 member query, from the first t_user.create_time (results/dr037_crm_check.csv)
to the end of NY 2026-10-09 (2026-10-10 04:00 UTC). Prints 'start~end' lines."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
c = pd.read_csv(os.path.join(PKG, "results", "dr037_crm_check.csv"))
start = pd.Timestamp(c.min_create.iloc[0]).normalize().replace(day=1)
end = pd.Timestamp("2026-10-10 04:00:00")
t = start
while t < end:
    u = min(t + pd.offsets.MonthBegin(1), end)
    print(f"{t:%Y-%m-%d %H:%M:%S}~{u:%Y-%m-%d %H:%M:%S}")
    t = u
