#!/usr/bin/env python3
"""
Quick command-line entry point.

Usage examples
--------------
$ python main.py --algo cmp      # Roi’s combinatorial algorithm
$ python main.py --algo lp       # LP formulation
"""
import argparse, time, networkx as nx
from algorithms.fractional_matching import (
    minimal_fraction_max_matching,
    solve_fractional_matching_lp,
    matching_value,
)

ALGORITHMS = {
    "cmp": minimal_fraction_max_matching,
    "lp":  solve_fractional_matching_lp,
}

def random_graph(n: int = 10, p: float = 0.15) -> nx.Graph:
    return nx.fast_gnp_random_graph(n, p, seed=None)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=ALGORITHMS.keys(), default="cmp",
                    help="Which algorithm to run")
    ap.add_argument("-n", type=int, default=10,
                    help="Number of vertices for a random G(n,p)")
    ap.add_argument("-p", type=float, default=0.15,
                    help="Edge probability for G(n,p)")
    args = ap.parse_args()

    G = random_graph(args.n, args.p)
    solver = ALGORITHMS[args.algo]

    t0 = time.perf_counter()
    M = solver(G)
    dt = time.perf_counter() - t0
    val = matching_value(M)

    print(f"{args.algo.upper()}  n={args.n}  p={args.p:.2f}")
    print(f"size = {val:.1f}   time = {dt:.3f}s")
    print(M)

if __name__ == "__main__":
    main()
