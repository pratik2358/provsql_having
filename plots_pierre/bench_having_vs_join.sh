#!/bin/bash
# Scratch benchmark: HAVING COUNT(obj) >= K  vs  K self-joins, on the coco DB.
# Reports median execution time + output row count over REPS reps.
#
# Timing comes from EXPLAIN (ANALYZE, TIMING OFF, ...) so result rows are not
# shipped to the client (no client I/O in the timing) but the projection
# expression (sr_formula / probability_evaluate) is still fully evaluated.
#
#   ./bench_having_vs_join.sh                       # formula, >=, K=1..13
#   SEMI=prob ./bench_having_vs_join.sh             # probability_evaluate
#   OP='<=' ./bench_having_vs_join.sh               # at-most-K (JOIN via EXCEPT)
#   REPS=5 KMAX=8 STATEMENT_TIMEOUT=60s ./bench_having_vs_join.sh
#   OBJ=72 KMIN=1 KMAX=13 ./bench_having_vs_join.sh
#
# psql connection comes from the environment (PGDATABASE, PGHOST, ...).

set -uo pipefail

KMIN=${KMIN:-1}
KMAX=${KMAX:-13}
REPS=${REPS:-3}
OBJ=${OBJ:-72}
STATEMENT_TIMEOUT=${STATEMENT_TIMEOUT:-0}   # '0' = none, e.g. '60s'
SEMI=${SEMI:-formula}                       # 'formula' or 'prob'
OP=${OP:-'>='}                              # '>=' or '<='

case "$SEMI" in
  formula)
    EVAL_EXPR="sr_formula(provenance(),'image_mapping')"
    ZERO_PRED="prov <> '𝟘'"
    ;;
  prob)
    EVAL_EXPR="probability_evaluate(provenance())"
    ZERO_PRED="prov > 0"
    ;;
  *)
    echo >&2 "SEMI must be 'formula' or 'prob' (got '$SEMI')"; exit 1 ;;
esac

case "$OP" in
  '>='|'<=') ;;
  *) echo >&2 "OP must be '>=' or '<=' (got '$OP')"; exit 1 ;;
esac

# ---------- query templates ------------------------------------------------

having_sql() {
  local k=$1
  cat <<EOF
SELECT * FROM (
  SELECT img, $EVAL_EXPR AS prov
  FROM pred_dataset
  WHERE obj = $OBJ
  GROUP BY img
  HAVING COUNT(obj) $OP $k
) sub WHERE $ZERO_PRED
EOF
}

# "At least n distinct obj=$OBJ rows per img" via (n-1)-fold self-join.
join_at_least() {
  local n=$1
  local joins=""
  for ((i=2; i<=n; i++)); do
    local p=$((i-1))
    joins+="
    JOIN pred_dataset d$i ON d$i.img = d1.img AND d$i.obj = $OBJ AND d$i.id > d$p.id"
  done
  cat <<EOF
  SELECT DISTINCT d1.img
  FROM pred_dataset d1$joins
  WHERE d1.obj = $OBJ
EOF
}

join_sql() {
  local k=$1
  case "$OP" in
    '>=')
      cat <<EOF
SELECT * FROM (
  SELECT img, $EVAL_EXPR AS prov
  FROM (
$(join_at_least $k)
  ) AS t
) sub WHERE $ZERO_PRED
EOF
      ;;
    '<=')
      # COUNT <= k  ==  (at least 1) EXCEPT (at least k+1).
      # The outer ZERO_PRED filter is needed here too: monus(A, A∩B)
      # can evaluate to 𝟘 / 0 for some img.
      cat <<EOF
SELECT * FROM (
  SELECT img, $EVAL_EXPR AS prov
  FROM (
$(join_at_least 1)
    EXCEPT
$(join_at_least $((k+1)))
  ) AS t
) sub WHERE $ZERO_PRED
EOF
      ;;
  esac
}

# ---------- runner ---------------------------------------------------------

