#!/usr/bin/env python3
"""Print UTC windows for a target America/New_York time range and the same hours on each of the previous N days,
one 'start~end' per line (input for shard_runner.py --windows-file). DST-safe: each day's bounds are converted
separately.
  python3 same_hours.py 2026-09-24T00:00 2026-09-25T00:00 --prev 7 > windows.txt"""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
NY, UTC = ZoneInfo("America/New_York"), ZoneInfo("UTC")
ap = argparse.ArgumentParser(); ap.add_argument("start"); ap.add_argument("end"); ap.add_argument("--prev", type=int, default=7)
a = ap.parse_args()
s, e = (datetime.fromisoformat(x).replace(tzinfo=NY) for x in (a.start, a.end))
for k in range(0, a.prev + 1):
    ws, we = s - timedelta(days=k), e - timedelta(days=k)
    print(f"{ws.astimezone(UTC):%Y-%m-%d %H:%M:%S}~{we.astimezone(UTC):%Y-%m-%d %H:%M:%S}")
