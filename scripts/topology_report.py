#!/usr/bin/env python3
"""Create descriptive topology figures and a summary for the local LN snapshot."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lngraph_2021_11_27__00_00.json"))
    parser.add_argument("--plots", type=Path, default=Path("results/plots/topology"))
    parser.add_argument("--summary", type=Path, default=Path("results/raw/topology_summary.json"))
    args = parser.parse_args()
    args.plots.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)

    with args.input.open(encoding="utf-8") as f:
        data = json.load(f)
    nodes, edges = data["nodes"], data["edges"]
    graph = nx.MultiGraph()
    graph.add_nodes_from(n["pub_key"] for n in nodes)
    capacities = np.asarray([int(e["capacity"]) for e in edges], dtype=np.int64)
    for e in edges:
        graph.add_edge(e["node1_pub"], e["node2_pub"], key=e["channel_id"])
    degrees = np.asarray([d for _, d in graph.degree()], dtype=np.int64)
    components = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    policy_counts = {
        "both_present": sum(e.get("node1_policy") is not None and e.get("node2_policy") is not None for e in edges),
        "one_present": sum((e.get("node1_policy") is None) != (e.get("node2_policy") is None) for e in edges),
        "both_missing": sum(e.get("node1_policy") is None and e.get("node2_policy") is None for e in edges),
    }
    summary = {
        "input": str(args.input),
        "nodes": len(nodes), "channels": len(edges),
        "connected_components": len(components),
        "largest_component_nodes": components[0] if components else 0,
        "degree": {"mean": float(degrees.mean()), "median": float(np.median(degrees)), "max": int(degrees.max())},
        "capacity_sats": {
            "min": int(capacities.min()), "p25": float(np.percentile(capacities, 25)),
            "median": float(np.median(capacities)), "mean": float(capacities.mean()),
            "p75": float(np.percentile(capacities, 75)), "max": int(capacities.max()),
        },
        "policy_presence": policy_counts,
        "caveat": "Descriptive topology statistics only; these do not constitute routing protocol experiment results.",
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def save(name: str) -> None:
        plt.tight_layout()
        plt.savefig(args.plots / f"{name}.png", dpi=180)
        plt.savefig(args.plots / f"{name}.pdf")
        plt.close()

    plt.figure(figsize=(8, 5))
    positive = degrees[degrees > 0]
    bins = np.logspace(0, np.log10(max(positive.max(), 2)), 35)
    plt.hist(positive, bins=bins, color="#2364aa", edgecolor="white")
    plt.xscale("log"); plt.yscale("log")
    plt.xlabel("Node degree (channels)"); plt.ylabel("Number of nodes")
    plt.title("Lightning snapshot degree distribution")
    save("degree_distribution")

    plt.figure(figsize=(8, 5))
    plt.hist(capacities, bins=60, color="#3da35d", edgecolor="white")
    plt.xlabel("Channel capacity (satoshi)"); plt.ylabel("Number of channels")
    plt.title("Channel capacity distribution")
    save("capacity_distribution")

    plt.figure(figsize=(8, 5))
    sorted_caps = np.sort(capacities)
    plt.plot(sorted_caps, np.arange(1, len(sorted_caps) + 1) / len(sorted_caps), color="#e07a5f")
    plt.xscale("log"); plt.ylim(0, 1)
    plt.xlabel("Channel capacity (satoshi, log scale)"); plt.ylabel("Cumulative fraction")
    plt.title("Channel capacity empirical CDF")
    save("capacity_cdf")

    plt.figure(figsize=(7, 5))
    plt.bar(list(policy_counts), list(policy_counts.values()), color=["#2364aa", "#f4a261", "#9b5de5"])
    plt.ylabel("Number of channels"); plt.title("Directional policy availability")
    plt.xticks(rotation=15, ha="right")
    save("policy_availability")

    plt.figure(figsize=(8, 5))
    plt.bar(["Nodes", "Channels", "Largest component"], [len(nodes), len(edges), summary["largest_component_nodes"]], color="#4d908e")
    plt.ylabel("Count"); plt.title("Snapshot scale and connectivity")
    save("network_scale")

    plt.figure(figsize=(8, 5))
    counts = Counter(components)
    plt.bar(range(1, min(len(components), 25) + 1), components[:25], color="#577590")
    plt.xlabel("Connected component rank"); plt.ylabel("Nodes in component")
    plt.title("Largest connected components")
    save("component_sizes")

    print(json.dumps(summary, indent=2))
    print(f"Figures: {args.plots}")
    print(f"Summary: {args.summary}")


if __name__ == "__main__":
    main()