# Echoes "<ms> <rows>", "TIMEOUT 0", or returns non-zero on error.
# Second arg (optional) is extra SET statements to issue before the EXPLAIN
# (e.g. "SET provsql.cmp_probability_evaluation = off;").
run_once() {
  local sql=$1 extra=${2:-} out rc
  out=$(psql -X -q -A -t -v ON_ERROR_STOP=1 <<PSQL 2>&1
\pset pager off
SET search_path TO public, provsql;
SET statement_timeout = '$STATEMENT_TIMEOUT';
$extra
EXPLAIN (ANALYZE, TIMING OFF, COSTS OFF, BUFFERS OFF, SUMMARY ON) $sql;
PSQL
)
  rc=$?
  if (( rc != 0 )); then
    if echo "$out" | grep -q 'canceling statement due to statement timeout'; then
      echo "TIMEOUT 0"; return 0
    fi
    echo >&2 "psql error (rc=$rc):"
    echo >&2 "$out"
    return 1
  fi
  local ms rows
  ms=$(echo "$out"   | grep -oE 'Execution Time: [0-9.]+ ms' | awk '{print $3}')
  rows=$(echo "$out" | grep -oE 'actual rows=[0-9]+'         | head -1 | cut -d= -f2)
  if [[ -z $ms || -z $rows ]]; then
    echo >&2 "could not parse EXPLAIN output:"
    echo >&2 "$out"
    return 1
  fi
  echo "$ms $rows"
}

# For SEMI=prob, materialise both shapes into temp tables, FULL JOIN on img,
# and check (count, count, max|h.prov - j.prov|, one-sided count).  Also crank
# provsql.verbose_level so the Poisson-binomial shortcut NOTICE (if any) lands
# in psql's output.  Echoes "<check>|<shortcut_flag>", where check is
# OK / BAD(...) / TIMEOUT / ERR / - and shortcut_flag is Y / N / -.
verify_pair() {
  local k=$1
  local SHORTCUT_USED="-"
  [[ $SEMI != prob ]] && { echo "-|-"; return 0; }
  local hsql jsql out rc
  hsql=$(having_sql $k)
  jsql=$(join_sql   $k)
  # Each shape must be its own top-level SELECT so ProvSQL's planner hook
  # rewrites it (`provenance()` doesn't work inside a CTE the outer query
  # pulls from -- hits "provenance() called on a table without provenance").
  # Fresh psql session -> no leftover temp tables, no need for DROP IF EXISTS.
  out=$(psql -X -q -A -t -F'|' -v ON_ERROR_STOP=1 <<PSQL 2>&1
\pset pager off
SET search_path TO public, provsql;
SET statement_timeout = '$STATEMENT_TIMEOUT';
SET provsql.verbose_level = 5;
CREATE TEMP TABLE _vh AS $hsql;
CREATE TEMP TABLE _vj AS $jsql;
SELECT
  (SELECT count(*) FROM _vh),
  (SELECT count(*) FROM _vj),
  COALESCE((SELECT max(abs(h.prov - j.prov))
            FROM _vh h FULL JOIN _vj j USING (img)
            WHERE h.img IS NOT NULL AND j.img IS NOT NULL), 0),
  (SELECT count(*) FROM _vh h FULL JOIN _vj j USING (img)
   WHERE h.img IS NULL OR j.img IS NULL);
PSQL
)
  rc=$?
  local pb_count
  pb_count=$(echo "$out" | grep -c 'Poisson-binomial')
  if (( pb_count > 0 )); then
    SHORTCUT_USED="Y"
  elif (( rc == 0 )); then
    SHORTCUT_USED="N"
  fi
  if (( rc != 0 )); then
    if echo "$out" | grep -q 'canceling statement due to statement timeout'; then
      echo "TIMEOUT|$SHORTCUT_USED"; return 0
    fi
    echo >&2 "verify error: $out"
    echo "ERR|$SHORTCUT_USED"; return 0
  fi
  # Find the result line: four pipe-separated numeric fields.  Skips
  # NOTICE lines (Poisson-binomial NOTICE, etc.).
  local line h_n j_n max_diff one_side
  line=$(echo "$out" \
         | grep -E '^[0-9]+\|[0-9]+\|[0-9.eE+-]+\|[0-9]+$' \
         | tail -1)
  if [[ -z $line ]]; then
    echo >&2 "verify parse error, raw output was:"
    echo >&2 "$out"
    echo "ERR|$SHORTCUT_USED"; return 0
  fi
  IFS='|' read -r h_n j_n max_diff one_side <<< "$line"
  echo >&2 "  verify k=$k: h_n=$h_n j_n=$j_n max_diff=$max_diff one_side=$one_side shortcut=$SHORTCUT_USED"
  if [[ "$h_n" == "$j_n" && "$one_side" == "0" ]] \
     && awk "BEGIN { exit !($max_diff < 1e-6) }"; then
    echo "OK|$SHORTCUT_USED"
  else
    echo "BAD(h=$h_n j=$j_n d=$max_diff one=$one_side)|$SHORTCUT_USED"
  fi
}

