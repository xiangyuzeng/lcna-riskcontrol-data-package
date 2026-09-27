#!/usr/bin/env python3
"""UTC bounds of America/New_York calendar days, for WHERE create_time >= start AND create_time < end."""
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY, UTC = ZoneInfo("America/New_York"), ZoneInfo("UTC")

def ny_day_bounds_utc(d):
    start = datetime.combine(d, time(0), tzinfo=NY).astimezone(UTC)
    end = datetime.combine(d + timedelta(days=1), time(0), tzinfo=NY).astimezone(UTC)
    offset_h = int(-datetime.combine(d, time(12), tzinfo=NY).utcoffset().total_seconds() // 3600)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), offset_h

def last_full_days(n, today=None):
    today = today or datetime.now(NY).date()
    return [today - timedelta(days=i) for i in range(n, 0, -1)]

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    for d in last_full_days(n):
        s, e, off = ny_day_bounds_utc(d)
        print(f"{d}  utc_start={s}  utc_end={e}  offset_hours={off}")
