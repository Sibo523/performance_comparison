"""
plot_results.py - pretty plots from output/benchmarks.csv
• collapses repetitions (mean std)
• draws error bars
• distinct markers + line styles (LP is dotted)
"""

from __future__ import annotations
import logging
import pathlib
import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

CSV = pathlib.Path("output") / "benchmarks.csv"
if not CSV.exists():
    log.error(f"No data to plot! Run benchmark.py first to generate {CSV}")
    exit(1)

# Read the CSV file
df = pd.read_csv(CSV).dropna(subset=["cmp_val", "lp_val", "gr_val"])

# Check if C++ results exist in the dataframe
has_cpp = "cpp_time" in df.columns and "cpp_val" in df.columns

# Define aggregation functions for each column
agg_dict = {
    "cmp_time": ["mean", "std"],
    "lp_time": ["mean", "std"],
    "gr_time": ["mean", "std"],
    "cmp_val": ["mean", "std"],
    "lp_val": ["mean", "std"],
    "gr_val": ["mean", "std"],
}

# Add C++ aggregations if the columns exist
if has_cpp:
    agg_dict["cpp_time"] = ["mean", "std"]
    agg_dict["cpp_val"] = ["mean", "std"]

# Group by n and aggregate
grp = df.groupby("n").agg(agg_dict)
# Flatten the multi-level column index
grp.columns = ['_'.join(col).strip() for col in grp.columns.values]
grp = grp.reset_index()

# Helper function to plot with error bars
def _plot(ax, x, y, std, label):
    ax.errorbar(x, y, yerr=std, label=label, 
                marker=STYLES[label]["marker"], 
                linestyle=STYLES[label]["linestyle"],
                linewidth=STYLES[label]["linewidth"])

# Define plot styles
STYLES = {
    "Combinatorial": dict(marker="o", linestyle="-",  linewidth=1.6),  # solid
    "LP":            dict(marker="s", linestyle=":",  linewidth=1.6),  # dotted
    "Greedy":        dict(marker="^", linestyle="--", linewidth=1.6),  # dashed
    "C++":           dict(marker="*", linestyle="-.", linewidth=1.6),  # dash-dot
}

# ───────────────────────── run-time plot ─────────────────────────
fig_rt, ax_rt = plt.subplots(figsize=(7, 5))
_plot(ax_rt, grp["n"], grp["cmp_time_mean"], grp["cmp_time_std"], "Combinatorial")
_plot(ax_rt, grp["n"], grp["lp_time_mean"],  grp["lp_time_std"],  "LP")
_plot(ax_rt, grp["n"], grp["gr_time_mean"],  grp["gr_time_std"],  "Greedy")
if "cpp_time" in df.columns and not df["cpp_time"].isna().all():
    _plot(ax_rt, grp["n"], grp["cpp_time_mean"], grp["cpp_time_std"], "C++")

# ax_rt.set_yscale("log")  # Remove log scale
ax_rt.set_xlabel("n (vertices)")
ax_rt.set_ylabel("run-time (seconds)")
ax_rt.set_title("Run-time vs n")
ax_rt.grid(True, linestyle="--", linewidth=0.3)
ax_rt.legend(framealpha=0.92)
fig_rt.tight_layout()
fig_rt.savefig(CSV.parent / "runtime_vs_n.png", dpi=150)
plt.close(fig_rt)

# ───────────────────────── value plot ─────────────────────────
fig_val, ax_val = plt.subplots(figsize=(7, 5))
_plot(ax_val, grp["n"], grp["cmp_val_mean"], grp["cmp_val_std"], "Combinatorial")
_plot(ax_val, grp["n"], grp["lp_val_mean"],  grp["lp_val_std"],  "LP")
_plot(ax_val, grp["n"], grp["gr_val_mean"],  grp["gr_val_std"],  "Greedy")
if "cpp_val" in df.columns and not df["cpp_val"].isna().all():
    _plot(ax_val, grp["n"], grp["cpp_val_mean"], grp["cpp_val_std"], "C++")

ax_val.set_xlabel("n (vertices)")
ax_val.set_ylabel("matching value")
ax_val.set_title("Matching value vs n")
ax_val.grid(True, linestyle="--", linewidth=0.3)
ax_val.legend(framealpha=0.92)
fig_val.tight_layout()
fig_val.savefig(CSV.parent / "value_vs_n.png", dpi=150)
plt.close(fig_val)

log.info("Plots generated: runtime_vs_n.png and value_vs_n.png")
