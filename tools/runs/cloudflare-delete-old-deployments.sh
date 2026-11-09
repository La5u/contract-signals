#!/bin/bash
# 2026-11-09 (owner: delete history): delete every Cloudflare Pages deployment of contract-signals except KEEP, the
# current production deployment, because each old deployment keeps its own *.pages.dev address with the files of its
# commit (raw snapshots with contact details, names). Wrangler lists 25 at a time, so it repeats until only KEEP is left.
# --force is needed: without it wrangler asks for confirmation, gets no answer, and exits 0 having deleted nothing.
# Stops if KEEP is missing from the list, or if a round removes nothing.
# Run: bash tools/runs/cloudflare-delete-old-deployments.sh <KEEP deployment id>
KEEP=${1:?current production deployment id}
P=contract-signals; n=0; fail=0; last=
while :; do
  list=$(npx --no-install wrangler pages deployment list --project-name $P --json 2>/dev/null) || { echo "list failed"; exit 1; }
  ids=$(python3 -I -c "
import json, sys
d = json.loads(sys.argv[1])
if '$KEEP' not in [x['Id'] for x in d]: sys.exit('KEEP is not the newest listed deployment set; stopped')
print(' '.join(x['Id'] for x in d if x['Id'] != '$KEEP'))" "$list") || exit 1
  [ -z "$ids" ] && break
  [ "$ids" = "$last" ] && { echo "a round removed nothing, stopped"; break; }
  last=$ids
  for id in $ids; do
    if out=$(npx --no-install wrangler pages deployment delete "$id" --project-name $P --force 2>&1); then n=$((n+1)); echo "deleted $id"; else fail=$((fail+1)); echo "failed $id: $(echo "$out" | tail -2 | cut -c1-200)"; fi
    [ $fail -gt 10 ] && { echo "too many failures, stopped"; break 2; }
  done
done
echo "deleted $n, failed $fail"
