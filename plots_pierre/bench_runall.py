#!/usr/bin/env python3
"""
Run ./bench_having_vs_join.sh for every (OP, SEMI) combination on K=KMIN..KMAX,
parse the per-rep timings the bench prints to stderr, aggregate them
(mean / std / min / max over REPS), and write two CSVs:

  bench_runs.csv     -- per-rep raw rows (op, semi, k, side, rep, time_ms,
                        plan_ms, rows); time_ms is the execution time and
                        plan_ms the planning time reported by EXPLAIN ANALYZE
  bench_summary.csv  -- per (op, semi, k, side) aggregate of the execution
                        time, the planning time and their sum

Env overrides:
  KMIN (0), KMAX (15), REPS (3), OBJ (72), STATEMENT_TIMEOUT (300s),
  PGDATABASE / PGHOST / ... (passed through to psql),
  OUT_RAW (bench_runs.csv), OUT_SUMMARY (bench_summary.csv).
"""

import csv
import os
import re
import statistics
import subprocess
import sys
from collections import defaultdict

KMIN = int(os.environ.get("KMIN", 0))
KMAX = int(os.environ.get("KMAX", 15))
REPS = int(os.environ.get("REPS", 3))
OBJ = int(os.environ.get("OBJ", 72))
TIMEOUT = os.environ.get("STATEMENT_TIMEOUT", "300s")
OUT_RAW = os.environ.get("OUT_RAW", "bench_runs.csv")
OUT_SUMMARY = os.environ.get("OUT_SUMMARY", "bench_summary.csv")

# Matches per-rep stderr lines from bench_having_vs_join.sh:
#   "  having    k=2 rep 1: 525.693 ms (plan=3.412 ms, rows=2483)"
#   "  having_NS k=2 rep 1: 533.327 ms (plan=3.398 ms, rows=2483)"
#   "  join      k=2 rep 1: 494.767 ms (plan=12.050 ms, rows=2483)"
PAT = re.compile(
    r"^\s+(having_NS|having|join)\s+k=(\d+)\s+rep\s+(\d+):\s+([\d.]+)\s+ms"
    r"\s+\(plan=([\d.]+)\s+ms,\s+rows=(\d+)\)"
)

COMBOS = [
    # (SEMI, OP)
    ("formula", ">="),
    ("formula", "<="),
    ("prob",    ">="),
    ("prob",    "<="),
]


def run_one_combo(semi: str, op: str) -> list[dict]:
    """Spawn the bench for one (semi, op); echo all output through; collect per-rep."""
    env = os.environ.copy()
    env.update({
        "SEMI": semi,
        "OP": op,
        "KMIN": str(KMIN),
        "KMAX": str(KMAX),
        "REPS": str(REPS),
        "OBJ": str(OBJ),
        "STATEMENT_TIMEOUT": TIMEOUT,
    })
    print(f"\n===== SEMI={semi}  OP='{op}' =====", file=sys.stderr, flush=True)
    p = subprocess.Popen(
        ["./bench_having_vs_join.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=1,
        text=True,
    )
    rows = []
    for line in p.stdout:
        sys.stderr.write(line)
        sys.stderr.flush()
        m = PAT.match(line)
        if m:
            side, k, rep, ms, plan_ms, n_rows = m.groups()
            rows.append({
                "op": op,
                "semi": semi,
                "k": int(k),
                "side": side,
                "rep": int(rep),
                "time_ms": float(ms),
                "plan_ms": float(plan_ms),
                "rows": int(n_rows),
            })
    p.wait()
    return rows


def main() -> None:
    raw_rows: list[dict] = []
    for semi, op in COMBOS:
        raw_rows.extend(run_one_combo(semi, op))

    with open(OUT_RAW, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["op", "semi", "k", "side", "rep", "time_ms", "plan_ms", "rows"],
        )
        w.writeheader()
        for r in raw_rows:
            w.writerow(r)

    groups: dict[tuple[str, str, int, str], list[tuple[float, float, int]]] = defaultdict(list)
    for r in raw_rows:
        groups[(r["op"], r["semi"], r["k"], r["side"])].append(
            (r["time_ms"], r["plan_ms"], r["rows"]))

    def stats(xs: list[float]) -> tuple[float, float]:
        return (statistics.mean(xs),
                statistics.stdev(xs) if len(xs) >= 2 else 0.0)

    with open(OUT_SUMMARY, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["op", "semi", "k", "side",
                    "n_reps", "mean_ms", "std_ms", "min_ms", "max_ms",
                    "mean_plan_ms", "std_plan_ms",
                    "mean_total_ms", "std_total_ms", "rows"])
        for (op, semi, k, side), vals in sorted(groups.items()):
            times = [v[0] for v in vals]
            plans = [v[1] for v in vals]
            totals = [v[0] + v[1] for v in vals]
            n_rows = vals[0][2]
            mean, std = stats(times)
            pmean, pstd = stats(plans)
            tmean, tstd = stats(totals)
            w.writerow([
                op, semi, k, side,
                len(times),
                f"{mean:.3f}",
                f"{std:.3f}",
                f"{min(times):.3f}",
                f"{max(times):.3f}",
                f"{pmean:.3f}",
                f"{pstd:.3f}",
                f"{tmean:.3f}",
                f"{tstd:.3f}",
                n_rows,
            ])

    print(f"\nwrote {OUT_RAW} ({len(raw_rows)} rows) and {OUT_SUMMARY}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
