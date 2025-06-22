"""
benchmark.py  -  Section  performance driver

• Generates Erdős-Rényi graphs G(n, p)
• Runs:
    - minimal_fraction_max_matching  (combinatorial)
    - solve_fractional_matching_lp   (MILP via PuLP/CBC)
    - networkx.maximum_matching      (integral baseline)
    - networkx.maximal_matching      (simple greedy baseline)
• Records value and wall-clock time → CSV
"""

from __future__ import annotations
import argparse, time, random, logging, pathlib

import pandas as pd
import networkx as nx

from algorithms.fractional_matching import (
    minimal_fraction_max_matching,
    solve_fractional_matching_lp,
    matching_value,
)

log = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

DATA_DIR = pathlib.Path("output")
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "benchmarks.csv"


# ───────────────────────── graph generator ─────────────────────────
def er_graph(n: int, p: float) -> nx.Graph:
    """Undirected G(n, p) with a fresh seed each call."""
    return nx.fast_gnp_random_graph(n, p, seed=random.randrange(1_000_000))


# ───────────────────────── one experiment ─────────────────────────
def run_one(n: int, p: float) -> dict[str, float | int]:
    G = er_graph(n, p)

    # -------- fractional (combinatorial) ----------
    t0 = time.perf_counter()
    frac_cmp = minimal_fraction_max_matching(G)
    cmp_time = time.perf_counter() - t0
    cmp_val  = matching_value(frac_cmp)

    # -------- fractional (LP) ----------
    t0 = time.perf_counter()
    frac_lp  = solve_fractional_matching_lp(G)
    lp_time  = time.perf_counter() - t0
    lp_val   = matching_value(frac_lp)

   
    # -------- integral (greedy) ----------
    t0 = time.perf_counter()
    greedy   = nx.maximal_matching(G)
    gr_time  = time.perf_counter() - t0
    gr_val   = len(greedy)

    return dict(
        n=n, p=p,
        cmp_val=cmp_val, cmp_time=cmp_time,
        lp_val=lp_val,  lp_time=lp_time,
        gr_val=gr_val,   gr_time=gr_time,
    )


# ───────────────────────── main loop ─────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", nargs="+", type=int,
                    default=[200, 400, 800],
                    help="vertex counts to test")
    ap.add_argument("--p", type=float, default=0.05,
                    help="edge probability for G(n,p)")
    ap.add_argument("--repeat", type=int, default=3,
                    help="independent trials per n")
    ap.add_argument("--time-cap", type=float, default=60.0,
                    help="stop when combinatorial algo exceeds this many seconds")
    args = ap.parse_args()

    rows: list[dict] = []
    for n in args.sizes:
        for r in range(args.repeat):
            res = run_one(n, args.p)
            rows.append(res)
            log.info("✓ n=%d rep=%d  cmp=%.3fs  lp=%.3fs   gr=%.3fs",
                     n, r, res['cmp_time'], res['lp_time'],
                     res['gr_time'])
            if res["cmp_time"] > args.time_cap:
                log.warning("Combinatorial algo hit %.1fs (>%gs) - stopping", 
                            res["cmp_time"], args.time_cap)
                break
        else:
            # continue outer loop if inner did **not** break
            continue
        break  # inner break -> stop sizes loop

    pd.DataFrame(rows).to_csv(CSV_PATH, index=False)
    log.info("Saved results ➜ %s", CSV_PATH)


if __name__ == "__main__":
    main()