median() {
  sort -n | awk '
    { v[NR]=$1 }
    END {
      n=NR; if (n==0) { print "NA"; exit }
      m=int((n+1)/2)
      if (n%2==1) print v[m]
      else printf("%.3f\n", (v[m]+v[m+1])/2)
    }'
}

# Echoes "<median_ms> <rows>" (or "TIMEOUT ?" / "ERROR ?").
# Third arg (optional) is extra SETs passed through to run_once.
measure() {
  local label=$1 sql=$2 extra=${3:-}
  local times=() rows="?" res r
  for ((r=1; r<=REPS; r++)); do
    if ! res=$(run_once "$sql" "$extra"); then
      echo >&2 "  $label rep $r: error"
      echo "ERROR ?"; return 0
    fi
    if [[ $res == TIMEOUT* ]]; then
      echo >&2 "  $label rep $r: TIMEOUT"
      echo "TIMEOUT ?"; return 0
    fi
    times+=("${res% *}")
    rows="${res#* }"
    echo >&2 "  $label rep $r: ${res% *} ms (rows=$rows)"
  done
  local med
  med=$(printf '%s\n' "${times[@]}" | median)
  echo "$med $rows"
}

# ---------- main loop ------------------------------------------------------

echo >&2 "SEMI=$SEMI  OP='$OP'  OBJ=$OBJ  REPS=$REPS  K=$KMIN..$KMAX  timeout=$STATEMENT_TIMEOUT"

# The "HAVING no shortcut" column is only meaningful for SEMI=prob (the
# Poisson-binomial pre-pass lives in probability_evaluate).  For SEMI=formula
# we omit it.
WANT_NOSHORT=0
[[ $SEMI == prob ]] && WANT_NOSHORT=1

if (( WANT_NOSHORT )); then
  printf '\n%-3s | %14s %8s | %14s %8s | %14s %8s | %8s | %8s | %-8s | %s\n' \
    K 'HAVING_ms' rows 'HAVING_NS_ms' rows 'JOIN_ms' rows 'NS/H' 'J/H' 'shortcut' 'check'
  printf -- '----+-------------------------+-------------------------+-------------------------+----------+----------+----------+--------\n'
else
  printf '\n%-3s | %14s %8s | %14s %8s | %8s | %-8s | %s\n' \
    K 'HAVING_ms' rows 'JOIN_ms' rows 'J/H' 'shortcut' 'check'
  printf -- '----+-------------------------+-------------------------+----------+----------+--------\n'
fi

for ((k=KMIN; k<=KMAX; k++)); do
  echo >&2 "=== K=$k ==="
  hv=$(measure "having    k=$k" "$(having_sql $k)")
  if (( WANT_NOSHORT )); then
    hns=$(measure "having_NS k=$k" "$(having_sql $k)" \
                   "SET provsql.cmp_probability_evaluation = off;")
  fi
  jv=$(measure "join      k=$k" "$(join_sql $k)")
  h_ms=${hv% *}; h_rows=${hv#* }
  j_ms=${jv% *}; j_rows=${jv#* }
  if (( WANT_NOSHORT )); then
    hn_ms=${hns% *}; hn_rows=${hns#* }
  fi
  if [[ $h_ms =~ ^[0-9.]+$ && $j_ms =~ ^[0-9.]+$ ]]; then
    sp=$(awk "BEGIN { printf(\"%.2fx\", $j_ms / $h_ms) }")
  else
    sp="-"
  fi
  if (( WANT_NOSHORT )) && [[ $hn_ms =~ ^[0-9.]+$ && $h_ms =~ ^[0-9.]+$ ]]; then
    nsh=$(awk "BEGIN { printf(\"%.2fx\", $hn_ms / $h_ms) }")
  else
    nsh="-"
  fi
  vp=$(verify_pair $k)
  chk=${vp%|*}; sc=${vp##*|}
  if (( WANT_NOSHORT )); then
    printf '%-3s | %14s %8s | %14s %8s | %14s %8s | %8s | %8s | %-8s | %s\n' \
      "$k" "$h_ms" "$h_rows" "$hn_ms" "$hn_rows" "$j_ms" "$j_rows" \
      "$nsh" "$sp" "$sc" "$chk"
  else
    printf '%-3s | %14s %8s | %14s %8s | %8s | %-8s | %s\n' \
      "$k" "$h_ms" "$h_rows" "$j_ms" "$j_rows" "$sp" "$sc" "$chk"
  fi
done
