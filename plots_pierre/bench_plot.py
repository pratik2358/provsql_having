#!/usr/bin/env python3
"""
Render the four paper-style figures from bench_summary.csv as vector PDFs
matching the acmart layout of ../main.tex (libertine + newtxmath):

  fig1_formula_ge.pdf  --  COUNT(*) >= k, formula semiring (query exec time)
  fig2_formula_le.pdf  --  COUNT(*) <= k, formula
  fig3_prob_ge.pdf     --  COUNT(*) >= k, probability_evaluate
  fig4_prob_le.pdf     --  COUNT(*) <= k, probability

Each figure has two bars per K (HAVING vs JOIN) for the formula panels and
three bars per K for the probability panels (HAVING with the Poisson-binomial
shortcut, HAVING without it, JOIN). The y-axis is log-scaled, error bars are
+/- 1 std across reps. A combined 2x2 layout is also written:

  bench_fig_combined.pdf

Text is rendered by pdflatex via the pgf backend so the figures match the
surrounding paper's serif (Linux Libertine) and math fonts exactly. Individual
panels are sized for a 0.49\\textwidth slot in acmsmall.

Usage:
  ./bench_plot.py [bench_summary.csv]
"""

import csv
import sys
from collections import defaultdict

import matplotlib

matplotlib.use("pgf")
import matplotlib.pyplot as plt
import numpy as np

# Match the acmart preamble: libertine for text, newtxmath for math.
matplotlib.rcParams.update({
    "pgf.texsystem": "pdflatex",
    "text.usetex": True,
    "font.family": "serif",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "pgf.rcfonts": False,
    "pgf.preamble": r"""
\usepackage[T1]{fontenc}
\usepackage[tt=false]{libertine}
\usepackage[libertine]{newtxmath}
""",
})

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "bench_summary.csv"

# Style: muted blue / pink, consistent with the existing PDFs in ../plots.
HAVING_COLOR = "#9e9def"
HAVING_NS_COLOR = "#5d5cc4"   # darker shade of the same hue, no-shortcut bar
JOIN_COLOR = "#f5a3a0"

FIGS = [
    # (semi, op, title, individual filename)
    ("formula", ">=", r"$\mathtt{COUNT(*)}\geqslant k$ (symbolic provenance)", "fig1_formula_ge.pdf"),
    ("formula", "<=", r"$\mathtt{COUNT(*)}\leqslant k$ (symbolic provenance)", "fig2_formula_le.pdf"),
    ("prob",    ">=", r"$\mathtt{COUNT(*)}\geqslant k$ (probability)",         "fig3_prob_ge.pdf"),
    ("prob",    "<=", r"$\mathtt{COUNT(*)}\leqslant k$ (probability)",         "fig4_prob_le.pdf"),
]


def load_summary(path: str):
    """Returns dict keyed by (op, semi, k, side) -> (mean_ms, std_ms)."""
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r["op"], r["semi"], int(r["k"]), r["side"])
            out[key] = (float(r["mean_ms"]), float(r["std_ms"]))
    return out


def series(data, op, semi, side):
    pts = [(k, *v) for (o, s, k, sd), v in data.items()
           if o == op and s == semi and sd == side]
    pts.sort()
    return pts  # list of (k, mean, std)


def plot_panel(ax, data, op, semi, title=None):
    h = series(data, op, semi, "having")
    n = series(data, op, semi, "having_NS")  # only present for SEMI=prob
    j = series(data, op, semi, "join")
    if not h and not j:
        ax.text(0.5, 0.5, "no data", ha="center", va="center",
                transform=ax.transAxes)
        return

    use_ns = bool(n)
    ks = sorted(set([k for k, _, _ in h] +
                    [k for k, _, _ in j] +
                    [k for k, _, _ in n]))
    # K=0 with <= is degenerate (HAVING excludes empty groups, so
    # `COUNT(*) <= 0` returns no img regardless of input). >= 0 is
    # kept as the all-imgs baseline.
    if op == "<=":
        ks = [k for k in ks if k != 0]
    xpos = np.arange(len(ks))

    def pack(ser):
        d = {k: (m, s) for k, m, s in ser}
        return ([d.get(k, (np.nan, 0))[0] for k in ks],
                [d.get(k, (0, 0))[1] for k in ks])

    h_means, h_stds = pack(h)
    j_means, j_stds = pack(j)
    if use_ns:
        n_means, n_stds = pack(n)
        bw = 0.27
        offsets = [-bw, 0.0, +bw]
        bars = [
            (r"\textsc{having} (Poisson-bin.)", h_means, h_stds, HAVING_COLOR),
            (r"\textsc{having} (plain)",        n_means, n_stds, HAVING_NS_COLOR),
            (r"\textsc{join}",                  j_means, j_stds, JOIN_COLOR),
        ]
    else:
        bw = 0.4
        offsets = [-bw / 2, +bw / 2]
        bars = [
            (r"\textsc{having}", h_means, h_stds, HAVING_COLOR),
            (r"\textsc{join}",   j_means, j_stds, JOIN_COLOR),
        ]
    for off, (label, means, stds, color) in zip(offsets, bars):
        ax.bar(xpos + off, means, bw, yerr=stds, label=label, color=color,
               edgecolor="black", linewidth=0.3,
               capsize=1.2, error_kw=dict(ecolor="0.35", elinewidth=0.3, capthick=0.2))

    ax.set_yscale("log")
    ax.set_xticks(xpos)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel(r"$k$")
    ax.set_ylabel(r"Execution time (ms, log scale)")
    ax.grid(True, axis="y", which="major", linestyle=":",
            linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(direction="in", length=2)
    ax.legend(loc="upper left", frameon=False, handlelength=1.2,
              handletextpad=0.4, borderpad=0.2, labelspacing=0.2)
    if title:
        ax.set_title(title)


def main() -> None:
    data = load_summary(CSV_PATH)

    # Individual figures: sized to fit a 0.49\textwidth slot in acmsmall
    # (text width ~5"). 3.4" wide gives ~70% scaling when inlined, which
    # keeps the labels readable without crowding.
    for semi, op, title, fname in FIGS:
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        plot_panel(ax, data, op, semi, title=None)
        fig.tight_layout(pad=0.3)
        fig.savefig(fname, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        print(f"wrote {fname}")

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.6))
    for ax, (semi, op, title, _) in zip(axes.flat, FIGS):
        plot_panel(ax, data, op, semi, title=title)
    fig.tight_layout(pad=0.4)
    out = "bench_fig_combined.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
