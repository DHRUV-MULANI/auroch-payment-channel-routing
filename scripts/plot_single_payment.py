#!/usr/bin/env python3
"""Plot the route allocation from the recorded single-payment smoke run."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/raw/single_payment_result.json"))
    parser.add_argument("--output", type=Path, default=Path("results/plots/single_payment"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = json.loads(args.input.read_text(encoding="utf-8"))
    values = result["route_allocations_sats"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar([f"Route {i}" for i in range(1, len(values) + 1)], values,
                  color=["#2364aa", "#3da35d", "#b9c0c9"])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in values], padding=3)
    ax.set_ylabel("Allocated payment (satoshi)")
    ax.set_title("Auroch prototype: one 100,000-sat payment\n(single unseeded smoke run; not paper-scale results)")
    ax.set_ylim(0, max(values + [1]) * 1.18)
    fig.tight_layout()
    fig.savefig(args.output / "route_allocations.png", dpi=180)
    fig.savefig(args.output / "route_allocations.pdf")
    plt.close(fig)
    print(f"Wrote figures to {args.output}")


if __name__ == "__main__":
    main()
