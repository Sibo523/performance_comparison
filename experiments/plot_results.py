"""
plot_results.py - pretty plots from output/benchmarks.csv
• collapses repetitions (mean std)
• draws error bars
• distinct markers + line styles (LP is dotted)
"""

from __future__ import annotations
import pathlib, logging
import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

CSV = pathlib.Path("output") / "benchmarks.csv"
if not CSV.exists():
    raise SystemExit("benchmarks.csv not found – run benchmark.py first.")

df = pd.read_csv(CSV).dropna(subset=["cmp_val", "lp_val", "gr_val"])

# ───────────────────────── aggregation ─────────────────────────
grp = df.groupby("n").agg(
    cmp_time_mean=("cmp_time", "mean"), cmp_time_std=("cmp_time", "std"),
    lp_time_mean=("lp_time", "mean"),   lp_time_std=("lp_time", "std"),
    gr_time_mean=("gr_time", "mean"),   gr_time_std=("gr_time", "std"),

    cmp_val_mean=("cmp_val", "mean"),   cmp_val_std=("cmp_val", "std"),
    lp_val_mean=("lp_val", "mean"),     lp_val_std=("lp_val", "std"),
    gr_val_mean=("gr_val", "mean"),     gr_val_std=("gr_val", "std"),
).reset_index()

# ───────────────────────── style palette ─────────────────────────
STYLES = {
    "Combinatorial": dict(marker="o", linestyle="-",  linewidth=1.6),  # solid
    "LP":            dict(marker="s", linestyle=":",  linewidth=1.6),  # dotted
    "Greedy":        dict(marker="^", linestyle="--", linewidth=1.6),  # dashed
}

def _plot(ax, x, y, yerr, label):
    m = ~y.isna()
    ax.errorbar(x[m], y[m], yerr=yerr[m], capsize=3, label=label, **STYLES[label])

# ───────────── run-time plot ─────────────
fig_rt, ax_rt = plt.subplots(figsize=(7, 5))
_plot(ax_rt, grp["n"], grp["cmp_time_mean"], grp["cmp_time_std"], "Combinatorial")
_plot(ax_rt, grp["n"], grp["lp_time_mean"],  grp["lp_time_std"],  "LP")
_plot(ax_rt, grp["n"], grp["gr_time_mean"],  grp["gr_time_std"],  "Greedy")

ax_rt.set_yscale("log")
ax_rt.set_xlabel("n (vertices)")
ax_rt.set_ylabel("run-time [s]  (log scale)")
ax_rt.set_title("Run-time vs n")
ax_rt.grid(True, which="both", linestyle="--", linewidth=0.3)
ax_rt.legend(framealpha=0.92)
fig_rt.tight_layout()
(fig_rt).savefig(CSV.parent / "runtime_vs_n.png", dpi=150)
plt.close(fig_rt)

# ───────────── value plot ─────────────
fig_val, ax_val = plt.subplots(figsize=(7, 5))
_plot(ax_val, grp["n"], grp["cmp_val_mean"], grp["cmp_val_std"], "Combinatorial")
_plot(ax_val, grp["n"], grp["lp_val_mean"],  grp["lp_val_std"],  "LP")
_plot(ax_val, grp["n"], grp["gr_val_mean"],  grp["gr_val_std"],  "Greedy")

ax_val.set_xlabel("n (vertices)")
ax_val.set_ylabel("matching value")
ax_val.set_title("Solution quality vs n")
ax_val.grid(True, linestyle="--", linewidth=0.3)
ax_val.legend(framealpha=0.92)
fig_val.tight_layout()
(fig_val).savefig(CSV.parent / "value_vs_n.png", dpi=150)
plt.close(fig_val)
