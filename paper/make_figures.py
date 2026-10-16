"""Figures for the paper, built from the committed result files only.

Usage:
    python paper/make_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
INK, MUTED, GRID, SERIES = "#0b0b0b", "#52514e", "#d9d8d4", "#2a78d6"
plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": INK})


def load(p):
    return json.loads((ROOT / p).read_text())


def forest() -> None:
    r3 = load("results/round3/evaluation.json")["gpt-4o"]["fresh_2017_2023"]
    cit = load("results/citation_label.json")["all"]["citation"]["v3_ens"]["pooled"]
    tpl = load("results/templates_leakage.json")
    hum = load("results/human_predict.json")["auc"]
    pooled = r3["T4_v3_vs_source_prior_pooled"]
    rows = [
        ("Fresh 2017+2023, pooled (n=395)", pooled["value"], pooled["ci95"]),
        ("Fresh 2017+2023, within source", r3["T1_v3_within_source"]["value"], r3["T1_v3_within_source"]["ci95"]),
        ("Fresh 2017+2023, tension questions", r3["T6_v3_tension_auc"]["value"], r3["T6_v3_tension_auc"]["ci95"]),
        ("Citation-graph label (n=755)", cit["value"], cit["ci95"]),
        ("LLM-free template questions (n=595)", tpl["G1_v3_pooled_auc"]["value"], tpl["G1_v3_pooled_auc"]["ci95"]),
        ("Human annotator 1 (n=90)", hum["human_1"]["v3_ens"]["auc"], hum["human_1"]["v3_ens"]["ci95"]),
        ("Human annotator 2 (n=90)", hum["human_2"]["v3_ens"]["auc"], hum["human_2"]["v3_ens"]["ci95"]),
        ("Both humans agree (n=90)", hum["both_humans_say_addressed"]["v3_ens"]["auc"],
         hum["both_humans_say_addressed"]["v3_ens"]["ci95"]),
    ]
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    for i, (lab, v, (lo, hi)) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=SERIES, lw=2, solid_capstyle="round")
        ax.plot(v, y, "o", color=SERIES, ms=6, mec="white", mew=1.5)
        ax.text(hi + 0.012, y, f"{v:.2f}", va="center", color=INK, fontsize=8)
    ax.axvline(0.5, color=MUTED, lw=1, ls="--")
    ax.text(0.502, len(rows) - 0.45, "chance", color=MUTED, fontsize=7.5)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1])
    ax.set_xlim(0.4, 0.95)
    ax.set_ylim(-0.6, len(rows) - 0.3)
    ax.set_xlabel("AUC of the v3 forecast (95% bootstrap CI)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "forest_v3.pdf")
    fig.savefig(OUT / "forest_v3.png", dpi=200)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    forest()
