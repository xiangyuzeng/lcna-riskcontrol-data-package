#!/usr/bin/env python3
"""Reproducibility checkpoint: sum results/p5_checkpoint.csv (team cookbook window, 20 x 24 h ending 2026-09-10 20:09 UTC) and
compare with reference counts given on the command line (never stored in code):
  python3 sql/local/p5_checkpoint.py --ref rows_cc_filter=N,pass_cc_filter=N,reject_cc_filter=N,review_cc_filter=N"""
import argparse, os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
ap = argparse.ArgumentParser(); ap.add_argument("--ref", default=""); a = ap.parse_args()
c = pd.read_csv(os.path.join(R, "p5_checkpoint.csv"))
cols = [x for x in ("rows_no_cc_filter", "rows_cc_filter", "pass_cc_filter", "reject_cc_filter", "review_cc_filter") if x in c]
tot = c[cols].sum()
ref = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in a.ref.split(",") if "=" in kv}
rows = [{"metric": m, "this_run": int(tot[m]), "reference": ref.get(m, ""), "diff": int(tot[m]) - ref[m] if m in ref else ""} for m in tot.index]
out = pd.DataFrame(rows); out.to_csv(os.path.join(R, "p5_checkpoint_summary.csv"), index=False); print(out.to_string(index=False))
