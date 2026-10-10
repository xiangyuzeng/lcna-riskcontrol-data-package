#!/usr/bin/env bash
# P5 toolkit test tk06 (rule recheck), as run on 2026-10-10 ~02:30 NY from the package folder.
# Parameters come from sql/local/p5_pick.py (here: strategy_lf6DsxMdAPzy / feature_lydpDiga6SB9, '>' 10, period 300 s).
# Step 1 sends SQL through the runner (needs the gateway environment; only inside the production pull window);
# step 2 is local only. The extract (salted, row level) stays in _local_only/raw/ and is never packaged.
set -euo pipefail
eval "$(python3 sql/local/p5_pick.py)"
W0=$(python3 -c "from datetime import datetime,timedelta;print((datetime(2026,10,9,4)-timedelta(seconds=$TK06_PERIOD_S+3600)).strftime('%Y-%m-%d %H:%M:%S'))")
bash _local_only/gw.sh python3 toolkit/shard_runner.py run --name tk06_extract_$TK06_STRATEGY --template toolkit/tk06_rule_recheck_extract.sql \
  --kind rows --local --utc "$W0~2026-10-10 04:00:00" --chunk hour --param scene=LKUS_push --param feature_id=$TK06_FEATURE \
  --param strategy_id=$TK06_STRATEGY --desc "toolkit test: tk06 row-level extract for $TK06_STRATEGY / $TK06_FEATURE, NY 2026-10-09 plus warm-up (local only)"
python3 toolkit/recheck_counter.py --extract _local_only/raw/tk06_extract_$TK06_STRATEGY.csv.gz --feature-id $TK06_FEATURE --op "$TK06_OP" \
  --threshold $TK06_THRESHOLD --eval-from '2026-10-09 04:00:00' --config results/config_counter_features.csv \
  --out results/toolkit_tests/tk06_recheck_$TK06_STRATEGY.csv
